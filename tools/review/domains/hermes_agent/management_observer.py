"""Hermes가 사용할 관리 상태의 제한된 읽기 전용 관측값."""
from datetime import datetime, timezone


def inspect_hermes_model_status(current_model_ready=None, current_preparation_status=None):
    """기존 모델 관리와 같은 준비 판정을 읽는다. 모델을 적재하지 않는다."""
    from tools.review.common.hermes_model_download import WORKFLOW_ROOT_DIRECTORY, inspect_hermes_model_files
    from tools.review.common.model_prepare_process import inspect_registered_preparation
    from tools.review.domains.hermes_agent.service import validate_hermes_runtime_ready
    if current_model_ready is None:
        current_model_ready = inspect_hermes_model_files()
    if current_preparation_status is None:
        current_preparation_status = inspect_registered_preparation(WORKFLOW_ROOT_DIRECTORY, 'hermes-model')
    current_runtime_ready = False
    current_status_message = '모델 파일 준비 필요 · 다운로드 후 SHA-256 검증'
    if current_model_ready:
        try:
            validate_hermes_runtime_ready()
            current_runtime_ready = True
            current_status_message = '모델과 실행 구성 준비 · GPU 접근과 전체 해시는 실행 시 확인'
        except ValueError as current_runtime_error:
            current_status_message = '모델 파일 준비됨 · ' + str(current_runtime_error)
    if current_preparation_status == 'failed':
        current_status_message += ' · 다운로드 실패: 준비 로그 확인 후 재시도'
    return {'ready': current_model_ready, 'generation_ready': current_runtime_ready, 'message': current_status_message, 'preparation_status': current_preparation_status}


