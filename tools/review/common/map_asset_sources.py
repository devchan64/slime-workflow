"""에셋 저장소의 맵 YAML을 요청마다 검증해 검수 화면 데이터로 해석한다."""
from pathlib import Path
import yaml
from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_asset

MAP_CITY_REVIEW_IDENTIFIERS = ('iseulon','reedhaven','stonewarm')
MAP_REVIEW_IDENTIFIERS = ('iseulon','reedhaven','stonewarm','dry-creek','reed-crossing','silver-marsh','pebble-shore')
MAP_CITY_TERRAIN_CODES = dict(g='grass',p='paving',w='water',h='shallow-water',q='deep-water',r='reed-bed',v='gravel',b='boulder')
MAP_BLOCKED_TERRAIN_NAMES = {'water','wall','boulder','tree-base','cactus','shallow-water','deep-water'}
MAP_SOURCE_BLOCK_HEIGHT = 60


class UniqueMapSourceLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result_mapping_value = {}
        for source_key_node,source_value_node in node.value:
            source_key_value = self.construct_object(source_key_node,deep=deep)
            if not isinstance(source_key_value,str) or source_key_value in result_mapping_value:
                raise ValueError('맵 원본 YAML 키 오류')
            result_mapping_value[source_key_value] = self.construct_object(source_value_node,deep=deep)
        return result_mapping_value


def read_registered_map_data(relative_source_path, source_provenance_records):
    asset_root_directory, registered_asset_records = load_registered_tiles()
    current_source_path,current_source_record = resolve_registered_asset('assets/maps/'+relative_source_path,asset_root_directory,registered_asset_records,'assets/maps')
    current_source_document = yaml.load(current_source_path.read_text(),Loader=UniqueMapSourceLoader)
    if not isinstance(current_source_document,dict) or set(current_source_document)!={'managementId','data'} or current_source_document['managementId']!=current_source_record['managementId'] or not isinstance(current_source_document['data'],dict):
        raise ValueError('맵 원본 관리 ID·자료형 오류: '+relative_source_path)
    source_provenance_records.append(current_source_record)
    return current_source_document['data']


def build_source_building_blocks(current_building_record):
    current_block_records = []
    current_floor_count = current_building_record['floors']
    current_slope_columns = current_building_record['width']%2==0
    current_slope_length = current_building_record['width'] if current_slope_columns else current_building_record['height']
    if current_slope_length%2: raise ValueError('맞배 지붕은 가로 또는 세로가 짝수여야 합니다.')
    for current_row_index in range(current_building_record['height']):
        for current_column_index in range(current_building_record['width']):
            current_slope_index = current_column_index if current_slope_columns else current_row_index
            current_roof_level = min(current_slope_index,current_slope_length-1-current_slope_index)
            current_roof_base = (current_floor_count+current_roof_level)*MAP_SOURCE_BLOCK_HEIGHT
            for current_stack_height in range(0,current_roof_base,MAP_SOURCE_BLOCK_HEIGHT):
                current_block_records.append(dict(id=f"{current_building_record['id']}-{current_column_index}-{current_row_index}-{current_stack_height}",column=current_column_index,row=current_row_index,layer=current_stack_height//MAP_SOURCE_BLOCK_HEIGHT,offsetHeight=0,height=MAP_SOURCE_BLOCK_HEIGHT,shape='full',material='wall',walkable=False))
            current_high_side = ('east' if current_slope_index<current_slope_length//2 else 'west') if current_slope_columns else ('south' if current_slope_index<current_slope_length//2 else 'north')
            current_block_records.append(dict(id=f"{current_building_record['id']}-roof-{current_column_index}-{current_row_index}",column=current_column_index,row=current_row_index,layer=current_roof_base//MAP_SOURCE_BLOCK_HEIGHT,offsetHeight=0,height=MAP_SOURCE_BLOCK_HEIGHT,shape='ramp',highSide=current_high_side,material='roof',walkable=False))
    return current_block_records


def load_registered_map_review(map_identifier_value):
    if map_identifier_value not in MAP_REVIEW_IDENTIFIERS: raise ValueError('검수 대상 맵 ID가 아닙니다.')
    source_provenance_records = []
    read_map_source_data = lambda relative_source_path: read_registered_map_data(relative_source_path,source_provenance_records)
    current_name_record = read_map_source_data('map_names/'+map_identifier_value+'.yaml')
    if map_identifier_value in ('dry-creek','reed-crossing','silver-marsh','pebble-shore'):
        current_map_record = read_map_source_data('terrain/maps/'+map_identifier_value+'.yaml')
        current_map_record['terrainRows'] = read_map_source_data('field_tiles/'+map_identifier_value+'.yaml')['rows']
        current_map_record['terrainCodes'] = read_map_source_data('field_tiles/codes.yaml')
        current_map_record.update(read_map_source_data('map_spawns/'+map_identifier_value+'.yaml'))
        current_map_record['buildings'] = []
        current_map_record['blocked'] = [dict(column=current_position[0],row=current_position[1]) for current_position in current_map_record['blocked']] + [dict(current_map_record['startPoint'])]
    else:
        current_map_record = read_map_source_data('city_layouts/'+map_identifier_value+'.yaml')
        current_map_record['terrainCodes'] = MAP_CITY_TERRAIN_CODES
        current_map_record['blocked'] = []
        for current_building_record in current_map_record['buildings']:
            current_building_record['facilityKind'] = current_building_record['facilityId'].rsplit('-',1)[-1]
            if current_building_record['facilityKind'] not in {'guild','bookshop','inn','workshop','market'}: raise ValueError('등록되지 않은 건물 종류')
            current_building_record['blockSchemaVersion'] = 1
            current_building_record['blocks'] = build_source_building_blocks(current_building_record)
            for current_row_index in range(current_building_record['height']):
                for current_column_index in range(current_building_record['width']):
                    current_map_record['blocked'].append(dict(column=current_building_record['origin']['column']+current_column_index,row=current_building_record['origin']['row']+current_row_index))
    current_map_record.update(id=map_identifier_value,name=current_name_record['ko'],provenance=source_provenance_records)
    for current_row_index,current_terrain_row in enumerate(current_map_record['terrainRows']):
        if len(current_terrain_row)!=current_map_record['columns']: raise ValueError('맵 원본 행 길이 오류')
        for current_column_index,current_code_value in enumerate(current_terrain_row):
            if current_map_record['terrainCodes'][current_code_value] in MAP_BLOCKED_TERRAIN_NAMES:
                current_map_record['blocked'].append(dict(column=current_column_index,row=current_row_index))
    if len(current_map_record['terrainRows'])!=current_map_record['rows']: raise ValueError('맵 원본 행 수 오류')
    current_map_record['terrainCodes'] = {current_code_value:current_terrain_name for current_code_value,current_terrain_name in current_map_record['terrainCodes'].items() if any(current_code_value in current_row_value for current_row_value in current_map_record['terrainRows'])}
    return current_map_record
