"""Hermes의 작가 AI 작업 위임과 검토 결과 조회."""
import os
from pathlib import PurePosixPath
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason


def call_hermes_writer_service(current_command_name,current_payload_record):
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('writer-agent',current_command_name,current_payload_record,current_gateway_address)


def validate_hermes_writer_request(current_request_record):
    from generators.writer_agent.jobs import validate_job_request
    validate_job_request(current_request_record)
    current_state_value=call_hermes_writer_service('writer-state',{})
    if not isinstance(current_state_value,dict) or current_state_value.get('configured') is not True or current_state_value.get('ready') is not True:
        raise ValueError('작가 AI 문서 설정과 모델 준비 상태를 확인하세요.')
    if current_state_value.get('active_job'):
        raise ValueError('작가 AI 작업이 이미 실행 또는 대기 중입니다.')
    if current_request_record['mode']!='learn' and current_state_value.get('trained') is not True:
        raise ValueError('작가 AI 문서 색인을 먼저 갱신하세요.')
    if current_request_record['mode']!='learn':
        current_index_value=call_hermes_writer_service('writer-index-status',{})
        if not isinstance(current_index_value,dict) or current_index_value.get('status')!='fresh':
            raise ValueError('작가 AI 문서 색인이 오래됐거나 확인할 수 없습니다. 색인을 갱신한 뒤 다시 확인하세요.')


def submit_hermes_writer_request(current_request_identifier,current_request_record):
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,'writer-agent',current_request_record,
        lambda current_request_value:call_hermes_writer_service('writer-submit',current_request_value),validate_hermes_writer_request)


