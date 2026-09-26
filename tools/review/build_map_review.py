#!/usr/bin/env python3
"""이슬온 YAML 맵을 조립하고 검수 서버용 패키지를 만든다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import json
import shutil
import sys

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_DIRECTORY = WORKFLOW_ROOT / 'assets/world/isloon/maps'
REVIEW_TEMPLATE_PATH = WORKFLOW_ROOT / 'assets/world/isloon/map-review.html'
FRONTEND_ASSET_ROOT = WORKFLOW_ROOT.parent / 'slime-frontend/src/assets'
def load_map_render_profiles():
    import yaml
    profile_record_values = yaml.safe_load((WORKFLOW_ROOT/'assets/world/isloon/render-profiles.yaml').read_text())
    if not isinstance(profile_record_values,dict) or set(profile_record_values)!={'schema_version','field','town','wall_height','character_height'} or profile_record_values['schema_version']!=1:
        raise ValueError('맵 렌더링 프로필 형식 오류')
    for profile_kind_name in ('field','town'):
        profile_size_record = profile_record_values[profile_kind_name]
        if set(profile_size_record)!={'tile_width','tile_height'} or any(type(size_value) is not int or size_value<=0 for size_value in profile_size_record.values()) or profile_size_record['tile_width']!=2*profile_size_record['tile_height']:
            raise ValueError('맵 타일은 양의 정수 2:1 크기여야 합니다.')
    if profile_record_values['wall_height']!=100 or profile_record_values['character_height']!=60:
        raise ValueError('벽 높이 100px와 캐릭터 기준 60px는 고정입니다.')
    return profile_record_values

MAP_RENDER_PROFILE_VALUES = load_map_render_profiles()
ISOMETRIC_BUILDING_WALL_HEIGHT = MAP_RENDER_PROFILE_VALUES['wall_height']
ISOMETRIC_BUILDING_ROOF_HEIGHT = 7
ISOMETRIC_BUILDING_PREVIEW_LEVEL = 2
ISOMETRIC_PREVIEW_TOP_PADDING = ISOMETRIC_BUILDING_PREVIEW_LEVEL * ISOMETRIC_BUILDING_WALL_HEIGHT + ISOMETRIC_BUILDING_ROOF_HEIGHT + 32
ISOMETRIC_DOOR_HEIGHT = 72
ISOMETRIC_DOOR_HALF_WIDTH_TILES = .28
ISOMETRIC_DOOR_FRAME_HALF_WIDTH_TILES = .32
ISOMETRIC_MAP_ROTATIONS = (0, 90, 180, 270)
ISOMETRIC_VISIBLE_BUILDING_SIDES = {'east', 'south'}

sys.path.insert(0, str(WORKFLOW_ROOT / 'generators/worldbuilding'))
from isloon_tiles import assemble_isloon_map


def project_building_point(column_value, row_value, elevation_value, row_count, half_tile_width, half_tile_height, vertical_offset=0):
    return (row_count * half_tile_width + (column_value - row_value) * half_tile_width,
            (column_value + row_value) * half_tile_height - elevation_value + vertical_offset)


def rotate_map_cell_position(cell_values, map_dimension, rotation_degrees):
    column_value = cell_values['column']
    row_value = cell_values['row']
    if rotation_degrees == 0:
        return {'column': column_value, 'row': row_value}
    if rotation_degrees == 90:
        return {'column': map_dimension - 1 - row_value, 'row': column_value}
    if rotation_degrees == 180:
        return {'column': map_dimension - 1 - column_value, 'row': map_dimension - 1 - row_value}
    if rotation_degrees == 270:
        return {'column': row_value, 'row': map_dimension - 1 - column_value}
    raise ValueError(f'지원하지 않는 맵 회전: {rotation_degrees}')


def rotate_map_rectangle_position(position_values, rectangle_width, rectangle_depth, map_dimension, rotation_degrees):
    origin_column = position_values['column']
    origin_row = position_values['row']
    if rotation_degrees == 0:
        return {'position': dict(position_values), 'width': rectangle_width, 'depth': rectangle_depth}
    if rotation_degrees == 90:
        return {'position': {'column': map_dimension - origin_row - rectangle_depth, 'row': origin_column}, 'width': rectangle_depth, 'depth': rectangle_width}
    if rotation_degrees == 180:
        return {'position': {'column': map_dimension - origin_column - rectangle_width, 'row': map_dimension - origin_row - rectangle_depth}, 'width': rectangle_width, 'depth': rectangle_depth}
    if rotation_degrees == 270:
        return {'position': {'column': origin_row, 'row': map_dimension - origin_column - rectangle_width}, 'width': rectangle_depth, 'depth': rectangle_width}
    raise ValueError(f'지원하지 않는 맵 회전: {rotation_degrees}')


def rotate_building_side(side_name, rotation_degrees):
    compass_side_names = ('north', 'east', 'south', 'west')
    return compass_side_names[(compass_side_names.index(side_name) + rotation_degrees // 90) % len(compass_side_names)]


def rotate_building_local_cell(cell_values, building_width, building_depth, rotation_degrees):
    if rotation_degrees == 0:
        return dict(cell_values)
    if rotation_degrees == 90:
        return {'column': building_depth - 1 - cell_values['row'], 'row': cell_values['column']}
    if rotation_degrees == 180:
        return {'column': building_width - 1 - cell_values['column'], 'row': building_depth - 1 - cell_values['row']}
    if rotation_degrees == 270:
        return {'column': cell_values['row'], 'row': building_width - 1 - cell_values['column']}
    raise ValueError(f'지원하지 않는 건물 회전: {rotation_degrees}')


def select_building_entrance_side(building_instance, prefab_record, ground_tile_lookup):
    origin_column = building_instance['position']['column']
    origin_row = building_instance['position']['row']
    building_width = prefab_record['size']['columns']
    building_depth = prefab_record['size']['rows']
    side_cells = {
        'north': [(origin_column + column_offset, origin_row - 1) for column_offset in range(building_width)],
        'east': [(origin_column + building_width, origin_row + row_offset) for row_offset in range(building_depth)],
        'south': [(origin_column + column_offset, origin_row + building_depth) for column_offset in range(building_width)],
        'west': [(origin_column - 1, origin_row + row_offset) for row_offset in range(building_depth)],
    }
    entrance_cells = prefab_record.get('entrances', [])
    if len(entrance_cells) != 1:
        raise ValueError(f'건물 프리팹에는 기준 입구 타일을 정확히 1개 지정해야 합니다: {prefab_record["id"]}')
    entrance_cell = entrance_cells[0]
    side_distances = {
        'north': entrance_cell['row'],
        'east': building_width - 1 - entrance_cell['column'],
        'south': building_depth - 1 - entrance_cell['row'],
        'west': entrance_cell['column'],
    }
    side_priority_names = ('south', 'east', 'north', 'west')
    return max(side_priority_names, key=lambda current_side_name: (
        -side_distances[current_side_name],
        sum(ground_tile_lookup.get(current_cell_position) == 'paving' for current_cell_position in side_cells[current_side_name]),
        -side_priority_names.index(current_side_name)))


def transform_building_for_map_rotation(building_instance, prefab_record, map_dimension, rotation_degrees, ground_tile_lookup):
    origin_column = building_instance['position']['column']
    origin_row = building_instance['position']['row']
    building_width = prefab_record['size']['columns']
    building_depth = prefab_record['size']['rows']
    entrance_side = select_building_entrance_side(building_instance, prefab_record, ground_tile_lookup)
    rotated_geometry = rotate_map_rectangle_position(building_instance['position'], building_width, building_depth, map_dimension, rotation_degrees)
    entrance_cell = rotate_building_local_cell(prefab_record['entrances'][0], building_width, building_depth, rotation_degrees)
    return {'position': rotated_geometry['position'], 'size': {'columns': rotated_geometry['width'], 'rows': rotated_geometry['depth']},
            'entrance_side': rotate_building_side(entrance_side, rotation_degrees), 'entrance_cell': entrance_cell}


def draw_no_entry_zone_preview(preview_image, zone_values, map_dimension, rotation_degrees, half_tile_width, half_tile_height):
    from PIL import ImageDraw
    drawing_context = ImageDraw.Draw(preview_image, 'RGBA')
    for source_cell_values in zone_values['cells']:
        rotated_cell = rotate_map_cell_position(source_cell_values, map_dimension, rotation_degrees)
        center_point = project_building_point(rotated_cell['column'] + .5, rotated_cell['row'] + .5, 0,
                                              map_dimension, half_tile_width, half_tile_height,
                                              ISOMETRIC_PREVIEW_TOP_PADDING)
        corner_points = ((center_point[0], center_point[1] - half_tile_height),
                         (center_point[0] + half_tile_width, center_point[1]),
                         (center_point[0], center_point[1] + half_tile_height),
                         (center_point[0] - half_tile_width, center_point[1]))
        drawing_context.polygon(corner_points, fill=(191, 86, 61, 52), outline=(218, 121, 92, 150))


def draw_tree_volume_preview(preview_image, vegetation_record, map_dimension, rotation_degrees, half_tile_width, half_tile_height):
    from PIL import ImageDraw
    rotated_position = rotate_map_cell_position(vegetation_record['position'], map_dimension, rotation_degrees)
    tree_center = project_building_point(rotated_position['column'] + .5, rotated_position['row'] + .5, 0,
                                         map_dimension, half_tile_width, half_tile_height,
                                         ISOMETRIC_PREVIEW_TOP_PADDING)
    scale_value = float(vegetation_record['crown_scale'])
    drawing_context = ImageDraw.Draw(preview_image, 'RGBA')
    trunk_top_y = tree_center[1] - 76 * scale_value
    drawing_context.polygon(((tree_center[0] - 6, tree_center[1]), (tree_center[0] + 6, tree_center[1]),
                             (tree_center[0] + 4, trunk_top_y + 12), (tree_center[0] - 4, trunk_top_y + 12)),
                            fill=(104, 67, 39, 255), outline=(61, 43, 29, 255))
    for canopy_level, canopy_radius in enumerate((28, 23, 17)):
        canopy_center_y = trunk_top_y + canopy_level * 15 * scale_value + 10
        canopy_radius_value = canopy_radius * scale_value
        foliage_color = ((49, 105, 66, 255), (61, 126, 75, 255), (79, 145, 85, 255))[canopy_level]
        drawing_context.ellipse((tree_center[0] - canopy_radius_value, canopy_center_y - canopy_radius_value * .42,
                                 tree_center[0] + canopy_radius_value, canopy_center_y + canopy_radius_value * .42),
                                fill=foliage_color, outline=(35, 79, 48, 255), width=2)
    drawing_context.ellipse((tree_center[0] - 4, trunk_top_y + 6, tree_center[0] + 4, trunk_top_y + 14), fill=(117, 175, 95, 255))


def render_isometric_map_preview(assembled_map_values, map_source_values, prefab_lookup, tile_images,
                                 tile_width, tile_height, rotation_degrees, wall_texture_images):
    from PIL import Image, ImageDraw
    half_tile_width = tile_width // 2
    half_tile_height = tile_height // 2
    map_columns = assembled_map_values['grid']['columns']
    map_rows = assembled_map_values['grid']['rows']
    if map_columns != map_rows:
        raise ValueError('회전 검수는 정사각형 맵만 지원합니다.')
    preview_image = Image.new('RGBA', ((map_columns + map_rows) * half_tile_width,
                                       (map_columns + map_rows) * half_tile_height + tile_height + ISOMETRIC_PREVIEW_TOP_PADDING), (16, 28, 22, 255))
    def project_cell_position(cell_values):
        rotated_cell = rotate_map_cell_position(cell_values, map_columns, rotation_degrees)
        center_x = map_rows * half_tile_width + (rotated_cell['column'] - rotated_cell['row']) * half_tile_width
        center_y = (rotated_cell['column'] + rotated_cell['row']) * half_tile_height + half_tile_height + ISOMETRIC_PREVIEW_TOP_PADDING
        return center_x - half_tile_width, center_y - half_tile_height
    ground_tile_lookup = {(cell_values['column'], cell_values['row']): cell_values['tile']
                          for cell_values in assembled_map_values['layers']['ground']}
    for layer_name in ('ground', 'object'):
        for cell_values in sorted(assembled_map_values['layers'][layer_name], key=lambda current_cell: current_cell['column'] + current_cell['row']):
            preview_image.alpha_composite(tile_images[cell_values['tile']], project_cell_position(cell_values))
    for zone_values in map_source_values.get('no_entry_zones', []):
        draw_no_entry_zone_preview(preview_image, zone_values, map_columns, rotation_degrees, half_tile_width, half_tile_height)
    depth_sorted_instances = []
    for vegetation_record in assembled_map_values['vegetation']:
        rotated_position = rotate_map_cell_position(vegetation_record['position'], map_columns, rotation_degrees)
        depth_sorted_instances.append((sum(rotated_position.values()), 'vegetation', vegetation_record))
    for building_instance in assembled_map_values['buildings']:
        prefab_record = prefab_lookup[building_instance['prefab']]
        transformed_building = transform_building_for_map_rotation(building_instance, prefab_record, map_columns,
                                                                   rotation_degrees, ground_tile_lookup)
        building_depth_value = sum(transformed_building['position'].values()) + sum(transformed_building['size'].values())
        depth_sorted_instances.append((building_depth_value, 'building', (building_instance, transformed_building, prefab_record)))
    rotated_spawn_position = rotate_map_cell_position(assembled_map_values['spawn'], map_columns, rotation_degrees)
    depth_sorted_instances.append((sum(rotated_spawn_position.values()), 'spawn', rotated_spawn_position))
    for _, instance_kind, instance_values in sorted(depth_sorted_instances, key=lambda current_instance: current_instance[0]):
        if instance_kind == 'vegetation':
            draw_tree_volume_preview(preview_image, instance_values, map_columns, rotation_degrees,
                                     half_tile_width, half_tile_height)
            continue
        if instance_kind == 'spawn':
            start_marker_position = project_cell_position(assembled_map_values['spawn'])
            ImageDraw.Draw(preview_image).polygon(((start_marker_position[0] + half_tile_width, start_marker_position[1] + 8),
                                                   (start_marker_position[0] + tile_width - 8, start_marker_position[1] + half_tile_height),
                                                   (start_marker_position[0] + half_tile_width, start_marker_position[1] + tile_height - 8),
                                                   (start_marker_position[0] + 8, start_marker_position[1] + half_tile_height)),
                                                  outline=(255, 255, 255, 255), width=3)
            continue
        _, transformed_building, prefab_record = instance_values
        draw_building_volume_preview(preview_image, transformed_building, prefab_record, map_rows,
                                     half_tile_width, half_tile_height, transformed_building['entrance_side'], wall_texture_images[prefab_record['wall_tile']])
    return preview_image


def paste_projected_wall_texture(preview_image, wall_texture_image, top_left_point, top_right_point, bottom_left_point):
    """원본 타일 전체를 벽의 평행사변형에 투영한다."""
    from PIL import Image
    import math
    horizontal_axis_vector = (top_right_point[0] - top_left_point[0], top_right_point[1] - top_left_point[1])
    vertical_axis_vector = (bottom_left_point[0] - top_left_point[0], bottom_left_point[1] - top_left_point[1])
    bottom_right_point = (top_right_point[0] + vertical_axis_vector[0], top_right_point[1] + vertical_axis_vector[1])
    corner_point_values = (top_left_point, top_right_point, bottom_left_point, bottom_right_point)
    output_left_position = math.floor(min(current_point[0] for current_point in corner_point_values))
    output_top_position = math.floor(min(current_point[1] for current_point in corner_point_values))
    output_image_width = math.ceil(max(current_point[0] for current_point in corner_point_values)) - output_left_position
    output_image_height = math.ceil(max(current_point[1] for current_point in corner_point_values)) - output_top_position
    transform_determinant_value = horizontal_axis_vector[0]*vertical_axis_vector[1] - horizontal_axis_vector[1]*vertical_axis_vector[0]
    if transform_determinant_value == 0:
        raise ValueError('벽면 투영 영역이 비어 있습니다.')
    inverse_horizontal_x = wall_texture_image.width * vertical_axis_vector[1] / transform_determinant_value
    inverse_horizontal_y = -wall_texture_image.width * vertical_axis_vector[0] / transform_determinant_value
    inverse_vertical_x = -wall_texture_image.height * horizontal_axis_vector[1] / transform_determinant_value
    inverse_vertical_y = wall_texture_image.height * horizontal_axis_vector[0] / transform_determinant_value
    offset_horizontal_value = output_left_position - top_left_point[0]
    offset_vertical_value = output_top_position - top_left_point[1]
    projected_wall_image = wall_texture_image.transform((output_image_width, output_image_height), Image.Transform.AFFINE,
        (inverse_horizontal_x, inverse_horizontal_y, inverse_horizontal_x*offset_horizontal_value + inverse_horizontal_y*offset_vertical_value,
         inverse_vertical_x, inverse_vertical_y, inverse_vertical_x*offset_horizontal_value + inverse_vertical_y*offset_vertical_value), Image.Resampling.BILINEAR)
    preview_image.alpha_composite(projected_wall_image, (output_left_position, output_top_position))


def draw_building_volume_preview(preview_image, building_instance, prefab_record, row_count, half_tile_width, half_tile_height, entrance_side, wall_texture_image):
    from PIL import ImageDraw
    drawing_context = ImageDraw.Draw(preview_image)
    origin_column = building_instance['position']['column']
    origin_row = building_instance['position']['row']
    building_width = building_instance['size']['columns']
    building_depth = building_instance['size']['rows']
    wall_height = ISOMETRIC_BUILDING_PREVIEW_LEVEL * ISOMETRIC_BUILDING_WALL_HEIGHT
    point_values = lambda column_value, row_value, elevation_value: project_building_point(
        origin_column + column_value, origin_row + row_value, elevation_value,
        row_count, half_tile_width, half_tile_height, ISOMETRIC_PREVIEW_TOP_PADDING)
    corner_values = [point_values(0, 0, 0), point_values(building_width, 0, 0),
                     point_values(building_width, building_depth, 0), point_values(0, building_depth, 0)]
    upper_corner_values = [point_values(0, 0, wall_height), point_values(building_width, 0, wall_height),
                           point_values(building_width, building_depth, wall_height), point_values(0, building_depth, wall_height)]
    drawing_context.polygon([corner_values[1], corner_values[2], upper_corner_values[2], upper_corner_values[1]],
                            fill=(211, 166, 98, 255), outline=(92, 55, 27, 255))
    drawing_context.polygon([corner_values[2], corner_values[3], upper_corner_values[3], upper_corner_values[2]],
                            fill=(177, 126, 69, 255), outline=(79, 47, 25, 255))
    # 카탈로그의 창문 포함 벽 타일을 한 칸·한 층마다 투영한다.
    for current_floor_index in range(ISOMETRIC_BUILDING_PREVIEW_LEVEL):
        current_bottom_height = current_floor_index * ISOMETRIC_BUILDING_WALL_HEIGHT
        current_top_height = current_bottom_height + ISOMETRIC_BUILDING_WALL_HEIGHT
        for current_column_index in range(building_width):
            paste_projected_wall_texture(preview_image, wall_texture_image,
                point_values(current_column_index, building_depth, current_top_height),
                point_values(current_column_index + 1, building_depth, current_top_height),
                point_values(current_column_index, building_depth, current_bottom_height))
        for current_row_index in range(building_depth):
            paste_projected_wall_texture(preview_image, wall_texture_image,
                point_values(building_width, current_row_index + 1, current_top_height),
                point_values(building_width, current_row_index, current_top_height),
                point_values(building_width, current_row_index + 1, current_bottom_height))
    for horizontal_tile_boundary in range(1, building_width):
        wall_top_start = point_values(horizontal_tile_boundary, building_depth, wall_height)
        wall_base_start = point_values(horizontal_tile_boundary, building_depth, 0)
        drawing_context.line((wall_base_start, wall_top_start), fill=(153, 106, 60, 190), width=1)
    for depth_tile_boundary in range(1, building_depth):
        wall_top_end = point_values(building_width, depth_tile_boundary, wall_height)
        wall_base_end = point_values(building_width, depth_tile_boundary, 0)
        drawing_context.line((wall_base_end, wall_top_end), fill=(137, 93, 53, 190), width=1)
    for level_index in range(1, ISOMETRIC_BUILDING_PREVIEW_LEVEL):
        seam_elevation = level_index * ISOMETRIC_BUILDING_WALL_HEIGHT
        seam_start = point_values(building_width, building_depth, seam_elevation)
        seam_middle = point_values(0, building_depth, seam_elevation)
        seam_end = point_values(building_width, 0, seam_elevation)
        drawing_context.line((seam_start, seam_middle), fill=(105, 66, 34, 255), width=2)
        drawing_context.line((seam_start, seam_end), fill=(125, 78, 38, 255), width=2)
    if entrance_side in ISOMETRIC_VISIBLE_BUILDING_SIDES:
        entrance_cell = building_instance['entrance_cell']
        if entrance_side in {'north', 'south'}:
            wall_span = building_width
            wall_row = 0 if entrance_side == 'north' else building_depth
            door_center_value = entrance_cell['column'] + .5
            door_position_values = lambda horizontal_value, height_value: point_values(horizontal_value, wall_row, height_value)
        else:
            wall_span = building_depth
            wall_column = 0 if entrance_side == 'west' else building_width
            door_center_value = entrance_cell['row'] + .5
            door_position_values = lambda horizontal_value, height_value: point_values(wall_column, horizontal_value, height_value)
        door_center_value = min(max(door_center_value, .5), wall_span - .5)
        frame_half_width = min(ISOMETRIC_DOOR_FRAME_HALF_WIDTH_TILES, door_center_value, wall_span - door_center_value)
        leaf_half_width = min(ISOMETRIC_DOOR_HALF_WIDTH_TILES, frame_half_width - .04)
        frame_bottom_points = (door_position_values(door_center_value - frame_half_width, 0),
                               door_position_values(door_center_value + frame_half_width, 0))
        frame_top_points = (door_position_values(door_center_value - frame_half_width, ISOMETRIC_DOOR_HEIGHT + 6),
                            door_position_values(door_center_value + frame_half_width, ISOMETRIC_DOOR_HEIGHT + 6))
        drawing_context.polygon([frame_bottom_points[0], frame_bottom_points[1], frame_top_points[1], frame_top_points[0]],
                                fill=(224, 183, 112, 255), outline=(65, 40, 25, 255))
        door_bottom_points = (door_position_values(door_center_value - leaf_half_width, 0),
                              door_position_values(door_center_value + leaf_half_width, 0))
        door_top_points = (door_position_values(door_center_value - leaf_half_width, ISOMETRIC_DOOR_HEIGHT),
                           door_position_values(door_center_value + leaf_half_width, ISOMETRIC_DOOR_HEIGHT))
        drawing_context.polygon([door_bottom_points[0], door_bottom_points[1], door_top_points[1], door_top_points[0]],
                                fill=(87, 48, 27, 255), outline=(49, 31, 22, 255))
        handle_point = door_position_values(door_center_value + leaf_half_width * .58, ISOMETRIC_DOOR_HEIGHT * .48)
        drawing_context.ellipse((handle_point[0] - 2, handle_point[1] - 2,
                                 handle_point[0] + 2, handle_point[1] + 2), fill=(236, 196, 102, 255))
    roof_top_values = [point_values(0, 0, wall_height + ISOMETRIC_BUILDING_ROOF_HEIGHT),
                       point_values(building_width, 0, wall_height + ISOMETRIC_BUILDING_ROOF_HEIGHT),
                       point_values(building_width, building_depth, wall_height + ISOMETRIC_BUILDING_ROOF_HEIGHT),
                       point_values(0, building_depth, wall_height + ISOMETRIC_BUILDING_ROOF_HEIGHT)]
    drawing_context.polygon([upper_corner_values[1], upper_corner_values[2], roof_top_values[2], roof_top_values[1]],
                            fill=(181, 93, 40, 255), outline=(91, 44, 22, 255))
    drawing_context.polygon([upper_corner_values[2], upper_corner_values[3], roof_top_values[3], roof_top_values[2]],
                            fill=(153, 75, 33, 255), outline=(91, 44, 22, 255))
    drawing_context.polygon(roof_top_values, fill=(203, 115, 54, 255), outline=(91, 44, 22, 255))
    drawing_context.line([roof_top_values[0], roof_top_values[1], roof_top_values[2], roof_top_values[3], roof_top_values[0]], fill=(240, 175, 104, 255), width=3)


def build_map_review(map_path=None, output_root=None):
    map_paths = [Path(map_path).resolve()] if map_path else sorted(DEFAULT_MAP_DIRECTORY.glob('*.yaml'))
    if not map_paths:
        raise ValueError(f'등록된 이슬온 맵이 없습니다: {DEFAULT_MAP_DIRECTORY}')
    if output_root is None:
        timestamp_text = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
        output_root = WORKFLOW_ROOT / '.tmp' / timestamp_text / 'isloon-map-review'
    output_root = Path(output_root).resolve()
    if not output_root.is_relative_to((WORKFLOW_ROOT / '.tmp').resolve()):
        raise ValueError('검수 결과는 저장소 .tmp 하위여야 합니다.')
    output_root.mkdir(parents=True, exist_ok=False)
    map_output_directory = output_root / 'maps'
    map_output_directory.mkdir()
    from link_review_file import link_or_copy_review_file
    from isloon_tiles import load_yaml_document
    catalog_values = load_yaml_document(WORKFLOW_ROOT / 'assets/world/isloon/tile-catalog.yaml')
    building_prefab_values = load_yaml_document(WORKFLOW_ROOT / 'assets/world/isloon/building-prefabs.yaml')
    tile_output_directory = output_root / 'tiles'
    tile_output_directory.mkdir()
    tile_asset_records = {}
    tile_source_paths = {}
    for tile_record in catalog_values['tiles']:
        source_asset_path = (FRONTEND_ASSET_ROOT / tile_record['asset']).resolve()
        if not source_asset_path.is_file() or not source_asset_path.is_relative_to(FRONTEND_ASSET_ROOT.resolve()):
            raise FileNotFoundError(f'프론트엔드 타일 에셋 누락 또는 범위 밖 경로: {tile_record["asset"]}')
        output_asset_name = f'{tile_record["id"]}{source_asset_path.suffix.lower()}'
        link_or_copy_review_file(source_asset_path, tile_output_directory / output_asset_name)
        tile_asset_records[tile_record['id']] = {'file': f'tiles/{output_asset_name}', 'source': tile_record['asset']}
        tile_source_paths[tile_record['id']] = source_asset_path
    map_records = []
    for current_map_path in map_paths:
        assembled_map_path = map_output_directory / f'{current_map_path.stem}.json'
        assembled_map_values = assemble_isloon_map(current_map_path, assembled_map_path)
        from PIL import Image, ImageDraw
        selected_render_profile = MAP_RENDER_PROFILE_VALUES['town' if assembled_map_values['safe_town'] else 'field']
        isometric_tile_width = selected_render_profile['tile_width']
        isometric_tile_height = selected_render_profile['tile_height']
        half_tile_width = isometric_tile_width // 2
        half_tile_height = isometric_tile_height // 2
        isometric_mask = Image.new('L', (isometric_tile_width, isometric_tile_height), 0)
        ImageDraw.Draw(isometric_mask).polygon(((half_tile_width, 0), (isometric_tile_width - 1, half_tile_height), (half_tile_width, isometric_tile_height - 1), (0, half_tile_height)), fill=255)
        tile_images = {}
        for tile_id, tile_path in tile_source_paths.items():
            # 역투영이 읽는 정사각형 전체를 한 타일로 사용한다.
            source_tile_image = Image.open(tile_path).convert('RGBA').resize((isometric_tile_width, isometric_tile_width), Image.Resampling.LANCZOS)
            projected_tile_image = source_tile_image.transform((isometric_tile_width, isometric_tile_height), Image.Transform.AFFINE, (1, 2, -half_tile_width, -1, 2, half_tile_width), Image.Resampling.BILINEAR)
            projected_tile_image.putalpha(isometric_mask)
            tile_images[tile_id] = projected_tile_image
        wall_texture_images = {tile_record['id']: Image.open(tile_source_paths[tile_record['id']]).convert('RGBA')
                               for tile_record in catalog_values['tiles'] if tile_record['category'] == 'structure'}
        prefab_lookup = {prefab_record['id']: prefab_record for prefab_record in building_prefab_values['prefabs']}
        map_source_values = load_yaml_document(current_map_path)
        preview_records = {}
        for rotation_degrees in ISOMETRIC_MAP_ROTATIONS:
            preview_image = render_isometric_map_preview(assembled_map_values, map_source_values, prefab_lookup,
                                                         tile_images, isometric_tile_width, isometric_tile_height,
                                                         rotation_degrees, wall_texture_images)
            preview_path = map_output_directory / f'{current_map_path.stem}.rotation-{rotation_degrees}.png'
            preview_image.save(preview_path)
            preview_records[str(rotation_degrees)] = f'maps/{preview_path.name}'
        map_records.append({'id': assembled_map_values['map_id'], 'label': assembled_map_values['display_name'], 'file': f'maps/{assembled_map_path.name}', 'preview': preview_records['0'], 'previews': preview_records, 'source': str(current_map_path.relative_to(WORKFLOW_ROOT)), 'render_profile': {**selected_render_profile, 'wall_height': ISOMETRIC_BUILDING_WALL_HEIGHT, 'character_height': MAP_RENDER_PROFILE_VALUES['character_height']}})
    (output_root / 'map-index.json').write_text(json.dumps({'schema_version': 1, 'maps': map_records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output_root / 'tile-assets.json').write_text(json.dumps({'schema_version': 1, 'tiles': tile_asset_records}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output_root / 'building-prefabs.json').write_text(json.dumps(building_prefab_values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # 게임 런타임과 같은 스탠딩 프레임·발 기준점을 검수 패키지에 복사한다.
    from PIL import Image
    character_source_directory = FRONTEND_ASSET_ROOT/'characters/default/standing-v4'
    character_animation_record = json.loads((character_source_directory/'idle-v4.animation.json').read_text())
    character_source_record = json.loads((character_source_directory/'source.json').read_text())
    character_preview_records = {}
    character_output_directory = output_root/'character'
    character_output_directory.mkdir()
    for character_direction_name in ('down_left','down_right','up_left','up_right'):
        character_frame_record = next(frame_record_value for frame_record_value in character_animation_record['frames'] if frame_record_value['frameId']==character_direction_name+'.0')
        character_frame_rectangle = character_frame_record['rect']
        with Image.open(character_source_directory/('standing-'+character_direction_name.replace('_','-')+'.png')) as character_sheet_image:
            character_sheet_image.crop((character_frame_rectangle['x'],character_frame_rectangle['y'],character_frame_rectangle['x']+character_frame_rectangle['width'],character_frame_rectangle['y']+character_frame_rectangle['height'])).save(character_output_directory/(character_direction_name+'.png'))
        character_preview_records[character_direction_name]={'file':'character/'+character_direction_name+'.png','anchor':character_frame_record['anchor'],'width':character_frame_rectangle['width'],'height':character_frame_rectangle['height']}
    (output_root/'character-preview.json').write_text(json.dumps({'directions':character_preview_records,'body_height':character_source_record['referenceBodyHeight'],'top_padding':ISOMETRIC_PREVIEW_TOP_PADDING}))
    shutil.copy2(WORKFLOW_ROOT/'tools/review/ui/map/map-character-preview.js',output_root/'map-character-preview.js')
    shutil.copy2(WORKFLOW_ROOT/'tools/review/ui/map/map-review-layout.css',output_root/'map-review-layout.css')
    shutil.copy2(REVIEW_TEMPLATE_PATH, output_root / 'map-review.html')
    shutil.copy2(WORKFLOW_ROOT / 'assets/world/isloon/building-volume-review.html', output_root / 'building-volume-review.html')
    from tools.review.common.game_render_metrics import load_game_render_metrics
    (output_root / 'game-render-metrics.json').write_text(json.dumps(load_game_render_metrics(FRONTEND_ASSET_ROOT.parents[1]), ensure_ascii=False, indent=2))
    (output_root / 'README.txt').write_text('검수 서버: python3 tools/review/serve.py --root "' + str(output_root) + '" --entry map-review.html\n', encoding='utf-8')
    return output_root


def run_map_review_build_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    print(build_map_review(arguments.map, arguments.output))


if __name__ == '__main__':
    run_map_review_build_command()
