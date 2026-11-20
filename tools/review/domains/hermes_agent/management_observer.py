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
        current_active_response = execute_management_command('kimodo', 'active-observe', {}, current_gateway_address)
        if not isinstance(current_active_response, dict) or type(current_active_response.get('running')) is not bool:
            raise ValueError('생성기 활성 상태 형식 오류')
        current_job_identifier = current_active_response.get('id')
        if current_job_identifier is not None and (not isinstance(current_job_identifier, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}', current_job_identifier)):
            raise ValueError('생성기 활성 작업 ID 형식 오류')
        current_recorded_count=current_active_response.get('count')
        current_unknown_count=current_active_response.get('unknown_count')
        if type(current_recorded_count) is not int or current_recorded_count<0 or type(current_unknown_count) is not int or current_unknown_count<0 or current_active_response['running']!=(current_recorded_count>0) or (current_job_identifier is None)!=(current_recorded_count==0):
            raise ValueError('생성기 활성 기록 수와 작업 ID가 일치하지 않습니다.')
        current_active_values = {'status': 'available', 'running': current_active_response['running'], 'id': current_job_identifier, 'count':current_recorded_count,'unknown_count':current_unknown_count}
    except (OSError, ValueError, TypeError, KeyError):
        current_active_values = {'status': 'unavailable'}
    return {'kimodo': {'model': current_model_values, 'active': current_active_values}}


def read_hermes_memory_capacity(current_gpu_values):
    """공용 대기열과 같은 영역·호스트 여유 기준의 현재 수치를 제공한다."""
    import sys
    from tools.review.common.gpu_job_queue import GPU_MEMORY_REQUIREMENTS, read_host_available_memory, calculate_gpu_pool_capacity
    from tools.review.common.gpu_memory_history import estimate_required_memory, identify_execution_command
    from tools.review.common.host_memory_guard import HOST_MEMORY_RESERVE_KIB
    from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY
    try:
        if current_gpu_values.get('status') not in ('idle', 'busy'):
            raise ValueError('GPU 정보 없음')
        current_device_memory=current_gpu_values.get('queue_device_memory')
        if not isinstance(current_device_memory,dict):raise ValueError('대기열 장치 메모리 정보 없음')
        current_gtt_total = current_device_memory.get('gtt_total_mib')
        current_vram_total = current_device_memory.get('vram_total_mib')
        if any(type(current_value) is not int or current_value < 0 for current_value in (current_gtt_total, current_vram_total)):
            raise ValueError('GPU 메모리 영역 정보 오류')
        current_memory_domain = 'vram' if current_vram_total > current_gtt_total else 'gtt'
        current_gpu_free = current_device_memory.get(current_memory_domain + '_free_mib')
        current_gpu_total=current_device_memory.get(current_memory_domain+'_total_mib')
        if type(current_gpu_free) is not int or current_gpu_total<=0 or not 0<=current_gpu_free<=current_gpu_total:
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
        current_pool_available = calculate_gpu_pool_capacity(current_memory_domain,current_gpu_free,current_host_available)
        return {'status': 'available', 'domain': current_memory_domain, 'gpu_free_mib': current_gpu_free, 'host_available_mib': current_host_available, 'host_reserve_mib': current_host_reserve, 'required_mib': current_required_memory, 'pool_available_mib': current_pool_available, 'capacity_sufficient': current_pool_available >= current_required_memory, 'detail': '관측 당시 메모리만 비교하며 다른 예약과 작업 순서는 반영하지 않습니다. 첫 번째 GPU의 수치를 사용하며 실제 실행 가능 여부를 보장하지 않습니다.'}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status': 'unavailable'}


def read_hermes_gpu_reservation_snapshot(current_queue_root=None):
    """공용 대기열의 예약 기록만 읽고 정리하거나 프로세스를 중지하지 않는다."""
    import json
    import os
    import re
    import stat
    from pathlib import Path
    from tools.review.common.gpu_job_queue import GPU_QUEUE_DIRECTORY, is_gpu_queue_executor_alive, open_verified_hermes_process_group, identify_gpu_queue_source, identify_dedicated_gpu_reservation_source, is_dedicated_gpu_source_verifiable
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
                if not isinstance(current_job_identifier, str) or not re.fullmatch(r'(?:\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}|\d{8}-\d{6})-[a-f0-9]{8}', current_job_identifier):
                    current_job_identifier = None
                current_cleanup_flag=current_reservation_record.get('cleanup_unverified',False)
                if type(current_cleanup_flag) is not bool:raise ValueError('예약 정리 상태 오류')
                if not current_cleanup_flag:
                    current_executor_pid=current_reservation_record.get('pid')
                    current_executor_token=current_reservation_record.get('pid_start_token')
                    if type(current_executor_pid) is not int or current_executor_pid<=1 or not isinstance(current_executor_token,str) or not is_gpu_queue_executor_alive(current_executor_pid,current_executor_token):
                        current_cleanup_flag=True
                current_safe_record={'state':'cleanup_unverified' if current_cleanup_flag else 'recorded', 'service':current_service_name, 'job_id':current_job_identifier, 'required_memory_mib':current_memory_value}
                if current_job_identifier is not None and isinstance(current_job_path,str):
                    current_source_service=identify_gpu_queue_source(current_job_path,current_service_name)
                    if current_source_service is None and is_dedicated_gpu_source_verifiable(current_service_name):
                        current_source_service=identify_dedicated_gpu_reservation_source(current_job_path,current_service_name)
                    if current_source_service is not None:
                        current_safe_record['source_service']=current_source_service
                if current_cleanup_flag and (current_service_name=='writer-agent' or 'worker_pgid' in current_reservation_record):
                    current_worker_descriptor=open_verified_hermes_process_group(current_reservation_record)
                    current_safe_record['worker_leader']='verified_running' if current_worker_descriptor is not None else 'unverified'
                    if current_worker_descriptor is not None:os.close(current_worker_descriptor)
                current_reservation_values.append(current_safe_record)
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
            current_queue_device=current_gpu_record.get('queue_device_memory')
            if isinstance(current_queue_device,dict):
                current_gpu_values['queue_device_memory']={current_field_name:current_queue_device.get(current_field_name) if type(current_queue_device.get(current_field_name)) is int and current_queue_device[current_field_name]>=0 else None for current_field_name in ('gtt_total_mib','gtt_free_mib','vram_total_mib','vram_free_mib')}
            current_device_count=current_gpu_record.get('gpu_count')
            current_gpu_values['gpu_count']=current_device_count if type(current_device_count) is int and current_device_count>0 else None
            current_process_records = current_gpu_record.get('processes')
            current_gpu_values['process_count'] = len(current_process_records) if isinstance(current_process_records, list) else None
    except (OSError, ValueError, TypeError, KeyError):
        current_gpu_values = {'status': 'unavailable'}

    try:
        current_queue_record = list_waiting_gpu_jobs(include_source_identity=True)
        current_waiting_jobs = current_queue_record['jobs']
        if not isinstance(current_waiting_jobs, list):
            raise ValueError('GPU 대기열 형식 오류')
        current_queue_values = {'status': 'available', 'jobs': []}
        for current_job_record in current_waiting_jobs:
            if not isinstance(current_job_record, dict) or not isinstance(current_job_record.get('id'), str) or not isinstance(current_job_record.get('service'), str):
                raise ValueError('GPU 대기 작업 형식 오류')
            current_public_job={'id': current_job_record['id'], 'service': current_job_record['service']}
            current_executor_identity=current_job_record.get('executor_identity','unverified')
            if current_executor_identity not in ('verified','unverified'):raise ValueError('대기 실행기 신원 형식 오류')
            current_public_job['executor_identity']=current_executor_identity
            current_ticket_revision=current_job_record.get('ticket_revision')
            if isinstance(current_ticket_revision,str):
                import re
                if re.fullmatch(r'[a-f0-9]{64}',current_ticket_revision):current_public_job['ticket_revision']=current_ticket_revision
            current_source_service=current_job_record.get('source_service')
            if isinstance(current_source_service,str):
                from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
                if current_source_service in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES) or (current_job_record['service']=='review-capture' and current_source_service=='review-capture'):
                    current_public_job['source_service']=current_source_service
                if current_job_record['service']=='review-capture' and current_source_service=='review-capture':
                    from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY
                    from tools.review.domains.hermes_agent.capture_status import find_verified_capture_request_identity
                    from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
                    current_capture_identity=find_verified_capture_request_identity(HermesDelegationStore(),current_job_record['id'],WORKFLOW_ROOT_DIRECTORY)
                    if current_capture_identity is not None:
                        current_public_job.update(current_capture_identity)
            current_queue_values['jobs'].append(current_public_job)
    except (OSError, ValueError, TypeError, KeyError):
        current_queue_values = {'status': 'unavailable', 'jobs': []}

    try:
        current_model_values = {'status': 'available', **inspect_hermes_model_status()}
    except (OSError, ValueError, TypeError, KeyError):
        current_model_values = {'status': 'unavailable'}

    return {'queried_at': datetime.now(timezone.utc).isoformat(),
            'detail': '조회 시각이며 GPU 관측값은 공용 상태 조회의 짧은 캐시를 사용할 수 있습니다. 최근 작업 조회는 로컬 잠금을 만듭니다. 대기 티켓의 실행기 신원은 조회 시점의 부팅 식별값과 PID 시작 식별값으로 확인하며 값이 빠진 티켓은 미확인입니다. GPU idle은 관측된 프로세스가 없다는 뜻이며 실제 사용 가능을 보증하지 않습니다. 여러 GPU의 메모리 값은 합계일 수 있습니다. Kimodo 활성 상태는 기록 기준이며 실제 프로세스 생존을 보증하지 않습니다.',
            'model': current_model_values, 'gpu': current_gpu_values, 'memory_capacity': read_hermes_memory_capacity(current_gpu_values), 'queue': current_queue_values, 'reservations': read_hermes_gpu_reservation_snapshot(),
            'generators': read_hermes_generator_snapshot(), 'recent_hermes_jobs': read_hermes_recent_job_snapshot()}


