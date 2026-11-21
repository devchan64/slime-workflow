"""Qwen 이미지 생성의 공용 화풍 원문과 최종 조합."""
import hashlib
from pathlib import Path

import yaml

STYLE_SOURCE_PATH = Path(__file__).resolve().parents[2] / 'prompts/common/art-style-v1.5.0.yaml'
STYLE_PROMPT_ID = 'slime_common_art_style'
STYLE_PROMPT_VERSION = '1.5.0'


def load_common_style_record():
    current_style_record = yaml.safe_load(STYLE_SOURCE_PATH.read_text(encoding='utf-8'))
    if not isinstance(current_style_record, dict) or current_style_record.get('prompt_id') != STYLE_PROMPT_ID or current_style_record.get('version') != STYLE_PROMPT_VERSION:
        raise ValueError('공용 화풍 v1.5.0 식별자가 일치하지 않습니다.')
    current_style_text = current_style_record.get('prompt')
    if not isinstance(current_style_text, str) or not current_style_text.strip() or hashlib.sha256(current_style_text.encode()).hexdigest() != current_style_record.get('sha256') or len(current_style_text.split()) != current_style_record.get('word_count'):
        raise ValueError('공용 화풍 v1.5.0 원문 무결성 오류')
    return current_style_record


def compose_common_style_prompt(current_prompt_text):
    if not isinstance(current_prompt_text, str):
        raise ValueError('프롬프트는 문자열이어야 합니다.')
    current_style_record = load_common_style_record()
    current_style_text = current_style_record['prompt']
    # YAML 줄바꿈과 화면 공백의 차이를 무시하고 기존 원문 중복을 방지한다.
    current_normalized_prompt = ' '.join(current_prompt_text.split())
    current_normalized_style = ' '.join(current_style_text.split())
    current_occurrence_count = current_normalized_prompt.count(current_normalized_style)
    if current_occurrence_count > 1:
        raise ValueError('공용 화풍 v1.5.0 원문이 중복됩니다.')
    current_final_prompt = current_prompt_text.strip() if current_occurrence_count else ' '.join(filter(None, (current_prompt_text.strip(), current_style_text)))
    return current_final_prompt, {'id': STYLE_PROMPT_ID, 'version': STYLE_PROMPT_VERSION, 'source': 'prompts/common/art-style-v1.5.0.yaml', 'prompt': current_style_text, 'sha256': current_style_record['sha256'], 'already_present': bool(current_occurrence_count), 'user_prompt': current_prompt_text}
