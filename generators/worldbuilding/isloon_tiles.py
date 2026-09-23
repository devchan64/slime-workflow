#!/usr/bin/env python3
"""이슬온 타일 카탈로그와 건물 프리셋을 조립·검증한다."""
from pathlib import Path
import argparse
import json
import yaml

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
ISLOON_ROOT = WORKFLOW_ROOT / 'assets/world/isloon'


def load_yaml_document(document_path):
    with Path(document_path).open(encoding='utf-8') as document_file:
        document_values = yaml.safe_load(document_file)
    if not isinstance(document_values, dict) or document_values.get('schema_version') != 1:
        raise ValueError(f'지원하지 않는 YAML 문서: {document_path}')
    return document_values


def expand_rectangle_tiles(rectangle_values, tile_identifier):
    return [{'column': rectangle_values['column'] + column_offset, 'row': rectangle_values['row'] + row_offset, 'tile': tile_identifier}
            for row_offset in range(rectangle_values['rows'])
            for column_offset in range(rectangle_values['columns'])]


def expand_prefab_cells(prefab_values):
    if 'cells' in prefab_values:
        return prefab_values['cells']
    size_values = prefab_values['size']
    if 'tile' in prefab_values:
        return [{'column': column_index, 'row': row_index, 'tile': prefab_values['tile'], 'layer': 'roof'}
                for row_index in range(size_values['rows'])
                for column_index in range(size_values['columns'])]
    roof_rows = prefab_values['roof_rows']
    entrance_positions = {(cell['column'], cell['row']) for cell in prefab_values.get('entrances', [])}
    cells = [{'column': column_index, 'row': row_index,
              'tile': prefab_values['roof_tile'] if row_index < roof_rows else prefab_values['wall_tile'],
              'layer': 'roof' if row_index < roof_rows else 'object'}
             for row_index in range(size_values['rows'])
             for column_index in range(size_values['columns'])]
    cells.extend({'column': column_index, 'row': row_index, 'tile': prefab_values['door_tile'], 'layer': 'object'}
                 for column_index, row_index in entrance_positions)
    return cells


def expand_prefab_collision(prefab_values):
    if 'collision' in prefab_values:
        return prefab_values['collision']
    entrance_cells = {(cell['column'], cell['row']) for cell in prefab_values.get('entrances', [])}
    size_values = prefab_values['size']
    return [{'column': column_index, 'row': row_index}
            for row_index in range(size_values['rows'])
            for column_index in range(size_values['columns'])
            if (column_index, row_index) not in entrance_cells]


def match_adjacent_tile_connections(layer_cells, connection_values):
    cell_lookup = {(cell['column'], cell['row']): cell['tile'] for cell in layer_cells}
    connection_lookup = {(connection['from'], connection['to']): connection['id'] for connection in connection_values}
    matched_connections = []
    for (column, row), tile_identifier in cell_lookup.items():
        for neighbor_column, neighbor_row, edge_name in ((column + 1, row, 'east'), (column, row + 1, 'south')):
            neighbor_tile = cell_lookup.get((neighbor_column, neighbor_row))
            connection_id = connection_lookup.get((tile_identifier, neighbor_tile))
            reverse_connection_id = connection_lookup.get((neighbor_tile, tile_identifier))
            if connection_id or reverse_connection_id:
                matched_connections.append({'column': column, 'row': row, 'edge': edge_name, 'from': tile_identifier, 'to': neighbor_tile, 'connection': connection_id or reverse_connection_id})
    return matched_connections


