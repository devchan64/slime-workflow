"""야외 맵의 타일·고도·빌보드 초안 검증과 원본 저장."""
from tools.management.maintenance.sync_billboard_catalog import load_billboard_catalog, list_billboard_catalog_paths, write_billboard_catalog, prepare_billboard_catalog_files
import copy
import fcntl
import threading
import tempfile
import hashlib
import json
import os
import re
from collections import deque
from pathlib import Path
import yaml
from tools.management.common.map_tile_assets import load_registered_tiles, resolve_registered_asset
from tools.management.common.map_asset_sources import load_registered_map_review, normalize_field_surface_data, map_wall_tile_records, MAP_BLOCKED_TERRAIN_NAMES, validate_map_cliff_overrides
from tools.management.common.sprite_display_properties import apply_sprite_display_properties, collect_billboard_blocked_cells
from tools.management.domains.map_assets.placement import validate_scenery_object_collisions
from tools.management.maintenance.sync_billboard_catalog import load_unique_yaml_document, build_catalog_reference

MAP_EDITOR_STORAGE_ROOT=Path(__file__).resolve().parents[4]/'.tmp/map-layout-editor'
MAP_EDITOR_ALLOWED_COMMANDS=('map-edit-load','map-edit-preview','map-edit-save')
MAP_EDITOR_SAVE_LOCK = threading.RLock()


def inspect_map_save_pending(current_marker_path):
    """중단 표식의 실제 부재만 저장 가능 상태로 인정한다."""
    try:
        current_marker_path.lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return None
    return True


