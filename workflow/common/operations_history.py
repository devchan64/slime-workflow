"""운영 작업 이력과 GPU 관측 기록의 조회 및 연결."""
from collections import Counter
import re
import base64
import binascii
import hashlib

def resolve_operations_queue_identity(current_service_name):
    """검증된 전용 대기열 이름을 반환하고 공용 image 소유권은 추정하지 않는다."""
    current_shared_services={'kimodo','dwpose','wan22-vace','wan22-animate2','qwen-21','qwen-21-circular','mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','expression','seamless-tile','floor-tile'}
    from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if current_service_name in current_shared_services or current_service_name in FLUX_IMAGE_PROFILE_RECORDS:
        return None
    if current_service_name=='wan22-fun-control':
        return 'wan-fun'
    return current_service_name



def read_operations_verified_source(current_service_name,current_source_value):
    """GPU 관측 응답에서 허용된 공유 대기열의 원 서비스만 표시한다."""
    from workflow.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    current_image_sources={'kimodo','dwpose','wan22-vace','wan22-animate2','qwen-21','qwen-21-circular','mannequin-generator','prop-generator','vegetation-generator','expression','seamless-tile','floor-tile','billboard-generator','building-generator'}
    if current_service_name=='image' and isinstance(current_source_value,str) and current_source_value in current_image_sources:return current_source_value
    if current_service_name=='flux-image' and isinstance(current_source_value,str) and current_source_value in FLUX_IMAGE_PROFILE_RECORDS:return current_source_value
    from workflow.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    if is_dedicated_gpu_source_verifiable(current_service_name):
        current_expected_source='wan22-fun-control' if current_service_name in ('wan-fun','wan-fun-prepare') else current_service_name
        if current_source_value==current_expected_source:return current_expected_source
    return None


def summarize_operations_reservation_snapshot(current_management_record):
    """예약의 관측 기록만 표시하며 종료나 해제 여부를 추정하지 않는다."""
    try:
        current_reservation_record=current_management_record['reservations']
        if current_reservation_record.get('status')!='available' or not isinstance(current_reservation_record.get('records'),list) or type(current_reservation_record.get('truncated')) is not bool:
            raise ValueError('예약 조회 불가')
        current_reservation_values=current_reservation_record['records']
        current_reservation_index={}
        current_reservation_rows=[]
        current_unmatched_record=bool(current_reservation_record['truncated'])
        for current_reservation_value in current_reservation_values:
            if not isinstance(current_reservation_value,dict) or current_reservation_value.get('state') not in ('recorded','cleanup_unverified','unknown'):
                raise ValueError('예약 형식 오류')
            current_state_value=current_reservation_value['state']
            current_service_name=current_reservation_value.get('service')
            current_job_identifier=current_reservation_value.get('job_id')
            current_memory_value=current_reservation_value.get('required_memory_mib')
            if current_state_value=='unknown':
                current_unmatched_record=True
                current_reservation_rows.append(['확인 불가','확인 불가','확인 불가','확인 불가','확인 불가','확인 불가'])
                continue
            if not isinstance(current_service_name,str) or type(current_memory_value) is not int or current_memory_value<0 or (current_job_identifier is not None and not isinstance(current_job_identifier,str)):
                raise ValueError('예약 항목 형식 오류')
            current_leader_value=current_reservation_value.get('worker_leader')
            if current_leader_value not in (None,'verified_running','unverified'):raise ValueError('리더 상태 형식 오류')
            current_leader_label={'verified_running':'리더 생존 확인 · 그룹 전체는 미확인','unverified':'리더 확인 불가',None:'미제공'}[current_leader_value]
            current_state_label='정리 확인 필요' if current_state_value=='cleanup_unverified' else '예약 기록'
            current_verified_source=read_operations_verified_source(current_service_name,current_reservation_value.get('source_service'))
            current_reservation_rows.append([current_state_label,current_service_name,current_job_identifier or 'ID 확인 불가',str(current_memory_value),current_leader_label,current_verified_source or '미확인'])
            if current_job_identifier is None:current_unmatched_record=True
            else:
                current_reservation_index.setdefault((current_service_name,current_job_identifier),[]).append(current_state_value)
                current_source_service=current_verified_source
                if isinstance(current_source_service,str):
                    current_reservation_index.setdefault(('source',current_service_name,current_source_service,current_job_identifier),[]).append(current_state_value)
        current_notice_text='예약 기록 '+str(len(current_reservation_rows))+'건'+(' 이상 · 일부 미조회' if current_reservation_record['truncated'] else '')+' · 기록만으로 프로세스 생존이나 예약 해제를 보장하지 않습니다. 관측 '+str(current_management_record.get('queried_at','확인 불가'))
        return current_reservation_index,current_unmatched_record,current_reservation_rows,current_notice_text
    except (TypeError,ValueError,KeyError,AttributeError):
        return None,True,[],'GPU 예약 조회 불가 · 예약이 없다는 뜻이 아닙니다.'


