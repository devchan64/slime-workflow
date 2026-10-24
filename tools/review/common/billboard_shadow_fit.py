"""투명 여백을 제외한 이미지 표시 폭에 맞춘 그림자 크기 제안."""
import math
from PIL import Image

SHADOW_ALPHA_THRESHOLD = 32
SHADOW_VISIBLE_WIDTH_RATIO = 0.95
SHADOW_TRANSPARENCY_GAIN = 0.5
SHADOW_MAXIMUM_WIDTH_BOOST = 0.25
SHADOW_RENDERER_CORNER_RATIO = 0.35
SHADOW_REFERENCE_TILE_WIDTH = 160


def calculate_horizontal_shadow_ratio(current_alpha_image):
    """외곽 여백을 제외한 가로 열별 점유율로 성긴 외형의 폭을 보강한다."""
    current_binary_mask=current_alpha_image.point(lambda current_alpha_value:255 if current_alpha_value>SHADOW_ALPHA_THRESHOLD else 0)
    current_visible_bounds=current_binary_mask.getbbox()
    if current_visible_bounds is None:raise ValueError('불투명한 이미지 영역이 없습니다.')
    current_cropped_mask=current_binary_mask.crop(current_visible_bounds)
    current_column_counts=[current_cropped_mask.crop((current_column_index,0,current_column_index+1,current_cropped_mask.height)).histogram()[255] for current_column_index in range(current_cropped_mask.width)]
    current_opaque_count=sum(current_column_counts)
    current_transparent_ratio=1-current_opaque_count/(current_cropped_mask.width*current_cropped_mask.height)
    # 같은 투명 비율이라도 소수 열에 몰린 외형보다 넓게 퍼진 외형을 보강한다.
    current_horizontal_spread=current_opaque_count/(max(current_column_counts)*current_cropped_mask.width)
    current_width_boost=min(SHADOW_MAXIMUM_WIDTH_BOOST,current_transparent_ratio*current_horizontal_spread*SHADOW_TRANSPARENCY_GAIN)
    return SHADOW_VISIBLE_WIDTH_RATIO+current_width_boost


def calculate_image_shadow_size(current_image_source, current_display_height, current_column_count=1, current_row_count=1):
    """가로 알파 분포에 맞춰 외곽 폭을 보정하며 점유 타일의 열·행 비율을 유지한다."""
    if any(not isinstance(current_value, (int, float)) or isinstance(current_value, bool) or not math.isfinite(current_value) or current_value <= 0 for current_value in (current_display_height,current_column_count,current_row_count)):
        raise ValueError('표시 높이와 점유 크기는 양수여야 합니다.')
    with Image.open(current_image_source) as current_source_image:
        if current_source_image.mode != 'RGBA':raise ValueError('RGBA 원본이 필요합니다.')
        current_visible_bounds=current_source_image.getchannel('A').point(lambda current_alpha_value:255 if current_alpha_value>SHADOW_ALPHA_THRESHOLD else 0).getbbox()
        if current_visible_bounds is None:raise ValueError('불투명한 이미지 영역이 없습니다.')
        current_target_ratio=calculate_horizontal_shadow_ratio(current_source_image.getchannel('A'))
        current_visible_width=(current_visible_bounds[2]-current_visible_bounds[0])*current_display_height/current_source_image.height
    # 둥근 모서리의 투영 폭 감소를 실제 렌더러와 동일하게 보정한다.
    current_corner_radius=min(current_column_count,current_row_count)/2*SHADOW_RENDERER_CORNER_RATIO
    current_projected_width=SHADOW_REFERENCE_TILE_WIDTH*((current_column_count+current_row_count)/2-current_corner_radius*(2-math.sqrt(2)))
    current_scale_ratio=current_visible_width*current_target_ratio/current_projected_width
    return tuple(round(max(.1,min(4,current_dimension_value*current_scale_ratio)),2) for current_dimension_value in (current_column_count,current_row_count))
