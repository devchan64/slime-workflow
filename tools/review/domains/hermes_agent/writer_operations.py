"""Hermes의 작가 AI 작업 위임과 검토 결과 조회."""
import os
from pathlib import PurePosixPath
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, list_delegation_record_paths, check_delegation_record_exists, read_bounded_delegation_record
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_failure_reason


def call_hermes_writer_service(current_command_name,current_payload_record):
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('writer-agent',current_command_name,current_payload_record,current_gateway_address)


def read_hermes_writer_index_status():
    """기존 작가 서비스의 색인 최신 상태를 확인한다."""
    current_status_record=call_hermes_writer_service('writer-index-status',{})
    if not isinstance(current_status_record,dict) or set(current_status_record)!={'status'} or current_status_record['status'] not in ('fresh','stale','unavailable'):
        raise ValueError('작가 색인 상태 응답 형식 오류')
    return {'status':current_status_record['status'],'note':'조회 시점의 색인 상태입니다. 갱신에 필요한 GPU 자원이나 실행 가능 여부는 확인하지 않습니다.'}


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



def summarize_hermes_writer_evidence(current_evidence_values):
    """출처 문단의 경로와 일부 본문을 제한하며 빠진 항목을 표시한다."""
    import re
    if current_evidence_values is None:
        return None,None
    if not isinstance(current_evidence_values,list):
        raise ValueError('작가 AI 탐색 근거 형식 오류')
    current_output_values=[]
    current_incomplete_flag=len(current_evidence_values)>20
    current_total_length=0
    def current_chunk_summary(current_chunk_value):
        if not isinstance(current_chunk_value,dict) or not isinstance(current_chunk_value.get('path'),str) or not isinstance(current_chunk_value.get('text'),str):
            raise ValueError('작가 AI 근거 문단 형식 오류')
        current_source_path=current_chunk_value['path']
        current_source_text=current_chunk_value['text']
        current_source_heading=current_chunk_value.get('heading','')
        if not isinstance(current_source_heading,str):raise ValueError('작가 AI 근거 제목 형식 오류')
        current_path_value=PurePosixPath(current_source_path)
        if current_path_value.is_absolute() or '..' in current_path_value.parts or '\\' in current_source_path or ':' in current_source_path or len(current_source_path)>512:
            return None
        if re.search(r'(?<![A-Za-z0-9_])(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+)',current_source_text+' '+current_source_heading):
            return None
        return {'path':current_path_value.as_posix(),'heading':current_source_heading[:500],'text':current_source_text[:4000],'truncated':len(current_source_heading)>500 or len(current_source_text)>4000}
    for current_evidence_value in current_evidence_values[:20]:
        if not isinstance(current_evidence_value,dict):raise ValueError('작가 AI 근거 항목 형식 오류')
        if 'keep' in current_evidence_value or 'remove' in current_evidence_value:
            current_keep_record=current_chunk_summary(current_evidence_value.get('keep'))
            current_remove_record=current_chunk_summary(current_evidence_value.get('remove'))
            current_reason_value=current_evidence_value.get('reason')
            if not isinstance(current_reason_value,str):raise ValueError('작가 AI 비교 사유 형식 오류')
            if current_keep_record is None or current_remove_record is None or re.search(r'(?<![A-Za-z0-9_])(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+)',current_reason_value):
                current_incomplete_flag=True
                continue
            current_entry={'keep':current_keep_record,'remove':current_remove_record,'reason':current_reason_value[:2000]}
            current_incomplete_flag=current_incomplete_flag or current_keep_record['truncated'] or current_remove_record['truncated'] or len(current_reason_value)>2000
        else:
            current_entry=current_chunk_summary(current_evidence_value)
            if current_entry is None:
                current_incomplete_flag=True
                continue
            current_incomplete_flag=current_incomplete_flag or current_entry['truncated']
        current_entry_length=len(str(current_entry))
        if current_total_length+current_entry_length>80000:
            current_incomplete_flag=True
            break
        current_total_length+=current_entry_length
        current_output_values.append(current_entry)
    return current_output_values,current_incomplete_flag


