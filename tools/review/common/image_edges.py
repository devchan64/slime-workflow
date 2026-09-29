"""이미지 외부의 검정 프레임과 내부 텍스처 경계를 찾는 공용 라이브러리."""
from dataclasses import dataclass
from math import ceil
from statistics import median

from PIL import Image

BLACK_BRIGHTNESS_LIMIT = 48
# 이전 import 경로의 호환 상수. 판정은 최대 채널값이 아닌 명도를 사용한다.
BLACK_CHANNEL_LIMIT = BLACK_BRIGHTNESS_LIMIT
RGB_BRIGHTNESS_WEIGHTS = (299, 587, 114)
RGB_BRIGHTNESS_SCALE = 1000



BLACK_CHROMA_LIMIT = 16
WHITE_MARGIN_CHROMA_LIMIT = 16
BLACK_SATURATION_LIMIT = 0.05



EDGE_SAMPLE_FRACTION = 0.15



EDGE_SEARCH_FRACTION = 0.25



MINIMUM_FRAME_RUN = 3



MINIMUM_CONTENT_RUN = 3



TEXTURE_COLOR_DIFFERENCE = 12



TEXTURE_TRANSITION_RUN = 2



MINIMUM_VALID_FRACTION = 0.6



@dataclass(frozen=True)
class TileBorderTrace:
    """좌표는 원본 픽셀, 오른쪽·아래쪽은 배타적 경계다."""

    content_crop_bounds: tuple[int, int, int, int]
    edge_trace_samples: dict[str, tuple[int, ...]]



def is_black_border(pixel_color_value):
    """RGB가 비슷하고 명도와 HSV 채도가 낮은 픽셀을 검은 엣지로 판정한다."""
    pixel_channel_difference = max(pixel_color_value)-min(pixel_color_value)
    pixel_maximum_channel = max(pixel_color_value)
    pixel_saturation_value = pixel_channel_difference/pixel_maximum_channel if pixel_maximum_channel else 0
    pixel_brightness_total = sum(current_channel_value*current_channel_weight for current_channel_value, current_channel_weight in zip(pixel_color_value, RGB_BRIGHTNESS_WEIGHTS))
    return pixel_channel_difference <= BLACK_CHROMA_LIMIT and pixel_saturation_value <= BLACK_SATURATION_LIMIT and pixel_brightness_total <= BLACK_BRIGHTNESS_LIMIT*RGB_BRIGHTNESS_SCALE



def trace_black_border(source_image_value):
    """중앙 70%의 주사선에서 검정 연속 구간 뒤의 내용물 경계를 검출한다.

    흰 외부 여백은 건너뛴다. 각 변의 중앙값으로 돌출 풀잎·그림자 영향을
    줄이며, 충분한 주사선에서 경계를 검출하지 못하면 추측하지 않고 실패한다.
    """
    if source_image_value.mode not in ('RGB', 'RGBA'):
        raise ValueError('테두리 추적은 RGB/RGBA 이미지만 지원합니다.')
    if source_image_value.mode == 'RGBA' and source_image_value.getextrema()[3] != (255, 255):
        raise ValueError('투명 이미지의 검은 테두리는 추적할 수 없습니다.')
    source_rgb_image = source_image_value.convert('RGB')
    source_image_width, source_image_height = source_rgb_image.size
    if min(source_rgb_image.size) < 32:
        raise ValueError('테두리 추적에는 최소 32×32 이미지가 필요합니다.')
    edge_trace_samples = {}
    for edge_side_name in ('left', 'top', 'right', 'bottom'):
        horizontal_scan_enabled = edge_side_name in ('left', 'right')
        scan_axis_length = source_image_width if horizontal_scan_enabled else source_image_height
        cross_axis_length = source_image_height if horizontal_scan_enabled else source_image_width
        scan_start_offset = ceil(cross_axis_length*EDGE_SAMPLE_FRACTION)
        scan_end_offset = cross_axis_length-scan_start_offset
        scan_depth_limit = ceil(scan_axis_length*EDGE_SEARCH_FRACTION)
        detected_edge_values = []
        for cross_axis_offset in range(scan_start_offset, scan_end_offset):
            black_run_length = 0
            content_run_length = 0
            frame_found_flag = False
            for scan_depth_offset in range(scan_depth_limit):
                scan_axis_offset = scan_axis_length-1-scan_depth_offset if edge_side_name in ('right', 'bottom') else scan_depth_offset
                source_pixel_point = (scan_axis_offset, cross_axis_offset) if horizontal_scan_enabled else (cross_axis_offset, scan_axis_offset)
                if is_black_border(source_rgb_image.getpixel(source_pixel_point)):
                    black_run_length += 1
                    content_run_length = 0
                    if black_run_length >= MINIMUM_FRAME_RUN:
                        frame_found_flag = True
                else:
                    black_run_length = 0
                    if frame_found_flag:
                        content_run_length += 1
                        if content_run_length >= MINIMUM_CONTENT_RUN:
                            content_start_depth = scan_depth_offset-content_run_length+1
                            detected_edge_values.append(content_start_depth)
                            break
        if len(detected_edge_values) < (scan_end_offset-scan_start_offset)*MINIMUM_VALID_FRACTION:
            raise ValueError(f'검은 테두리 검출 근거 부족: {edge_side_name}')
        edge_trace_samples[edge_side_name] = tuple(detected_edge_values)
    content_crop_bounds = (
        round(median(edge_trace_samples['left'])),
        round(median(edge_trace_samples['top'])),
        source_image_width-round(median(edge_trace_samples['right'])),
        source_image_height-round(median(edge_trace_samples['bottom'])),
    )
    return TileBorderTrace(content_crop_bounds, edge_trace_samples)



