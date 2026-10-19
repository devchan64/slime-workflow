"""중심 앵커 장식의 접지 영역을 보수적으로 검사한다."""
from math import ceil, isfinite


def calculate_centered_footprint_cells(current_cell_position, current_footprint_columns, current_footprint_rows):
    """짝수 폭은 중심 양쪽의 반 칸까지 걸치므로 접촉 셀을 모두 반환한다."""
    if any(type(current_dimension_value) is not int or current_dimension_value < 1 for current_dimension_value in (current_footprint_columns, current_footprint_rows)):
        raise ValueError('장식 점유 폭은 양의 정수여야 합니다.')
    current_column_radius = ceil((current_footprint_columns - 1) / 2)
    current_row_radius = ceil((current_footprint_rows - 1) / 2)
    return {(current_cell_position[0] + current_column_offset, current_cell_position[1] + current_row_offset)
            for current_column_offset in range(-current_column_radius, current_column_radius + 1)
            for current_row_offset in range(-current_row_radius, current_row_radius + 1)}


def validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, current_reserved_cells):
    """맵 경계·예약 영역·접지 셀 간 단차를 검사하고 거절 사유를 반환한다."""
    if not current_ground_cells or not current_elevation_rows or not current_elevation_rows[0]:
        raise ValueError('접지 셀과 고도 행이 필요합니다.')
    current_column_count = len(current_elevation_rows[0])
    if any(len(current_elevation_row) != current_column_count for current_elevation_row in current_elevation_rows):
        raise ValueError('고도 행의 너비가 일치해야 합니다.')
    if any(not (0 <= current_column_index < current_column_count and 0 <= current_row_index < len(current_elevation_rows)) for current_column_index, current_row_index in current_ground_cells):
        return '맵 경계 침범'
    if current_ground_cells & current_reserved_cells:
        return '예약 영역 중첩'
    if len({current_elevation_rows[current_row_index][current_column_index] for current_column_index, current_row_index in current_ground_cells}) != 1:
        return '접지 영역 고도 불일치'
    return None


def validate_scenery_object_collisions(current_object_records, current_property_catalog, current_elevation_rows):
    """장식 접지 충돌을 모아 예외로 반환한다. 화면 위쪽 실루엣 겹침은 제외한다."""
    current_cell_owners = {}
    current_error_messages = []
    for current_object_record in current_object_records:
        if current_object_record['kind'] not in ('decoration', 'billboard'):
            continue
        current_object_position = current_object_record['position']
        current_property_values = current_property_catalog[current_object_record['textureKey']]
        current_ground_cells = calculate_centered_footprint_cells(
            (current_object_position['column'], current_object_position['row']),
            current_property_values['groundFootprintColumns'], current_property_values['groundFootprintRows'])
        current_failure_reason = validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, set())
        if current_failure_reason:
            current_error_messages.append(f"{current_object_record['id']}: {current_failure_reason} · {current_object_position}")
        for current_ground_cell in sorted(current_ground_cells):
            for current_previous_owner in current_cell_owners.get(current_ground_cell, []):
                current_error_messages.append(f"{current_previous_owner} ↔ {current_object_record['id']}: 점유 영역 충돌 · {current_ground_cell}")
            current_cell_owners.setdefault(current_ground_cell, []).append(current_object_record['id'])
    if current_error_messages:
        raise ValueError('장식 배치 검수 실패:\n' + '\n'.join(current_error_messages))


SCENERY_CONTACT_BAND_RATIO = 0.25
SCENERY_ALPHA_VISIBLE_THRESHOLD = 16
SCENERY_PIXEL_ROUNDING_TOLERANCE = 1.0