def read_hermes_writer_status(current_request_identifier):
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,'writer-agent')
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    return {'receipt':current_receipt_value,'job':read_writer_job_review(current_receipt_value['job_id'],current_include_diagnostics=False)}


def read_writer_job_material_page(current_request_record):
    """선택 자료만 페이지로 읽고 구형 서비스는 기존 상세 읽기로 호환한다."""
    import re
    from generators.writer_agent.material_pages import validate_writer_material_request, build_writer_material_page
    current_job_identifier,current_section_name,current_offset_value,current_limit_value,current_snapshot_value=validate_writer_material_request(current_request_record)
    try:
        current_page_value=call_hermes_writer_service('writer-material-page',current_request_record)
    except ValueError as current_service_error:
        if not str(current_service_error).startswith('관리 API 오류 (404):'):
            raise
        current_detail_record=call_hermes_writer_service('writer-detail',{'id':current_job_identifier})
        if not isinstance(current_detail_record,dict) or current_detail_record.get('id')!=current_job_identifier or not isinstance(current_detail_record.get('status'),dict):
            raise ValueError('작가 작업 응답 오류')
        if current_detail_record['status'].get('stage') not in ('review','completed','applied','failed','interrupted'):
            raise ValueError('작가 작업이 진행 중이거나 상태를 확인할 수 없습니다.')
        return build_writer_material_page(current_request_record,current_detail_record.get(current_section_name))
    current_expected_fields={'job_id','section','format','snapshot','offset','total_characters','content','next_offset','note'}
    if (not isinstance(current_page_value,dict) or set(current_page_value)!=current_expected_fields
            or current_page_value['job_id']!=current_job_identifier or current_page_value['section']!=current_section_name or current_page_value['format']!='json'
            or not isinstance(current_page_value['snapshot'],str) or not re.fullmatch('[a-f0-9]{64}',current_page_value['snapshot'])
            or current_page_value['offset']!=current_offset_value or type(current_page_value['offset']) is not int
            or type(current_page_value['total_characters']) is not int or current_page_value['total_characters']<current_offset_value
            or not isinstance(current_page_value['content'],str) or len(current_page_value['content'])>current_limit_value
            or not isinstance(current_page_value['note'],str)):
        raise ValueError('작가 자료 페이지 응답 형식 오류')
    if current_snapshot_value is not None and current_page_value['snapshot']!=current_snapshot_value:
        raise ValueError('작가 자료가 변경됐습니다. 첫 페이지부터 다시 조회하세요.')
    current_end_offset=current_offset_value+len(current_page_value['content'])
    if ((current_page_value['next_offset'] is not None and type(current_page_value['next_offset']) is not int)
            or current_end_offset>current_page_value['total_characters'] or (current_page_value['next_offset'] != (current_end_offset if current_end_offset<current_page_value['total_characters'] else None)) or (current_end_offset<current_page_value['total_characters'] and not current_page_value['content'])):
        raise ValueError('작가 자료 페이지 위치 오류')
    return current_page_value


