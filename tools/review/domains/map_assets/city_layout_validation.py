"""도시 원장 편집 시 건물 점유와 이동 연결을 검증한다."""
import copy
import re
from collections import deque
from tools.review.common.sprite_display_properties import apply_sprite_display_properties

CITY_ALLOWED_TERRAIN_CODES = frozenset('dsgpwhqrvb')
CITY_BLOCKED_TERRAIN_CODES = frozenset('whqb')
CITY_ALLOWED_DIRECTIONS = {'north', 'south', 'east', 'west'}
CITY_NEIGHBOR_OFFSETS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def validate_content_city_document(current_property_catalog, current_document_record):
    if not isinstance(current_document_record, dict) or set(current_document_record) != {'managementId', 'data'} or not isinstance(current_document_record['data'], dict):
        raise ValueError('도시 원장 문서 형식 오류')
    current_city_data = copy.deepcopy(current_document_record['data'])
    current_city_required_fields = {'version', 'cityId', 'columns', 'rows', 'safeTown', 'terrainRows', 'startPoint', 'buildings', 'connections', 'objects'}
    if not current_city_required_fields <= set(current_city_data) or set(current_city_data) - current_city_required_fields - {'elevations'}:
        raise ValueError('도시 원장 필드 오류')
    if type(current_city_data['version']) is not int or current_city_data['version'] < 1:
        raise ValueError('도시 원장 버전 오류')
    apply_sprite_display_properties(copy.deepcopy(current_city_data), current_property_catalog)
    current_city_identifier = current_city_data.get('cityId')
    if not isinstance(current_city_identifier, str) or not re.fullmatch(r'[a-z0-9-]+', current_city_identifier) or current_document_record['managementId'] != 'config.city-layouts.' + current_city_identifier:
        raise ValueError('도시 관리 ID 불일치')
    current_column_count = current_city_data.get('columns'); current_row_count = current_city_data.get('rows')
    if any(type(current_count_value) is not int or current_count_value < 3 for current_count_value in (current_column_count, current_row_count)) or current_city_data.get('safeTown') is not True:
        raise ValueError('도시 크기 또는 안전 구역 오류')
    current_terrain_rows = current_city_data.get('terrainRows')
    if not isinstance(current_terrain_rows, list) or len(current_terrain_rows) != current_row_count or any(not isinstance(current_row_value, str) or len(current_row_value) != current_column_count or not set(current_row_value) <= CITY_ALLOWED_TERRAIN_CODES for current_row_value in current_terrain_rows):
        raise ValueError('도시 지형 행 오류')
    current_elevations = current_city_data.get('elevations')
    if current_elevations is not None and (not isinstance(current_elevations, list) or len(current_elevations) != current_row_count or any(not isinstance(current_row_value, list) or len(current_row_value) != current_column_count or any(type(current_height_value) is not int or not 0 <= current_height_value <= 20 for current_height_value in current_row_value) for current_row_value in current_elevations)):
        raise ValueError('도시 고도 오류')
    current_blocked_cells = {(current_column_index, current_row_index) for current_row_index, current_row_value in enumerate(current_terrain_rows) for current_column_index, current_terrain_code in enumerate(current_row_value) if current_terrain_code in CITY_BLOCKED_TERRAIN_CODES}
    current_occupied_cells = set(); current_building_ids = set(); current_required_points = []
    def validate_grid_position(current_position_record):
        if not isinstance(current_position_record, dict) or any(type(current_position_record.get(current_axis_name)) is not int for current_axis_name in ('column', 'row')):
            raise ValueError('도시 좌표 오류')
        current_position_value = (current_position_record['column'], current_position_record['row'])
        if not 0 <= current_position_value[0] < current_column_count or not 0 <= current_position_value[1] < current_row_count:
            raise ValueError('도시 좌표 범위 오류')
        return current_position_value
    current_buildings = current_city_data.get('buildings'); current_objects = current_city_data.get('objects', []); current_connections = current_city_data.get('connections')
    if not isinstance(current_buildings, list) or not current_buildings or not isinstance(current_objects, list) or not isinstance(current_connections, list) or not current_connections:
        raise ValueError('도시 건물·장식·출구 목록 오류')
    for current_building_record in current_buildings:
        if not isinstance(current_building_record, dict) or set(current_building_record) - {'id', 'name', 'kind', 'facilityId', 'sprite', 'origin', 'width', 'height', 'floors', 'entrance', 'facing'}: raise ValueError('건물 필드 오류')
        current_building_kind = current_building_record.get('kind', 'facility')
        if current_building_kind not in ('facility', 'residence') or (current_building_kind == 'facility') != (current_building_record.get('facilityId') is not None): raise ValueError('건물 시설 종류 오류')
        if not isinstance(current_building_record.get('name'), str) or not current_building_record['name'].strip() or type(current_building_record.get('floors', 1)) is not int or current_building_record.get('floors', 1) < 1: raise ValueError('건물 이름·층수 오류')
        current_sprite_record = current_building_record.get('sprite')
        if not isinstance(current_sprite_record, dict) or set(current_sprite_record) != {'textureKey', 'contentWidth'} or type(current_sprite_record['contentWidth']) not in (int, float) or not 0 < current_sprite_record['contentWidth'] <= 1: raise ValueError('건물 스프라이트 오류')
        current_building_id = current_building_record.get('id'); current_origin = validate_grid_position(current_building_record.get('origin')); current_entrance = validate_grid_position(current_building_record.get('entrance'))
        current_width = current_building_record.get('width'); current_height = current_building_record.get('height'); current_direction = current_building_record.get('facing')
        if not isinstance(current_building_id, str) or current_building_id in current_building_ids or any(type(current_size_value) is not int or current_size_value < 1 for current_size_value in (current_width, current_height)) or current_direction not in CITY_ALLOWED_DIRECTIONS:
            raise ValueError('도시 건물 ID·크기·방향 오류')
        current_building_ids.add(current_building_id)
        current_texture_key = current_building_record.get('sprite', {}).get('textureKey')
        if current_texture_key not in current_property_catalog: raise ValueError('건물 공용 속성 누락: ' + str(current_texture_key))
        current_cells = {(current_column_index, current_row_index) for current_column_index in range(current_origin[0], current_origin[0] + current_width) for current_row_index in range(current_origin[1], current_origin[1] + current_height)}
        if any(current_column_index >= current_column_count or current_row_index >= current_row_count for current_column_index, current_row_index in current_cells) or current_cells & (current_occupied_cells | current_blocked_cells): raise ValueError('건물 점유 충돌 또는 범위 오류')
        current_occupied_cells.update(current_cells)
        current_entrance_sides = {'north': current_origin[1]-1 == current_entrance[1] and current_origin[0] <= current_entrance[0] < current_origin[0]+current_width, 'south': current_origin[1]+current_height == current_entrance[1] and current_origin[0] <= current_entrance[0] < current_origin[0]+current_width, 'west': current_origin[0]-1 == current_entrance[0] and current_origin[1] <= current_entrance[1] < current_origin[1]+current_height, 'east': current_origin[0]+current_width == current_entrance[0] and current_origin[1] <= current_entrance[1] < current_origin[1]+current_height}
        if not current_entrance_sides[current_direction]: raise ValueError('건물 출입구 방향 오류')
        current_required_points.append(current_entrance)
    current_blocked_cells |= current_occupied_cells
    current_required_points.append(validate_grid_position(current_city_data.get('startPoint')))
    for current_connection_record in current_connections:
        current_connection_point = validate_grid_position(current_connection_record); current_direction = current_connection_record.get('direction')
        if current_direction not in CITY_ALLOWED_DIRECTIONS or not {'north': current_connection_point[1] == 0, 'south': current_connection_point[1] == current_row_count-1, 'west': current_connection_point[0] == 0, 'east': current_connection_point[0] == current_column_count-1}[current_direction]: raise ValueError('도시 출구 경계 오류')
        current_required_points.append(current_connection_point)
    current_object_positions = set(); current_object_ids = set()
    for current_object_record in current_objects:
        current_object_point = validate_grid_position(current_object_record.get('position')); current_texture_key = current_object_record.get('textureKey'); current_object_id = current_object_record.get('id')
        if current_texture_key not in current_property_catalog or not isinstance(current_object_id, str) or current_object_id in current_object_ids or current_object_point in current_object_positions or current_object_point in current_occupied_cells or current_terrain_rows[current_object_point[1]][current_object_point[0]] == 'p' or any(abs(current_object_point[0]-current_point[0])+abs(current_object_point[1]-current_point[1]) <= 1 for current_point in current_required_points): raise ValueError('도시 장식 위치·속성 오류')
        current_object_ids.add(current_object_id); current_object_positions.add(current_object_point)
        current_object_properties = current_property_catalog[current_texture_key]
        if current_object_properties.get('billboardBlocksMovement', False):
            for current_column_offset in range(current_object_properties['groundFootprintColumns']):
                for current_row_offset in range(current_object_properties['groundFootprintRows']):current_blocked_cells.add((current_object_point[0]+current_column_offset, current_object_point[1]+current_row_offset))
    if any(current_point in current_blocked_cells for current_point in current_required_points): raise ValueError('시작점·출입구·출구가 차단되었습니다.')
    current_reachable_cells = {current_required_points[-len(current_connections)-1]}; current_pending_cells = deque(current_reachable_cells)
    while current_pending_cells:
        current_column_index, current_row_index = current_pending_cells.popleft()
        for current_column_offset, current_row_offset in CITY_NEIGHBOR_OFFSETS:
            current_next_cell = (current_column_index+current_column_offset, current_row_index+current_row_offset)
            if not (0 <= current_next_cell[0] < current_column_count and 0 <= current_next_cell[1] < current_row_count) or current_next_cell in current_blocked_cells or current_next_cell in current_reachable_cells: continue
            if current_elevations is not None and abs(current_elevations[current_next_cell[1]][current_next_cell[0]]-current_elevations[current_row_index][current_column_index]) > 1: continue
            current_reachable_cells.add(current_next_cell); current_pending_cells.append(current_next_cell)
    if any(current_point not in current_reachable_cells for current_point in current_required_points) or len(current_reachable_cells) != current_column_count*current_row_count-len(current_blocked_cells): raise ValueError('도시 통행 공간이 단절되었습니다.')
    return {'cityId':current_city_identifier, 'columns':current_column_count, 'rows':current_row_count, 'buildings':len(current_buildings), 'objects':len(current_objects)}
