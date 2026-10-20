"""공용 빌보드 목록·일괄 속성 검증·저장. 기존 이미지 변경 잠금을 공유한다."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import yaml
from tools.review.common.sprite_display_properties import validate_sprite_display_properties, calculate_billboard_blocking_state
from tools.review.maintenance.sync_billboard_catalog import build_catalog_reference, load_unique_yaml_document

EDITOR_MUTABLE_FIELDS = {'anchorX','anchorY','groundFootprintColumns','groundFootprintRows','displayHeight','billboardPlacementAnchor','shadowOffsetColumn','shadowOffsetRow','shadowScaleX','shadowScaleY'}
EDITOR_STORAGE_DIRECTORY = Path(__file__).resolve().parents[4]/'.tmp/map-asset-editor'


def read_editor_snapshot(current_asset_root=None):
    if current_asset_root is None:
        from tools.review.common.map_tile_assets import load_registered_tiles
        current_asset_root = load_registered_tiles()[0]
    current_asset_root = Path(current_asset_root)
    current_source_paths = [current_asset_root/'assets/maps/sprite-display-properties.yaml',current_asset_root/'asset-registry.yaml',current_asset_root/'assets/billboards/catalog.yaml',current_asset_root.parent/'slime-backend/map-data.lock.yaml']
    current_source_bytes = {current_source_path:current_source_path.read_bytes() for current_source_path in current_source_paths}
    current_revision_hash = hashlib.sha256(b''.join(hashlib.sha256(current_content_bytes).digest() for current_content_bytes in current_source_bytes.values())).hexdigest()
    current_property_document = load_unique_yaml_document(current_source_paths[0])
    validate_sprite_display_properties(current_property_document['data'])
    current_catalog_document = build_catalog_reference(current_asset_root)
    return current_asset_root,current_source_paths,current_source_bytes,current_revision_hash,current_property_document,current_catalog_document


def load_editor_catalog(current_request_payload, current_asset_root=None):
    if current_request_payload != {}:raise ValueError('목록 조회에는 입력값을 지정하지 않습니다.')
    current_asset_root,current_source_paths,current_source_bytes,current_revision_hash,current_property_document,current_catalog_document=read_editor_snapshot(current_asset_root)
    current_asset_rows=[]
    for current_asset_record in current_catalog_document['billboards']:
        current_texture_key=current_asset_record['texture_key'];current_family_record=current_catalog_document['families'][current_asset_record['family']]
        current_asset_rows.append({'texture':current_texture_key,'name':current_family_record['name'],'category':current_family_record['review_category'],'image':str(current_asset_root/current_asset_record['source_file']['path']),'size':[current_asset_record['source_file']['width'],current_asset_record['source_file']['height']],'properties':current_property_document['data'][current_texture_key],'maps':current_asset_record['map_references'],'modeling':current_asset_record['modeling'],'metadata':current_asset_record.get('metadata_references',[])})
    return {'revision':current_revision_hash,'assets':current_asset_rows}


def prepare_editor_changes(current_request_payload,current_asset_root=None):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'revision','changes'}:raise ValueError('revision·changes가 필요합니다.')
    current_snapshot_values=read_editor_snapshot(current_asset_root)
    current_asset_root,current_source_paths,current_source_bytes,current_revision_hash,current_property_document,current_catalog_document=current_snapshot_values
    if current_request_payload['revision']!=current_revision_hash:raise ValueError('원본이 변경되었습니다. 목록을 새로고침한 뒤 다시 검증하세요.')
    current_change_records=current_request_payload['changes']
    if not isinstance(current_change_records,list) or not 1<=len(current_change_records)<=1000:raise ValueError('변경할 에셋 1~1000개가 필요합니다.')
    current_allowed_textures={current_record['texture_key'] for current_record in current_catalog_document['billboards']}
    current_changed_textures=set();current_diff_records=[]
    for current_change_record in current_change_records:
        if not isinstance(current_change_record,dict) or set(current_change_record)!={'texture','values'}:raise ValueError('변경 항목은 texture·values만 허용합니다.')
        current_texture_key=current_change_record['texture'];current_input_values=current_change_record['values']
        if not isinstance(current_texture_key,str) or current_texture_key not in current_allowed_textures or current_texture_key in current_changed_textures:raise ValueError('미등록 또는 중복 에셋 ID')
        if not isinstance(current_input_values,dict) or not current_input_values or set(current_input_values)-EDITOR_MUTABLE_FIELDS:raise ValueError('수정할 공용 속성 필드 오류')
        current_original_values=current_property_document['data'][current_texture_key]
        if current_original_values.get('billboardAnchorMode') == 'tile-bottom-center' and 'billboardPlacementAnchor' in current_input_values:raise ValueError('상하 배치는 앵커에서 자동 판정됩니다.')
        current_updated_values={**current_original_values,**current_input_values}
        current_updated_values['billboardBlocksMovement']=calculate_billboard_blocking_state(current_updated_values)
        validate_sprite_display_properties({current_texture_key:current_updated_values})
        if current_updated_values==current_original_values:raise ValueError('변경 없는 에셋은 제외하세요: '+current_texture_key)
        current_property_document['data'][current_texture_key]=current_updated_values;current_changed_textures.add(current_texture_key)
        current_diff_records.append({'texture':current_texture_key,'before':current_original_values,'after':current_updated_values})
    # 실제 사용 맵의 선언 접지·고도를 재검수한다. 이미지 실루엣을 접지로 오인하지 않는다.
    from tools.review.domains.map_assets.placement import validate_scenery_object_collisions
    current_affected_maps=[];current_map_warnings=[]
    for current_map_path in sorted((current_asset_root/'assets/maps').rglob('*.yaml')):
        if current_map_path==current_source_paths[0]:continue
        current_map_document=load_unique_yaml_document(current_map_path)
        if not isinstance(current_map_document,dict):continue
        current_map_values=current_map_document.get('data',{})
        if not isinstance(current_map_values,dict):continue
        current_map_objects=current_map_values.get('objects',[])
        if not any(current_object_record.get('textureKey') in current_changed_textures for current_object_record in current_map_objects):continue
        current_relative_path=str(current_map_path.relative_to(current_asset_root))
        current_affected_maps.append(current_relative_path)
        try:
            current_elevation_rows=current_map_values.get('elevations')
            if current_elevation_rows is None and current_map_path.parent.name=='field_tiles':
                current_surface_path=current_asset_root/'assets/maps/terrain/maps'/current_map_path.name
                current_elevation_rows=load_unique_yaml_document(current_surface_path)['data']['elevations']
            if current_elevation_rows is None and current_map_path.parent.name=='city_layouts':
                current_elevation_rows=[[0]*current_map_values['columns'] for current_row_index in range(current_map_values['rows'])]
            if current_elevation_rows is None:raise ValueError('사용 맵의 고도 데이터가 없습니다: '+str(current_map_path))
            validate_scenery_object_collisions(current_map_objects,current_property_document['data'],current_elevation_rows)
        except (ValueError,KeyError,FileNotFoundError,TypeError,IndexError) as current_map_error:
            current_map_warnings.append({'map':current_relative_path,'message':str(current_map_error)})
    return current_snapshot_values,{'changes':current_diff_records,'maps':current_affected_maps,'map_warnings':current_map_warnings,'note':'맵 배치·고도 문제는 경고이며 공용 에셋 저장을 차단하지 않습니다. 맵 배치는 별도로 수정하세요.'}


def preview_editor_changes(current_request_payload,current_asset_root=None):
    current_snapshot_values,current_preview_result=prepare_editor_changes(current_request_payload,current_asset_root)
    current_preview_token=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    EDITOR_STORAGE_DIRECTORY.mkdir(parents=True,exist_ok=True)
    (EDITOR_STORAGE_DIRECTORY/(current_preview_token+'.json')).write_text(json.dumps(current_request_payload,ensure_ascii=False))
    return {**current_preview_result,'token':current_preview_token}


def save_editor_changes(current_request_payload,current_asset_root=None):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'token','revision','changes'}:raise ValueError('검증 token·revision·changes가 필요합니다.')
    current_validation_payload={current_field_name:current_request_payload[current_field_name] for current_field_name in ('revision','changes')}
    current_preview_token=hashlib.sha256(json.dumps(current_validation_payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if current_request_payload['token']!=current_preview_token:raise ValueError('검증 이후 입력값이 변경되었습니다. 다시 검증하세요.')
    current_receipt_path=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-saved.json')
    if current_receipt_path.is_file():return json.loads(current_receipt_path.read_text())
    current_preview_path=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'.json')
    if not current_preview_path.is_file() or json.loads(current_preview_path.read_text())!=current_validation_payload:raise ValueError('먼저 변경 검증을 실행하세요.')
    current_snapshot_values,current_preview_result=prepare_editor_changes(current_validation_payload,current_asset_root)
    current_asset_root,current_source_paths,current_source_bytes,current_revision_hash,current_property_document,current_catalog_document=current_snapshot_values
    current_property_bytes=yaml.safe_dump(current_property_document,allow_unicode=True,sort_keys=False).encode()
    current_old_hash=hashlib.sha256(current_source_bytes[current_source_paths[0]]).hexdigest();current_new_hash=hashlib.sha256(current_property_bytes).hexdigest()
    current_pending_files={current_source_paths[0]:current_property_bytes}
    for current_metadata_path in (current_source_paths[1],current_source_paths[3]):
        current_metadata_text=current_source_bytes[current_metadata_path].decode()
        if current_metadata_text.count(current_old_hash)!=1:raise ValueError('등록부·소비자 해시 잠금 불일치')
        current_pending_files[current_metadata_path]=current_metadata_text.replace(current_old_hash,current_new_hash).encode()
    current_backup_directory=EDITOR_STORAGE_DIRECTORY/(current_preview_token+'-backup');current_backup_directory.mkdir(exist_ok=True)
    for current_file_index,(current_file_path,current_file_bytes) in enumerate(current_source_bytes.items()):(current_backup_directory/str(current_file_index)).write_bytes(current_file_bytes)
    (current_backup_directory/'paths.json').write_text(json.dumps([str(current_file_path) for current_file_path in current_source_paths]))
    for current_file_path,current_file_bytes in current_source_bytes.items():
        if current_file_path.read_bytes()!=current_file_bytes:raise ValueError('저장 직전에 원본이 변경되었습니다. 다시 검증하세요.')
    try:
        for current_file_path,current_file_bytes in current_pending_files.items():
            current_temporary_path=current_file_path.with_name(current_file_path.name+'.editor-tmp');current_temporary_path.write_bytes(current_file_bytes);os.replace(current_temporary_path,current_file_path)
        current_synced_catalog=build_catalog_reference(current_asset_root)
        current_source_paths[2].write_text(yaml.safe_dump(current_synced_catalog,allow_unicode=True,sort_keys=False))
        current_result_record={'saved':True,'count':len(current_preview_result['changes']),'maps':current_preview_result['maps'],'map_warnings':current_preview_result['map_warnings'],'saved_at':datetime.now(timezone.utc).isoformat(),'sha256':current_new_hash}
        current_receipt_path.write_text(json.dumps(current_result_record,ensure_ascii=False))
        return current_result_record
    except Exception:
        for current_file_path,current_file_bytes in current_source_bytes.items():current_file_path.write_bytes(current_file_bytes)
        raise
