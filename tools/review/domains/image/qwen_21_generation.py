"""추가 프롬프트 없이 입력 원문을 사용하는 Qwen Image 2.1 서비스."""
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


def validate_qwen_plain_request(current_request_record):
    if isinstance(current_request_record, dict) and isinstance(current_request_record.get('images'), list):
        current_request_record = {**current_request_record, 'images': [
            base64.b64encode(decode_reference_image(current_image_text, composite_transparent_background=True)).decode()
            for current_image_text in current_request_record['images']
        ]}
    validated_request_record = validate_three_reference_request(current_request_record, allowed_inference_steps=QWEN_ALLOWED_INFERENCE_STEPS, maximum_reference_count=10)
    prompt_word_count = len(validated_request_record['prompt'].split())
    if not 0 < prompt_word_count < 100:
        raise ValueError('프롬프트는 1~99단어로 입력하세요. 자동 문구 추가·축약은 하지 않습니다.')
    return {**validated_request_record, 'qwen21': {
        'schema_version': 1, 'model_id': QWEN_MODEL_IDENTIFIER, 'revision': QWEN_MODEL_REVISION,
        'prompt_word_count': prompt_word_count,
        'prompt_sha256': hashlib.sha256(validated_request_record['prompt'].encode()).hexdigest(),
        'additional_prompt': '',
    }}


def verify_qwen_saved_request(current_job_root, current_request_record):
    verify_reference_snapshots(current_job_root, current_request_record)
    # 저장된 메타데이터도 동일한 입력 검증에서 다시 계산한다.
    import base64
    restored_input_record = {current_field_name: current_request_record[current_field_name]
        for current_field_name in ('action', 'prompt', 'tag', 'width', 'height', 'steps', 'seed')}
    restored_input_record['images'] = [base64.b64encode((current_job_root / current_reference_name).read_bytes()).decode()
        for current_reference_name in current_request_record['references']]
    expected_source_record = validate_qwen_plain_request(restored_input_record)['qwen21']
    if current_request_record.get('qwen21') != expected_source_record:
        raise ValueError('Qwen 2.1 실행 기록의 모델·프롬프트 정보가 일치하지 않습니다.')


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
        validate_image_runtime(WORKFLOW_ROOT_PATH / '.venv-qwen21')

    def validate_generation_request(self, request_record_value):
        return validate_qwen_plain_request(request_record_value)

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory / 'request.json').read_text())
        verify_qwen_saved_request(selected_job_directory, current_request_record)

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'qwen-21'