@dataclass(frozen=True)
class TileTextureBoundary:
    """원본 좌표계의 텍스처·외부 검정·접촉 경계 마스크와 좌표."""

    texture_region_mask: Image.Image
    black_frame_mask: Image.Image
    texture_boundary_mask: Image.Image
    texture_boundary_points: tuple[tuple[int, int], ...]
    content_crop_bounds: tuple[int, int, int, int]
    side_transition_records: dict[str, list[tuple[tuple[int, int], tuple[int, int]]]]



def scan_border_transition(scan_pixel_values):
    """첫 검정 구간의 기준색과 작은 차이가 지속되는 지점을 찾는다."""
    black_run_length = 0
    texture_run_length = 0
    frame_start_offset = None
    frame_reference_color = None
    for scan_pixel_offset, pixel_color_value in enumerate(scan_pixel_values):
        if frame_start_offset is None:
            black_run_length = black_run_length+1 if is_black_border(pixel_color_value) else 0
            if black_run_length >= MINIMUM_FRAME_RUN:
                frame_start_offset = scan_pixel_offset-black_run_length+1
                reference_pixel_values = scan_pixel_values[frame_start_offset:scan_pixel_offset+1]
                frame_reference_color = tuple(median(reference_pixel_value[channel_axis_index] for reference_pixel_value in reference_pixel_values) for channel_axis_index in range(3))
            continue
        white_margin_match = min(pixel_color_value) >= 180 and max(pixel_color_value)-min(pixel_color_value) <= WHITE_MARGIN_CHROMA_LIMIT
        if white_margin_match:
            frame_start_offset = None
            frame_reference_color = None
            black_run_length = 0
            texture_run_length = 0
            continue
        # 검정 분류 안에 남아 있어도 기준색과 달라지면 텍스처 후보로 인정한다.
        color_difference_value = max(abs(pixel_color_value[channel_axis_index]-frame_reference_color[channel_axis_index]) for channel_axis_index in range(3))
        texture_candidate_match = not is_black_border(pixel_color_value) or color_difference_value >= TEXTURE_COLOR_DIFFERENCE
        texture_run_length = texture_run_length+1 if texture_candidate_match else 0
        if texture_run_length >= TEXTURE_TRANSITION_RUN:
            return frame_start_offset, scan_pixel_offset-texture_run_length+1
    return None



