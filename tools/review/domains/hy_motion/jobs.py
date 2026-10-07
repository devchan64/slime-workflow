"""HY-Motion 작업 서비스. 실행 수명과 GPU 동시성은 공용 대기열을 사용한다."""
from datetime import datetime, timedelta
import fcntl
import json
from pathlib import Path
import re
import statistics
import uuid
from zoneinfo import ZoneInfo

from generators.hy_motion.contracts import WORKFLOW_ROOT_DIRECTORY, MODEL_CACHE_DIRECTORY, load_generation_defaults, validate_generation_request, build_prompt_provenance
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation, resume_gpu_generation

GENERATION_STORAGE_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/hy-motion'
GENERATION_HISTORY_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/manager-current/hy-motion'
GENERATION_IDENTIFIER_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'
GENERATION_WORKER_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/worker.py'
GENERATION_PYTHON_PATH = WORKFLOW_ROOT_DIRECTORY / '.venv/bin/python'


def resolve_generation_directory(generation_job_identifier):
    if not isinstance(generation_job_identifier, str) or not re.fullmatch(GENERATION_IDENTIFIER_PATTERN, generation_job_identifier):
        raise ValueError('HY-Motion 생성 ID 형식 오류')
    generation_job_path = GENERATION_STORAGE_ROOT / generation_job_identifier[:19] / generation_job_identifier[20:]
    if generation_job_path.resolve() != generation_job_path.absolute():
        raise ValueError('작업 경로의 심볼릭 링크는 허용하지 않습니다.')
    return generation_job_path


def read_generation_status(generation_job_identifier):
    generation_job_path = resolve_generation_directory(generation_job_identifier)
    current_status_record = json.loads((generation_job_path / 'status.json').read_text())
    current_request_record = json.loads((generation_job_path / 'request.json').read_text())
    current_log_file = generation_job_path / 'worker.log'
    current_result_file = generation_job_path / 'result.json'
    current_log_text = ''
    if current_log_file.exists():
        with current_log_file.open('rb') as current_log_stream:
            current_log_stream.seek(max(0, current_log_file.stat().st_size - 16000))
            current_log_text = current_log_stream.read().decode(errors='replace')
    return {**current_status_record, 'eta': estimate_generation_completion(generation_job_path, current_request_record, current_status_record), 'id': generation_job_identifier, 'request': current_request_record,
            'prompt': current_request_record.get('prompt'), 'prompt_word_count': len(current_request_record.get('prompt', '').split()),
            'path': str(generation_job_path), 'log': current_log_text,
            'result': json.loads(current_result_file.read_text()) if current_result_file.exists() else None}


def estimate_generation_completion(generation_job_path, current_request_record, current_status_record):
    current_unknown_estimate = {'remaining': None, 'completion': None, 'basis': '동일 조건 완료 표본 없음 · 계산 중'}
    if current_status_record['status'] == 'queued':
        return {**current_unknown_estimate, 'basis': 'GPU 대기 중 · 시작 시각 미정'}
    if current_status_record['status'] != 'running' or not current_status_record.get('started_at') or current_request_record.get('action') == 'prepare':
        return current_unknown_estimate
    current_config_record = json.loads((generation_job_path / 'config.json').read_text())
    current_elapsed_samples = []
    for current_history_path in sorted(GENERATION_HISTORY_ROOT.glob('*.json'), reverse=True):
        current_sample_identifier = json.loads(current_history_path.read_text())['id']
        current_sample_directory = resolve_generation_directory(current_sample_identifier)
        current_result_path = current_sample_directory / 'result.json'
        if current_sample_directory == generation_job_path or not current_result_path.is_file():
            continue
        current_sample_request = json.loads((current_sample_directory / 'request.json').read_text())
        current_sample_status = json.loads((current_sample_directory / 'status.json').read_text())
        if current_sample_status['status'] != 'completed' or any(current_sample_request.get(current_field_name) != current_request_record[current_field_name] for current_field_name in ('duration_seconds', 'directions')):
            continue
        if len(current_sample_request.get('prompt', '').split()) != len(current_request_record['prompt'].split()) or json.loads((current_sample_directory / 'config.json').read_text()) != current_config_record:
            continue
        current_elapsed_samples.append(json.loads(current_result_path.read_text())['elapsed_seconds'])
        if len(current_elapsed_samples) == 5:
            break
    if not current_elapsed_samples:
        return current_unknown_estimate
    current_estimated_finish = datetime.fromisoformat(current_status_record['started_at']) + timedelta(seconds=statistics.median(current_elapsed_samples))
    current_remaining_seconds = (current_estimated_finish - datetime.now(ZoneInfo('Asia/Seoul'))).total_seconds()
    current_estimate_basis = f'동일 설정·길이·방향·프롬프트 단어 수의 최근 {len(current_elapsed_samples)}개 완료 실행 중앙값 · 환경 부하에 따라 변동'
    if current_remaining_seconds <= 0:
        return {**current_unknown_estimate, 'basis': current_estimate_basis + ' · 표본 시간을 초과하여 계산 중'}
    return {'remaining': round(current_remaining_seconds), 'completion': current_estimated_finish.isoformat(), 'basis': current_estimate_basis}


