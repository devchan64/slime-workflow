"""선택형 화풍·투명 배경 프롬프트를 조합하는 Qwen Image 2.1 서비스."""
import base64
import hashlib
import json
from pathlib import Path

from generators.image.qwen_21_runtime import QWEN_ALLOWED_INFERENCE_STEPS, QWEN_MODEL_IDENTIFIER, QWEN_MODEL_REVISION, validate_qwen_model_assets
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT
from tools.review.domains.image.image_runtime import validate_image_runtime
from tools.review.domains.image.three_reference_generation import decode_reference_image, validate_three_reference_request, verify_reference_snapshots

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[4]
QWEN_GENERATION_ROOT = WORKFLOW_ROOT_PATH / '.tmp/test/qwen-image-21'


def validate_qwen_plain_request(current_request_record, allowed_inference_steps=QWEN_ALLOWED_INFERENCE_STEPS):
    from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt, load_qwen_prompt_options, QWEN_PROMPT_OPTION_NAMES
    reference_resolution_value = None
    vae_roundtrip_diagnostic = None
    if isinstance(current_request_record, dict) and 'vae_roundtrip_diagnostic' in current_request_record:
        current_request_record = dict(current_request_record)
        vae_roundtrip_diagnostic = current_request_record.pop('vae_roundtrip_diagnostic')
        if vae_roundtrip_diagnostic is not True or not isinstance(current_request_record.get('images'), list) or len(current_request_record['images']) != 1:
            raise ValueError('VAE 왕복 진단에는 참조 이미지 한 장과 true 설정이 필요합니다.')
    if isinstance(current_request_record, dict) and 'reference_resolution' in current_request_record:
        current_request_record = dict(current_request_record)
        reference_resolution_value = current_request_record.pop('reference_resolution')
        if type(reference_resolution_value) is not int or reference_resolution_value not in (992, 1024, 1056):
            raise ValueError('참조 처리 해상도는 992·1024·1056 중 선택해야 합니다.')
        if not current_request_record.get('images'):
            raise ValueError('참조 처리 해상도에는 참조 이미지가 필요합니다.')
    current_prompt_options = None
    if isinstance(current_request_record, dict) and any(current_option_name in current_request_record for current_option_name in QWEN_PROMPT_OPTION_NAMES):
        current_request_record = dict(current_request_record)
        current_user_prompt = current_request_record.get('prompt')
        current_prompt_options = {current_option_name: current_request_record.pop(current_option_name, False) for current_option_name in QWEN_PROMPT_OPTION_NAMES}
        current_option_snapshot = load_qwen_prompt_options()
        current_final_prompt, current_added_prompt = compose_qwen_option_prompt(current_user_prompt, saved_option_prompts=current_option_snapshot, **{current_option_name+'_enabled':current_option_value for current_option_name,current_option_value in current_prompt_options.items()})
        current_request_record['prompt'] = current_final_prompt
    if isinstance(current_request_record, dict) and isinstance(current_request_record.get('images'), list):
        current_request_record = {**current_request_record, 'images': [
            base64.b64encode(decode_reference_image(current_image_text, composite_transparent_background=True)).decode()
            for current_image_text in current_request_record['images']
        ]}
    validated_request_record = validate_three_reference_request(current_request_record, allowed_inference_steps=allowed_inference_steps, maximum_reference_count=10, minimum_output_size=256)
    prompt_word_count = len(validated_request_record['prompt'].split())
    if not 0 < prompt_word_count < 100:
        raise ValueError('옵션 포함 최종 프롬프트는 1~99단어여야 합니다.')
    return {**validated_request_record, 'qwen21': {
        'schema_version': 1, 'model_id': QWEN_MODEL_IDENTIFIER, 'revision': QWEN_MODEL_REVISION,
        'prompt_word_count': prompt_word_count,
        'prompt_sha256': hashlib.sha256(validated_request_record['prompt'].encode()).hexdigest(),
        'additional_prompt': current_added_prompt if current_prompt_options is not None else '',
        **({'reference_resolution': reference_resolution_value} if reference_resolution_value is not None else {}),
        **({'vae_roundtrip_diagnostic': True} if vae_roundtrip_diagnostic else {}),
        **({'prompt_options': current_prompt_options, 'user_prompt': current_user_prompt, 'option_prompt_snapshot': current_option_snapshot, 'composition_version': 2} if current_prompt_options is not None else {}),
    }}


