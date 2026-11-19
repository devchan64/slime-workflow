"""GPU 우선 실행 접수를 중복 방지하고 결과를 보존한다."""
import json
import re
from pathlib import Path

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore

PRIORITY_RECEIPT_ROOT=Path(__file__).resolve().parents[4]/'.local/hermes-agent/priority-receipts'


def inspect_hermes_priority_receipt(current_record_value,current_request_identifier):
    """접수 기록이 같은 대상과 확인값을 갖는지 검증한다."""
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_SERVICE_PATTERN, validate_service_job_identifier
    if not isinstance(current_record_value,dict) or set(current_record_value)!={'version','id','service','job_id','ticket_revision','state'} or type(current_record_value.get('version')) is not int or current_record_value.get('version')!=1 or current_record_value.get('id')!=current_request_identifier or current_record_value.get('state') not in ('dispatching','completed'):
        raise ValueError('우선 실행 접수 기록 형식 오류')
    if not isinstance(current_record_value.get('ticket_revision'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_record_value['ticket_revision']):
        raise ValueError('우선 실행 티켓 확인값 오류')
    current_service_name=current_record_value.get('service')
    if not isinstance(current_service_name,str) or not HERMES_DELEGATION_SERVICE_PATTERN.fullmatch(current_service_name) or len(current_service_name)>80 or not validate_service_job_identifier(current_service_name,current_record_value.get('job_id')):
        raise ValueError('우선 실행 대상 기록 오류')
    return {'request_id':current_request_identifier,'service':current_record_value['service'],'job_id':current_record_value['job_id'],'ticket_revision':current_record_value['ticket_revision'],'state':'unknown' if current_record_value['state']=='dispatching' else 'completed'}


def read_hermes_priority_receipt(current_request_identifier):
    current_storage=HermesDelegationStore(PRIORITY_RECEIPT_ROOT)
    with current_storage.hold_delegation_storage_lock():
        current_path=current_storage.resolve_delegation_record_path(current_request_identifier)
        if not current_path.exists():return {'state':'not_found'}
        return inspect_hermes_priority_receipt(json.loads(current_path.read_text(encoding='utf-8')),current_request_identifier)


def submit_hermes_priority_once(current_request_identifier,current_service_name,current_job_identifier,current_ticket_revision):
    """동일 요청은 기록만 반환하고 결과 불명 시 우선순위를 다시 변경하지 않는다."""
    from tools.review.domains.hermes_agent.priority_observer import validate_hermes_priority_target
    from tools.review.common.gpu_job_queue import prioritize_waiting_generation
    validate_hermes_priority_target(current_service_name,current_job_identifier)
    if not isinstance(current_ticket_revision,str) or not re.fullmatch(r'[a-f0-9]{64}',current_ticket_revision):
        raise ValueError('검토한 대기 티켓 확인값이 필요합니다.')
    current_storage=HermesDelegationStore(PRIORITY_RECEIPT_ROOT)
    with current_storage.hold_delegation_storage_lock():
        current_path=current_storage.resolve_delegation_record_path(current_request_identifier)
        if current_path.exists():
            current_receipt=inspect_hermes_priority_receipt(json.loads(current_path.read_text(encoding='utf-8')),current_request_identifier)
            if (current_receipt['service'],current_receipt['job_id'],current_receipt['ticket_revision'])!=(current_service_name,current_job_identifier,current_ticket_revision):
                raise ValueError('같은 접수 ID를 다른 대기 작업이나 티켓에 사용할 수 없습니다.')
            return {**current_receipt,'duplicate':True}
        for current_existing_path in current_storage.delegation_storage_root.glob('*.json'):
            current_existing_identifier=current_existing_path.stem
            current_storage.resolve_delegation_record_path(current_existing_identifier)
            if not current_existing_path.is_file():raise ValueError('우선 실행 접수 목록을 확인할 수 없습니다.')
            current_existing_receipt=inspect_hermes_priority_receipt(json.loads(current_existing_path.read_text(encoding='utf-8')),current_existing_identifier)
            if (current_existing_receipt['service'],current_existing_receipt['job_id'],current_existing_receipt['ticket_revision'])==(current_service_name,current_job_identifier,current_ticket_revision):
                raise ValueError('같은 대기 티켓의 기존 우선 실행 접수가 있습니다. 접수와 대기열을 확인하세요.')
        current_record={'version':1,'id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'ticket_revision':current_ticket_revision,'state':'dispatching'}
        write_record_atomically(current_path,current_record)
        current_response=prioritize_waiting_generation(current_job_identifier,current_service_name,current_ticket_revision)
        if not isinstance(current_response,dict) or current_response.get('id')!=current_job_identifier or current_response.get('status')!='queued' or type(current_response.get('queue_position')) is not int or current_response.get('queue_position')!=1:
            raise ValueError('우선 실행 결과를 확인할 수 없습니다. 자동 재요청하지 마세요.')
        if json.loads(current_path.read_text(encoding='utf-8'))!=current_record:
            raise ValueError('우선 실행 접수 기록이 변경됐습니다. 접수와 대기열을 확인하세요.')
        current_record['state']='completed'
        write_record_atomically(current_path,current_record)
        return {**inspect_hermes_priority_receipt(current_record,current_request_identifier),'duplicate':False}
