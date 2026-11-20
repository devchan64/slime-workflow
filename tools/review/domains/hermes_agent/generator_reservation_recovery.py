"""생성기 GPU 예약의 조건부 정리와 중복 방지 접수."""
import os
import re

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, check_delegation_record_exists, read_bounded_delegation_record
from tools.review.domains.hermes_agent.reservation_observer import find_generator_reservation_record, inspect_generator_reservation_record
from tools.review.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock, is_writer_executor_definitely_absent


def inspect_generator_recovery_receipt(current_receipt_record,current_request_identifier):
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
    current_supported_services=(set(SOURCE_HISTORY_GENERATOR_SERVICES)|set(SOURCE_HISTORY_AUDIO_SERVICES)) - {'writer-agent'}
    if (not isinstance(current_receipt_record,dict) or set(current_receipt_record)!={'version','id','service','job_id','review_sha256','state'}
            or type(current_receipt_record.get('version')) is not int or current_receipt_record.get('version')!=13
            or current_receipt_record.get('id')!=current_request_identifier or current_receipt_record.get('state') not in ('dispatching','completed')):
        raise ValueError('생성기 예약 정리 접수 기록 오류')
    if (not isinstance(current_receipt_record.get('service'),str) or current_receipt_record['service'] not in current_supported_services
            or not isinstance(current_receipt_record.get('job_id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_receipt_record['job_id'])
            or not isinstance(current_receipt_record.get('review_sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_receipt_record['review_sha256'])):
        raise ValueError('생성기 예약 정리 접수 기록 오류')
    return {'request_id':current_request_identifier,'service':current_receipt_record['service'],'job_id':current_receipt_record['job_id'],'state':'unknown' if current_receipt_record['state']=='dispatching' else 'completed'}


def recover_generator_reservation_once(current_request_identifier,current_service_name,current_job_identifier,current_review_digest,current_outside_processes_checked):
    """명시적 확인과 재검증 후 일치하는 작업자 그룹만 정리한다."""
    from tools.review.common import gpu_job_queue as current_queue_module
    if current_outside_processes_checked is not True:raise ValueError('별도 그룹 GPU 프로세스를 확인해야 합니다.')
    if not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('예약 검토 해시 오류')
    current_store_value=HermesDelegationStore()
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_path=current_store_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_record=read_bounded_delegation_record(current_receipt_path)
            current_result_record=inspect_generator_recovery_receipt(current_receipt_record,current_request_identifier)
            if (current_receipt_record.get('service'),current_receipt_record.get('job_id'),current_receipt_record.get('review_sha256'))!=(current_service_name,current_job_identifier,current_review_digest):raise ValueError('같은 접수 ID를 다른 예약에 사용할 수 없습니다.')
            return {**current_result_record,'duplicate':True}
        with hold_writer_reservation_queue_lock() as current_active_root:
            current_record_path,current_record_value,current_memory_value=find_generator_reservation_record(current_active_root,current_service_name,current_job_identifier)
            current_preview_record,current_worker_descriptor=inspect_generator_reservation_record(current_record_path,current_record_value,current_memory_value,current_service_name,current_job_identifier)
            if not current_preview_record['review_ready'] or current_preview_record['review_sha256']!=current_review_digest:
                if current_worker_descriptor is not None:os.close(current_worker_descriptor)
                raise ValueError('예약 상태가 바뀌었거나 신원을 확인할 수 없습니다. 다시 검토하세요.')
            try:
                current_receipt_record={'version':13,'id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'review_sha256':current_review_digest,'state':'dispatching'}
                write_record_atomically(current_receipt_path,current_receipt_record)
                current_marked_record={**current_record_value,'cleanup_unverified':True,'recovery_in_progress':current_request_identifier}
                write_record_atomically(current_record_path,current_marked_record)
            except BaseException:
                os.close(current_worker_descriptor)
                raise
    try:
        current_queue_module.stop_hermes_worker_process_group(current_record_value['worker_pgid'],current_worker_descriptor)
    finally:
        os.close(current_worker_descriptor)
    with hold_writer_reservation_queue_lock() as current_active_root:
        current_current_path,current_current_record,_=find_generator_reservation_record(current_active_root,current_service_name,current_job_identifier)
        if current_current_path!=current_record_path or current_current_record!=current_marked_record:raise ValueError('정리 중 예약이 변경됐습니다. 결과를 확인하세요.')
        if not is_writer_executor_definitely_absent(current_record_value['pid']):raise ValueError('실행기 부재를 확인할 수 없습니다. 예약을 유지합니다.')
        current_current_path.unlink()
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_record=read_bounded_delegation_record(current_receipt_path)
        current_expected_record={'version':13,'id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'review_sha256':current_review_digest,'state':'dispatching'}
        if current_receipt_record!=current_expected_record:raise ValueError('정리 접수 기록이 변경됐습니다. 결과를 확인하세요.')
        current_receipt_record['state']='completed'
        write_record_atomically(current_receipt_path,current_receipt_record)
        return {**inspect_generator_recovery_receipt(current_receipt_record,current_request_identifier),'duplicate':False}


def read_generator_recovery_receipt(current_request_identifier):
    current_store_value=HermesDelegationStore()
    with current_store_value.hold_delegation_storage_lock():
        current_receipt_path=current_store_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'state':'not_found'}
        return inspect_generator_recovery_receipt(read_bounded_delegation_record(current_receipt_path),current_request_identifier)
