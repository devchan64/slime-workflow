"""투명 여백을 제외한 이미지 표시 폭에 맞춘 그림자 크기 제안."""
import math
from PIL import Image

SHADOW_ALPHA_THRESHOLD = 32
SHADOW_VISIBLE_WIDTH_RATIO = 0.85
SHADOW_REFERENCE_TILE_WIDTH = 160


def calculate_image_shadow_size(current_image_source, current_display_height, current_column_count=1, current_row_count=1):
    """외형 폭의 85%로 제안하며 점유 타일의 열·행 비율을 유지한다."""
    if any(not isinstance(current_value, (int, float)) or isinstance(current_value, bool) or not math.isfinite(current_value) or current_value <= 0 for current_value in (current_display_height,current_column_count,current_row_count)):
        raise ValueError('표시 높이와 점유 크기는 양수여야 합니다.')
    with Image.open(current_image_source) as current_source_image:
        if current_source_image.mode != 'RGBA':raise ValueError('RGBA 원본이 필요합니다.')
        current_visible_bounds=current_source_image.getchannel('A').point(lambda current_alpha_value:255 if current_alpha_value>SHADOW_ALPHA_THRESHOLD else 0).getbbox()
        if current_visible_bounds is None:raise ValueError('불투명한 이미지 영역이 없습니다.')
        current_visible_width=(current_visible_bounds[2]-current_visible_bounds[0])*current_display_height/current_source_image.height
    current_scale_ratio=current_visible_width*SHADOW_VISIBLE_WIDTH_RATIO/(SHADOW_REFERENCE_TILE_WIDTH*(current_column_count+current_row_count)/2)
    return tuple(round(max(.1,min(4,current_dimension_value*current_scale_ratio)),2) for current_dimension_value in (current_column_count,current_row_count))