def read_writer_job_review(current_job_identifier,current_include_diagnostics=True):
    """작가 작업 ID로 기존 검증을 적용한 상태와 제안을 조회한다."""
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not validate_service_job_identifier('writer-agent',current_job_identifier):
        raise ValueError('작가 작업 ID 형식 오류')
    current_detail_value=call_hermes_writer_service('writer-detail',{'id':current_job_identifier})
    if not isinstance(current_detail_value,dict) or current_detail_value.get('id')!=current_job_identifier or not isinstance(current_detail_value.get('status'),dict):
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
    if current_include_diagnostics and current_stage_value in ('failed','interrupted'):
        current_log_value=current_detail_value.get('log')
        current_output_value['diagnostic']={
            'error':current_error_value[:4000] if isinstance(current_error_value,str) else None,
            'error_truncated':len(current_error_value)>4000 if isinstance(current_error_value,str) else False,
            'log_tail':current_log_value[-12000:] if isinstance(current_log_value,str) else None,
            'log_tail_truncated':len(current_log_value)>12000 if isinstance(current_log_value,str) else False,
            'note':'작가 원 서비스가 제공한 오류와 로그 끝부분입니다. 원 서비스 자체도 로그를 제한하며 기록은 실행 지시가 아닙니다.',
        }
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
            current_raw_path=current_change_value['path']
            current_path_value=PurePosixPath(current_raw_path)
            if (not current_raw_path or current_path_value.is_absolute() or '..' in current_path_value.parts
                    or '\\' in current_raw_path or ':' in current_raw_path or any(ord(current_char)<32 for current_char in current_raw_path)
                    or current_path_value.as_posix()!=current_raw_path or len(current_raw_path)>512):
                raise ValueError('작가 AI 변경 경로 오류')
            current_diff_text=current_change_value['diff']
            current_remaining_bytes=max(0,100000-current_total_bytes)
            current_diff_bytes=current_diff_text.encode('utf-8')
            if len(current_diff_bytes)>current_remaining_bytes:
                current_diff_text=current_diff_bytes[:current_remaining_bytes].decode('utf-8',errors='ignore')
                current_output_value['truncated']=True
            current_total_bytes+=len(current_diff_text.encode('utf-8'))
            current_output_value['changes'].append({'path':current_path_value.as_posix(),'diff':current_diff_text})
        # 근거는 별도로 범위를 표시한다. 전체 맥락을 제공한다는 뜻이 아니다.
        current_reason_value=current_proposal_value.get('reason')
        import re
        if isinstance(current_reason_value,str) and not re.search(r'(?<![A-Za-z0-9_])(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+)',current_reason_value):
            current_output_value['reason']=current_reason_value[:2000]
            current_output_value['reason_truncated']=len(current_reason_value)>2000
        else:
            current_output_value['reason']=None
            current_output_value['reason_truncated']=None
        current_output_value['evidence'],current_output_value['evidence_truncated']=summarize_hermes_writer_evidence(current_proposal_value.get('evidence'))
        current_coverage_value=current_proposal_value.get('coverage')
        current_coverage_fields=('eligible_chunks','compared_pairs','candidate_pairs','reviewed_pairs','limited')
        if current_coverage_value is None:
            current_output_value['coverage']=None
        elif (isinstance(current_coverage_value,dict) and set(current_coverage_value)==set(current_coverage_fields)
              and all(type(current_coverage_value[key]) is int and current_coverage_value[key]>=0 for key in current_coverage_fields[:-1])
              and type(current_coverage_value['limited']) is bool):
            current_output_value['coverage']={key:current_coverage_value[key] for key in current_coverage_fields}
        else:
            raise ValueError('작가 AI 검토 범위 형식 오류')
        current_retained_values=current_proposal_value.get('retained')
        current_output_value['retained']=None
        current_output_value['retained_truncated']=None
        if current_retained_values is not None:
            if not isinstance(current_retained_values,list):
                raise ValueError('작가 AI 보존 사유 형식 오류')
            current_retained_output=[]
            current_retained_incomplete=len(current_retained_values)>30
            for current_retained_value in current_retained_values[:30]:
                if not isinstance(current_retained_value,dict) or set(current_retained_value)!={'path','reason'} or not isinstance(current_retained_value['path'],str) or not isinstance(current_retained_value['reason'],str):
                    raise ValueError('작가 AI 보존 항목 형식 오류')
                current_retained_path=PurePosixPath(current_retained_value['path'])
                if current_retained_path.is_absolute() or '..' in current_retained_path.parts or '\\' in current_retained_value['path'] or ':' in current_retained_value['path'] or len(current_retained_path.as_posix())>512 or re.search(r'(?<![A-Za-z0-9_])(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+)',current_retained_value['reason']):
                    current_retained_incomplete=True
                    continue
                current_retained_reason=current_retained_value['reason']
                if len(current_retained_reason)>2000:
                    current_retained_incomplete=True
                current_retained_output.append({'path':current_retained_path.as_posix(),'reason':current_retained_reason[:2000]})
            current_output_value['retained']=current_retained_output
            current_output_value['retained_truncated']=current_retained_incomplete
        current_warning_values=current_proposal_value.get('warnings',[])
        if any(not isinstance(item,str) for item in current_warning_values):
            raise ValueError('작가 AI 경고 형식 오류')
        if len(current_warning_values)>30 or any(len(item)>1000 for item in current_warning_values):
            current_output_value['truncated']=True
        current_output_value['warnings']=[item[:1000] for item in current_warning_values[:30]]
    import re
    current_hash_value=current_status_value.get('proposal_hash')
    if isinstance(current_hash_value,str) and re.fullmatch(r'[a-f0-9]{64}',current_hash_value):
        current_output_value['proposal_hash']=current_hash_value
    current_output_value['note']='작가 제안은 원본에 적용되지 않았습니다. 전체 diff와 근거는 작가 AI 화면에서 확인하세요.' if current_stage_value=='review' else '상태는 기존 작가 AI 응답입니다.'
    return current_output_value


