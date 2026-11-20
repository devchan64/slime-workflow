"""운영 대화와 공용 GPU 대기 기록을 구분해 읽는 이력 화면."""
from collections import Counter
from datetime import datetime, timezone
import html
import hashlib
import re

import gradio as gr

from tools.review.common.management_client import execute_remote_management_command
from tools.review.ui.gradio.hermes_agent_app import refresh_hermes_work_status, describe_unconfirmed_resume_error
from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES, SOURCE_HISTORY_AUDIO_SERVICES, SOURCE_HISTORY_SERVICE_ALIASES
from tools.review.domains.hermes_agent.audio_operations import sanitize_hermes_source_history
from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS




def resolve_operations_queue_identity(current_service_name):
    """검증된 전용 대기열 이름을 반환하고 공용 image 소유권은 추정하지 않는다."""
    current_shared_services={'kimodo','dwpose','wan22-vace','wan22-animate2','qwen-21','qwen-21-circular','mannequin-generator','billboard-generator','prop-generator','vegetation-generator','building-generator','expression','seamless-tile','floor-tile'}
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    if current_service_name in current_shared_services or current_service_name in FLUX_IMAGE_PROFILE_RECORDS:
        return None
    if current_service_name=='wan22-fun-control':
        return 'wan-fun'
    return current_service_name



def read_operations_verified_source(current_service_name,current_source_value):
    """GPU 관측 응답에서 허용된 공유 대기열의 원 서비스만 표시한다."""
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    current_image_sources={'kimodo','dwpose','wan22-vace','wan22-animate2','qwen-21','qwen-21-circular','mannequin-generator','prop-generator','vegetation-generator','expression','seamless-tile','floor-tile','billboard-generator','building-generator'}
    if current_service_name=='image' and isinstance(current_source_value,str) and current_source_value in current_image_sources:return current_source_value
    if current_service_name=='flux-image' and isinstance(current_source_value,str) and current_source_value in FLUX_IMAGE_PROFILE_RECORDS:return current_source_value
    from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
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


from tools.review.domains.hermes_agent.history_catalog import HERMES_HISTORY_STATUS_LABELS as OPERATIONS_HISTORY_STATUS_LABELS, normalize_hermes_history_status


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


def validate_operations_history_link(current_job_identifier,current_session_identifier):
    """링크로 받은 작업과 세션의 형식만 검증하고 실제 존재는 별도로 확인한다."""
    current_job_value=current_job_identifier if isinstance(current_job_identifier,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier) else ''
    current_session_value=current_session_identifier if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier) else ''
    return current_job_value,current_session_value


def read_operations_history_overview(current_search_text='', current_status_filter='전체', current_selected_session=None):
    """각 원본을 독립 조회하고 정확한 서비스·작업 ID만 연결한다."""
    current_search_value=(current_search_text or '').strip().casefold()
    current_checked_time=datetime.now(timezone.utc).isoformat()
    current_errors_list=[]
    try:
        current_session_result=execute_remote_management_command('hermes-agent','hermes-session-list',{})
        current_session_records=current_session_result['sessions']
        current_session_choices=[(str(item['updated_at'])+' · '+str(item['id'])[:8]+' · '+str(item['message_count'])+'개 메시지',item['id']) for item in current_session_records]
        current_session_notice='세션 '+str(len(current_session_choices))+'개'+(' · 최근 100개만 표시' if current_session_result.get('truncated') else '')
        current_unreadable_count=current_session_result.get('unreadable_count',0)
        if type(current_unreadable_count) is not int or current_unreadable_count<0:raise ValueError('세션 누락 수 오류')
        if current_unreadable_count:current_session_notice+=' · 읽을 수 없는 세션 '+str(current_unreadable_count)+'개 제외'
        current_session_matches=[item for item in current_session_records if item['id']==current_selected_session]
        if current_selected_session and not current_session_matches and isinstance(current_selected_session,str) and re.fullmatch(r'[a-f0-9]{32}',current_selected_session):
            try:
                current_old_session=execute_remote_management_command('hermes-agent','hermes-session-read',{'session_id':current_selected_session})
                if not isinstance(current_old_session,dict) or current_old_session.get('id')!=current_selected_session or not isinstance(current_old_session.get('updated_at'),str) or not isinstance(current_old_session.get('messages'),list):raise ValueError('이전 세션 오류')
                current_session_choices.append((current_old_session['updated_at']+' · '+current_selected_session[:8]+' · '+str(len(current_old_session['messages']))+'개 메시지 · 이전 세션',current_selected_session))
                current_session_matches=[current_old_session]
                current_session_notice+=' · 선택한 이전 세션 포함'
            except (OSError,ValueError,KeyError,TypeError,RuntimeError):
                pass
        current_session_value=current_selected_session if isinstance(current_selected_session,str) and re.fullmatch(r'[a-f0-9]{32}',current_selected_session) and len(current_session_matches)==1 else None
        if current_selected_session and current_session_value is None:
            current_session_notice+=' · 이전 선택을 목록에서 유일하게 확인할 수 없습니다.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as current_session_error:
        current_session_choices=[]
        current_session_value=None
        current_session_notice='세션 조회 불가 · 관리 게이트웨이를 확인하세요.'
        current_errors_list.append('세션')
    current_management_record=None
    try:
        current_management_record=execute_remote_management_command('hermes-agent','hermes-management-status',{})
        current_queue_record=current_management_record['queue']
        if current_queue_record.get('status')!='available' or not isinstance(current_queue_record.get('jobs'),list):
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
        current_errors_list.append('대기열')
    current_reservation_index,current_unmatched_record,current_reservation_rows,current_reservation_notice=summarize_operations_reservation_snapshot(current_management_record)
    if current_reservation_index is None:current_errors_list.append('예약')
    try:
        current_history_record=execute_remote_management_command('hermes-agent','hermes-history',{})
        current_history_records=current_history_record['records']
        if not isinstance(current_history_records,list):raise ValueError('이력 형식 오류')
        current_history_ids=Counter(item.get('id') for item in current_history_records if isinstance(item,dict) and isinstance(item.get('id'),str))
        current_history_rows=[]
        for current_job_record in current_history_records:
            if not isinstance(current_job_record,dict) or not isinstance(current_job_record.get('id'),str):
                raise ValueError('작업 이력 형식 오류')
            current_job_identifier=current_job_record['id']
            current_status_record=current_job_record.get('status') or {}
            current_request_record=current_job_record.get('request') or {}
            current_status_value=current_status_record.get('status') if isinstance(current_status_record,dict) else None
            current_status_name=normalize_hermes_history_status(current_status_value)
            current_status_label=OPERATIONS_HISTORY_STATUS_LABELS[current_status_name]
            current_prompt_value=current_request_record.get('prompt','') if isinstance(current_request_record,dict) else ''
            current_prompt_value=current_prompt_value if isinstance(current_prompt_value,str) else ''
            if current_status_filter!='전체' and current_status_name!=current_status_filter:continue
            if current_search_value and current_search_value not in (current_job_identifier+' '+current_prompt_value).casefold():continue
            if current_history_ids[current_job_identifier]!=1:current_queue_label='연결 불확실 · 중복 작업 ID'
            else:current_queue_label=label_operations_dedicated_queue(current_queue_counts,'hermes-agent',current_job_identifier)
            current_reservation_label=label_operations_reservation_record(current_reservation_index,current_unmatched_record,'hermes-agent',current_job_identifier) if current_history_ids[current_job_identifier]==1 else '연결 불확실 · 중복 작업 ID'
            current_history_rows.append([current_job_identifier,current_status_label,current_queue_label,current_prompt_value[:120],current_reservation_label])
        current_history_notice='Hermes 작업 '+str(len(current_history_rows))+'건 · 최근 100건 범위 내 검색. 전체 검색은 이전 작업 찾기를 이용하세요.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        current_history_rows=[]
        current_history_notice='Hermes 작업 이력 조회 불가 · 관리 게이트웨이를 확인하세요.'
        current_errors_list.append('작업 이력')
    current_summary_text='확인 시각 '+current_checked_time+' · '+('일부 조회 불가: '+', '.join(current_errors_list) if current_errors_list else '각 기록을 독립적으로 조회했습니다.')
    return gr.update(choices=current_session_choices,value=current_session_value),current_session_notice,current_history_rows,current_history_notice,current_queue_rows,current_queue_notice,current_summary_text,current_reservation_rows,current_reservation_notice


def read_operations_job_history_page(current_search_text,current_status_filter,current_page_record=None,current_direction='first'):
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
        current_result=execute_remote_management_command('hermes-agent','hermes-history',current_request)
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
            current_management=execute_remote_management_command('hermes-agent','hermes-management-status',{})
            current_queue=current_management['queue']
            if current_queue.get('status')!='available' or not isinstance(current_queue.get('jobs'),list) or any(not isinstance(item,dict) or not isinstance(item.get('service'),str) or not isinstance(item.get('id'),str) for item in current_queue['jobs']):raise ValueError('대기열 오류')
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
        return current_rows,current_notice,current_page,gr.update(interactive=current_next is not None),gr.update(interactive=current_offset>0)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        return [],'작업 목록을 확인할 수 없거나 변경됐습니다. 처음부터 다시 조회하세요.',None,gr.update(interactive=False),gr.update(interactive=False)


def read_linked_operations_history_page(current_job_identifier,current_status_filter):
    """유효한 작업 링크에 한해 전체 이력 검색의 첫 페이지를 연다."""
    current_job_value,_=validate_operations_history_link(current_job_identifier,'')
    if not current_job_value:
        return [],'작업 목록을 조회하세요.',None,gr.update(interactive=False),gr.update(interactive=False),gr.update(open=False)
    current_rows_value,current_notice_value,current_page_value,current_older_value,current_newer_value=read_operations_job_history_page(current_job_value,current_status_filter)
    if current_page_value is not None and not any(current_row_value[0]==current_job_value for current_row_value in current_rows_value):
        current_notice_value+=' 이 페이지에서 링크한 작업 ID가 확인되지 않습니다. 지시문에 ID를 언급한 다른 작업이 포함될 수 있으므로 작업 ID를 확인하고 다음 페이지도 살펴보세요.'
    return current_rows_value,current_notice_value,current_page_value,current_older_value,current_newer_value,gr.update(open=True)


def read_older_operations_job_history(current_search_text,current_status_filter,current_page_record):
    return read_operations_job_history_page(current_search_text,current_status_filter,current_page_record,'older')


def read_newer_operations_job_history(current_search_text,current_status_filter,current_page_record):
    return read_operations_job_history_page(current_search_text,current_status_filter,current_page_record,'newer')


