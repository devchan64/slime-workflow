"""공용 Qwen 작업 서비스를 사용하는 독립 순환 VAE 실험 생성기."""
from generators.image.qwen_21_circular import build_circular_configuration, CIRCULAR_SOFT_SHADING_PROMPT, CIRCULAR_PATTERN_VIEW_PROMPT
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT


class QwenCircularGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/image-generation-21-circular'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/qwen-image-21-circular'

    def validate_generation_request(self, request_record_value):
        soft_shading_enabled = request_record_value.get('soft_shading', False)
        if type(soft_shading_enabled) is not bool:
            raise ValueError('부드러운 음영 옵션은 ON/OFF 값이어야 합니다.')
        pattern_view_enabled = request_record_value.get('pattern_view', True)
        if type(pattern_view_enabled) is not bool:
            raise ValueError('패턴 시점 옵션은 ON/OFF 값이어야 합니다.')
        user_prompt_text = request_record_value.get('prompt', '')
        prepared_request_record = {current_field_name: current_field_value for current_field_name, current_field_value in request_record_value.items() if current_field_name not in ('circular_radius', 'soft_shading', 'pattern_view', 'baseline_decode')}
        prepared_request_record['prompt'] = ' '.join(current_prompt_part for current_prompt_part in (user_prompt_text.strip(), CIRCULAR_PATTERN_VIEW_PROMPT if pattern_view_enabled else '', CIRCULAR_SOFT_SHADING_PROMPT if soft_shading_enabled else '') if current_prompt_part)
        validated_request_record = super().validate_generation_request(prepared_request_record)
        validated_request_record['pattern_view'] = pattern_view_enabled
        validated_request_record['soft_shading'] = soft_shading_enabled
        validated_request_record['user_prompt'] = user_prompt_text
        if validated_request_record.get('images') or validated_request_record.get('references'):
            raise ValueError('순환 Attention 실험은 참조 없이 프롬프트만 입력하세요.')
        validated_request_record['circular_vae'] = build_circular_configuration(request_record_value.get('circular_radius', 12), request_record_value.get('baseline_decode', False))
        return validated_request_record

    def enrich_generation_status(self, current_job_root, current_status_record):
        for current_image_name in ('baseline', 'baseline-preview'):
            if (current_job_root / (current_image_name + '.png')).is_file():
                current_status_record[current_image_name] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/{current_image_name}.png'
        return current_status_record

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'qwen-21-circular'
