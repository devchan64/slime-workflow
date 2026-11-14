"""MIGraphX 빌드 접수와 상태를 공용 GPU 대기열에 연결한다."""
import fcntl
import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid
from datetime import datetime

from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON
from generators.kimodo.dwpose_runtime import validate_fun_pose_assets
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_job_queue import launch_gpu_process

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
POSE_BUILD_JOB_ROOT = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/kimodo-migraphx-build'
POSE_CACHE_CHECK_SECONDS = 30
POSE_CACHE_CHECK_LOCK = threading.Lock()
POSE_CACHE_CHECK_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='pose-cache-check')
POSE_CACHE_CHECK_STATE = {'future': None, 'signature': None, 'completed': None}


def check_pose_cache_environment():
    """빌드와 같은 Python·라이브러리 환경에서 모델과 캐시를 확인한다."""
    if not KIMODO_ENVIRONMENT_PYTHON.is_file():
        raise RuntimeError('Kimodo ROCm 실행 환경을 먼저 준비하세요.')
    current_worker_path = WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/migraphx_build_worker.py'
    current_process_result = subprocess.run([str(KIMODO_ENVIRONMENT_PYTHON), str(current_worker_path), '--check'],
                                            cwd=WORKFLOW_ROOT_DIRECTORY, capture_output=True, text=True, timeout=120)
    if current_process_result.returncode:
        raise RuntimeError('모델·GPU 실행 환경을 확인하지 못했습니다. 모델 준비와 GPU 상태를 확인하세요.')
    current_output_lines = current_process_result.stdout.strip().splitlines()
    current_result_record = json.loads(current_output_lines[-1]) if current_output_lines else {}
    if type(current_result_record.get('ready')) is not bool:
        raise ValueError('MIGraphX 캐시 검사 결과가 올바르지 않습니다.')
    return current_result_record['ready']


def inspect_pose_cache_validity(current_job_signature):
    """중복 검사를 제한하고 캐시 확인 중에는 준비 여부를 단정하지 않는다."""
    with POSE_CACHE_CHECK_LOCK:
        current_future_value = POSE_CACHE_CHECK_STATE['future']
        if current_future_value is not None and current_future_value.done() and POSE_CACHE_CHECK_STATE['completed'] is None:
            POSE_CACHE_CHECK_STATE['completed'] = time.monotonic()
        current_expired_value = (POSE_CACHE_CHECK_STATE['completed'] is not None
                                 and time.monotonic() - POSE_CACHE_CHECK_STATE['completed'] >= POSE_CACHE_CHECK_SECONDS)
        if current_future_value is None or ((current_expired_value or POSE_CACHE_CHECK_STATE['signature'] != current_job_signature) and current_future_value.done()):
            current_future_value = POSE_CACHE_CHECK_EXECUTOR.submit(check_pose_cache_environment)
            POSE_CACHE_CHECK_STATE.update(future=current_future_value, signature=current_job_signature, completed=None)
        if not current_future_value.done() or POSE_CACHE_CHECK_STATE['signature'] != current_job_signature:
            return {'status': 'checking'}
        try:
            return {'status': 'ready' if current_future_value.result() else 'rebuild_required'}
        except Exception as current_check_error:
            return {'status': 'unavailable', 'error': str(current_check_error) or type(current_check_error).__name__}


def inspect_pose_build_status():
    current_latest_path = POSE_BUILD_JOB_ROOT/'latest.json'
    try:
        current_job_name = json.loads(current_latest_path.read_text())['job']
        if Path(current_job_name).name != current_job_name:
            raise ValueError('잘못된 빌드 작업 ID')
        current_job_root = POSE_BUILD_JOB_ROOT/current_job_name
        current_status_record = json.loads((current_job_root/'status.json').read_text())
        current_status_record = {**current_status_record, 'id': current_job_name}
    except FileNotFoundError:
        current_status_record = {'status': 'idle'}
    if current_status_record.get('status') in ('queued', 'running'):
        return current_status_record
    current_job_signature = (current_status_record.get('id'), current_status_record.get('status'), current_status_record.get('exit_code'))
    return {**current_status_record, 'build_status': current_status_record.get('status'), **inspect_pose_cache_validity(current_job_signature)}


def start_pose_build_job():
    POSE_BUILD_JOB_ROOT.mkdir(parents=True, exist_ok=True)
    with (POSE_BUILD_JOB_ROOT/'submit.lock').open('a') as current_submit_lock:
        fcntl.flock(current_submit_lock, fcntl.LOCK_EX)
        current_status_record = inspect_pose_build_status()
        if current_status_record['status'] != 'rebuild_required':
            return current_status_record
        # 주기적인 화면 조회 후 환경이 바뀐 경우에도 불필요한 빌드를 접수하지 않는다.
        if check_pose_cache_environment():
            with POSE_CACHE_CHECK_LOCK:
                POSE_CACHE_CHECK_STATE.update(future=None, signature=None, completed=None)
            return {**current_status_record, 'status': 'ready'}
        if not KIMODO_ENVIRONMENT_PYTHON.is_file():
            raise ValueError('Kimodo ROCm 실행 환경을 먼저 준비하세요.')
        validate_fun_pose_assets()
        current_job_name = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
        current_job_root = POSE_BUILD_JOB_ROOT/current_job_name
        current_job_root.mkdir()
        current_worker_path = WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/migraphx_build_worker.py'
        with (current_job_root/'worker.log').open('ab') as current_log_stream:
            launch_gpu_process([str(KIMODO_ENVIRONMENT_PYTHON), str(current_worker_path)], current_job_root, 'image',
                               cwd=WORKFLOW_ROOT_DIRECTORY, stdout=current_log_stream, stderr=current_log_stream, start_new_session=True)
        write_record_atomically(POSE_BUILD_JOB_ROOT/'latest.json', {'job': current_job_name})
        return {'status': 'queued', 'id': current_job_name}
