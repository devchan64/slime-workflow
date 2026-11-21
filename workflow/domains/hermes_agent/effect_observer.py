"""맵 이펙트 편집기의 목록과 좌표를 제한된 형태로 조회한다."""
import json
import math
import os
import re
from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from workflow.common.management_gateway import execute_management_command

EFFECT_IDENTIFIER_PATTERN = re.compile(r'[a-z][a-z0-9-]{0,95}')


def call_hermes_effect_editor(current_command_name,current_payload_record):
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('map-assets',current_command_name,current_payload_record,current_gateway_address)


def list_hermes_effect_catalog(current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'query','offset','limit'}:
        raise ValueError('이펙트 검색에는 query·offset·limit만 허용합니다.')
    current_query_text=current_request_record.get('query','')
    current_offset_value=current_request_record.get('offset',0)
    current_limit_value=current_request_record.get('limit',20)
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or any(ord(current_character_value)<32 for current_character_value in current_query_text):
        raise ValueError('검색어는 100자 이하 한 줄이어야 합니다.')
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('목록 위치 또는 개수 오류')
    current_response_record=call_hermes_effect_editor('effect-list',{})
    if not isinstance(current_response_record,dict) or not isinstance(current_response_record.get('effects'),list) or len(current_response_record['effects'])>1000:
        raise ValueError('이펙트 목록 응답 오류')
    current_effect_records=[]
    current_seen_identifiers=set()
    for current_effect_record in current_response_record['effects']:
        if not isinstance(current_effect_record,dict):raise ValueError('이펙트 항목 오류')
        current_effect_identifier=current_effect_record.get('id')
        current_effect_name=current_effect_record.get('name')
        if not isinstance(current_effect_identifier,str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_effect_identifier) or current_effect_identifier in current_seen_identifiers or not isinstance(current_effect_name,str) or not 1<=len(current_effect_name)<=200:
            raise ValueError('이펙트 ID·이름 오류')
        current_seen_identifiers.add(current_effect_identifier)
        if current_query_text.strip().casefold() in (current_effect_identifier+' '+current_effect_name).casefold():
            current_effect_records.append({'id':current_effect_identifier,'name':current_effect_name})
    current_total_count=len(current_effect_records)
    return {'items':current_effect_records[current_offset_value:current_offset_value+current_limit_value],'total':current_total_count,'offset':current_offset_value,'limit':current_limit_value,'next_offset':current_offset_value+current_limit_value if current_offset_value+current_limit_value<current_total_count else None,'note':'검수 가능한 DB 이펙트 목록입니다. 조회는 로컬 잠금을 사용할 수 있습니다.'}


def read_hermes_effect_detail(current_effect_identifier):
    if not isinstance(current_effect_identifier,str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_effect_identifier):
        raise ValueError('이펙트 ID 오류')
    current_response_record=call_hermes_effect_editor('effect-load',{'id':current_effect_identifier})
    if not isinstance(current_response_record,dict) or not isinstance(current_response_record.get('document'),dict):
        raise ValueError('이펙트 상세 응답 오류')
    current_effect_record=current_response_record['document']
    current_revision_value=current_response_record.get('revision')
    if current_effect_record.get('id')!=current_effect_identifier or not isinstance(current_revision_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_revision_value):
        raise ValueError('이펙트 ID·리비전 오류')
    current_name_value=current_effect_record.get('name')
    current_renderer_value=current_effect_record.get('renderer')
    if not isinstance(current_name_value,str) or not 1<=len(current_name_value)<=200 or not isinstance(current_renderer_value,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}',current_renderer_value):
        raise ValueError('이펙트 이름·렌더러 오류')
    current_result_record={'id':current_effect_identifier,'name':current_name_value,'renderer':current_renderer_value,'revision':current_revision_value}
    for current_count_name in ('rows','columns','frames'):
        current_count_value=current_effect_record.get(current_count_name)
        if type(current_count_value) is not int or not 1<=current_count_value<=256:raise ValueError('이펙트 시트 크기 오류')
        current_result_record[current_count_name]=current_count_value
    current_alignment_value=current_effect_record.get('alignment')
    if current_alignment_value is not None:
        if not isinstance(current_alignment_value,dict) or set(current_alignment_value)!={'key','texture','target','alpha','frames'}:
            raise ValueError('이펙트 좌표 형식 오류')
        if any(not isinstance(current_alignment_value[current_field_name],str) or not EFFECT_IDENTIFIER_PATTERN.fullmatch(current_alignment_value[current_field_name]) for current_field_name in ('key','texture')):
            raise ValueError('이펙트 연결 ID 오류')
        current_frame_values=current_alignment_value['frames']
        current_rectangle_values=[current_alignment_value['target'],*(current_frame_values if isinstance(current_frame_values,list) else [])]
        if not isinstance(current_frame_values,list) or len(current_frame_values)!=current_result_record['frames'] or any(not isinstance(current_rectangle,list) or len(current_rectangle)!=4 or any(type(current_number) not in (int,float) or not math.isfinite(current_number) or not 0<=current_number<=1 for current_number in current_rectangle) for current_rectangle in current_rectangle_values):
            raise ValueError('이펙트 좌표 값 오류')
        current_alpha_value=current_alignment_value['alpha']
        if type(current_alpha_value) not in (int,float) or not math.isfinite(current_alpha_value) or not 0<=current_alpha_value<=1:
            raise ValueError('이펙트 불투명도 오류')
        current_result_record['alignment']=current_alignment_value
    else:
        current_result_record['alignment']=None
    if len(json.dumps(current_result_record,ensure_ascii=False,allow_nan=False).encode())>30000:
        raise ValueError('이펙트 응답 크기 초과')
    return {**current_result_record,'note':'이미지와 애니메이션 원본 검증은 기존 이펙트 편집기를 사용합니다. 좌표 조회는 시각적 검수 완료를 뜻하지 않습니다.'}
