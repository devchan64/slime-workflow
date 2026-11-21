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
from tools.management.common.generation_records import write_record_atomically
from tools.management.common.gpu_job_queue import launch_gpu_process

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
POSE_BUILD_JOB_ROOT = WORKFLOW_ROOT_DIRECTORY/'.tmp/test/kimodo-migraphx-build'
POSE_CACHE_CHECK_SECONDS = 30
POSE_CACHE_CHECK_LOCK = threading.Lock()
POSE_CACHE_CHECK_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix='pose-cache-check')
POSE_CACHE_CHECK_STATE = {'future': None, 'signature': None, 'completed': None}


def check_pose_cache_environment():
    """GPU 장치 확인을 공용 대기열에서 배타적으로 수행한다."""
    import shutil
    import tempfile
    if not KIMODO_ENVIRONMENT_PYTHON.is_file():
        raise RuntimeError('Kimodo ROCm 실행 환경을 먼저 준비하세요.')
    current_check_root=POSE_BUILD_JOB_ROOT/'cache-checks'
    current_check_root.mkdir(parents=True,exist_ok=True)
    current_check_path=Path(tempfile.mkdtemp(prefix='check-',dir=current_check_root))
    current_worker_path=WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/migraphx_build_worker.py'
    current_queue_process=None
    try:
        with (current_check_path/'worker.log').open('w+',encoding='utf-8') as current_log_handle:
            current_queue_process=launch_gpu_process([str(KIMODO_ENVIRONMENT_PYTHON),str(current_worker_path),'--check'],current_check_path,'kimodo-cache-check',cwd=WORKFLOW_ROOT_DIRECTORY,stdout=current_log_handle,stderr=subprocess.STDOUT,start_new_session=True)
            try:
                current_exit_code=current_queue_process.wait(timeout=120)
            except subprocess.TimeoutExpired as current_timeout_error:
                (current_check_path/'cancel.request').touch()
                try:current_queue_process.wait(timeout=30)
                except subprocess.TimeoutExpired:pass
                raise RuntimeError('GPU 대기 또는 캐시 검사가 시간 제한을 넘었습니다. 잠시 후 다시 확인하세요.') from current_timeout_error
            current_status_record=json.loads((current_check_path/'status.json').read_text())
            if current_exit_code!=0 or current_status_record.get('status')!='completed':
                raise RuntimeError('모델·GPU 실행 환경을 확인하지 못했습니다. 모델 준비와 GPU 상태를 확인하세요.')
            current_log_handle.flush()
            current_log_handle.seek(0)
            current_output_lines=current_log_handle.read().splitlines()
            current_result_records=[]
            for current_output_line in current_output_lines:
                try:current_parsed_value=json.loads(current_output_line)
                except (ValueError,TypeError):continue
                if isinstance(current_parsed_value,dict) and set(current_parsed_value)=={'ready'} and type(current_parsed_value['ready']) is bool:
                    current_result_records.append(current_parsed_value)
            if len(current_result_records)!=1:
                raise ValueError('MIGraphX 캐시 검사 결과가 올바르지 않습니다.')
            return current_result_records[0]['ready']
    finally:
        if current_queue_process is None or current_queue_process.poll() is not None:
            shutil.rmtree(current_check_path)


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


def inspect_recorded_pose_build_status():
    """GPU 초기화 없이 최근 빌드 기록만 읽는다. 캐시 유효성은 검사하지 않는다."""
    import re
    try:
        current_latest_text=(POSE_BUILD_JOB_ROOT/'latest.json').read_text()
    except FileNotFoundError:
        return {'status':'idle','id':None,'cache_status':'unverified'}
    current_job_identifier=json.loads(current_latest_text)['job']
    if not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier):
        raise ValueError('빌드 작업 ID 오류')
    current_status_record=json.loads((POSE_BUILD_JOB_ROOT/current_job_identifier/'status.json').read_text())
    current_status_value=current_status_record['status']
    if current_status_value not in ('queued','running','completed','failed','cancelled'):
        raise ValueError('빌드 상태 오류')
    current_result_record={'status':current_status_value,'id':current_job_identifier,'cache_status':'unverified'}
    current_error_value=current_status_record.get('error')
    if current_status_value=='failed' and isinstance(current_error_value,str):
        if current_error_value.startswith('시스템 RAM 보호:'):current_result_record['failure_code']='host_memory_guard'
        elif current_error_value.startswith('시스템 RAM 감시 실패:'):current_result_record['failure_code']='host_memory_monitor_failed'
    return current_result_record


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
