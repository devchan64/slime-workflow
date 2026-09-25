"""웹·CLI 공용 MoMask 작업 생성과 독립 실행 감독."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import fcntl
import json
import os
import re
import signal
import subprocess
import time
import uuid

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
GENERATION_JOB_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/momask-generator/jobs'
GENERATION_HISTORY_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/momask-generator/history'
GENERATION_LOCK_FILE = GENERATION_JOB_DIRECTORY.parent / 'generation.lock'
SUPPORTED_ACTION_NAMES = ('standing', 'deep_breath', 'stretch', 'walking')
SUPPORTED_DIRECTION_NAMES = ('down_left', 'down_right', 'up_left', 'up_right')


from tools.review.common.generation_records import write_record_atomically


def resolve_generation_directory(generation_job_identifier):
    if not re.fullmatch(r'[0-9a-f_-]+', generation_job_identifier):
        raise ValueError('생성 ID 형식 오류')
    return GENERATION_JOB_DIRECTORY / generation_job_identifier


def check_generation_running():
    GENERATION_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with GENERATION_LOCK_FILE.open('a') as generation_lock_handle:
        try:
            fcntl.flock(generation_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
    return False


def start_generation_job(action_name_value, direction_name_values):
    if action_name_value not in SUPPORTED_ACTION_NAMES or not direction_name_values or len(set(direction_name_values)) != len(direction_name_values) or set(direction_name_values)-set(SUPPORTED_DIRECTION_NAMES):
        raise ValueError('포즈 또는 방향 요청 오류')
    GENERATION_JOB_DIRECTORY.mkdir(parents=True, exist_ok=True)
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    generation_lock_handle = GENERATION_LOCK_FILE.open('a')
    try:
        try:
            fcntl.flock(generation_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('MoMask 생성 작업이 실행 중입니다.') from None
        creation_time_value = datetime.now(ZoneInfo('Asia/Seoul'))
        generation_job_identifier = creation_time_value.strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        generation_job_path.mkdir()
        generation_record_value = dict(id=generation_job_identifier, created_at=creation_time_value.isoformat(), action=action_name_value, directions=direction_name_values, status='running')
        write_record_atomically(generation_job_path/'request.json', dict(action=action_name_value, directions=direction_name_values))
        write_record_atomically(generation_job_path/'status.json', {'status':'running'})
        write_record_atomically(GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json'), generation_record_value)
        try:
            with (generation_job_path/'worker.log').open('w') as generation_log_handle:
                subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--supervise', generation_job_identifier, '--lock-fd', str(generation_lock_handle.fileno())], stdout=generation_log_handle, stderr=subprocess.STDOUT, start_new_session=True, pass_fds=(generation_lock_handle.fileno(),))
        except Exception:
            generation_record_value['status']='failed'
            write_record_atomically(generation_job_path/'status.json', {'status':'failed','error':'작업 실행기 시작 실패'})
            write_record_atomically(GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json'), generation_record_value)
            raise
        return {'id':generation_job_identifier, 'status':'running'}
    finally:
        generation_lock_handle.close()


def list_generation_history():
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return [json.loads(record_file_path.read_text()) for record_file_path in sorted(GENERATION_HISTORY_DIRECTORY.glob('*.json'), reverse=True)]


def read_generation_status(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_status_value = json.loads((generation_job_path/'status.json').read_text())
    generation_log_path = generation_job_path/'worker.log'
    generation_status_value['log'] = generation_log_path.read_text(errors='replace')[-12000:] if generation_log_path.exists() else ''
    if (generation_job_path/'result.json').exists():
        generation_status_value['result'] = json.loads((generation_job_path/'result.json').read_text())
    return generation_status_value


def reset_generation_history():
    for record_file_path in GENERATION_HISTORY_DIRECTORY.glob('*.json'):
        record_file_path.unlink(missing_ok=True)
    return {'status':'cleared'}


def cancel_generation_job(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    if json.loads((generation_job_path/'status.json').read_text())['status'] != 'running':
        raise ValueError('실행 중인 작업이 아닙니다.')
    (generation_job_path/'cancel.request').touch()
    return {'status':'running', 'cancel_requested':True}


def supervise_generation_job(generation_job_identifier, inherited_lock_descriptor):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_request_value = json.loads((generation_job_path/'request.json').read_text())
    generation_final_state = {'status':'failed'}
    generation_worker_process = None
    try:
        generation_worker_process = subprocess.Popen([str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'), str(WORKFLOW_ROOT_DIRECTORY/'generators/momask/run_managed_generation.py'), '--job-dir', str(generation_job_path), '--action', generation_request_value['action'], '--directions', ','.join(generation_request_value['directions'])], start_new_session=True)
        while generation_worker_process.poll() is None:
            if (generation_job_path/'cancel.request').exists():
                os.killpg(generation_worker_process.pid, signal.SIGTERM)
                try:
                    generation_worker_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(generation_worker_process.pid, signal.SIGKILL)
                    generation_worker_process.wait()
                break
            time.sleep(.25)
        generation_final_state = {'status':'cancelled' if (generation_job_path/'cancel.request').exists() else ('completed' if generation_worker_process.returncode == 0 else 'failed'), 'exit_code':generation_worker_process.returncode}
    except Exception as execution_error_value:
        generation_final_state['error']=str(execution_error_value)
        raise
    finally:
        write_record_atomically(generation_job_path/'status.json', generation_final_state)
        generation_history_path = GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json')
        # 사용자가 수동 초기화한 이력은 작업 종료 시 복원하지 않는다.
        if generation_history_path.exists():
            generation_record_value = json.loads(generation_history_path.read_text())
            generation_record_value.update(generation_final_state)
            write_record_atomically(generation_history_path, generation_record_value)
        os.close(inherited_lock_descriptor)


if __name__ == '__main__':
    execution_argument_parser = argparse.ArgumentParser()
    execution_argument_parser.add_argument('--supervise', required=True)
    execution_argument_parser.add_argument('--lock-fd', type=int, required=True)
    execution_argument_values = execution_argument_parser.parse_args()
    supervise_generation_job(execution_argument_values.supervise, execution_argument_values.lock_fd)
