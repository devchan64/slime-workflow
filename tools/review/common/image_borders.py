"""검출 경계를 기준으로 픽셀·비율 보더를 남겨 크롭하는 공용 라이브러리."""
from math import ceil

from PIL import Image

from tools.review.common.image_edges import detect_texture_boundary, trace_black_border

def crop_traced_tile(source_image_value, *, output_tile_size=256, retained_edge_pixels=2):
    """최종 출력 기준의 테두리 두께를 원본 좌표로 환산한다.

    불규칙한 테두리의 두께는 중앙값 기준이며 모든 픽셀의 두께를 보장하지 않는다.
    원본을 변형하거나 검은 선을 덧그리지 않는다.
    """
    if type(output_tile_size) is not int or type(retained_edge_pixels) is not int or retained_edge_pixels < 0 or output_tile_size <= 2*retained_edge_pixels:
        raise ValueError('출력 크기와 남길 테두리 픽셀 수가 올바르지 않습니다.')
    border_trace_result = trace_black_border(source_image_value)
    content_left_bound, content_top_bound, content_right_bound, content_bottom_bound = border_trace_result.content_crop_bounds
    source_margin_width = (content_right_bound-content_left_bound)*retained_edge_pixels/(output_tile_size-2*retained_edge_pixels)
    source_margin_height = (content_bottom_bound-content_top_bound)*retained_edge_pixels/(output_tile_size-2*retained_edge_pixels)
    source_crop_bounds = (content_left_bound-source_margin_width, content_top_bound-source_margin_height, content_right_bound+source_margin_width, content_bottom_bound+source_margin_height)
    if source_crop_bounds[0] < 0 or source_crop_bounds[1] < 0 or source_crop_bounds[2] > source_image_value.width or source_crop_bounds[3] > source_image_value.height:
        raise ValueError('요청한 테두리 두께를 남길 원본 여유가 없습니다.')
    cropped_tile_image = source_image_value.resize((output_tile_size, output_tile_size), Image.Resampling.LANCZOS, box=source_crop_bounds)
    return cropped_tile_image, border_trace_result, source_crop_bounds



def crop_border_contour(source_image_value, *, output_tile_size=256):
    """공용 경계 검출 결과로 바깥 영역을 투명 처리한 0px 크롭."""
    if type(output_tile_size) is not int or output_tile_size < 1:
        raise ValueError('출력 크기는 양의 정수여야 합니다.')
    boundary_trace_result = detect_texture_boundary(source_image_value)
    output_rgba_image = source_image_value.convert('RGBA')
    output_rgba_image.putalpha(boundary_trace_result.texture_region_mask)
    return output_rgba_image.crop(boundary_trace_result.content_crop_bounds).resize((output_tile_size, output_tile_size), Image.Resampling.LANCZOS), boundary_trace_result.content_crop_bounds



def crop_inner_border(source_image_value, *, retained_border_ratio=0.01):
    """각 변에서 가장 안쪽 경계로 직사각형을 정하고 비율 보더를 남긴다.

    비율은 리사이즈 전 검출 텍스처 폭·높이 기준이며 각 축별로 올림한다.
    결과 검수 전에는 크기를 변경하거나 정식 에셋을 덮어쓰지 않는다.
    """
    if isinstance(retained_border_ratio, bool) or not isinstance(retained_border_ratio, (int, float)) or not 0 <= retained_border_ratio <= 1:
        raise ValueError('보더 비율은 0 이상 1 이하의 유한 수여야 합니다.')
    boundary_trace_result = detect_texture_boundary(source_image_value)
    # 모서리 바깥의 주사선이 반대편 프레임까지 통과하는 경우는 제외한다.
    representative_inner_bounds = trace_black_border(source_image_value).content_crop_bounds
    valid_side_boundaries = {}
    for edge_side_name in ('left', 'right', 'top', 'bottom'):
        edge_axis_index = 0 if edge_side_name in ('left', 'right') else 1
        cross_axis_index = 1-edge_axis_index
        valid_side_boundaries[edge_side_name] = [texture_start_point[edge_axis_index] for _, texture_start_point in boundary_trace_result.side_transition_records[edge_side_name] if representative_inner_bounds[cross_axis_index] <= texture_start_point[cross_axis_index] < representative_inner_bounds[cross_axis_index+2]]
        if not valid_side_boundaries[edge_side_name]:
            raise ValueError(f'변 내부의 유효한 경계가 없습니다: {edge_side_name}')
    content_left_bound = max(valid_side_boundaries['left'])
    content_right_bound = min(valid_side_boundaries['right'])+1
    content_top_bound = max(valid_side_boundaries['top'])
    content_bottom_bound = min(valid_side_boundaries['bottom'])+1
    texture_region_width = content_right_bound-content_left_bound
    texture_region_height = content_bottom_bound-content_top_bound
    if texture_region_width <= 0 or texture_region_height <= 0:
        raise ValueError('중심에 가까운 경계들이 교차하여 유효한 텍스처 사각형이 없습니다.')
    horizontal_border_pixels = ceil(texture_region_width*retained_border_ratio)
    vertical_border_pixels = ceil(texture_region_height*retained_border_ratio)
    source_crop_bounds = (content_left_bound-horizontal_border_pixels, content_top_bound-vertical_border_pixels, content_right_bound+horizontal_border_pixels, content_bottom_bound+vertical_border_pixels)
    if source_crop_bounds[0] < 0 or source_crop_bounds[1] < 0 or source_crop_bounds[2] > source_image_value.width or source_crop_bounds[3] > source_image_value.height:
        raise ValueError('보더를 포함한 크롭 범위가 원본을 벗어납니다.')
    crop_measurement_record = {'inner_bounds':[content_left_bound,content_top_bound,content_right_bound,content_bottom_bound],'texture_size':[texture_region_width,texture_region_height],'border_ratio':retained_border_ratio,'border_pixels':[horizontal_border_pixels,vertical_border_pixels],'crop_box':list(source_crop_bounds),'coordinate_policy':'오른쪽·아래쪽 배타적 좌표, 보더는 각 변에 적용'}
    return source_image_value.crop(source_crop_bounds), crop_measurement_record