def read_hermes_generator_snapshot():
    """등록된 Kimodo의 모델·활성 상태만 기존 게이트웨이로 조회한다."""
    import os
    import re
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command
    try:
        current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        current_model_response = execute_management_command('kimodo', 'model-status', {}, current_gateway_address)
        if not isinstance(current_model_response, dict) or type(current_model_response.get('ready')) is not bool:
            raise ValueError('생성기 모델 상태 형식 오류')
        current_preparation_state = current_model_response.get('preparation_status')
        if current_preparation_state not in ('idle', 'running', 'completed', 'failed'):
            current_preparation_state = 'unknown'
        current_model_values = {'status': 'available', 'ready': current_model_response['ready'], 'preparation_status': current_preparation_state}
    except (OSError, ValueError, TypeError, KeyError):
        current_model_values = {'status': 'unavailable'}
    try:
        current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        current_active_response = execute_management_command('kimodo', 'active', {}, current_gateway_address)
        if not isinstance(current_active_response, dict) or type(current_active_response.get('running')) is not bool:
            raise ValueError('생성기 활성 상태 형식 오류')
        current_job_identifier = current_active_response.get('id')
        if current_job_identifier is not None and (not isinstance(current_job_identifier, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', current_job_identifier)):
            raise ValueError('생성기 활성 작업 ID 형식 오류')
        if current_active_response['running'] and current_job_identifier is None:
            raise ValueError('실행 중인 생성기 작업 ID 누락')
        current_active_values = {'status': 'available', 'running': current_active_response['running'], 'id': current_job_identifier}
    except (OSError, ValueError, TypeError, KeyError):
        current_active_values = {'status': 'unavailable'}
    return {'kimodo': {'model': current_model_values, 'active': current_active_values}}


def read_hermes_memory_capacity(current_gpu_values):
    """공용 대기열과 같은 영역·호스트 여유 기준의 현재 수치를 제공한다."""
    import sys
    from tools.review.common.gpu_job_queue import GPU_MEMORY_REQUIREMENTS, read_host_available_memory
    from tools.review.common.gpu_memory_history import estimate_required_memory, identify_execution_command
    from tools.review.common.host_memory_guard import HOST_MEMORY_RESERVE_KIB
    from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY
    try:
        if current_gpu_values.get('status') not in ('idle', 'busy'):
            raise ValueError('GPU 정보 없음')
        current_gtt_total = current_gpu_values.get('gtt_total_mib')
        current_vram_total = current_gpu_values.get('vram_total_mib')
        if any(type(current_value) is not int or current_value < 0 for current_value in (current_gtt_total, current_vram_total)):
            raise ValueError('GPU 메모리 영역 정보 오류')
        current_memory_domain = 'vram' if current_vram_total > current_gtt_total else 'gtt'
        current_gpu_free = current_gpu_values.get(current_memory_domain + '_free_mib')
        if type(current_gpu_free) is not int or current_gpu_free < 0:
            raise ValueError('GPU 여유 메모리 정보 오류')
        current_host_available = read_host_available_memory()
        if type(current_host_available) is not int or current_host_available < 0:
            raise ValueError('호스트 여유 메모리 정보 오류')
        current_worker_path = WORKFLOW_ROOT_DIRECTORY / 'tools/review/domains/hermes_agent/worker.py'
        current_command_identity = identify_execution_command([sys.executable, str(current_worker_path)], None, current_memory_domain)
        current_memory_estimate = estimate_required_memory('hermes-agent', GPU_MEMORY_REQUIREMENTS['hermes-agent'], current_command_identity)
        current_required_memory = current_memory_estimate['required_memory_mib']
        if type(current_required_memory) is not int or current_required_memory < 1:
            raise ValueError('예약량 정보 오류')
        current_host_reserve = HOST_MEMORY_RESERVE_KIB // 1024
        current_pool_available = min(current_gpu_free, current_host_available) if current_memory_domain == 'gtt' else current_gpu_free if current_host_available >= current_host_reserve else 0
        return {'status': 'available', 'domain': current_memory_domain, 'gpu_free_mib': current_gpu_free, 'host_available_mib': current_host_available, 'host_reserve_mib': current_host_reserve, 'required_mib': current_required_memory, 'pool_available_mib': current_pool_available, 'capacity_sufficient': current_pool_available >= current_required_memory, 'detail': '관측 당시 메모리만 비교하며 다른 예약과 작업 순서는 반영하지 않습니다.'}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status': 'unavailable'}


def read_hermes_gpu_reservation_snapshot(current_queue_root=None):
    """공용 대기열의 예약 기록만 읽고 정리하거나 프로세스를 중지하지 않는다."""
    import json
    import os
    import re
    import stat
    from pathlib import Path
    from tools.review.common.gpu_job_queue import GPU_QUEUE_DIRECTORY
    try:
        current_queue_root = Path(current_queue_root) if current_queue_root is not None else GPU_QUEUE_DIRECTORY
        current_active_root = current_queue_root / 'active'
        if current_queue_root.is_symlink() or current_active_root.is_symlink():
            raise ValueError('GPU 예약 경로가 심볼릭 링크입니다.')
        try:
            current_active_stat = current_active_root.stat()
        except FileNotFoundError:
            return {'status':'available', 'records':[], 'truncated':False, 'note':'예약 기록이며 실행기 생존과 해제 여부는 별도 확인이 필요합니다.'}
        if not stat.S_ISDIR(current_active_stat.st_mode):
            raise ValueError('GPU 예약 경로 형식 오류')
        with os.scandir(current_active_root) as current_directory_entries:
            current_record_paths = sorted(current_active_root / current_entry.name for current_entry in current_directory_entries if current_entry.name.endswith('.json'))
        current_reservation_values = []
        for current_record_path in current_record_paths[:100]:
            try:
                if current_record_path.is_symlink() or not current_record_path.is_file():
                    raise ValueError('예약 기록 형식 오류')
                current_reservation_record = json.loads(current_record_path.read_text())
                current_service_name = current_reservation_record['service']
                current_memory_value = current_reservation_record['required_memory_mib']
                if not isinstance(current_service_name, str) or not re.fullmatch(r'[a-z0-9-]{1,64}', current_service_name) or type(current_memory_value) is not int or current_memory_value < 0:
                    raise ValueError('예약 필드 형식 오류')
                current_job_path = current_reservation_record.get('path')
                current_job_identifier = Path(current_job_path).name if isinstance(current_job_path, str) else None
                if not isinstance(current_job_identifier, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', current_job_identifier):
                    current_job_identifier = None
                current_reservation_values.append({'state':'recorded', 'service':current_service_name, 'job_id':current_job_identifier, 'required_memory_mib':current_memory_value})
            except (OSError, ValueError, TypeError, KeyError):
                current_reservation_values.append({'state':'unknown', 'service':None, 'job_id':None, 'required_memory_mib':None})
        return {'status':'available', 'records':current_reservation_values, 'truncated':len(current_record_paths)>100, 'note':'예약 기록이며 실행기 생존과 해제 여부는 별도 확인이 필요합니다.'}
    except (OSError, ValueError, TypeError):
        return {'status':'unavailable', 'records':[], 'truncated':False}


def read_hermes_recent_job_snapshot(current_service_manager=None):
    """기존 작업의 ID와 상태만 조회하고 지시·경로·로그는 반환하지 않는다."""
    import json
    from tools.review.domains.hermes_agent.service import HermesServiceManager
    try:
        current_service_manager = current_service_manager or HermesServiceManager()
        with current_service_manager.hold_hermes_service_lock():
            current_job_paths = current_service_manager.list_hermes_job_paths()
            current_job_values = []
            for current_job_path in current_job_paths[:10]:
                current_status_path = current_job_path / 'status.json'
                try:
                    if current_status_path.is_symlink() or not current_status_path.is_file():
                        raise ValueError('작업 상태 파일 없음')
                    current_status_record = json.loads(current_status_path.read_text())
                    current_status_name = current_status_record['status']
                    if current_status_name not in ('queued', 'running', 'completed', 'failed', 'cancelled'):
                        raise ValueError('작업 상태 형식 오류')
                except (OSError, ValueError, TypeError, KeyError):
                    current_status_name = 'unknown'
                current_job_values.append({'id': current_job_path.name, 'status': current_status_name})
            return {'status': 'available', 'jobs': current_job_values, 'truncated': len(current_job_paths) > 10}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status': 'unavailable', 'jobs': [], 'truncated': False}


def read_hermes_management_snapshot():
    """공용 GPU 관측과 대기열에서 지정된 필드만 반환한다."""
    from tools.review.common.gpu_status import read_gpu_status
    from tools.review.common.gpu_job_queue import list_waiting_gpu_jobs

    try:
        current_gpu_record = read_gpu_status()
        if not isinstance(current_gpu_record, dict) or current_gpu_record.get('status') not in ('idle', 'busy', 'unavailable'):
            raise ValueError('GPU 상태 형식 오류')
        current_gpu_values = {'status': current_gpu_record['status']}
        if current_gpu_record['status'] in ('idle', 'busy'):
            for current_memory_field in ('gtt_total_mib', 'gtt_free_mib', 'vram_total_mib', 'vram_free_mib'):
                current_memory_value = current_gpu_record.get(current_memory_field)
                current_gpu_values[current_memory_field] = current_memory_value if type(current_memory_value) is int and current_memory_value >= 0 else None
            current_process_records = current_gpu_record.get('processes')
            current_gpu_values['process_count'] = len(current_process_records) if isinstance(current_process_records, list) else None
    except (OSError, ValueError, TypeError, KeyError):
        current_gpu_values = {'status': 'unavailable'}

    try:
        current_queue_record = list_waiting_gpu_jobs()
        current_waiting_jobs = current_queue_record['jobs']
        if not isinstance(current_waiting_jobs, list):
            raise ValueError('GPU 대기열 형식 오류')
        current_queue_values = {'status': 'available', 'jobs': []}
        for current_job_record in current_waiting_jobs:
            if not isinstance(current_job_record, dict) or not isinstance(current_job_record.get('id'), str) or not isinstance(current_job_record.get('service'), str):
                raise ValueError('GPU 대기 작업 형식 오류')
            current_queue_values['jobs'].append({'id': current_job_record['id'], 'service': current_job_record['service']})
    except (OSError, ValueError, TypeError, KeyError):
        current_queue_values = {'status': 'unavailable', 'jobs': []}

    try:
        current_model_values = {'status': 'available', **inspect_hermes_model_status()}
    except (OSError, ValueError, TypeError, KeyError):
        current_model_values = {'status': 'unavailable'}

    return {'queried_at': datetime.now(timezone.utc).isoformat(),
            'detail': '조회 시각이며 GPU 관측값은 공용 상태 조회의 짧은 캐시를 사용할 수 있습니다.',
            'model': current_model_values, 'gpu': current_gpu_values, 'memory_capacity': read_hermes_memory_capacity(current_gpu_values), 'queue': current_queue_values, 'reservations': read_hermes_gpu_reservation_snapshot(),
            'generators': read_hermes_generator_snapshot(), 'recent_hermes_jobs': read_hermes_recent_job_snapshot()}
