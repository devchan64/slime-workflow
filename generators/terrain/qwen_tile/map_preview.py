"""타일 후보를 적용할 맵 스냅샷의 엄격한 YAML 계약을 제공한다."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml


def read_map_preview_snapshot(snapshot_file_path: Path) -> tuple[dict, str]:
    """중복 키 없이 맵 검수 스냅샷을 읽고 해시를 돌려준다."""
    class UniqueMapPreviewLoader(yaml.SafeLoader):
        pass

    def construct_unique_map_mapping(loader_instance, node_value, deep=False):
        parsed_mapping_values = {}
        for key_node, value_node in node_value.value:
            current_key_value = loader_instance.construct_object(key_node, deep=deep)
            if current_key_value in parsed_mapping_values:
                raise ValueError(f'중복 맵 스냅샷 키: {current_key_value}')
            parsed_mapping_values[current_key_value] = loader_instance.construct_object(value_node, deep=deep)
        return parsed_mapping_values

    UniqueMapPreviewLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_map_mapping)
    snapshot_source_bytes = Path(snapshot_file_path).read_bytes()
    snapshot_value = yaml.load(snapshot_source_bytes.decode('utf-8'), Loader=UniqueMapPreviewLoader)
    return validate_map_preview_snapshot(snapshot_value), hashlib.sha256(snapshot_source_bytes).hexdigest()


def validate_map_preview_snapshot(snapshot_value: dict) -> dict:
    """특정 맵의 지정 타일 적용 검수에 필요한 최소 상태를 검증한다."""
    expected_field_names = {'schemaVersion', 'mapId', 'displayNameKo', 'columns', 'rows', 'terrainRows', 'terrainCodes', 'targetCells'}
    if not isinstance(snapshot_value, dict) or set(snapshot_value) != expected_field_names:
        raise ValueError('맵 스냅샷 필드가 계약과 다릅니다.')
    if snapshot_value['schemaVersion'] != 1 or not isinstance(snapshot_value['mapId'], str) or not snapshot_value['mapId']:
        raise ValueError('맵 스냅샷 schemaVersion 또는 mapId가 올바르지 않습니다.')
    if not isinstance(snapshot_value['displayNameKo'], str) or not snapshot_value['displayNameKo'].strip():
        raise ValueError('맵 스냅샷 displayNameKo가 필요합니다.')
    for current_dimension_name in ('columns', 'rows'):
        current_dimension_value = snapshot_value[current_dimension_name]
        if type(current_dimension_value) is not int or not 1 <= current_dimension_value <= 64:
            raise ValueError(f'맵 스냅샷 {current_dimension_name}은 1~64 정수여야 합니다.')
    map_column_count = snapshot_value['columns']
    map_row_count = snapshot_value['rows']
    if not isinstance(snapshot_value['terrainRows'], list) or len(snapshot_value['terrainRows']) != map_row_count or any(not isinstance(current_row_value, str) or len(current_row_value) != map_column_count for current_row_value in snapshot_value['terrainRows']):
        raise ValueError('맵 스냅샷 terrainRows 크기가 맞지 않습니다.')
    if not isinstance(snapshot_value['terrainCodes'], dict) or not snapshot_value['terrainCodes']:
        raise ValueError('맵 스냅샷 terrainCodes가 필요합니다.')
    for current_code_name, current_code_value in snapshot_value['terrainCodes'].items():
        if not isinstance(current_code_name, str) or len(current_code_name) != 1 or not isinstance(current_code_value, dict) or set(current_code_value) != {'labelKo', 'color'}:
            raise ValueError('맵 스냅샷 terrainCodes 형식이 올바르지 않습니다.')
        if not isinstance(current_code_value['labelKo'], str) or not current_code_value['labelKo'].strip() or not isinstance(current_code_value['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', current_code_value['color']):
            raise ValueError('맵 스냅샷 지형 라벨 또는 색상이 올바르지 않습니다.')
    known_terrain_codes = set(snapshot_value['terrainCodes'])
    if any(current_code_name not in known_terrain_codes for current_row_value in snapshot_value['terrainRows'] for current_code_name in current_row_value):
        raise ValueError('terrainRows에 정의되지 않은 지형 코드가 있습니다.')
    if not isinstance(snapshot_value['targetCells'], list) or not snapshot_value['targetCells']:
        raise ValueError('맵 스냅샷 targetCells가 필요합니다.')
    selected_cell_keys = set()
    for current_target_cell in snapshot_value['targetCells']:
        if not isinstance(current_target_cell, dict) or set(current_target_cell) != {'column', 'row'} or type(current_target_cell['column']) is not int or type(current_target_cell['row']) is not int or not (0 <= current_target_cell['column'] < map_column_count and 0 <= current_target_cell['row'] < map_row_count):
            raise ValueError('맵 스냅샷 targetCells 좌표가 올바르지 않습니다.')
        current_cell_key = (current_target_cell['column'], current_target_cell['row'])
        if current_cell_key in selected_cell_keys:
            raise ValueError('맵 스냅샷 targetCells 좌표가 중복됩니다.')
        selected_cell_keys.add(current_cell_key)
    return snapshot_value
