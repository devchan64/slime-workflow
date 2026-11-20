"""서비스별 재개 접수 기록의 공용 중복 방지와 응답 유실 처리."""
from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, list_delegation_record_paths, check_delegation_record_exists, read_bounded_delegation_record


def inspect_resume_receipt_record(current_record_value,current_request_identifier,current_validate_target):
    if not isinstance(current_record_value,dict) or set(current_record_value)!={'version','id','service','job_id','fingerprint','state'} or type(current_record_value.get('version')) is not int or current_record_value['version']!=1 or current_record_value.get('id')!=current_request_identifier or current_record_value.get('state') not in ('dispatching','accepted'):
        raise ValueError('재개 접수 기록 오류')
    current_validate_target(current_record_value.get('service'),current_record_value.get('job_id'),current_record_value.get('fingerprint'))
    if not isinstance(current_record_value.get('fingerprint'),str):raise ValueError('재개 확인값 오류')
    return {'request_id':current_request_identifier,'service':current_record_value['service'],'job_id':current_record_value['job_id'],'expected_resume_fingerprint':current_record_value['fingerprint'],'state':'unknown' if current_record_value['state']=='dispatching' else 'accepted'}


def read_resume_receipt_record(current_receipt_root,current_request_identifier,current_validate_target):
    current_receipt_store=HermesDelegationStore(current_receipt_root)
    with current_receipt_store.hold_delegation_storage_lock():
        current_receipt_path=current_receipt_store.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_receipt_path):return {'state':'not_found','request_id':current_request_identifier}
        return inspect_resume_receipt_record(read_bounded_delegation_record(current_receipt_path),current_request_identifier,current_validate_target)


def submit_resume_receipt_once(current_receipt_root,current_request_identifier,current_service_name,current_job_identifier,current_fingerprint_value,current_validate_target,current_submit_callback,*,current_preflight_callback=None):
    current_validate_target(current_service_name,current_job_identifier,current_fingerprint_value)
    if not isinstance(current_fingerprint_value,str):raise ValueError('재개 확인값이 필요합니다.')
    current_receipt_store=HermesDelegationStore(current_receipt_root)
    with current_receipt_store.hold_delegation_storage_lock():
        current_receipt_path=current_receipt_store.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_receipt_path):
            current_receipt_value=inspect_resume_receipt_record(read_bounded_delegation_record(current_receipt_path),current_request_identifier,current_validate_target)
            if (current_receipt_value['service'],current_receipt_value['job_id'],current_receipt_value['expected_resume_fingerprint'])!=(current_service_name,current_job_identifier,current_fingerprint_value):
                raise ValueError('같은 접수 ID를 다른 재개 대상에 사용할 수 없습니다.')
            return {**current_receipt_value,'duplicate':True}
        for current_existing_path in list_delegation_record_paths(current_receipt_store.delegation_storage_root):
            if current_existing_path.is_symlink() or not current_existing_path.is_file():
                raise ValueError('재개 접수 목록을 확인할 수 없습니다.')
            current_existing_identifier=current_existing_path.stem
            current_receipt_store.resolve_delegation_record_path(current_existing_identifier)
            current_existing_value=inspect_resume_receipt_record(read_bounded_delegation_record(current_existing_path),current_existing_identifier,current_validate_target)
            if (current_existing_value['service'],current_existing_value['job_id'])==(current_service_name,current_job_identifier) and current_existing_value['state']=='unknown':
                raise ValueError(f'같은 작업에 결과가 확인되지 않은 기존 접수가 있습니다 (접수 ID: {current_existing_identifier}). 해당 접수와 원 서비스 상태를 확인하세요. 자동 재접수하지 마세요.')
            if (current_existing_value['service'],current_existing_value['job_id'],current_existing_value['expected_resume_fingerprint'])==(current_service_name,current_job_identifier,current_fingerprint_value):
                raise ValueError(f'같은 재개 검토의 기존 접수가 있습니다 (접수 ID: {current_existing_identifier}). 해당 접수와 원 서비스 상태를 확인하세요.')
        if current_preflight_callback is not None:
            current_preflight_result=current_preflight_callback(current_service_name,current_job_identifier,current_fingerprint_value)
            if current_preflight_result is not None:
                if current_preflight_result not in ('download_running','other_preparation','unavailable','fingerprint_changed'):
                    raise ValueError('재개 사전 확인 결과 오류')
                return {'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value,'state':'blocked','reason':current_preflight_result,'duplicate':False}
        current_record_value={'version':1,'id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'fingerprint':current_fingerprint_value,'state':'dispatching'}
        write_record_atomically(current_receipt_path,current_record_value)
        current_response_value=current_submit_callback(current_service_name,current_job_identifier,current_fingerprint_value)
        if not isinstance(current_response_value,dict) or current_response_value.get('id')!=current_job_identifier or current_response_value.get('status')!='queued':
            raise ValueError('재개 접수 확인 불가. 원 서비스 상태를 확인하고 자동 재요청하지 마세요.')
        if read_bounded_delegation_record(current_receipt_path)!=current_record_value:
            raise ValueError('접수 기록이 변경됐습니다. 원 서비스 상태를 확인하세요.')
        current_record_value['state']='accepted'
        write_record_atomically(current_receipt_path,current_record_value)
        return {**inspect_resume_receipt_record(current_record_value,current_request_identifier,current_validate_target),'duplicate':False}
