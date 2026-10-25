"""에셋 저장소의 맵 YAML을 요청마다 검증해 검수 화면 데이터로 해석한다."""
from pathlib import Path
from contextvars import ContextVar
from copy import deepcopy
import os
import hashlib
import json
from urllib.parse import urlencode

CURRENT_REVIEW_DATABASE_BUNDLE = ContextVar('review_database_bundle',default=None)
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset

MAP_CITY_TERRAIN_CODES = dict(d='dry-soil-branches',s='stone',g='grass',p='paving',w='water',h='shallow-water',q='deep-water',r='reed-bed',v='gravel',b='boulder')
MAP_BLOCKED_TERRAIN_NAMES = {'water','wall','boulder','tree-base','cactus','shallow-water','deep-water'}
MAP_SOURCE_BLOCK_HEIGHT = 60


def normalize_field_surface_data(current_map_record):
    """현행 원본의 고도 문자열을 숫자 격자로 전달하고 폐기된 연결은 거절한다."""
    current_height_rows = current_map_record['elevations']
    if len(current_height_rows) != current_map_record['rows']:
        raise ValueError('필드 고도 행 수 오류')
    current_normalized_rows = []
    current_legacy_rows = all(isinstance(current_height_row,str) for current_height_row in current_height_rows)
    current_numeric_rows = all(isinstance(current_height_row,list) for current_height_row in current_height_rows)
    if not (current_legacy_rows or current_numeric_rows):
        raise ValueError('고도 행은 문자열 또는 정수 배열로 통일해야 합니다.')
    for current_height_row in current_height_rows:
        if len(current_height_row)!=current_map_record['columns']:
            raise ValueError('필드 고도 행 길이 오류')
        if current_legacy_rows:
            if any(current_height_code not in '0123456789' for current_height_code in current_height_row):
                raise ValueError('기존 고도 문자열은 0~9만 허용합니다. 10~20은 정수 배열을 사용하세요.')
            current_height_row = [int(current_height_code) for current_height_code in current_height_row]
        if any(type(current_height_value) is not int or not 0<=current_height_value<=20 for current_height_value in current_height_row):
            raise ValueError('필드 고도는 0~20 정수여야 합니다.')
        current_normalized_rows.append(list(current_height_row))
    current_map_record['elevations'] = current_normalized_rows
    if current_map_record.get('terrainMovementVersion') != 2:
        raise ValueError('맵 검수 원본은 지형 이동 버전 2여야 합니다.')
    if current_map_record.get('elevationTiles') or current_map_record.get('ramps'):
        raise ValueError('맵 검수 원본은 폐기된 계단·경사로 연결을 허용하지 않습니다.')



class UniqueMapSourceLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result_mapping_value = {}
        for source_key_node,source_value_node in node.value:
            source_key_value = self.construct_object(source_key_node,deep=deep)
            if not isinstance(source_key_value,str) or source_key_value in result_mapping_value:
                raise ValueError('맵 원본 YAML 키 오류')
            result_mapping_value[source_key_value] = self.construct_object(source_value_node,deep=deep)
        return result_mapping_value


def read_registered_map_data(relative_source_path, source_provenance_records, current_source_catalog=None):
    asset_root_directory, registered_asset_records = load_registered_tiles() if current_source_catalog is None else current_source_catalog
    if os.environ.get('SLIME_CONTENT_STORAGE')=='database':
        from tools.review.domains.map_assets.database_client import execute_content_api_request
        current_database_bundle=CURRENT_REVIEW_DATABASE_BUNDLE.get()
        if current_database_bundle is None:
            current_source_document=execute_content_api_request('GET','/internal/v1/content/map-document?'+urlencode({'path':relative_source_path}))
        else:
            current_source_document=deepcopy(current_database_bundle['documents'][relative_source_path])
        current_source_record={'managementId':current_source_document['managementId'],'path':'assets/maps/'+relative_source_path,'source':'assets/maps/'+relative_source_path,
            'version':'database','sha256':hashlib.sha256(json.dumps(current_source_document,sort_keys=True).encode()).hexdigest()}
    else:
        current_source_path,current_source_record = resolve_registered_asset('assets/maps/'+relative_source_path,asset_root_directory,registered_asset_records,'assets/maps')
        current_source_document = yaml.load(current_source_path.read_text(),Loader=UniqueMapSourceLoader)
    if not isinstance(current_source_document,dict) or set(current_source_document)!={'managementId','data'} or current_source_document['managementId']!=current_source_record['managementId'] or not isinstance(current_source_document['data'],dict):
        raise ValueError('맵 원본 관리 ID·자료형 오류: '+relative_source_path)
    source_provenance_records.append(current_source_record)
    current_source_data = current_source_document['data']
    if relative_source_path.startswith(('city_layouts/', 'field_tiles/')) and ('objects' in current_source_data or 'buildings' in current_source_data):
        from tools.review.common.sprite_display_properties import apply_sprite_display_properties, validate_sprite_display_properties
        current_property_catalog = read_registered_map_data('sprite-display-properties.yaml', source_provenance_records, (asset_root_directory, registered_asset_records))
        apply_sprite_display_properties(current_source_data, validate_sprite_display_properties(current_property_catalog))
    return current_source_data