def validate_scenery_image_footprint(current_texture_key, current_source_image, current_property_values, current_tile_width):
    """불투명 영역 하단 25%의 가로 돌출을 보수적으로 검사한다.

    접지 마스크가 없는 원본의 자동 선별 검사이며 정확한 3D 접촉면 판정은 아니다.
    상단 수관은 제외하고 앵커 기준 좌우 허용 폭을 각각 검사한다.
    """
    from math import isfinite
    current_display_height = current_property_values['displayHeight']
    current_anchor_offset = current_property_values['anchorX']
    if any(not isinstance(current_numeric_value, (int, float)) or isinstance(current_numeric_value, bool) or not isfinite(current_numeric_value) for current_numeric_value in (current_display_height, current_anchor_offset, current_tile_width)) or current_display_height <= 0 or current_tile_width <= 0 or not 0 <= current_anchor_offset <= 1:
        raise ValueError('이미지 접지 검사 크기·앵커 값이 잘못되었습니다.')
    current_alpha_image = current_source_image.convert('RGBA').getchannel('A').point(lambda current_alpha_value: 255 if current_alpha_value >= SCENERY_ALPHA_VISIBLE_THRESHOLD else 0)
    current_alpha_bounds = current_alpha_image.getbbox()
    if current_alpha_bounds is None:
        raise ValueError(f'{current_texture_key}: 불투명 영역이 없는 이미지')
    current_contact_start = current_alpha_bounds[3] - ceil((current_alpha_bounds[3] - current_alpha_bounds[1]) * SCENERY_CONTACT_BAND_RATIO)
    current_contact_bounds = current_alpha_image.crop((0, current_contact_start, current_source_image.width, current_alpha_bounds[3])).getbbox()
    current_display_scale = current_display_height / current_source_image.height
    current_render_left = (current_contact_bounds[0] - current_source_image.width * current_anchor_offset) * current_display_scale
    current_render_right = (current_contact_bounds[2] - current_source_image.width * current_anchor_offset) * current_display_scale
    current_allowed_half_width = (current_property_values['groundFootprintColumns'] + current_property_values['groundFootprintRows']) * current_tile_width / 4
    if current_render_left < -current_allowed_half_width - SCENERY_PIXEL_ROUNDING_TOLERANCE or current_render_right > current_allowed_half_width + SCENERY_PIXEL_ROUNDING_TOLERANCE:
        raise ValueError(f'{current_texture_key}: 이미지 접지 폭 초과 · 하단 {SCENERY_CONTACT_BAND_RATIO:.0%} 실측 {current_render_right-current_render_left:.1f}px · 좌우 [{current_render_left:.1f}, {current_render_right:.1f}]px · 허용 ±{current_allowed_half_width:.1f}px · 표시 높이 {current_display_height}px')


def validate_registered_scenery_images(current_object_records, current_property_catalog, current_tile_width, current_tile_height, current_elevation_rows, current_billboard_scale=1):
    """원본 속성은 보존하고 렌더 배율을 반영한 이미지 접지를 검사한다."""
    if not isinstance(current_billboard_scale, (int, float)) or isinstance(current_billboard_scale, bool) or not isfinite(current_billboard_scale) or current_billboard_scale <= 0:
        raise ValueError("빌보드 렌더 배율은 양수여야 합니다.")
    current_property_catalog = {current_texture_key: {**current_property_values, "displayHeight": current_property_values["displayHeight"] * current_billboard_scale} for current_texture_key, current_property_values in current_property_catalog.items()}
    from pathlib import Path
    from PIL import Image
    from tools.review.common.map_tile_assets import load_registered_tiles, resolve_registered_sprite
    current_source_catalog = load_registered_tiles()
    current_texture_paths = {}
    for current_asset_path, current_asset_record in current_source_catalog[1].items():
        if current_asset_record['managementId'].startswith('image.scenery.'):
            current_texture_name = Path(current_asset_path).stem
            if current_texture_name in current_texture_paths:
                raise ValueError('지형지물 텍스처 ID 중복: ' + current_texture_name)
            current_texture_paths[current_texture_name] = current_asset_path
    current_error_messages = []
    for current_object_record in current_object_records:
        if current_object_record['kind'] not in ('decoration', 'billboard'):
            continue
        current_texture_key = current_object_record['textureKey']
        current_frame_size = current_object_record.get('frameSize') if current_object_record['kind'] == 'billboard' else None
        current_image_path, _ = resolve_registered_sprite(current_texture_paths[current_texture_key], current_source_catalog)
        with Image.open(current_image_path) as current_source_image:
            if current_object_record['kind'] == 'billboard':
                if type(current_frame_size) is not int or current_frame_size <= 0 or current_source_image.width % current_frame_size or current_source_image.height % current_frame_size:
                    raise ValueError(f'{current_texture_key}: 빌보드 프레임 크기 오류')
                current_frame_images = [current_source_image.crop((current_column_offset, current_row_offset, current_column_offset+current_frame_size, current_row_offset+current_frame_size)) for current_row_offset in range(0, current_source_image.height, current_frame_size) for current_column_offset in range(0, current_source_image.width, current_frame_size)]
            else:
                current_frame_images = [current_source_image]
            for current_frame_index, current_frame_image in enumerate(current_frame_images):
                try:
                    validate_scenery_image_footprint(current_texture_key, current_frame_image, current_property_catalog[current_texture_key], current_tile_width)
                except ValueError as current_validation_error:
                    current_error_messages.append(f'{current_validation_error} · 프레임 {current_frame_index}')
                try:
                    validate_image_contact_elevations(current_object_record, current_frame_image, current_property_catalog[current_texture_key], current_elevation_rows, current_tile_width, current_tile_height)
                except ValueError as current_validation_error:
                    current_error_messages.append(f'{current_validation_error} · 프레임 {current_frame_index}')
    if current_error_messages:
        raise ValueError('장식 이미지 점유 검수 실패:\n' + '\n'.join(current_error_messages))


