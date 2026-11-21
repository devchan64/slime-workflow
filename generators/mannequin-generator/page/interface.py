"""마네킨 제작 단계별 Qwen 2.1 입력."""
from pathlib import Path

from PIL import Image

MANNEQUIN_BASELINE_DIRECTORY = Path(__file__).resolve().parents[3] / 'baseline/mannequin'
MANNEQUIN_PRESET_RECORDS = {
    'jointed': ('관절 신체 조정', 'neutral-body-four-directions.png', None, 'Edit image 1 as an articulated neutral body mannequin. Preserve head size, body proportions and pose unless requested. Four views: front, front-quarter, profile, back, in a 2x2 grid. Plain background.'),
    'clothed': ('피부·기본복 적용', 'neutral-body-faced-four-directions.png', None, 'Edit image 1. Replace mechanical joints with skin and add a fitted simple top and shorts. Preserve the existing facial features and expression in each view, head shape, body proportions, pose and four-view 2x2 layout. Bald. Plain background.'),
    'face': ('기본 얼굴 조정', 'neutral-head-basic-four-directions.png', None, 'Edit image 1 as a neutral mannequin head. Preserve head silhouette and facial proportions unless requested. Four views: front, front-quarter, profile, back, in a 2x2 grid. Plain background.'),
    'face-on-body': ('전신에 얼굴 적용', 'neutral-body-four-directions.png', 'neutral-head-basic-four-directions.png', 'Edit only facial features in image 1, using image 2 as reference. Keep image 1 head silhouette and every body part unchanged: positions, outlines, proportions, joints and original shading. Add eyes, nose and mouth to front, quarter and profile. Preserve exact 2x2 layout and back view. No hair.'),
}


def load_mannequin_preset(current_preset_identifier):
    """선택한 기준 이미지를 복사해 반환하고 기존 입력을 명시적으로 교체한다."""
    if current_preset_identifier not in MANNEQUIN_PRESET_RECORDS:
        raise ValueError('등록되지 않은 마네킨 제작 단계입니다.')
    current_label_text, current_first_name, current_second_name, current_prompt_text = MANNEQUIN_PRESET_RECORDS[current_preset_identifier]
    current_image_values = []
    for current_image_name in (current_first_name, current_second_name):
        if current_image_name is None:
            current_image_values.append(None)
        else:
            with Image.open(MANNEQUIN_BASELINE_DIRECTORY / current_image_name) as current_image_value:
                current_image_values.append(current_image_value.convert('RGB').copy())
    return current_prompt_text, *current_image_values


def preview_mannequin_preset(current_preset_identifier):
    """제작 단계의 기준 이미지와 파일명을 적용 전에 보여준다."""
    current_prompt_text, current_first_image, current_second_image = load_mannequin_preset(current_preset_identifier)
    current_label_text, current_first_name, current_second_name, current_prompt_value = MANNEQUIN_PRESET_RECORDS[current_preset_identifier]
    current_description_text = f'참조 1: `{current_first_name}`' + (f' · 참조 2: `{current_second_name}`' if current_second_name else '')
    return current_description_text, current_first_image, current_second_image


GENERATOR_PAGE_OPTIONS = {'qwen21_mode_enabled': True, 'mannequin_mode_enabled': True}


def build_generator_page(current_server_address, current_review_port):
    from tools.management.ui.shared.qwen_generator_page import build_qwen_2511_interface
    return build_qwen_2511_interface(current_server_address, **GENERATOR_PAGE_OPTIONS)