def load_review_map_identifiers(current_source_catalog=None):
    current_source_catalog = load_registered_tiles() if current_source_catalog is None else current_source_catalog
    current_source_records = []
    current_city_index = read_registered_map_data('city_layouts/index.yaml', current_source_records, current_source_catalog)
    current_field_index = read_registered_map_data('field_tiles/index.yaml', current_source_records, current_source_catalog)
    current_city_identifiers = tuple(current_city_index['includes']['layouts'])
    current_field_identifiers = tuple(current_field_index['includes']['maps'])
    if set(current_city_identifiers) & set(current_field_identifiers):
        raise ValueError('도시와 필드의 맵 ID가 중복되었습니다.')
    return current_city_identifiers, (*current_city_identifiers, *current_field_identifiers)


def load_registered_map_review(map_identifier_value):
    if os.environ.get('SLIME_CONTENT_STORAGE')!='database':
        return build_registered_map_review(map_identifier_value)
    from tools.review.domains.map_assets.database_client import execute_content_api_request
    current_database_bundle=execute_content_api_request('GET','/internal/v1/content/review-bundle?'+urlencode({'map':map_identifier_value}))
    current_context_token=CURRENT_REVIEW_DATABASE_BUNDLE.set(current_database_bundle)
    try:
        current_review_record=build_registered_map_review(map_identifier_value)
        current_review_record['contentGeneration']=current_database_bundle['generation']
        current_review_record['imageManifest']={current_texture_key:{**current_image_record,
            'url':'/management/map-assets/database-images/'+current_image_record['sha256']}
            for current_texture_key,current_image_record in current_database_bundle['imageManifest'].items()}
        return current_review_record
    finally:
        CURRENT_REVIEW_DATABASE_BUNDLE.reset(current_context_token)