def validate_image_contact_elevations(current_object_record, current_source_image, current_property_values, current_elevation_rows, current_tile_width, current_tile_height):
    """이미지 하단 접지 후보를 월드 셀에 역투영해 단차 침범을 거절한다."""
    from math import floor
    current_alpha_image = current_source_image.convert('RGBA').getchannel('A').point(lambda current_alpha_value: 255 if current_alpha_value >= SCENERY_ALPHA_VISIBLE_THRESHOLD else 0)
    current_alpha_bounds = current_alpha_image.getbbox()
    if current_alpha_bounds is None:
        raise ValueError(f"{current_object_record['id']}: 불투명 영역이 없는 이미지")
    current_contact_start = current_alpha_bounds[3] - ceil((current_alpha_bounds[3] - current_alpha_bounds[1]) * SCENERY_CONTACT_BAND_RATIO)
    current_display_scale = current_property_values['displayHeight'] / current_source_image.height
    current_anchor_offsets = {'center': 0, 'front': 0.25, 'back': -0.25}
    current_tile_anchor = current_object_record.get('tileAnchor', 'center')
    if current_tile_anchor not in current_anchor_offsets:
        raise ValueError('지원하지 않는 접지 앵커: ' + current_tile_anchor)
    current_object_column = current_object_record['position']['column']
    current_object_row = current_object_record['position']['row']
    current_ground_cells = {(current_object_column, current_object_row)}
    for current_pixel_row in range(current_contact_start, current_alpha_bounds[3]):
        for current_pixel_column in range(current_alpha_bounds[0], current_alpha_bounds[2]):
            if not current_alpha_image.getpixel((current_pixel_column, current_pixel_row)):
                continue
            current_screen_offset_x = (current_pixel_column + 0.5 - current_source_image.width * current_property_values['anchorX']) * current_display_scale
            current_screen_offset_y = (current_pixel_row + 0.5 - current_source_image.height * current_property_values['anchorY']) * current_display_scale
            current_column_offset = current_screen_offset_x / current_tile_width + current_screen_offset_y / current_tile_height
            current_row_offset = current_screen_offset_y / current_tile_height - current_screen_offset_x / current_tile_width
            current_ground_cells.add((floor(current_object_column + current_anchor_offsets[current_tile_anchor] + current_column_offset + 0.5), floor(current_object_row + current_anchor_offsets[current_tile_anchor] + current_row_offset + 0.5)))
    current_failure_reason = validate_scenery_ground_placement(current_ground_cells, current_elevation_rows, set())
    if current_failure_reason:
        current_height_details = [(current_column_index, current_row_index, current_elevation_rows[current_row_index][current_column_index] if 0 <= current_row_index < len(current_elevation_rows) and 0 <= current_column_index < len(current_elevation_rows[0]) else '맵 밖') for current_column_index, current_row_index in sorted(current_ground_cells)]
        raise ValueError(f"{current_object_record['id']} / {current_object_record['textureKey']}: 실제 이미지 {current_failure_reason} · 셀(열, 행, 높이) {current_height_details}")
    return current_ground_cells
