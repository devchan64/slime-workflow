"""빌보드 전용 Qwen 작업·이력. GPU 실행기는 공용으로 유지한다."""
from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT


class BillboardGuideGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/billboard-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/billboard-generator'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'billboard-generator'

    def validate_generation_request(self, current_request_record):
        current_validated_record = super().validate_generation_request(current_request_record)
        if not current_request_record.get('images'):
            raise ValueError('빌보드·건물 생성에는 첫 가이드 참조 이미지가 필요합니다.')
        return current_validated_record