def verify_qwen_saved_request(current_job_root, current_request_record):
    from generators.image.qwen_21_circular import CIRCULAR_SELECTABLE_CONFIGURATIONS, CIRCULAR_SQUARE_WINDOW_SELECTABLE_CONFIGURATIONS, CIRCULAR_TANGENT_ONE_SELECTABLE_CONFIGURATIONS, CIRCULAR_PREVIOUS_SELECTABLE_CONFIGURATIONS, CIRCULAR_VAE_CONFIGURATION, CIRCULAR_SQUARE_WINDOW_CONFIGURATION, CIRCULAR_TANGENT_ONE_CONFIGURATION, CIRCULAR_PREVIOUS_VAE_CONFIGURATION, CIRCULAR_CORNER_CONFIGURATION, CIRCULAR_DOUBLE_STRIP_CONFIGURATION, CIRCULAR_SINGLE_STRIP_CONFIGURATION, CIRCULAR_VERTICAL_CONFIGURATION, CIRCULAR_COMPARISON_CONFIGURATION, CIRCULAR_LEGACY_CONFIGURATION, CIRCULAR_HALO_CONFIGURATION
    from generators.image.qwen_21_toroidal import TOROIDAL_LEGACY_CONFIGURATION, TOROIDAL_ATTENTION_CONFIGURATION
    circular_storage_enabled = current_job_root.parent.name == 'qwen-image-21-circular'
    if circular_storage_enabled and current_request_record.get('circular_vae') not in (*CIRCULAR_SELECTABLE_CONFIGURATIONS, *CIRCULAR_SQUARE_WINDOW_SELECTABLE_CONFIGURATIONS, *CIRCULAR_TANGENT_ONE_SELECTABLE_CONFIGURATIONS, *CIRCULAR_PREVIOUS_SELECTABLE_CONFIGURATIONS, CIRCULAR_VAE_CONFIGURATION, CIRCULAR_SQUARE_WINDOW_CONFIGURATION, CIRCULAR_TANGENT_ONE_CONFIGURATION, CIRCULAR_PREVIOUS_VAE_CONFIGURATION, CIRCULAR_CORNER_CONFIGURATION, CIRCULAR_DOUBLE_STRIP_CONFIGURATION, CIRCULAR_SINGLE_STRIP_CONFIGURATION, CIRCULAR_VERTICAL_CONFIGURATION, CIRCULAR_COMPARISON_CONFIGURATION, CIRCULAR_LEGACY_CONFIGURATION, CIRCULAR_HALO_CONFIGURATION, TOROIDAL_LEGACY_CONFIGURATION, TOROIDAL_ATTENTION_CONFIGURATION):
        raise ValueError('순환 VAE 실행 기록 설정이 일치하지 않습니다.')
    if not circular_storage_enabled and 'circular_vae' in current_request_record:
        raise ValueError('일반 Qwen 기록에 순환 VAE 설정을 사용할 수 없습니다.')
    verify_reference_snapshots(current_job_root, current_request_record)
    if 'body_reference_sources' in current_request_record:
        from importlib import import_module
        import_module('generators.character-generator.body_references').verify_body_reference_history(current_job_root, current_request_record)
    verify_saved_common_style(current_request_record)
    # 저장된 메타데이터도 동일한 입력 검증에서 다시 계산한다.
    import base64
    restored_input_record = {current_field_name: current_request_record[current_field_name]
        for current_field_name in ('action', 'prompt', 'tag', 'width', 'height', 'steps', 'seed')}
    restored_input_record['images'] = [base64.b64encode((current_job_root / current_reference_name).read_bytes()).decode()
        for current_reference_name in current_request_record['references']]
    if 'reference_resolution' in current_request_record.get('qwen21', {}):
        restored_input_record['reference_resolution'] = current_request_record['qwen21']['reference_resolution']
    if 'vae_roundtrip_diagnostic' in current_request_record.get('qwen21', {}):
        restored_input_record['vae_roundtrip_diagnostic'] = current_request_record['qwen21']['vae_roundtrip_diagnostic']
    if 'prompt_options' in current_request_record.get('qwen21', {}):
        from generators.image.qwen_21_prompt_options import compose_qwen_option_prompt
        current_prompt_metadata = current_request_record['qwen21']
        if current_prompt_metadata.get('composition_version') == 2:
            current_expected_prompt, current_added_prompt = compose_qwen_option_prompt(
                current_prompt_metadata['user_prompt'],
                current_prompt_metadata['prompt_options']['common_style'],
                current_prompt_metadata['prompt_options']['transparent_background'],
                saved_option_prompts=current_prompt_metadata['option_prompt_snapshot'])
        else:
            current_added_prompt = current_prompt_metadata['additional_prompt']
            current_expected_prompt = ' '.join(filter(None, (current_prompt_metadata['user_prompt'].strip(), current_added_prompt))) if current_added_prompt else current_prompt_metadata['user_prompt']
        if current_expected_prompt != current_request_record['prompt'] or hashlib.sha256(current_expected_prompt.encode()).hexdigest() != current_prompt_metadata['prompt_sha256']:
            raise ValueError('Qwen 최종 프롬프트가 옵션 기록과 일치하지 않습니다.')
    if current_job_root.parent.name == 'pose-transfer' or 'vnccs' in current_request_record:
        raise ValueError('포즈 변환 생성기는 폐기되었습니다.')
    expected_source_record = validate_qwen_plain_request(restored_input_record)['qwen21']
    if 'prompt_options' in current_request_record.get('qwen21', {}):
        expected_source_record.update({current_field_name: current_prompt_metadata[current_field_name] for current_field_name in ('prompt_options', 'user_prompt')})
        expected_source_record['additional_prompt'] = current_added_prompt
        if 'composition_version' in current_prompt_metadata:
            if current_prompt_metadata['composition_version'] != 2:
                raise ValueError('지원하지 않는 프롬프트 조합 버전입니다.')
            expected_source_record.update({current_field_name: current_prompt_metadata[current_field_name] for current_field_name in ('composition_version', 'option_prompt_snapshot')})
    if current_request_record.get('qwen21') != expected_source_record:
        raise ValueError('Qwen 2.1 실행 기록의 모델·프롬프트 정보가 일치하지 않습니다.')