def read_operations_session_page(current_query_text,current_page_record=None,current_direction='first'):
    """최근 100개 밖의 세션을 ID로 찾거나 페이지별로 조회한다."""
    current_query=(current_query_text or '').strip()
    try:
        if len(current_query)>100 or any(ord(char)<32 for char in current_query):raise ValueError('세션 검색 오류')
        current_offset=0
        current_request={'offset':0,'limit':30}
        if current_query:current_request['query']=current_query
        if current_direction!='first':
            if current_direction not in ('older','newer') or not isinstance(current_page_record,dict) or current_page_record.get('query')!=current_query:raise ValueError('검색 조건 오류')
            current_offset=current_page_record.get('next_offset') if current_direction=='older' else max(0,current_page_record.get('offset',0)-30)
            current_snapshot=current_page_record.get('snapshot')
            if type(current_offset) is not int or current_offset<0 or not isinstance(current_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot):raise ValueError('페이지 오류')
            current_request.update(offset=current_offset,snapshot=current_snapshot)
        current_result=execute_remote_management_command('hermes-agent','hermes-session-list',current_request)
        if not isinstance(current_result,dict) or not isinstance(current_result.get('sessions'),list) or type(current_result.get('total')) is not int or current_result.get('offset')!=current_offset:raise ValueError('세션 응답 오류')
        current_total=current_result['total']
        current_records=current_result['sessions']
        current_expected=min(30,max(0,current_total-current_offset))
        current_next=current_offset+current_expected if current_offset+current_expected<current_total else None
        current_snapshot=current_result.get('snapshot')
        if current_total<0 or current_offset>current_total or len(current_records)!=current_expected or current_result.get('next_offset')!=current_next or not isinstance(current_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot) or (current_direction!='first' and current_snapshot!=current_request['snapshot']):raise ValueError('세션 페이지 오류')
        current_rows=[]
        current_seen=set()
        for current_item in current_records:
            if not isinstance(current_item,dict) or not isinstance(current_item.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',current_item['id']) or current_item['id'] in current_seen or not isinstance(current_item.get('updated_at'),str) or type(current_item.get('message_count')) is not int or current_item['message_count']<0:raise ValueError('세션 항목 오류')
            current_seen.add(current_item['id'])
            current_rows.append([current_item['updated_at'],current_item['id'],str(current_item['message_count'])])
        current_page={'query':current_query,'offset':current_offset,'next_offset':current_next,'snapshot':current_snapshot}
        current_notice='검색된 세션 '+str(current_total)+'개 · '+str(current_offset+1 if current_rows else 0)+'–'+str(current_offset+len(current_rows))+'번째. 행을 선택해 지시 이력을 여세요.'
        current_unreadable_count=current_result.get('unreadable_count',0)
        if type(current_unreadable_count) is not int or current_unreadable_count<0:raise ValueError('세션 누락 수 오류')
        if current_unreadable_count:current_notice+=' 읽을 수 없는 세션 '+str(current_unreadable_count)+'개는 검색 결과에서 제외했습니다.'
        return current_rows,current_notice,current_page,gr.update(interactive=current_next is not None),gr.update(interactive=current_offset>0)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        return [],'세션 목록을 확인할 수 없거나 변경됐습니다. 처음부터 다시 조회하세요.',None,gr.update(interactive=False),gr.update(interactive=False)


def read_older_operations_session_page(current_query_text,current_page_record):
    return read_operations_session_page(current_query_text,current_page_record,'older')


def read_newer_operations_session_page(current_query_text,current_page_record):
    return read_operations_session_page(current_query_text,current_page_record,'newer')


def select_operations_older_session(current_session_rows,current_select_event:gr.SelectData):
    """선택한 세션을 원본에서 다시 확인하고 기존 세션 선택기에 추가한다."""
    current_index=current_select_event.index
    if isinstance(current_index,(tuple,list)):current_index=current_index[0] if current_index else None
    if type(current_index) is not int or not isinstance(current_session_rows,list) or not 0<=current_index<len(current_session_rows):raise gr.Error('세션을 다시 선택하세요.')
    current_row=current_session_rows[current_index]
    if not isinstance(current_row,(tuple,list)) or len(current_row)!=3 or not isinstance(current_row[1],str) or not re.fullmatch(r'[a-f0-9]{32}',current_row[1]):raise gr.Error('세션 ID를 확인할 수 없습니다.')
    current_session_id=current_row[1]
    current_session=execute_remote_management_command('hermes-agent','hermes-session-read',{'session_id':current_session_id})
    if not isinstance(current_session,dict) or current_session.get('id')!=current_session_id or not isinstance(current_session.get('updated_at'),str) or not isinstance(current_session.get('messages'),list):raise gr.Error('세션 원본을 확인할 수 없습니다.')
    current_recent=execute_remote_management_command('hermes-agent','hermes-session-list',{})
    if not isinstance(current_recent,dict) or not isinstance(current_recent.get('sessions'),list):raise gr.Error('최근 세션 목록을 확인할 수 없습니다.')
    current_choices=[]
    current_ids=set()
    for current_entry in current_recent['sessions']:
        if not isinstance(current_entry,dict) or not isinstance(current_entry.get('id'),str) or not re.fullmatch(r'[a-f0-9]{32}',current_entry['id']) or current_entry['id'] in current_ids or not isinstance(current_entry.get('updated_at'),str) or type(current_entry.get('message_count')) is not int:raise gr.Error('최근 세션 목록을 확인할 수 없습니다.')
        current_ids.add(current_entry['id'])
        current_choices.append((current_entry['updated_at']+' · '+current_entry['id'][:8]+' · '+str(current_entry['message_count'])+'개 메시지',current_entry['id']))
    if current_session_id not in current_ids:current_choices.append((current_session['updated_at']+' · '+current_session_id[:8]+' · '+str(len(current_session['messages']))+'개 메시지 · 이전 세션',current_session_id))
    return gr.update(choices=current_choices,value=current_session_id),'이전 세션을 선택했습니다. 세션 지시 조회를 누르세요.'


def read_operations_session_history(current_session_identifier):
    """세션에서 지시와 해당 Hermes 작업의 기록 상태를 확인한다."""
    if not isinstance(current_session_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):
        raise gr.Error('조회할 세션을 선택하세요.')
    current_session_record=execute_remote_management_command('hermes-agent','hermes-session-view',{'session_id':current_session_identifier})
    if not isinstance(current_session_record,dict) or current_session_record.get('id')!=current_session_identifier:
        raise gr.Error('세션을 확인할 수 없습니다.')
    current_message_records=current_session_record.get('messages')
    if not isinstance(current_message_records,list):raise gr.Error('세션 메시지를 확인할 수 없습니다.')
    current_message_rows=[]
    for current_message_record in current_message_records:
        current_job_record=current_message_record.get('job') or {}
        current_status_record=current_job_record.get('status') or {}
        current_message_rows.append([str(current_message_record.get('created_at') or '미제공'),str(current_message_record.get('text',''))[:200],str(current_message_record.get('job_id') or '접수 확인 필요'),str(current_status_record.get('status','unknown')), '일부 문맥만 전달' if current_message_record.get('context_truncated') else ''])
    current_notice_text='세션 메시지 '+str(len(current_message_rows))+'건'+(' · 최근 일부만 표시' if current_session_record.get('truncated') else '')+' · 지시 요약은 최대 200자입니다.'
    current_link_html='<a href="/management/frame/hermes-agent/?session='+html.escape(current_session_identifier,quote=True)+'" target="_blank" rel="noopener">이 세션의 운영 대화 열기</a>'
    return current_message_rows,current_notice_text,current_link_html




def read_operations_session_history_page(current_session_identifier,current_page_state=None):
    """선택 세션의 이전 지시를 같은 기록 버전에서 20개씩 확인한다."""
    if not isinstance(current_session_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):
        raise gr.Error('조회할 세션을 선택하세요.')
    current_payload_record={'session_id':current_session_identifier}
    if current_page_state is not None:
        if not isinstance(current_page_state,dict) or current_page_state.get('session_id')!=current_session_identifier or type(current_page_state.get('offset')) is not int or not isinstance(current_page_state.get('snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_page_state['snapshot']):
            return [],'세션이 바뀌었습니다. 처음부터 다시 조회하세요.','',None,gr.update(interactive=False),gr.update(interactive=False)
        current_payload_record.update({'offset':current_page_state['offset'],'snapshot':current_page_state['snapshot']})
    try:
        current_session_record=execute_remote_management_command('hermes-agent','hermes-session-view',current_payload_record)
        if not isinstance(current_session_record,dict) or current_session_record.get('id')!=current_session_identifier or not isinstance(current_session_record.get('messages'),list):raise ValueError('세션 오류')
        if current_page_state is None and 'offset' in current_session_record and (type(current_session_record['offset']) is not int or current_session_record['offset']!=0):raise ValueError('첫 페이지 위치 오류')
        if current_page_state is not None and (current_session_record.get('offset')!=current_payload_record['offset'] or current_session_record.get('snapshot')!=current_payload_record['snapshot']):raise ValueError('페이지 식별 정보 불일치')
        current_messages_value=current_session_record['messages']
        current_rows_value=[]
        for current_message_value in current_messages_value:
            if not isinstance(current_message_value,dict):raise ValueError('메시지 오류')
            current_job_value=current_message_value.get('job') or {}
            current_status_value=current_job_value.get('status') or {}
            if not isinstance(current_status_value,dict):raise ValueError('상태 오류')
            current_rows_value.append([str(current_message_value.get('created_at') or '미제공'),str(current_message_value.get('text',''))[:200],str(current_message_value.get('job_id') or '접수 확인 필요'),str(current_status_value.get('status','unknown')),'일부 문맥만 전달' if current_message_value.get('context_truncated') else ''])
        current_next_value=current_session_record.get('next_offset')
        current_snapshot_value=current_session_record.get('snapshot')
        current_start_offset=current_payload_record.get('offset',0)
        if current_next_value is not None and (type(current_next_value) is not int or current_next_value!=current_start_offset+len(current_rows_value) or current_next_value<=current_start_offset or not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)):
            raise ValueError('페이지 오류')
        current_page_state={'session_id':current_session_identifier,'offset':current_start_offset,'next_offset':current_next_value,'snapshot':current_snapshot_value} if isinstance(current_snapshot_value,str) and re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value) else None
        current_notice_value='최근부터 '+str(current_start_offset+1 if current_rows_value else 0)+'~'+str(current_start_offset+len(current_rows_value))+'번째 지시 · 요약은 최대 200자입니다.'
        if current_next_value is not None:current_notice_value+=' 이전 지시가 더 있습니다.'
        elif current_session_record.get('truncated') is True:current_notice_value+=' 이전 지시가 있지만 현재 게이트웨이는 페이지 조회를 지원하지 않습니다.'
        current_link_value='<a href="/management/frame/hermes-agent/?session='+html.escape(current_session_identifier,quote=True)+'" target="_blank" rel="noopener">이 세션의 운영 대화 열기</a>'
        return current_rows_value,current_notice_value,current_link_value,current_page_state,gr.update(interactive=current_next_value is not None),gr.update(interactive=current_page_state is not None and current_start_offset>0)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        return [],'세션 이력을 확인할 수 없거나 조회 중 변경됐습니다. 처음부터 다시 조회하세요.','',None,gr.update(interactive=False),gr.update(interactive=False)


def read_next_operations_session_history(current_session_identifier,current_page_state):
    if current_page_state is None:
        return [],'먼저 세션 지시를 조회하세요.','',None,gr.update(interactive=False),gr.update(interactive=False)
    if not isinstance(current_page_state,dict) or type(current_page_state.get('next_offset')) is not int:
        return [],'이전 지시가 없습니다.','',None,gr.update(interactive=False),gr.update(interactive=False)
    return read_operations_session_history_page(current_session_identifier,{**current_page_state,'offset':current_page_state['next_offset']})


def read_newer_operations_session_history(current_session_identifier,current_page_state):
    """같은 세션과 기록 확인값에서 더 최근 지시 페이지로 돌아간다."""
    if not isinstance(current_page_state,dict) or type(current_page_state.get('offset')) is not int or current_page_state['offset']<=0:
        return [],'더 최근 지시가 없습니다.','',None,gr.update(interactive=False),gr.update(interactive=False)
    return read_operations_session_history_page(current_session_identifier,{**current_page_state,'offset':max(0,current_page_state['offset']-20)})


def collect_operations_session_page(current_session_identifier,current_page_state,current_request_token,current_direction_name):
    """지시 페이지와 요청 식별값을 묶어 늦은 결과를 구분한다."""
    current_readers={'first':lambda:read_operations_session_history_page(current_session_identifier),'older':lambda:read_next_operations_session_history(current_session_identifier,current_page_state),'newer':lambda:read_newer_operations_session_history(current_session_identifier,current_page_state)}
    try:
        current_result_values=current_readers[current_direction_name]()
    except (gr.Error,OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError):
        current_result_values=([],'세션 이력을 확인할 수 없습니다. 처음부터 다시 조회하세요.','',None,gr.update(interactive=False),gr.update(interactive=False))
    return {'session_id':current_session_identifier,'token':current_request_token,'result':current_result_values}


def render_operations_session_page(current_session_identifier,current_request_token,current_result_record):
    """요청 후 세션이나 조회가 바뀌면 화면을 갱신하지 않는다."""
    if not isinstance(current_result_record,dict) or (current_result_record.get('session_id'),current_result_record.get('token'))!=(current_session_identifier,current_request_token):
        return (gr.skip(),)*10
    current_result_values=current_result_record.get('result')
    if not isinstance(current_result_values,(list,tuple)) or len(current_result_values)!=6:
        return (gr.skip(),)*10
    return (*current_result_values,[],'표시된 지시의 접수 기록을 조회하세요.','',gr.update(interactive=True))


def select_operations_session_job_link(current_session_identifier,current_history_rows,current_select_event:gr.SelectData):
    """선택 행에서 안전한 세션·작업 ID만 대화 링크로 만든다."""
    if not isinstance(current_session_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):raise gr.Error('세션을 다시 선택하세요.')
    current_selected_index=current_select_event.index
    if isinstance(current_selected_index,(tuple,list)):current_selected_index=current_selected_index[0] if current_selected_index else None
    if type(current_selected_index) is not int or not isinstance(current_history_rows,list) or not 0<=current_selected_index<len(current_history_rows):raise gr.Error('지시를 다시 선택하세요.')
    current_selected_row=current_history_rows[current_selected_index]
    if not isinstance(current_selected_row,(list,tuple)) or len(current_selected_row)!=5:raise gr.Error('지시 행을 확인할 수 없습니다.')
    current_job_identifier=current_selected_row[2]
    current_session_url='/management/frame/hermes-agent/?session='+html.escape(current_session_identifier,quote=True)
    if not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier):
        return '<a href="'+current_session_url+'" target="_blank" rel="noopener">이 세션의 운영 대화 열기</a><p>연결된 작업 ID를 확인할 수 없습니다.</p>'
    return '<a href="'+current_session_url+'&amp;job='+html.escape(current_job_identifier,quote=True)+'" target="_blank" rel="noopener">이 작업을 운영 대화에서 열기</a><p>대화에서 세션 소속과 완료·중복 상태를 다시 확인합니다.</p>'