def cancel_hermes_writer_request(current_request_identifier,current_job_identifier):
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,'writer-agent')
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('작가 접수와 확인한 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_writer_service('writer-cancel',{'id':current_job_identifier})
    if not isinstance(current_cancel_value,dict) or current_cancel_value.get('id')!=current_job_identifier or current_cancel_value.get('cancel_requested') is not True:
        raise ValueError('작가 작업 중지 접수 여부를 확인할 수 없습니다.')
    return {'job_id':current_job_identifier,'status':current_cancel_value.get('status','unknown'),'cancel_requested':True}


def read_hermes_writer_status(current_request_identifier):
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,'writer-agent')
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    current_detail_value=call_hermes_writer_service('writer-detail',{'id':current_receipt_value['job_id']})
    if not isinstance(current_detail_value,dict) or current_detail_value.get('id')!=current_receipt_value['job_id'] or not isinstance(current_detail_value.get('status'),dict):
        raise ValueError('작가 AI 상태 응답 형식 오류')
    current_status_value=current_detail_value['status']
    current_stage_value=current_status_value.get('stage')
    if current_stage_value not in ('queued','preparing','indexing','searching','reasoning','review','completed','applied','failed','interrupted'):
        current_stage_value='unknown'
    current_summary_value=current_status_value.get('summary')
    if not isinstance(current_summary_value,str) or len(current_summary_value)>1000:
        current_summary_value=''
    current_output_value={'stage':current_stage_value,'summary':current_summary_value,'changes':[],'warnings':[], 'proposal_hash':None,'truncated':False}
    current_error_value=current_status_value.get('error')
    current_guard_reason=observe_hermes_failure_reason(current_stage_value,current_error_value)
    if current_guard_reason:
        current_output_value.update(current_guard_reason)
    elif current_stage_value=='failed' and isinstance(current_error_value,str) and '색인이 오래되었습니다' in current_error_value:
        current_output_value['failure_reason']='문서 색인이 오래되었습니다. 작가 AI 문서 색인을 갱신하세요.'
    elif current_stage_value=='failed' and isinstance(current_error_value,str) and '검토 중 원문이 변경되어' in current_error_value:
        current_output_value['failure_reason']='검토 중 원문이 변경돼 제안이 중단됐습니다. 문서 상태와 색인을 확인하세요.'
    elif current_stage_value in ('failed','interrupted'):
        current_output_value['failure_reason']='작업이 종료되었습니다. 자세한 원인은 작가 AI 화면에서 확인하세요.'
    current_proposal_value=current_detail_value.get('proposal')
    if current_proposal_value is not None:
        if not isinstance(current_proposal_value,dict) or not isinstance(current_proposal_value.get('changes',[]),list) or not isinstance(current_proposal_value.get('warnings',[]),list):
            raise ValueError('작가 AI 제안 형식 오류')
        current_change_values=current_proposal_value.get('changes',[])
        current_output_value['truncated']=len(current_change_values)>20
        current_total_bytes=0
        for current_change_value in current_change_values[:20]:
            if not isinstance(current_change_value,dict) or not isinstance(current_change_value.get('path'),str) or not isinstance(current_change_value.get('diff'),str):
                raise ValueError('작가 AI 변경 형식 오류')
            current_path_value=PurePosixPath(current_change_value['path'])
            if current_path_value.is_absolute() or '..' in current_path_value.parts or len(current_path_value.as_posix())>512:
                raise ValueError('작가 AI 변경 경로 오류')
            current_diff_text=current_change_value['diff']
            current_remaining_bytes=max(0,100000-current_total_bytes)
            current_diff_bytes=current_diff_text.encode('utf-8')
            if len(current_diff_bytes)>current_remaining_bytes:
                current_diff_text=current_diff_bytes[:current_remaining_bytes].decode('utf-8',errors='ignore')
                current_output_value['truncated']=True
            current_total_bytes+=len(current_diff_text.encode('utf-8'))
            current_output_value['changes'].append({'path':current_path_value.as_posix(),'diff':current_diff_text})
        current_output_value['warnings']=[item[:1000] for item in current_proposal_value.get('warnings',[])[:30] if isinstance(item,str)]
    import re
    current_hash_value=current_status_value.get('proposal_hash')
    if isinstance(current_hash_value,str) and re.fullmatch(r'[a-f0-9]{64}',current_hash_value):
        current_output_value['proposal_hash']=current_hash_value
    current_output_value['note']='작가 제안은 원본에 적용되지 않았습니다. 전체 diff와 근거는 작가 AI 화면에서 확인하세요.' if current_stage_value=='review' else '상태는 기존 작가 AI 응답입니다.'
    return {'receipt':current_receipt_value,'job':current_output_value}


