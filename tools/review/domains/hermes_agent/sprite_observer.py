"""등록 스프라이트 시트의 메타데이터를 제한된 형태로 조회한다."""
import base64
import hashlib
import math
import os
import re
from pathlib import PurePosixPath
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command


def call_hermes_sprite_editor(current_command_name,current_payload_record):
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command('character-animation',current_command_name,current_payload_record,current_gateway_address)


def validate_hermes_sprite_path(current_asset_path):
    if not isinstance(current_asset_path,str) or not 1<=len(current_asset_path)<=512 or '\\' in current_asset_path:
        raise ValueError('스프라이트 경로 오류')
    current_path_value=PurePosixPath(current_asset_path)
    if current_path_value.is_absolute() or '..' in current_path_value.parts or str(current_path_value)!=current_asset_path or current_path_value.suffix!='.png':
        raise ValueError('스프라이트 경로 오류')
    if not (current_asset_path.startswith('assets/sprites/') or current_asset_path.startswith('assets/characters/') and '/animations/' in current_asset_path):
        raise ValueError('등록 스프라이트 원본만 조회할 수 있습니다.')
    return current_asset_path


def read_hermes_sprite_catalog(current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'query','offset','limit'}:
        raise ValueError('스프라이트 검색에는 query·offset·limit만 허용합니다.')
    current_query_text=current_request_record.get('query','')
    current_offset_value=current_request_record.get('offset',0)
    current_limit_value=current_request_record.get('limit',20)
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or any(ord(current_character_value)<32 for current_character_value in current_query_text):
        raise ValueError('검색어는 100자 이하 한 줄이어야 합니다.')
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('조회 위치 또는 개수 오류')
    current_response_record=call_hermes_sprite_editor('sheet-search',{'query':current_query_text,'source':'assets'})
    if not isinstance(current_response_record,dict) or not isinstance(current_response_record.get('items'),list) or len(current_response_record['items'])>5000:
        raise ValueError('스프라이트 목록 응답 오류')
    current_item_values=[]
    current_seen_paths=set()
    for current_item_record in current_response_record['items']:
        if not isinstance(current_item_record,dict):raise ValueError('스프라이트 항목 오류')
        current_asset_path=validate_hermes_sprite_path(current_item_record.get('path'))
        current_label_value=current_item_record.get('label')
        current_hash_value=current_item_record.get('sha256')
        current_animation_ids=current_item_record.get('animationIds',[])
        if current_asset_path in current_seen_paths or not isinstance(current_label_value,str) or not 1<=len(current_label_value)<=300 or not isinstance(current_hash_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_hash_value) or not isinstance(current_animation_ids,list) or len(current_animation_ids)>100 or any(not isinstance(current_identifier,str) or not 1<=len(current_identifier)<=200 for current_identifier in current_animation_ids):
            raise ValueError('스프라이트 목록 형식 오류')
        current_seen_paths.add(current_asset_path)
        current_item_values.append({'path':current_asset_path,'label':current_label_value,'sha256':current_hash_value,'animation_ids':current_animation_ids})
    current_total_count=len(current_item_values)
    return {'items':current_item_values[current_offset_value:current_offset_value+current_limit_value],'total':current_total_count,'offset':current_offset_value,'limit':current_limit_value,'next_offset':current_offset_value+current_limit_value if current_offset_value+current_limit_value<current_total_count else None,'note':'등록 에셋 검색 결과입니다. 이미지·메타데이터 해시는 상세 조회 시 다시 확인합니다.'}