def read_verified_operations_session_instruction(current_session_identifier,current_history_rows,current_page_state,current_select_event:gr.SelectData):
    """선택한 페이지의 기록 버전을 다시 확인하고 지시 원문을 표시한다."""
    current_index_value=current_select_event.index
    if isinstance(current_index_value,(tuple,list)):current_index_value=current_index_value[0] if current_index_value else None
    if not isinstance(current_page_state,dict) or current_page_state.get('session_id')!=current_session_identifier or type(current_page_state.get('offset')) is not int or current_page_state['offset']<0 or not isinstance(current_page_state.get('snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_page_state['snapshot']):
        raise gr.Error('세션 지시를 다시 조회하세요.')
    if type(current_index_value) is not int or not isinstance(current_history_rows,list) or not 0<=current_index_value<len(current_history_rows):raise gr.Error('지시를 다시 선택하세요.')
    try:
        current_payload_value={'session_id':current_session_identifier,'offset':current_page_state['offset'],'snapshot':current_page_state['snapshot']}
        current_record_value=execute_remote_management_command('hermes-agent','hermes-session-view',current_payload_value)
        if not isinstance(current_record_value,dict) or current_record_value.get('id')!=current_session_identifier or current_record_value.get('offset')!=current_page_state['offset'] or current_record_value.get('snapshot')!=current_page_state['snapshot'] or not isinstance(current_record_value.get('messages'),list) or current_index_value>=len(current_record_value['messages']):raise ValueError('페이지 불일치')
        current_message_value=current_record_value['messages'][current_index_value]
        if not isinstance(current_message_value,dict) or not isinstance(current_message_value.get('text'),str):raise ValueError('지시 원문 오류')
        current_expected_row=[str(current_message_value.get('created_at') or '미제공'),current_message_value['text'][:200],str(current_message_value.get('job_id') or '접수 확인 필요')]
        if not isinstance(current_history_rows[current_index_value],(list,tuple)) or list(current_history_rows[current_index_value][:3])!=current_expected_row:raise ValueError('표시 행 불일치')
        return select_operations_session_job_link(current_session_identifier,current_history_rows,current_select_event),current_message_value['text']
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,AttributeError) as current_error_value:
        raise gr.Error('지시 원문을 확인할 수 없습니다. 세션 지시를 다시 조회하세요.') from current_error_value



def select_operations_session_instruction(current_session_identifier,current_history_rows,current_page_state,current_select_event:gr.SelectData):
    """확인에 실패해도 이전 지시 원문과 작업 링크를 지운다."""
    try:
        return read_verified_operations_session_instruction(current_session_identifier,current_history_rows,current_page_state,current_select_event)
    except gr.Error:
        return '', '지시를 확인할 수 없습니다. 세션 지시를 다시 조회하세요.'


def prepare_operations_instruction_selection(current_session_identifier,current_history_rows,current_page_state,current_select_event:gr.SelectData):
    """선택 순간의 세션·페이지·행과 새 식별값을 고정한다."""
    current_request_token=create_cleanup_preview_token()
    current_selected_index=current_select_event.index
    if isinstance(current_selected_index,(tuple,list)):current_selected_index=current_selected_index[0] if current_selected_index else None
    return current_request_token,{'session_id':current_session_identifier,'page':current_page_state,'rows':current_history_rows,'index':current_selected_index,'token':current_request_token},'', '지시를 확인하고 있습니다.'


def collect_operations_instruction_selection(current_selection_record):
    """고정된 행의 원문을 원본 세션에서 다시 확인한다."""
    from types import SimpleNamespace
    if not isinstance(current_selection_record,dict):return None
    current_link_value,current_text_value=select_operations_session_instruction(current_selection_record.get('session_id'),current_selection_record.get('rows'),current_selection_record.get('page'),SimpleNamespace(index=current_selection_record.get('index')))
    return {**current_selection_record,'link':current_link_value,'text':current_text_value}


def render_operations_instruction_selection(current_session_identifier,current_page_state,current_request_token,current_result_record):
    """요청 후 세션·페이지·선택이 변경된 원문은 표시하지 않는다."""
    if not isinstance(current_result_record,dict) or (current_result_record.get('session_id'),current_result_record.get('page'),current_result_record.get('token'))!=(current_session_identifier,current_page_state,current_request_token):
        return gr.skip(),gr.skip()
    if not isinstance(current_result_record.get('link'),str) or not isinstance(current_result_record.get('text'),str):return gr.skip(),gr.skip()
    return current_result_record['link'],current_result_record['text']


def read_operations_session_receipts(current_session_identifier,current_page_state=None):
    """대화 카드의 접수 ID 규칙과 영수증을 비교하며 작업을 실행하지 않는다."""
    import hashlib
    if not isinstance(current_session_identifier, str) or not re.fullmatch(r'[a-f0-9]{32}', current_session_identifier):
        raise gr.Error('조회할 세션을 선택하세요.')
    current_request_payload={'session_id':current_session_identifier}
    if current_page_state is not None:
        if not isinstance(current_page_state,dict) or current_page_state.get('session_id')!=current_session_identifier or type(current_page_state.get('offset')) is not int or current_page_state['offset']<0 or not isinstance(current_page_state.get('snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_page_state['snapshot']):
            raise ValueError('현재 세션 지시 페이지를 다시 조회하세요.')
        current_request_payload.update(offset=current_page_state['offset'],snapshot=current_page_state['snapshot'])
    current_session_record = execute_remote_management_command('hermes-agent', 'hermes-session-view', current_request_payload)
    if not isinstance(current_session_record,dict) or current_session_record.get('id')!=current_session_identifier:
        raise ValueError('세션이 일치하지 않거나 확인되지 않습니다.')
    if current_page_state is None and 'offset' in current_session_record and (type(current_session_record['offset']) is not int or current_session_record['offset']!=0):
        raise ValueError('첫 세션 지시 페이지가 아닙니다.')
    if current_page_state is not None and (current_session_record.get('id')!=current_session_identifier or current_session_record.get('offset')!=current_page_state['offset'] or current_session_record.get('snapshot')!=current_page_state['snapshot']):
        raise ValueError('세션 지시 페이지가 변경됐습니다.')
    current_messages = current_session_record.get('messages')
    if not isinstance(current_messages, list):
        raise gr.Error('세션 메시지를 확인할 수 없습니다.')
    current_job_counts = Counter(item.get('job_id') for item in current_messages if isinstance(item, dict) and isinstance(item.get('job_id'), str))
    current_kind_values = ('kimodo', 'flux', 'translation', 'audio', 'video', 'writer', 'field', 'city', 'effect', 'billboard', 'building', 'sprite', 'model_preparation', 'kimodo_resume', 'flux_resume', 'video_resume')
    current_receipt_cache = {}
    current_rows = []
    current_model_receipt_rows = []
    current_kimodo_resume_rows = []
    current_flux_resume_rows = []
    current_video_resume_rows = []
    current_skipped = 0
    for current_message in current_messages:
        if not isinstance(current_message, dict):
            current_skipped += 1
            continue
        current_job_id = current_message.get('job_id')
        current_job = current_message.get('job') or {}
        if not isinstance(current_job, dict):
            current_skipped += 1
            continue
        current_answer = current_job.get('final_response')
        if not isinstance(current_answer, str):
            continue
        current_kinds = [kind for kind in current_kind_values if 'HERMES_' + kind.upper() + '_PROPOSAL' in current_answer]
        if not current_kinds:
            continue
        current_job_status = current_job.get('status')
        current_job_unique=current_message.get('session_job_unique')
        if (not isinstance(current_job_id, str) or current_job_counts[current_job_id] != 1
                or (current_job_unique is not None and current_job_unique is not True)
                or ((current_page_state is not None or current_session_record.get('truncated') is True) and current_job_unique is not True)
                or current_job.get('final_response_truncated') or not isinstance(current_job_status, dict) or current_job_status.get('status') != 'completed'):
            current_skipped += 1
            continue
        for current_kind in current_kinds:
            current_seed = current_session_identifier + ':' + current_job_id + ('' if current_kind == 'kimodo' else ':' + current_kind)
            current_request_id = 'chat_' + hashlib.sha256(current_seed.encode('utf-8')).hexdigest()
            try:
                current_proposal_command={'model_preparation':'hermes-model-preparation-proposal','kimodo_resume':'hermes-kimodo-resume-proposal','flux_resume':'hermes-flux-resume-proposal','video_resume':'hermes-video-resume-proposal'}.get(current_kind,'hermes-' + current_kind + '-proposal')
                current_proposal = execute_remote_management_command('hermes-agent', current_proposal_command, {'id': current_job_id})
                if current_proposal.get('job_id') != current_job_id or not isinstance(current_proposal.get('proposal'), dict):
                    raise ValueError('제안 확인 불가')
                current_service = {'kimodo':'kimodo', 'flux':'flux-image', 'translation':'prompt-translation', 'writer':'writer-agent'}.get(current_kind, current_kind)
                if current_kind=='flux':
                    current_service=current_proposal['proposal'].get('service','flux-image')
                if current_kind in ('audio', 'video', 'model_preparation'):
                    current_service = current_proposal['proposal'].get('service')
                    if not isinstance(current_service, str):
                        raise ValueError('서비스 확인 불가')
                if current_kind=='kimodo_resume':
                    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
                    current_target_job=current_proposal['proposal'].get('job_id')
                    current_target_fingerprint=current_proposal['proposal'].get('expected_resume_fingerprint')
                    if not validate_service_job_identifier('kimodo',current_target_job) or not isinstance(current_target_fingerprint,str) or not re.fullmatch(r'[a-f0-9]{64}',current_target_fingerprint):raise ValueError('Kimodo 재개 제안 대상 오류')
                    current_service='kimodo'
                    current_request_id='kimodo_resume_'+hashlib.sha256(('kimodo\0'+current_target_job+'\0'+current_target_fingerprint).encode()).hexdigest()
                    current_receipt=execute_remote_management_command('hermes-agent','hermes-kimodo-resume-receipt',{'request_id':current_request_id})
                    if not isinstance(current_receipt,dict) or current_receipt.get('request_id')!=current_request_id or current_receipt.get('state') not in ('not_found','accepted','unknown'):raise ValueError('Kimodo 재개 접수 확인 불가')
                    if current_receipt['state']!='not_found' and any(current_receipt.get(current_name)!=current_expected for current_name,current_expected in (('service','kimodo'),('job_id',current_target_job),('expected_resume_fingerprint',current_target_fingerprint))):raise ValueError('Kimodo 재개 접수 대상 불일치')
                    current_state={'not_found':'이 ID의 기록 없음','unknown':'접수 확인 필요','accepted':'접수 기록'}[current_receipt['state']]
                    current_target_id=current_target_job if current_receipt['state']=='accepted' else None
                elif current_kind in ('flux_resume','video_resume'):
                    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
                    current_service=current_proposal['proposal'].get('service')
                    if current_service not in (FLUX_IMAGE_PROFILE_RECORDS if current_kind=='flux_resume' else ('dwpose','wan22-animate2','wan22-vace','wan22-fun-control')):raise ValueError('재개 서비스 오류')
                    current_target_job=current_proposal['proposal'].get('job_id')
                    current_target_fingerprint=current_proposal['proposal'].get('expected_resume_fingerprint')
                    if not validate_service_job_identifier(current_service,current_target_job) or not isinstance(current_target_fingerprint,str) or not re.fullmatch(r'[a-f0-9]{64}',current_target_fingerprint):raise ValueError('FLUX 재개 제안 대상 오류')
                    current_request_id=current_kind+'_'+hashlib.sha256((current_service+'\0'+current_target_job+'\0'+current_target_fingerprint).encode()).hexdigest()
                    current_receipt=execute_remote_management_command('hermes-agent','hermes-'+('flux' if current_kind=='flux_resume' else 'video')+'-resume-receipt',{'request_id':current_request_id})
                    if not isinstance(current_receipt,dict) or current_receipt.get('request_id')!=current_request_id or current_receipt.get('state') not in ('not_found','accepted','unknown'):raise ValueError('FLUX 재개 접수 확인 불가')
                    if current_receipt['state']!='not_found' and any(current_receipt.get(current_name)!=current_expected for current_name,current_expected in (('service',current_service),('job_id',current_target_job),('expected_resume_fingerprint',current_target_fingerprint))):raise ValueError('FLUX 재개 접수 대상 불일치')
                    current_state={'not_found':'이 ID의 기록 없음','unknown':'접수 확인 필요','accepted':'접수 기록'}[current_receipt['state']]
                    current_target_id=current_target_job if current_receipt['state']=='accepted' else None
                elif current_kind=='model_preparation':
                    from tools.review.common.model_management_catalog import MODEL_PREPARATION_SERVICES
                    from tools.review.domains.hermes_agent.delegation_store import HERMES_DELEGATION_JOB_PATTERN
                    if current_service not in {current_name for _,current_name in MODEL_PREPARATION_SERVICES}:raise ValueError('모델 준비 서비스 오류')
                    current_receipt=execute_remote_management_command('hermes-agent','hermes-model-prepare-status',{'request_id':current_request_id,'service':current_service})
                    if not isinstance(current_receipt,dict) or current_receipt.get('request_id')!=current_request_id or current_receipt.get('service')!=current_service or current_receipt.get('state') not in ('not_found','accepted','unknown'):
                        raise ValueError('모델 준비 접수 확인 불가')
                    current_state={'not_found':'이 ID의 기록 없음','unknown':'접수 확인 필요','accepted':'접수 기록'}[current_receipt['state']]
                    current_target_id=current_receipt.get('job_id') if current_receipt['state']=='accepted' else None
                    if current_target_id is not None and (not isinstance(current_target_id,str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_target_id)):
                        raise ValueError('모델 준비 작업 ID 오류')
                elif current_kind in ('kimodo', 'field', 'city', 'effect', 'billboard', 'building', 'sprite'):
                    current_command = 'hermes-delegation-status' if current_kind == 'kimodo' else 'hermes-' + current_kind + '-receipt'
                    current_receipt = execute_remote_management_command('hermes-agent', current_command, {'request_id': current_request_id})
                    if not isinstance(current_receipt, dict) or current_receipt.get('state') not in ('not_found', 'accepted', 'unknown', 'completed'):
                        raise ValueError('접수 확인 불가')
                    if current_kind=='kimodo' and (current_receipt.get('request_id')!=current_request_id or current_receipt.get('service')!='kimodo'):
                        raise ValueError('Kimodo 접수 ID 또는 서비스 불일치')
                    if current_kind in ('city','field') and current_receipt['state'] in ('unknown','completed') and (current_receipt.get('request_id')!=current_request_id or current_receipt.get('map')!=current_proposal['proposal'].get('map') or not isinstance(current_receipt.get('map'),str)):
                        raise ValueError('맵 접수 ID 또는 맵 불일치')
                    current_state = {'not_found':'이 ID의 기록 없음', 'accepted':'접수 기록', 'unknown':'접수 확인 필요', 'completed':'저장 완료 기록'}[current_receipt['state']]
                    if current_kind in ('billboard','sprite') and current_receipt['state'] in ('unknown','completed'):
                        current_receipt_target=current_receipt.get('textures' if current_kind=='billboard' else 'path')
                        if current_receipt_target is not None:
                            if current_kind=='billboard':
                                current_change_values=current_proposal['proposal'].get('changes')
                                if not isinstance(current_change_values,list) or any(not isinstance(item,dict) or not isinstance(item.get('texture'),str) for item in current_change_values):raise ValueError('빌보드 제안 대상 오류')
                                current_proposal_target=sorted(item['texture'] for item in current_change_values)
                            else:current_proposal_target=current_proposal['proposal'].get('path')
                            if current_receipt_target!=current_proposal_target:raise ValueError('에셋 접수 대상 불일치')
                    if current_kind=='effect' and current_receipt['state'] in ('unknown','completed'):
                        current_effect_identifier=current_receipt.get('effect_id')
                        if current_effect_identifier is not None and current_effect_identifier!=current_proposal['proposal'].get('id'):raise ValueError('이펙트 접수 대상 불일치')
                    if current_kind=='building' and current_receipt['state']=='unknown':
                        current_receipt_texture=current_receipt.get('texture')
                        if current_receipt_texture is None:current_state+=' · 대상 미확인'
                        elif current_receipt_texture!=current_proposal['proposal'].get('texture'):raise ValueError('건물 접수 대상 불일치')
                    if current_receipt['state'] == 'completed':
                        if current_receipt.get('request_id')!=current_request_id or type(current_receipt.get('saved')) is not bool:
                            raise ValueError('저장 접수 ID 또는 결과 확인 불가')
                        current_state = '저장 완료 기록' if current_receipt['saved'] else '저장되지 않음'
                        if current_kind=='city' and current_receipt['saved']:current_state='도시 DB 저장 기록'
                        if current_kind=='building' and current_receipt['saved']:
                            current_receipt_texture=current_receipt.get('texture')
                            if current_receipt_texture is None:
                                current_state='건물 앵커 DB 저장 기록 · 대상 미확인'
                            elif current_receipt_texture!=current_proposal['proposal'].get('texture'):
                                raise ValueError('건물 접수 대상 불일치')
                            else:
                                current_state='건물 앵커 DB 저장 기록'
                    if current_kind=='effect' and current_receipt['state'] in ('unknown','completed') and current_receipt.get('effect_id') is None:current_state+=' · 대상 미확인'
                    if current_kind in ('billboard','sprite') and current_receipt['state'] in ('unknown','completed') and current_receipt.get('textures' if current_kind=='billboard' else 'path') is None:current_state+=' · 대상 미확인'
                    current_target_id = current_receipt.get('job_id') if current_receipt['state'] in ('accepted', 'completed') else None
                    if current_receipt['state'] == 'accepted' and not isinstance(current_target_id, str):
                        raise ValueError('작업 ID 확인 불가')
                elif current_page_state is not None:
                    current_receipt=execute_remote_management_command('hermes-agent','hermes-service-receipt',{'request_id':current_request_id,'service':current_service})
                    if not isinstance(current_receipt,dict) or current_receipt.get('request_id')!=current_request_id or current_receipt.get('state') not in ('not_found','accepted','unknown'):
                        raise ValueError('접수 확인 불가')
                    if current_receipt['state'] in ('accepted','unknown') and current_receipt.get('service')!=current_service:
                        raise ValueError('접수 서비스 불일치')
                    current_state={'not_found':'이 ID의 기록 없음','unknown':'접수 확인 필요','accepted':'접수 기록'}[current_receipt['state']]
                    current_target_id=current_receipt.get('job_id') if current_receipt['state']=='accepted' else None
                    if current_receipt['state']=='accepted' and not isinstance(current_target_id,str):raise ValueError('작업 ID 확인 불가')
                else:
                    current_command = {'flux':'hermes-flux-delegation-history', 'translation':'hermes-translation-history', 'audio':'hermes-audio-history', 'video':'hermes-video-history', 'writer':'hermes-writer-history'}[current_kind]
                    if current_kind=='flux' and current_service!='flux-image':
                        current_command='hermes-flux-profile-history'
                    current_cache_key = (current_command, current_service)
                    if current_cache_key not in current_receipt_cache:
                        current_payload = {'service': current_service} if current_kind in ('audio', 'video') or current_command=='hermes-flux-profile-history' else {}
                        current_receipt_cache[current_cache_key] = execute_remote_management_command('hermes-agent', current_command, current_payload)
                    current_history = current_receipt_cache[current_cache_key]
                    if not isinstance(current_history, dict) or not isinstance(current_history.get('records'), list) or type(current_history.get('truncated')) is not bool:
                        raise ValueError('접수 이력 확인 불가')
                    current_matches = [item for item in current_history['records'] if isinstance(item, dict) and item.get('request_id') == current_request_id and item.get('service') == current_service]
                    if len(current_matches) > 1:
                        current_state, current_target_id = '중복 접수 기록 · 확인 필요', None
                    elif not current_matches:
                        current_state, current_target_id = '최근 접수 목록에 없음 · 확인 필요', None
                    else:
                        current_receipt = current_matches[0]
                        if current_receipt.get('state') not in ('accepted', 'unknown'):
                            raise ValueError('접수 상태 확인 불가')
                        current_state = '접수 기록' if current_receipt['state'] == 'accepted' else '접수 확인 필요'
                        current_target_id = current_receipt.get('job_id') if current_receipt['state'] == 'accepted' else None
                        if current_receipt['state'] == 'accepted' and not isinstance(current_target_id, str):
                            raise ValueError('작업 ID 확인 불가')
                current_rows.append([current_job_id, current_service, current_request_id, current_state, current_target_id or ('해당 없음' if current_kind in ('field','city','effect','billboard','building','sprite') else '미확인')])
                if current_kind=='model_preparation':current_model_receipt_rows.append(current_rows[-1])
                if current_kind=='kimodo_resume':current_kimodo_resume_rows.append(current_rows[-1])
                if current_kind=='flux_resume':current_flux_resume_rows.append(current_rows[-1])
                if current_kind=='video_resume':current_video_resume_rows.append(current_rows[-1])
            except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
                current_rows.append([current_job_id, current_kind, current_request_id, '제안 또는 접수 조회 불가', '미확인'])
    current_management_record = None
    current_queue_counts = None
    current_source_counts = None
    if any(row[3] == '접수 기록' and row[4] != '미확인' for row in current_rows):
        try:
            current_management_record = execute_remote_management_command('hermes-agent', 'hermes-management-status', {})
            current_queue_record = current_management_record['queue']
            if current_queue_record.get('status') != 'available' or not isinstance(current_queue_record.get('jobs'), list):
                raise ValueError('대기열 조회 불가')
            current_queue_jobs = current_queue_record['jobs']
            if any(not isinstance(item, dict) or not isinstance(item.get('service'), str) or not isinstance(item.get('id'), str) for item in current_queue_jobs):
                raise ValueError('대기열 형식 오류')
            current_queue_counts = Counter((item['service'], item['id']) for item in current_queue_jobs)
            current_source_counts = Counter((item['service'],read_operations_verified_source(item['service'],item.get('source_service')),item['id']) for item in current_queue_jobs if read_operations_verified_source(item['service'],item.get('source_service')) is not None)
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError):
            current_queue_counts = None
    current_reservation_index, current_unmatched_record, _, _ = summarize_operations_reservation_snapshot(current_management_record)
    current_target_counts = Counter((row[1], row[4]) for row in current_rows if row[3] == '접수 기록' and row[4] != '미확인')
    for current_row in current_rows:
        if current_row[1] in ('city','field','effect','billboard','building','sprite'):
            current_row.extend(['GPU 작업 아님', 'GPU 예약 대상 아님'])
            continue
        if current_row[3] != '접수 기록' or current_row[4] == '미확인':
            current_row.extend(['작업 ID 미확인', '작업 ID 미확인'])
            continue
        current_target_key = (current_row[1], current_row[4])
        if current_target_counts[current_target_key] != 1:
            current_row.extend(['연결 불확실 · 중복 작업 ID', '연결 불확실 · 중복 작업 ID'])
            continue
        current_queue_service=resolve_operations_queue_identity(current_row[1])
        if current_queue_service is None:
            current_shared_name='flux-image' if current_row[1].startswith('flux-') else 'image'
            current_queue_label=label_operations_shared_queue_record(current_queue_counts,current_source_counts,current_shared_name,current_row[1],current_row[4])
            current_reservation_label=label_operations_shared_reservation_record(current_reservation_index,current_unmatched_record,current_shared_name,current_row[1],current_row[4])
        else:
            from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
            current_queue_key=(current_queue_service,current_row[4])
            if is_dedicated_gpu_source_verifiable(current_queue_service):
                current_queue_label=label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,current_queue_service,current_row[1],current_row[4])
                current_reservation_label=label_operations_verified_dedicated_reservation(current_reservation_index,current_unmatched_record,current_queue_service,current_row[1],current_row[4])
            else:
                current_queue_label=label_operations_dedicated_queue(current_queue_counts,*current_queue_key,current_missing_label='대기 기록 없음 · 시점 기준')
                current_reservation_label=label_operations_reservation_record(current_reservation_index,current_unmatched_record,*current_queue_key)
        current_row.extend([current_queue_label, current_reservation_label])
    current_observed_time = str(current_management_record.get('queried_at', '확인 불가')) if isinstance(current_management_record, dict) else '조회 불가'
    for current_row in current_rows:
        if current_row[1] != 'writer-agent':
            current_row.append('해당 없음')
            continue
        if current_row[3] != '접수 기록' or current_row[4] == '미확인' or current_target_counts[(current_row[1],current_row[4])] != 1:
            current_row.append('접수 확인 필요')
            continue
        current_apply_seed=current_session_identifier+':'+current_row[0]+':writer'
        current_apply_id='chat_apply_'+hashlib.sha256(current_apply_seed.encode('utf-8')).hexdigest()
        try:
            current_apply_receipt=execute_remote_management_command('hermes-agent','hermes-writer-apply-status',{'request_id':current_apply_id})
            if not isinstance(current_apply_receipt,dict):raise ValueError('적용 기록 오류')
            current_apply_state=current_apply_receipt.get('state')
            if current_apply_state=='not_found':
                current_apply_label='이 ID의 적용 기록 없음'
            elif current_apply_state in ('completed','unknown') and (current_apply_receipt.get('request_id'),current_apply_receipt.get('writer_request_id'),current_apply_receipt.get('job_id'))==(current_apply_id,current_row[2],current_row[4]):
                current_apply_label='적용 완료 기록' if current_apply_state=='completed' else '적용 확인 필요'
            else:
                current_apply_label='적용 연결 확인 불가'
        except (OSError,ValueError,KeyError,TypeError,AttributeError,RuntimeError):
            current_apply_label='적용 조회 불가'
        current_row.append(current_apply_label)
    current_notice = '선택한 세션 메시지 페이지의 대화 카드 ID 규칙으로 접수 기록을 대조했습니다. 세션 전체에서 중복된 Hermes 작업 ID는 연결하지 않습니다. 서비스 작업 ID의 중복 확인은 이 페이지에 한정됩니다. 같은 ID라도 입력이나 출처의 일치는 별도 확인해야 합니다. 접수 기록이 손상되었거나 구버전 게이트웨이면 조회 불가로 표시합니다. 작업 실행·복구는 하지 않습니다.'
    current_notice += ' GPU 관측 ' + current_observed_time + ' · 전용 대기열은 서비스와 작업 ID가, 공용 대기열은 검증된 원 서비스와 작업 ID가 일치한 기록만 연결하며 완료나 생존을 뜻하지 않습니다.'
    if current_session_record.get('truncated'):
        current_notice += ' · 이전 메시지는 조회 범위 밖입니다.'
    if current_skipped:
        current_notice += ' · 잘림·중복·미완료 등으로 확인하지 못한 메시지 ' + str(current_skipped) + '건'
    for current_model_receipt_row in current_model_receipt_rows:
        current_model_receipt_row[3]='모델 준비 · '+current_model_receipt_row[3]
    for current_kimodo_resume_row in current_kimodo_resume_rows:
        current_kimodo_resume_row[3]='Kimodo 재개 · '+current_kimodo_resume_row[3]
    for current_flux_resume_row in current_flux_resume_rows:
        current_flux_resume_row[3]='FLUX 재개 · '+current_flux_resume_row[3]
    for current_video_resume_row in current_video_resume_rows:
        current_video_resume_row[3]='영상 재개 · '+current_video_resume_row[3]
    return current_rows, current_notice



def read_operations_current_page_receipts(current_session_identifier,current_page_state):
    """화면에 표시된 지시 페이지와 같은 버전에서 접수 기록을 확인한다."""
    if current_page_state is None:
        return [],'먼저 세션 지시를 조회하세요. 구버전 게이트웨이는 페이지 연결을 지원하지 않습니다.'
    try:
        return read_operations_session_receipts(current_session_identifier,current_page_state)
    except (gr.Error,OSError,ValueError,KeyError,TypeError,AttributeError,RuntimeError):
        return [],'세션 이력이나 접수 기록을 확인할 수 없거나 변경됐습니다. 세션 지시를 처음부터 다시 조회하세요.'


def collect_operations_page_receipts(current_session_identifier,current_page_state,current_request_token):
    """지시 페이지와 조회 식별값을 결과에 고정한다."""
    current_rows_value,current_notice_text=read_operations_current_page_receipts(current_session_identifier,current_page_state)
    return {'session_id':current_session_identifier,'page':current_page_state,'token':current_request_token,'rows':current_rows_value,'notice':current_notice_text}


def render_operations_page_receipts(current_session_identifier,current_page_state,current_request_token,current_result_record):
    """현재 선택과 요청이 일치하지 않는 늦은 결과는 표시하지 않는다."""
    if not isinstance(current_result_record,dict) or (current_result_record.get('session_id'),current_result_record.get('page'),current_result_record.get('token'))!=(current_session_identifier,current_page_state,current_request_token):
        return gr.skip(),gr.skip(),gr.skip(),gr.skip()
    if not isinstance(current_result_record.get('rows'),list) or not isinstance(current_result_record.get('notice'),str):
        return gr.skip(),gr.skip(),gr.skip(),gr.skip()
    return current_result_record['rows'],current_result_record['notice'],'',gr.update(interactive=True)


def read_operations_cleanup_preview(current_service_name):
    """선택한 서비스의 정리 대상 수만 조회한다. 삭제하지 않는다."""
    try:
        if not isinstance(current_service_name,str) or not re.fullmatch(r'[a-z0-9-]{1,80}',current_service_name):
            raise ValueError('서비스 이름 오류')
        current_summary_record=execute_remote_management_command('hermes-agent','hermes-cleanup-preview',{'service':current_service_name})
        if (not isinstance(current_summary_record,dict) or current_summary_record.get('service')!=current_service_name
                or type(current_summary_record.get('job_count')) is not int or current_summary_record['job_count']<0
                or type(current_summary_record.get('blocked_count')) is not int or current_summary_record['blocked_count']<0
                or not isinstance(current_summary_record.get('status_counts'),dict)
                or type(current_summary_record.get('can_reset')) is not bool
                or type(current_summary_record.get('excludes_blocked')) is not bool):
            raise ValueError('정리 요약 오류')
        current_status_counts=current_summary_record['status_counts']
        current_allowed_states={'completed','failed','cancelled','canceled','paused','running','queued','unknown','other'}
        if any(current_key_name not in current_allowed_states or type(current_count_value) is not int or current_count_value<0 for current_key_name,current_count_value in current_status_counts.items()) or sum(current_status_counts.values())!=current_summary_record['job_count']:
            raise ValueError('정리 상태 합계 오류')
        current_status_text=', '.join(current_key_name+' '+str(current_count_value)+'건' for current_key_name,current_count_value in sorted(current_status_counts.items())) or '대상 없음'
        current_scope_text='차단 작업은 후보에서 제외됨' if current_summary_record['excludes_blocked'] else '차단 작업을 포함한 전체 대상'
        return ('서비스: `'+current_service_name+'` · 정리 검토: '+str(current_summary_record['job_count'])+'건 · 차단 '+str(current_summary_record['blocked_count'])+'건 · '+current_scope_text+'  \n상태: '+current_status_text+'  \n조회 시점의 기록입니다. 삭제는 수행하지 않았으며 실제 정리 전 대상과 상태를 다시 확인해야 합니다.')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '정리 미리보기를 확인하지 못했습니다. 해당 서비스 지원 여부와 원본 작업 상태를 확인하세요.'


def create_cleanup_preview_token():
    import uuid
    return uuid.uuid4().hex


def collect_operations_cleanup_preview(current_service_name,current_request_token):
    """조회 대상과 결과를 함께 보관해 현재 선택과 비교할 수 있게 한다."""
    return {'service':current_service_name,'token':current_request_token,'message':read_operations_cleanup_preview(current_service_name)}


def render_operations_cleanup_preview(current_service_name,current_request_token,current_preview_record):
    """조회 중 서비스가 바뀐 결과는 화면에 표시하지 않는다."""
    if not isinstance(current_preview_record,dict) or (current_preview_record.get('service'),current_preview_record.get('token'))!=(current_service_name,current_request_token):
        return gr.skip()
    current_message_value=current_preview_record.get('message')
    return current_message_value if isinstance(current_message_value,str) else gr.skip()


def prepare_operations_audio_resume(current_service_name,current_job_identifier,current_page_state,current_source_rows):
    """선택된 원본 행과 재개 검토·기존 접수를 확인한다."""
    try:
        if current_service_name not in ('music-heartmula','sfx-dasheng-audiogen','prompt-translation','kimodo','dwpose','wan22-animate2','wan22-vace','wan22-fun-control',*FLUX_IMAGE_PROFILE_RECORDS) or not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or not isinstance(current_page_state.get('snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_page_state['snapshot']):raise ValueError('서비스 또는 페이지 오류')
        if not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier) or not isinstance(current_source_rows,list):raise ValueError('작업 오류')
        if sum(isinstance(item,(list,tuple)) and len(item)==5 and item[0]==current_job_identifier for item in current_source_rows)!=1:raise ValueError('선택 행 오류')
        current_preview_command='hermes-flux-resume-preview' if current_service_name in FLUX_IMAGE_PROFILE_RECORDS else {'prompt-translation':'hermes-translation-resume-preview','kimodo':'hermes-kimodo-resume-preview','dwpose':'hermes-video-resume-preview','wan22-animate2':'hermes-video-resume-preview','wan22-vace':'hermes-video-resume-preview','wan22-fun-control':'hermes-video-resume-preview'}.get(current_service_name,'hermes-audio-resume-preview')
        current_preview_payload={'job_id':current_job_identifier} if current_service_name in ('prompt-translation','kimodo') else {'service':current_service_name,'job_id':current_job_identifier}
        current_preview_value=execute_remote_management_command('hermes-agent',current_preview_command,current_preview_payload)
        if not isinstance(current_preview_value,dict) or (current_preview_value.get('service'),current_preview_value.get('job_id'))!=(current_service_name,current_job_identifier) or current_preview_value.get('status') not in ('failed','cancelled','paused'):raise ValueError('재개 대상 오류')
        if current_service_name!='prompt-translation':
            current_resume_availability=current_preview_value.get('resume_availability','unknown')
            if current_resume_availability=='download_running':return None,'모델 다운로드가 진행 중입니다. 완료 후 다시 재개를 검토하세요.',''
            if current_resume_availability=='other_preparation':return None,'다른 모델 준비 작업이 대기·실행 중입니다. 작업을 확인한 뒤 다시 검토하세요.',''
            if current_resume_availability=='unknown':return None,'다운로드·다른 준비 작업의 충돌 상태를 확인할 수 없습니다. 원 서비스를 갱신하고 다시 검토하세요.',''
            if current_resume_availability!='available':raise ValueError('재개 가능 상태 오류')
        current_fingerprint_value=current_preview_value.get('expected_resume_fingerprint')
        if not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value):raise ValueError('확인값 오류')
        current_request_prefix='flux_resume_' if current_service_name in FLUX_IMAGE_PROFILE_RECORDS else {'prompt-translation':'trans_resume_','kimodo':'kimodo_resume_','dwpose':'video_resume_','wan22-animate2':'video_resume_','wan22-vace':'video_resume_','wan22-fun-control':'video_resume_'}.get(current_service_name,'audio_resume_')
        current_request_identifier=current_request_prefix+hashlib.sha256((current_service_name+'\0'+current_job_identifier+'\0'+current_fingerprint_value).encode()).hexdigest()
        current_request_record={'request_id':current_request_identifier,'service':current_service_name,'job_id':current_job_identifier,'expected_resume_fingerprint':current_fingerprint_value}
        current_receipt_command='hermes-flux-resume-receipt' if current_service_name in FLUX_IMAGE_PROFILE_RECORDS else {'prompt-translation':'hermes-translation-resume-receipt','kimodo':'hermes-kimodo-resume-receipt','dwpose':'hermes-video-resume-receipt','wan22-animate2':'hermes-video-resume-receipt','wan22-vace':'hermes-video-resume-receipt','wan22-fun-control':'hermes-video-resume-receipt'}.get(current_service_name,'hermes-audio-resume-receipt')
        current_receipt_value=execute_remote_management_command('hermes-agent',current_receipt_command,{'request_id':current_request_identifier})
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier:raise ValueError('접수 오류')
        if current_receipt_value.get('state')!='not_found':
            if any(current_receipt_value.get(item)!=current_request_record[item] for item in ('request_id','service','job_id','expected_resume_fingerprint')) or current_receipt_value.get('state') not in ('unknown','accepted'):raise ValueError('접수 대상 오류')
            return None,'이전 재개 접수 기록이 있습니다. 원 서비스와 GPU 대기열에서 상태를 확인하세요.',current_request_identifier
        current_availability_note=' 충돌 상태는 접수 시 다시 확인합니다.' if current_service_name=='prompt-translation' or current_preview_value.get('resume_availability')=='available' else ' 다운로드·다른 준비 작업의 현재 충돌 여부는 확인되지 않았으며 접수 시 다시 확인합니다.'
        return {**current_request_record,'history_snapshot':current_page_state['snapshot']},'재개 검토: '+current_service_name+' · '+current_job_identifier+' · 기록 상태 '+current_preview_value['status']+'. 확인하면 저장된 작업을 GPU 대기열에 다시 추가합니다.'+current_availability_note,current_request_identifier
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return None,'재개 대상 또는 접수를 확인할 수 없습니다. 원 서비스와 작업 기록을 확인하세요.',''


def submit_operations_audio_resume(current_request_record,current_service_name,current_job_identifier,current_page_state,current_source_rows):
    """검토한 대상만 접수하고 응답 유실 시 재요청하지 않는다."""
    if not isinstance(current_request_record,dict) or (current_request_record.get('service'),current_request_record.get('job_id'))!=(current_service_name,current_job_identifier) or not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or not isinstance(current_request_record.get('history_snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_request_record['history_snapshot']) or current_page_state.get('snapshot')!=current_request_record['history_snapshot'] or not isinstance(current_source_rows,list) or sum(isinstance(item,(list,tuple)) and len(item)==5 and item[0]==current_job_identifier for item in current_source_rows)!=1:
        return None,'선택한 작업이 바뀌었습니다. 다시 검토하세요.'
    try:
        current_submit_command='hermes-flux-resume-submit' if current_service_name in FLUX_IMAGE_PROFILE_RECORDS else {'prompt-translation':'hermes-translation-resume-submit','kimodo':'hermes-kimodo-resume-submit','dwpose':'hermes-video-resume-submit','wan22-animate2':'hermes-video-resume-submit','wan22-vace':'hermes-video-resume-submit','wan22-fun-control':'hermes-video-resume-submit'}.get(current_service_name,'hermes-audio-resume-submit')
        current_submit_payload={current_key_name:current_request_record[current_key_name] for current_key_name in ('request_id','job_id','expected_resume_fingerprint')}
        if current_service_name not in ('prompt-translation','kimodo'):current_submit_payload['service']=current_service_name
        current_receipt_value=execute_remote_management_command('hermes-agent',current_submit_command,current_submit_payload)
        if not isinstance(current_receipt_value,dict) or any(current_receipt_value.get(item)!=current_request_record.get(item) for item in ('request_id','service','job_id','expected_resume_fingerprint')) or current_receipt_value.get('state') not in ('accepted','unknown','blocked'):raise ValueError('접수 불일치')
        if current_receipt_value['state']=='blocked':
            current_block_messages={'download_running':'모델 다운로드가 진행 중입니다. 완료 후 재개를 다시 검토하세요.','other_preparation':'다른 모델 준비 작업이 대기·실행 중입니다. 상태를 확인하고 다시 검토하세요.','unavailable':'재개 충돌 상태를 확인할 수 없습니다. 원 서비스를 확인하고 다시 검토하세요.','fingerprint_changed':'작업 기록이 변경되었습니다. 재개를 다시 검토하세요.'}
            if current_service_name=='prompt-translation' or current_receipt_value.get('reason') not in current_block_messages:raise ValueError('재개 차단 사유 오류')
            return None,'재개 접수 전 차단: '+current_block_messages[current_receipt_value['reason']]
        if current_receipt_value['state']=='accepted':return None,'재개가 대기열에 접수되었습니다. 실제 실행·완료는 원 서비스와 GPU 대기열에서 확인하세요.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as current_resume_error:
        current_resume_message=describe_unconfirmed_resume_error(current_resume_error)
        if current_resume_message:return None,current_resume_message
    return None,'접수 결과를 확인할 수 없습니다. 같은 접수 ID와 원 서비스 상태를 확인하고 다시 요청하지 마세요.'


def read_operations_audio_resume_receipt(current_request_identifier,current_selected_service=None):
    try:
        if not isinstance(current_request_identifier,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',current_request_identifier):raise ValueError('접수 ID 오류')
        current_generated_match=re.fullmatch(r'(audio_resume_|trans_resume_|kimodo_resume_|flux_resume_|video_resume_)[a-f0-9]{64}',current_request_identifier)
        current_service_commands={'prompt-translation':'hermes-translation-resume-receipt','kimodo':'hermes-kimodo-resume-receipt','music-heartmula':'hermes-audio-resume-receipt','sfx-dasheng-audiogen':'hermes-audio-resume-receipt'}
        current_service_commands.update({current_video_service:'hermes-video-resume-receipt' for current_video_service in ('dwpose','wan22-animate2','wan22-vace','wan22-fun-control')})
        current_service_commands.update({current_flux_service:'hermes-flux-resume-receipt' for current_flux_service in FLUX_IMAGE_PROFILE_RECORDS})
        if current_selected_service is not None:
            if current_selected_service not in current_service_commands:raise ValueError('서비스 선택 오류')
            current_receipt_command=current_service_commands[current_selected_service]
        elif current_generated_match:
            current_receipt_command={'trans_resume_':'hermes-translation-resume-receipt','kimodo_resume_':'hermes-kimodo-resume-receipt','audio_resume_':'hermes-audio-resume-receipt','flux_resume_':'hermes-flux-resume-receipt','video_resume_':'hermes-video-resume-receipt'}[current_generated_match.group(1)]
        else:raise ValueError('서비스 선택 오류')
        current_receipt_value=execute_remote_management_command('hermes-agent',current_receipt_command,{'request_id':current_request_identifier})
        if not isinstance(current_receipt_value,dict) or current_receipt_value.get('request_id')!=current_request_identifier:raise ValueError('접수 오류')
        if current_receipt_value.get('state')=='not_found':return '선택한 서비스에 접수 기록이 없습니다. 원 서비스 상태를 확인하세요.'
        if current_receipt_value.get('state') not in ('accepted','unknown'):raise ValueError('접수 오류')
        current_service_name=current_receipt_value.get('service')
        current_job_identifier=current_receipt_value.get('job_id')
        current_fingerprint_value=current_receipt_value.get('expected_resume_fingerprint')
        if current_service_name not in current_service_commands or current_service_commands[current_service_name]!=current_receipt_command or (current_selected_service is not None and current_service_name!=current_selected_service) or not isinstance(current_job_identifier,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_identifier) or not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value):raise ValueError('접수 대상 오류')
        if current_generated_match:
            current_request_prefix='flux_resume_' if current_service_name in FLUX_IMAGE_PROFILE_RECORDS else {'prompt-translation':'trans_resume_','kimodo':'kimodo_resume_','dwpose':'video_resume_','wan22-animate2':'video_resume_','wan22-vace':'video_resume_','wan22-fun-control':'video_resume_'}.get(current_service_name,'audio_resume_')
            current_expected_identifier=current_request_prefix+hashlib.sha256((current_service_name+'\0'+current_job_identifier+'\0'+current_fingerprint_value).encode()).hexdigest()
            if current_expected_identifier!=current_request_identifier:raise ValueError('접수 대상 불일치')
        return current_service_name+' · '+current_job_identifier+' · '+('대기열 접수 기록' if current_receipt_value['state']=='accepted' else '접수 결과 확인 필요 · 자동 재요청하지 마세요.')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '접수 기록을 확인할 수 없습니다. 원 서비스 상태를 확인하세요.'


def describe_operations_source_status(current_status_name):
    """원본 기록 상태를 번역하고 판별되지 않은 값은 완료로 추정하지 않는다."""
    current_status_labels={'queued':'대기','running':'실행 중','completed':'완료 기록','failed':'실패 기록','cancelled':'취소 기록','canceled':'취소 기록','paused':'일시정지','unknown':'확인 불가','preparing':'준비 중','indexing':'색인 중','searching':'검색 중','reasoning':'추론 중','review':'검토 중','applied':'적용 기록','interrupted':'중단 기록'}
    return current_status_labels.get(current_status_name,'확인 불가')


def read_operations_source_history(current_service_name,current_page_state=None,current_next_page=False,current_search_text=''):
    """원본 관측을 스냅샷으로 조회하고 서비스·작업 ID가 일치한 대기만 연결한다."""
    if current_service_name not in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES):
        return [],'지원하는 서비스를 선택하세요.',None,gr.update(interactive=False),''
    if not isinstance(current_search_text,str) or len(current_search_text)>80 or (current_search_text and not re.fullmatch(r'[A-Za-z0-9_-]+',current_search_text)):
        return [],'작업 ID 검색어는 영문·숫자·하이픈·밑줄만 입력하세요.',None,gr.update(interactive=False),''
    current_search_text=current_search_text.casefold()
    current_request_record={'service':current_service_name,'limit':30}
    if current_search_text:current_request_record['query']=current_search_text
    if current_next_page:
        if not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or current_page_state.get('query','')!=current_search_text or type(current_page_state.get('next_offset')) is not int or not isinstance(current_page_state.get('snapshot'),str):
            return [],'서비스나 페이지가 바뀌었습니다. 처음부터 조회하세요.',None,gr.update(interactive=False),''
        current_request_record.update(offset=current_page_state['next_offset'],snapshot=current_page_state['snapshot'])
    current_command_name='hermes-audio-source-history' if current_service_name in SOURCE_HISTORY_AUDIO_SERVICES else 'hermes-generator-source-history'
    try:
        current_source_record=execute_remote_management_command('hermes-agent',current_command_name,current_request_record)
        if not isinstance(current_source_record,dict) or current_source_record.get('service')!=current_service_name:
            raise ValueError('서비스 불일치')
        current_source_service=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
        if current_source_record.get('source_service',current_source_service)!=current_source_service:
            raise ValueError('원본 서비스 불일치')
        current_validated_record=sanitize_hermes_source_history(current_service_name,{key:value for key,value in current_request_record.items() if key!='service'},current_source_record)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return [],'원본 이력 조회 불가 · 서비스 연결 또는 변경된 목록을 확인하고 처음부터 다시 조회하세요.',None,gr.update(interactive=False),''
    current_management_record=None
    try:
        current_management_record=execute_remote_management_command('hermes-agent','hermes-management-status',{})
        current_queue_record=current_management_record['queue']
        if current_queue_record.get('status')!='available' or not isinstance(current_queue_record.get('jobs'),list):raise ValueError('대기열 조회 불가')
        current_queue_values=current_queue_record['jobs']
        if any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not isinstance(item.get('service'),str) for item in current_queue_values):raise ValueError('대기열 형식 오류')
        current_queue_counts=Counter((item['service'],item['id']) for item in current_queue_values)
        current_source_counts=Counter((item['service'],read_operations_verified_source(item['service'],item.get('source_service')),item['id']) for item in current_queue_values if read_operations_verified_source(item['service'],item.get('source_service')) is not None)
        current_queue_time=str(current_management_record.get('queried_at','확인 불가'))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        current_queue_counts=None
        current_source_counts=None
        current_queue_time='조회 불가'
    current_reservation_index,current_unmatched_record,_,_=summarize_operations_reservation_snapshot(current_management_record)
    current_source_labels={'job':'작업 상태 파일','index':'이전 색인','unavailable':'확인 불가'}
    current_result_rows=[]
    for current_item_record in current_validated_record['records']:
        current_queue_service=resolve_operations_queue_identity(current_source_service)
        if current_queue_service is None:
            current_shared_name='flux-image' if current_source_service.startswith('flux-') else 'image'
            current_queue_label=label_operations_shared_queue_record(current_queue_counts,current_source_counts,current_shared_name,current_source_service,current_item_record['id'])
            current_reservation_label=label_operations_shared_reservation_record(current_reservation_index,current_unmatched_record,current_shared_name,current_source_service,current_item_record['id'])
        else:
            from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
            if is_dedicated_gpu_source_verifiable(current_queue_service):
                current_queue_label=label_operations_verified_dedicated_queue(current_queue_counts,current_source_counts,current_queue_service,current_source_service,current_item_record['id'])
                current_reservation_label=label_operations_verified_dedicated_reservation(current_reservation_index,current_unmatched_record,current_queue_service,current_source_service,current_item_record['id'])
            else:
                current_queue_label=label_operations_dedicated_queue(current_queue_counts,current_queue_service,current_item_record['id'])
                current_reservation_label=label_operations_reservation_record(current_reservation_index,current_unmatched_record,current_queue_service,current_item_record['id'])
        current_result_rows.append([current_item_record['id'],describe_operations_source_status(current_item_record['recorded_status']),current_source_labels[current_item_record['status_source']],current_queue_label,current_reservation_label])
    current_next_offset=current_validated_record['next_offset']
    current_next_state={'service':current_service_name,'query':current_search_text,'offset':current_validated_record['offset'],'next_offset':current_next_offset,'snapshot':current_validated_record['snapshot']}
    current_first_index=current_validated_record['offset']+1 if current_result_rows else 0
    current_last_index=current_validated_record['offset']+len(current_result_rows)
    current_notice_text='원본 '+current_source_service+' · 전체 '+str(current_validated_record['total'])+'건 중 '+str(current_first_index)+'–'+str(current_last_index)+'건 · GPU 대기 관측 '+current_queue_time+'. 기록 상태는 실제 작업 생존이나 결과 품질을 보증하지 않습니다.'
    if current_validated_record['unavailable_count']:current_notice_text+=' · 확인 불가 이력 '+str(current_validated_record['unavailable_count'])+'건'
    if current_source_service!=current_service_name:current_notice_text+=' · 선택한 서비스는 이 원본 이력을 공유합니다.'
    return current_result_rows,current_notice_text,current_next_state,gr.update(interactive=current_next_offset is not None),render_operations_source_link(current_source_service)


def render_operations_source_link(current_service_name,current_job_identifier=None,current_session_identifier=None):
    """확인된 관리 도구 주소만 표시하며 작업 상세를 추측하지 않는다."""
    current_tool_paths={'kimodo':'kimodo-generator','dwpose':'dwpose-generator','wan22-animate2':'wan22-animate2-generator','wan22-fun-control':'wan22-fun-control-generator','wan22-vace':'wan22-vace-generator','prompt-translation':'prompt-translation','writer-agent':'writer-agent','music-heartmula':'music-heartmula','sfx-dasheng-audiogen':'sfx-dasheng-audiogen','flux-expression':'flux-expression-generator'}
    for current_profile_name in ('flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless'):
        current_tool_paths[current_profile_name]=current_profile_name+'-generator'
    current_path_value=current_tool_paths.get(current_service_name)
    if current_path_value is None:return '<span>이 서비스의 도구 이동 링크는 제공되지 않습니다. 위 원본 이력의 기록 상태를 확인하세요.</span>'
    current_linked_services={'kimodo','dwpose','wan22-animate2','wan22-fun-control','wan22-vace','music-heartmula','sfx-dasheng-audiogen','flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-building','flux-seamless','flux-expression','prompt-translation','writer-agent'}
    current_job_query=''
    if current_service_name in current_linked_services and isinstance(current_job_identifier,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job_identifier):
        current_job_query='?job='+current_job_identifier
    if isinstance(current_session_identifier,str) and re.fullmatch(r'[a-f0-9]{32}',current_session_identifier):
        current_job_query+=('&amp;' if current_job_query else '?')+'session='+current_session_identifier
    return '<a href="/management/frame/'+html.escape(current_path_value,quote=True)+'/'+current_job_query+'" target="_blank" rel="noopener">해당 도구의 이력 열기</a>'



def select_operations_source_job(current_service_name,current_page_state,current_source_rows,current_select_event:gr.SelectData,current_session_identifier=None):
    """현재 원본 이력의 선택 ID와 실제 소유 서비스만 표시한다."""
    if current_service_name not in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES) or not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or not isinstance(current_page_state.get('snapshot'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_page_state['snapshot']):
        raise gr.Error('원본 이력을 다시 조회하세요.')
    current_index=current_select_event.index
    if isinstance(current_index,(tuple,list)):current_index=current_index[0] if current_index else None
    if type(current_index) is not int or not isinstance(current_source_rows,list) or not 0<=current_index<len(current_source_rows):raise gr.Error('작업 행을 다시 선택하세요.')
    current_row=current_source_rows[current_index]
    if not isinstance(current_row,(tuple,list)) or len(current_row)!=5 or not isinstance(current_row[0],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_row[0]):raise gr.Error('작업 ID를 확인할 수 없습니다.')
    current_owner_service=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
    current_link=render_operations_source_link(current_owner_service,current_row[0],current_session_identifier)
    current_notice='원본 서비스: '+html.escape(current_owner_service)+' · '+('도구에서 전달된 작업 찾기 버튼을 눌러 확인하세요. 상태 조회는 중단된 기록을 복구할 수 있습니다.' if '?job=' in current_link else '선택한 작업 ID를 확인하세요. 이 화면은 작업을 자동 선택하지 않습니다.')
    return current_row[0],current_link+'<p>'+current_notice+'</p>'


def select_operations_receipt_service(current_receipt_rows, current_select_event:gr.SelectData,current_session_identifier=None):
    """확인된 접수 ID만 원본 서비스에 전달하며 불확실한 연결은 생략한다."""
    current_selected_index = current_select_event.index
    if isinstance(current_selected_index, (tuple, list)):
        current_selected_index = current_selected_index[0] if current_selected_index else None
    if type(current_selected_index) is not int or not isinstance(current_receipt_rows, list) or not 0 <= current_selected_index < len(current_receipt_rows):
        raise gr.Error('접수 행을 다시 선택하세요.')
    current_selected_row = current_receipt_rows[current_selected_index]
    if not isinstance(current_selected_row, (tuple, list)) or len(current_selected_row) != 8 or not isinstance(current_selected_row[1], str):
        raise gr.Error('접수 행을 확인할 수 없습니다.')
    current_job_identifier = current_selected_row[4]
    current_matching_rows = [current_row for current_row in current_receipt_rows if isinstance(current_row,(tuple,list)) and len(current_row)==8 and current_row[3] in ('접수 기록','모델 준비 · 접수 기록','Kimodo 재개 · 접수 기록') and current_row[1]==current_selected_row[1] and current_row[4]==current_job_identifier]
    current_confirmed_identifier = current_job_identifier if current_selected_row[3] in ('접수 기록','모델 준비 · 접수 기록','Kimodo 재개 · 접수 기록') and isinstance(current_job_identifier,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job_identifier) and current_job_identifier!='미확인' and len(current_matching_rows)==1 else None
    current_link_html = render_operations_source_link(current_selected_row[1],current_confirmed_identifier,current_session_identifier)
    if '?job=' in current_link_html:
        return current_link_html + '<p>도구에서 전달된 작업 찾기를 눌러 확인하세요. 상태 조회는 중단된 기록을 복구할 수 있습니다. ID 일치는 입력이나 출처의 일치를 보증하지 않습니다.</p>'
    return current_link_html + ('<p>도구의 이력에서 위 서비스 작업 ID를 직접 확인하세요. 이 링크는 특정 작업을 선택하지 않습니다.</p>' if '<a ' in current_link_html else '<p>위 원본 이력의 작업 ID와 기록 상태를 확인하세요.</p>')


def read_next_operations_source_history(current_service_name,current_page_state):
    return read_operations_source_history(current_service_name,current_page_state,True,current_page_state.get('query','') if isinstance(current_page_state,dict) else '')


def read_previous_operations_source_history(current_service_name,current_page_state):
    if not isinstance(current_page_state,dict) or current_page_state.get('service')!=current_service_name or type(current_page_state.get('offset')) is not int or current_page_state['offset']<=0 or not isinstance(current_page_state.get('snapshot'),str):
        return [],'서비스나 페이지가 바뀌었습니다. 처음부터 조회하세요.',None,gr.update(interactive=False),''
    current_previous_state={**current_page_state,'next_offset':max(0,current_page_state['offset']-30)}
    return read_operations_source_history(current_service_name,current_previous_state,True,current_previous_state.get('query',''))


def render_operations_source_history_page(current_service_name,current_page_state=None,current_direction='first',current_search_text=''):
    if current_direction!='first' and (not isinstance(current_page_state,dict) or current_page_state.get('query','')!=current_search_text.casefold()):current_page_result=([],'검색 조건이 바뀌었습니다. 처음부터 조회하세요.',None,gr.update(interactive=False),'')
    elif current_direction=='next':current_page_result=read_next_operations_source_history(current_service_name,current_page_state)
    elif current_direction=='previous':current_page_result=read_previous_operations_source_history(current_service_name,current_page_state)
    else:current_page_result=read_operations_source_history(current_service_name,current_search_text=current_search_text)
    current_returned_state=current_page_result[2]
    return (*current_page_result,gr.update(interactive=isinstance(current_returned_state,dict) and current_returned_state.get('offset',0)>0))



def select_operations_reservation_target(current_reservation_rows,current_select_event:gr.SelectData):
    """예약 행의 확인된 원 서비스만 안내하며 예약이나 프로세스는 변경하지 않는다."""
    current_index=current_select_event.index
    if isinstance(current_index,(tuple,list)):current_index=current_index[0] if current_index else None
    if type(current_index) is not int or not isinstance(current_reservation_rows,list) or not 0<=current_index<len(current_reservation_rows):raise gr.Error('예약 행을 다시 선택하세요.')
    current_row=current_reservation_rows[current_index]
    if not isinstance(current_row,(list,tuple)) or len(current_row)!=6 or not all(isinstance(current_value,str) for current_value in current_row):raise gr.Error('예약 기록을 확인할 수 없습니다.')
    current_state,current_pool,current_job,_,_,current_source=current_row
    if current_state not in ('예약 기록','정리 확인 필요') or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job) or current_job=='ID 확인 불가':
        return '<p>예약의 서비스나 작업 ID를 확인할 수 없습니다. GPU 프로세스와 원 서비스 기록을 직접 확인하세요.</p>'
    if sum(isinstance(current_other,(list,tuple)) and len(current_other)==6 and current_other[1]==current_pool and current_other[2]==current_job for current_other in current_reservation_rows)!=1:
        return '<p>같은 서비스와 작업 ID의 예약이 중복되어 원본 작업을 연결하지 않습니다.</p>'
    from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    if current_pool in ('image','flux-image') or is_dedicated_gpu_source_verifiable(current_pool):
        current_owner=read_operations_verified_source(current_pool,current_source)
    else:
        current_owner=current_pool
    if current_owner is None:return '<p>GPU 예약의 원 서비스가 확인되지 않았습니다. 서비스와 GPU 프로세스를 직접 확인하세요.</p>'
    current_link=render_operations_source_link(current_owner,current_job)
    current_notice='예약 중복은 화면에 표시된 범위에서만 확인했습니다. 원 서비스와 GPU 프로세스를 확인하세요. 리더 확인만으로 하위 그룹 전체의 종료를 보증하지 않습니다.'
    if current_state=='정리 확인 필요':current_notice+=' 자동 정리하지 않으며 정리하려면 별도 확인이 필요합니다.'
    if '?job=' in current_link:current_notice+=' 도구에서 전달된 작업 찾기를 누르면 상태 조회가 중단 기록을 복구할 수 있습니다.'
    return current_link+'<p>'+current_notice+'</p>'


