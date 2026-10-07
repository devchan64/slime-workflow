"""검수 PNG를 방향별 GIF와 동기화된 4방향 비교 GIF로 내보낸다."""
from PIL import Image, ImageDraw

GIF_TIME_UNIT_MILLISECONDS = 10
GIF_SECOND_MILLISECONDS = 1000
GIF_CONTACT_COLUMN_COUNT = 2
GIF_CAPTION_HEIGHT_PIXELS = 24
GIF_BACKGROUND_COLOR = (245, 245, 245)
GIF_SKELETON_COLOR = (38, 71, 94)
GIF_LABEL_COLOR = (0, 0, 0)


def export_motion_gifs(current_preview_record, current_output_path, current_progress_callback, current_palette_mode='skeleton'):
    current_frame_count = current_preview_record['frames']
    current_frame_rate = current_preview_record['preview_fps']
    current_direction_names = current_preview_record['directions']
    if current_palette_mode not in ('skeleton', 'adaptive'):
        raise ValueError('GIF 팔레트 방식 오류')
    if type(current_frame_count) is not int or current_frame_count < 1 or current_frame_rate != 8:
        raise ValueError('GIF 입력은 1프레임 이상의 8 FPS 검수 결과여야 합니다.')
    if not current_direction_names or len(set(current_direction_names)) != len(current_direction_names) or set(current_direction_names) - {'down_left', 'down_right', 'up_left', 'up_right'}:
        raise ValueError('GIF 방향 입력 오류')
    current_palette_image = Image.new('P', (1, 1))
    current_palette_image.putpalette(list(GIF_BACKGROUND_COLOR + GIF_SKELETON_COLOR + GIF_LABEL_COLOR) + [0] * (768 - 9))
    # GIF의 10ms 단위 제약을 120/130ms 교대로 표현해 총 재생 시간을 보존한다.
    current_frame_durations = [(int((current_frame_index + 1) * GIF_SECOND_MILLISECONDS / current_frame_rate / GIF_TIME_UNIT_MILLISECONDS) - int(current_frame_index * GIF_SECOND_MILLISECONDS / current_frame_rate / GIF_TIME_UNIT_MILLISECONDS)) * GIF_TIME_UNIT_MILLISECONDS for current_frame_index in range(current_frame_count)]
    current_direction_frames = {}
    current_expected_size = None
    for current_direction_name in current_direction_names:
        current_loaded_frames = []
        for current_frame_index in range(1, current_frame_count + 1):
            with Image.open(current_output_path / current_direction_name / f'frame-{current_frame_index:04d}.png') as current_source_image:
                if current_source_image.format != 'PNG':
                    raise ValueError('GIF 원본은 PNG만 허용합니다.')
                if current_expected_size is None:
                    current_expected_size = current_source_image.size
                if current_source_image.size != current_expected_size:
                    raise ValueError('GIF 원본 프레임 크기가 서로 다릅니다.')
                current_loaded_frames.append(current_source_image.convert('RGB'))
        current_direction_frames[current_direction_name] = current_loaded_frames
    if current_palette_mode == 'adaptive':
        # 메시 음영을 위해 모든 프레임을 표본화한 공통 팔레트를 사용한다.
        current_palette_samples = [current_frame_image.resize((128, 128)) for current_loaded_frames in current_direction_frames.values() for current_frame_image in current_loaded_frames]
        current_palette_sheet = Image.new('RGB', (128 * len(current_direction_names), 128 * current_frame_count), GIF_BACKGROUND_COLOR)
        for current_sample_index, current_sample_image in enumerate(current_palette_samples):
            current_palette_sheet.paste(current_sample_image, (current_sample_index // current_frame_count * 128, current_sample_index % current_frame_count * 128))
        current_palette_image = current_palette_sheet.quantize(colors=256)
    current_export_records = []

    def save_animated_frames(current_image_frames, current_relative_name, current_label_text):
        current_indexed_frames = [current_frame_image.quantize(palette=current_palette_image, dither=Image.Dither.NONE) for current_frame_image in current_image_frames]
        with (current_output_path / current_relative_name).open('xb') as current_output_stream:
            current_indexed_frames[0].save(current_output_stream, format='GIF', save_all=True, append_images=current_indexed_frames[1:], duration=current_frame_durations, loop=0, disposal=2, optimize=False)
        current_export_records.append({'path': current_relative_name, 'label': current_label_text, 'duration_ms': sum(current_frame_durations), 'loop': 'repeat_without_seam_correction'})
        current_progress_callback('gif', f'{current_relative_name} 저장 · {sum(current_frame_durations)}ms · 루프 연결 보정 없음')

    for current_direction_name, current_loaded_frames in current_direction_frames.items():
        save_animated_frames(current_loaded_frames, current_direction_name + '.gif', current_direction_name + ' GIF')
    current_column_count = min(GIF_CONTACT_COLUMN_COUNT, len(current_direction_names))
    current_row_count = (len(current_direction_names) + current_column_count - 1) // current_column_count
    current_frame_width, current_frame_height = current_expected_size
    current_cell_height = current_frame_height + GIF_CAPTION_HEIGHT_PIXELS
    current_contact_frames = []
    for current_frame_index in range(current_frame_count):
        current_contact_image = Image.new('RGB', (current_frame_width * current_column_count, current_cell_height * current_row_count), GIF_BACKGROUND_COLOR)
        current_drawing_context = ImageDraw.Draw(current_contact_image)
        for current_direction_index, current_direction_name in enumerate(current_direction_names):
            current_column_offset = current_direction_index % current_column_count * current_frame_width
            current_row_offset = current_direction_index // current_column_count * current_cell_height
            current_contact_image.paste(current_direction_frames[current_direction_name][current_frame_index], (current_column_offset, current_row_offset + GIF_CAPTION_HEIGHT_PIXELS))
            current_drawing_context.text((current_column_offset + 8, current_row_offset + 5), current_direction_name, fill=GIF_LABEL_COLOR)
        current_contact_frames.append(current_contact_image)
    save_animated_frames(current_contact_frames, 'overview.gif', '전체 방향 비교 GIF')
    return current_export_records