def build_registered_map_review(map_identifier_value):
    current_source_catalog = load_registered_tiles()
    current_city_identifiers, current_map_identifiers = load_review_map_identifiers(current_source_catalog)
    if map_identifier_value not in current_map_identifiers: raise ValueError('검수 대상 맵 ID가 아닙니다.')
    source_provenance_records = []
    read_map_source_data = lambda relative_source_path: read_registered_map_data(relative_source_path,source_provenance_records,current_source_catalog)
    current_name_record = read_map_source_data('map_names/'+map_identifier_value+'.yaml')
    if map_identifier_value not in current_city_identifiers:
        current_map_record = read_map_source_data('terrain/maps/'+map_identifier_value+'.yaml')
        normalize_field_surface_data(current_map_record)
        # 기존 응답의 빈 연결 필드는 클라이언트 계약 호환을 위해 유지한다.
        current_map_record.update(terrainMovementVersion=2, ramps=[], elevationTiles=[])
        current_map_record['safeTown'] = False
        current_field_tile_data = read_map_source_data('field_tiles/'+map_identifier_value+'.yaml')
        current_map_record['terrainRows'] = current_field_tile_data['rows']
        current_map_record['objects'] = current_field_tile_data.get('objects', [])
        current_map_record['groundDecals'] = current_field_tile_data.get('groundDecals', [])
        from tools.review.domains.map_assets.decals import validate_ground_decal_records
        validate_ground_decal_records(current_map_record['groundDecals'],current_map_record['columns'],current_map_record['rows'])
        current_map_record['groundOverrides'] = current_field_tile_data.get('groundOverrides', [])
        current_map_record['cliffOverrides'] = validate_map_cliff_overrides(current_field_tile_data.get('cliffOverrides', []),current_map_record['columns'],current_map_record['rows'])
        current_map_record['cliffTextureKey'] = validate_map_cliff_texture(current_field_tile_data.get('cliffTextureKey', 'cliff-wall'))
        current_map_record['terrainCodes'] = read_map_source_data('field_tiles/codes.yaml')
        current_map_record.update(read_map_source_data('map_spawns/'+map_identifier_value+'.yaml'))
        current_map_record['buildings'] = []
        from tools.review.common.guard_center_assets import load_guard_center_visuals
        current_guard_catalog,current_guard_provenance = load_guard_center_visuals(current_source_catalog)
        current_map_record['guardCenterProvenance'] = current_guard_provenance
        current_map_record['guardCenters'] = []
        current_map_record['connections'] = []
        for current_connection_record in read_map_source_data('field_waypoints/'+map_identifier_value+'.yaml')['connections']:
            current_horizontal_edge = current_connection_record['direction'] in ('north','south')
            current_edge_length = current_map_record['columns'] if current_horizontal_edge else current_map_record['rows']
            current_edge_offset = current_connection_record['edgeOffset']
            if current_edge_offset == 'center': current_edge_offset = current_edge_length//2
            if type(current_edge_offset) is not int or not 0<=current_edge_offset<current_edge_length:
                raise ValueError('경비센터 관문 좌표 오류')
            current_column_value = current_edge_offset if current_horizontal_edge else (0 if current_connection_record['direction']=='west' else current_map_record['columns']-1)
            current_row_value = (0 if current_connection_record['direction']=='north' else current_map_record['rows']-1) if current_horizontal_edge else current_edge_offset
            current_map_record['connections'].append(dict(current_connection_record,column=current_column_value,row=current_row_value))
            if current_connection_record['target'] not in current_city_identifiers:
                continue
            current_style_name = current_guard_catalog['cities'][current_connection_record['target']]
            current_map_record['guardCenters'].append(dict(cityId=current_connection_record['target'],position=dict(column=current_column_value,row=current_row_value),renderPosition=dict(column=max(1,min(current_map_record['columns']-2,current_column_value)),row=max(1,min(current_map_record['rows']-2,current_row_value))),**current_guard_catalog['styles'][current_style_name]))
        current_map_record['blocked'] = [dict(column=current_position[0],row=current_position[1]) for current_position in current_map_record['blocked']]
    else:
        current_map_record = read_map_source_data('city_layouts/'+map_identifier_value+'.yaml')
        current_map_record['safeTown'] = True
        current_map_record['terrainCodes'] = MAP_CITY_TERRAIN_CODES
        current_map_record['blocked'] = []
        for current_building_record in current_map_record['buildings']:
            if current_building_record.get('kind', 'facility') == 'residence':
                if current_building_record.get('facilityId') is not None: raise ValueError('일반 주택에는 시설 ID를 지정할 수 없습니다.')
                current_building_record['facilityKind'] = 'residence'
            else:
                if current_building_record.get('kind', 'facility') != 'facility': raise ValueError('등록되지 않은 건물 용도')
                current_building_record['facilityKind'] = current_building_record['facilityId'].rsplit('-',1)[-1]
                if current_building_record['facilityKind'] not in {'guild','bookshop','inn','workshop','market'}: raise ValueError('등록되지 않은 건물 종류')
            for current_row_index in range(current_building_record['height']):
                for current_column_index in range(current_building_record['width']):
                    current_map_record['blocked'].append(dict(column=current_building_record['origin']['column']+current_column_index,row=current_building_record['origin']['row']+current_row_index))
    for current_connection_record in current_map_record.get('connections',[]):
        current_connection_record['targetName'] = read_map_source_data('map_names/'+current_connection_record['target']+'.yaml')['ko']
    current_map_record.update(id=map_identifier_value,name=current_name_record['ko'],provenance=source_provenance_records)
    for current_row_index,current_terrain_row in enumerate(current_map_record['terrainRows']):
        if len(current_terrain_row)!=current_map_record['columns']: raise ValueError('맵 원본 행 길이 오류')
        for current_column_index,current_code_value in enumerate(current_terrain_row):
            if current_map_record['terrainCodes'][current_code_value] in MAP_BLOCKED_TERRAIN_NAMES:
                current_map_record['blocked'].append(dict(column=current_column_index,row=current_row_index))
    if len(current_map_record['terrainRows'])!=current_map_record['rows']: raise ValueError('맵 원본 행 수 오류')
    from tools.review.common.sprite_display_properties import collect_billboard_blocked_cells
    current_existing_cells = {(current_cell_record['column'],current_cell_record['row']) for current_cell_record in current_map_record['blocked']}
    current_existing_cells.update((current_column_value,current_row_value)
        for current_column_value,current_row_value in collect_billboard_blocked_cells(current_map_record.get('objects', []))
        if 0 <= current_column_value < current_map_record['columns'] and 0 <= current_row_value < current_map_record['rows'])
    current_map_record['blocked'] = [dict(column=current_column_value,row=current_row_value) for current_column_value,current_row_value in sorted(current_existing_cells)]
    current_map_record['terrainCodes'] = {current_code_value:current_terrain_name for current_code_value,current_terrain_name in current_map_record['terrainCodes'].items() if any(current_code_value in current_row_value for current_row_value in current_map_record['terrainRows'])}
    current_used_textures = {current_object_record['textureKey'] for current_object_record in current_map_record.get('objects', []) if 'textureKey' in current_object_record}
    current_used_textures.update(current_building_record['sprite']['textureKey'] for current_building_record in current_map_record.get('buildings', []) if current_building_record.get('sprite'))
    current_shared_catalog = read_map_source_data('sprite-display-properties.yaml')
    current_map_record['spriteProperties'] = {current_texture_key: current_shared_catalog[current_texture_key] for current_texture_key in current_used_textures if current_texture_key in current_shared_catalog}
    return current_map_record

