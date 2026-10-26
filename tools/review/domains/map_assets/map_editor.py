"""야외 맵의 타일·고도·빌보드 초안 검증과 원본 저장."""
from tools.review.maintenance.sync_billboard_catalog import load_billboard_catalog, list_billboard_catalog_paths, write_billboard_catalog, prepare_billboard_catalog_files
import copy
import hashlib
import json
import os
import re
from collections import deque
from pathlib import Path
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
from tools.review.common.map_asset_sources import load_registered_map_review, normalize_field_surface_data, MAP_BLOCKED_TERRAIN_NAMES, validate_map_cliff_overrides
from tools.review.common.sprite_display_properties import apply_sprite_display_properties, collect_billboard_blocked_cells
from tools.review.domains.map_assets.placement import validate_scenery_object_collisions
from tools.review.maintenance.sync_billboard_catalog import load_unique_yaml_document, build_catalog_reference

MAP_EDITOR_STORAGE_ROOT=Path(__file__).resolve().parents[4]/'.tmp/map-layout-editor'
MAP_EDITOR_ALLOWED_COMMANDS=('map-edit-load','map-edit-preview','map-edit-save')


def read_map_editor_snapshot(current_map_identifier):
    if not isinstance(current_map_identifier,str) or not re.fullmatch('[a-z0-9-]+',current_map_identifier):raise ValueError('맵 ID 오류')
    current_asset_root,current_asset_records=load_registered_tiles()
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        from urllib.parse import urlencode
        current_database_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle?'+urlencode({'map':current_map_identifier}))
        current_relative_documents=[f'field_tiles/{current_map_identifier}.yaml',f'terrain/maps/{current_map_identifier}.yaml']
        current_source_paths=[current_asset_root/'assets/maps'/current_relative_path for current_relative_path in current_relative_documents]
        current_documents=[current_database_bundle['documents'][current_relative_path] for current_relative_path in current_relative_documents]
        current_source_bytes={current_source_path:yaml.safe_dump(current_document).encode() for current_source_path,current_document in zip(current_source_paths,current_documents)}
        current_revision_hash=json.dumps({'generation':current_database_bundle['generation'],'revisions':{current_relative_path:current_database_bundle['revisions'][current_relative_path] for current_relative_path in current_relative_documents}},sort_keys=True)
        return current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash
    current_relative_paths=[f'assets/maps/field_tiles/{current_map_identifier}.yaml',f'assets/maps/terrain/maps/{current_map_identifier}.yaml']
    current_source_paths=[resolve_registered_asset(current_relative_path,current_asset_root,current_asset_records,'assets/maps')[0] for current_relative_path in current_relative_paths]
    current_documents=[load_unique_yaml_document(current_source_path) for current_source_path in current_source_paths]
    current_source_bytes={current_source_path:current_source_path.read_bytes() for current_source_path in current_source_paths}
    current_property_path=current_asset_root/'assets/maps/sprite-display-properties.yaml'
    current_source_bytes[current_property_path]=current_property_path.read_bytes()
    current_revision_hash=hashlib.sha256(b''.join(current_source_bytes.values())).hexdigest()
    return current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash


def load_map_editor_document(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'map'}:raise ValueError('map ID만 지정하세요. 현재 야외필드 편집을 지원합니다.')
    current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash=read_map_editor_snapshot(current_request_payload['map'])
    current_render_record=load_registered_map_review(current_request_payload['map'])
    current_render_record['terrainCodes']=read_map_editor_source_data(current_asset_root,'field_tiles/codes.yaml')
    return {'map':current_request_payload['map'],'revision':current_revision_hash,'tiles':current_documents[0]['data'],'terrain':current_documents[1]['data'],'render':current_render_record,'textures':sorted(read_map_editor_billboard_identifiers(current_asset_root)),'codes':current_render_record['terrainCodes']}


