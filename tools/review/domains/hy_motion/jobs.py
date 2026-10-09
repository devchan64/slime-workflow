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
from tools.review.common.generation_estimates import calculate_generation_estimate
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
    current_estimate_scope = '작업 시작부터 모델 로드·모션 추론·ANNY 제약·렌더·OpenPose·패키징까지 · GPU 대기 제외'
    current_unknown_estimate = calculate_generation_estimate(current_status_record, [], '동일 조건 완료 표본 없음 · 첫 완료 실행 후 계산 가능', current_estimate_scope)
    if current_status_record['status'] not in ('running', 'queued'):
        return current_unknown_estimate
    if current_status_record.get('progress', {}).get('stage') == 'render' and current_status_record.get('attempt_path'):
        current_attempt_directory = (generation_job_path / current_status_record['attempt_path']).resolve()
        if not current_attempt_directory.is_relative_to(generation_job_path.resolve()):
            raise ValueError('시간 추정 시도 경로가 작업 경계를 벗어났습니다.')
        current_render_directory = current_attempt_directory if current_request_record.get('action') == 'export-vnccs' else current_attempt_directory / 'anny'
        current_stage_path = current_render_directory / 'stage-request.json'
        if current_stage_path.is_file():
            current_stage_record = json.loads(current_stage_path.read_text())
            current_render_request = current_stage_record['request']
            current_total_units = len(range(current_render_request['start_frame'], current_render_request['end_frame'] + 1, current_render_request['frame_step'])) * len(current_render_request['directions']) * len(current_stage_record['config']['projections'])
            current_render_times = sorted(current_image_path.stat().st_mtime for current_image_path in current_render_directory.glob('**/frame-*.png') if re.fullmatch(r'frame-\d{4}\.png', current_image_path.name))
            if 2 <= len(current_render_times) < current_total_units:
                current_recent_times = current_render_times[-6:]
                current_unit_intervals = [current_right_time - current_left_time for current_left_time, current_right_time in zip(current_recent_times, current_recent_times[1:])]
                current_remaining_units = current_total_units - len(current_render_times)
                current_render_estimate = calculate_generation_estimate({'status': 'running', 'started_at': datetime.fromtimestamp(current_render_times[-1], ZoneInfo('Asia/Seoul')).isoformat()}, [statistics.median(current_unit_intervals) * current_remaining_units], f'현재 작업 렌더 {len(current_render_times)}/{current_total_units}장 · 최근 {len(current_unit_intervals)}개 완료 간격 중앙값', '남은 ANNY 렌더 단계만 · 후속 OpenPose·패키징 시간 제외')
                current_render_estimate.update(sample_count=len(current_unit_intervals), completed_units=len(current_render_times), total_units=current_total_units, measured_progress=round(100 * len(current_render_times) / current_total_units, 1), estimated_progress=None, total_seconds=None)
                return current_render_estimate
    if current_request_record.get('action') == 'export-vnccs':
        return {**current_unknown_estimate, 'basis': '리그 변환·CUDA 렌더 출력 · 소요 시간 표본 수집 전'}
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
        current_render_path = generation_job_path / 'render-config.json'
        current_sample_render_path = current_sample_directory / 'render-config.json'
        if current_render_path.exists() != current_sample_render_path.exists():
            continue
        if current_render_path.exists() and json.loads(current_render_path.read_text()) != json.loads(current_sample_render_path.read_text()):
            continue
        current_elapsed_samples.append(json.loads(current_result_path.read_text())['elapsed_seconds'])
        if len(current_elapsed_samples) == 5:
            break
    if not current_elapsed_samples:
        return current_unknown_estimate
    current_estimate_basis = f'동일 설정·길이·방향·프롬프트 단어 수의 최근 {len(current_elapsed_samples)}개 완료 실행 중앙값 · 환경 부하에 따라 변동'
    return calculate_generation_estimate(current_status_record, current_elapsed_samples, current_estimate_basis, current_estimate_scope)