# 기존 메뉴·검수 빌드 호출부의 import 계약도 등록 인덱스를 따른다.
MAP_CITY_REVIEW_IDENTIFIERS, MAP_REVIEW_IDENTIFIERS = load_review_map_identifiers()


def validate_map_cliff_texture(current_texture_key):
    """벽면 용도로 등록된 타일만 선택한다."""
    current_catalog_path = Path(__file__).resolve().parents[1]/'ui/map/config/tile-catalog.yaml'
    current_tile_catalog = yaml.load(current_catalog_path.read_text(), Loader=UniqueMapSourceLoader)
    current_wall_records = {current_tile_record['id']:current_tile_record for current_tile_record in current_tile_catalog['tiles'] if current_tile_record['category']=='wall'}
    if not isinstance(current_texture_key,str) or current_texture_key not in current_wall_records:
        raise ValueError('등록되지 않은 벽면 타일: '+str(current_texture_key))
    from tools.review.common.map_tile_assets import resolve_registered_tile
    current_asset_root, current_registered_records = load_registered_tiles()
    resolve_registered_tile(current_wall_records[current_texture_key]['asset'], current_asset_root, current_registered_records)
    return current_texture_key


def validate_map_cliff_overrides(current_wall_records, current_column_count, current_row_count):
    """셀별 벽면 선택의 좌표·중복·등록 재질을 검사한다."""
    if not isinstance(current_wall_records, list):
        raise ValueError('벽면 배치는 목록이어야 합니다.')
    current_seen_positions = set()
    current_validated_textures = set()
    for current_wall_record in current_wall_records:
        if not isinstance(current_wall_record, dict) or set(current_wall_record) != {'position', 'textureKey'}:
            raise ValueError('벽면 배치 필드가 올바르지 않습니다.')
        current_cell_position = current_wall_record['position']
        if not isinstance(current_cell_position, dict) or set(current_cell_position) != {'column', 'row'}:
            raise ValueError('벽면 좌표 필드가 올바르지 않습니다.')
        current_column_index, current_row_index = current_cell_position['column'], current_cell_position['row']
        if type(current_column_index) is not int or type(current_row_index) is not int or not (0 <= current_column_index < current_column_count and 0 <= current_row_index < current_row_count):
            raise ValueError('벽면 좌표가 맵 범위를 벗어났습니다.')
        current_position_pair = (current_column_index, current_row_index)
        if current_position_pair in current_seen_positions:
            raise ValueError('벽면 배치가 중복되었습니다.')
        current_seen_positions.add(current_position_pair)
        current_texture_key = current_wall_record['textureKey']
        if not isinstance(current_texture_key, str) or current_texture_key not in current_validated_textures:
            validate_map_cliff_texture(current_texture_key)
            current_validated_textures.add(current_texture_key)
    return current_wall_records