def validate_map_editor_changes(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)-{'terrainEffects','ambientTint'}!={'map','revision','cells','objects'}:raise ValueError('map·revision·cells·objects가 필요합니다.')
    current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash=read_map_editor_snapshot(current_request_payload['map'])
    if current_request_payload['revision']!=current_revision_hash:raise ValueError('맵 또는 에셋 속성이 변경되었습니다. 초안은 유지됩니다. 원본을 다시 불러오기 전에 변경 내용을 보관하세요.')
    current_tile_data,current_terrain_data=(current_document['data'] for current_document in current_documents)
    normalize_field_surface_data(current_terrain_data)
    current_column_count=current_terrain_data['columns'];current_row_count=current_terrain_data['rows']
    current_render_record=load_registered_map_review(current_request_payload['map'])
    current_render_record['terrainCodes']=read_map_editor_source_data(current_asset_root,'field_tiles/codes.yaml')
    current_allowed_codes=current_render_record['terrainCodes']
    current_changed_cells=current_request_payload['cells']
    if not isinstance(current_changed_cells,list) or len(current_changed_cells)>current_column_count*current_row_count:raise ValueError('셀 변경 목록 오류')
    current_seen_positions=set();current_blocked_positions={tuple(current_position) for current_position in current_terrain_data['blocked']}
    for current_cell_record in current_changed_cells:
        if not isinstance(current_cell_record,dict) or set(current_cell_record) not in ({'column','row','tile','height','blocked'},{'column','row','tile','height','blocked','wall'}):raise ValueError('셀 변경 필드 오류')
        current_cell_column=current_cell_record['column'];current_cell_row=current_cell_record['row']
        if type(current_cell_column) is not int or type(current_cell_row) is not int or not 0<=current_cell_column<current_column_count or not 0<=current_cell_row<current_row_count:raise ValueError('셀 좌표 범위 오류')
        current_cell_position=(current_cell_column,current_cell_row)
        if current_cell_position in current_seen_positions:raise ValueError('중복 셀 변경')
        current_seen_positions.add(current_cell_position)
        if current_cell_record['tile'] not in current_allowed_codes or type(current_cell_record['height']) is not int or not 0<=current_cell_record['height']<=20 or type(current_cell_record['blocked']) is not bool:raise ValueError('타일·고도(0~20)·통행 차단 값 오류')
        if current_allowed_codes[current_cell_record['tile']] in MAP_BLOCKED_TERRAIN_NAMES and not current_cell_record['blocked']:raise ValueError('물·벽·바위 등 차단 타일은 통행 차단을 켜세요.')
        if 'wall' in current_cell_record:
            current_wall_records=[current_wall_record for current_wall_record in current_tile_data.get('cliffOverrides',[]) if current_wall_record['position']!={'column':current_cell_column,'row':current_cell_row}]
            current_wall_records.append({'position':{'column':current_cell_column,'row':current_cell_row},'textureKey':current_cell_record['wall']})
            current_tile_data['cliffOverrides']=current_wall_records
        current_tile_row=list(current_tile_data['rows'][current_cell_row]);current_tile_row[current_cell_column]=current_cell_record['tile'];current_tile_data['rows'][current_cell_row]=''.join(current_tile_row)
        current_terrain_data['elevations'][current_cell_row][current_cell_column]=current_cell_record['height']
        if current_cell_record['blocked']:current_blocked_positions.add(current_cell_position)
        else:current_blocked_positions.discard(current_cell_position)
    validate_map_cliff_overrides(current_tile_data.get('cliffOverrides',[]),current_column_count,current_row_count)
    current_terrain_data['blocked']=[list(current_position) for current_position in sorted(current_blocked_positions,key=lambda current_position:(current_position[1],current_position[0]))]
    current_object_records=current_request_payload['objects']
    if not isinstance(current_object_records,list) or len(current_object_records)>1000:raise ValueError('빌보드 목록 오류')
    current_property_data=read_map_editor_source_data(current_asset_root,'sprite-display-properties.yaml')
    current_allowed_textures=read_map_editor_billboard_identifiers(current_asset_root)
    current_seen_identifiers=set()
    for current_object_record in current_object_records:
        if not isinstance(current_object_record,dict) or set(current_object_record)!={'id','kind','position','textureKey','tileAnchor'}:raise ValueError('빌보드 필드 오류')
        current_object_identifier=current_object_record['id']
        if not isinstance(current_object_identifier,str) or not re.fullmatch('[a-z0-9][a-z0-9-]{0,95}',current_object_identifier) or current_object_identifier in current_seen_identifiers:raise ValueError('빌보드 ID 중복 또는 형식 오류')
        current_seen_identifiers.add(current_object_identifier)
        if current_object_record['kind']!='decoration' or current_object_record['textureKey'] not in current_allowed_textures or current_object_record['tileAnchor']!='center':raise ValueError('등록된 장식 빌보드만 배치할 수 있습니다.')
        current_cell_position=current_object_record['position']
        if not isinstance(current_cell_position,dict) or set(current_cell_position)!={'column','row'} or any(type(current_cell_position[current_axis_name]) is not int or not 0<=current_cell_position[current_axis_name]<current_axis_limit for current_axis_name,current_axis_limit in [('column',current_column_count),('row',current_row_count)]):raise ValueError('빌보드 좌표 오류')
    current_fixed_objects=[current_object_record for current_object_record in current_tile_data.get('objects',[]) if current_object_record['kind']!='decoration']
    if current_seen_identifiers & {current_object_record['id'] for current_object_record in current_fixed_objects}:raise ValueError('보호된 구조물 ID입니다.')
    current_tile_data['objects']=current_fixed_objects+copy.deepcopy(current_object_records)
    validate_scenery_object_collisions(current_tile_data['objects'],current_property_data,current_terrain_data['elevations'])
    from tools.review.domains.map_assets.terrain_effects import validate_terrain_effect_records
    from tools.review.domains.map_assets.terrain_ambient import validate_terrain_ambient_tint
    validate_terrain_ambient_tint(current_request_payload)
    if 'ambientTint' in current_request_payload:
        current_terrain_data['ambientTint']=current_request_payload['ambientTint']
    validate_terrain_ambient_tint(current_terrain_data)
    if 'ambientTint' in current_terrain_data:
        current_render_record['ambientTint']=current_terrain_data['ambientTint']
    current_effect_records=current_request_payload.get('terrainEffects',current_terrain_data.get('terrainEffects',[]))
    validate_terrain_effect_records(current_effect_records,current_column_count,current_row_count,current_tile_data['objects'])
    if 'terrainEffects' in current_request_payload:
        current_terrain_data['terrainEffects']=copy.deepcopy(current_effect_records)
    current_render_record['terrainEffects']=copy.deepcopy(current_effect_records)
    current_render_record.update(elevations=current_terrain_data['elevations'],terrainRows=current_tile_data['rows'],objects=copy.deepcopy(current_tile_data['objects']),blocked=[{'column':current_column,'row':current_row} for current_column,current_row in current_blocked_positions])
    current_render_record['cliffOverrides']=copy.deepcopy(current_tile_data.get('cliffOverrides',[]))
    apply_sprite_display_properties(current_render_record,current_property_data)
    current_render_record['spriteProperties']={current_record['textureKey']:current_property_data[current_record['textureKey']] for current_record in current_object_records}
    current_blocked_positions|=collect_billboard_blocked_cells(current_render_record['objects'])
    current_start_position=tuple(current_render_record['startPoint'][current_axis_name] for current_axis_name in ('column','row'))
    if current_start_position in current_blocked_positions:raise ValueError('시작점은 통행 가능해야 합니다.')
    current_reachable_cells={current_start_position};current_pending_cells=deque([current_start_position])
    while current_pending_cells:
        current_cell_column,current_cell_row=current_pending_cells.popleft()
        for current_next_column,current_next_row in [(current_cell_column+1,current_cell_row),(current_cell_column-1,current_cell_row),(current_cell_column,current_cell_row+1),(current_cell_column,current_cell_row-1)]:
            current_next_position=(current_next_column,current_next_row)
            if not 0<=current_next_column<current_column_count or not 0<=current_next_row<current_row_count or current_next_position in current_blocked_positions or current_next_position in current_reachable_cells:continue
            if abs(current_terrain_data['elevations'][current_next_row][current_next_column]-current_terrain_data['elevations'][current_cell_row][current_cell_column])>1:continue
            current_reachable_cells.add(current_next_position);current_pending_cells.append(current_next_position)
    for current_connection_record in current_render_record['connections']:
        if (current_connection_record['column'],current_connection_record['row']) not in current_reachable_cells:raise ValueError('출구 연결이 끊어집니다: '+current_connection_record['direction'])
    current_walkable_count=current_column_count*current_row_count-len(current_blocked_positions)
    if len(current_reachable_cells)!=current_walkable_count:raise ValueError(f'고립된 통행 셀 {current_walkable_count-len(current_reachable_cells)}칸이 있습니다.')
    current_documents_changed=any(current_document!=yaml.safe_load(current_source_bytes[current_source_path]) for current_source_path,current_document in zip(current_source_paths,current_documents))
    current_preview_result={'changed':current_documents_changed,'render':current_render_record,'reachable':len(current_reachable_cells),'objects':len(current_object_records),'cells':len(current_changed_cells)}
    return (current_asset_root,current_source_paths,current_documents,current_source_bytes),current_preview_result