def inspect_writer_apply_receipt(current_record_value,current_apply_identifier):
    import re
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN, validate_service_job_identifier
    if (not isinstance(current_record_value,dict) or current_record_value.get('version')!=6 or current_record_value.get('id')!=current_apply_identifier
            or not isinstance(current_record_value.get('writer_request_id'),str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_record_value['writer_request_id'])
            or not validate_service_job_identifier('writer-agent',current_record_value.get('job_id'))
            or not isinstance(current_record_value.get('proposal_hash'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_record_value['proposal_hash'])):
        raise ValueError('작가 적용 접수 기록 오류')
    current_state_value=current_record_value.get('state')
    if current_state_value not in ('dispatching','completed'):
        raise ValueError('작가 적용 접수 상태 오류')
    return {'request_id':current_apply_identifier,'writer_request_id':current_record_value['writer_request_id'],'job_id':current_record_value['job_id'],
            'proposal_hash':current_record_value['proposal_hash'],'state':'unknown' if current_state_value=='dispatching' else 'completed'}


def apply_hermes_writer_proposal_once(current_apply_identifier,current_writer_identifier,current_job_identifier,current_proposal_hash):
    """확인된 전체 diff의 해시만 적용하며 결과 유실 시 재적용하지 않는다."""
    import re
    from tools.review.common.generation_records import write_record_atomically
    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_ID_PATTERN, validate_service_job_identifier
    if not isinstance(current_writer_identifier,str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_writer_identifier):
        raise ValueError('작가 위임 접수 ID 형식 오류')
    if not validate_service_job_identifier('writer-agent',current_job_identifier) or not isinstance(current_proposal_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_proposal_hash):
        raise ValueError('작가 작업 ID 또는 제안 해시 형식 오류')
    current_storage_value=HermesDelegationStore()
    def inspect_existing_apply(current_record_path):
        import json
        current_record_value=json.loads(current_record_path.read_text(encoding='utf-8'))
        current_receipt_value=inspect_writer_apply_receipt(current_record_value,current_apply_identifier)
        if (current_receipt_value['writer_request_id'],current_receipt_value['job_id'],current_receipt_value['proposal_hash'])!=(current_writer_identifier,current_job_identifier,current_proposal_hash):
            raise ValueError('같은 적용 접수 ID를 다른 제안에 사용할 수 없습니다.')
        return {**current_receipt_value,'duplicate':True}
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if current_record_path.exists():
            return inspect_existing_apply(current_record_path)
    current_status_value=read_hermes_writer_status(current_writer_identifier)
    current_receipt_value=current_status_value.get('receipt',{})
    current_job_value=current_status_value.get('job',{})
    if (current_receipt_value.get('job_id')!=current_job_identifier or current_job_value.get('stage')!='review'
            or current_job_value.get('proposal_hash')!=current_proposal_hash or current_job_value.get('truncated') is not False
            or not current_job_value.get('changes')):
        raise ValueError('작업·제안이 바뀌었거나 전체 변경을 확인할 수 없습니다.')
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if current_record_path.exists():
            return inspect_existing_apply(current_record_path)
        current_record_value={'version':6,'id':current_apply_identifier,'writer_request_id':current_writer_identifier,'job_id':current_job_identifier,'proposal_hash':current_proposal_hash,'state':'dispatching'}
        write_record_atomically(current_record_path,current_record_value)
        current_result_value=call_hermes_writer_service('writer-apply',{'id':current_job_identifier,'proposal_hash':current_proposal_hash})
        if not isinstance(current_result_value,dict) or current_result_value.get('status')!='applied':
            raise ValueError('작가 적용 결과 확인 필요. 자동 재적용하지 않습니다.')
        current_record_value['state']='completed'
        write_record_atomically(current_record_path,current_record_value)
        return {**inspect_writer_apply_receipt(current_record_value,current_apply_identifier),'duplicate':False}


def read_writer_apply_receipt(current_apply_identifier):
    import json
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if not current_record_path.exists():
            return {'state':'not_found'}
        return inspect_writer_apply_receipt(json.loads(current_record_path.read_text(encoding='utf-8')),current_apply_identifier)


def list_writer_apply_receipts():
    import json
    from datetime import datetime, timezone
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_records_list=[]
        for current_record_path in current_storage_value.delegation_storage_root.glob('*.json'):
            if current_record_path.is_symlink() or not current_record_path.is_file():
                continue
            try:
                current_apply_identifier=current_record_path.stem
                current_storage_value.resolve_delegation_record_path(current_apply_identifier)
                current_record_value=json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_record_value,dict) or current_record_value.get('version')!=6:
                    continue
                current_receipt_value=inspect_writer_apply_receipt(current_record_value,current_apply_identifier)
                current_updated_time=current_record_path.stat().st_mtime
                current_records_list.append({**current_receipt_value,'updated_at':datetime.fromtimestamp(current_updated_time,timezone.utc).isoformat(),'_sort_time':current_updated_time})
            except (OSError,ValueError,TypeError,KeyError):
                continue
        current_records_list.sort(key=lambda current_record_value:(current_record_value['_sort_time'],current_record_value['request_id']),reverse=True)
        for current_record_value in current_records_list:
            current_record_value.pop('_sort_time')
        return {'records':current_records_list[:100],'truncated':len(current_records_list)>100,'note':'손상된 기록은 제외됩니다. 결과 불명일 때 원본과 작가 AI 상태를 확인하세요.'}
