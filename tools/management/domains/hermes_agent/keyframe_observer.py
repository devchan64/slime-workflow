"""Kimodo의 기존 키프레임 기록을 제한적으로 조회한다."""
import os
import re
from tools.management.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.management.common.management_gateway import execute_management_command


def read_hermes_kimodo_keyframe_catalog(current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'query','offset','limit','snapshot'}:
        raise ValueError('키프레임 검색 필드 오류')
    current_query_text=current_request_record.get('query','')
    current_offset_value=current_request_record.get('offset',0)
    current_limit_value=current_request_record.get('limit',20)
    current_expected_snapshot=current_request_record.get('snapshot')
    if current_expected_snapshot is not None and (not isinstance(current_expected_snapshot,str) or not re.fullmatch(r'[a-f0-9]{64}',current_expected_snapshot)):
        raise ValueError('키프레임 목록 기준 해시 오류')
    if not isinstance(current_query_text,str) or len(current_query_text)>100 or any(ord(value)<32 for value in current_query_text) or type(current_offset_value) is not int or current_offset_value<0 or type(current_limit_value) is not int or not 1<=current_limit_value<=30:
        raise ValueError('키프레임 검색 범위 오류')
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_response_value=execute_management_command('kimodo','keyframe-list',{},current_gateway_address)
    if not isinstance(current_response_value,dict) or not isinstance(current_response_value.get('records'),list) or len(current_response_value['records'])>10000:
        raise ValueError('키프레임 목록 응답 오류')
    current_items_value=[]
    current_identifiers=set()
    for current_record_value in current_response_value['records']:
        if not isinstance(current_record_value,dict):
            raise ValueError('키프레임 기록 오류')
        current_id_value=current_record_value.get('id')
        current_tag_value=current_record_value.get('tag')
        current_frame_value=current_record_value.get('source_frame')
        if not isinstance(current_id_value,str) or not re.fullmatch(r'[a-f0-9]{32}',current_id_value) or current_id_value in current_identifiers or not isinstance(current_tag_value,str) or len(current_tag_value)>200 or any(ord(value)<32 for value in current_tag_value) or type(current_frame_value) is not int or current_frame_value<1:
            raise ValueError('키프레임 식별·태그·프레임 오류')
        current_identifiers.add(current_id_value)
        if current_query_text.strip().casefold() in (current_id_value+' '+current_tag_value).casefold():
            current_items_value.append({'id':current_id_value,'tag':current_tag_value,'source_frame':current_frame_value})
    import hashlib, json
    current_snapshot_value=hashlib.sha256(json.dumps(current_items_value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if current_expected_snapshot is not None and current_expected_snapshot!=current_snapshot_value:
        raise ValueError('키프레임 목록이 변경됐습니다. 처음부터 다시 검색하세요.')
    current_page_value=current_items_value[current_offset_value:current_offset_value+current_limit_value]
    current_next_offset=current_offset_value+len(current_page_value)
    current_page_note='기존 키프레임 기록 목록입니다. 원본 해시·미리보기와 동작 적합성은 Kimodo에서 별도로 확인합니다.'
    if current_offset_value>0 and current_expected_snapshot is None:
        current_page_note+=' 이전 페이지의 목록 확인값 없이 조회해 페이지 간 변경 여부를 확인하지 못했습니다. 처음부터 검색하고 반환된 snapshot을 전달하세요.'
    return {'items':current_page_value,'total':len(current_items_value),'offset':current_offset_value,'snapshot':current_snapshot_value,'next_offset':current_next_offset if current_next_offset<len(current_items_value) else None,'note':current_page_note}


def read_hermes_kimodo_keyframe_preview(current_keyframe_identifier):
    """Kimodo가 검증한 키프레임 미리보기와 이미지 해시를 확인한다."""
    import base64
    import binascii
    import hashlib
    if not isinstance(current_keyframe_identifier,str) or not re.fullmatch(r'[a-f0-9]{32}',current_keyframe_identifier):
        raise ValueError('키프레임 ID 오류')
    current_gateway_address=validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL',DEFAULT_GATEWAY_ADDRESS))
    current_response_value=execute_management_command('kimodo','keyframe-preview',{'id':current_keyframe_identifier},current_gateway_address)
    if not isinstance(current_response_value,dict) or not isinstance(current_response_value.get('record'),dict) or current_response_value['record'].get('id')!=current_keyframe_identifier:
        raise ValueError('키프레임 미리보기 응답 오류')
    current_skeleton_signature=current_response_value.get('skeleton_signature_sha256')
    if not isinstance(current_skeleton_signature,str) or not re.fullmatch(r'[a-f0-9]{64}',current_skeleton_signature):
        raise ValueError('키프레임 골격 서명 확인 불가 · Kimodo 서비스를 갱신하세요.')
    current_image_text=current_response_value.get('image_base64')
    current_file_hashes=current_response_value['record'].get('files')
    if not isinstance(current_image_text,str) or len(current_image_text)>8_000_000 or not isinstance(current_file_hashes,dict) or not isinstance(current_file_hashes.get('preview.png'),str) or not re.fullmatch(r'[a-f0-9]{64}',current_file_hashes['preview.png']):
        raise ValueError('키프레임 이미지 또는 해시 오류')
    try:
        current_image_bytes=base64.b64decode(current_image_text,validate=True)
    except (ValueError,binascii.Error) as current_decode_error:
        raise ValueError('키프레임 이미지 인코딩 오류') from current_decode_error
    if hashlib.sha256(current_image_bytes).hexdigest()!=current_file_hashes['preview.png'] or not current_image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('키프레임 미리보기 해시 또는 형식 오류')
    from tools.management.domains.kimodo.keyframe_storage import hash_kimodo_keyframe_source
    current_source_hash=hash_kimodo_keyframe_source(current_file_hashes)
    return {'id':current_keyframe_identifier,'image_base64':current_image_text,'sha256':current_file_hashes['preview.png'],'skeleton_signature_sha256':current_skeleton_signature,'source_sha256':current_source_hash,'note':'Kimodo가 모션·골격·미리보기 파일을 검증한 결과입니다. 이미지 확인은 생성 동작의 품질 보증이 아닙니다.'}


def validate_hermes_kimodo_keyframe_batch(current_request_record):
    """배치의 각 원본과 서로 같은 골격 구조를 검증한다."""
    from tools.management.domains.kimodo.keyframe_storage import validate_kimodo_keyframe_placements
    if not isinstance(current_request_record,dict) or set(current_request_record)!={'keyframes','frames'} or type(current_request_record['frames']) is not int or current_request_record['frames']<1:
        raise ValueError('키프레임 배치와 정수 프레임 수가 필요합니다.')
    current_placements_value=validate_kimodo_keyframe_placements(current_request_record['keyframes'],current_request_record['frames'])
    current_verified_values=[]
    current_seen_values=set()
    current_skeleton_signature=None
    for current_placement_value in current_placements_value:
        current_identifier_value=current_placement_value['id']
        if current_identifier_value in current_seen_values:
            continue
        current_preview_value=read_hermes_kimodo_keyframe_preview(current_identifier_value)
        current_signature_value=current_preview_value['skeleton_signature_sha256']
        if current_skeleton_signature is not None and current_signature_value!=current_skeleton_signature:
            raise ValueError('키프레임 골격 구조가 서로 다릅니다.')
        current_skeleton_signature=current_signature_value
        current_seen_values.add(current_identifier_value)
        current_verified_values.append({'id':current_identifier_value,'preview_sha256':current_preview_value['sha256'],'source_sha256':current_preview_value['source_sha256']})
    return {'placements':current_placements_value,'sources':current_verified_values,'skeleton_signature_sha256':current_skeleton_signature,'note':'접수 시 원본을 다시 검증하므로 이 검증 뒤 원본이 바뀔 수 있습니다.'}