def read_hermes_sprite_sheet(current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'path','offset','limit','snapshot'} or 'path' not in current_request_record:
        raise ValueError('스프라이트 경로와 선택적 offset·limit·snapshot만 허용합니다.')
    current_asset_path=validate_hermes_sprite_path(current_request_record['path'])
    current_offset_value=current_request_record.get('offset',0)
    current_limit_value=current_request_record.get('limit',20)
    if type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('프레임 조회 위치 또는 개수 오류')
    current_snapshot_value=current_request_record.get('snapshot')
    if current_snapshot_value is not None and (not isinstance(current_snapshot_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_snapshot_value)):
        raise ValueError('스프라이트 원본 기준 해시 오류')
    if current_offset_value>0 and current_snapshot_value is None:
        raise ValueError('다음 프레임은 첫 조회의 snapshot이 필요합니다.')
    current_response_record=call_hermes_sprite_editor('sheet-image',{'path':current_asset_path,'source':'assets'})
    if not isinstance(current_response_record,dict) or current_response_record.get('path')!=current_asset_path or not isinstance(current_response_record.get('image'),str):
        raise ValueError('스프라이트 응답 오류')
    try:current_image_bytes=base64.b64decode(current_response_record['image'],validate=True)
    except (ValueError,TypeError) as current_decode_error:raise ValueError('스프라이트 이미지 형식 오류') from current_decode_error
    if len(current_image_bytes)>8*1024*1024:raise ValueError('스프라이트 이미지 크기 초과')
    current_metadata_hash=current_response_record.get('metadataSha256')
    if current_metadata_hash is not None and (not isinstance(current_metadata_hash,str) or not re.fullmatch(r'[a-f0-9]{64}',current_metadata_hash)):
        raise ValueError('메타데이터 해시 오류')
    current_image_hash=hashlib.sha256(current_image_bytes).hexdigest()
    current_snapshot_digest=hashlib.sha256((current_image_hash+':'+(current_metadata_hash or 'none')).encode('ascii')).hexdigest()
    if current_snapshot_value is not None and current_snapshot_value!=current_snapshot_digest:
        raise ValueError('스프라이트 원본이 변경됐습니다. 첫 프레임부터 다시 조회하세요.')
    current_animation_record=current_response_record.get('animation')
    current_result_record={'path':current_asset_path,'sha256':current_image_hash,'metadata_sha256':current_metadata_hash,'snapshot':current_snapshot_digest,'animation':None,'frames':[],'offset':current_offset_value,'limit':current_limit_value,'next_offset':None}
    if current_animation_record is not None:
        if not isinstance(current_animation_record,dict) or not isinstance(current_animation_record.get('frames'),list) or len(current_animation_record['frames'])>1000:
            raise ValueError('스프라이트 애니메이션 형식 오류')
        current_animation_id=current_animation_record.get('animationId')
        current_animation_version=current_animation_record.get('version')
        if any(not isinstance(current_text_value,str) or not 1<=len(current_text_value)<=200 for current_text_value in (current_animation_id,current_animation_version)):
            raise ValueError('애니메이션 ID·버전 오류')
        current_frame_records=current_animation_record['frames']
        current_frame_values=[]
        for current_frame_record in current_frame_records[current_offset_value:current_offset_value+current_limit_value]:
            if not isinstance(current_frame_record,dict) or not isinstance(current_frame_record.get('frameId'),str) or len(current_frame_record['frameId'])>200:
                raise ValueError('프레임 ID 오류')
            current_rect_value=current_frame_record.get('rect')
            current_anchor_value=current_frame_record.get('anchor')
            if not isinstance(current_rect_value,dict) or set(current_rect_value)!={'x','y','width','height'} or any(type(current_coordinate_value) is not int for current_coordinate_value in current_rect_value.values()) or not isinstance(current_anchor_value,dict) or set(current_anchor_value)!={'x','y'} or any(type(current_coordinate_value) not in (int,float) or not math.isfinite(current_coordinate_value) for current_coordinate_value in current_anchor_value.values()):
                raise ValueError('프레임 좌표·앵커 형식 오류')
            current_frame_values.append({'id':current_frame_record['frameId'],'rect':current_rect_value,'anchor':current_anchor_value})
        current_result_record['animation']={'id':current_animation_id,'version':current_animation_version,'frame_count':len(current_frame_records)}
        current_result_record['frames']=current_frame_values
        if current_offset_value+current_limit_value<len(current_frame_records):current_result_record['next_offset']=current_offset_value+current_limit_value
    return {**current_result_record,'note':'등록된 이미지와 메타데이터 해시를 확인한 조회 결과이며 시각적 검수나 게임 표시 크기 확인을 뜻하지 않습니다.'}