def read_hermes_model_download_status():
    """기록을 정리하지 않고 모델 다운로드 진행 상태만 조회한다."""
    import os
    import re
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_response_record=execute_management_command('model-downloads','download-observe',{},current_gateway_address)
    if not isinstance(current_response_record,dict) or not isinstance(current_response_record.get('records'),list):raise ValueError('모델 다운로드 상태 형식 오류')
    current_unavailable_count=current_response_record.get('unavailable_count')
    if type(current_unavailable_count) is not int or current_unavailable_count<0:raise ValueError('모델 다운로드 확인 불가 건수 오류')
    current_safe_records=[]
    current_records_value=current_response_record['records']
    for current_record_value in current_records_value[:100]:
        if not isinstance(current_record_value,dict):raise ValueError('모델 다운로드 기록 오류')
        current_model_name=current_record_value.get('model')
        current_status_name=current_record_value.get('status')
        if not isinstance(current_model_name,str) or len(current_model_name)>256 or not re.fullmatch(r'[A-Za-z0-9_.\-/]+',current_model_name) or current_model_name.startswith('/') or '..' in current_model_name.split('/') or current_status_name not in ('running','completed','failed','interrupted'):
            raise ValueError('모델 다운로드 식별 또는 상태 오류')
        current_safe_record={'model':current_model_name,'status':current_status_name}
        for current_field_name in ('bytes','total_bytes'):
            current_field_value=current_record_value.get(current_field_name)
            if current_field_value is not None and (type(current_field_value) is not int or current_field_value<0):raise ValueError('모델 다운로드 크기 오류')
            current_safe_record[current_field_name]=current_field_value
        current_safe_records.append(current_safe_record)
    return {'records':current_safe_records,'unavailable_count':current_unavailable_count,'truncated':len(current_records_value)>100,'note':'관리도구에 기록된 진행 작업과 모델별 최근 종료 기록입니다. 확인 불가 건수에 손상되거나 읽을 수 없는 기록이 포함됩니다. PID 재사용과 외부 다운로드는 확인되지 않으며 완료는 파일 전체 해시나 실행 준비를 보증하지 않습니다.'}