def detect_texture_boundary(source_image_value):
    """네 변에서 바깥→검정 프레임→텍스처 순으로 찾은 첫 경계를 반환한다.

    내부에서 외부로 연결 영역을 확장하지 않는다. 각 주사선은 첫 유효
    전이에서 멈추므로 텍스처 내부의 검정 그림자는 계속 추적하지 않는다.
    """
    trace_black_border(source_image_value)
    source_rgb_image = source_image_value.convert('RGB')
    source_image_width, source_image_height = source_rgb_image.size
    black_frame_mask = Image.new('L', source_image_value.size, 0)
    texture_boundary_mask = Image.new('L', source_image_value.size, 0)
    texture_region_mask = Image.new('L', source_image_value.size, 0)
    side_boundary_records = {}
    side_transition_records = {}
    for edge_side_name in ('left', 'right', 'top', 'bottom'):
        horizontal_scan_enabled = edge_side_name in ('left', 'right')
        scan_axis_length = source_image_width if horizontal_scan_enabled else source_image_height
        cross_axis_length = source_image_height if horizontal_scan_enabled else source_image_width
        scan_depth_limit = scan_axis_length
        side_boundary_records[edge_side_name] = {}
        side_transition_records[edge_side_name] = []
        for cross_axis_offset in range(cross_axis_length):
            scan_pixel_points = [
                ((scan_axis_length-1-scan_depth_offset if edge_side_name in ('right', 'bottom') else scan_depth_offset), cross_axis_offset)
                if horizontal_scan_enabled else
                (cross_axis_offset, (scan_axis_length-1-scan_depth_offset if edge_side_name in ('right', 'bottom') else scan_depth_offset))
                for scan_depth_offset in range(scan_depth_limit)
            ]
            transition_offset_values = scan_border_transition([source_rgb_image.getpixel(pixel_point_value) for pixel_point_value in scan_pixel_points])
            if transition_offset_values is None:
                continue
            frame_start_offset, texture_start_offset = transition_offset_values
            boundary_pixel_point = scan_pixel_points[texture_start_offset]
            side_boundary_records[edge_side_name][cross_axis_offset] = boundary_pixel_point[0 if horizontal_scan_enabled else 1]
            side_transition_records[edge_side_name].append((scan_pixel_points[frame_start_offset], boundary_pixel_point))
            for scan_pixel_offset in range(frame_start_offset, texture_start_offset):
                current_pixel_point = scan_pixel_points[scan_pixel_offset]
                if is_black_border(source_rgb_image.getpixel(current_pixel_point)):
                    black_frame_mask.putpixel(current_pixel_point, 255)
            texture_boundary_mask.putpixel(boundary_pixel_point, 255)
        if not side_boundary_records[edge_side_name]:
            raise ValueError(f'검정에서 텍스처로 바뀌는 경계가 없습니다: {edge_side_name}')
    # 네 방향에서 검출된 첫 경계의 내부만 남긴다. 경계를 못 찾은 선은 제외한다.
    for vertical_pixel_offset in range(source_image_height):
        content_left_bound = side_boundary_records['left'].get(vertical_pixel_offset)
        content_right_bound = side_boundary_records['right'].get(vertical_pixel_offset)
        if content_left_bound is None or content_right_bound is None:
            continue
        for horizontal_pixel_offset in range(content_left_bound, content_right_bound+1):
            content_top_bound = side_boundary_records['top'].get(horizontal_pixel_offset)
            content_bottom_bound = side_boundary_records['bottom'].get(horizontal_pixel_offset)
            if content_top_bound is not None and content_bottom_bound is not None and content_top_bound <= vertical_pixel_offset <= content_bottom_bound:
                texture_region_mask.putpixel((horizontal_pixel_offset, vertical_pixel_offset), 255)
    content_crop_bounds = texture_region_mask.getbbox()
    if content_crop_bounds is None:
        raise ValueError('네 방향 경계 안쪽에 유효한 텍스처 영역이 없습니다.')
    texture_boundary_points = tuple((horizontal_pixel_offset, vertical_pixel_offset) for vertical_pixel_offset in range(source_image_height) for horizontal_pixel_offset in range(source_image_width) if texture_boundary_mask.getpixel((horizontal_pixel_offset, vertical_pixel_offset)))
    return TileTextureBoundary(texture_region_mask, black_frame_mask, texture_boundary_mask, texture_boundary_points, content_crop_bounds, side_transition_records)



def render_texture_boundary(source_image_value, boundary_trace_result):
    """원본을 유지하고 검출한 접촉 경계만 빨간색으로 표시한다."""
    if boundary_trace_result.texture_boundary_mask.size != source_image_value.size:
        raise ValueError('경계 마스크와 원본 이미지의 크기가 다릅니다.')
    boundary_overlay_image = source_image_value.convert('RGB')
    boundary_overlay_image.paste((255, 40, 40), mask=boundary_trace_result.texture_boundary_mask)
    return boundary_overlay_image
