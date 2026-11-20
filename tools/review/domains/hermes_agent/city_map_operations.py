"""콘텐츠 DB 도시 맵 편집기의 초안 검증과 저장을 연결한다."""
from datetime import datetime, timezone
import hashlib
import json

from tools.review.common.generation_records import write_record_atomically
from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore, list_delegation_record_paths, check_delegation_record_exists
from tools.review.domains.hermes_agent.field_map_operations import call_field_map_editor, HERMES_FIELD_MAP_PATTERN, HERMES_FIELD_TOKEN_PATTERN, HERMES_FIELD_MAX_BYTES


def validate_hermes_city_draft(current_draft_record):
    if not isinstance(current_draft_record,dict) or set(current_draft_record) != {'map','generation','revision','document'}:
        raise ValueError('도시 맵 초안의 map·generation·revision·document가 필요합니다.')
    if not isinstance(current_draft_record['map'],str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_draft_record['map']):
        raise ValueError('도시 맵 ID 형식 오류')
    if any(type(current_draft_record[current_name_value]) is not int or current_draft_record[current_name_value]<0 for current_name_value in ('generation','revision')) or not isinstance(current_draft_record['document'],dict):
        raise ValueError('도시 맵 원장 세대·리비전 또는 문서 오류')
    try:
        current_serialized_bytes = json.dumps(current_draft_record,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as current_draft_error:
        raise ValueError('도시 맵 초안을 JSON으로 인코딩할 수 없습니다.') from current_draft_error
    if len(current_serialized_bytes)>HERMES_FIELD_MAX_BYTES:
        raise ValueError('도시 맵 초안 크기 초과')
    return hashlib.sha256(current_serialized_bytes).hexdigest()


def read_hermes_city_source(current_map_identifier):
    """DB 연결 없이 검증된 도시 맵 에셋 원본을 읽는다."""
    import os
    from pathlib import Path
    from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
    from tools.review.domains.map_assets.source_consistency import read_registered_city_source
    current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY))
    return read_registered_city_source(current_asset_root,current_asset_root.parent/'slime-backend/map-data.lock.yaml',current_map_identifier)


def load_hermes_city_map(current_map_identifier):
    if not isinstance(current_map_identifier,str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_map_identifier):
        raise ValueError('도시 맵 ID 형식 오류')
    current_source_value = call_field_map_editor('city-edit-load',{'map':current_map_identifier})
    validate_hermes_city_draft(current_source_value)
    if current_source_value['map'] != current_map_identifier:
        raise ValueError('도시 맵 응답 ID 불일치')
    return current_source_value


def preview_hermes_city_map(current_draft_record):
    current_expected_token = validate_hermes_city_draft(current_draft_record)
    current_preview_value = call_field_map_editor('city-edit-preview',current_draft_record)
    if not isinstance(current_preview_value,dict) or current_preview_value.get('token') != current_expected_token or current_preview_value.get('cityId') != current_draft_record['map'] or type(current_preview_value.get('changed')) is not bool:
        raise ValueError('도시 맵 미리보기 응답 형식 오류')
    for current_count_name in ('columns','rows','buildings','objects'):
        if type(current_preview_value.get(current_count_name)) is not int or current_preview_value[current_count_name]<0:
            raise ValueError('도시 맵 미리보기 수량 오류')
    current_alignment_record={'status':'unavailable','note':'도시 DB 문서와 에셋 원본의 일치를 확인할 수 없습니다.'}
    try:
        import os
        from pathlib import Path
        from tools.review.common.map_tile_assets import DEFAULT_ASSET_REPOSITORY
        from tools.review.domains.map_assets.source_consistency import inspect_city_source_alignment
        current_database_record=load_hermes_city_map(current_draft_record['map'])
        if (current_database_record['generation'],current_database_record['revision'])==(current_draft_record['generation'],current_draft_record['revision']):
            current_asset_root=Path(os.environ.get('SLIME_ASSETS_ROOT',DEFAULT_ASSET_REPOSITORY)).resolve()
            current_alignment_record=inspect_city_source_alignment(current_asset_root,current_asset_root.parent/'slime-backend/map-data.lock.yaml',current_draft_record['map'],current_database_record['document'])
            current_final_database=load_hermes_city_map(current_draft_record['map'])
            if (current_final_database['generation'],current_final_database['revision'])!=(current_database_record['generation'],current_database_record['revision']):
                current_alignment_record={'status':'unavailable','note':'도시 DB 문서가 비교 중 변경되어 확인할 수 없습니다.'}
    except (OSError,ValueError,TypeError,KeyError):
        pass
    import re
    current_source_plan=current_preview_value.get('source_plan',{'status':'unavailable'})
    if not isinstance(current_source_plan,dict) or current_source_plan.get('status') not in ('available','unavailable'):
        raise ValueError('도시 원본 변경 계획 응답 오류')
    if current_source_plan['status']=='available':
        if set(current_source_plan)!={'status','before_sha256','after_sha256'} or any(not isinstance(current_source_plan[current_hash_name],str) or not re.fullmatch(r'[a-f0-9]{64}',current_source_plan[current_hash_name]) for current_hash_name in ('before_sha256','after_sha256')):
            raise ValueError('도시 원본 변경 계획 해시 오류')
    elif set(current_source_plan)!={'status'}:
        raise ValueError('도시 원본 변경 계획 응답 오류')
    return {**{key:current_preview_value[key] for key in ('token','cityId','changed','columns','rows','buildings','objects')},'save_available':False,'source_alignment':current_alignment_record,'source_plan':current_source_plan}