def label_operations_dedicated_queue(current_queue_counts,current_service_name,current_job_identifier,current_missing_label='대기 기록 없음 · 상태 별도 확인'):
    """전용 대기열과 다른 서비스의 동일 ID를 구분한다."""
    if current_queue_counts is None:return '조회 불가'
    current_match_count=current_queue_counts.get((current_service_name,current_job_identifier),0)
    if current_match_count>1:return '연결 불확실 · 중복 대기'
    if current_match_count==1 and any(current_id==current_job_identifier and current_service!=current_service_name and current_count>0 for (current_service,current_id),current_count in current_queue_counts.items()):
        return '대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가'
    if current_match_count==1:return '대기 기록 확인'
    if any(current_id==current_job_identifier and current_service!=current_service_name and current_count>0 for (current_service,current_id),current_count in current_queue_counts.items()):
        return '다른 GPU 서비스 동일 ID · 소유 확인 필요'
    return current_missing_label


def label_operations_reservation_record(current_reservation_index,current_unmatched_record,current_service_name,current_job_identifier):
    if current_reservation_index is None:return '조회 불가'
    current_matches=current_reservation_index.get((current_service_name,current_job_identifier),[])
    if len(current_matches)>1:return '연결 불확실 · 중복 예약'
    if len(current_matches)==1:
        current_label_value='정리 확인 필요' if current_matches[0]=='cleanup_unverified' else '예약 기록 확인'
        if any(isinstance(current_key,tuple) and len(current_key)==2 and current_key[1]==current_job_identifier and current_key[0]!=current_service_name and current_values for current_key,current_values in current_reservation_index.items()):
            current_label_value+=' · 다른 서비스 동일 ID'
        return current_label_value+(' · 미확인 기록 포함' if current_unmatched_record else '')
    if any(isinstance(current_key,tuple) and len(current_key)==2 and current_key[1]==current_job_identifier and current_key[0]!=current_service_name and current_values for current_key,current_values in current_reservation_index.items()):
        return '다른 GPU 서비스 동일 ID · 소유 확인 필요'+(' · 미확인 기록 포함' if current_unmatched_record else '')
    return '미확인 예약 포함' if current_unmatched_record else '예약 기록 없음 · 시점 기준'



def label_operations_shared_queue_record(current_queue_counts,current_source_counts,current_pool_name,current_source_name,current_job_identifier):
    """공용 대기 기록의 부재, 다른 서비스, 중복과 소유 불명을 구분한다."""
    if current_queue_counts is None or current_source_counts is None:return '조회 불가'
    current_pool_count=current_queue_counts.get((current_pool_name,current_job_identifier),0)
    current_source_count=current_source_counts.get((current_pool_name,current_source_name,current_job_identifier),0)
    if current_pool_count>1:return '연결 불확실 · 중복 대기'
    if current_pool_count==1 and current_source_count==1 and any(current_id==current_job_identifier and current_service!=current_pool_name and current_count>0 for (current_service,current_id),current_count in current_queue_counts.items()):
        return '대기 기록 확인 · 다른 서비스 동일 ID · 우선 실행 확인 불가'
    if current_pool_count==1 and current_source_count==1:return '대기 기록 확인 · 원 서비스 확인'
    if current_pool_count==1:return '공용 '+current_pool_name+' 대기열 · 소유 확인 필요'
    if any(current_id==current_job_identifier and current_service!=current_pool_name and current_count>0 for (current_service,current_id),current_count in current_queue_counts.items()):
        return '다른 GPU 서비스 동일 ID · 소유 확인 필요'
    return '일치 대기 기록 없음 · 상태 별도 확인'