def select_operations_reservation_inspection(current_reservation_rows,current_select_event:gr.SelectData):
    """표시된 행에서 확인 가능한 생성기 예약의 비파괴 조회 대상을 고른다."""
    current_index=current_select_event.index
    if isinstance(current_index,(tuple,list)):current_index=current_index[0] if current_index else None
    if type(current_index) is not int or not isinstance(current_reservation_rows,list) or not 0<=current_index<len(current_reservation_rows):
        return None,gr.update(interactive=False),'예약 행을 다시 선택하세요.'
    current_row=current_reservation_rows[current_index]
    if not isinstance(current_row,(list,tuple)) or len(current_row)!=6 or not all(isinstance(current_value,str) for current_value in current_row):
        return None,gr.update(interactive=False),'예약 기록을 확인할 수 없습니다.'
    current_state,current_pool,current_job,_,_,current_source=current_row
    from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    current_owner=read_operations_verified_source(current_pool,current_source) if current_pool in ('image','flux-image') or is_dedicated_gpu_source_verifiable(current_pool) else current_pool
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_AUDIO_SERVICES
    if current_state not in ('예약 기록','정리 확인 필요') or current_owner not in (*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES) or current_owner=='writer-agent' or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_job):
        return None,gr.update(interactive=False),'확인 가능한 생성기 예약을 선택하세요. 작가 예약은 운영 대화의 작가 예약 검토를 이용하세요.'
    if sum(isinstance(current_other,(list,tuple)) and len(current_other)==6 and current_other[1]==current_pool and current_other[2]==current_job for current_other in current_reservation_rows)!=1:
        return None,gr.update(interactive=False),'표시된 예약이 중복되어 조회 대상을 선택할 수 없습니다.'
    return {'service':current_owner,'job_id':current_job},gr.update(interactive=True),'선택한 예약을 확인할 수 있습니다. 조회만 하며 예약이나 프로세스는 변경하지 않습니다.'