def read_map_editor_snapshot(current_map_identifier):
    if not isinstance(current_map_identifier,str) or not re.fullmatch('[a-z0-9-]+',current_map_identifier):raise ValueError('맵 ID 오류')
    current_asset_root,current_asset_records=load_registered_tiles()
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.management.domains.map_assets.database_client import execute_content_api_request
        from urllib.parse import urlencode
        current_database_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle?'+urlencode({'map':current_map_identifier}))
        from tools.management.common.map_asset_sources import UniqueMapSourceLoader, validate_review_bundle_map_sources
        validate_review_bundle_map_sources(current_database_bundle)
        current_relative_documents=[f'field_tiles/{current_map_identifier}.yaml',f'terrain/maps/{current_map_identifier}.yaml']
        current_registered_sources=[resolve_registered_asset('assets/maps/'+current_relative_path,current_asset_root,current_asset_records,'assets/maps') for current_relative_path in current_relative_documents]
        current_source_paths=[current_source_path for current_source_path,current_source_record in current_registered_sources]
        current_property_source=resolve_registered_asset('assets/maps/sprite-display-properties.yaml',current_asset_root,current_asset_records,'assets/maps')
        current_source_bytes={}
        for current_source_path,current_source_record in [*current_registered_sources,current_property_source]:
            current_source_content=current_source_path.read_bytes()
            if hashlib.sha256(current_source_content).hexdigest()!=current_source_record['sha256']:
                raise ValueError('맵 편집 원본이 읽는 중 변경되었습니다.')
            current_source_bytes[current_source_path]=current_source_content
        current_documents=[yaml.load(current_source_bytes[current_source_path],Loader=UniqueMapSourceLoader) for current_source_path in current_source_paths]
        for current_relative_path,current_document_value in zip(current_relative_documents,current_documents):
            if json.dumps(current_document_value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))!=json.dumps(current_database_bundle['documents'][current_relative_path],sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')):
                raise ValueError('DB 맵 편집 문서가 에셋 원본과 다릅니다: '+current_relative_path)
        validate_review_bundle_map_sources(current_database_bundle)
        current_revision_hash=json.dumps({'generation':current_database_bundle['generation'],'revisions':{current_relative_path:current_database_bundle['revisions'][current_relative_path] for current_relative_path in current_relative_documents},'asset_sha256':{current_source_path.relative_to(current_asset_root/'assets/maps').as_posix():hashlib.sha256(current_bytes_value).hexdigest() for current_source_path,current_bytes_value in current_source_bytes.items()}},sort_keys=True)
        return current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash
    current_relative_paths=[f'assets/maps/field_tiles/{current_map_identifier}.yaml',f'assets/maps/terrain/maps/{current_map_identifier}.yaml']
    from tools.management.common.map_asset_sources import UniqueMapSourceLoader
    current_registered_sources=[resolve_registered_asset(current_relative_path,current_asset_root,current_asset_records,'assets/maps') for current_relative_path in current_relative_paths]
    current_property_source=resolve_registered_asset('assets/maps/sprite-display-properties.yaml',current_asset_root,current_asset_records,'assets/maps')
    current_source_paths=[current_source_path for current_source_path,current_source_record in current_registered_sources]
    current_source_bytes={}
    for current_source_path,current_source_record in [*current_registered_sources,current_property_source]:
        current_source_content=current_source_path.read_bytes()
        if hashlib.sha256(current_source_content).hexdigest()!=current_source_record['sha256']:
            raise ValueError('맵 편집 원본이 읽는 중 변경되었습니다.')
        current_source_bytes[current_source_path]=current_source_content
    current_documents=[yaml.load(current_source_bytes[current_source_path],Loader=UniqueMapSourceLoader) for current_source_path in current_source_paths]
    current_revision_hash=hashlib.sha256(b''.join(current_source_bytes.values())).hexdigest()
    return current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash


def load_map_editor_document(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'map'}:raise ValueError('map ID만 지정하세요. 현재 야외필드 편집을 지원합니다.')
    current_asset_root,current_source_paths,current_documents,current_source_bytes,current_revision_hash=read_map_editor_snapshot(current_request_payload['map'])
    current_render_record=load_registered_map_review(current_request_payload['map'])
    current_render_record['terrainCodes']=read_map_editor_source_data(current_asset_root,'field_tiles/codes.yaml')
    return {'map':current_request_payload['map'],'revision':current_revision_hash,'tiles':current_documents[0]['data'],'terrain':current_documents[1]['data'],'render':current_render_record,'textures':sorted(read_map_editor_billboard_identifiers(current_asset_root)),'codes':current_render_record['terrainCodes'],
            'wall_tiles':list(map_wall_tile_records()),
            'blocked_tile_codes':[code for code,name in current_render_record['terrainCodes'].items() if name in MAP_BLOCKED_TERRAIN_NAMES]}


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
    from tools.management.domains.map_assets.terrain_effects import validate_terrain_effect_records
    from tools.management.domains.map_assets.terrain_ambient import validate_terrain_ambient_tint
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
    current_database_mode=os.environ.get('SLIME_CONTENT_STORAGE')=='database'
    current_pending_marker=MAP_EDITOR_STORAGE_ROOT/'map-save-pending.json'
    current_pending_state=inspect_map_save_pending(current_pending_marker)
    current_save_block_reason='interrupted' if current_pending_state is True else 'database' if current_pending_state is False and current_database_mode else None
    return {**current_preview_result,'token':current_preview_token,'save_available':current_pending_state is False and not current_database_mode,'save_block_reason':current_save_block_reason}


def update_registered_map_hashes(current_metadata_text,current_hash_replacements):
    """경로별 등록 항목의 검증된 SHA-256만 바꾸며 YAML 서식을 보존한다."""
    if any(isinstance(current_yaml_event,yaml.AliasEvent) for current_yaml_event in yaml.parse(current_metadata_text,Loader=yaml.SafeLoader)):
        raise ValueError('맵 등록 목록의 YAML 별칭은 안전하게 갱신할 수 없습니다.')
    current_root_node=yaml.compose(current_metadata_text,Loader=yaml.SafeLoader)
    if not isinstance(current_root_node,yaml.MappingNode):raise ValueError('맵 등록 목록 형식 오류')
    current_root_entries={}
    for current_key_node,current_value_node in current_root_node.value:
        if not isinstance(current_key_node,yaml.ScalarNode) or current_key_node.value in current_root_entries:raise ValueError('맵 등록 목록 중복 키 오류')
        current_root_entries[current_key_node.value]=current_value_node
    current_list_nodes=[current_root_entries[current_name] for current_name in ('assets','files') if current_name in current_root_entries]
    if len(current_list_nodes)!=1 or not isinstance(current_list_nodes[0],yaml.SequenceNode):raise ValueError('맵 등록 항목 형식 오류')
    current_replacement_nodes=[]
    for current_entry_node in current_list_nodes[0].value:
        if not isinstance(current_entry_node,yaml.MappingNode):raise ValueError('맵 등록 항목 오류')
        current_field_nodes={}
        for current_key_node,current_value_node in current_entry_node.value:
            if not isinstance(current_key_node,yaml.ScalarNode) or current_key_node.value in current_field_nodes:raise ValueError('맵 등록 항목 중복 키 오류')
            current_field_nodes[current_key_node.value]=current_value_node
        current_path_node=current_field_nodes.get('path')
        if not isinstance(current_path_node,yaml.ScalarNode) or current_path_node.value not in current_hash_replacements:continue
        current_hash_node=current_field_nodes.get('sha256')
        current_old_hash,current_new_hash=current_hash_replacements[current_path_node.value]
        if not isinstance(current_hash_node,yaml.ScalarNode) or current_hash_node.value!=current_old_hash or not re.fullmatch('[a-f0-9]{64}',current_new_hash):raise ValueError('등록부·소비자 해시 불일치')
        current_replacement_nodes.append((current_hash_node.start_mark.index,current_hash_node.end_mark.index,current_new_hash,current_path_node.value))
    if len(current_replacement_nodes)!=len(current_hash_replacements) or len({current_item[3] for current_item in current_replacement_nodes})!=len(current_hash_replacements):raise ValueError('맵 경로별 등록 항목 누락 또는 중복')
    for current_start_index,current_end_index,current_hash_value,_ in sorted(current_replacement_nodes,reverse=True):
        current_metadata_text=current_metadata_text[:current_start_index]+current_hash_value+current_metadata_text[current_end_index:]
    return current_metadata_text


def prepare_registered_map_update_files(current_asset_root,current_source_paths,current_documents,current_source_bytes,current_metadata_paths):
    """원본·등록부·백엔드 잠금의 변경 바이트를 계산하며 파일에는 쓰지 않는다."""
    if not current_source_paths or len(current_source_paths)!=len(current_documents) or len(set(current_source_paths))!=len(current_source_paths) or len(current_metadata_paths)!=2 or len(set(current_metadata_paths))!=2:
        raise ValueError('맵 원본 또는 등록부 변경 대상 오류')
    current_map_root=current_asset_root/'assets/maps'
    if any(not current_source_path.is_relative_to(current_map_root) or current_source_path.suffix!='.yaml' or current_source_path not in current_source_bytes for current_source_path in current_source_paths):
        raise ValueError('맵 원본 변경 경로 오류')
    if any(current_metadata_path not in current_source_bytes for current_metadata_path in current_metadata_paths):
        raise ValueError('맵 등록부 변경 원본 누락')
    current_pending_files={current_source_path:yaml.safe_dump(current_document,allow_unicode=True,sort_keys=False,width=120).encode() for current_source_path,current_document in zip(current_source_paths,current_documents)}
    current_hash_replacements={current_source_path.relative_to(current_asset_root).as_posix():(hashlib.sha256(current_source_bytes[current_source_path]).hexdigest(),hashlib.sha256(current_pending_files[current_source_path]).hexdigest()) for current_source_path in current_source_paths}
    for current_metadata_path in current_metadata_paths:
        current_metadata_text=current_source_bytes[current_metadata_path].decode()
        current_pending_files[current_metadata_path]=update_registered_map_hashes(current_metadata_text,current_hash_replacements).encode()
    return current_pending_files


def save_map_editor_changes(current_request_payload):
    """같은 편집기의 파일 저장을 프로세스 간 직렬화한다."""
    with MAP_EDITOR_SAVE_LOCK:
        MAP_EDITOR_STORAGE_ROOT.mkdir(parents=True,exist_ok=True)
        current_lock_path=MAP_EDITOR_STORAGE_ROOT/'save.lock'
        current_lock_descriptor=os.open(current_lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            fcntl.flock(current_lock_descriptor,fcntl.LOCK_EX)
            return save_locked_map_editor_changes(current_request_payload)
        finally:
            os.close(current_lock_descriptor)


def save_locked_map_editor_changes(current_request_payload):
    if not isinstance(current_request_payload,dict) or set(current_request_payload)-{'terrainEffects','ambientTint'}!={'token','map','revision','cells','objects'}:raise ValueError('검증된 초안과 token이 필요합니다.')
    current_validation_payload={current_field_name:current_field_value for current_field_name,current_field_value in current_request_payload.items() if current_field_name!='token'}
    current_preview_token=hashlib.sha256(json.dumps(current_validation_payload,sort_keys=True).encode()).hexdigest()
    if current_request_payload['token']!=current_preview_token or not (MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'.json')).is_file():raise ValueError('변경 내용을 먼저 검증하세요.')
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        raise ValueError('DB 모드의 야외 맵 저장은 원본·등록부·백엔드 잠금의 동기 저장이 구현될 때까지 중단됩니다.')
    current_pending_marker=MAP_EDITOR_STORAGE_ROOT/'map-save-pending.json'
    current_pending_state=inspect_map_save_pending(current_pending_marker)
    if current_pending_state is None:
        raise ValueError('야외 맵 저장 표식의 상태를 확인할 수 없습니다. 저장을 보류합니다.')
    if current_pending_state:
        raise ValueError('완료되지 않은 야외 맵 저장이 있습니다. 백업과 원본·등록부·잠금을 확인하세요.')
    (current_asset_root,current_source_paths,current_documents,current_source_bytes),current_preview_result=validate_map_editor_changes(current_validation_payload)
    if not current_preview_result['changed']:return {'saved':False,'unchanged':True,'map':current_request_payload['map']}
    current_metadata_paths=[current_asset_root/'asset-registry.yaml',current_asset_root.parent/'slime-backend/map-data.lock.yaml',current_asset_root/'assets/billboards/catalog.yaml']
    current_metadata_paths.extend(list_billboard_catalog_paths(current_asset_root)[1:])
    for current_metadata_path in current_metadata_paths:current_source_bytes[current_metadata_path]=current_metadata_path.read_bytes()
    current_pending_files=prepare_registered_map_update_files(current_asset_root,current_source_paths,current_documents,current_source_bytes,current_metadata_paths[:2])
    current_backup_root=MAP_EDITOR_STORAGE_ROOT/(current_preview_token+'-backup');current_backup_root.mkdir(exist_ok=True)
    for current_file_index,(current_source_path,current_source_content) in enumerate(current_source_bytes.items()):(current_backup_root/str(current_file_index)).write_bytes(current_source_content)
    (current_backup_root/'paths.json').write_text(json.dumps([str(current_source_path) for current_source_path in current_source_bytes]))
    for current_source_path,current_source_content in current_source_bytes.items():
        if current_source_path.read_bytes()!=current_source_content:raise ValueError('저장 직전에 원본이 변경되었습니다. 초안은 유지됩니다.')
    from tools.management.common.generation_records import write_record_atomically
    write_record_atomically(current_pending_marker,{'version':2,'map':current_request_payload['map'],'backup':current_preview_token+'-backup','before_sha256':[hashlib.sha256(current_source_content).hexdigest() for current_source_content in current_source_bytes.values()],'after_sha256':[hashlib.sha256(current_pending_files[current_source_path]).hexdigest() if current_source_path in current_pending_files else None for current_source_path in current_source_bytes]})
    try:
        for current_source_path,current_output_bytes in current_pending_files.items():
            current_temporary_descriptor,current_temporary_name=tempfile.mkstemp(prefix='.'+current_source_path.name+'.map-',dir=current_source_path.parent)
            current_temporary_path=Path(current_temporary_name)
            try:
                with os.fdopen(current_temporary_descriptor,'wb') as current_temporary_file:
                    os.fchmod(current_temporary_file.fileno(),current_source_path.stat().st_mode & 0o7777)
                    current_temporary_file.write(current_output_bytes)
                os.replace(current_temporary_path,current_source_path)
            finally:
                current_temporary_path.unlink(missing_ok=True)
        write_billboard_catalog(current_asset_root,build_catalog_reference(current_asset_root))
    except Exception as current_save_error:
        current_failed_paths=[]
        for current_source_path,current_source_content in current_source_bytes.items():
            try:current_source_path.write_bytes(current_source_content)
            except Exception:current_failed_paths.append(current_source_path.name)
        if current_failed_paths:
            raise RuntimeError('야외 맵 저장 실패 후 일부 복원에 실패했습니다. 백업을 확인하세요: '+', '.join(current_failed_paths)) from current_save_error
        current_pending_marker.unlink()
        raise
    current_pending_marker.unlink()
    return {'saved':True,'map':current_request_payload['map'],'reachable':current_preview_result['reachable'],'backup':current_preview_token}



def read_map_editor_source_data(current_asset_root,current_relative_path):
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.management.domains.map_assets.database_client import execute_content_api_request
        from urllib.parse import urlencode
        from tools.management.common.map_asset_sources import UniqueMapSourceLoader, validate_review_bundle_map_sources
        current_database_document=execute_content_api_request('GET','/internal/v1/content/map-document?'+urlencode({'path':current_relative_path}))
        current_database_bundle={'documents':{current_relative_path:current_database_document}}
        validate_review_bundle_map_sources(current_database_bundle)
        current_registered_root,current_registered_records=load_registered_tiles()
        if Path(current_asset_root).resolve()!=current_registered_root.resolve():raise ValueError('맵 편집 에셋 저장소가 변경되었습니다.')
        current_source_path,current_source_record=resolve_registered_asset('assets/maps/'+current_relative_path,current_registered_root,current_registered_records,'assets/maps')
        current_source_bytes=current_source_path.read_bytes()
        if hashlib.sha256(current_source_bytes).hexdigest()!=current_source_record['sha256']:raise ValueError('맵 편집 원본이 읽는 중 변경되었습니다.')
        current_source_document=yaml.load(current_source_bytes,Loader=UniqueMapSourceLoader)
        if json.dumps(current_source_document,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))!=json.dumps(current_database_document,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':')):
            raise ValueError('DB 맵 편집 문서가 에셋 원본과 다릅니다: '+current_relative_path)
        validate_review_bundle_map_sources(current_database_bundle)
        return current_source_document['data']
    return load_unique_yaml_document(current_asset_root/'assets/maps'/current_relative_path)['data']


def read_map_editor_billboard_identifiers(current_asset_root):
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        return {current_asset_identifier for current_asset_identifier,current_property_values in read_map_editor_source_data(current_asset_root,'sprite-display-properties.yaml').items() if 'groundFootprintColumns' in current_property_values}
    return {current_record['texture_key'] for current_record in build_catalog_reference(current_asset_root)['billboards']}
