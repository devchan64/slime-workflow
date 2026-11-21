"""VACE 입력 모드와 Python 생성 요청 변환."""
from pathlib import Path
import base64
import io
from contextlib import nullcontext
from PIL import Image, ImageOps
from generators.wan_vace.contracts import validate_vace_request

VACE_INPUT_CHOICES = [('제어 영상 + 참조 이미지 · 포즈', 'pose'), ('참조 이미지 + 프롬프트', 'reference'), ('첫 프레임 + 프롬프트', 'first_frame'), ('프롬프트만', 'text'), ('영상 부분 편집 + 참조 이미지', 'video_edit'), ('영상 전체 조건 + 참조 이미지 · 실험', 'video_condition')]


VACE_MODE_HELP_TEXT = {
    'pose': '**제어 영상 + 참조 이미지 · 포즈**\n\n1. 캐릭터 외형 참조 이미지 1장과 키모도 DWPose MP4를 첨부합니다. SOMA 렌더나 완성 캐릭터 영상은 포즈 입력이 아닙니다.\n2. 주체·동작·카메라를 적고 출력 프레임을 영상 길이 이내의 4n+1로 설정합니다.\n3. 고급 설정에서 스텝·CFG·Flow shift·VACE 조건 강도를 확인합니다. 제작자 예제는 81프레임·16fps, 50스텝, CFG 5, shift 12, 조건 강도 1을 사용합니다. 설정은 자동으로 바뀌지 않습니다.\n\nMP4는 832×480·16fps·32MiB 이하여야 합니다. 관절 위치를 강제하지 않으므로 자세와 타이밍을 검수하세요. 현재 화면은 제어 영상 중 DWPose만 지원합니다.',
    'reference': '**참조 이미지 + 프롬프트**\n\n1. 캐릭터 외형 참조 이미지 1장을 첨부합니다.\n2. 주체·동작·카메라를 적고 출력 프레임을 선택합니다.\n3. 고급 설정에서 스텝·CFG·Flow shift·VACE 조건 강도를 조정합니다.\n\n이미지는 외형 조건이며 첫 화면이나 동작을 고정하지 않습니다. 포즈 영상을 따르려면 제어 영상 + 참조 이미지를 선택하세요.',
    'first_frame': '**첫 프레임 + 프롬프트**\n\n1. 시작 장면 이미지 1장을 첨부합니다.\n2. 이어질 동작을 적고 출력 프레임을 선택합니다.\n3. 고급 설정에서 스텝·CFG·Flow shift를 조정합니다.\n\n이미지는 첫 프레임 조건이며 출력 픽셀의 완전 일치는 보장되지 않습니다.',
    'text': '**프롬프트만**\n\n1. 주체·동작·배경·카메라를 적습니다.\n2. 출력 프레임을 선택하고 고급 설정에서 스텝·CFG·Flow shift를 조정합니다.\n\n이미지나 영상은 사용하지 않습니다. 특정 외형이나 포즈가 필요하면 참조 이미지 또는 제어 영상 모드를 선택하세요.',
    'video_edit': '**영상 부분 편집 + 참조 이미지**\n\n1. 외형 참조 이미지와 원본 MP4, 같은 좌표·길이의 마스크 MP4를 첨부합니다.\n2. 바꿀 내용을 적고 출력 프레임을 입력 길이 이내로 정합니다.\n3. 고급 설정에서 스텝·CFG·Flow shift·VACE 조건 강도를 조정합니다.\n\n마스크의 흰색은 재생성, 검정은 보존 조건입니다. MP4는 832×480·16fps·각 32MiB 이하여야 합니다. 마스크 밖도 바뀔 수 있으며 원본과 자동 합성하지 않습니다.',
    'video_condition': '**영상 전체 조건 + 참조 이미지 · 실험**\n\n1. 캐릭터 참조 이미지 1장과 원본 RGB 영상을 첨부합니다.\n2. 장면과 원하는 변화를 적고 출력 프레임을 영상 길이 이내로 설정합니다.\n3. 고급 설정에서 스텝·CFG·Flow shift·VACE 조건 강도를 조정합니다.\n\n전체 영상이 조건이며 자동 합성하지 않습니다. 자세와 외형 보존은 보장되지 않습니다. MP4는 832×480·16fps·32MiB 이하여야 합니다.',
}

def build_vace_payload(current_input_mode, current_reference_path, current_prompt_text, current_negative_text, current_frame_count, current_seed_value, current_steps_value, current_shift_value, current_guidance_value, current_strength_value, current_edit_video=None, current_edit_mask=None, current_pose_video=None):
    for current_integer_value in (current_frame_count, current_seed_value, current_steps_value):
        if isinstance(current_integer_value, bool) or not isinstance(current_integer_value, (int, float)) or not float(current_integer_value).is_integer():
            raise ValueError('프레임·시드·스텝은 정수여야 합니다.')
    current_encoded_images = []
    if current_input_mode == 'text' and current_reference_path:
        raise ValueError('텍스트만 모드에서는 첨부 이미지를 지워 주세요.')
    if current_reference_path:
        with (nullcontext(current_reference_path) if isinstance(current_reference_path, Image.Image) else Image.open(current_reference_path)) as current_image_object:
            current_image_object = ImageOps.contain(current_image_object.convert('RGBA'), (832, 480), Image.Resampling.LANCZOS)
            current_canvas_image = Image.new('RGB', (832, 480), 'white')
            current_canvas_image.paste(current_image_object, ((832-current_image_object.width)//2, (480-current_image_object.height)//2), current_image_object)
            current_image_buffer = io.BytesIO()
            current_canvas_image.save(current_image_buffer, format='PNG')
            current_encoded_images.append(base64.b64encode(current_image_buffer.getvalue()).decode())
    current_payload_record = dict(action='generate', mode=current_input_mode, prompt=current_prompt_text, negative_prompt=current_negative_text, images=current_encoded_images, width=832, height=480, frames=int(current_frame_count), seed=int(current_seed_value), steps=int(current_steps_value), flow_shift=current_shift_value, guidance_scale=current_guidance_value, reference_strength=current_strength_value)
    if current_input_mode == 'pose':
        if not current_pose_video or current_edit_video or current_edit_mask:
            raise ValueError('DWPose MP4를 첨부하고 부분 편집 영상·마스크는 비워 주세요.')
        current_payload_record['pose_video'] = base64.b64encode(Path(current_pose_video).read_bytes()).decode()
    elif current_pose_video:
        raise ValueError('포즈 모드 외에는 DWPose 영상을 비워 주세요.')
    if current_input_mode == 'video_edit':
        if not current_edit_video or not current_edit_mask:
            raise ValueError('원본 MP4와 편집 마스크 MP4가 필요합니다.')
        current_payload_record.update(edit_video=base64.b64encode(Path(current_edit_video).read_bytes()).decode(), edit_mask=base64.b64encode(Path(current_edit_mask).read_bytes()).decode())
    elif current_input_mode == 'video_condition':
        if not current_edit_video or current_edit_mask:
            raise ValueError('영상 전체 조건에는 원본 MP4만 필요하며 마스크는 입력하지 않습니다.')
        current_payload_record['edit_video'] = base64.b64encode(Path(current_edit_video).read_bytes()).decode()
    elif current_edit_video or current_edit_mask:
        raise ValueError('영상 편집 외 모드에서는 영상·마스크를 비워 주세요.')
    validate_vace_request(current_payload_record)
    return current_payload_record
