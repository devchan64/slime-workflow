"""프레임 외곽에 연결된 밝은 배경만 제거하고 내부의 흰 의복은 보존한다."""
from collections import deque
from PIL import Image

BACKGROUND_MINIMUM_CHANNEL = 235
BACKGROUND_MAXIMUM_CHROMA = 24


def extract_connected_background(current_source_image):
    current_output_image = current_source_image.convert('RGBA')
    current_image_width, current_image_height = current_output_image.size
    current_pixel_values = list(current_output_image.getdata())
    current_background_mask = bytearray(len(current_pixel_values))
    current_pending_pixels = deque()

    def enqueue_background_pixel(current_pixel_index):
        if current_background_mask[current_pixel_index]:
            return
        current_pixel_color = current_pixel_values[current_pixel_index]
        if current_pixel_color[3] == 0 or (min(current_pixel_color[:3]) >= BACKGROUND_MINIMUM_CHANNEL and max(current_pixel_color[:3])-min(current_pixel_color[:3]) <= BACKGROUND_MAXIMUM_CHROMA):
            current_background_mask[current_pixel_index] = 1
            current_pending_pixels.append(current_pixel_index)

    for current_column_index in range(current_image_width):
        enqueue_background_pixel(current_column_index)
        enqueue_background_pixel((current_image_height-1)*current_image_width+current_column_index)
    for current_row_index in range(current_image_height):
        enqueue_background_pixel(current_row_index*current_image_width)
        enqueue_background_pixel(current_row_index*current_image_width+current_image_width-1)
    while current_pending_pixels:
        current_pixel_index = current_pending_pixels.popleft()
        current_column_index = current_pixel_index % current_image_width
        if current_column_index:
            enqueue_background_pixel(current_pixel_index-1)
        if current_column_index+1 < current_image_width:
            enqueue_background_pixel(current_pixel_index+1)
        if current_pixel_index >= current_image_width:
            enqueue_background_pixel(current_pixel_index-current_image_width)
        if current_pixel_index+current_image_width < len(current_pixel_values):
            enqueue_background_pixel(current_pixel_index+current_image_width)
    current_output_image.putdata([(*current_pixel_color[:3], 0 if current_background_mask[current_pixel_index] else current_pixel_color[3]) for current_pixel_index,current_pixel_color in enumerate(current_pixel_values)])
    return current_output_image