def label_operations_shared_reservation_record(current_reservation_index,current_unmatched_record,current_pool_name,current_source_name,current_job_identifier):
    """예약 자체에서 출처를 확인한 유일한 기록만 서비스 작업에 연결한다."""
    if current_reservation_index is None:return '조회 불가'
    current_pool_values=current_reservation_index.get((current_pool_name,current_job_identifier),[])
    current_source_values=current_reservation_index.get(('source',current_pool_name,current_source_name,current_job_identifier),[])
    current_uncertainty_suffix=' · 미확인 기록 포함' if current_unmatched_record else ''
    if len(current_pool_values)>1:return '연결 불확실 · 중복 예약'+current_uncertainty_suffix
    if not current_pool_values:
        if any(isinstance(current_key,tuple) and len(current_key)==2 and current_key[1]==current_job_identifier and current_key[0]!=current_pool_name and current_values for current_key,current_values in current_reservation_index.items()):
            return '다른 GPU 서비스 동일 ID · 소유 확인 필요'+current_uncertainty_suffix
        return '미확인 예약 포함' if current_unmatched_record else '일치 예약 기록 없음 · 상태 별도 확인'
    if len(current_pool_values)==1 and len(current_source_values)==1:
        current_label='정리 확인 필요' if current_source_values[0]=='cleanup_unverified' else '예약 기록 확인 · 원 서비스 확인'
        if any(isinstance(current_key,tuple) and len(current_key)==2 and current_key[1]==current_job_identifier and current_key[0]!=current_pool_name and current_values for current_key,current_values in current_reservation_index.items()):
            current_label+=' · 다른 서비스 동일 ID'
        return current_label+current_uncertainty_suffix
    return '공용 '+current_pool_name+' 예약 · 소유 확인 필요'+current_uncertainty_suffix


def label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,current_queue_service,current_source_service,current_job_identifier):
    """경로로 확인된 독립 서비스 대기 기록만 원본 작업에 연결한다."""
    current_result_label=label_operations_shared_queue_record(current_queue_counts,current_source_counts,current_queue_service,current_source_service,current_job_identifier)
    if current_queue_service=='wan-fun' and current_source_service=='wan22-fun-control':
        current_prepare_label=label_operations_shared_queue_record(current_queue_counts,current_source_counts,'wan-fun-prepare',current_source_service,current_job_identifier)
        return '생성: '+current_result_label+' / 준비: '+current_prepare_label
    return current_result_label.replace('공용 '+current_queue_service+' 대기열 · 소유 확인 필요','대기 기록 · 원 서비스 확인 필요')


def label_operations_verified_dedicated_reservation(current_reservation_index,current_unmatched_record,current_queue_service,current_source_service,current_job_identifier):
    """경로로 확인된 독립 서비스 예약만 원본 작업에 연결한다."""
    current_result_label=label_operations_shared_reservation_record(current_reservation_index,current_unmatched_record,current_queue_service,current_source_service,current_job_identifier)
    if current_queue_service=='wan-fun' and current_source_service=='wan22-fun-control':
        current_prepare_label=label_operations_shared_reservation_record(current_reservation_index,current_unmatched_record,'wan-fun-prepare',current_source_service,current_job_identifier)
        return '생성: '+current_result_label+' / 준비: '+current_prepare_label
    return current_result_label.replace('공용 '+current_queue_service+' 예약 · 소유 확인 필요','예약 기록 · 원 서비스 확인 필요')


from workflow.domains.hermes_agent.history_catalog import HERMES_HISTORY_STATUS_LABELS as OPERATIONS_HISTORY_STATUS_LABELS, normalize_hermes_history_status


