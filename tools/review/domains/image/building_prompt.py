"""건물 Qwen 페이지의 추적 기본 문구와 입력 준비 상태."""
from pathlib import Path
from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt

BUILDING_PROMPT_SOURCE_PATH = Path(__file__).resolve().parents[4] / 'generators/image/config/building-qwen-prompt.txt'


def load_building_base_prompt():
    current_prompt_text = BUILDING_PROMPT_SOURCE_PATH.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('건물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def check_building_input_readiness(current_prompt_text, current_style_enabled, current_transparency_enabled, current_layout_image):
    current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_prompt_text, current_style_enabled, current_transparency_enabled)
    return current_layout_image is not None and 0 < len(current_final_prompt.split()) < 100


def load_prop_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('prop-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('기물 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text


def load_vegetation_base_prompt():
    current_prompt_path = BUILDING_PROMPT_SOURCE_PATH.with_name('vegetation-qwen-prompt.txt')
    current_prompt_text = current_prompt_path.read_text(encoding='utf-8').strip()
    if not 0 < len(current_prompt_text.split()) < 100:
        raise ValueError('식생 기본 프롬프트는 1~99단어여야 합니다.')
    return current_prompt_text
