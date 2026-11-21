"""도시맵 원장의 초안 검증과 조건부 저장."""
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from workflow.domains.map_assets.database_client import execute_content_api_request
from workflow.domains.map_assets.city_layout_validation import validate_content_city_document
from workflow.common.sprite_display_properties import validate_sprite_display_properties

CITY_EDITOR_STORAGE_ROOT = Path(__file__).resolve().parents[3] / '.tmp/city-layout-editor'


def read_validated_city_editor_sources(current_database_bundle,current_document_path):
    """DB 문서와 일치하는 등록 도시 원본·공용 속성을 읽는다."""
    import yaml
    from workflow.common.map_asset_sources import UniqueMapSourceLoader, validate_review_bundle_map_sources
    from workflow.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
    validate_review_bundle_map_sources(current_database_bundle)
    current_asset_root,current_asset_records=load_registered_tiles()
    current_source_documents=[]
    for current_relative_path in (current_document_path,'sprite-display-properties.yaml'):
        current_source_path,current_source_record=resolve_registered_asset('assets/maps/'+current_relative_path,current_asset_root,current_asset_records,'assets/maps')
        current_source_bytes=current_source_path.read_bytes()
        if hashlib.sha256(current_source_bytes).hexdigest()!=current_source_record['sha256']:
            raise ValueError('도시 맵 편집 원본이 읽는 중 변경되었습니다.')
        current_source_document=yaml.load(current_source_bytes,Loader=UniqueMapSourceLoader)
        current_source_json=json.dumps(current_source_document,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        current_database_json=json.dumps(current_database_bundle['documents'][current_relative_path],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        if current_source_json!=current_database_json:
            raise ValueError('도시 DB 문서가 에셋 원본과 다릅니다: '+current_relative_path)
        current_source_documents.append(current_source_document)
    validate_review_bundle_map_sources(current_database_bundle)
    return current_source_documents[0],current_source_documents[1]['data']


def read_city_editor_snapshot(current_request_payload):
    if os.environ.get('SLIME_CONTENT_STORAGE') != 'database':
        raise ValueError('도시맵 편집에는 콘텐츠 DB가 필요합니다.')
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map'}:
        raise ValueError('map ID만 지정하세요.')
    current_city_identifier = current_request_payload['map']
    if not isinstance(current_city_identifier, str) or not re.fullmatch(r'[a-z0-9-]+', current_city_identifier):
        raise ValueError('도시맵 ID 오류')
    current_document_path = f'city_layouts/{current_city_identifier}.yaml'
    current_database_bundle = execute_content_api_request('GET', '/internal/v1/content/review-bundle?' + urlencode({'map': current_city_identifier}))
    if current_document_path not in current_database_bundle['documents']:
        raise ValueError('등록되지 않은 도시맵입니다.')
    current_source_document,current_source_properties=read_validated_city_editor_sources(current_database_bundle,current_document_path)
    return {'map': current_city_identifier, 'generation': current_database_bundle['generation'],
            'revision': current_database_bundle['revisions'][current_document_path],
            'document': current_source_document, 'properties': current_source_properties}


def load_city_editor_document(current_request_payload):
    current_snapshot_record = read_city_editor_snapshot(current_request_payload)
    return {current_field_name: current_field_value for current_field_name, current_field_value in current_snapshot_record.items() if current_field_name != 'properties'}


def preview_city_editor_changes(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map', 'generation', 'revision', 'document'}:
        raise ValueError('map·generation·revision·document가 필요합니다.')
    current_original_record = read_city_editor_snapshot({'map': current_request_payload['map']})
    if (current_original_record['generation'], current_original_record['revision']) != (current_request_payload['generation'], current_request_payload['revision']):
        raise ValueError('도시 원장이 변경되었습니다. 다시 불러오세요.')
    current_document_record = current_request_payload['document']
    if not isinstance(current_document_record, dict) or current_document_record.get('managementId') != 'config.city-layouts.' + current_request_payload['map'] or current_document_record.get('data', {}).get('cityId') != current_request_payload['map']:
        raise ValueError('도시 원장의 ID가 일치하지 않습니다.')
    current_validation_record = validate_content_city_document(validate_sprite_display_properties(current_original_record['properties']), current_document_record)
    current_preview_token = hashlib.sha256(json.dumps(current_request_payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    CITY_EDITOR_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    (CITY_EDITOR_STORAGE_ROOT / (current_preview_token + '.json')).write_text(json.dumps(current_request_payload, ensure_ascii=False, allow_nan=False))
    current_plan_summary=inspect_city_source_plan(current_original_record,current_document_record,current_preview_token)
    return {**current_validation_record, 'changed': current_document_record != current_original_record['document'], 'token': current_preview_token,'source_plan':current_plan_summary}


def prepare_city_source_update_plan(current_asset_root,current_snapshot_record,current_document_record,current_request_identifier,current_source_bytes,current_metadata_paths):
    """검증된 도시 원본과 DB 요청의 계획만 계산하며 어떤 저장도 실행하지 않는다."""
    import yaml
    from workflow.common.map_asset_sources import UniqueMapSourceLoader
    from workflow.domains.map_assets.map_editor import prepare_registered_map_update_files
    if not isinstance(current_snapshot_record,dict) or set(current_snapshot_record)!={'map','generation','revision','document'}:
        raise ValueError('도시 편집 스냅샷 오류')
    current_city_identifier=current_snapshot_record['map']
    if not isinstance(current_city_identifier,str) or not re.fullmatch(r'[a-z0-9-]+',current_city_identifier) or type(current_snapshot_record['generation']) is not int or current_snapshot_record['generation']<0 or type(current_snapshot_record['revision']) is not int or current_snapshot_record['revision']<1:
        raise ValueError('도시 편집 신원 또는 세대 오류')
    if not isinstance(current_request_identifier,str) or not 1<=len(current_request_identifier)<=180:
        raise ValueError('맵 DB 요청 ID 오류')
    if not isinstance(current_document_record,dict) or current_document_record.get('managementId')!='config.city-layouts.'+current_city_identifier or not isinstance(current_document_record.get('data'),dict) or current_document_record['data'].get('cityId')!=current_city_identifier:
        raise ValueError('도시 원장의 ID가 일치하지 않습니다.')
    try:
        current_document_record=json.loads(json.dumps(current_document_record,ensure_ascii=False,allow_nan=False))
    except (TypeError,ValueError) as current_document_error:
        raise ValueError('도시 변경 문서 형식 오류') from current_document_error
    current_asset_root=Path(current_asset_root)
    current_expected_metadata=[current_asset_root/'asset-registry.yaml',current_asset_root.parent/'slime-backend/map-data.lock.yaml']
    if not isinstance(current_metadata_paths,list) or current_metadata_paths!=current_expected_metadata:
        raise ValueError('도시 맵 등록부 또는 백엔드 잠금 경로 오류')
    current_source_path=current_asset_root/'assets/maps/city_layouts'/(current_city_identifier+'.yaml')
    if not isinstance(current_source_bytes,dict) or current_source_path not in current_source_bytes or not isinstance(current_source_bytes[current_source_path],bytes):
        raise ValueError('도시 원본 바이트 누락')
    try:
        current_old_document=yaml.load(current_source_bytes[current_source_path],Loader=UniqueMapSourceLoader)
        current_snapshot_json=json.dumps(current_snapshot_record['document'],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
        current_source_json=json.dumps(current_old_document,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))
    except (yaml.YAMLError,TypeError,ValueError) as current_parse_error:
        raise ValueError('도시 원본 형식 오류') from current_parse_error
    if current_snapshot_json!=current_source_json:
        raise ValueError('도시 DB 스냅샷과 원본이 일치하지 않습니다.')
    current_pending_files=prepare_registered_map_update_files(current_asset_root,[current_source_path],[current_document_record],current_source_bytes,current_metadata_paths)
    current_database_request={'requestId':current_request_identifier,'expectedGeneration':current_snapshot_record['generation'],'documents':[{'path':'city_layouts/'+current_city_identifier+'.yaml','revision':current_snapshot_record['revision'],'document':current_document_record}]}
    current_request_hash=hashlib.sha256(json.dumps(current_database_request,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()
    return {'database_request':current_database_request,'request_sha256':current_request_hash,'pending_files':current_pending_files}


def inspect_city_source_plan(current_snapshot_record,current_document_record,current_preview_token):
    """변경 계획의 파일 해시만 읽으며 실제 저장·DB 접수를 만들지 않는다."""
    import yaml
    try:
        from workflow.common.map_tile_assets import load_registered_tiles
        current_asset_root,_=load_registered_tiles()
        current_source_path=current_asset_root/'assets/maps/city_layouts'/(current_snapshot_record['map']+'.yaml')
        current_metadata_paths=[current_asset_root/'asset-registry.yaml',current_asset_root.parent/'slime-backend/map-data.lock.yaml']
        current_tracked_paths=[current_source_path,*current_metadata_paths]
        if any(current_path.is_symlink() or not current_path.is_file() for current_path in current_tracked_paths):
            raise ValueError('도시 원본 경로 확인 실패')
        current_source_bytes={current_path:current_path.read_bytes() for current_path in current_tracked_paths}
        current_snapshot_value={current_key:current_snapshot_record[current_key] for current_key in ('map','generation','revision','document')}
        current_plan_value=prepare_city_source_update_plan(current_asset_root,current_snapshot_value,current_document_record,'preview-'+current_preview_token,current_source_bytes,current_metadata_paths)
        if any(current_path.read_bytes()!=current_source_bytes[current_path] for current_path in current_tracked_paths):
            raise ValueError('도시 원본이 조회 중 변경되었습니다.')
        current_final_snapshot=read_city_editor_snapshot({'map':current_snapshot_record['map']})
        if any(current_final_snapshot[current_key]!=current_snapshot_record[current_key] for current_key in ('generation','revision','document')):
            raise ValueError('도시 DB가 조회 중 변경되었습니다.')
        if any(current_path.read_bytes()!=current_source_bytes[current_path] for current_path in current_tracked_paths):
            raise ValueError('도시 원본이 최종 DB 확인 중 변경되었습니다.')
        return {'status':'available','before_sha256':hashlib.sha256(current_source_bytes[current_source_path]).hexdigest(),'after_sha256':hashlib.sha256(current_plan_value['pending_files'][current_source_path]).hexdigest()}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,yaml.YAMLError):
        return {'status':'unavailable'}


def save_city_editor_changes(current_request_payload):
    if not isinstance(current_request_payload, dict) or set(current_request_payload) != {'map', 'generation', 'revision', 'document', 'token'}:
        raise ValueError('검증된 도시 초안과 token이 필요합니다.')
    current_validation_payload = {current_field_name: current_field_value for current_field_name, current_field_value in current_request_payload.items() if current_field_name != 'token'}
    current_preview_token = hashlib.sha256(json.dumps(current_validation_payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    if current_request_payload['token'] != current_preview_token or not (CITY_EDITOR_STORAGE_ROOT / (current_preview_token + '.json')).is_file():
        raise ValueError('변경 내용을 먼저 검증하세요.')
    raise ValueError('도시 맵 저장은 원본·등록부·백엔드 잠금의 동기 저장이 구현될 때까지 중단됩니다.')
