"""VNCCS 신규 작업의 고정 실행 계약. 과거 포즈 변환 기록과 구분한다."""
import hashlib
from pathlib import Path

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
VNCCS_LORA_RELATIVE_PATH = '.model/vnccs-posestudio-qi21/VNCCS_QI2_PoseStudioV1.1-diffusers.safetensors'
VNCCS_LORA_EXPECTED_DIGEST = '12412b65e5799c15e6e6bc4e42430715ecd6a606f3eb520853dfb874be94cf13'
VNCCS_EXECUTION_PROFILE = {
    'schema_version': 1, 'pipeline': 'QwenImage21Pipeline', 'dtype': 'bfloat16',
    'quantization': 'none', 'offload': 'sequential-cpu-weights-cuda-compute',
    'resolution': 512, 'steps': 40, 'output_resolution': 512,
    'reference_order': ['pose', 'identity'], 'lora_path': VNCCS_LORA_RELATIVE_PATH,
    'lora_sha256': VNCCS_LORA_EXPECTED_DIGEST, 'lora_scale': 1.0,
    'minimum_available_bytes': 12 * 1024**3, 'maximum_rss_bytes': 42 * 1024**3,
    'maximum_seconds': 1200,
}
VNCCS_QUALITY_WARNING_TEXT = '실험 단계: 공식 포즈 일부도 부분 추종합니다. 전신 비례·포즈·프레임 일관성의 품질 승인은 별도 검수가 필요합니다.'


def build_vnccs_profile():
    return {**VNCCS_EXECUTION_PROFILE, 'reference_order': list(VNCCS_EXECUTION_PROFILE['reference_order'])}


def validate_vnccs_profile(current_request_record):
    if current_request_record.get('vnccs') != VNCCS_EXECUTION_PROFILE:
        raise ValueError('VNCCS 실행 버전·정밀도·모델·참조 순서 설정이 일치하지 않습니다.')
    if any(type(current_request_record.get(current_field_name)) is not int or current_request_record[current_field_name] != current_expected_value for current_field_name, current_expected_value in (('width',512),('height',512),('steps',40))):
        raise ValueError('신규 VNCCS 생성은 512×512·40스텝 고정입니다.')


def validate_vnccs_assets():
    current_lora_path = WORKFLOW_ROOT_DIRECTORY / VNCCS_LORA_RELATIVE_PATH
    if not current_lora_path.is_file():
        raise FileNotFoundError(f'VNCCS V1.1 LoRA 준비 필요: {current_lora_path}')
    with current_lora_path.open('rb') as current_lora_stream:
        current_file_digest = hashlib.file_digest(current_lora_stream, 'sha256').hexdigest()
    if current_file_digest != VNCCS_LORA_EXPECTED_DIGEST:
        raise ValueError('VNCCS V1.1 LoRA SHA-256 불일치')
    return current_lora_path
