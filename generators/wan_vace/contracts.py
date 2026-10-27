"""VACE-Fun 고정 가중치와 GUI·CLI 공용 입력 계약."""
from pathlib import Path
import hashlib
import io
import math
from PIL import Image
from tools.review.domains.image.three_reference_generation import decode_reference_image

VACE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
VACE_JOB_STORAGE = VACE_WORKSPACE_ROOT / '.tmp/test/wan22-vace'
VACE_RUNTIME_DIRECTORY = VACE_WORKSPACE_ROOT / '.local/wan22-animate'
VACE_MODEL_IDENTIFIER = 'QuantStack/Wan2.2-VACE-Fun-A14B-GGUF'
VACE_MODEL_REVISION = '93b339260b1d819e2c171dd7ca9e66a761d4a84d'
VACE_SOURCE_REVISION = '13bb3c625e8b1e457d7124d92207b49e00e4a6fe'
VACE_MODEL_FILES = {
    'high': ('.model/wan22-vace/HighNoise/Wan2.2-VACE-Fun-A14B-high-noise-Q4_K_M.gguf', 11639453600, '46584a1be3a01d50cfdb7b4e326d01f9a4ef9ddeb2a85b6df8bcd5f5f874916c'),
    'low': ('.model/wan22-vace/LowNoise/Wan2.2-VACE-Fun-A14B-low-noise-Q4_K_M.gguf', 11639453600, 'efa88568f8a8fec0b7e3867db40b8c940b95bcfcf5543cf9fb8db8c5aca1dac2'),
    'encoder': ('.model/wan22-animate-components/umt5-xxl-encoder-Q4_K_M.gguf', 3655145312, None),
    'vae': ('.model/wan22-animate-components/split_files/vae/wan_2.1_vae.safetensors', 253815318, None),
}
VACE_RUNTIME_REVISIONS = {'ComfyUI': 'b8730510db30c8858e1e5d8e126ef19eac395560', 'ComfyUI-GGUF': '6ea2651e7df66d7585f6ffee804b20e92fb38b8a'}
VACE_DEFAULT_SETTINGS = {'mode': 'reference', 'frames': 21, 'steps': 50, 'seed': 42, 'flow_shift': 12.0, 'guidance_scale': 5.0, 'reference_strength': 1.0}
VACE_EXPERT_BOUNDARY = 0.875
VACE_INPUT_MODES = ('text', 'reference', 'first_frame')


def inspect_vace_assets():
    missing_model_paths = []
    for current_model_name, expected_model_size, expected_model_hash in VACE_MODEL_FILES.values():
        current_model_path = VACE_WORKSPACE_ROOT / current_model_name
        if not current_model_path.is_file() or current_model_path.stat().st_size != expected_model_size:
            missing_model_paths.append(current_model_name)
    for current_runtime_name, expected_revision_text in VACE_RUNTIME_REVISIONS.items():
        current_revision_path = VACE_RUNTIME_DIRECTORY / current_runtime_name / 'PINNED_REVISION'
        if not current_revision_path.is_file() or current_revision_path.read_text().strip() != expected_revision_text:
            missing_model_paths.append(str(current_revision_path))
    return {'ready': not missing_model_paths, 'missing': missing_model_paths, 'message': '모델 파일 준비 완료 · 8GB 실행·품질은 별도 검수' if not missing_model_paths else '모델 준비 필요: ' + ', '.join(missing_model_paths)}


def validate_vace_assets():
    current_asset_status = inspect_vace_assets()
    if not current_asset_status['ready']:
        raise ValueError(current_asset_status['message'])


def verify_vace_weights():
    """실제 추론 전 전용 가중치의 스트리밍 해시를 확인한다."""
    validate_vace_assets()
    for current_model_name, expected_model_size, expected_model_hash in VACE_MODEL_FILES.values():
        if expected_model_hash is None:
            continue
        with (VACE_WORKSPACE_ROOT / current_model_name).open('rb') as current_model_stream:
            current_model_digest = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
        if current_model_digest != expected_model_hash:
            raise ValueError(f'모델 SHA-256 불일치: {current_model_name}')


def validate_vace_request(current_request_record):
    required_field_names = {'action', 'mode', 'prompt', 'negative_prompt', 'images', 'width', 'height', 'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale', 'reference_strength'}
    if not isinstance(current_request_record, dict) or set(current_request_record) != required_field_names:
        raise ValueError('VACE 요청 필드가 맞지 않습니다.')
    if current_request_record['action'] != 'generate' or current_request_record['mode'] not in VACE_INPUT_MODES:
        raise ValueError('generate와 text/reference/first_frame 모드가 필요합니다.')
    for current_field_name in ('prompt', 'negative_prompt'):
        if not isinstance(current_request_record[current_field_name], str) or len(current_request_record[current_field_name]) > 8000:
            raise ValueError('프롬프트는 8000자 이하 문자열이어야 합니다.')
    if not current_request_record['prompt'].strip():
        raise ValueError('장면·동작 프롬프트를 입력하세요.')
    for current_field_name, minimum_field_value, maximum_field_value in [('frames', 5, 81), ('steps', 2, 100), ('seed', 0, 2147483647), ('width', 832, 832), ('height', 480, 480)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) is not int or not minimum_field_value <= current_field_value <= maximum_field_value:
            raise ValueError(f'{current_field_name}: {minimum_field_value}~{maximum_field_value} 정수가 필요합니다.')
    if (current_request_record['frames'] - 1) % 4:
        raise ValueError('프레임 수는 4n+1이어야 합니다.')
    for current_field_name, minimum_field_value, maximum_field_value in [('flow_shift', 0.1, 20), ('guidance_scale', 1, 10), ('reference_strength', 0.1, 2)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) not in (int, float) or not math.isfinite(current_field_value) or not minimum_field_value <= current_field_value <= maximum_field_value:
            raise ValueError(f'{current_field_name}: {minimum_field_value}~{maximum_field_value} 범위가 필요합니다.')
    expected_image_count = 0 if current_request_record['mode'] == 'text' else 1
    if not isinstance(current_request_record['images'], list) or len(current_request_record['images']) != expected_image_count:
        raise ValueError('텍스트 모드는 이미지 0장, 외형 참조·첫 프레임 모드는 이미지 1장이 필요합니다.')
    for current_image_text in current_request_record['images']:
        with Image.open(io.BytesIO(decode_reference_image(current_image_text))) as current_image_object:
            if current_image_object.size != (832, 480):
                raise ValueError('입력은 832×480 PNG여야 합니다.')
    return {**current_request_record, 'prompt': current_request_record['prompt'].strip(), 'tag': 'wan22-vace'}


def locate_expert_switch(current_sigma_values):
    """제작자 t >= 875 고노이즈 조건을 sigma >= 0.875로 적용한다."""
    current_switch_index = sum(float(current_sigma_value) >= VACE_EXPERT_BOUNDARY for current_sigma_value in current_sigma_values[:-1])
    if not 0 < current_switch_index < len(current_sigma_values) - 1:
        raise ValueError('현재 스케줄은 고·저노이즈 양쪽 단계를 포함하지 않습니다. 스텝·Shift를 조정하세요.')
    return current_switch_index