def preview_map_editor_changes(current_request_payload):
    current_snapshot_values,current_preview_result=validate_map_editor_changes(current_request_payload)
    current_preview_token=hashlib.sha256(json.dumps(current_request_payload,sort_keys=True).encode()).hexdigest()
    MAP_EDITOR_STORAGE_ROOT.mkdir(parents=True,exist_ok=True)
    (MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'.json')).write_text(json.dumps(current_request_payload))
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        current_asset_root,current_source_paths,current_documents,current_source_bytes=current_snapshot_values
        current_revision_record=json.loads(current_request_payload['revision'])
        current_database_payload={'requestId':current_preview_token,'expectedGeneration':current_revision_record['generation'],
            'documents':[{'path':current_source_path.relative_to(current_asset_root/'assets/maps').as_posix(),
                'revision':current_revision_record['revisions'][current_source_path.relative_to(current_asset_root/'assets/maps').as_posix()],
                'document':current_document} for current_source_path,current_document in zip(current_source_paths,current_documents)]}
        (MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'-database.json')).write_text(json.dumps(current_database_payload))
    return {**current_preview_result,'token':current_preview_token}


def save_map_editor_changes(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)-{'terrainEffects','ambientTint'}!={'token','map','revision','cells','objects'}:raise ValueError('검증된 초안과 token이 필요합니다.')
    current_validation_payload={current_field_name:current_field_value for current_field_name,current_field_value in current_request_payload.items() if current_field_name!='token'}
    current_preview_token=hashlib.sha256(json.dumps(current_validation_payload,sort_keys=True).encode()).hexdigest()
    if current_request_payload['token']!=current_preview_token or not (MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'.json')).is_file():raise ValueError('변경 내용을 먼저 검증하세요.')
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        current_database_payload=json.loads((MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'-database.json')).read_text())
        current_database_result=execute_content_api_request('POST','/internal/v1/content/map-changes',current_database_payload)
        return {**current_database_result,'map':current_request_payload['map']}
    (current_asset_root,current_source_paths,current_documents,current_source_bytes),current_preview_result=validate_map_editor_changes(current_validation_payload)
    if not current_preview_result['changed']:return {'saved':False,'unchanged':True,'map':current_request_payload['map']}
    current_metadata_paths=[current_asset_root/'asset-registry.yaml',current_asset_root.parent/'slime-backend/map-data.lock.yaml',current_asset_root/'assets/billboards/catalog.yaml']
    current_metadata_paths.extend(list_billboard_catalog_paths(current_asset_root)[1:])
    for current_metadata_path in current_metadata_paths:current_source_bytes[current_metadata_path]=current_metadata_path.read_bytes()
    current_pending_files={current_source_path:yaml.safe_dump(current_document,allow_unicode=True,sort_keys=False,width=120).encode() for current_source_path,current_document in zip(current_source_paths,current_documents)}
    for current_metadata_path in current_metadata_paths[:2]:
        current_metadata_text=current_source_bytes[current_metadata_path].decode()
        for current_source_path in current_source_paths:
            current_output_bytes=current_pending_files[current_source_path]
            current_old_hash=hashlib.sha256(current_source_bytes[current_source_path]).hexdigest()
            if current_metadata_text.count(current_old_hash)!=1:raise ValueError('등록부·소비자 해시 불일치')
            current_metadata_text=current_metadata_text.replace(current_old_hash,hashlib.sha256(current_output_bytes).hexdigest())
        current_pending_files[current_metadata_path]=current_metadata_text.encode()
    current_backup_root=MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'-backup');current_backup_root.mkdir(exist_ok=True)
    for current_file_index,(current_source_path,current_source_content) in enumerate(current_source_bytes.items()):(current_backup_root/str(current_file_index)).write_bytes(current_source_content)
    (current_backup_root/'paths.json').write_text(json.dumps([str(current_source_path) for current_source_path in current_source_bytes]))
    for current_source_path,current_source_content in current_source_bytes.items():
        if current_source_path.read_bytes()!=current_source_content:raise ValueError('저장 직전에 원본이 변경되었습니다. 초안은 유지됩니다.')
    try:
        for current_source_path,current_output_bytes in current_pending_files.items():
            current_temporary_path=current_source_path.with_suffix('.map-editor-tmp');current_temporary_path.write_bytes(current_output_bytes);os.replace(current_temporary_path,current_source_path)
        write_billboard_catalog(current_asset_root,build_catalog_reference(current_asset_root))
    except Exception:
        for current_source_path,current_source_content in current_source_bytes.items():current_source_path.write_bytes(current_source_content)
        raise
    return {'saved':True,'map':current_request_payload['map'],'reachable':current_preview_result['reachable'],'backup':current_preview_token}



def read_map_editor_source_data(current_asset_root,current_relative_path):
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        from urllib.parse import urlencode
        return execute_content_api_request('GET','/internal/v1/content/map-document?'+urlencode({'path':current_relative_path}))['data']
    return load_unique_yaml_document(current_asset_root/'assets/maps'/current_relative_path)['data']


def read_map_editor_billboard_identifiers(current_asset_root):
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        return {current_asset_identifier for current_asset_identifier,current_property_values in read_map_editor_source_data(current_asset_root,'sprite-display-properties.yaml').items() if 'groundFootprintColumns' in current_property_values}
    return {current_record['texture_key'] for current_record in build_catalog_reference(current_asset_root)['billboards']}
