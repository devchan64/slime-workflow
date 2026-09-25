"""캐릭터 애니메이션의 GUI·CLI 공용 기록과 독립 작업 감독."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import sys
import time
import traceback
import uuid

if __package__:
    from .character_animation_assets import WORKFLOW_ROOT_DIRECTORY, prepare_animation_request, build_animation_catalog
    from .momask_jobs import write_record_atomically
else:
    from character_animation_assets import WORKFLOW_ROOT_DIRECTORY, prepare_animation_request, build_animation_catalog
    from momask_jobs import write_record_atomically

GENERATION_ROOT_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/character-animation'
GENERATION_HISTORY_DIRECTORY = GENERATION_ROOT_DIRECTORY/'history'
GENERATION_LOCK_PATH = GENERATION_ROOT_DIRECTORY/'generation.lock'

def resolve_generation_directory(generation_job_identifier):
    if not isinstance(generation_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',generation_job_identifier):
        raise ValueError('생성 ID 형식 오류')
    return GENERATION_ROOT_DIRECTORY/generation_job_identifier[:19]/generation_job_identifier

def read_generation_status(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_status_record = json.loads((generation_job_path/'status.json').read_text())
    generation_log_path = generation_job_path/'worker.log'
    with generation_log_path.open('rb') as generation_log_handle:
        generation_log_handle.seek(max(0,generation_log_path.stat().st_size-16000))
        generation_status_record['log'] = generation_log_handle.read().decode(errors='replace')
    for record_file_name in ('progress','result'):
        record_file_path = generation_job_path/(record_file_name+'.json')
        if record_file_path.exists():
            generation_status_record[record_file_name] = json.loads(record_file_path.read_text())
    generation_status_record.update(id=generation_job_identifier,path=str(generation_job_path),request=json.loads((generation_job_path/'request.json').read_text()))
    return generation_status_record

def start_animation_generation(command_payload_value):
    generation_request_record = prepare_animation_request(command_payload_value)
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True,exist_ok=True)
    generation_lock_handle = GENERATION_LOCK_PATH.open('a')
    try:
        try: fcntl.flock(generation_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('캐릭터 애니메이션 생성이 이미 진행 중입니다.') from None
        creation_time_value = datetime.now(ZoneInfo('Asia/Seoul'))
        generation_job_identifier = creation_time_value.strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        generation_job_path.mkdir(parents=True)
        write_record_atomically(generation_job_path/'request.json',generation_request_record)
        write_record_atomically(generation_job_path/'status.json',{'status':'running'})
        write_record_atomically(GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json'),{'id':generation_job_identifier,'created_at':creation_time_value.isoformat()})
        write_record_atomically(GENERATION_ROOT_DIRECTORY/'active.json',{'id':generation_job_identifier})
        try:
            with (generation_job_path/'worker.log').open('w') as generation_log_handle:
                subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--supervise',generation_job_identifier,'--lock-fd',str(generation_lock_handle.fileno())],stdout=generation_log_handle,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(generation_lock_handle.fileno(),))
        except Exception as generation_start_error:
            write_record_atomically(generation_job_path/'status.json',{'status':'failed','error':str(generation_start_error)})
            raise
        return {'id':generation_job_identifier,'status':'running','path':str(generation_job_path)}
    finally:
        generation_lock_handle.close()

def execute_animation_command(operation_command_name,command_payload_value):
    if operation_command_name=='catalog':
        return build_animation_catalog()
    if operation_command_name=='generate':
        return start_animation_generation(command_payload_value)
    if operation_command_name=='status':
        return read_generation_status(command_payload_value['id'])
    if operation_command_name=='logs':
        return (resolve_generation_directory(command_payload_value['id'])/'worker.log').read_text(errors='replace')
    if operation_command_name=='active':
        active_record_path = GENERATION_ROOT_DIRECTORY/'active.json'
        if not active_record_path.exists(): return {'running':False}
        active_record_value = json.loads(active_record_path.read_text())
        return {**active_record_value,'running':read_generation_status(active_record_value['id'])['status']=='running'}
    if operation_command_name=='history':
        history_record_values = []
        for history_record_path in sorted(GENERATION_HISTORY_DIRECTORY.glob('*.json'),reverse=True):
            history_record_value = json.loads(history_record_path.read_text())
            generation_status_value = read_generation_status(history_record_value['id'])
            history_record_values.append({**history_record_value,'status':{'status':generation_status_value['status'],'error':generation_status_value.get('error')},'request':{**{key:generation_status_value['request'][key] for key in ('motion','character','source','directions')},'frame_step':generation_status_value['request'].get('frame_step',1)},'playable':generation_status_value['status']=='completed'})
        return {'records':history_record_values}
    if operation_command_name=='history-reset':
        for history_record_path in GENERATION_HISTORY_DIRECTORY.glob('*.json'):history_record_path.unlink(missing_ok=True)
        return {'status':'cleared'}
    if operation_command_name=='cancel':
        generation_job_path = resolve_generation_directory(command_payload_value['id'])
        if read_generation_status(command_payload_value['id'])['status']!='running':raise ValueError('실행 중인 작업이 아닙니다.')
        (generation_job_path/'cancel.request').touch()
        return {'status':'running','cancel_requested':True}
    raise ValueError('지원하지 않는 명령')

def supervise_animation_generation(generation_job_identifier,inherited_lock_descriptor):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_final_record = {'status':'failed'}
    generation_worker_process = None
    try:
        print(f'{datetime.now().isoformat()}/character-animation/start id={generation_job_identifier} root={generation_job_path}',flush=True)
        generation_worker_process = subprocess.Popen([str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'generators/animation/run_character_animation.py'),'--job-dir',str(generation_job_path)],start_new_session=True)
        heartbeat_clock_value = 0
        while generation_worker_process.poll() is None:
            if (generation_job_path/'cancel.request').exists():
                os.killpg(generation_worker_process.pid,signal.SIGTERM)
                try:generation_worker_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(generation_worker_process.pid,signal.SIGKILL)
                    generation_worker_process.wait()
                break
            if time.monotonic()-heartbeat_clock_value>=5:
                progress_record_path = generation_job_path/'progress.json'
                print(f'{datetime.now().isoformat()}/character-animation/heartbeat progress={progress_record_path.read_text() if progress_record_path.exists() else "준비 중"}',flush=True)
                heartbeat_clock_value=time.monotonic()
            time.sleep(.25)
        generation_final_record = {'status':'cancelled' if (generation_job_path/'cancel.request').exists() else 'completed' if generation_worker_process.returncode==0 else 'failed','exit_code':generation_worker_process.returncode}
        if generation_final_record['status']=='completed' and not (generation_job_path/'result.json').exists():
            raise ValueError('작업이 결과 목록을 작성하지 않았습니다.')
    except Exception as generation_execution_error:
        generation_final_record={'status':'failed','error':str(generation_execution_error)}
        traceback.print_exc()
    finally:
        if generation_worker_process is not None and generation_worker_process.poll() is None:
            os.killpg(generation_worker_process.pid,signal.SIGKILL)
            generation_worker_process.wait()
        write_record_atomically(generation_job_path/'status.json',generation_final_record)
        # 이력 인덱스는 생성 시에만 기록한다. 수동 초기화 뒤 자동 복원하지 않는다.
        print(f'{datetime.now().isoformat()}/character-animation/end {generation_final_record}',flush=True)
        os.close(inherited_lock_descriptor)

if __name__=='__main__':
    execution_argument_parser=argparse.ArgumentParser()
    execution_argument_parser.add_argument('--supervise',required=True)
    execution_argument_parser.add_argument('--lock-fd',required=True,type=int)
    execution_argument_values=execution_argument_parser.parse_args()
    supervise_animation_generation(execution_argument_values.supervise,execution_argument_values.lock_fd)