def inspect_hermes_city_receipt(current_record_value,current_request_identifier):
    if (not isinstance(current_record_value,dict) or current_record_value.get('version') != 5 or current_record_value.get('id') != current_request_identifier
            or not isinstance(current_record_value.get('map'),str) or not HERMES_FIELD_MAP_PATTERN.fullmatch(current_record_value['map'])
            or not isinstance(current_record_value.get('token'),str) or not HERMES_FIELD_TOKEN_PATTERN.fullmatch(current_record_value['token'])):
        raise ValueError('도시 맵 접수 기록 오류')
    if current_record_value.get('state') == 'dispatching':
        return {'request_id':current_request_identifier,'map':current_record_value['map'],'state':'unknown','saved':None}
    if current_record_value.get('state') != 'completed' or type(current_record_value.get('saved')) is not bool:
        raise ValueError('도시 맵 접수 상태 오류')
    return {'request_id':current_request_identifier,'map':current_record_value['map'],'state':'completed','saved':current_record_value['saved']}


def save_hermes_city_map_once(current_request_identifier,current_draft_record,current_preview_token):
    current_expected_token = validate_hermes_city_draft(current_draft_record)
    if not isinstance(current_preview_token,str) or not HERMES_FIELD_TOKEN_PATTERN.fullmatch(current_preview_token) or current_preview_token != current_expected_token:
        raise ValueError('검토한 도시 초안과 토큰이 일치하지 않습니다.')
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path = current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if check_delegation_record_exists(current_record_path):
            current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
            current_receipt_value = inspect_hermes_city_receipt(current_record_value,current_request_identifier)
            if current_record_value['token'] != current_preview_token or current_receipt_value['map'] != current_draft_record['map']:
                raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {**current_receipt_value,'duplicate':True}
        raise ValueError('도시 맵 원본·등록부·소비자 잠금의 동기 저장이 지원될 때까지 신규 저장을 사용할 수 없습니다.')


def read_hermes_city_receipt(current_request_identifier):
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_record_path = current_storage_value.resolve_delegation_record_path(current_request_identifier)
        if not check_delegation_record_exists(current_record_path):
            return {'state':'not_found'}
        return inspect_hermes_city_receipt(json.loads(current_record_path.read_text(encoding='utf-8')),current_request_identifier)


def list_hermes_city_receipts():
    current_storage_value = HermesDelegationStore()
    with current_storage_value.hold_delegation_storage_lock():
        current_records_list = []
        for current_record_path in list_delegation_record_paths(current_storage_value.delegation_storage_root):
            if current_record_path.is_symlink() or not current_record_path.is_file():
                continue
            try:
                current_request_identifier = current_record_path.stem
                current_storage_value.resolve_delegation_record_path(current_request_identifier)
                current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_record_value,dict) or current_record_value.get('version') != 5:
                    continue
                current_receipt_value = inspect_hermes_city_receipt(current_record_value,current_request_identifier)
                current_update_time = current_record_path.stat().st_mtime
                current_records_list.append({**current_receipt_value,'updated_at':datetime.fromtimestamp(current_update_time,timezone.utc).isoformat(),'_sort_time':current_update_time})
            except (OSError,ValueError,TypeError,KeyError):
                continue
        current_records_list.sort(key=lambda current_record_value:(current_record_value['_sort_time'],current_record_value['request_id']),reverse=True)
        for current_receipt_value in current_records_list:
            current_receipt_value.pop('_sort_time')
        return {'records':current_records_list[:100],'truncated':len(current_records_list)>100,'note':'손상된 기록은 제외됩니다. 확인 불가는 원본 상태를 별도로 확인하세요.'}
