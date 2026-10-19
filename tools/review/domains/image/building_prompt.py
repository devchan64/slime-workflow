"""건물 Qwen 페이지의 추적 기본 문구와 입력 준비 상태."""
from pathlib import Path
from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt

BUILDING_PROMPT_SOURCE_PATH = Path(__file__).resolve().parents[4] / 'generators/image/config/building-qwen-prompt.txt'


def load_building_base_prompt():
    current_prompt_text = BUILDING_PROMPT_SOURCE_PATH.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('건물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def check_building_input_readiness(current_prompt_text, current_style_enabled, current_transparency_enabled, current_layout_image, building_prompt_enabled=False):
    if building_prompt_enabled:
        current_prompt_text = (current_prompt_text.strip() + ' ' + load_building_base_prompt()).strip()
    current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_prompt_text, current_style_enabled, current_transparency_enabled)
    return current_layout_image is not None and 0 < len(current_final_prompt.split()) < 100


def load_prop_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('prop-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('소품 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def load_vegetation_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('vegetation-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('자연물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


BUILDING_LAYOUT_PRESET_NAMES = tuple(f'{current_width_count}x{current_depth_count}-{current_entrance_side}' for current_width_count, current_depth_count in ((2, 2), (3, 3), (4, 3)) for current_entrance_side in ('south', 'east'))


def load_building_layout_preset(current_preset_name, current_height_pixels=140):
    from PIL import Image
    if current_preset_name not in BUILDING_LAYOUT_PRESET_NAMES:
        raise ValueError('등록되지 않은 건물 구도 프리셋입니다.')
    if current_height_pixels not in (80, 140, 200):
        raise ValueError('등록되지 않은 건물 높이 가이드입니다.')
    current_height_suffix = '' if current_height_pixels == 140 else '-' + str(current_height_pixels)
    current_image_path = BUILDING_PROMPT_SOURCE_PATH.parent / 'building-layouts' / (current_preset_name + current_height_suffix + '.png')
    with Image.open(current_image_path) as current_image_value:
        return current_image_value.copy()
