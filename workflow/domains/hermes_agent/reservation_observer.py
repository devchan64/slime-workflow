"""다른 생성기의 GPU 예약을 식별해 비파괴적으로 관측한다."""
import hashlib
import json
import os
import re
import uuid
from pathlib import Path
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record


def find_generator_reservation_record(current_active_root,current_service_name,current_job_identifier):
    """잠금 안에서 유일한 예약 및 원 서비스 경로를 확인한다."""
    from workflow.common import gpu_job_queue as current_queue_module
    from workflow.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
    current_supported_services=set(SOURCE_HISTORY_GENERATOR_SERVICES)|set(SOURCE_HISTORY_AUDIO_SERVICES)
    current_supported_services.discard('writer-agent')
    if not isinstance(current_service_name,str) or current_service_name not in current_supported_services:
        raise ValueError('지원하는 생성기 서비스를 선택하세요.')
    if not isinstance(current_job_identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job_identifier):
        raise ValueError('작업 ID 형식 오류')
    current_matching_records=[]
    for current_record_path in current_active_root.glob('*.json'):
        if current_record_path.is_symlink() or not current_record_path.is_file():raise ValueError('GPU 예약 기록을 확인할 수 없습니다.')
        try:current_record_value=read_bounded_delegation_record(current_record_path)
        except (OSError,ValueError,TypeError) as current_read_error:raise ValueError('GPU 예약 기록을 확인할 수 없습니다.') from current_read_error
        if not isinstance(current_record_value,dict) or not isinstance(current_record_value.get('path'),str) or not isinstance(current_record_value.get('service'),str):
            raise ValueError('GPU 예약 식별 정보를 확인할 수 없습니다.')
        if Path(current_record_value['path']).name==current_job_identifier:current_matching_records.append((current_record_path,current_record_value))
    if len(current_matching_records)!=1:raise ValueError('작업 ID가 유일한 GPU 예약을 확인할 수 없습니다.')
    current_record_path,current_record_value=current_matching_records[0]
    current_queue_service=current_record_value['service']
    if current_queue_service in ('image','flux-image'):
        current_source_service=current_queue_module.identify_gpu_queue_source(current_record_value['path'],current_queue_service)
    else:current_source_service=current_queue_module.identify_dedicated_gpu_reservation_source(current_record_value['path'],current_queue_service)
    if current_source_service!=current_service_name:raise ValueError('예약의 원 서비스가 일치하지 않거나 확인되지 않습니다.')
    current_memory_value=current_record_value.get('required_memory_mib')
    if type(current_memory_value) is not int or current_memory_value<0:raise ValueError('GPU 예약 메모리 오류')
    return current_record_path,current_record_value,current_memory_value


def is_generator_process_group_absent(current_record_value):
    """현재 부팅의 완전한 신원이 있고 PID와 그룹이 모두 없을 때만 부재로 판정한다."""
    current_group_id=current_record_value.get('worker_pgid')
    current_start_token=current_record_value.get('worker_start_token')
    current_worker_token=current_record_value.get('worker_process_token')
    current_boot_id=current_record_value.get('boot_id')
    if (type(current_group_id) is not int or not 1<current_group_id<=2147483647
            or not isinstance(current_start_token,str) or not current_start_token.isascii() or not current_start_token.isdigit()
            or not isinstance(current_worker_token,str) or not re.fullmatch(r'[a-f0-9]{32}',current_worker_token)
            or not isinstance(current_boot_id,str)):
        return False
    try:
        if str(uuid.UUID(current_boot_id))!=current_boot_id or Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=current_boot_id:
            return False
        try:
            os.kill(current_group_id,0)
        except ProcessLookupError:
            pass
        else:
            return False
        try:
            os.killpg(current_group_id,0)
        except ProcessLookupError:
            return True
    except (OSError,ValueError,AttributeError):
        return False
    return False


def inspect_generator_reservation_record(current_record_path,current_record_value,current_memory_value,current_service_name,current_job_identifier):
    """잠금 안에서 신원과 검토 해시를 확인하고 열린 pidfd를 반환한다."""
    from workflow.common import gpu_job_queue as current_queue_module
    current_executor_pid=current_record_value.get('pid')
    current_executor_token=current_record_value.get('pid_start_token')
    current_executor_state='unverified'
    if type(current_executor_pid) is int and 1<current_executor_pid<=2147483647 and isinstance(current_executor_token,str) and current_executor_token.isascii() and current_executor_token.isdigit():
        try:
            os.kill(current_executor_pid,0)
        except ProcessLookupError:
            current_executor_state='not_observed'
        except OSError:
            pass
        else:
            try:
                if current_queue_module.inspect_gpu_ticket_executor_identity(current_record_value)=='verified':current_executor_state='observed'
            except ValueError:
                pass
    current_worker_descriptor=current_queue_module.open_verified_hermes_process_group(current_record_value)
    current_worker_state='verified_running' if current_worker_descriptor is not None else ('group_absent' if is_generator_process_group_absent(current_record_value) else 'unverified')
    current_review_ready=(current_executor_state=='not_observed' and current_worker_state in ('verified_running','group_absent') and current_record_value.get('recovery_in_progress') is None)
    try:
        current_review_digest=None
        if current_review_ready:
            current_review_bytes=json.dumps({'filename':current_record_path.name,'service':current_service_name,'job_id':current_job_identifier,'record':current_record_value},sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            current_review_digest=hashlib.sha256(current_review_bytes).hexdigest()
        current_result_record={'service':current_service_name,'job_id':current_job_identifier,'required_memory_mib':current_memory_value,'executor':current_executor_state,'worker_leader':current_worker_state,'review_ready':current_review_ready,'review_sha256':current_review_digest,'note':'비파괴 관측입니다. 확인값은 재검토 기준이며 정리 권한이나 실행 명령이 아닙니다. 실행기 미관측이나 리더 확인은 그룹 전체·별도 그룹의 종료를 보증하지 않습니다. 예약 정리나 프로세스 종료는 수행하지 않습니다.'}
        return current_result_record,current_worker_descriptor
    except BaseException:
        if current_worker_descriptor is not None:os.close(current_worker_descriptor)
        raise


def inspect_generator_reservation_identity(current_service_name,current_job_identifier):
    """예약과 리더만 확인하며 프로세스 종료·예약 해제는 하지 않는다."""
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    with hold_writer_reservation_queue_lock() as current_active_root:
        current_record_path,current_record_value,current_memory_value=find_generator_reservation_record(current_active_root,current_service_name,current_job_identifier)
        current_result_record,current_worker_descriptor=inspect_generator_reservation_record(current_record_path,current_record_value,current_memory_value,current_service_name,current_job_identifier)
        if current_worker_descriptor is not None:os.close(current_worker_descriptor)
        return current_result_record
