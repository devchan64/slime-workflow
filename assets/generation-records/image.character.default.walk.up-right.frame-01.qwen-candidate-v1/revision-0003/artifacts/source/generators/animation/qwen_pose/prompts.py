"""외부에서 전달한 버전별 기준 프롬프트를 엄격하게 읽는다."""
from pathlib import Path
import hashlib
from string import Formatter
import yaml

ALLOWED_POSE_KINDS = ('rig', 'openpose')
ALLOWED_REFERENCE_ORDERS = ('standing-first', 'pose-first')
REQUIRED_PROFILE_FIELDS = {'id', 'version', 'templates'}
REQUIRED_TEMPLATE_FIELDS = {'pose_prompt', 'optional_prompt', 'validation_status'}
REQUIRED_PROMPT_FIELDS = {'character_image_index', 'pose_image_index'}


def validate_reference_options(pose_reference_kind, selected_reference_order):
    if pose_reference_kind not in ALLOWED_POSE_KINDS:
        raise ValueError('pose kind는 rig 또는 openpose여야 합니다.')
    if selected_reference_order not in ALLOWED_REFERENCE_ORDERS:
        raise ValueError('지원하지 않는 참조 순서입니다.')


class UniqueKeySafeLoader(yaml.SafeLoader):
    """중복 YAML 키를 거부한다."""


def construct_unique_mapping(yaml_loader_instance, yaml_mapping_node):
    parsed_mapping_values = {}
    for mapping_key_node, mapping_value_node in yaml_mapping_node.value:
        mapping_key_value = yaml_loader_instance.construct_object(mapping_key_node)
        if not isinstance(mapping_key_value, str) or mapping_key_value in parsed_mapping_values:
            raise ValueError('YAML 키는 중복 없는 문자열이어야 합니다.')
        parsed_mapping_values[mapping_key_value] = yaml_loader_instance.construct_object(mapping_value_node)
    return parsed_mapping_values


UniqueKeySafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def load_pose_prompt(prompt_profile_path, pose_reference_kind, selected_reference_order='standing-first', *, include_optional_prompt=True):
    if type(include_optional_prompt) is not bool:
        raise ValueError('옵션 프롬프트 사용 여부는 bool이어야 합니다.')
    validate_reference_options(pose_reference_kind, selected_reference_order)
    profile_source_bytes = Path(prompt_profile_path).read_bytes()
    profile_parsed_values = yaml.load(profile_source_bytes, Loader=UniqueKeySafeLoader)
    if not isinstance(profile_parsed_values, dict) or set(profile_parsed_values) != REQUIRED_PROFILE_FIELDS:
        raise ValueError('프롬프트 프로필 필드는 id/version/templates여야 합니다.')
    if not isinstance(profile_parsed_values['id'], str) or not profile_parsed_values['id'].strip():
        raise ValueError('프로필 id가 필요합니다.')
    if type(profile_parsed_values['version']) is not int or profile_parsed_values['version'] < 1:
        raise ValueError('프로필 version은 양의 정수여야 합니다.')
    profile_template_values = profile_parsed_values['templates']
    if not isinstance(profile_template_values, dict) or set(profile_template_values) != set(ALLOWED_POSE_KINDS):
        raise ValueError('rig/openpose 템플릿을 모두 정의해야 합니다.')
    for template_entry_value in profile_template_values.values():
        if not isinstance(template_entry_value, dict) or set(template_entry_value) != REQUIRED_TEMPLATE_FIELDS:
            raise ValueError('템플릿 필드는 pose_prompt/optional_prompt/validation_status여야 합니다.')
        if template_entry_value['validation_status'] not in ('unverified', 'pose-change-success'):
            raise ValueError('지원하지 않는 프롬프트 검증 상태입니다.')
        template_prompt_text = template_entry_value['pose_prompt']
        if not isinstance(template_prompt_text, str) or not template_prompt_text.strip():
            raise ValueError('프롬프트가 비어 있습니다.')
        template_format_parts = list(Formatter().parse(template_prompt_text))
        if {template_field_name for _, template_field_name, _, _ in template_format_parts if template_field_name is not None} != REQUIRED_PROMPT_FIELDS:
            raise ValueError('프롬프트에는 캐릭터·포즈 이미지 번호만 명시해야 합니다.')
        if any(template_format_spec or template_conversion_flag for _, _, template_format_spec, template_conversion_flag in template_format_parts):
            raise ValueError('프롬프트 포맷 변환은 지원하지 않습니다.')
        optional_prompt_text = template_entry_value['optional_prompt']
        if not isinstance(optional_prompt_text, str) or '{' in optional_prompt_text or '}' in optional_prompt_text:
            raise ValueError('옵션 프롬프트는 치환 필드 없는 문자열이어야 합니다.')
    selected_template_value = profile_template_values[pose_reference_kind]
    character_image_index = 1 if selected_reference_order == 'standing-first' else 2
    rendered_prompt_text = selected_template_value['pose_prompt'].strip().format(character_image_index=character_image_index, pose_image_index=3-character_image_index)
    # 기준 포즈 문구의 변경은 참조 역할·순서와 포즈 재검증을 동반해야 한다.
    if include_optional_prompt and selected_template_value['optional_prompt'].strip():
        rendered_prompt_text += ' ' + selected_template_value['optional_prompt'].strip()
    prompt_source_record = {'id': profile_parsed_values['id'], 'version': profile_parsed_values['version'], 'profile_sha256': hashlib.sha256(profile_source_bytes).hexdigest(), 'pose_reference_kind': pose_reference_kind, 'validation_status': selected_template_value['validation_status'], 'optional_prompt_enabled': include_optional_prompt}
    return rendered_prompt_text, prompt_source_record
