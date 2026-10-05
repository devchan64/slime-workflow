#!/usr/bin/env python3
"""에셋 저장소의 등록 맵으로 검수 서버용 패키지를 만든다."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse
import sys

WORKFLOW_ROOT = Path(__file__).resolve().parents[2]
def load_map_render_profiles():
    import yaml
    profile_record_values = yaml.safe_load((WORKFLOW_ROOT/'tools/review/ui/map/config/render-profiles.yaml').read_text())
    if not isinstance(profile_record_values,dict) or set(profile_record_values)!={'schema_version','field','town','wall_height','character_height','block_height'} or profile_record_values['schema_version']!=1:
        raise ValueError('맵 렌더링 프로필 형식 오류')
    for profile_kind_name in ('field','town'):
        profile_size_record = profile_record_values[profile_kind_name]
        if set(profile_size_record)!={'tile_width','tile_height'} or any(type(size_value) is not int or size_value<=0 for size_value in profile_size_record.values()) or profile_size_record['tile_width']!=2*profile_size_record['tile_height']:
            raise ValueError('맵 타일은 양의 정수 2:1 크기여야 합니다.')
    if any(type(profile_record_values[metric_name]) is not int or profile_record_values[metric_name] <= 0
           for metric_name in ('wall_height', 'character_height', 'block_height')):
        raise ValueError('벽·캐릭터·블록 높이 기준은 양의 정수여야 합니다.')
    return profile_record_values

MAP_RENDER_PROFILE_VALUES = load_map_render_profiles()
ISOMETRIC_BUILDING_WALL_HEIGHT = MAP_RENDER_PROFILE_VALUES['wall_height']
ISOMETRIC_BUILDING_ROOF_HEIGHT = 0
ISOMETRIC_BUILDING_PREVIEW_LEVEL = 2
ISOMETRIC_PREVIEW_TOP_PADDING = ISOMETRIC_BUILDING_PREVIEW_LEVEL * ISOMETRIC_BUILDING_WALL_HEIGHT + ISOMETRIC_BUILDING_ROOF_HEIGHT + 32
ISOMETRIC_DOOR_HEIGHT = 72
ISOMETRIC_DOOR_FRAME_HALF_WIDTH_TILES = .32
ISOMETRIC_MAP_ROTATIONS = (0, 90, 180, 270)
ISOMETRIC_VISIBLE_BUILDING_SIDES = {'east', 'south'}

sys.path.insert(0, str(WORKFLOW_ROOT))


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
                                 tile_width, tile_height, rotation_degrees, wall_texture_images, door_texture_images):
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
                                     half_tile_width, half_tile_height, transformed_building['entrance_side'],
                                     wall_texture_images[prefab_record['wall_tile']],
                                     door_texture_images[prefab_record['door_tile']],
                                     tile_images[prefab_record['roof_tile']],
                                     wall_texture_images.get(prefab_record.get('ground_floor_plain_wall_tile')),
                                     wall_texture_images.get(prefab_record.get('ground_floor_small_window_wall_tile')),
                                     wall_texture_images.get(prefab_record.get('upper_floor_large_window_wall_tile')))
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


def select_floor_wall_texture(current_floor_index, wall_cell_index, entrance_cell_index, default_wall_texture,
                              plain_wall_texture, small_window_wall_texture, large_window_wall_texture):
    """1층은 방범 간격을, 2층 이상은 작은창문·큰창문 교대 간격을 적용한다."""
    if current_floor_index != 0:
        if small_window_wall_texture is not None and wall_cell_index % 2 == 0:
            return small_window_wall_texture
        return large_window_wall_texture or default_wall_texture
    if small_window_wall_texture is not None and abs(wall_cell_index - entrance_cell_index) % 2 == 1:
        return small_window_wall_texture
    return plain_wall_texture or default_wall_texture


def draw_building_volume_preview(preview_image, building_instance, prefab_record, row_count, half_tile_width, half_tile_height,
                                 entrance_side, wall_texture_image, door_texture_image, roof_tile_image, plain_wall_texture=None,
                                 small_window_wall_texture=None, large_window_wall_texture=None):
    from PIL import ImageDraw
    drawing_context = ImageDraw.Draw(preview_image)
    origin_column = building_instance['position']['column']
    origin_row = building_instance['position']['row']
    building_width = building_instance['size']['columns']
    building_depth = building_instance['size']['rows']
    building_floor_count = prefab_record['floor_count']
    wall_height = building_floor_count * ISOMETRIC_BUILDING_WALL_HEIGHT
    entrance_cell = building_instance['entrance_cell']
    point_values = lambda column_value, row_value, elevation_value: project_building_point(
        origin_column + column_value, origin_row + row_value, elevation_value,
        row_count, half_tile_width, half_tile_height, ISOMETRIC_PREVIEW_TOP_PADDING)
    corner_values = [point_values(0, 0, 0), point_values(building_width, 0, 0),
                     point_values(building_width, building_depth, 0), point_values(0, building_depth, 0)]
    upper_corner_values = [point_values(0, 0, wall_height), point_values(building_width, 0, wall_height),
                           point_values(building_width, building_depth, wall_height), point_values(0, building_depth, wall_height)]
    drawing_context.polygon([corner_values[1], corner_values[2], upper_corner_values[2], upper_corner_values[1]], fill=(211, 166, 98, 255))
    drawing_context.polygon([corner_values[2], corner_values[3], upper_corner_values[3], upper_corner_values[2]], fill=(177, 126, 69, 255))
    # 카탈로그의 창문 포함 벽 타일을 한 칸·한 층마다 투영한다.
    for current_floor_index in range(building_floor_count):
        current_bottom_height = current_floor_index * ISOMETRIC_BUILDING_WALL_HEIGHT
        current_top_height = current_bottom_height + ISOMETRIC_BUILDING_WALL_HEIGHT
        for current_column_index in range(building_width):
            if entrance_side == 'south' and current_floor_index == 0 and current_column_index == entrance_cell['column']:
                continue
            selected_wall_texture = select_floor_wall_texture(current_floor_index, current_column_index,
                                                              entrance_cell['column'], wall_texture_image,
                                                              plain_wall_texture, small_window_wall_texture, large_window_wall_texture)
            paste_projected_wall_texture(preview_image, selected_wall_texture,
                point_values(current_column_index, building_depth, current_top_height),
                point_values(current_column_index + 1, building_depth, current_top_height),
                point_values(current_column_index, building_depth, current_bottom_height))
        for current_row_index in range(building_depth):
            if entrance_side == 'east' and current_floor_index == 0 and current_row_index == entrance_cell['row']:
                continue
            selected_wall_texture = select_floor_wall_texture(current_floor_index, current_row_index,
                                                              entrance_cell['row'], wall_texture_image,
                                                              plain_wall_texture, small_window_wall_texture, large_window_wall_texture)
            paste_projected_wall_texture(preview_image, selected_wall_texture,
                point_values(building_width, current_row_index + 1, current_top_height),
                point_values(building_width, current_row_index, current_top_height),
                point_values(building_width, current_row_index + 1, current_bottom_height))
    if entrance_side in ISOMETRIC_VISIBLE_BUILDING_SIDES:
        if entrance_side == 'south':
            paste_projected_wall_texture(preview_image, door_texture_image,
                point_values(entrance_cell['column'], building_depth, ISOMETRIC_BUILDING_WALL_HEIGHT),
                point_values(entrance_cell['column'] + 1, building_depth, ISOMETRIC_BUILDING_WALL_HEIGHT),
                point_values(entrance_cell['column'], building_depth, 0))
        else:
            paste_projected_wall_texture(preview_image, door_texture_image,
                point_values(building_width, entrance_cell['row'] + 1, ISOMETRIC_BUILDING_WALL_HEIGHT),
                point_values(building_width, entrance_cell['row'], ISOMETRIC_BUILDING_WALL_HEIGHT),
                point_values(building_width, entrance_cell['row'] + 1, 0))
    for current_column_index in range(building_width):
        for current_row_index in range(building_depth):
            roof_center_point = point_values(current_column_index + .5, current_row_index + .5,
                                             wall_height + ISOMETRIC_BUILDING_ROOF_HEIGHT)
            preview_image.alpha_composite(roof_tile_image, (round(roof_center_point[0] - half_tile_width),
                                                             round(roof_center_point[1] - half_tile_height)))


def build_map_review(map_path=None, output_root=None):
    from tools.review.build_block_map_review import build_block_map_review
    if map_path is not None:
        raise ValueError('로컬 맵 사본 입력은 폐기되었습니다. 에셋 저장소의 등록 맵을 사용하세요.')
    selected_output_directory = output_root or WORKFLOW_ROOT / '.tmp/test/map-review' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    return build_block_map_review(selected_output_directory)


def run_map_review_build_command():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', type=Path)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()
    print(build_map_review(arguments.map, arguments.output))


if __name__ == '__main__':
    run_map_review_build_command()