def inspect_operations_reservation_target(current_inspection_target):
    """서버가 전체 예약의 유일성과 서비스·리더 신원을 다시 확인한다."""
    if not isinstance(current_inspection_target,dict) or set(current_inspection_target)!={'service','job_id'}:return '확인할 예약을 먼저 선택하세요.'
    try:
        current_result=execute_remote_management_command('hermes-agent','hermes-generator-reservation-inspect',current_inspection_target)
        if not isinstance(current_result,dict) or (current_result.get('service'),current_result.get('job_id'))!=(current_inspection_target['service'],current_inspection_target['job_id']):raise ValueError('예약 대상 불일치')
        current_executor={'observed':'신원 일치로 관측','not_observed':'일치 실행기 미관측','unverified':'확인 불가'}.get(current_result.get('executor'))
        current_leader={'verified_running':'신원 일치로 관측','unverified':'확인 불가'}.get(current_result.get('worker_leader'))
        current_memory=current_result.get('required_memory_mib')
        if current_executor is None or current_leader is None or type(current_memory) is not int or current_memory<0:raise ValueError('예약 응답 오류')
        current_review_notice=' 정리 검토에서 현재 상태를 다시 확인할 수 있습니다.' if current_result.get('review_ready') is True else ''
        return '실행기: '+current_executor+' · 작업자 리더: '+current_leader+' · 예약: '+str(current_memory)+' MiB. 조회만 수행했습니다. 실행기 미관측이나 리더 확인은 그룹 전체·별도 그룹의 종료를 보증하지 않습니다.'+current_review_notice
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '예약 신원을 확인할 수 없습니다. 원 서비스와 GPU 프로세스를 확인하세요. 예약이나 프로세스는 변경하지 않았습니다.'