def read_hermes_model_inventory():
    """기존 모델 관리 원본에서 경로 없이 보유량만 읽는다."""
    import os
    import re
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command
    try:
        current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        current_inventory_response = execute_management_command('model-downloads', 'download-inventory', {}, current_gateway_address)
        current_inventory_records = current_inventory_response['models']
        if not isinstance(current_inventory_records, dict) or len(current_inventory_records) > 100:
            raise ValueError('모델 목록 형식 오류')
        current_model_values = []
        for current_service_name, current_model_record in sorted(current_inventory_records.items()):
            if not isinstance(current_service_name, str) or not re.fullmatch(r'[a-z0-9-]{1,80}', current_service_name) or not isinstance(current_model_record, dict):
                raise ValueError('모델 항목 형식 오류')
            current_file_count = current_model_record.get('count')
            current_total_bytes = current_model_record.get('total_bytes')
            current_incomplete_flag = current_model_record.get('incomplete')
            if type(current_file_count) is not int or current_file_count < 0 or type(current_total_bytes) is not int or current_total_bytes < 0 or type(current_incomplete_flag) is not bool:
                raise ValueError('모델 용량 형식 오류')
            current_model_values.append({'service':current_service_name, 'file_count':current_file_count, 'total_bytes':current_total_bytes, 'incomplete':current_incomplete_flag})
        return {'status':'available', 'queried_at':datetime.now(timezone.utc).isoformat(), 'models':current_model_values, 'note':'파일 존재는 모델 준비 완료나 해시 검증을 뜻하지 않습니다.'}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status':'unavailable', 'queried_at':datetime.now(timezone.utc).isoformat(), 'models':[], 'note':'모델 파일 목록을 확인할 수 없습니다.'}


