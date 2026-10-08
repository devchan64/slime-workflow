"""캐릭터 애니메이션의 GUI·CLI 공용 기록과 독립 작업 감독."""
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
import shutil
import subprocess
import time
import traceback
import uuid
from tools.review.common.gpu_job_queue import launch_gpu_process

from tools.review.domains.character_animation.character_animation_assets import WORKFLOW_ROOT_DIRECTORY, prepare_animation_request, build_animation_catalog, load_animation_configuration
from tools.review.common.generation_records import write_record_atomically

GENERATION_ROOT_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/character-animation'
GENERATION_HISTORY_DIRECTORY = GENERATION_ROOT_DIRECTORY/'history'
GENERATION_LOCK_PATH = GENERATION_ROOT_DIRECTORY/'generation.lock'
VNCCS_ALPHA_SOURCE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/vnccs-posestudio-qi21-4frame-results/2026-10-08_19-48-55'
VNCCS_ALPHA_SOURCE_FRAME_NUMBERS = (1,16,31,46)
VNCCS_ALPHA_VERSION_NAME = 'vnccs-posestudio-qi21-alpha-0.1'

def resolve_generation_directory(generation_job_identifier):
    if not isinstance(generation_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',generation_job_identifier):
        raise ValueError('생성 ID 형식 오류')
    return GENERATION_ROOT_DIRECTORY/generation_job_identifier[:19]/generation_job_identifier

def describe_generation_progress(generation_job_path, generation_request_record, generation_status_record):
    """완료 이미지·원본 번호·한 이미지의 추론 스텝을 구분한다."""
    saved_progress_record = generation_status_record.get('progress',{})
    source_frame_records = generation_request_record['frames']
    total_frame_count = len(source_frame_records)
    completed_frame_count = saved_progress_record.get('completed',0)
    if type(completed_frame_count) is not int or not 0 <= completed_frame_count <= total_frame_count:
        raise ValueError('완료 이미지 수가 요청 범위를 벗어났습니다.')
    if generation_status_record['status']=='completed':
        completed_frame_count=total_frame_count
    progress_display_record = {'completed':completed_frame_count,'total':total_frame_count,'stage':'preparing','inference_steps':generation_request_record.get('steps',4),'inference_completed':None}
    if generation_status_record['status'] not in ('running','queued'):
        progress_display_record['stage']=generation_status_record['status']
        return progress_display_record
    if completed_frame_count==total_frame_count:
        progress_display_record['stage']='saving'
        return progress_display_record
    source_frame_record=source_frame_records[completed_frame_count]
    direction_frame_records=[frame_record_value for frame_record_value in source_frame_records if frame_record_value['direction']==source_frame_record['direction']]
    progress_display_record.update(direction=source_frame_record['direction'],frame=source_frame_record['frame'],direction_index=direction_frame_records.index(source_frame_record)+1,direction_total=len(direction_frame_records))
    frame_log_path=generation_job_path/source_frame_record['direction']/f"frame-{source_frame_record['frame']:04d}"/'execution.log'
    if frame_log_path.exists():
        with frame_log_path.open('rb') as frame_log_handle:
            frame_log_handle.seek(max(0,frame_log_path.stat().st_size-8000))
            recent_frame_log=frame_log_handle.read().decode(errors='replace')
        for frame_log_line in recent_frame_log.splitlines():
            if '/qwen-pose/load ' in frame_log_line:progress_display_record['stage']='load'
            if '/qwen-pose/inference ' in frame_log_line:progress_display_record['stage']='inference'
            step_match_value=re.search(r'/qwen-pose/(?:denoise step=|heartbeat stage=inference step=)(\d+)/(\d+)',frame_log_line)
            if step_match_value:
                progress_display_record['stage']='inference'
                progress_display_record['inference_completed']=int(step_match_value[1])
            if '/qwen-pose/complete ' in frame_log_line:progress_display_record['stage']='saving'
    elif 'stage=waiting-gpu' in generation_status_record.get('log',''):
        progress_display_record['stage']='waiting-gpu'
    return progress_display_record

def estimate_generation_remaining(generation_job_path, generation_request_record, generation_status_record):
    """같은 작업의 최근 완료 이미지 최대 5장으로 남은 시간을 추정한다."""
    if generation_status_record['status'] not in ('running','queued'):
        return {'remaining_seconds':0 if generation_status_record['status']=='completed' else None,'reason':'finished','samples':0}
    progress_record_value=generation_status_record['progress']
    completed_frame_count=progress_record_value['completed']
    source_frame_records=generation_request_record['frames']
    completed_duration_values=[]
    for frame_record_value in source_frame_records[max(0,completed_frame_count-5):completed_frame_count]:
        frame_result_path=generation_job_path/frame_record_value['direction']/f"frame-{frame_record_value['frame']:04d}"/'result.json'
        if frame_result_path.exists():
            duration_seconds_value=json.loads(frame_result_path.read_text()).get('elapsed_seconds')
            if isinstance(duration_seconds_value,(int,float)) and not isinstance(duration_seconds_value,bool) and 0<duration_seconds_value<float('inf'):
                completed_duration_values.append(duration_seconds_value)
    if not completed_duration_values:return {'remaining_seconds':None,'reason':'first-frame','samples':0}
    average_duration_seconds=sum(completed_duration_values)/len(completed_duration_values)
    current_elapsed_seconds=0
    if completed_frame_count<len(source_frame_records):
        current_frame_record=source_frame_records[completed_frame_count]
        current_reference_path=generation_job_path/current_frame_record['direction']/f"frame-{current_frame_record['frame']:04d}"/'character-reference.png'
        if current_reference_path.exists():current_elapsed_seconds=max(0,time.time()-current_reference_path.stat().st_mtime)
        if current_elapsed_seconds>=average_duration_seconds:
            return {'remaining_seconds':None,'reason':'overrun','samples':len(completed_duration_values)}
    remaining_seconds_value=max(0,round(average_duration_seconds*(len(source_frame_records)-completed_frame_count)-current_elapsed_seconds))
    return {'remaining_seconds':remaining_seconds_value,'estimated_finish_at':datetime.fromtimestamp(time.time()+remaining_seconds_value,ZoneInfo('Asia/Seoul')).isoformat(),'reason':'measured','samples':len(completed_duration_values)}

def collect_partial_result(generation_job_path, generation_request_record):
    completed_frame_records={}
    source_number_records={}
    for source_frame_record in generation_request_record['frames']:
        frame_direction_name=source_frame_record['direction']
        frame_relative_directory=f"{frame_direction_name}/frame-{source_frame_record['frame']:04d}"
        frame_output_directory=generation_job_path/frame_relative_directory
        frame_result_path=frame_output_directory/'result.json'
        if not frame_result_path.is_file() or not (frame_output_directory/'result.png').is_file():continue
        if json.loads(frame_result_path.read_text()).get('status')!='completed':continue
        completed_frame_records.setdefault(frame_direction_name,[]).append(frame_relative_directory+'/result.png')
        source_number_records.setdefault(frame_direction_name,[]).append(source_frame_record['frame'])
    if not completed_frame_records:return None
    return {'frames':completed_frame_records,'source_frame_numbers':source_number_records,'fps':generation_request_record['fps'],'partial':True,'completed':sum(map(len,completed_frame_records.values())),'total':len(generation_request_record['frames'])}

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
    generation_status_record['progress']=describe_generation_progress(generation_job_path,generation_status_record['request'],generation_status_record)
    generation_status_record['preview']=None
    completed_frame_count=generation_status_record['progress']['completed']
    if completed_frame_count:
        latest_frame_record=generation_status_record['request']['frames'][completed_frame_count-1]
        latest_frame_directory=f"{latest_frame_record['direction']}/frame-{latest_frame_record['frame']:04d}"
        if (generation_job_path/latest_frame_directory/'result.png').is_file():
            generation_status_record['preview']={'direction':latest_frame_record['direction'],'frame':latest_frame_record['frame'],'completed':completed_frame_count,'image':latest_frame_directory+'/result.png','reference':latest_frame_directory+'/character-reference.png'}
    if generation_status_record['status']!='completed':
        generation_status_record['result']=collect_partial_result(generation_job_path,generation_status_record['request'])
    generation_status_record['estimate']=estimate_generation_remaining(generation_job_path,generation_status_record['request'],generation_status_record)
    return generation_status_record

def start_animation_generation(command_payload_value):
    generation_request_record = prepare_animation_request(command_payload_value)
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True,exist_ok=True)
    generation_lock_handle = GENERATION_LOCK_PATH.open('a')
    try:
        try: fcntl.flock(generation_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('캐릭터 애니메이션 생성이 이미 진행 중입니다.') from None
        # 동일 입력의 대기·실행 작업은 기존 ID를 반환하여 연속 클릭을 합친다.
        for existing_status_path in GENERATION_ROOT_DIRECTORY.glob('*/*/status.json'):
            existing_status_record=json.loads(existing_status_path.read_text())
            if existing_status_record.get('status') not in ('running','queued'):continue
            existing_request_path=existing_status_path.parent/'request.json'
            current_existing_request=json.loads(existing_request_path.read_text()) if existing_request_path.is_file() else None
            if current_existing_request and 'character_image' in current_existing_request:
                for current_frame_record in current_existing_request['frames']:
                    current_frame_record['character_path']='character-reference.png'
            if current_existing_request==generation_request_record:
                return {'id':existing_status_path.parent.name,'status':existing_status_record['status'],'path':str(existing_status_path.parent),'reused':True}
        creation_time_value = datetime.now(ZoneInfo('Asia/Seoul'))
        generation_job_identifier = creation_time_value.strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        generation_job_path.mkdir(parents=True)
        if 'character_image' in generation_request_record:
            from tools.review.domains.character_animation.character_animation_assets import decode_character_reference
            current_reference_path=generation_job_path/'character-reference.png'
            current_reference_path.write_bytes(decode_character_reference(generation_request_record['character_image']))
            for current_frame_record in generation_request_record['frames']:
                current_frame_record['character_path']=str(current_reference_path.relative_to(WORKFLOW_ROOT_DIRECTORY))
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

def resume_animation_generation(command_payload_value):
    if set(command_payload_value)!={'id'}:raise ValueError('재개에는 작업 ID만 필요합니다.')
    generation_job_identifier=command_payload_value['id']
    generation_job_path=resolve_generation_directory(generation_job_identifier)
    with GENERATION_LOCK_PATH.open('a') as generation_lock_handle:
        try:fcntl.flock(generation_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('다른 캐릭터 애니메이션 생성이 진행 중입니다.') from None
        generation_status_record=read_generation_status(generation_job_identifier)
        if generation_status_record['status'] not in ('cancelled','failed'):raise ValueError('취소되거나 실패한 작업만 재개할 수 있습니다.')
        saved_request_record=json.loads((generation_job_path/'request.json').read_text())
        if saved_request_record['motion'] not in load_animation_configuration()['motions']:
            raise ValueError('폐기된 모션의 작업은 재개할 수 없습니다. 등록된 모션으로 새로 생성하세요.')
        (generation_job_path/'cancel.request').unlink(missing_ok=True)
        write_record_atomically(generation_job_path/'status.json',{'status':'running'})
        write_record_atomically(GENERATION_ROOT_DIRECTORY/'active.json',{'id':generation_job_identifier})
        try:
            with (generation_job_path/'worker.log').open('a') as generation_log_handle:
                generation_log_handle.write(f'{datetime.now().isoformat()}/character-animation/resume id={generation_job_identifier}\n')
                generation_log_handle.flush()
                subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--supervise',generation_job_identifier,'--lock-fd',str(generation_lock_handle.fileno())],stdout=generation_log_handle,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(generation_lock_handle.fileno(),))
        except Exception as generation_start_error:
            write_record_atomically(generation_job_path/'status.json',{'status':'failed','error':str(generation_start_error)})
            raise
    return {'id':generation_job_identifier,'status':'running','path':str(generation_job_path)}

def record_vnccs_alpha_pilot(command_payload_value):
    """검증 완료한 VNCCS 파일럿을 재추론 없이 공용 이력으로 가져온다."""
    if command_payload_value != {}:
        raise ValueError('VNCCS 알파 기록 명령에는 입력값을 넣을 수 없습니다.')
    source_assessment_path=VNCCS_ALPHA_SOURCE_DIRECTORY/'pilot-assessment.json'
    if not source_assessment_path.is_file():
        raise ValueError('검증 완료된 VNCCS 알파 판정 기록을 찾을 수 없습니다.')
    source_assessment_record=json.loads(source_assessment_path.read_text(encoding='utf-8'))
    if source_assessment_record.get('status')!='completed':
        raise ValueError('완료된 VNCCS 알파 결과만 기록할 수 있습니다.')
    source_frame_paths=[]
    for frame_offset_value in range(len(VNCCS_ALPHA_SOURCE_FRAME_NUMBERS)):
        source_frame_path=VNCCS_ALPHA_SOURCE_DIRECTORY/f'frame-{frame_offset_value+1:02d}'/'result-4step.png'
        if not source_frame_path.is_file():
            raise ValueError(f'VNCCS 알파 {frame_offset_value+1}번 프레임 결과를 찾을 수 없습니다.')
        source_frame_paths.append(source_frame_path)
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True,exist_ok=True)
    existing_record_paths=sorted(GENERATION_HISTORY_DIRECTORY.glob('*.json'),reverse=True)
    for existing_history_path in existing_record_paths:
        existing_history_record=json.loads(existing_history_path.read_text(encoding='utf-8'))
        existing_job_path=resolve_generation_directory(existing_history_record['id'])
        existing_request_path=existing_job_path/'request.json'
        if existing_request_path.is_file() and json.loads(existing_request_path.read_text(encoding='utf-8')).get('alpha_version')==VNCCS_ALPHA_VERSION_NAME:
            return {'id':existing_history_record['id'],'status':'completed','path':str(existing_job_path),'reused':True}
    creation_time_value=datetime.now(ZoneInfo('Asia/Seoul'))
    generation_job_identifier=creation_time_value.strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
    generation_job_path=resolve_generation_directory(generation_job_identifier)
    generation_job_path.mkdir(parents=True)
    result_frame_paths=[]
    for frame_offset_value,(source_frame_number,source_frame_path) in enumerate(zip(VNCCS_ALPHA_SOURCE_FRAME_NUMBERS,source_frame_paths),start=1):
        destination_frame_directory=generation_job_path/'down_left'/f'frame-{source_frame_number:04d}'
        destination_frame_directory.mkdir(parents=True)
        destination_frame_path=destination_frame_directory/'result.png'
        shutil.copy2(source_frame_path,destination_frame_path)
        write_record_atomically(destination_frame_directory/'result.json',{'status':'completed','source':'vnccs-alpha-import','source_frame':source_frame_number})
        result_frame_paths.append(str(destination_frame_path.relative_to(generation_job_path)))
    shutil.copy2(source_assessment_path,generation_job_path/'pilot-assessment.json')
    source_experiment_path=str(VNCCS_ALPHA_SOURCE_DIRECTORY)
    if VNCCS_ALPHA_SOURCE_DIRECTORY.is_relative_to(WORKFLOW_ROOT_DIRECTORY):
        source_experiment_path=str(VNCCS_ALPHA_SOURCE_DIRECTORY.relative_to(WORKFLOW_ROOT_DIRECTORY))
    alpha_request_record={
        'record_kind':'alpha-import','alpha_version':VNCCS_ALPHA_VERSION_NAME,
        'motion':'walking-v13','character':'experimental-reference','source':'vnccs-posestudio-qi21',
        'directions':['down_left'],'start_frame':VNCCS_ALPHA_SOURCE_FRAME_NUMBERS[0],
        'end_frame':VNCCS_ALPHA_SOURCE_FRAME_NUMBERS[-1],'resolution':256,'steps':4,
        'target_fps':4,'speed':1,'tag':'VNCCS PoseStudio QI2.1 알파 · 검증 기준선',
        'frames':[{'direction':'down_left','frame':source_frame_number} for source_frame_number in VNCCS_ALPHA_SOURCE_FRAME_NUMBERS],
        'source_experiment':source_experiment_path,
        'adoption_decision':'production-sprite-output-rejected',
    }
    alpha_result_record={'frames':{'down_left':result_frame_paths},'source_frame_numbers':{'down_left':list(VNCCS_ALPHA_SOURCE_FRAME_NUMBERS)},'fps':4,'alpha':True}
    write_record_atomically(generation_job_path/'request.json',alpha_request_record)
    write_record_atomically(generation_job_path/'result.json',alpha_result_record)
    write_record_atomically(generation_job_path/'status.json',{'status':'completed','record_kind':'alpha-import','quality_gate':'rejected-for-production-sprite-output'})
    (generation_job_path/'worker.log').write_text(f'{creation_time_value.isoformat()}/character-animation/alpha-record imported version={VNCCS_ALPHA_VERSION_NAME} source={alpha_request_record["source_experiment"]}\n',encoding='utf-8')
    write_record_atomically(GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json'),{'id':generation_job_identifier,'created_at':creation_time_value.isoformat(),'record_kind':'alpha-import'})
    return {'id':generation_job_identifier,'status':'completed','path':str(generation_job_path),'alpha_version':VNCCS_ALPHA_VERSION_NAME}

def execute_animation_command(operation_command_name,command_payload_value):
    if operation_command_name.startswith('sprite-v2-'):
        from .sprite_editor_v2 import execute_v2_command
        return execute_v2_command(operation_command_name,command_payload_value)
    if operation_command_name in ('anchor-save','anchor-history','anchor-load','anchor-history-reset'):
        from .anchor_history import execute_anchor_history_command
        return execute_anchor_history_command(operation_command_name,command_payload_value)
    if operation_command_name in ('sprite-source','sprite-save','sprite-load','sprite-history','sprite-history-reset','sprite-history-delete'):
        from .sprite_editor import execute_sprite_editor_command
        return execute_sprite_editor_command(operation_command_name,command_payload_value)
    if operation_command_name=='resume':return resume_animation_generation(command_payload_value)
    if operation_command_name=='catalog':
        return build_animation_catalog()
    if operation_command_name=='generate':
        return start_animation_generation(command_payload_value)
    if operation_command_name=='record-alpha-vnccs':
        return record_vnccs_alpha_pilot(command_payload_value)
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
            preview_image_record=generation_status_value.get('preview')
            history_record_value['image']=(f"/character-animation/files/{history_record_value['id']}/{preview_image_record['image']}" if preview_image_record else None)
            measured_progress_record=generation_status_value['progress']
            completed_image_count=measured_progress_record['completed']
            total_image_count=measured_progress_record['total']
            stage_label_value={'preparing':'생성 준비 중','load':'모델 로딩 중','inference':'추론 중','saving':'결과 저장 중','waiting-gpu':'GPU 대기 중','queued':'GPU 대기 중'}.get(measured_progress_record['stage'],measured_progress_record['stage'])
            if generation_status_value['status']=='queued':stage_label_value='GPU 대기 중'
            detail_text_value=stage_label_value
            if measured_progress_record.get('frame') is not None:
                detail_text_value+=f" · {measured_progress_record['direction']} · 원본 {measured_progress_record['frame']}번"
            if measured_progress_record.get('inference_completed') is not None:
                detail_text_value+=f" · 현재 이미지 추론 {measured_progress_record['inference_completed']}/{measured_progress_record['inference_steps']}스텝"
            history_record_value['progress']={'label':'이미지 생성','unit':'장 완료','completed_frames':completed_image_count,'total_frames':total_image_count,'percent':round(100*completed_image_count/total_image_count,1) if total_image_count else 0,'detail':detail_text_value}
            history_record_values.append({**history_record_value,'path':generation_status_value['path'],'status':{'status':generation_status_value['status'],'error':generation_status_value.get('error')},'request':{**{key:generation_status_value['request'][key] for key in ('motion','character','source','directions','start_frame','end_frame')},'tag':generation_status_value['request'].get('tag',''),'resolution':generation_status_value['request'].get('resolution',512),'speed':generation_status_value['request'].get('speed',1),'target_fps':generation_status_value['request'].get('target_fps'),'frame_step':generation_status_value['request'].get('frame_step',1),'steps':generation_status_value['request'].get('steps',4),'alpha_version':generation_status_value['request'].get('alpha_version')},'playable':bool(generation_status_value.get('result'))})
        return {'records':history_record_values}
    if operation_command_name=='history-delete':
        selected_job_identifier=command_payload_value['id']
        selected_job_status=read_generation_status(selected_job_identifier)
        if selected_job_status['status'] in ('queued','running'):
            raise ValueError('대기·실행 중인 작업은 먼저 중지한 뒤 삭제하세요.')
        selected_history_path=GENERATION_HISTORY_DIRECTORY/(selected_job_identifier+'.json')
        selected_history_path.unlink(missing_ok=True)
        return {'deleted':selected_job_identifier,'files_preserved':True}
    if operation_command_name=='history-reset':
        for history_record_path in GENERATION_HISTORY_DIRECTORY.glob('*.json'):history_record_path.unlink(missing_ok=True)
        return {'status':'cleared'}
    if operation_command_name=='cancel':
        generation_job_path = resolve_generation_directory(command_payload_value['id'])
        if read_generation_status(command_payload_value['id'])['status'] not in ('running','queued'):raise ValueError('실행 중인 작업이 아닙니다.')
        (generation_job_path/'cancel.request').touch()
        return {'status':'running','cancel_requested':True}
    raise ValueError('지원하지 않는 명령')

def supervise_animation_generation(generation_job_identifier,inherited_lock_descriptor):
    os.close(inherited_lock_descriptor)
    inherited_lock_descriptor = None
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_final_record = {'status':'failed'}
    generation_worker_process = None
    try:
        print(f'{datetime.now().isoformat()}/character-animation/start id={generation_job_identifier} root={generation_job_path}',flush=True)
        generation_worker_process = launch_gpu_process([str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'generators/animation/run_character_animation.py'),'--job-dir',str(generation_job_path)],generation_job_path,'character-animation',start_new_session=True)
        heartbeat_clock_value = 0
        while generation_worker_process.poll() is None:
            if (generation_job_path/'cancel.request').exists():
                os.killpg(generation_worker_process.pid,signal.SIGTERM)
                try:generation_worker_process.wait(timeout=15)
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
        saved_execution_record = json.loads((generation_job_path/'status.json').read_text())
        if saved_execution_record.get('error'): generation_final_record['error'] = saved_execution_record['error']
        write_record_atomically(generation_job_path/'status.json',generation_final_record)
        # 이력 인덱스는 생성 시에만 기록한다. 수동 초기화 뒤 자동 복원하지 않는다.
        print(f'{datetime.now().isoformat()}/character-animation/end {generation_final_record}',flush=True)
        if inherited_lock_descriptor is not None: os.close(inherited_lock_descriptor)

if __name__=='__main__':
    execution_argument_parser=argparse.ArgumentParser()
    execution_argument_parser.add_argument('--supervise',required=True)
    execution_argument_parser.add_argument('--lock-fd',required=True,type=int)
    execution_argument_values=execution_argument_parser.parse_args()
    supervise_animation_generation(execution_argument_values.supervise,execution_argument_values.lock_fd)