def prepare_operations_reservation_recovery(current_reservation_target):
    """예약을 다시 조회하고 명시적인 정리 확인을 준비한다."""
    current_closed=(None,'예약을 다시 선택하고 신원을 확인하세요.','',gr.update(visible=False),False)
    if not isinstance(current_reservation_target,dict) or set(current_reservation_target)!={'service','job_id'}:return current_closed
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-generator-reservation-inspect',current_reservation_target)
        if not isinstance(current_result_record,dict) or (current_result_record.get('service'),current_result_record.get('job_id'))!=(current_reservation_target['service'],current_reservation_target['job_id']) or current_result_record.get('review_ready') is not True:
            return None,'예약을 안전하게 정리할 수 있는 상태인지 확인하지 못했습니다. 원 서비스와 GPU 프로세스를 확인하세요.','',gr.update(visible=False),False
        current_review_digest=current_result_record.get('review_sha256')
        if not isinstance(current_review_digest,str) or not re.fullmatch(r'[a-f0-9]{64}',current_review_digest):raise ValueError('예약 검토값 오류')
        current_request_identifier='recovery_'+hashlib.sha256((current_reservation_target['service']+'\0'+current_reservation_target['job_id']+'\0'+current_review_digest).encode()).hexdigest()
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-generator-reservation-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict) or current_receipt_record.get('state')!='not_found':
            return None,'이미 접수되었거나 접수 상태를 확인할 수 없습니다. 접수 결과를 조회하고 재실행하지 마세요.',current_request_identifier,gr.update(visible=False),False
        current_request_record={'request_id':current_request_identifier,**current_reservation_target,'review_sha256':current_review_digest}
        return current_request_record,'검토 대상: '+current_reservation_target['service']+' · '+current_reservation_target['job_id']+'. 확인하면 해당 작업자 그룹을 강제 종료하고 예약을 해제합니다.',current_request_identifier,gr.update(visible=True),False
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return None,'검토 또는 접수 상태를 확인하지 못했습니다. 프로세스와 예약은 변경하지 않았습니다.','',gr.update(visible=False),False


def start_operations_reservation_review():
    """새 예약 검토 전 이전 요청·확인 상태를 즉시 지운다."""
    return create_cleanup_preview_token(),gr.update(interactive=False),None,gr.update(visible=False),False


def collect_operations_reservation_recovery(current_reservation_target,current_request_token):
    """검토 대상과 요청 식별값을 묶어 늦은 응답을 구분한다."""
    return {'target':current_reservation_target,'token':current_request_token,'result':prepare_operations_reservation_recovery(current_reservation_target)}


def render_operations_reservation_recovery(current_reservation_target,current_request_token,current_result_record):
    """예약 선택 또는 요청이 바뀐 결과는 확인 창에 표시하지 않는다."""
    if not isinstance(current_result_record,dict) or (current_result_record.get('target'),current_result_record.get('token'))!=(current_reservation_target,current_request_token):
        return (gr.skip(),)*6
    current_result_values=current_result_record.get('result')
    if not isinstance(current_result_values,(list,tuple)) or len(current_result_values)!=5:return (gr.skip(),)*6
    return (*current_result_values,gr.update(interactive=True))


def submit_operations_reservation_recovery(current_request_record,current_reservation_target,current_outside_checked):
    """확인한 대상만 접수하며 응답이 불확실하면 자동 재시도하지 않는다."""
    if not isinstance(current_request_record,dict) or not isinstance(current_reservation_target,dict) or (current_request_record.get('service'),current_request_record.get('job_id'))!=(current_reservation_target.get('service'),current_reservation_target.get('job_id')):
        return None,'예약 선택이 바뀌었습니다. 다시 검토하세요.',gr.update(visible=False)
    if current_outside_checked is not True:
        return current_request_record,'별도 그룹의 GPU 프로세스 확인 항목을 선택해야 합니다.',gr.update(visible=True)
    try:
        current_result_record=execute_remote_management_command('hermes-agent','hermes-generator-reservation-recover',{**current_request_record,'outside_processes_checked':True})
        if not isinstance(current_result_record,dict) or any(current_result_record.get(current_field_name)!=current_request_record[current_field_name] for current_field_name in ('request_id','service','job_id')) or current_result_record.get('state') not in ('completed','unknown'):
            raise ValueError('접수 응답 오류')
        if current_result_record['state']=='completed':return None,'정리가 완료되었습니다. 원 서비스와 GPU 상태를 확인하고 이력을 새로고침하세요.',gr.update(visible=False)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        pass
    return None,'정리 결과 확인이 필요합니다. 접수 ID로 조회하고 원 서비스와 GPU 프로세스를 확인하세요. 다시 실행하지 마세요.',gr.update(visible=False)


def read_operations_reservation_recovery_receipt(current_request_identifier):
    if not isinstance(current_request_identifier,str) or not re.fullmatch(r'recovery_[a-f0-9]{64}',current_request_identifier):return '유효한 정리 접수 ID를 입력하세요.'
    try:
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-generator-reservation-receipt',{'request_id':current_request_identifier})
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


def read_operations_selected_capture_status(current_queue_rows,current_select_event:gr.SelectData):
    """선택한 캡처 대기 기록의 접수·작업 신원을 다시 확인한다."""
    current_selected_index=current_select_event.index
    if isinstance(current_selected_index,(tuple,list)):
        current_selected_index=current_selected_index[0] if current_selected_index else None
    if type(current_selected_index) is not int or not isinstance(current_queue_rows,list) or not 0<=current_selected_index<len(current_queue_rows):
        return '대기 행을 다시 선택하세요.'
    current_row_value=current_queue_rows[current_selected_index]
    if not isinstance(current_row_value,(list,tuple)) or len(current_row_value)!=5 or not all(isinstance(current_item_value,str) for current_item_value in current_row_value):
        return '대기 기록을 확인할 수 없습니다.'
    if current_row_value[1]!='review-capture' or current_row_value[3]!='review-capture':
        return '캡처 대기 기록을 선택하면 접수 상태를 확인합니다.'
    current_capture_label,current_separator_value,current_request_identifier=current_row_value[4].partition(' · ')
    current_service_name={'맵':'map-review','캐릭터':'character-review'}.get(current_capture_label)
    if not current_separator_value or current_service_name is None or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',current_request_identifier):
        return '캡처 접수 신원을 확인할 수 없습니다.'
    try:
        current_result_value=execute_remote_management_command('hermes-agent','hermes-capture-status',{'request_id':current_request_identifier,'service':current_service_name})
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


def select_operations_priority_target(current_queue_rows,current_select_event:gr.SelectData):
    """화면에 관측된 행에서 지원 가능한 원 서비스와 작업 ID를 고른다."""
    from tools.review.common.management_gateway import resolve_management_command
    current_selected_index=current_select_event.index
    if isinstance(current_selected_index,(tuple,list)):
        current_selected_index=current_selected_index[0] if current_selected_index else None
    if type(current_selected_index) is not int or not isinstance(current_queue_rows,list) or not 0<=current_selected_index<len(current_queue_rows):
        raise gr.Error('대기 행을 다시 선택하세요.')
    current_row=current_queue_rows[current_selected_index]
    if not isinstance(current_row,(list,tuple)) or len(current_row) not in (4,5) or not all(isinstance(item,str) for item in current_row):
        raise gr.Error('대기 행을 확인할 수 없습니다.')
    current_gpu_service,current_job_identifier,current_source_service=current_row[1:4]
    from tools.review.common.gpu_job_queue import is_dedicated_gpu_source_verifiable
    if current_gpu_service in ('image','flux-image') or is_dedicated_gpu_source_verifiable(current_gpu_service):
        current_service_name=read_operations_verified_source(current_gpu_service,current_source_service)
        if current_service_name is None:
            return None,'GPU 서비스의 원 서비스가 확인되지 않았습니다. 해당 도구에서 확인하세요.',gr.update(interactive=False)
    else:
        current_service_name='wan22-fun-control' if current_gpu_service=='wan-fun' else current_gpu_service
    try:
        resolve_management_command(current_service_name,'prioritize',{'id':current_job_identifier})
    except (ValueError,TypeError,KeyError):
        return None,'이 서비스의 우선 실행 대상 조회는 지원되지 않습니다.',gr.update(interactive=False)
    return {'service':current_service_name,'id':current_job_identifier},'선택: '+current_service_name+' · '+current_job_identifier+' · 대상 확인을 눌러 현재 대기 상태를 다시 조회하세요.',gr.update(interactive=True)


def preview_operations_priority_target(current_priority_target):
    """게이트웨이에서 대기 대상과 원 서비스를 재확인하며 순서는 바꾸지 않는다."""
    if not isinstance(current_priority_target,dict) or set(current_priority_target)!={'service','id'}:
        raise gr.Error('확인할 대기 작업을 선택하세요.')
    try:
        current_preview=execute_remote_management_command('hermes-agent','hermes-priority-preview',current_priority_target)
        if not isinstance(current_preview,dict) or (current_preview.get('service'),current_preview.get('job_id'))!=(current_priority_target['service'],current_priority_target['id']):
            raise ValueError('대상 불일치')
        current_position,current_count=current_preview.get('queue_position'),current_preview.get('queue_count')
        current_identity_label={'verified':'부팅·시작 식별값 일치','unverified':'미확인'}.get(current_preview.get('executor_identity','unverified'))
        if current_identity_label is None:raise ValueError('실행기 신원 오류')
        if type(current_position) is not int or type(current_count) is not int or not 1<=current_position<=current_count:
            raise ValueError('대기 순번 오류')
        return '대기 대상 확인: '+current_priority_target['service']+' · '+current_priority_target['id']+' · 관측 순번 '+str(current_position)+' / '+str(current_count)+' · 실행기 신원: '+current_identity_label+' · 확인 '+str(current_preview.get('observed_at') or '미제공')+'. 식별값이 빠진 티켓은 실행기 신원을 확인할 수 없습니다. 순서는 변경하지 않았으며 이후 상태가 달라질 수 있습니다.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '대기 대상을 확인할 수 없습니다. 이력을 새로고침하고 원 서비스와 작업 상태를 확인하세요. 순서는 변경하지 않았습니다.'



def prepare_operations_priority_request(current_priority_target):
    """대기 티켓과 기존 접수를 확인하여 명시적인 사용자 검토를 준비한다."""
    try:
        if not isinstance(current_priority_target,dict) or set(current_priority_target)!={'service','id'}:
            raise ValueError('대상 오류')
        current_preview_record=execute_remote_management_command('hermes-agent','hermes-priority-preview',current_priority_target)
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
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-priority-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict):raise ValueError('접수 기록 오류')
        if current_receipt_record.get('state')!='not_found':
            current_expected_record=(current_request_identifier,current_priority_target['service'],current_priority_target['id'],current_ticket_revision)
            if (current_receipt_record.get('request_id'),current_receipt_record.get('service'),current_receipt_record.get('job_id'),current_receipt_record.get('ticket_revision'))!=current_expected_record or current_receipt_record.get('state') not in ('completed','unknown'):
                raise ValueError('접수 대상 오류')
            current_receipt_state=current_receipt_record['state']
            current_receipt_notice='이전에 순서 변경이 접수되었습니다. 현재 순번이나 작업 완료를 뜻하지 않습니다.' if current_receipt_state=='completed' else '이전 요청의 결과를 확인할 수 없습니다. 재요청하지 말고 원 서비스와 대기열을 확인하세요.'
            return None,current_receipt_notice,current_request_identifier,gr.update(visible=False)
        current_review_notice='검토 대상: '+current_priority_target['service']+' · '+current_priority_target['id']+' · 관측 순번 '+str(current_queue_position)+' / '+str(current_queue_count)+' · 실행기 신원: '+current_identity_label+' · 확인 '+str(current_preview_record.get('observed_at') or '미제공')+'. 식별값이 빠진 티켓은 실행기 신원을 확인할 수 없습니다. 확인하면 다른 대기 작업보다 앞서도록 순서를 변경합니다. 실행 중인 GPU 작업은 선점하지 않습니다.'
        return current_request_record,current_review_notice,current_request_identifier,gr.update(visible=True)
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return None,'대상 또는 접수 기록을 확인할 수 없습니다. 원 서비스와 대기열을 확인하세요. 순서는 변경하지 않았습니다.','',gr.update(visible=False)


