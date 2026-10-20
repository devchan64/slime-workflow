"""에셋 공통 스프라이트 속성 변경."""
import hashlib
import math
import re
from pathlib import Path
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset, UniqueAssetYamlLoader


def save_map_sprite_anchor(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload) not in ({'map','kind','texture','anchorX','anchorY','expected'},{'map','kind','texture','anchorX','anchorY','expected','layout'}):
        raise ValueError('맵·종류·텍스처·앵커·기존 앵커 정보가 필요합니다.')
    current_texture_key=current_request_payload['texture']
    if not isinstance(current_texture_key,str) or not re.fullmatch('[a-z][a-z0-9-]*',current_texture_key):
        raise ValueError('텍스처 ID 오류')
    current_map_identifier=current_request_payload['map']
    if not isinstance(current_map_identifier,str) or not re.fullmatch('[a-z0-9-]+',current_map_identifier):
        raise ValueError('맵 ID 오류')
    current_map_kind=current_request_payload['kind']
    if current_map_kind not in ('town','field'):raise ValueError('도시·야외필드만 지원합니다.')
    for current_anchor_name in ('anchorX','anchorY'):
        current_anchor_value=current_request_payload[current_anchor_name]
        if type(current_anchor_value) not in (int,float) or not math.isfinite(current_anchor_value) or not -16<=current_anchor_value<=16:
            raise ValueError('앵커는 -16~16 범위의 숫자여야 합니다.')
    current_layout_values=current_request_payload.get('layout')
    if current_layout_values is not None:
        if not isinstance(current_layout_values,dict) or set(current_layout_values)!={'groundFootprintColumns','groundFootprintRows','displayHeight'}:raise ValueError('바닥 열·행과 표시 높이가 필요합니다.')
        for current_dimension_name in ('groundFootprintColumns','groundFootprintRows'):
            if type(current_layout_values[current_dimension_name]) is not int or not 1<=current_layout_values[current_dimension_name]<=8:raise ValueError('바닥 크기는 각 축 1~8칸입니다.')
        current_display_height=current_layout_values['displayHeight']
        if type(current_display_height) not in (int,float) or not math.isfinite(current_display_height) or not 0<current_display_height<=1024:raise ValueError('표시 높이는 0 초과 1024 이하입니다.')
    current_asset_root,current_asset_records=load_registered_tiles()
    current_map_relative='assets/maps/'+('city_layouts' if current_map_kind=='town' else 'field_tiles')+'/'+current_map_identifier+'.yaml'
    current_map_path,current_map_provenance=resolve_registered_asset(current_map_relative,current_asset_root,current_asset_records,'assets/maps')
    current_map_document=yaml.load(current_map_path.read_text(), Loader=UniqueAssetYamlLoader)
    from tools.review.common.sprite_display_properties import validate_sprite_display_properties, calculate_billboard_blocking_state, calculate_billboard_intersection_properties
    current_properties_relative = 'assets/maps/sprite-display-properties.yaml'
    current_properties_path, current_properties_provenance = resolve_registered_asset(current_properties_relative,current_asset_root,current_asset_records,'assets/maps')
    current_properties_document = yaml.load(current_properties_path.read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(current_properties_document, dict) or set(current_properties_document) != {'managementId', 'data'} or current_properties_document['managementId'] != current_properties_provenance['managementId']:
        raise ValueError('공통 속성 원본 관리 ID·필드 오류')
    current_property_catalog = validate_sprite_display_properties(current_properties_document['data'])
    current_map_data=current_map_document['data']
    current_target_entries=[]
    for current_object_record in current_map_data.get('objects',[]):
        if current_object_record.get('textureKey')==current_request_payload['texture']:current_target_entries.append((current_object_record['id'],current_object_record))
    for current_building_record in current_map_data.get('buildings',[]):
        if current_building_record.get('sprite',{}).get('textureKey')==current_request_payload['texture']:current_target_entries.append((current_building_record['id'],current_building_record['sprite']))
    current_is_billboard = any(current_object_record.get('textureKey') == current_texture_key for current_object_record in current_map_data.get('objects', []))
    if current_layout_values is not None and not current_is_billboard:
        raise ValueError('바닥 크기·높이 편집은 빌보드 에셋만 지원합니다.')
    if not current_target_entries or current_request_payload['expected'] != current_property_catalog.get(current_texture_key):
        raise ValueError('에셋 공용 속성이 변경되었거나 선택 맵에서 사용하지 않습니다. 새로고침하세요.')
    current_shared_properties = dict(current_property_catalog[current_texture_key])
    current_shared_properties.update(current_layout_values or current_property_catalog.get(current_request_payload['texture'], {}))
    # 기존 레이아웃을 유지할 때도 이번 앵커 입력을 우선한다.
    current_shared_properties.update({current_anchor_name:current_request_payload[current_anchor_name] for current_anchor_name in ('anchorX','anchorY')})
    if current_is_billboard:
        current_shared_properties = calculate_billboard_intersection_properties(current_shared_properties)
    current_property_catalog[current_request_payload['texture']] = current_shared_properties
    validate_sprite_display_properties(current_property_catalog)
    current_map_bytes=yaml.safe_dump(current_properties_document,allow_unicode=True,sort_keys=False).encode()
    current_map_hash=hashlib.sha256(current_map_bytes).hexdigest()
    current_registry_path=current_asset_root/'asset-registry.yaml'
    current_backend_lock=current_asset_root.parent/'slime-backend/map-data.lock.yaml'
    current_pending_files={current_properties_path:current_map_bytes}
    for current_metadata_path in (current_registry_path,current_backend_lock):
        current_metadata_text=current_metadata_path.read_text()
        if current_properties_provenance['sha256'] not in current_metadata_text:raise ValueError('공통 속성 등록부·잠금 불일치')
        current_pending_files[current_metadata_path]=current_metadata_text.replace(current_properties_provenance['sha256'],current_map_hash).encode()
    current_previous_files={current_file_path:current_file_path.read_bytes() for current_file_path in current_pending_files}
    try:
        for current_file_path,current_file_bytes in current_pending_files.items():current_file_path.write_bytes(current_file_bytes)
    except Exception:
        for current_file_path,current_file_bytes in current_previous_files.items():current_file_path.write_bytes(current_file_bytes)
        raise
    return {'count':len(current_target_entries),'map':current_map_identifier,'scope':'asset','texture':current_request_payload['texture']}
