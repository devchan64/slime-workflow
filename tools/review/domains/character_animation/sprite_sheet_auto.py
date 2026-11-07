"""흰색·투명 배경 시트의 분리된 캐릭터를 크롭 범위로 검출한다."""
import base64
from io import BytesIO
import numpy as np
from PIL import Image
from .sprite_sheet_editor import SPRITE_SHEET_IMAGE_LIMIT, SPRITE_SHEET_PIXEL_LIMIT

AUTO_SHEET_DEFAULT_PADDING = 30
AUTO_SHEET_WHITE_THRESHOLD = 240
AUTO_SHEET_MINIMUM_GAP = 12


def collect_projection_intervals(current_projection_values):
    current_active_indices = np.flatnonzero(current_projection_values)
    if not len(current_active_indices):
        return []
    current_split_indices = np.flatnonzero(np.diff(current_active_indices) > AUTO_SHEET_MINIMUM_GAP) + 1
    return [(int(current_index_group[0]), int(current_index_group[-1])+1) for current_index_group in np.split(current_active_indices, current_split_indices)]


def execute_sprite_sheet_automatic(current_payload_record):
    if not isinstance(current_payload_record, dict) or set(current_payload_record) - {'image','padding'} or 'image' not in current_payload_record:
        raise ValueError('자동 시트 입력은 image와 padding만 허용합니다.')
    current_padding_pixels = current_payload_record.get('padding', AUTO_SHEET_DEFAULT_PADDING)
    if type(current_padding_pixels) is not int or not 0 <= current_padding_pixels <= 500:
        raise ValueError('여백은 0~500px 정수여야 합니다.')
    current_source_bytes = base64.b64decode(current_payload_record['image'], validate=True)
    if not 0 < len(current_source_bytes) <= SPRITE_SHEET_IMAGE_LIMIT:
        raise ValueError('원본 PNG는 8MB 이하여야 합니다.')
    with Image.open(BytesIO(current_source_bytes)) as current_source_image:
        if current_source_image.format != 'PNG' or current_source_image.width*current_source_image.height > SPRITE_SHEET_PIXEL_LIMIT or getattr(current_source_image,'n_frames',1)!=1:
            raise ValueError('1600만 픽셀 이하 단일 PNG가 필요합니다.')
        current_rgba_pixels = np.array(current_source_image.convert('RGBA'))
    current_foreground_mask = (current_rgba_pixels[:,:,3] > 16) & (current_rgba_pixels[:,:,:3].min(axis=2) < AUTO_SHEET_WHITE_THRESHOLD)
    current_black_mask = (current_rgba_pixels[:,:,:3].max(axis=2) < 20) & (current_rgba_pixels[:,:,3] > 16)
    current_foreground_mask[current_black_mask.mean(axis=1) > .95,:] = False
    current_foreground_mask[:,current_black_mask.mean(axis=0) > .95] = False
    current_row_intervals = collect_projection_intervals(current_foreground_mask.any(axis=1))
    current_detected_bounds = []
    current_column_counts = []
    for current_top_pixels,current_bottom_pixels in current_row_intervals:
        current_column_intervals = collect_projection_intervals(current_foreground_mask[current_top_pixels:current_bottom_pixels].any(axis=0))
        current_column_counts.append(len(current_column_intervals))
        for current_left_pixels,current_right_pixels in current_column_intervals:
            current_local_mask = current_foreground_mask[current_top_pixels:current_bottom_pixels,current_left_pixels:current_right_pixels]
            current_local_rows = np.flatnonzero(current_local_mask.any(axis=1))
            if current_local_mask.sum() < 64:
                raise ValueError('작은 독립 영역이 발견되었습니다. 배경 잡음 또는 분리된 신체 부위를 확인하세요.')
            current_detected_bounds.append((current_left_pixels,current_top_pixels+int(current_local_rows[0]),current_right_pixels,current_top_pixels+int(current_local_rows[-1])+1))
    if not current_detected_bounds or len(current_detected_bounds)>128 or len(set(current_column_counts))!=1:
        raise ValueError('행별 캐릭터 수가 다르거나 영역을 검출하지 못했습니다. 흰색·투명 배경과 분리된 배치를 확인하세요.')
    current_frame_records = []
    current_source_bounds = []
    for current_left_pixels,current_top_pixels,current_right_pixels,current_bottom_pixels in current_detected_bounds:
        current_frame_width = current_right_pixels-current_left_pixels
        current_frame_height = current_bottom_pixels-current_top_pixels
        current_source_bounds.append([current_left_pixels,current_top_pixels,current_frame_width,current_frame_height])
        current_frame_records.append(dict(x=current_left_pixels-current_padding_pixels,y=current_top_pixels-current_padding_pixels,width=current_frame_width+2*current_padding_pixels,height=current_frame_height+2*current_padding_pixels,anchorX=current_frame_width//2+current_padding_pixels,anchorY=current_frame_height+current_padding_pixels-1))
    return {'frames':current_frame_records,'sourceFrames':current_source_bounds,'columns':current_column_counts[0],'rows':len(current_row_intervals),'padding':current_padding_pixels}
