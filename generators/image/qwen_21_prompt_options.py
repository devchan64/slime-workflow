"""Qwen 2.1에서 선택한 공용 화풍·투명 배경 문구를 조합한다."""
from pathlib import Path
import yaml

QWEN_PROMPT_OPTIONS_PATH = Path(__file__).parent / 'config/qwen_21_prompt_options.yaml'
QWEN_PROMPT_OPTION_NAMES = ('common_style', 'transparent_background')


class UniquePromptOptionsLoader(yaml.SafeLoader):
    """중복 옵션 키를 거절하는 안전한 설정 로더."""


def construct_prompt_options_mapping(current_yaml_loader, current_mapping_node):
    current_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_field_name = current_yaml_loader.construct_object(current_key_node)
        if current_field_name in current_mapping_values:
            raise ValueError(f'Qwen 프롬프트 옵션 중복 키: {current_field_name}')
        current_mapping_values[current_field_name] = current_yaml_loader.construct_object(current_value_node)
    return current_mapping_values


UniquePromptOptionsLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_prompt_options_mapping)


def load_qwen_prompt_options():
    current_option_record = yaml.load(QWEN_PROMPT_OPTIONS_PATH.read_text(), Loader=UniquePromptOptionsLoader)
    return validate_prompt_option_record(current_option_record)


def validate_prompt_option_record(current_option_record):
    if not isinstance(current_option_record, dict) or set(current_option_record) != {'style_source', 'transparent_background_suffix', *QWEN_PROMPT_OPTION_NAMES}:
        raise ValueError('Qwen 프롬프트 옵션 설정 필드 오류')
    if any(not isinstance(current_option_record[current_option_name], str) or not current_option_record[current_option_name].strip() for current_option_name in current_option_record):
        raise ValueError('Qwen 프롬프트 옵션 문구 오류')
    return current_option_record


def compose_qwen_option_prompt(current_user_prompt, common_style_enabled=False, transparent_background_enabled=False, saved_option_prompts=None):
    if not isinstance(current_user_prompt, str):
        raise ValueError('프롬프트는 문자열이어야 합니다.')
    if type(common_style_enabled) is not bool or type(transparent_background_enabled) is not bool:
        raise ValueError('프롬프트 옵션은 불리언이어야 합니다.')
    current_option_record = load_qwen_prompt_options() if saved_option_prompts is None else validate_prompt_option_record(saved_option_prompts)
    current_prefix_prompt = current_option_record['transparent_background'] if transparent_background_enabled else ''
    current_style_prompt = current_option_record['common_style'] if common_style_enabled else ''
    current_suffix_prompt = current_option_record['transparent_background_suffix'] if transparent_background_enabled else ''
    current_added_prompt = ' '.join(filter(None, (current_prefix_prompt, current_style_prompt, current_suffix_prompt)))
    current_final_prompt = ' '.join(filter(None, (current_prefix_prompt, current_style_prompt, current_user_prompt.strip(), current_suffix_prompt)))
    return current_final_prompt,current_added_prompt