def read_operations_job_history_page(current_search_text,current_status_filter,current_page_record=None,current_direction='first', *, command):
    """작업 목록의 페이지와 관측 가능한 GPU 기록을 같은 행에 표시한다."""
    current_query=(current_search_text or '').strip().casefold()
    try:
        if current_status_filter not in ('전체',*OPERATIONS_HISTORY_STATUS_LABELS):raise ValueError('상태 필터 오류')
        current_offset=0
        current_request={'offset':0,'limit':30}
        if current_query:current_request['query']=current_query
        if current_status_filter!='전체':current_request['status']=current_status_filter
        if current_direction!='first':
            if current_direction not in ('older','newer') or not isinstance(current_page_record,dict) or current_page_record.get('query')!=current_query or current_page_record.get('status')!=current_status_filter:
                raise ValueError('검색 조건 변경')
            current_offset=current_page_record.get('next_offset') if current_direction=='older' else max(0,current_page_record.get('offset',0)-30)
            current_snapshot=current_page_record.get('snapshot')
            if type(current_offset) is not int or current_offset<0 or not isinstance(current_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot):raise ValueError('페이지 상태 오류')
            current_request.update(offset=current_offset,snapshot=current_snapshot)
        current_result=command('hermes-agent','hermes-history',current_request)
        if not isinstance(current_result,dict) or not isinstance(current_result.get('records'),list) or len(current_result['records'])>30 or current_result.get('offset')!=current_offset or type(current_result.get('total')) is not int:
            raise ValueError('작업 이력 응답 오류')
        current_snapshot=current_result.get('snapshot')
        current_next=current_result.get('next_offset')
        current_total=current_result['total']
        current_expected_count=min(30,max(0,current_total-current_offset))
        current_expected_next=current_offset+current_expected_count if current_offset+current_expected_count<current_total else None
        if current_total<0 or current_offset>current_total or len(current_result['records'])!=current_expected_count or current_next!=current_expected_next or (current_next is not None and type(current_next) is not int):raise ValueError('작업 이력 페이지 범위 오류')
        if not isinstance(current_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot) or (current_direction!='first' and current_snapshot!=current_request['snapshot']):
            raise ValueError('작업 이력 페이지 오류')
        current_management=None
        try:
            current_management=command('hermes-agent','hermes-management-status',{})
            current_queue=current_management['queue']
            if not isinstance(current_queue,dict) or current_queue.get('status')!='available' or not isinstance(current_queue.get('jobs'),list) or any(not isinstance(item,dict) or not isinstance(item.get('service'),str) or not isinstance(item.get('id'),str) for item in current_queue['jobs']):raise ValueError('대기열 오류')
            current_counts=Counter((item['service'],item['id']) for item in current_queue['jobs'])
        except (OSError,ValueError,KeyError,TypeError,RuntimeError):
            current_counts=None
        current_reservations,current_unmatched,_,_=summarize_operations_reservation_snapshot(current_management)
        current_ids=Counter(item.get('id') for item in current_result['records'] if isinstance(item,dict) and isinstance(item.get('id'),str))
        current_rows=[]
        for current_item in current_result['records']:
            if not isinstance(current_item,dict) or not isinstance(current_item.get('id'),str):raise ValueError('작업 이력 형식 오류')
            current_id=current_item['id']
            current_status_record=current_item.get('status') or {}
            current_status=current_status_record.get('status') if isinstance(current_status_record,dict) else None
            current_status=normalize_hermes_history_status(current_status)
            current_request_record=current_item.get('request') or {}
            current_prompt=current_request_record.get('prompt','') if isinstance(current_request_record,dict) else ''
            current_prompt=current_prompt if isinstance(current_prompt,str) else ''
            if current_status_filter!='전체' and current_status!=current_status_filter:continue
            if current_query and current_query not in (current_id+' '+current_prompt).casefold():continue
            if current_ids[current_id]!=1:current_queue_label='연결 불확실 · 중복 작업 ID'
            else:current_queue_label=label_operations_dedicated_queue(current_counts,'hermes-agent',current_id)
            current_reservation_label=label_operations_reservation_record(current_reservations,current_unmatched,'hermes-agent',current_id) if current_ids[current_id]==1 else '연결 불확실 · 중복 작업 ID'
            current_rows.append([current_id,OPERATIONS_HISTORY_STATUS_LABELS[current_status],current_queue_label,current_prompt[:120],current_reservation_label])
        current_page={'query':current_query,'status':current_status_filter,'offset':current_offset,'next_offset':current_next,'snapshot':current_snapshot}
        current_notice='전체 '+str(current_result['total'])+'건 · '+str(current_offset+1 if current_result['records'] else 0)+'–'+str(current_offset+len(current_result['records']))+'번째 검색 결과 · 표시 '+str(len(current_rows))+'건. 상태와 GPU 관측은 조회 시점 기준입니다.'
        return current_rows,current_notice,current_page
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        return [],'작업 목록을 확인할 수 없거나 변경됐습니다. 처음부터 다시 조회하세요.',None


def format_operations_capture_request_id(current_job_record):
    """검증된 캡처 대기 작업의 접수 ID만 표시한다."""
    if current_job_record.get('service') != 'review-capture':
        return '—'
    current_request_identifier=current_job_record.get('request_id')
    current_capture_service=current_job_record.get('capture_service')
    if current_job_record.get('source_service') == 'review-capture' and current_capture_service in ('map-review','character-review') and isinstance(current_request_identifier,str) and re.fullmatch(r'[A-Za-z0-9_-]{8,80}',current_request_identifier):
        current_capture_label='맵' if current_capture_service=='map-review' else '캐릭터'
        return current_capture_label+' · '+current_request_identifier
    return '미확인'


def summarize_operations_queue_snapshot(current_management_record):
    try:
        current_queue_record=current_management_record['queue']
        if not isinstance(current_queue_record,dict) or current_queue_record.get('status')!='available' or not isinstance(current_queue_record.get('jobs'),list):
            raise ValueError('대기열 조회 불가')
        current_queue_records=current_queue_record['jobs']
        if any(not isinstance(item,dict) or not isinstance(item.get('service'),str) or not isinstance(item.get('id'),str) for item in current_queue_records):
            raise ValueError('대기열 형식 오류')
        current_queue_rows=[[str(index+1),item['service'],item['id'],read_operations_verified_source(item['service'],item.get('source_service')) or '미확인',format_operations_capture_request_id(item)] for index,item in enumerate(current_queue_records)]
        current_queue_counts=Counter((item['service'],item['id']) for item in current_queue_records)
        current_queue_notice='대기 기록 '+str(len(current_queue_rows))+'건 · 식별값이 빠진 티켓은 실행기 신원을 확인할 수 없으며 실행 순서나 완료도 보장하지 않습니다. 관측 '+str(current_management_record.get('queried_at','확인 불가'))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        current_queue_rows=[]
        current_queue_counts=None
        current_queue_notice='GPU 대기열 조회 불가 · 대기열이 비었다는 뜻이 아닙니다.'
    return current_queue_rows, current_queue_counts, current_queue_notice