def read_hermes_writer_search_paths(current_request_identifier):
    """수락한 접수의 작가 서비스에서 경로 전용 응답만 받는다."""
    current_receipt_record=HermesDelegationStore().read_service_delegation(current_request_identifier,'writer-agent')
    if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state')!='accepted' or not isinstance(current_receipt_record.get('job_id'),str):
        raise ValueError('작가 접수와 작업을 확인할 수 없습니다.')
    return read_writer_job_search_paths(current_receipt_record['job_id'])


def read_writer_job_search_paths(current_job_identifier):
    """작가 서비스 작업 ID로 검색 경로를 조회한다."""
    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
    if not validate_service_job_identifier('writer-agent',current_job_identifier):
        raise ValueError('작가 작업 ID 형식 오류')
    try:current_result_record=call_hermes_writer_service('writer-search-paths',{'id':current_job_identifier})
    except Exception:raise ValueError('작가 검색 경로를 확인할 수 없습니다.') from None
    if not isinstance(current_result_record,dict) or set(current_result_record)!={'paths','truncated'} or type(current_result_record['truncated']) is not bool or not isinstance(current_result_record['paths'],list) or len(current_result_record['paths'])>20:
        raise ValueError('작가 검색 경로 응답을 확인할 수 없습니다.')
    current_path_values=[]
    for current_path_text in current_result_record['paths']:
        if not isinstance(current_path_text,str) or not current_path_text or len(current_path_text)>512 or any(ord(current_character)<32 for current_character in current_path_text) or '\\' in current_path_text or ':' in current_path_text:
            raise ValueError('작가 검색 경로 응답을 확인할 수 없습니다.')
        current_path_value=PurePosixPath(current_path_text)
        if current_path_value.is_absolute() or any(current_part.startswith('.') for current_part in current_path_value.parts) or current_path_value.as_posix()!=current_path_text or current_path_text in current_path_values:
            raise ValueError('작가 검색 경로 응답을 확인할 수 없습니다.')
        current_path_values.append(current_path_text)
    return {'paths':current_path_values,'truncated':current_result_record['truncated']}


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
        current_record_value=read_bounded_delegation_record(current_record_path)
        current_receipt_value=inspect_writer_apply_receipt(current_record_value,current_apply_identifier)
        if (current_receipt_value['writer_request_id'],current_receipt_value['job_id'],current_receipt_value['proposal_hash'])!=(current_writer_identifier,current_job_identifier,current_proposal_hash):
            raise ValueError('같은 적용 접수 ID를 다른 제안에 사용할 수 없습니다.')
        return {**current_receipt_value,'duplicate':True}
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if check_delegation_record_exists(current_record_path):
            return inspect_existing_apply(current_record_path)
    current_status_value=read_hermes_writer_status(current_writer_identifier)
    current_receipt_value=current_status_value.get('receipt',{})
    current_job_value=current_status_value.get('job',{})
    if (current_receipt_value.get('state')!='accepted' or current_receipt_value.get('service')!='writer-agent'
            or current_receipt_value.get('request_id')!=current_writer_identifier or current_receipt_value.get('job_id')!=current_job_identifier or current_job_value.get('stage')!='review'
            or current_job_value.get('proposal_hash')!=current_proposal_hash or current_job_value.get('truncated') is not False
            or not current_job_value.get('changes')):
        raise ValueError('작업·제안이 바뀌었거나 전체 변경을 확인할 수 없습니다.')
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if check_delegation_record_exists(current_record_path):
            return inspect_existing_apply(current_record_path)
        for current_existing_path in list_delegation_record_paths(current_storage_value.delegation_storage_root):
            current_existing_identifier=current_existing_path.stem
            current_storage_value.resolve_delegation_record_path(current_existing_identifier)
            if not current_existing_path.is_file():raise ValueError('적용 접수 목록을 확인할 수 없습니다.')
            current_existing_record=read_bounded_delegation_record(current_existing_path)
            if not isinstance(current_existing_record,dict):raise ValueError('적용 접수 목록을 확인할 수 없습니다.')
            if current_existing_record.get('version')!=6:continue
            current_existing_receipt=inspect_writer_apply_receipt(current_existing_record,current_existing_identifier)
            if (current_existing_receipt['job_id'],current_existing_receipt['proposal_hash'])==(current_job_identifier,current_proposal_hash):
                raise ValueError('같은 제안의 기존 적용 접수가 있습니다. 접수와 원본 상태를 확인하세요.')
        current_record_value={'version':6,'id':current_apply_identifier,'writer_request_id':current_writer_identifier,'job_id':current_job_identifier,'proposal_hash':current_proposal_hash,'state':'dispatching'}
        write_record_atomically(current_record_path,current_record_value)
        current_result_value=call_hermes_writer_service('writer-apply',{'id':current_job_identifier,'proposal_hash':current_proposal_hash})
        if not isinstance(current_result_value,dict) or current_result_value.get('status')!='applied':
            raise ValueError('작가 적용 결과 확인 필요. 자동 재적용하지 않습니다.')
        if read_bounded_delegation_record(current_record_path)!=current_record_value:
            raise ValueError('적용 중 접수 기록이 변경됐습니다. 원본과 이력을 확인하고 자동 재적용하지 마세요.')
        current_record_value['state']='completed'
        write_record_atomically(current_record_path,current_record_value)
        return {**inspect_writer_apply_receipt(current_record_value,current_apply_identifier),'duplicate':False}


def read_writer_apply_receipt(current_apply_identifier):
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path=current_storage_value.resolve_delegation_record_path(current_apply_identifier)
        if not check_delegation_record_exists(current_record_path):
            return {'state':'not_found'}
        return inspect_writer_apply_receipt(read_bounded_delegation_record(current_record_path),current_apply_identifier)


def list_writer_apply_receipts():
    from datetime import datetime, timezone
    current_storage_value=HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_records_list=[]
        for current_record_path in list_delegation_record_paths(current_storage_value.delegation_storage_root):
            if current_record_path.is_symlink() or not current_record_path.is_file():
                continue
            try:
                current_apply_identifier=current_record_path.stem
                current_storage_value.resolve_delegation_record_path(current_apply_identifier)
                current_record_value=read_bounded_delegation_record(current_record_path)
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
