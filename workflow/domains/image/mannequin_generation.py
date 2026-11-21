"""마네킨 전용 Qwen 작업과 이력. GPU 실행기는 공용으로 유지한다."""
from workflow.domains.image.qwen_21_generation import QwenPlainGenerationManager, WORKFLOW_ROOT_PATH
from workflow.domains.image.image_generation import MANAGER_HISTORY_ROOT


class MannequinGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/mannequin-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test/mannequin-generator'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'mannequin-generator'