def prepare_operations_priority_request(current_priority_target, command):
    """대기 티켓과 기존 접수를 확인하여 명시적인 사용자 검토를 준비한다."""
    try:
        if not isinstance(current_priority_target,dict) or set(current_priority_target)!={'service','id'}:
            raise ValueError('대상 오류')
        current_preview_record=command('hermes-agent','hermes-priority-preview',current_priority_target)
        if not isinstance(current_preview_record,dict) or (current_preview_record.get('service'),current_preview_record.get('job_id'))!=(current_priority_target['service'],current_priority_target['id']):
            raise ValueError('대상 불일치')
        current_ticket_revision=current_preview_record.get('ticket_revision')
        current_queue_position=current_preview_record.get('queue_position')
        current_queue_count=current_preview_record.get('queue_count')
        current_identity_label={'verified':'부팅·시작 식별값 일치','unverified':'미확인'}.get(current_preview_record.get('executor_identity','unverified'))
        if current_identity_label is None:raise ValueError('실행기 신원 오류')
        if not isinstance(current_ticket_revision,str) or not re.fullmatch(r'[a-f0-9]{64}',current_ticket_revision) or type(current_queue_position) is not int or type(current_queue_count) is not int or not 1<=current_queue_position<=current_queue_count:
            raise ValueError('대기 정보 오류')
        current_request_digest=hashlib.sha256((current_priority_target['service']+'\0'+current_priority_target['id']+'\0'+current_ticket_revision).encode()).hexdigest()
        current_request_identifier='priority_'+current_request_digest
        current_request_record={'request_id':current_request_identifier,'service':current_priority_target['service'],'id':current_priority_target['id'],'ticket_revision':current_ticket_revision}
        current_receipt_record=command('hermes-agent','hermes-priority-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict):raise ValueError('접수 기록 오류')
        if current_receipt_record.get('state')!='not_found':
            current_expected_record=(current_request_identifier,current_priority_target['service'],current_priority_target['id'],current_ticket_revision)
            if (current_receipt_record.get('request_id'),current_receipt_record.get('service'),current_receipt_record.get('job_id'),current_receipt_record.get('ticket_revision'))!=current_expected_record or current_receipt_record.get('state') not in ('completed','unknown'):
                raise ValueError('접수 대상 오류')
            current_receipt_state=current_receipt_record['state']
            current_receipt_notice='이전에 순서 변경이 접수되었습니다. 현재 순번이나 작업 완료를 뜻하지 않습니다.' if current_receipt_state=='completed' else '이전 요청의 결과를 확인할 수 없습니다. 재요청하지 말고 원 서비스와 대기열을 확인하세요.'
            return None,current_receipt_notice,current_request_identifier
        current_review_notice='검토 대상: '+current_priority_target['service']+' · '+current_priority_target['id']+' · 관측 순번 '+str(current_queue_position)+' / '+str(current_queue_count)+' · 실행기 신원: '+current_identity_label+' · 확인 '+str(current_preview_record.get('observed_at') or '미제공')+'. 식별값이 빠진 티켓은 실행기 신원을 확인할 수 없습니다. 확인하면 다른 대기 작업보다 앞서도록 순서를 변경합니다. 실행 중인 GPU 작업은 선점하지 않습니다.'
        return current_request_record,current_review_notice,current_request_identifier
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return None,'대상 또는 접수 기록을 확인할 수 없습니다. 원 서비스와 대기열을 확인하세요. 순서는 변경하지 않았습니다.',''


def read_operations_priority_request(current_request_identifier, command):
    """화면을 다시 열어도 접수 ID로 결과를 확인할 수 있다."""
    try:
        if not isinstance(current_request_identifier,str) or not re.fullmatch(r'priority_[a-f0-9]{64}',current_request_identifier):raise ValueError('접수 ID 오류')
        current_receipt_record=command('hermes-agent','hermes-priority-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict):raise ValueError('접수 오류')
        if current_receipt_record.get('state')=='not_found':return '해당 접수 기록이 없습니다. 요청이 전달되지 않았다는 보장은 아니므로 원 서비스와 대기열을 확인하세요.'
        if current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('unknown','completed'):raise ValueError('접수 오류')
        current_target_label=str(current_receipt_record.get('service','확인 불가'))+' · '+str(current_receipt_record.get('job_id','확인 불가'))
        if current_receipt_record['state']=='completed':return current_target_label+' · 순서 변경 접수 완료. 현재 순번이나 작업 완료를 뜻하지 않습니다.'
        return current_target_label+' · 결과 확인 필요. 자동 재요청하지 말고 원 서비스와 대기열을 확인하세요.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '접수 기록을 확인할 수 없습니다. 접수 ID와 원 서비스 상태를 확인하세요.'


def reservation_inspection_target(current_reservation_rows,current_index):
    """표시된 행에서 확인 가능한 생성기 예약의 비파괴 조회 대상을 고른다."""
    if isinstance(current_index,(tuple,list)):current_index=current_index[0] if current_index else None
    if type(current_index) is not int or not isinstance(current_reservation_rows,list) or not 0<=current_index<len(current_reservation_rows):
        return None,'예약 행을 다시 선택하세요.'
    current_row=current_reservation_rows[current_index]
    if not isinstance(current_row,(list,tuple)) or len(current_row)!=6 or not all(isinstance(current_value,str) for current_value in current_row):
        return None,'예약 기록을 확인할 수 없습니다.'
    current_state,current_pool,current_job,_,_,current_source=current_row
    from workflow.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    current_owner=read_operations_verified_source(current_pool,current_source) if current_pool in ('image','flux-image') or is_dedicated_gpu_source_verifiable(current_pool) else current_pool
    from workflow.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
    if current_state not in ('예약 기록','정리 확인 필요') or current_owner not in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES) or current_owner=='writer-agent' or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job):
        return None,'확인 가능한 생성기 예약을 선택하세요. 작가 예약은 운영 대화의 작가 예약 검토를 이용하세요.'
    if sum(isinstance(current_other,(list,tuple)) and len(current_other)==6 and current_other[1]==current_pool and current_other[2]==current_job for current_other in current_reservation_rows)!=1:
        return None,'표시된 예약이 중복되어 조회 대상을 선택할 수 없습니다.'
    return {'service':current_owner,'job_id':current_job},'선택한 예약을 확인할 수 있습니다. 조회만 하며 예약이나 프로세스는 변경하지 않습니다.'


