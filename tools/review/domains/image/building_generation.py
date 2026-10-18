"""건물 전용 Qwen 작업·이력 저장소. GPU 실행 잠금은 공용 실행기를 사용한다."""
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT

BUILDING_GENERATION_STORAGE = WORKFLOW_ROOT_PATH / '.tmp/test/building-generator'


class BuildingGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/building-generator'
        self.job_storage_root = BUILDING_GENERATION_STORAGE

    def validate_generation_request(self, current_request_record):
        current_validated_record = super().validate_generation_request(current_request_record)
        if not current_request_record.get('images'):
            raise ValueError('건물 생성에는 첫 레이아웃 참조 이미지가 필요합니다.')
        return current_validated_record

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'building-generator'
