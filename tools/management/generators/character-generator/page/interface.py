"""캐릭터 생성 화면 설정."""
from pathlib import Path

import yaml

from tools.management.ui.shared.qwen_generator_page import build_qwen_2511_interface

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[5]
STYLE_PROMPT_PATH = WORKFLOW_ROOT_DIRECTORY / 'prompts/common/art-style-v1.5.0.yaml'
CHARACTER_PROMPT_PREFIX = ('Full-body adult fantasy adventurer, standing front view. '
                           'Brown shoulder-length hair, amber eyes, green tunic, leather boots and satchel. '
                           'Expressive eyes, small simple nose and mouth, softly tapered jaw, grouped hair locks. '
                           'Plain light background.')


def load_character_default_prompt():
    """화풍 원문을 직접 읽어 편집 가능한 예시와 결합한다."""
    current_style_record = yaml.safe_load(STYLE_PROMPT_PATH.read_text(encoding='utf-8'))
    if current_style_record.get('prompt_id') != 'slime_common_art_style' or current_style_record.get('version') != '1.5.0' or not isinstance(current_style_record.get('prompt'), str):
        raise ValueError('공용 화풍 v1.5.0 원문을 확인하세요.')
    return CHARACTER_PROMPT_PREFIX + '\n\n' + current_style_record['prompt']


GENERATOR_PAGE_OPTIONS = {'qwen21_mode_enabled': True, 'character_mode_enabled': True}


def build_generator_page(current_server_address, current_review_port):
    return build_qwen_2511_interface(current_server_address, **GENERATOR_PAGE_OPTIONS)