def inspect_operations_reservation_target(current_inspection_target,command):
    """서버가 전체 예약의 유일성과 서비스·리더 신원을 다시 확인한다."""
    if (not isinstance(current_inspection_target,dict) or set(current_inspection_target)!={'service','job_id'}
            or not isinstance(current_inspection_target['service'],str) or not re.fullmatch(r'[a-z0-9-]{1,80}',current_inspection_target['service'])
            or not isinstance(current_inspection_target['job_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_inspection_target['job_id'])):
        return '확인할 예약을 먼저 선택하세요.'
    try:
        current_result=command('hermes-agent','hermes-generator-reservation-inspect',current_inspection_target)
        if not isinstance(current_result,dict) or (current_result.get('service'),current_result.get('job_id'))!=(current_inspection_target['service'],current_inspection_target['job_id']):raise ValueError('예약 대상 불일치')
        current_executor={'observed':'신원 일치로 관측','not_observed':'일치 실행기 미관측','unverified':'확인 불가'}.get(current_result.get('executor'))
        current_leader={'verified_running':'신원 일치로 관측','group_absent':'기록된 그룹 미관측','unverified':'확인 불가'}.get(current_result.get('worker_leader'))
        current_memory=current_result.get('required_memory_mib')
        if current_executor is None or current_leader is None or type(current_memory) is not int or current_memory<0:raise ValueError('예약 응답 오류')
        current_review_notice=' 정리 검토에서 현재 상태를 다시 확인할 수 있습니다.' if current_result.get('review_ready') is True else ''
        return '대상: '+current_inspection_target['service']+' · '+current_inspection_target['job_id']+' · 실행기: '+current_executor+' · 작업자 리더: '+current_leader+' · 예약: '+str(current_memory)+' MiB. 조회만 수행했습니다. 실행기 미관측이나 리더 확인은 그룹 전체·별도 그룹의 종료를 보증하지 않습니다.'+current_review_notice
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '예약 신원을 확인할 수 없습니다. 원 서비스와 GPU 프로세스를 확인하세요. 예약이나 프로세스는 변경하지 않았습니다.'


def prepare_operations_reservation_recovery(current_reservation_target, command):
    """예약을 다시 조회하고 명시적인 정리 확인을 준비한다."""
    current_closed=(None,'예약을 다시 선택하고 신원을 확인하세요.','')
    if not isinstance(current_reservation_target,dict) or set(current_reservation_target)!={'service','job_id'}:return current_closed
    try:
        current_result_record=command('hermes-agent','hermes-generator-reservation-inspect',current_reservation_target)
        if not isinstance(current_result_record,dict) or (current_result_record.get('service'),current_result_record.get('job_id'))!=(current_reservation_target['service'],current_reservation_target['job_id']) or current_result_record.get('review_ready') is not True:
            return None,'예약을 안전하게 정리할 수 있는 상태인지 확인하지 못했습니다. 원 서비스와 GPU 프로세스를 확인하세요.',''
        current_review_digest=current_result_record.get('review_sha256')
        if not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('예약 검토값 오류')
        current_request_identifier='recovery_'+hashlib.sha256((current_reservation_target['service']+'\0'+current_reservation_target['job_id']+'\0'+current_review_digest).encode()).hexdigest()
        current_receipt_record=command('hermes-agent','hermes-generator-reservation-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state')!='not_found':
            return None,'이미 접수되었거나 접수 상태를 확인할 수 없습니다. 접수 결과를 조회하고 재실행하지 마세요.',current_request_identifier
        current_request_record={'request_id':current_request_identifier,**current_reservation_target,'review_sha256':current_review_digest}
        current_action_notice='기록된 작업자 그룹은 관측되지 않았으며 예약만 해제합니다.' if current_result_record.get('worker_leader')=='group_absent' else '해당 작업자 그룹을 강제 종료하고 예약을 해제합니다.'
        return current_request_record,'검토 대상: '+current_reservation_target['service']+' · '+current_reservation_target['job_id']+'. 확인하면 '+current_action_notice,current_request_identifier
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return None,'검토 또는 접수 상태를 확인하지 못했습니다. 프로세스와 예약은 변경하지 않았습니다.',''


def read_operations_reservation_recovery_receipt(current_request_identifier, command):
    from workflow.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_AUDIO_SERVICES
    if not isinstance(current_request_identifier,str) or not re.fullmatch(r'recovery_[a-f0-9]{64}',current_request_identifier):return '유효한 정리 접수 ID를 입력하세요.'
    try:
        current_receipt_record=command('hermes-agent','hermes-generator-reservation-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict):raise ValueError('접수 응답 오류')
        if current_receipt_record.get('state')=='not_found':return '접수 기록이 없습니다. 실제 예약과 GPU 프로세스를 확인하세요.'
        if current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('completed','unknown'):raise ValueError('접수 응답 오류')
        current_service_name=current_receipt_record.get('service')
        current_job_identifier=current_receipt_record.get('job_id')
        if (not isinstance(current_service_name,str) or current_service_name not in (set(SOURCE_HISTORY_GENERATOR_SERVICES)|set(SOURCE_HISTORY_AUDIO_SERVICES)) - {'writer-agent'}
                or not isinstance(current_job_identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job_identifier)):
            raise ValueError('정리 대상 확인 불가')
        current_target_text='대상: '+current_service_name+' · '+current_job_identifier+' · '
        return current_target_text+('정리 완료. 원 서비스와 GPU 상태를 확인하세요.' if current_receipt_record['state']=='completed' else '정리 결과 확인 필요. 재실행하지 말고 원 서비스와 GPU 프로세스를 확인하세요.')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '접수 결과를 확인할 수 없습니다. 재실행하지 말고 원 서비스와 GPU 프로세스를 확인하세요.'


def read_hermes_diff_page(current_job_identifier, current_cursor_record=None, *, command):
    """완료된 작업의 diff를 바이트 경계에서 이어 읽는다."""
    if not isinstance(current_job_identifier, str) or not current_job_identifier:
        raise ValueError('먼저 작업을 선택하세요.')
    if current_cursor_record is None:
        current_offset_value = 0
        current_expected_size = None
    elif not isinstance(current_cursor_record, dict) or current_cursor_record.get('job_id') != current_job_identifier:
        raise ValueError('작업이 변경됐습니다. 처음 부분부터 다시 보세요.')
    else:
        current_offset_value = current_cursor_record.get('next_offset')
        current_expected_size = current_cursor_record.get('size_bytes')
        if current_offset_value is None:
            raise ValueError('마지막 부분까지 표시했습니다.')
        if type(current_offset_value) is not int or current_offset_value < 0 or type(current_expected_size) is not int:
            raise ValueError('diff 위치를 확인할 수 없습니다. 처음부터 다시 보세요.')
    try:
        current_chunk_record = command('hermes-agent', 'hermes-diff', {'id': current_job_identifier, 'offset': current_offset_value, 'limit': 65536})
        current_total_bytes = current_chunk_record['size_bytes']
        if current_chunk_record.get('id') != current_job_identifier or current_chunk_record.get('offset') != current_offset_value or type(current_total_bytes) is not int or current_total_bytes < current_offset_value or (current_expected_size is not None and current_total_bytes != current_expected_size):
            raise ValueError('diff 크기 또는 응답 위치가 변경됐습니다. 처음부터 다시 보세요.')
        current_chunk_bytes = base64.b64decode(current_chunk_record['data_base64'], validate=True)
        if len(current_chunk_bytes) > 65536 or current_offset_value + len(current_chunk_bytes) > current_total_bytes or (not current_chunk_bytes and current_offset_value < current_total_bytes):
            raise ValueError('diff 응답 크기 오류')
        current_expected_next = current_offset_value + len(current_chunk_bytes)
        if current_chunk_record.get('next_offset') != (current_expected_next if current_expected_next < current_total_bytes else None):
            raise ValueError('diff 응답 이어보기 위치 오류')
        current_decode_warning = ''
        try:
            current_page_text = current_chunk_bytes.decode('utf-8')
        except UnicodeDecodeError as current_decode_error:
            if current_decode_error.reason == 'unexpected end of data' and current_decode_error.start > 0 and current_expected_next < current_total_bytes:
                current_chunk_bytes = current_chunk_bytes[:current_decode_error.start]
                current_page_text = current_chunk_bytes.decode('utf-8')
            else:
                current_page_text = current_chunk_bytes.decode('utf-8', errors='backslashreplace')
                current_decode_warning = ' · UTF-8이 아닌 바이트는 이스케이프 표시; 원본 바이트는 MCP에서 확인'
        current_end_offset = current_offset_value + len(current_chunk_bytes)
        current_next_offset = current_end_offset if current_end_offset < current_total_bytes else None
        current_cursor_value = {'job_id': current_job_identifier, 'next_offset': current_next_offset, 'size_bytes': current_total_bytes}
        current_page_message = f'바이트 {current_offset_value}~{current_end_offset} / {current_total_bytes}' + (' · 마지막 부분' if current_next_offset is None else ' · 다음 부분이 있습니다') + current_decode_warning
        return current_page_text, current_page_message, current_cursor_value
    except (KeyError, ValueError, TypeError, binascii.Error) as current_diff_error:
        raise ValueError('전체 diff 조회 실패: ' + str(current_diff_error)) from current_diff_error


def read_operations_capture_status(current_row_value, command):
    if not isinstance(current_row_value,(list,tuple)) or len(current_row_value)!=5 or not all(isinstance(current_item_value,str) for current_item_value in current_row_value):
        return '대기 기록을 확인할 수 없습니다.'
    if current_row_value[1]!='review-capture' or current_row_value[3]!='review-capture':
        return '캡처 대기 기록을 선택하면 접수 상태를 확인합니다.'
    current_capture_label,current_separator_value,current_request_identifier=current_row_value[4].partition(' · ')
    current_service_name={'맵':'map-review','캐릭터':'character-review'}.get(current_capture_label)
    if not current_separator_value or current_service_name is None or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',current_request_identifier):
        return '캡처 접수 신원을 확인할 수 없습니다.'
    try:
        current_result_value=command('hermes-agent','hermes-capture-status',{'request_id':current_request_identifier,'service':current_service_name})
        current_receipt_value=current_result_value.get('receipt') if isinstance(current_result_value,dict) else None
        current_job_value=current_result_value.get('job') if isinstance(current_result_value,dict) else None
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('state')!='accepted' or current_receipt_value.get('request_id')!=current_request_identifier or current_receipt_value.get('service')!=current_service_name or current_receipt_value.get('job_id')!=current_row_value[2] or not isinstance(current_job_value,dict):
            return '선택한 대기 기록과 접수 상태가 일치하지 않습니다. 다시 조회하세요.'
        current_status_name=current_job_value.get('status')
        current_status_label={'queued':'대기','running':'실행 중','completed':'완료','failed':'실패','cancelled':'취소','unknown':'확인 불가'}.get(current_status_name)
        if current_status_label is None or type(current_job_value.get('result_available')) is not bool:
            return '캡처 상태를 확인할 수 없습니다. 다시 조회하세요.'
        current_result_notice=' · 결과 확인 가능' if current_job_value['result_available'] else ''
        return current_capture_label+' 캡처 · '+current_status_label+current_result_notice+' · 접수 '+current_request_identifier+' · 작업 '+current_row_value[2]+' · 조회 시점 기준'
    except (OSError,ValueError,TypeError,KeyError,RuntimeError):
        return '캡처 상태 조회에 실패했습니다. 다시 조회하세요.'
