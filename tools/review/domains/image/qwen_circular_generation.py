"""공용 Qwen 작업 서비스를 사용하는 독립 순환 VAE 실험 생성기."""
from generators.image.qwen_21_circular import CIRCULAR_VAE_CONFIGURATION
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT


class QwenCircularGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/image-generation-21-circular'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/qwen-image-21-circular'

    def validate_generation_request(self, request_record_value):
        validated_request_record = super().validate_generation_request(request_record_value)
        validated_request_record['circular_vae'] = dict(CIRCULAR_VAE_CONFIGURATION)
        return validated_request_record

    def enrich_generation_status(self, current_job_root, current_status_record):
        for current_image_name in ('baseline', 'baseline-preview'):
            if (current_job_root / (current_image_name + '.png')).is_file():
                current_status_record[current_image_name] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/{current_image_name}.png'
        return current_status_record

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'qwen-21-circular'
