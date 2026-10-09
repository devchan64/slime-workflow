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
import shutil
import subprocess
import time
import uuid
from tools.review.common.gpu_job_queue import launch_gpu_process

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
GENERATION_JOB_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/momask-generator/jobs'
GENERATION_HISTORY_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/momask-generator/history'
GENERATION_LOCK_FILE = GENERATION_JOB_DIRECTORY.parent / 'generation.lock'
SUPPORTED_ACTION_NAMES = ('standing', 'walking', 'resting', 'custom')
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


def resolve_motion_frame_count(action_name_value, requested_frame_count=None):
    if requested_frame_count is None:
        current_action_config=json.loads((WORKFLOW_ROOT_DIRECTORY/'generators/momask/config/standing-loops-v1.json').read_text())['actions']
        requested_frame_count=current_action_config['standing' if action_name_value=='custom' else action_name_value]['source_frames']
    if type(requested_frame_count) is not int or requested_frame_count<8 or requested_frame_count%4:
        raise ValueError('프레임 길이는 8 이상인 4의 배수 정수여야 합니다.')
    return requested_frame_count


def start_generation_job(action_name_value, direction_name_values, include_face_points=False, history_tag_value='', custom_prompt_text=None, requested_frame_count=None):
    raise ValueError('MoMask 포즈 생성기는 폐기되었습니다. HY-Motion을 사용하세요.')


def resume_generation_job(generation_job_identifier):
    raise ValueError('MoMask 포즈 생성기는 폐기되어 재개할 수 없습니다.')


def list_generation_history():
    GENERATION_HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    return [{**json.loads(record_file_path.read_text()), **json.loads((resolve_generation_directory(record_file_path.stem)/'status.json').read_text())} for record_file_path in sorted(GENERATION_HISTORY_DIRECTORY.glob('*.json'), reverse=True)]


def read_render_progress(generation_job_path, log_text_value):
    """Fra는 현재 원본 프레임이며 완료 수는 방향별 저장된 이미지로 계산한다."""
    render_root_path = generation_job_path/'result/anny'
    contract_file_path = render_root_path/'retarget-contract.json'
    if not contract_file_path.exists():
        return None
    contract_record_value = json.loads(contract_file_path.read_text())
    frames_per_direction = contract_record_value['frames']
    direction_name_values = contract_record_value['directions']
    total_frame_count = frames_per_direction * len(direction_name_values)
    if total_frame_count <= 0:
        return None
    completed_frame_count = sum(
        sum((render_root_path/direction/f'preview-{index:04d}.png').is_file()
            for index in range(1, frames_per_direction + 1))
        for direction in direction_name_values
    )
    frame_match_values = re.findall(r'\bFra:(\d+)\b', log_text_value)
    return {'stage': 'anny-render', 'completed_frames': completed_frame_count,
            'total_frames': total_frame_count,
            'current_source_frame': int(frame_match_values[-1]) if frame_match_values else None,
            'percent': round(100 * completed_frame_count / total_frame_count, 1)}


