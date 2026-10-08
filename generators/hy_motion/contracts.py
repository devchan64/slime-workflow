"""HY-Motion의 고정 구성과 GUI·CLI 공통 입력 검증."""
import hashlib
import math
from pathlib import Path

import yaml
from tools.review.common.generation_records import validate_history_tag

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
MODEL_CACHE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.model/hy-motion'
SOURCE_BUNDLE_DIRECTORY = MODEL_CACHE_DIRECTORY / 'upstream'
DEFAULT_CONFIG_PATH = Path(__file__).parent / 'config/defaults.yaml'
ENCODER_TEMPLATE_PATH = Path(__file__).parent / 'config/encoder-system.txt'
MOTION_PRESETS_PATH = Path(__file__).parent / 'config/motion-presets.yaml'
SUPPORTED_DIRECTION_NAMES = ('down_left', 'down_right', 'up_left', 'up_right')
MAXIMUM_MOTION_FRAMES = 360
MOTION_OUTPUT_FPS = 30
MAXIMUM_DURATION_SECONDS = MAXIMUM_MOTION_FRAMES / MOTION_OUTPUT_FPS
EXPECTED_CONFIG_FIELDS = {'schema_version', 'model_id', 'model_variant', 'source_revision', 'duration_seconds', 'seed', 'steps', 'guidance_scale', 'prompt', 'directions', 'preview_fps', 'preview_size', 'camera_elevation', 'camera_angles'}


def load_unique_mapping(current_yaml_loader, current_mapping_node):
    current_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_field_name = current_yaml_loader.construct_object(current_key_node)
        if current_field_name in current_mapping_values:
            raise ValueError(f'중복 YAML 필드: {current_field_name}')
        current_mapping_values[current_field_name] = current_yaml_loader.construct_object(current_value_node)
    return current_mapping_values


class UniqueConfigLoader(yaml.SafeLoader):
    """중복 키를 거절한다."""


UniqueConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, load_unique_mapping)


def load_generation_defaults():
    current_config_values = yaml.load(DEFAULT_CONFIG_PATH.read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_config_values, dict) or set(current_config_values) != EXPECTED_CONFIG_FIELDS:
        raise ValueError('HY-Motion 기본 설정 필드 오류')
    if type(current_config_values['schema_version']) is not int or current_config_values['schema_version'] != 1 or current_config_values['model_id'] != 'tencent/HY-Motion-1.0' or current_config_values['model_variant'] != 'HY-Motion-1.0-Lite':
        raise ValueError('HY-Motion 고정 모델 계약 오류')
    if current_config_values['steps'] != 50 or current_config_values['guidance_scale'] != 5.0 or current_config_values['preview_fps'] != 8 or current_config_values['preview_size'] != 512:
        raise ValueError('HY-Motion 실행·미리보기 설정 오류')
    if not isinstance(current_config_values['camera_angles'], dict) or set(current_config_values['camera_angles']) != set(SUPPORTED_DIRECTION_NAMES) or any(type(current_angle_value) not in (int, float) or not math.isfinite(current_angle_value) for current_angle_value in current_config_values['camera_angles'].values()):
        raise ValueError('방향별 카메라 설정 오류')
    if type(current_config_values['camera_elevation']) not in (int, float) or not 0 <= current_config_values['camera_elevation'] <= 90:
        raise ValueError('카메라 내려다보기 각도 오류')
    import re
    if not isinstance(current_config_values['source_revision'], str) or not re.fullmatch('[0-9a-f]{40}', current_config_values['source_revision']):
        raise ValueError('공식 소스 버전은 고정 SHA여야 합니다.')
    validate_generation_request({current_field_name: current_config_values[current_field_name] for current_field_name in ('prompt', 'duration_seconds', 'seed', 'directions')})
    return current_config_values


def validate_generation_request(current_request_values):
    if not isinstance(current_request_values, dict) or set(current_request_values) - {'prompt', 'duration_seconds', 'seed', 'directions', 'tag'} or not {'prompt', 'duration_seconds', 'seed', 'directions'} <= set(current_request_values):
        raise ValueError('프롬프트·길이·시드·방향 입력이 필요하며 알 수 없는 필드는 허용하지 않습니다.')
    current_prompt_text = current_request_values['prompt']
    if not isinstance(current_prompt_text, str) or not 1 <= len(current_prompt_text.split()) <= 29 or len(current_prompt_text) > 2000:
        raise ValueError('영문 동작 프롬프트를 1~29단어로 입력하세요.')
    current_duration_value = current_request_values['duration_seconds']
    if type(current_duration_value) not in (int, float) or not math.isfinite(current_duration_value) or not 1 <= current_duration_value <= MAXIMUM_DURATION_SECONDS:
        raise ValueError(f'모션 길이는 1~{MAXIMUM_DURATION_SECONDS:g}초여야 합니다.')
    current_seed_value = current_request_values['seed']
    if type(current_seed_value) is not int or not 0 <= current_seed_value < 2**32:
        raise ValueError('시드는 0~4294967295 정수여야 합니다.')
    current_direction_names = current_request_values['directions']
    if not isinstance(current_direction_names, list) or not current_direction_names or any(not isinstance(current_direction_name, str) or current_direction_name not in SUPPORTED_DIRECTION_NAMES for current_direction_name in current_direction_names) or len(set(current_direction_names)) != len(current_direction_names):
        raise ValueError('중복 없는 미리보기 방향을 선택하세요.')
    return {**current_request_values, 'prompt': current_prompt_text.strip(), 'tag': validate_history_tag(current_request_values.get('tag', ''))}


def build_prompt_provenance(current_prompt_text):
    return {'text': current_prompt_text, 'word_count': len(current_prompt_text.split()), 'sha256': hashlib.sha256(current_prompt_text.encode()).hexdigest()}


def load_motion_presets():
    current_preset_document = yaml.load(MOTION_PRESETS_PATH.read_text(), Loader=UniqueConfigLoader)
    if not isinstance(current_preset_document, dict) or set(current_preset_document) != {'schema_version', 'presets'} or type(current_preset_document['schema_version']) is not int or current_preset_document['schema_version'] != 1:
        raise ValueError('모션 프리셋 문서 계약 오류')
    current_preset_records = current_preset_document['presets']
    if not isinstance(current_preset_records, dict) or set(current_preset_records) != {'standing', 'walking'}:
        raise ValueError('대기·걷기 프리셋이 필요합니다.')
    for current_preset_record in current_preset_records.values():
        if not isinstance(current_preset_record, dict) or set(current_preset_record) != {'label', 'prompt', 'duration_seconds'} or not isinstance(current_preset_record['label'], str) or not current_preset_record['label'].strip():
            raise ValueError('모션 프리셋 필드 오류')
        validate_generation_request({'prompt': current_preset_record['prompt'], 'duration_seconds': current_preset_record['duration_seconds'], 'seed': 10107, 'directions': list(SUPPORTED_DIRECTION_NAMES)})
    return current_preset_records


def read_encoder_system_prompt():
    # 공식 모델 상수의 줄바꿈·들여쓰기까지 보존한다.
    return '\n    ' + ENCODER_TEMPLATE_PATH.read_text().strip() + '\n'


def build_encoder_input_preview(current_prompt_text):
    # 고정 Qwen3 revision의 system/user 2메시지 템플릿. 실행 때 tokenizer 결과와 대조한다.
    return '<|im_start|>system\n' + read_encoder_system_prompt() + '<|im_end|>\n<|im_start|>user\n' + current_prompt_text.strip() + '<|im_end|>\n'