def list_generation_history():
    current_history_records = []
    for current_history_path in sorted(GENERATION_HISTORY_ROOT.glob('*.json'), reverse=True):
        current_history_record = json.loads(current_history_path.read_text())
        current_status_record = read_generation_status(current_history_record['id'])
        current_history_records.append({**current_history_record, 'status': current_status_record, 'request': current_status_record['request'], 'path': current_status_record['path'], 'playable': current_status_record['status'] == 'completed' and (current_status_record['result'] or {}).get('kind') in ('motion', 'vnccs')})
    return {'records': current_history_records, 'running': any(current_history_record['status']['status'] in ('queued', 'running') for current_history_record in current_history_records)}


def start_generation_job(current_request_values, generation_operation_name='generate'):
    if generation_operation_name not in ('generate', 'prepare', 'export-vnccs'):
        raise ValueError('지원하지 않는 HY-Motion 작업')
    current_export_source = None
    if generation_operation_name == 'export-vnccs':
        from generators.hy_motion.vnccs_contract import validate_vnccs_request, load_vnccs_config, calculate_file_digest
        current_source_directory = resolve_generation_directory(current_request_values.get('source_id'))
        current_source_status = read_generation_status(current_request_values['source_id'])
        if current_source_status['status'] != 'completed' or (current_source_status['result'] or {}).get('kind') != 'motion':
            raise ValueError('완료된 HY-Motion 원본 생성 ID만 VNCCS 출력할 수 있습니다.')
        current_source_frames = current_source_status['result']['source_frames']
        current_request_values = {**validate_vnccs_request(current_request_values, current_source_frames), 'action': 'export-vnccs'}
        current_motion_path = current_source_directory / current_source_status['result']['relative_path'] / 'motion.npz'
        if not current_motion_path.resolve().is_relative_to(current_source_directory.resolve()) or current_motion_path.is_symlink():
            raise ValueError('원본 모션 경로 오류')
        current_export_source = {'source_id': current_request_values['source_id'], 'job_directory': str(current_source_directory), 'motion_path': str(current_motion_path), 'motion_sha256': calculate_file_digest(current_motion_path), 'request': current_source_status['request'], 'frames': current_source_frames}
        current_config_record = load_vnccs_config()
    else:
        current_request_values = validate_generation_request(current_request_values) if generation_operation_name == 'generate' else {'action': 'prepare'}
        current_config_record = load_generation_defaults()
    GENERATION_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
    with (GENERATION_HISTORY_ROOT / 'service.lock').open('a') as current_service_lock:
        fcntl.flock(current_service_lock, fcntl.LOCK_EX)
        current_creation_time = datetime.now(ZoneInfo('Asia/Seoul'))
        generation_job_identifier = current_creation_time.strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8]
        generation_job_path = resolve_generation_directory(generation_job_identifier)
        generation_job_path.mkdir(parents=True)
        write_record_atomically(generation_job_path / 'request.json', current_request_values)
        write_record_atomically(generation_job_path / 'config.json', current_config_record)
        if generation_operation_name == 'generate':
            from generators.hy_motion.vnccs_contract import load_vnccs_config
            write_record_atomically(generation_job_path / 'render-config.json', load_vnccs_config())
        if current_export_source is not None:
            write_record_atomically(generation_job_path / 'export-source.json', current_export_source)
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
    if operation_command_name == 'export-vnccs':
        return start_generation_job(command_payload_value, 'export-vnccs')
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
    if operation_command_name == 'history-delete':
        GENERATION_HISTORY_ROOT.mkdir(parents=True, exist_ok=True)
        with (GENERATION_HISTORY_ROOT / 'service.lock').open('a') as current_service_lock:
            fcntl.flock(current_service_lock, fcntl.LOCK_EX)
            current_selected_status = read_generation_status(command_payload_value['id'])
            if current_selected_status['status'] in ('running', 'queued'):
                raise ValueError('실행·대기 중인 이력은 삭제할 수 없습니다. 종료 후 다시 선택하세요.')
            current_selected_path = GENERATION_HISTORY_ROOT / (command_payload_value['id'] + '.json')
            if not current_selected_path.is_file() or current_selected_path.is_symlink():
                raise ValueError('삭제할 생성 이력이 없거나 올바른 파일이 아닙니다.')
            current_selected_path.unlink()
        return {'status': 'deleted', 'id': command_payload_value['id'], 'files_preserved': True}
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
