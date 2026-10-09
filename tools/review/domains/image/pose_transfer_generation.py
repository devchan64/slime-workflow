"""아이덴티티 한 장과 포즈 한 장을 사용하는 Qwen 2.1 생성 서비스."""
import json
from pathlib import Path

from tools.review.domains.image.qwen_21_generation import QwenPlainGenerationManager, validate_qwen_plain_request, verify_qwen_saved_request
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT
from generators.image.vnccs_profile import build_vnccs_profile, validate_vnccs_profile, validate_vnccs_assets

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
POSE_TRANSFER_STORAGE_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/pose-transfer'
POSE_TRANSFER_PROMPT_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/config/pose-transfer-prompt.txt'
POSE_TRANSFER_ALLOWED_SIZES = (512, 768)


def load_pose_transfer_prompt():
    prompt_source_text = POSE_TRANSFER_PROMPT_PATH.read_text().strip()
    if not 0 < len(prompt_source_text.split()) < 100:
        raise ValueError('포즈 변환 기본 프롬프트는 1~99단어여야 합니다.')
    return prompt_source_text


def validate_pose_transfer_contract(current_request_record, saved_request_enabled=False):
    if not isinstance(current_request_record, dict):
        raise ValueError('포즈 변환 요청은 객체여야 합니다.')
    reference_image_values = current_request_record.get('references' if saved_request_enabled else 'images')
    if not isinstance(reference_image_values, list) or len(reference_image_values) != 2:
        raise ValueError('아이덴티티 이미지 1장과 포즈 이미지 1장을 순서대로 입력하세요.')
    selected_width_value = current_request_record.get('width')
    selected_height_value = current_request_record.get('height')
    if type(selected_width_value) is not int or selected_width_value not in POSE_TRANSFER_ALLOWED_SIZES or type(selected_height_value) is not int or selected_height_value != selected_width_value:
        raise ValueError('해상도는 512×512 또는 768×768만 지원합니다.')
    if not saved_request_enabled or 'vnccs' in current_request_record:
        validate_vnccs_profile(current_request_record if saved_request_enabled else {**current_request_record, 'vnccs': build_vnccs_profile(current_request_record.get('steps'))})


class PoseTransferGenerationManager(QwenPlainGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/pose-transfer'
        self.job_storage_root = POSE_TRANSFER_STORAGE_ROOT

    def validate_generation_request(self, current_request_record):
        validate_pose_transfer_contract(current_request_record)
        return {**validate_qwen_plain_request(current_request_record, allowed_inference_steps=(25, 40)), 'vnccs': build_vnccs_profile(current_request_record['steps'])}

    def validate_generation_runtime(self, saved_request_record=None):
        super().validate_generation_runtime(saved_request_record)
        if saved_request_record is None or 'vnccs' in saved_request_record:
            validate_vnccs_assets()

    def validate_generation_resume(self, selected_job_directory):
        saved_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        validate_pose_transfer_contract(saved_request_record, saved_request_enabled=True)
        verify_qwen_saved_request(selected_job_directory, saved_request_record)

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'pose-transfer'