def assemble_isloon_map(map_path, output_path):
    catalog_values = load_yaml_document(ISLOON_ROOT / 'tile-catalog.yaml')
    prefab_values = load_yaml_document(ISLOON_ROOT / 'building-prefabs.yaml')
    map_values = load_yaml_document(map_path)
    tile_values = {tile['id']: tile for tile in catalog_values['tiles']}
    prefab_lookup = {prefab['id']: prefab for prefab in prefab_values['prefabs']}
    grid_values = map_values['grid']
    assembled_layers = {'ground': [], 'object': [], 'roof': []}
    ground_values = map_values['layers']['ground']
    for row in range(grid_values['rows']):
        for column in range(grid_values['columns']):
            assembled_layers['ground'].append({'column': column, 'row': row, 'tile': ground_values['default']})
    for patch_values in ground_values.get('patches', []):
        assembled_layers['ground'] = [cell for cell in assembled_layers['ground'] if not (
            patch_values['rectangle']['column'] <= cell['column'] < patch_values['rectangle']['column'] + patch_values['rectangle']['columns'] and
            patch_values['rectangle']['row'] <= cell['row'] < patch_values['rectangle']['row'] + patch_values['rectangle']['rows'])]
        assembled_layers['ground'].extend(expand_rectangle_tiles(patch_values['rectangle'], patch_values['tile']))
    building_collision_cells = []
    for building_instance in map_values['buildings']:
        prefab = prefab_lookup[building_instance['prefab']]
        origin = building_instance['position']
        for cell in expand_prefab_cells(prefab):
            layer_name = cell['layer']
            assembled_layers[layer_name].append({'column': origin['column'] + cell['column'], 'row': origin['row'] + cell['row'], 'tile': cell['tile']})
        building_collision_cells.extend({'column': origin['column'] + cell['column'], 'row': origin['row'] + cell['row']} for cell in expand_prefab_collision(prefab))
    vegetation_values = map_values.get('vegetation', [])
    no_entry_zone_values = map_values.get('no_entry_zones', [])
    no_entry_cell_values = [cell_values for zone_values in no_entry_zone_values for cell_values in zone_values['cells']]
    all_cells = [cell for layer_cells in assembled_layers.values() for cell in layer_cells]
    for cell in all_cells:
        if cell['tile'] not in tile_values:
            raise ValueError(f'등록되지 않은 타일: {cell["tile"]}')
        if not 0 <= cell['column'] < grid_values['columns'] or not 0 <= cell['row'] < grid_values['rows']:
            raise ValueError(f'맵 밖 타일: {cell}')
    for zone_values in no_entry_zone_values:
        if not isinstance(zone_values.get('id'), str) or not zone_values['id'] or not zone_values.get('cells'):
            raise ValueError(f'잘못된 출입 금지 영역: {zone_values}')
        for blocked_cell_values in zone_values['cells']:
            if not 0 <= blocked_cell_values.get('column', -1) < grid_values['columns'] or not 0 <= blocked_cell_values.get('row', -1) < grid_values['rows']:
                raise ValueError(f'맵 밖 출입 금지 영역: {zone_values["id"]} {blocked_cell_values}')
    for vegetation_record in vegetation_values:
        if vegetation_record.get('kind') != 'broadleaf' or not isinstance(vegetation_record.get('id'), str) or not isinstance(vegetation_record.get('crown_scale'), (int, float)) or vegetation_record['crown_scale'] <= 0:
            raise ValueError(f'지원하지 않는 수목 데이터: {vegetation_record}')
        vegetation_position = vegetation_record.get('position', {})
        if not 0 <= vegetation_position.get('column', -1) < grid_values['columns'] or not 0 <= vegetation_position.get('row', -1) < grid_values['rows']:
            raise ValueError(f'맵 밖 수목 위치: {vegetation_record}')
        if (vegetation_position['column'], vegetation_position['row']) not in {
            (blocked_cell_values['column'], blocked_cell_values['row']) for blocked_cell_values in no_entry_cell_values
        }:
            raise ValueError(f'수목 뿌리 위치가 출입 금지 영역에 포함되지 않았습니다: {vegetation_record["id"]}')
    collision_cells = building_collision_cells + no_entry_cell_values
    if len({(cell_values['column'], cell_values['row']) for cell_values in collision_cells}) != len(collision_cells):
        raise ValueError('건물 충돌 영역과 출입 금지 영역의 칸이 중복됩니다.')
    assembled_values = {'schema_version': 1, 'map_id': map_values['map_id'], 'display_name': map_values.get('display_name', map_values['map_id']), 'safe_town': map_values.get('safe_town', False), 'grid': grid_values, 'layers': assembled_layers, 'connections': match_adjacent_tile_connections(assembled_layers['ground'], catalog_values['connections']), 'collision': collision_cells, 'no_entry_zones': no_entry_zone_values, 'vegetation': vegetation_values, 'buildings': map_values['buildings'], 'spawn': map_values['spawn'], 'map_connections': map_values.get('connections', []), 'tile_catalog': 'tile-catalog.yaml', 'building_prefabs': 'building-prefabs.yaml'}
    Path(output_path).write_text(json.dumps(assembled_values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return assembled_values


def run_isloon_tile_assembly_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path, default=ISLOON_ROOT / 'maps/village-01.yaml')
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    assemble_isloon_map(arguments.map, arguments.output)


if __name__ == '__main__':
    run_isloon_tile_assembly_command()