def validate_styled_qwen_request(current_request_record):
    from generators.image.common_art_style import compose_common_style_prompt
    if not isinstance(current_request_record, dict):
        raise ValueError('생성 요청은 객체여야 합니다.')
    current_request_values = dict(current_request_record)
    current_body_reference_id = current_request_values.pop('body_reference_id', None)
    if current_body_reference_id is not None and (not isinstance(current_body_reference_id, str) or not current_body_reference_id):
        raise ValueError('신체 비율 참조 ID 형식 오류')
    current_legacy_style = current_request_values.pop('common_style', False)
    if type(current_legacy_style) is not bool:
        raise ValueError('이전 공용 화풍 옵션은 불리언이어야 합니다.')
    current_styled_prompt, current_style_record = compose_common_style_prompt(current_request_values.get('prompt'))
    current_request_values['prompt'] = current_styled_prompt
    current_validated_record = validate_qwen_plain_request(current_request_values)
    if current_body_reference_id is not None:
        from importlib import import_module
        current_reference_matches = import_module('generators.character-generator.body_references').identify_body_reference_images(current_validated_record['images'])
        current_selected_matches = [current_match for current_match in current_reference_matches if current_match['order'] == 1 and current_match['id'] == current_body_reference_id]
        if len(current_selected_matches) != 1:
            raise ValueError('첫 참조 이미지가 선택한 신체 기준과 다릅니다. 기준을 다시 적용하세요.')
        current_validated_record['body_reference_sources'] = current_selected_matches
    return {**current_validated_record, 'common_style_v1': current_style_record}


def verify_saved_common_style(current_request_record):
    current_style_record = current_request_record.get('common_style_v1')
    if current_style_record is None:
        return
    if not isinstance(current_style_record, dict) or set(current_style_record) != {'id', 'version', 'source', 'prompt', 'sha256', 'already_present', 'user_prompt'}:
        raise ValueError('저장된 공용 화풍 기록 형식 오류')
    if current_style_record['id'] != 'slime_common_art_style' or current_style_record['version'] != '1.5.0' or current_style_record['source'] != 'prompts/common/art-style-v1.5.0.yaml' or type(current_style_record['already_present']) is not bool or not isinstance(current_style_record['user_prompt'], str) or not isinstance(current_style_record['prompt'], str) or hashlib.sha256(current_style_record['prompt'].encode()).hexdigest() != current_style_record['sha256']:
        raise ValueError('저장된 공용 화풍 기록 무결성 오류')
    current_normalized_style = ' '.join(current_style_record['prompt'].split())
    current_original_prompt = current_style_record['user_prompt']
    current_contains_style = current_normalized_style in ' '.join(current_original_prompt.split())
    if current_contains_style != current_style_record['already_present']:
        raise ValueError('저장된 화풍 중복 정보가 일치하지 않습니다.')
    current_styled_prompt = current_original_prompt.strip() if current_contains_style else ' '.join(filter(None, (current_original_prompt.strip(), current_style_record['prompt'])))
    current_saved_prompt = current_request_record.get('qwen21', {}).get('user_prompt', current_request_record['prompt'])
    if current_styled_prompt != current_saved_prompt:
        raise ValueError('저장된 사용자 입력과 공용 화풍 조합이 일치하지 않습니다.')


class QwenPlainGenerationManager(ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/image-generation-21'
        self.job_storage_root = QWEN_GENERATION_ROOT
        self.reference_request_limit = 40_100_000

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/image/run_qwen_21_reference.py'

    def validate_generation_runtime(self, saved_request_record=None):
        validate_qwen_model_assets()
        validate_image_runtime(WORKFLOW_ROOT_PATH / '.venv')

    def validate_generation_request(self, request_record_value):
        return validate_styled_qwen_request(request_record_value)

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        verify_qwen_saved_request(selected_job_directory, current_request_record)

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'qwen-21'
