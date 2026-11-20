"""기존 음악·효과음 생성기의 GPU 작업을 안전하게 위임한다."""
import os
import re
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
from tools.review.domains.hermes_agent.failure_observer import observe_hermes_generator_failure

HERMES_AUDIO_SERVICES = ('music-heartmula','sfx-dasheng-audiogen')


def validate_hermes_audio_service(current_service_name):
    if not isinstance(current_service_name,str) or current_service_name not in HERMES_AUDIO_SERVICES:
        raise ValueError('지원하는 음악 또는 효과음 서비스가 아닙니다.')


def call_hermes_audio_service(current_service_name,current_command_name,current_payload_record):
    validate_hermes_audio_service(current_service_name)
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command(current_service_name,current_command_name,current_payload_record,current_gateway_address)


def validate_hermes_audio_request(current_service_name,current_request_record):
    from generators.music.contracts import validate_music_request
    validate_hermes_audio_service(current_service_name)
    if not isinstance(current_request_record,dict) or current_request_record.get('action','generate')!='generate':
        raise ValueError('오디오 위임에는 생성 요청만 허용합니다.')
    validate_music_request(current_service_name,current_request_record)


def submit_hermes_audio_request(current_request_identifier,current_service_name,current_request_record):
    validate_hermes_audio_service(current_service_name)
    return HermesDelegationStore().execute_service_delegation_once(current_request_identifier,current_service_name,current_request_record,
        lambda current_request_value:call_hermes_audio_service(current_service_name,'generate',current_request_value),
        lambda current_request_value:validate_hermes_audio_request(current_service_name,current_request_value))


def read_hermes_audio_status(current_request_identifier,current_service_name):
    validate_hermes_audio_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted':
        return {'receipt':current_receipt_value}
    current_job_value=call_hermes_audio_service(current_service_name,'status',{'id':current_receipt_value['job_id']})
    if not isinstance(current_job_value,dict) or current_job_value.get('id')!=current_receipt_value['job_id']:
        raise ValueError('오디오 작업 상태 응답 형식 오류')
    current_status_value=current_job_value.get('status')
    if current_status_value not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown'):
        current_status_value='unknown'
    from tools.review.domains.hermes_agent.media_result_paths import validate_hermes_audio_result_path
    current_audio_path=validate_hermes_audio_result_path(current_service_name,current_receipt_value['job_id'],{**current_job_value,'status':current_status_value})
    current_result_status='available' if current_audio_path else 'unavailable' if current_status_value=='completed' else 'not_ready'
    return {'receipt':current_receipt_value,'job':{'status':current_status_value,'audio':current_audio_path,'result_status':current_result_status,
        'note':'완료 결과와 상세 로그·분리 음원은 해당 생성기 이력에서 확인하세요. 생성 결과는 자동으로 에셋에 등록되지 않습니다.', **observe_hermes_generator_failure(current_status_value,current_job_value.get('error'))}}


def list_hermes_audio_receipts(current_service_name):
    validate_hermes_audio_service(current_service_name)
    return HermesDelegationStore().list_service_delegations(current_service_name)


def cancel_hermes_audio_request(current_request_identifier,current_service_name,current_job_identifier):
    validate_hermes_audio_service(current_service_name)
    current_receipt_value=HermesDelegationStore().read_service_delegation(current_request_identifier,current_service_name)
    if current_receipt_value.get('state')!='accepted' or current_receipt_value.get('job_id')!=current_job_identifier:
        raise ValueError('접수 기록과 확인한 오디오 작업 ID가 일치하지 않습니다.')
    current_cancel_value=call_hermes_audio_service(current_service_name,'cancel',{'id':current_job_identifier})
    if (not isinstance(current_cancel_value,dict) or current_cancel_value.get('cancel_requested') is not True
            or ('id' in current_cancel_value and current_cancel_value['id']!=current_job_identifier)):
        raise ValueError('오디오 중지 응답 형식 오류')
    return {'job_id':current_job_identifier,'cancel_requested':True,'status':current_cancel_value.get('status','unknown')}



def read_hermes_audio_source_history(current_service_name,current_page_request):
    """기존 서비스의 기록 상태만 읽는다. 접수 ID나 입력·로그를 만들지 않는다."""
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_AUDIO_SERVICES
    if not isinstance(current_service_name,str) or current_service_name not in SOURCE_HISTORY_AUDIO_SERVICES:
        raise ValueError('지원하는 오디오 이력 서비스가 아닙니다.')
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_result_value=execute_management_command(current_service_name,'history-observe',current_page_request,current_gateway_address)
    return sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value)


def sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value):
    """기존 서비스 응답에서 ID·기록 상태와 페이지 정보만 허용한다."""
    if not isinstance(current_result_value,dict) or not isinstance(current_result_value.get('records'),list):
        raise ValueError('오디오 원본 이력 응답 오류')
    current_query_text=current_page_request.get('query','')
    if not isinstance(current_query_text,str) or len(current_query_text)>80 or (current_query_text and not re.fullmatch(r'[A-Za-z0-9_-]+',current_query_text)):
        raise ValueError('생성기 이력 검색어 오류')
    current_query_text=current_query_text.casefold()
    current_safe_records=[]
    for current_record_value in current_result_value['records']:
        if not isinstance(current_record_value,dict) or not isinstance(current_record_value.get('id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_record_value['id']) or current_record_value.get('recorded_status') not in ('queued','running','completed','failed','cancelled','canceled','paused','unknown','preparing','indexing','searching','reasoning','review','applied','interrupted'):
            raise ValueError('오디오 이력 레코드 오류')
        if current_query_text and current_query_text not in current_record_value['id'].casefold():raise ValueError('검색 결과 ID 불일치')
        current_status_source=current_record_value.get('status_source')
        if current_status_source not in ('job','index','unavailable') or (current_status_source=='unavailable' and current_record_value['recorded_status']!='unknown'):
            raise ValueError('생성기 이력 상태 출처 오류')
        current_safe_records.append({'id':current_record_value['id'],'recorded_status':current_record_value['recorded_status'],'status_source':current_status_source})
    current_total_value=current_result_value.get('total')
    current_offset_value=current_result_value.get('offset')
    current_next_offset=current_result_value.get('next_offset')
    current_snapshot_value=current_result_value.get('snapshot')
    current_unavailable_count=current_result_value.get('unavailable_count')
    current_request_offset=current_page_request.get('offset',0)
    current_request_limit=current_page_request.get('limit',10)
    current_request_snapshot=current_page_request.get('snapshot')
    if (type(current_request_offset) is not int or current_request_offset<0 or type(current_request_limit) is not int or not 1<=current_request_limit<=30
            or type(current_unavailable_count) is not int or current_unavailable_count<0 or type(current_total_value) is not int or current_total_value<0 or type(current_offset_value) is not int or current_offset_value!=current_request_offset
            or not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)
            or (current_request_snapshot is not None and current_snapshot_value!=current_request_snapshot)):
        raise ValueError('생성기 이력 페이지 오류')
    current_expected_count=min(current_request_limit,max(0,current_total_value-current_offset_value))
    current_expected_next=current_offset_value+current_expected_count if current_offset_value+current_expected_count<current_total_value else None
    if (len(current_safe_records)!=current_expected_count or len({current_record['id'] for current_record in current_safe_records})!=len(current_safe_records)
            or current_next_offset!=current_expected_next or (current_next_offset is not None and type(current_next_offset) is not int)):
        raise ValueError('생성기 이력 페이지 오류')
    return {'service':current_service_name,'records':current_safe_records,'total':current_total_value,'offset':current_offset_value,'next_offset':current_next_offset,'snapshot':current_snapshot_value,'unavailable_count':current_unavailable_count,'note':'기록 상태이며 실제 작업 생존과 결과 품질은 해당 생성기에서 확인하세요. 확인 불가 수에는 손상 색인과 중복 ID가 포함될 수 있습니다.'}



def read_hermes_generator_source_history(current_service_name,current_page_request):
    """이미지·영상·번역·작가 서비스의 원본 이력에서 기록 상태만 관측한다."""
    from tools.review.common.source_history_catalog import SOURCE_HISTORY_GENERATOR_SERVICES,SOURCE_HISTORY_SERVICE_ALIASES
    if not isinstance(current_service_name,str) or current_service_name not in SOURCE_HISTORY_GENERATOR_SERVICES:
        raise ValueError('지원하는 이미지·영상 생성기가 아닙니다.')
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_command_name='writer-history-observe' if current_service_name=='writer-agent' else 'history-observe'
    current_result_value=execute_management_command(current_service_name,current_command_name,current_page_request,current_gateway_address)
    current_sanitized_value=sanitize_hermes_source_history(current_service_name,current_page_request,current_result_value)
    current_sanitized_value['source_service']=SOURCE_HISTORY_SERVICE_ALIASES.get(current_service_name,current_service_name)
    if current_service_name=='building-generator':
        current_sanitized_value['note']+=' 건물 생성기는 빌보드 생성기 이력을 공유하는 호환 경로입니다.'
    return current_sanitized_value
