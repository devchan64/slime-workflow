"""반복 타일 경계 보간 및 3×3 미리보기."""
import numpy as np
from PIL import Image


def blend_opposite_tile_edges(current_image_value):
    current_pixel_array = np.asarray(current_image_value.convert('RGB'),dtype=np.float32).copy()
    current_height_value,current_width_value = current_pixel_array.shape[:2]
    current_band_width = max(2,min(current_width_value,current_height_value)//16)
    for current_distance_value in range(current_band_width):
        current_weight_value = 0.5*(1-current_distance_value/(current_band_width-1))
        current_left_values=current_pixel_array[:,current_distance_value].copy()
        current_right_values=current_pixel_array[:,-1-current_distance_value].copy()
        current_pixel_array[:,current_distance_value]=current_left_values*(1-current_weight_value)+current_right_values*current_weight_value
        current_pixel_array[:,-1-current_distance_value]=current_right_values*(1-current_weight_value)+current_left_values*current_weight_value
    for current_distance_value in range(current_band_width):
        current_weight_value = 0.5*(1-current_distance_value/(current_band_width-1))
        current_top_values=current_pixel_array[current_distance_value].copy()
        current_bottom_values=current_pixel_array[-1-current_distance_value].copy()
        current_pixel_array[current_distance_value]=current_top_values*(1-current_weight_value)+current_bottom_values*current_weight_value
        current_pixel_array[-1-current_distance_value]=current_bottom_values*(1-current_weight_value)+current_top_values*current_weight_value
    return Image.fromarray(np.clip(np.rint(current_pixel_array),0,255).astype('uint8'))


def build_repeated_tile_preview(current_image_value):
    current_preview_image=Image.new('RGB',(current_image_value.width*3,current_image_value.height*3))
    for current_row_number in range(3):
        for current_column_number in range(3):
            current_preview_image.paste(current_image_value,(current_column_number*current_image_value.width,current_row_number*current_image_value.height))
    return current_preview_image
