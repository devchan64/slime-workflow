"""바디 한 장과 아웃핏 한 장을 사용하는 Qwen 2.1 생성 서비스."""
import json
from pathlib import Path

from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, validate_qwen_plain_request, verify_qwen_saved_request
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
OUTFIT_TRANSFER_STORAGE_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/outfit-transfer'
OUTFIT_TRANSFER_PROMPT_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/config/outfit-transfer-prompt.txt'
OUTFIT_TRANSFER_ALLOWED_SIZES = (512, 768)


def load_outfit_transfer_prompt():
    prompt_source_text = OUTFIT_TRANSFER_PROMPT_PATH.read_text().strip()
    if not 0 < len(prompt_source_text.split()) < 100:
        raise ValueError('복장 착용 기본 프롬프트는 1~99단어여야 합니다.')
    return prompt_source_text


def validate_outfit_transfer_contract(current_request_record, saved_request_enabled=False):
    if not isinstance(current_request_record, dict):
        raise ValueError('복장 착용 요청은 객체여야 합니다.')
    reference_image_values = current_request_record.get('references' if saved_request_enabled else 'images')
    if not isinstance(reference_image_values, list) or len(reference_image_values) != 2:
        raise ValueError('바디 이미지 1장과 아웃핏 이미지 1장을 순서대로 입력하세요.')
    selected_width_value = current_request_record.get('width')
    selected_height_value = current_request_record.get('height')
    if type(selected_width_value) is not int or selected_width_value not in OUTFIT_TRANSFER_ALLOWED_SIZES or type(selected_height_value) is not int or selected_height_value != selected_width_value:
        raise ValueError('해상도는 512×512 또는 768×768만 지원합니다.')


class OutfitTransferGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/outfit-transfer'
        self.job_storage_root = OUTFIT_TRANSFER_STORAGE_ROOT

    def validate_generation_request(self, current_request_record):
        validate_outfit_transfer_contract(current_request_record)
        return validate_qwen_plain_request(current_request_record)

    def validate_generation_resume(self, selected_job_directory):
        saved_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        validate_outfit_transfer_contract(saved_request_record, saved_request_enabled=True)
        verify_qwen_saved_request(selected_job_directory, saved_request_record)

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'outfit-transfer'