def read_generation_status(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_status_value = json.loads((generation_job_path/'status.json').read_text())
    generation_status_value['request'] = json.loads((generation_job_path/'request.json').read_text())
    saved_prompt_path = generation_job_path/'motion-run/prompt.txt'
    generation_status_value['prompt'] = saved_prompt_path.read_text() if saved_prompt_path.exists() else None
    generation_status_value['prompt_word_count'] = len(generation_status_value['prompt'].split()) if generation_status_value['prompt'] is not None else None
    generation_log_path = generation_job_path/'worker.log'
    generation_status_value['log'] = generation_log_path.read_text(errors='replace')[-12000:] if generation_log_path.exists() else ''
    generation_status_value['progress'] = read_render_progress(generation_job_path, generation_status_value['log'])
    if generation_status_value['progress'] is not None:
        render_progress_value = generation_status_value['progress']
        progress_message_value = f"ANNY 렌더 {render_progress_value['percent']}% · {render_progress_value['completed_frames']}/{render_progress_value['total_frames']}프레임 저장"
        if render_progress_value['current_source_frame'] is not None:
            progress_message_value += f" · 최근 Fra:{render_progress_value['current_source_frame']}"
        generation_status_value['message'] = (generation_status_value.get('message', '') + ' · ' + progress_message_value).strip(' ·')
    if (generation_job_path/'result.json').exists():
        generation_status_value['result'] = json.loads((generation_job_path/'result.json').read_text())
    return generation_status_value


def reset_generation_history():
    for record_file_path in GENERATION_HISTORY_DIRECTORY.glob('*.json'):
        record_file_path.unlink(missing_ok=True)
    return {'status':'cleared'}


def delete_generation_history(generation_job_identifier):
    generation_job_path=resolve_generation_directory(generation_job_identifier)
    if generation_job_path.is_symlink() or generation_job_path.resolve().parent!=GENERATION_JOB_DIRECTORY.resolve():
        raise ValueError('작업 저장소 밖 경로는 삭제할 수 없습니다.')
    generation_status_record=read_generation_status(generation_job_identifier)
    if generation_status_record['status'] in ('queued','running'):
        raise ValueError('대기·실행 중인 작업은 먼저 중지한 뒤 삭제하세요.')
    shutil.rmtree(generation_job_path)
    (GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json')).unlink(missing_ok=True)
    return {'deleted':generation_job_identifier,'files_preserved':False}


def cancel_generation_job(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    if json.loads((generation_job_path/'status.json').read_text())['status'] not in ('running','queued'):
        raise ValueError('실행 중인 작업이 아닙니다.')
    (generation_job_path/'cancel.request').touch()
    return {'status':'running', 'cancel_requested':True}


def supervise_generation_job(generation_job_identifier, inherited_lock_descriptor):
    os.close(inherited_lock_descriptor)
    inherited_lock_descriptor = None
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    generation_request_value = json.loads((generation_job_path/'request.json').read_text())
    generation_final_state = {'status':'failed'}
    generation_worker_process = None
    try:
        if (generation_job_path/'resume.request').exists():
            generation_command_values=[str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'generators/momask/resume_render.py'),'--job-dir',str(generation_job_path)]
        else:
            generation_command_values=[str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'generators/momask/run_managed_generation.py'),'--job-dir',str(generation_job_path),'--action',generation_request_value['action'],'--directions',','.join(generation_request_value['directions'])]
        generation_worker_process=launch_gpu_process(generation_command_values,generation_job_path,'momask',start_new_session=True)
        while generation_worker_process.poll() is None:
            if (generation_job_path/'cancel.request').exists():
                os.killpg(generation_worker_process.pid, signal.SIGTERM)
                try:
                    generation_worker_process.wait(timeout=15)
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
        saved_execution_record = json.loads((generation_job_path/'status.json').read_text())
        if saved_execution_record.get('error'): generation_final_state['error'] = saved_execution_record['error']
        write_record_atomically(generation_job_path/'status.json', generation_final_state)
        generation_history_path = GENERATION_HISTORY_DIRECTORY/(generation_job_identifier+'.json')
        # 사용자가 수동 초기화한 이력은 작업 종료 시 복원하지 않는다.
        if generation_history_path.exists():
            generation_record_value = json.loads(generation_history_path.read_text())
            generation_record_value.update(generation_final_state)
            write_record_atomically(generation_history_path, generation_record_value)
        if inherited_lock_descriptor is not None: os.close(inherited_lock_descriptor)


if __name__ == '__main__':
    execution_argument_parser = argparse.ArgumentParser()
    execution_argument_parser.add_argument('--supervise', required=True)
    execution_argument_parser.add_argument('--lock-fd', type=int, required=True)
    execution_argument_values = execution_argument_parser.parse_args()
    supervise_generation_job(execution_argument_values.supervise, execution_argument_values.lock_fd)