def start_operations_priority_review():
    """새 우선 실행 검토 전 이전 요청과 확인 창을 지운다."""
    return create_cleanup_preview_token(),gr.update(interactive=False),None,gr.update(visible=False)


def collect_operations_priority_review(current_priority_target,current_request_token):
    """우선 실행 검토 결과와 선택·요청 식별값을 함께 보관한다."""
    return {'target':current_priority_target,'token':current_request_token,'result':prepare_operations_priority_request(current_priority_target)}


def render_operations_priority_review(current_priority_target,current_request_token,current_result_record):
    """대기 행이나 요청이 바뀌었다면 이전 확인 창을 표시하지 않는다."""
    if not isinstance(current_result_record,dict) or (current_result_record.get('target'),current_result_record.get('token'))!=(current_priority_target,current_request_token):return (gr.skip(),)*5
    current_result_values=current_result_record.get('result')
    if not isinstance(current_result_values,(tuple,list)) or len(current_result_values)!=4:return (gr.skip(),)*5
    return (*current_result_values,gr.update(interactive=True))


def submit_operations_priority_request(current_request_record,current_priority_target):
    """사용자가 검토한 요청을 한 번 접수하고 결과 불명을 보수적으로 표시한다."""
    if not isinstance(current_request_record,dict) or not isinstance(current_priority_target,dict) or (current_request_record.get('service'),current_request_record.get('id'))!=(current_priority_target.get('service'),current_priority_target.get('id')):
        return None,'선택한 작업이 바뀌었습니다. 다시 검토하세요.',gr.update(visible=False)
    try:
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-priority-submit',current_request_record)
        current_expected_record=(current_request_record['request_id'],current_request_record['service'],current_request_record['id'],current_request_record['ticket_revision'])
        if not isinstance(current_receipt_record,dict) or (current_receipt_record.get('request_id'),current_receipt_record.get('service'),current_receipt_record.get('job_id'),current_receipt_record.get('ticket_revision'))!=current_expected_record:
            raise ValueError('접수 결과 오류')
        if current_receipt_record.get('state')=='completed':
            return None,'우선 실행 순서 변경이 접수되었습니다. 현재 순번과 작업 완료는 대기열과 원 서비스에서 확인하세요.',gr.update(visible=False)
        if current_receipt_record.get('state')!='unknown':raise ValueError('접수 상태 오류')
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        pass
    return None,'요청 결과를 확인할 수 없습니다. 접수 ID로 조회하고 원 서비스와 대기열을 확인하세요. 자동으로 다시 요청하지 않습니다.',gr.update(visible=False)


def read_operations_priority_request(current_request_identifier):
    """화면을 다시 열어도 접수 ID로 결과를 확인할 수 있다."""
    try:
        if not isinstance(current_request_identifier,str) or not re.fullmatch(r'priority_[a-f0-9]{64}',current_request_identifier):raise ValueError('접수 ID 오류')
        current_receipt_record=execute_remote_management_command('hermes-agent','hermes-priority-receipt',{'request_id':current_request_identifier})
        if not isinstance(current_receipt_record,dict):raise ValueError('접수 오류')
        if current_receipt_record.get('state')=='not_found':return '해당 접수 기록이 없습니다. 요청이 전달되지 않았다는 보장은 아니므로 원 서비스와 대기열을 확인하세요.'
        if current_receipt_record.get('request_id')!=current_request_identifier or current_receipt_record.get('state') not in ('unknown','completed'):raise ValueError('접수 오류')
        current_target_label=str(current_receipt_record.get('service','확인 불가'))+' · '+str(current_receipt_record.get('job_id','확인 불가'))
        if current_receipt_record['state']=='completed':return current_target_label+' · 순서 변경 접수 완료. 현재 순번이나 작업 완료를 뜻하지 않습니다.'
        return current_target_label+' · 결과 확인 필요. 자동 재요청하지 말고 원 서비스와 대기열을 확인하세요.'
    except (OSError,ValueError,KeyError,TypeError,RuntimeError):
        return '접수 기록을 확인할 수 없습니다. 접수 ID와 원 서비스 상태를 확인하세요.'


def reset_operations_history_detail():
    """목록이 바뀌면 이전 작업의 상세와 로그를 지운다."""
    return '', '작업을 선택해 상세를 확인하세요.', '', '', '', '', None


def select_operations_history_job(current_history_rows,current_select_event:gr.SelectData):
    current_selected_index=current_select_event.index
    if isinstance(current_selected_index,(tuple,list)):current_selected_index=current_selected_index[0] if current_selected_index else None
    if type(current_selected_index) is not int or not isinstance(current_history_rows,list) or not 0<=current_selected_index<len(current_history_rows):return reset_operations_history_detail()
    current_selected_row=current_history_rows[current_selected_index]
    if not isinstance(current_selected_row,(list,tuple)) or len(current_selected_row)!=5 or not isinstance(current_selected_row[0],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_selected_row[0]):return reset_operations_history_detail()
    current_job_identifier=current_selected_row[0]
    current_status_text,current_answer_text,current_diff_text,current_log_text,current_result_record,current_original_prompt=refresh_hermes_work_status(current_job_identifier)
    return current_job_identifier,current_status_text,current_original_prompt,current_answer_text,current_diff_text,current_log_text,current_result_record