def read_hermes_model_readiness(current_service_name):
    """등록된 모델 관리 서비스의 상태만 호출하고 경로와 원시 오류를 제외한다."""
    import os
    from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command, MANAGEMENT_SERVICE_COMMANDS, inspect_registered_model_operation
    if current_service_name not in {name for _, name in MODEL_PREPARATION_SERVICES}:
        raise ValueError('등록된 모델 관리 서비스가 아닙니다.')
    current_command_names = MANAGEMENT_SERVICE_COMMANDS.get(current_service_name, ())
    current_prepare_allowed = inspect_registered_model_operation(current_service_name, current_command_names, 'prepare') is not None
    current_download_value = None
    try:
        current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        if current_service_name in ('music-heartmula','sfx-dasheng-audiogen'):
            try:
                current_download_record = execute_management_command(current_service_name, 'download-model-status', {}, current_gateway_address)
                if not isinstance(current_download_record,dict) or type(current_download_record.get('ready')) is not bool:
                    raise ValueError('다운로드 상태 형식 오류')
                current_download_state = current_download_record.get('preparation_status')
                if current_download_state not in ('idle','running','completed','failed'):
                    current_download_state = 'unknown'
                current_download_value = {'ready':current_download_record['ready'],'preparation_status':current_download_state}
            except (OSError, ValueError, TypeError, KeyError):
                current_download_value = None
        current_status_record = execute_management_command(current_service_name, 'model-status', {}, current_gateway_address)
        if not isinstance(current_status_record, dict) or type(current_status_record.get('ready')) is not bool:
            raise ValueError('모델 상태 형식 오류')
        current_artifacts_ready = current_status_record.get('artifacts_ready')
        if type(current_artifacts_ready) is not bool:
            current_artifacts_ready = None
        current_generation_ready = current_status_record.get('generation_ready')
        if type(current_generation_ready) is not bool:
            current_generation_ready = None
        current_preparation_state = current_status_record.get('preparation_status')
        if current_preparation_state not in ('idle','running','completed','failed'):
            current_preparation_state = 'unknown'
        current_readiness_note='서비스의 관측 결과이며 실행 권한, GPU 실행과 전체 해시 검증을 보증하지 않습니다. 상태 조회가 로컬 잠금 파일을 만들 수 있습니다.'
        if current_service_name=='flux-image':current_readiness_note+=' FLUX generation_ready는 모델 파일 크기 기준이며 한국어 번역 준비나 GPU 생성 검증을 뜻하지 않습니다.'
        return {'status':'available', 'service':current_service_name, 'queried_at':datetime.now(timezone.utc).isoformat(), 'ready':current_status_record['ready'], 'artifacts_ready':current_artifacts_ready, 'generation_ready':current_generation_ready, 'preparation_status':current_preparation_state, 'download':current_download_value, 'prepare_allowed':current_prepare_allowed, 'note':current_readiness_note}
    except (OSError, ValueError, TypeError, KeyError):
        return {'status':'unavailable','service':current_service_name,'queried_at':datetime.now(timezone.utc).isoformat(),'download':current_download_value,'note':'모델 상태를 확인할 수 없습니다.'}