def list_generation_history():
    current_history_records = []
    for current_history_path in sorted(GENERATION_HISTORY_ROOT.glob('*.json'), reverse=True):
        current_history_record = json.loads(current_history_path.read_text())
        current_status_record = read_generation_status(current_history_record['id'])
        current_history_records.append({**current_history_record, 'status': current_status_record, 'request': current_status_record['request'], 'path': current_status_record['path'], 'playable': current_status_record['status'] == 'completed' and (current_status_record['result'] or {}).get('kind') == 'motion'})
    return {'records': current_history_records, 'running': any(current_history_record['status']['status'] in ('queued', 'running') for current_history_record in current_history_records)}


def start_generation_job(current_request_values, generation_operation_name='generate'):
    if generation_operation_name not in ('generate', 'prepare'):
        raise ValueError('지원하지 않는 HY-Motion 작업')
    current_request_values = validate_generation_request(current_request_values) if generation_operation_name == 'generate' else {'action': 'prepare'}
    GENERATION_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    with (GENERATION_HISTORY_ROOT / 'service.lock').open('a') as current_service_lock:
        fcntl.flock(current_service_lock, fcntl.LOCK_EX)
        current_creation_time = datetime.now(ZoneInfo('Asia/Seoul'))
        generation_job_identifier = current_creation_time.strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8]
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        generation_job_path.mkdir(parents=True)
        write_record_atomically(generation_job_path / 'request.json', current_request_values)
        write_record_atomically(generation_job_path / 'config.json', load_generation_defaults())
        write_record_atomically(generation_job_path / 'prompt.json', build_prompt_provenance(current_request_values.get('prompt', '')))
        write_record_atomically(generation_job_path / 'status.json', {'status': 'queued'})
        write_record_atomically(GENERATION_HISTORY_ROOT / (generation_job_identifier + '.json'), {'id': generation_job_identifier, 'created_at': current_creation_time.isoformat()})
        try:
            with (generation_job_path / 'worker.log').open('a') as current_log_stream:
                launch_gpu_process([str(GENERATION_PYTHON_PATH), str(GENERATION_WORKER_PATH), '--job-dir', str(generation_job_path)], generation_job_path, 'hy-motion', stdout=current_log_stream, stderr=current_log_stream, start_new_session=True)
        except Exception as current_launch_error:
            write_record_atomically(generation_job_path / 'status.json', {'status': 'failed', 'error': str(current_launch_error)})
            raise
    return {'id': generation_job_identifier, 'status': 'queued'}


def read_model_readiness():
    from generators.hy_motion.runtime import inspect_prepared_bundle
    return inspect_prepared_bundle()


def execute_hymotion_command(operation_command_name, command_payload_value):
    if not isinstance(command_payload_value, dict):
        raise ValueError('명령 입력은 객체여야 합니다.')
    if operation_command_name == 'generate':
        return start_generation_job(command_payload_value)
    if operation_command_name == 'prepare':
        if command_payload_value not in ({}, {'action': 'prepare'}):
            raise ValueError('준비 명령 입력 오류')
        return start_generation_job({}, 'prepare')
    if operation_command_name in ('history', 'model-status', 'history-reset'):
        if command_payload_value not in ({}, {'action': 'reset'} if operation_command_name == 'history-reset' else {}):
            raise ValueError('명령 입력 필드 오류')
        if operation_command_name == 'model-status':
            return read_model_readiness()
        if operation_command_name == 'history':
            return list_generation_history()
        GENERATION_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
        with (GENERATION_HISTORY_ROOT / 'service.lock').open('a') as current_service_lock:
            fcntl.flock(current_service_lock, fcntl.LOCK_EX)
            if list_generation_history()['running']:
                raise ValueError('실행·대기 중에는 이력을 초기화할 수 없습니다.')
            for current_history_path in GENERATION_HISTORY_ROOT.glob('*.json'):
                current_history_path.unlink()
        return {'status': 'cleared', 'files_preserved': True}
    if set(command_payload_value) != {'id'}:
        raise ValueError('생성 ID만 입력하세요.')
    generation_job_path = resolve_generation_directory(command_payload_value['id'])
    if operation_command_name == 'status':
        return read_generation_status(command_payload_value['id'])
    if operation_command_name == 'logs':
        return (generation_job_path / 'worker.log').read_text(errors='replace')
    if operation_command_name == 'cancel':
        return cancel_gpu_generation(generation_job_path)
    if operation_command_name == 'resume':
        with (GENERATION_HISTORY_ROOT / 'service.lock').open('a') as current_service_lock:
            fcntl.flock(current_service_lock, fcntl.LOCK_EX)
            current_resume_record = resume_gpu_generation(generation_job_path)
        return {**current_resume_record, 'id': command_payload_value['id']}
    raise ValueError('지원하지 않는 HY-Motion 명령')