def build_operations_history_interface():
    with gr.Blocks(title='운영 이력') as current_history_interface:
        gr.Markdown('## 운영 이력\n운영 대화의 지시와 Hermes 작업을 찾아 확인합니다. 생성기 원본 이력은 서비스별 기록으로 확인하며 상세 결과는 각 도구에서 확인하세요.')
        with gr.Row():
            current_search_input=gr.Textbox(label='작업 ID·지시 검색')
            current_status_filter=gr.Dropdown(label='기록 상태',choices=[('전체','전체'),*((current_label,current_name) for current_name,current_label in OPERATIONS_HISTORY_STATUS_LABELS.items())],value='전체')
            current_refresh_button=gr.Button('이력과 대기열 새로고침')
        current_summary_status=gr.Markdown('이력을 확인하고 있습니다.')
        with gr.Accordion('대화 세션',open=True):
            current_session_dropdown=gr.Dropdown(label='세션 선택',choices=[])
            current_initial_session_state=gr.Textbox(value='',visible=False)
            current_session_notice=gr.Markdown()
            current_session_page=gr.State(None)
            current_session_query_token=gr.State(None)
            current_session_query_result=gr.State(None)
            with gr.Row():
                current_session_button=gr.Button('세션 지시 조회')
                current_session_older=gr.Button('이전 지시',interactive=False)
                current_session_newer=gr.Button('최근 지시 쪽',interactive=False)
            current_session_rows=gr.Dataframe(headers=['시각','지시 요약','Hermes 작업 ID','기록 상태','문맥'],datatype=['str']*5,interactive=False,type='array',label='세션 지시')
            current_session_detail_status=gr.Markdown('세션을 선택하세요.')
            current_session_link=gr.HTML()
            current_session_page_outputs=[current_session_rows,current_session_detail_status,current_session_link,current_session_page,current_session_older,current_session_newer]
            current_instruction_text=gr.Textbox(label='선택한 지시 원문',interactive=False,lines=4)
            current_instruction_token=gr.State(None)
            current_instruction_selection=gr.State(None)
            current_instruction_result=gr.State(None)
            current_session_rows.select(prepare_operations_instruction_selection,[current_session_dropdown,current_session_rows,current_session_page],[current_instruction_token,current_instruction_selection,current_session_link,current_instruction_text],queue=False).then(collect_operations_instruction_selection,[current_instruction_selection],[current_instruction_result],queue=False,trigger_mode='multiple').then(render_operations_instruction_selection,[current_session_dropdown,current_session_page,current_instruction_token,current_instruction_result],[current_session_link,current_instruction_text],queue=False)
            current_session_dropdown.change(lambda:(create_cleanup_preview_token(),''),outputs=[current_instruction_token,current_instruction_text],queue=False)
            current_session_dropdown.change(fn=None,inputs=[current_session_dropdown],js="(sessionId)=>{const returnLink=document.querySelector('#management-return-conversation a');if(returnLink)returnLink.setAttribute('href','/management/frame/hermes-agent/'+(/^[a-f0-9]{32}$/.test(sessionId || '')?'?session='+sessionId:''));return sessionId;}",queue=False)
            current_session_button.click(lambda:(create_cleanup_preview_token(),''),outputs=[current_instruction_token,current_instruction_text],queue=False)
            current_session_older.click(lambda:(create_cleanup_preview_token(),''),outputs=[current_instruction_token,current_instruction_text],queue=False)
            current_session_newer.click(lambda:(create_cleanup_preview_token(),''),outputs=[current_instruction_token,current_instruction_text],queue=False)
            current_session_dropdown.change(lambda:(create_cleanup_preview_token(),[],'세션을 선택하고 조회하세요.','',None,gr.update(interactive=False),gr.update(interactive=False),gr.update(interactive=True)),outputs=[current_session_query_token,*current_session_page_outputs,current_session_button],queue=False)
            with gr.Accordion('이전 세션 찾기',open=False):
                gr.Markdown('최근 100개보다 오래된 세션도 조회합니다. 지시 내용이나 세션 ID로 검색할 수 있습니다.')
                current_old_session_query=gr.Textbox(label='지시·세션 ID 검색',placeholder='기억나는 지시나 세션 ID · 선택')
                current_old_session_state=gr.State(None)
                with gr.Row():
                    current_old_session_first=gr.Button('세션 목록 처음부터 조회')
                    current_old_session_older=gr.Button('이전 세션',interactive=False)
                    current_old_session_newer=gr.Button('최근 세션 쪽',interactive=False)
                current_old_session_notice=gr.Markdown('세션 목록을 조회하세요.')
                current_old_session_table=gr.Dataframe(headers=['마지막 갱신','세션 ID','지시 수'],datatype=['str']*3,interactive=False,type='array',label='페이지별 세션')
                current_old_session_outputs=[current_old_session_table,current_old_session_notice,current_old_session_state,current_old_session_older,current_old_session_newer]
                current_old_session_first.click(read_operations_session_page,[current_old_session_query],current_old_session_outputs,queue=False)
                current_old_session_older.click(read_older_operations_session_page,[current_old_session_query,current_old_session_state],current_old_session_outputs,queue=False)
                current_old_session_newer.click(read_newer_operations_session_page,[current_old_session_query,current_old_session_state],current_old_session_outputs,queue=False)
                current_old_session_query.input(lambda:([],'검색 조건이 바뀌었습니다. 처음부터 다시 조회하세요.',None,gr.update(interactive=False),gr.update(interactive=False)),outputs=current_old_session_outputs,queue=False)
                current_old_session_table.select(select_operations_older_session,[current_old_session_table],[current_session_dropdown,current_session_notice],queue=False)
            current_receipt_button=gr.Button('표시된 지시의 접수 기록 조회')
            current_receipt_table=gr.Dataframe(headers=['Hermes 작업 ID','서비스','대화 접수 ID','접수 관측','서비스 작업 ID','GPU 대기 관측','GPU 예약 관측','작가 적용 관측'],datatype=['str']*8,interactive=False,type='array',label='제안과 접수 기록')
            current_receipt_notice=gr.Markdown('세션을 선택하고 조회하세요.')
            gr.Markdown('접수 행을 선택하면 해당 도구의 이력을 열 수 있습니다.')
            current_receipt_link=gr.HTML()
            current_receipt_token=gr.State(None)
            current_receipt_result=gr.State(None)
            current_receipt_table.select(select_operations_receipt_service,[current_receipt_table,current_session_dropdown],[current_receipt_link],queue=False)
            current_receipt_button.click(lambda:(create_cleanup_preview_token(),gr.update(interactive=False)),outputs=[current_receipt_token,current_receipt_button],queue=False).then(collect_operations_page_receipts,[current_session_dropdown,current_session_page,current_receipt_token],[current_receipt_result],queue=False).then(render_operations_page_receipts,[current_session_dropdown,current_session_page,current_receipt_token,current_receipt_result],[current_receipt_table,current_receipt_notice,current_receipt_link,current_receipt_button],queue=False)
            for current_page_button,current_page_direction in ((current_session_button,'first'),(current_session_older,'older'),(current_session_newer,'newer')):
                current_page_button.click(lambda:(create_cleanup_preview_token(),create_cleanup_preview_token(),gr.update(interactive=False),gr.update(interactive=False),gr.update(interactive=False),gr.update(interactive=True)),outputs=[current_session_query_token,current_receipt_token,current_session_button,current_session_older,current_session_newer,current_receipt_button],queue=False).then(lambda current_session,current_page,current_token,current_direction=current_page_direction:collect_operations_session_page(current_session,current_page,current_token,current_direction),[current_session_dropdown,current_session_page,current_session_query_token],[current_session_query_result],queue=False).then(render_operations_session_page,[current_session_dropdown,current_session_query_token,current_session_query_result],[*current_session_page_outputs,current_receipt_table,current_receipt_notice,current_receipt_link,current_session_button],queue=False)
            current_session_dropdown.change(lambda:(create_cleanup_preview_token(),[],'세션을 선택하고 조회하세요.','',gr.update(interactive=True)),outputs=[current_receipt_token,current_receipt_table,current_receipt_notice,current_receipt_link,current_receipt_button],queue=False)
        with gr.Accordion('Hermes 작업 이력',open=True):
            current_history_notice=gr.Markdown()
            current_history_table=gr.Dataframe(headers=['작업 ID','기록 상태','GPU 대기 관측','지시 요약','GPU 예약 관측'],datatype=['str']*5,interactive=False,type='array',label='Hermes 작업')
            gr.Markdown('행을 선택하면 원본 작업의 상세를 읽습니다. 대기 기록이 없어도 완료를 뜻하지 않습니다.')
            current_job_identifier=gr.Textbox(label='작업 ID',interactive=False)
            current_job_status=gr.Markdown()
            current_job_prompt=gr.Textbox(label='작업에 전달된 지시',interactive=False,lines=3)
            current_job_answer=gr.Textbox(label='Hermes 응답',interactive=False,lines=3)
            current_job_diff=gr.Code(label='변경 diff',interactive=False)
            current_job_log=gr.Textbox(label='작업 로그',interactive=False,lines=4)
            current_job_result=gr.JSON(label='검증과 실행 결과')
            current_history_detail_outputs=[current_job_identifier,current_job_status,current_job_prompt,current_job_answer,current_job_diff,current_job_log,current_job_result]
            current_history_table.select(select_operations_history_job,[current_history_table],current_history_detail_outputs,queue=False)
            with gr.Accordion('이전 Hermes 작업 찾기',open=False) as current_job_page_accordion:
                gr.Markdown('최근 100건보다 이전 기록도 페이지별로 조회합니다. 위 검색어와 상태 필터는 전체 작업 이력에 적용됩니다.')
                current_job_page_state=gr.State(None)
                with gr.Row():
                    current_job_page_first=gr.Button('작업 목록 처음부터 조회')
                    current_job_page_older=gr.Button('이전 작업',interactive=False)
                    current_job_page_newer=gr.Button('최근 작업 쪽',interactive=False)
                current_job_page_notice=gr.Markdown('작업 목록을 조회하세요.')
                current_job_page_table=gr.Dataframe(headers=['작업 ID','기록 상태','GPU 대기 관측','지시 요약','GPU 예약 관측'],datatype=['str']*5,interactive=False,type='array',label='페이지별 Hermes 작업')
                current_job_page_outputs=[current_job_page_table,current_job_page_notice,current_job_page_state,current_job_page_older,current_job_page_newer]
                current_job_page_first.click(read_operations_job_history_page,[current_search_input,current_status_filter],current_job_page_outputs,queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
                current_job_page_older.click(read_older_operations_job_history,[current_search_input,current_status_filter,current_job_page_state],current_job_page_outputs,queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
                current_job_page_newer.click(read_newer_operations_job_history,[current_search_input,current_status_filter,current_job_page_state],current_job_page_outputs,queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
                current_job_page_table.select(select_operations_history_job,[current_job_page_table],current_history_detail_outputs,queue=False)
                for current_filter_control in (current_search_input,current_status_filter):
                    current_filter_control.input(lambda:([],'검색 조건이 바뀌었습니다. 처음부터 다시 조회하세요.',None,gr.update(interactive=False),gr.update(interactive=False)),outputs=current_job_page_outputs,queue=False)
        with gr.Accordion('생성기 원본 이력',open=False):
            gr.Markdown('운영 대화 밖에서 시작한 작업도 원래 서비스의 기록 상태로 조회합니다. 상태 확인 시 생성기를 실행하거나 작업을 복구하지 않습니다.')
            current_source_service=gr.Dropdown(label='원본 서비스',choices=list(dict.fromkeys((*SOURCE_HISTORY_GENERATOR_SERVICES,*SOURCE_HISTORY_AUDIO_SERVICES))),value='kimodo')
            current_source_state=gr.State(None)
            current_source_search=gr.Textbox(label='작업 ID 검색',placeholder='작업 ID 일부 입력 후 조회')
            with gr.Row():
                current_source_refresh=gr.Button('원본 이력 조회')
                current_source_previous=gr.Button('이전 이력',interactive=False)
                current_source_next=gr.Button('다음 이력',interactive=False)
            with gr.Accordion('이력 정리 대상 확인',open=False):
                gr.Markdown('삭제하지 않고 후보와 차단 수만 확인합니다. 숨긴 작업까지 전체 순회하므로 이력이 많으면 시간이 걸릴 수 있습니다.')
                current_cleanup_preview_button=gr.Button('정리 대상 요약 조회')
                current_cleanup_preview_notice=gr.Markdown('서비스를 선택한 뒤 조회하세요.')
                current_cleanup_preview_state=gr.State(None)
                current_cleanup_preview_token=gr.State(None)
                current_cleanup_preview_button.click(create_cleanup_preview_token,outputs=current_cleanup_preview_token,queue=False).then(collect_operations_cleanup_preview,[current_source_service,current_cleanup_preview_token],[current_cleanup_preview_state],queue=False).then(render_operations_cleanup_preview,[current_source_service,current_cleanup_preview_token,current_cleanup_preview_state],[current_cleanup_preview_notice],queue=False)
                current_source_service.change(lambda:(create_cleanup_preview_token(),'서비스가 바뀌었습니다. 다시 조회하세요.'),outputs=[current_cleanup_preview_token,current_cleanup_preview_notice],queue=False)
            current_source_notice=gr.Markdown('원본 서비스를 선택하고 조회하세요.')
            current_source_table=gr.Dataframe(headers=['작업 ID','기록 상태','상태 출처','GPU 대기 관측','GPU 예약 관측'],datatype=['str']*5,interactive=False,type='array',label='생성기 원본 작업')
            current_source_selected_id=gr.Textbox(label='선택한 원본 작업 ID',interactive=False)
            current_source_link=gr.HTML()
            current_source_outputs=[current_source_table,current_source_notice,current_source_state,current_source_next,current_source_link,current_source_previous]
            current_source_refresh.click(lambda current_service_name,current_search_text:render_operations_source_history_page(current_service_name,current_search_text=current_search_text),[current_source_service,current_source_search],current_source_outputs,queue=False).then(lambda:'',outputs=current_source_selected_id,queue=False)
            current_source_next.click(lambda current_service_name,current_page_state,current_search_text:render_operations_source_history_page(current_service_name,current_page_state,'next',current_search_text),[current_source_service,current_source_state,current_source_search],current_source_outputs,queue=False).then(lambda:'',outputs=current_source_selected_id,queue=False)
            current_source_previous.click(lambda current_service_name,current_page_state,current_search_text:render_operations_source_history_page(current_service_name,current_page_state,'previous',current_search_text),[current_source_service,current_source_state,current_source_search],current_source_outputs,queue=False).then(lambda:'',outputs=current_source_selected_id,queue=False)
            current_source_service.change(lambda:([],'서비스가 바뀌었습니다. 원본 이력을 조회하세요.',None,gr.update(interactive=False),'',gr.update(interactive=False)),outputs=current_source_outputs,queue=False).then(lambda:'',outputs=current_source_selected_id,queue=False)
            current_source_search.input(lambda:([],'검색 조건이 바뀌었습니다. 원본 이력을 조회하세요.',None,gr.update(interactive=False),'',gr.update(interactive=False)),outputs=current_source_outputs,queue=False).then(lambda:'',outputs=current_source_selected_id,queue=False)
            current_source_table.select(select_operations_source_job,[current_source_service,current_source_state,current_source_table,current_session_dropdown],[current_source_selected_id,current_source_link],queue=False)
            current_session_dropdown.change(lambda:'',outputs=current_source_link,queue=False)
            gr.Markdown('### 생성·번역 작업 재개\nFLUX·Kimodo·음악·효과음·번역 원본 이력에서 실패·취소·일시정지된 작업을 선택하고 대상을 확인하세요.')
            current_audio_resume_record=gr.State(None)
            current_audio_resume_status=gr.Markdown('원본 작업을 선택하세요.')
            current_audio_resume_preview=gr.Button('재개 대상 검토')
            current_audio_resume_submit=gr.Button('검토한 작업 대기열에 추가',interactive=False)
            current_audio_resume_identifier=gr.Textbox(label='재개 접수 ID · 선택한 서비스에서 결과 확인')
            current_audio_resume_receipt_button=gr.Button('재개 접수 확인')
            current_audio_resume_receipt_notice=gr.Markdown()
            current_audio_resume_event=current_audio_resume_preview.click(prepare_operations_audio_resume,[current_source_service,current_source_selected_id,current_source_state,current_source_table],[current_audio_resume_record,current_audio_resume_status,current_audio_resume_identifier],queue=False)
            from tools.review.common.gradio_gpu_confirmation import bind_gpu_generation_confirmation
            from tools.review.ui.gradio.hermes_agent_app import match_hermes_confirmation_inputs
            bind_gpu_generation_confirmation(current_audio_resume_submit,submit_operations_audio_resume,[current_audio_resume_record,current_source_service,current_source_selected_id,current_source_state,current_source_table],[current_audio_resume_record,current_audio_resume_status],generation_readiness_callback=lambda current_record_value:bool(current_record_value),generation_readiness_inputs=[current_audio_resume_record],generation_readiness_events=[current_audio_resume_event],generation_confirmation_validator=match_hermes_confirmation_inputs,generation_confirmation_inputs=[current_audio_resume_record,current_source_service,current_source_selected_id,current_source_state,current_source_table])
            current_audio_resume_receipt_button.click(read_operations_audio_resume_receipt,[current_audio_resume_identifier,current_source_service],[current_audio_resume_receipt_notice],queue=False)
            for current_audio_resume_control in (current_source_service,current_source_selected_id):
                current_audio_resume_control.change(lambda:None,outputs=current_audio_resume_record,queue=False)
            for current_audio_resume_button in (current_source_refresh,current_source_previous,current_source_next):
                current_audio_resume_button.click(lambda:None,outputs=current_audio_resume_record,queue=False)
            current_source_search.input(lambda:None,outputs=current_audio_resume_record,queue=False)
            current_source_table.select(lambda:None,outputs=current_audio_resume_record,queue=False)
        with gr.Accordion('GPU 대기열 관측',open=True):
            current_queue_notice=gr.Markdown()
            current_queue_table=gr.Dataframe(headers=['관측 순번','GPU 서비스','작업 ID','확인된 원 서비스','캡처 접수 ID'],datatype=['str']*5,interactive=False,type='array',label='현재 대기 기록')
            current_capture_queue_notice=gr.Markdown('캡처 대기 기록을 선택하면 접수 상태를 확인합니다.')
            current_queue_table.select(read_operations_selected_capture_status,[current_queue_table],current_capture_queue_notice,queue=False)
            current_queue_table.change(lambda:'캡처 대기 기록을 선택하면 접수 상태를 확인합니다.',outputs=current_capture_queue_notice,queue=False)
            gr.Markdown('대기열은 실행 중 작업이나 전체 이력이 아닙니다. 예약과 GPU 프로세스는 상단의 GPU 정보에서 별도로 확인하세요.')
            gr.Markdown('대기 행을 선택하고 현재 상태를 검토한 뒤 우선 실행을 요청할 수 있습니다.')
            current_priority_target=gr.State(None)
            current_priority_request=gr.State(None)
            current_priority_review_token=gr.State(None)
            current_priority_review_result=gr.State(None)
            current_priority_status=gr.Markdown('대기 행을 선택하세요.')
            current_priority_preview=gr.Button('우선 실행 대상 확인',interactive=False)
            with gr.Group(visible=False) as current_priority_confirmation:
                gr.Markdown('대기 순서를 변경하시겠습니까? 다른 대기 작업의 순서가 뒤로 밀릴 수 있습니다.')
                with gr.Row():
                    current_priority_confirm=gr.Button('확인하고 우선 실행',variant='primary')
                    current_priority_cancel=gr.Button('취소')
            current_priority_receipt_id=gr.Textbox(label='우선 실행 접수 ID · 결과 확인용',placeholder='접수 ID를 보관하거나 입력하세요')
            current_priority_receipt_button=gr.Button('우선 실행 접수 결과 조회')
            current_priority_receipt_notice=gr.Markdown()
            current_queue_table.select(select_operations_priority_target,[current_queue_table],[current_priority_target,current_priority_status,current_priority_preview],queue=False).then(lambda:(create_cleanup_preview_token(),None,gr.update(visible=False)),outputs=[current_priority_review_token,current_priority_request,current_priority_confirmation],queue=False)
            current_queue_table.change(lambda:(create_cleanup_preview_token(),None,None,'대기 행을 다시 선택하세요.',gr.update(interactive=False),gr.update(visible=False)),outputs=[current_priority_review_token,current_priority_target,current_priority_request,current_priority_status,current_priority_preview,current_priority_confirmation],queue=False)
            current_priority_preview.click(start_operations_priority_review,outputs=[current_priority_review_token,current_priority_preview,current_priority_request,current_priority_confirmation],queue=False).then(collect_operations_priority_review,[current_priority_target,current_priority_review_token],[current_priority_review_result],queue=False,trigger_mode='multiple').then(render_operations_priority_review,[current_priority_target,current_priority_review_token,current_priority_review_result],[current_priority_request,current_priority_status,current_priority_receipt_id,current_priority_confirmation,current_priority_preview],queue=False)
            current_priority_confirm.click(submit_operations_priority_request,[current_priority_request,current_priority_target],[current_priority_request,current_priority_status,current_priority_confirmation],queue=False)
            current_priority_cancel.click(lambda:(None,'우선 실행 요청을 취소했습니다. 순서는 변경하지 않았습니다.',gr.update(visible=False)),outputs=[current_priority_request,current_priority_status,current_priority_confirmation],queue=False)
            current_priority_receipt_button.click(read_operations_priority_request,[current_priority_receipt_id],[current_priority_receipt_notice],queue=False)
        with gr.Accordion('GPU 예약 기록',open=True):
            current_reservation_notice=gr.Markdown()
            current_reservation_table=gr.Dataframe(headers=['기록 상태','GPU 서비스','작업 ID','예약 MiB','작업자 리더','확인된 원 서비스'],datatype=['str']*6,interactive=False,type='array',label='GPU 예약 기록')
            gr.Markdown('리더 확인은 같은 그룹 전체나 별도 그룹의 프로세스 종료를 증명하지 않습니다. 예약 정리는 별도 확인 후에만 실행합니다.')
            current_reservation_target=gr.State(None)
            current_reservation_inspect_button=gr.Button('선택한 생성기 예약 신원 확인',interactive=False)
            current_reservation_inspect_notice=gr.Markdown('예약 신원 조회는 프로세스를 종료하거나 예약을 해제하지 않습니다.')
            current_reservation_request=gr.State(None)
            current_reservation_review_token=gr.State(None)
            current_reservation_review_result=gr.State(None)
            current_reservation_recovery_button=gr.Button('선택한 예약 정리 검토')
            current_reservation_recovery_notice=gr.Markdown('예약을 선택하고 정리 가능 여부를 검토하세요.')
            with gr.Group(visible=False) as current_reservation_confirmation:
                gr.Markdown('확인하면 선택된 작업자 그룹을 강제 종료하고 GPU 예약을 해제합니다. 별도 그룹의 GPU 프로세스는 종료하거나 확인하지 않습니다.')
                current_reservation_outside_checked=gr.Checkbox(label='별도 그룹의 GPU 프로세스를 직접 확인했습니다',value=False)
                with gr.Row():
                    current_reservation_confirm=gr.Button('확인하고 예약 정리',variant='primary')
                    current_reservation_cancel=gr.Button('취소')
            current_reservation_receipt_id=gr.Textbox(label='예약 정리 접수 ID · 결과 확인용')
            current_reservation_receipt_button=gr.Button('예약 정리 접수 결과 조회')
            current_reservation_receipt_notice=gr.Markdown()
            current_reservation_link=gr.HTML('<p>예약 행을 선택하면 확인된 원 서비스로 이동할 수 있습니다.</p>')
            current_reservation_table.select(select_operations_reservation_target,[current_reservation_table],[current_reservation_link],queue=False)
            current_reservation_table.change(lambda:'',outputs=current_reservation_link,queue=False)
            current_reservation_table.select(select_operations_reservation_inspection,[current_reservation_table],[current_reservation_target,current_reservation_inspect_button,current_reservation_inspect_notice],queue=False)
            current_reservation_inspect_button.click(inspect_operations_reservation_target,[current_reservation_target],[current_reservation_inspect_notice],queue=False)
            current_reservation_table.change(lambda:(None,gr.update(interactive=False),'예약 행을 다시 선택하세요.'),outputs=[current_reservation_target,current_reservation_inspect_button,current_reservation_inspect_notice],queue=False)
            current_reservation_recovery_button.click(start_operations_reservation_review,outputs=[current_reservation_review_token,current_reservation_recovery_button,current_reservation_request,current_reservation_confirmation,current_reservation_outside_checked],queue=False).then(collect_operations_reservation_recovery,[current_reservation_target,current_reservation_review_token],[current_reservation_review_result],queue=False,trigger_mode='multiple').then(render_operations_reservation_recovery,[current_reservation_target,current_reservation_review_token,current_reservation_review_result],[current_reservation_request,current_reservation_recovery_notice,current_reservation_receipt_id,current_reservation_confirmation,current_reservation_outside_checked,current_reservation_recovery_button],queue=False)
            current_reservation_confirm.click(submit_operations_reservation_recovery,[current_reservation_request,current_reservation_target,current_reservation_outside_checked],[current_reservation_request,current_reservation_recovery_notice,current_reservation_confirmation],queue=False)
            current_reservation_cancel.click(lambda:(None,'예약 정리 요청을 취소했습니다.',gr.update(visible=False),False),outputs=[current_reservation_request,current_reservation_recovery_notice,current_reservation_confirmation,current_reservation_outside_checked],queue=False)
            current_reservation_receipt_button.click(read_operations_reservation_recovery_receipt,[current_reservation_receipt_id],[current_reservation_receipt_notice],queue=False)
            current_reservation_table.select(lambda:(create_cleanup_preview_token(),None,gr.update(visible=False),False,gr.update(interactive=True)),outputs=[current_reservation_review_token,current_reservation_request,current_reservation_confirmation,current_reservation_outside_checked,current_reservation_recovery_button],queue=False)
            current_reservation_table.change(lambda:(create_cleanup_preview_token(),None,gr.update(visible=False),False,gr.update(interactive=True)),outputs=[current_reservation_review_token,current_reservation_request,current_reservation_confirmation,current_reservation_outside_checked,current_reservation_recovery_button],queue=False)

        current_overview_outputs=[current_session_dropdown,current_session_notice,current_history_table,current_history_notice,current_queue_table,current_queue_notice,current_summary_status,current_reservation_table,current_reservation_notice]
        current_refresh_button.click(read_operations_history_overview,[current_search_input,current_status_filter,current_session_dropdown],current_overview_outputs,queue=False).then(lambda:(None,'대기 행을 선택하세요.',gr.update(interactive=False),None,gr.update(visible=False)),outputs=[current_priority_target,current_priority_status,current_priority_preview,current_priority_request,current_priority_confirmation],queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
        current_search_input.submit(read_operations_history_overview,[current_search_input,current_status_filter,current_session_dropdown],current_overview_outputs,queue=False).then(lambda:(None,'대기 행을 선택하세요.',gr.update(interactive=False),None,gr.update(visible=False)),outputs=[current_priority_target,current_priority_status,current_priority_preview,current_priority_request,current_priority_confirmation],queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
        current_status_filter.input(read_operations_history_overview,[current_search_input,current_status_filter,current_session_dropdown],current_overview_outputs,queue=False).then(lambda:(None,'대기 행을 선택하세요.',gr.update(interactive=False),None,gr.update(visible=False)),outputs=[current_priority_target,current_priority_status,current_priority_preview,current_priority_request,current_priority_confirmation],queue=False).then(reset_operations_history_detail,outputs=current_history_detail_outputs,queue=False)
        current_history_interface.load(validate_operations_history_link,[current_search_input,current_initial_session_state],[current_search_input,current_initial_session_state],js="(searchValue,sessionValue)=>{const params=new URL(window.location.href).searchParams;return [params.get('job') || searchValue || '',params.get('session') || sessionValue || null]}",queue=False).then(read_operations_history_overview,[current_search_input,current_status_filter,current_initial_session_state],current_overview_outputs,queue=False).then(read_linked_operations_history_page,[current_search_input,current_status_filter],[*current_job_page_outputs,current_job_page_accordion],queue=False)
    return current_history_interface