def read_hermes_content_database_status():
    """콘텐츠 DB의 세대와 원장 반영 상태만 반환하고 내부 오류는 숨긴다."""
    import os
    from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
    from tools.review.domains.map_assets.source_consistency import inspect_hermes_map_sources
    from pathlib import Path
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command
    current_query_time = datetime.now(timezone.utc).isoformat()
    current_asset_root = Path(os.environ.get('SLIME_ASSETS_ROOT', DEFAULT_ASSET_REPOSITORY))
    current_map_sources = inspect_hermes_map_sources(current_asset_root, current_asset_root.parent / 'slime-backend/map-data.lock.yaml')
    from tools.review.domains.hermes_agent.map_pending_observer import inspect_hermes_map_pending_status
    current_map_save = inspect_hermes_map_pending_status()
    current_map_mode = 'database' if os.environ.get('SLIME_CONTENT_STORAGE')=='database' else 'files'
    try:
        current_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        current_status_record = execute_management_command('map-assets', 'database-status', {}, current_gateway_address)
        if not isinstance(current_status_record, dict):
            raise ValueError('상태 형식 오류')
        current_generation_value = current_status_record.get('generation')
        current_snapshot_value = current_status_record.get('snapshotGeneration')
        current_pending_value = current_status_record.get('pending')
        if (type(current_generation_value) is not int or current_generation_value < 0
                or type(current_snapshot_value) is not int or not 0 <= current_snapshot_value <= current_generation_value
                or type(current_pending_value) is not bool
                or current_pending_value != (current_generation_value > current_snapshot_value)):
            raise ValueError('콘텐츠 세대 상태 오류')
        current_latest_record = current_status_record.get('latestSnapshot')
        current_latest_value = None
        if current_latest_record is not None:
            if not isinstance(current_latest_record, dict):
                raise ValueError('원장 반영 상태 오류')
            current_latest_state = current_latest_record.get('state')
            current_latest_generation = current_latest_record.get('generation')
            current_lease_expired = current_latest_record.get('leaseExpired')
            if (current_latest_state not in ('pending','running','completed','failed')
                    or type(current_latest_generation) is not int or current_latest_generation < 0
                    or type(current_lease_expired) is not bool):
                raise ValueError('원장 반영 상태 오류')
            current_latest_value = {'state':current_latest_state, 'generation':current_latest_generation, 'lease_expired':current_lease_expired}
        return {'status':'available', 'queried_at':current_query_time, 'generation':current_generation_value,
                'ledger_generation':current_snapshot_value, 'pending':current_pending_value, 'latest':current_latest_value, 'map_sources':current_map_sources, 'map_save':current_map_save, 'local_map_mode':current_map_mode,
                'note':'콘텐츠 DB 응답의 snapshotGeneration은 원장 반영 계약 이름입니다. 파일 스냅샷 보관을 뜻하지 않습니다. 맵 원본 비교는 별도 조회 시점 기준이며 DB 또는 실행 중인 백엔드 반영을 확인하지 않습니다.'}
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as current_status_error:
        current_reason_code = 'service_origin' if 'SLIME_CONTENT_SERVICE_ORIGIN에 콘텐츠 API origin을 지정하세요.' in str(current_status_error) else 'unknown'
        current_status_note = ('게이트웨이의 콘텐츠 서비스 주소 설정을 확인하세요.' if current_reason_code == 'service_origin' else '콘텐츠 DB 상태를 확인할 수 없습니다. 서비스 연결과 인증을 확인하세요.')
        return {'status':'unavailable', 'queried_at':current_query_time, 'map_sources':current_map_sources, 'map_save':current_map_save, 'local_map_mode':current_map_mode,
                'failure_reason':current_reason_code, 'note':current_status_note}


def read_hermes_kimodo_build_status():
    """GPU 초기화 없이 기존 빌드 기록을 읽고 캐시 유효성을 미확인으로 표시한다."""
    import os
    import re
    from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
    from tools.review.common.management_gateway import execute_management_command
    try:
        current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
        current_status_record=execute_management_command('kimodo','migraphx-build-observe',{},current_gateway_address)
        if not isinstance(current_status_record,dict) or current_status_record.get('status') not in ('idle','queued','running','completed','failed','cancelled') or current_status_record.get('cache_status') != 'unverified':
            raise ValueError('빌드 상태 오류')
        current_job_identifier=current_status_record.get('id')
        if current_job_identifier is not None and (not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier)):
            raise ValueError('빌드 작업 ID 오류')
        if (current_status_record['status']=='idle') != (current_job_identifier is None):
            raise ValueError('빌드 기록과 작업 ID 불일치')
        current_previous_status=current_status_record.get('status')
        if current_previous_status not in (None,'idle','queued','running','completed','failed','cancelled'):
            current_previous_status='unknown'
        current_result_record={'status':current_status_record['status'],'job_id':current_job_identifier,'build_status':current_previous_status,'queried_at':datetime.now(timezone.utc).isoformat(),'cache_status':'unverified','note':'빌드 기록만 조회합니다. 캐시 유효성과 실제 작업 생존 여부는 별도 확인해야 합니다.'}
        current_failure_code=current_status_record.get('failure_code')
        current_failure_messages={'host_memory_guard':'시스템 메모리 보호로 빌드가 중단됐습니다. 메모리 여유를 확인하세요.','host_memory_monitor_failed':'시스템 메모리를 감시할 수 없어 빌드가 중단됐습니다. 모델 관리에서 확인하세요.'}
        if current_status_record['status']=='failed' and current_failure_code in current_failure_messages:
            current_result_record.update(failure_code=current_failure_code,failure_reason=current_failure_messages[current_failure_code])
        return current_result_record
    except (OSError,ValueError,TypeError,KeyError):
        return {'status':'unavailable','job_id':None,'build_status':None,'queried_at':datetime.now(timezone.utc).isoformat(),'note':'빌드 상태 확인 실패. 모델 관리에서 확인하세요.'}
