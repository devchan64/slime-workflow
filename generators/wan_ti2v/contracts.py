"""Wan2.2 TI2V 5B의 고정 모델·입력 계약."""
from pathlib import Path
import io
import math

from PIL import Image

from tools.review.domains.image.three_reference_generation import decode_reference_image

TI2V_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
TI2V_JOB_STORAGE = TI2V_WORKSPACE_ROOT / '.tmp/test/wan22-ti2v'
TI2V_RUNTIME_DIRECTORY = TI2V_WORKSPACE_ROOT / '.local/wan22-animate'
TI2V_MODEL_FILES = {
    'diffusion': '.model/wan22-ti2v/diffusion_models/Wan2.2-TI2V-5B-Q4_K_M.gguf',
    'encoder': '.model/wan22-animate-components/umt5-xxl-encoder-Q4_K_M.gguf',
    'vae': '.model/wan22-ti2v/vae/wan2.2_vae.safetensors',
}
TI2V_RUNTIME_REVISION = 'b8730510db30c8858e1e5d8e126ef19eac395560'
TI2V_DEFAULT_SETTINGS = {'frames': 21, 'steps': 20, 'seed': 42, 'flow_shift': 8.0, 'guidance_scale': 5.0}
TI2V_MODEL_IDENTIFIER = 'QuantStack/Wan2.2-TI2V-5B-GGUF'
TI2V_MODEL_REVISION = '57437632ddd08bdcbd1508c866aa22e126ed51d2'
TI2V_GGUF_REVISION = '6ea2651e7df66d7585f6ffee804b20e92fb38b8a'
TI2V_MODEL_SIZES = {'diffusion': 3433116000, 'encoder': 3655145312, 'vae': 1409400960}
TI2V_DOWNLOAD_RECORDS = {
    'diffusion': ('Wan2.2-TI2V-5B-Q4_K_M.gguf', '95b19697b7f98e65b0a543640e9ca7b4dfec32e2a6e3731e8e10708be52655e2'),
    'vae': ('VAE/Wan2.2_VAE.safetensors', 'e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156'),
}


def inspect_ti2v_assets():
    missing_asset_paths = []
    for current_model_name, current_relative_path in TI2V_MODEL_FILES.items():
        current_model_path = TI2V_WORKSPACE_ROOT / current_relative_path
        if not current_model_path.is_file() or current_model_path.stat().st_size != TI2V_MODEL_SIZES[current_model_name]:
            missing_asset_paths.append(current_relative_path)
    for current_runtime_name, current_expected_revision in (('ComfyUI', TI2V_RUNTIME_REVISION), ('ComfyUI-GGUF', TI2V_GGUF_REVISION)):
        current_revision_path = TI2V_RUNTIME_DIRECTORY / current_runtime_name / 'PINNED_REVISION'
        if not current_revision_path.is_file() or current_revision_path.read_text().strip() != current_expected_revision:
            missing_asset_paths.append(str(current_revision_path))
    current_ready_value = not missing_asset_paths
    return {
        'ready': current_ready_value,
        'missing': missing_asset_paths,
        'message': ('모델 준비 완료 · TI2V 5B Q4_K_M · 8GB 대상 실험 구성 · 입력별 실행 검증 필요' if current_ready_value else '모델 준비 필요: ' + ', '.join(missing_asset_paths)),
    }


def validate_ti2v_assets():
    current_asset_status = inspect_ti2v_assets()
    if not current_asset_status['ready']:
        raise ValueError(current_asset_status['message'])


def validate_ti2v_request(current_request_record):
    required_field_names = {'action', 'prompt', 'negative_prompt', 'images', 'width', 'height', 'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale'}
    if not isinstance(current_request_record, dict) or set(current_request_record) != required_field_names:
        raise ValueError('Wan2.2 TI2V 요청 필드가 맞지 않습니다.')
    if current_request_record['action'] != 'generate':
        raise ValueError('generate 요청이 필요합니다.')
    for current_text_name in ('prompt', 'negative_prompt'):
        current_text_value = current_request_record[current_text_name]
        if not isinstance(current_text_value, str) or len(current_text_value) > 8000:
            raise ValueError('프롬프트는 8000자 이하 문자열이어야 합니다.')
    if not current_request_record['prompt'].strip():
        raise ValueError('장면·동작 프롬프트를 입력하세요.')
    if len(current_request_record['prompt'].split()) >= 100:
        raise ValueError('최종 프롬프트는 100단어 미만이어야 합니다.')
    for current_name, minimum_value, maximum_value in (('width', 832, 832), ('height', 480, 480), ('frames', 5, 81), ('steps', 2, 50), ('seed', 0, 2147483647)):
        current_value = current_request_record[current_name]
        if type(current_value) is not int or not minimum_value <= current_value <= maximum_value:
            raise ValueError(f'{current_name}: {minimum_value}~{maximum_value} 정수가 필요합니다.')
    if (current_request_record['frames'] - 1) % 4:
        raise ValueError('프레임 수는 4n+1이어야 합니다.')
    for current_name, minimum_value, maximum_value in (('flow_shift', 0.1, 20.0), ('guidance_scale', 1.0, 10.0)):
        current_value = current_request_record[current_name]
        if type(current_value) not in (int, float) or not math.isfinite(current_value) or not minimum_value <= current_value <= maximum_value:
            raise ValueError(f'{current_name}: {minimum_value}~{maximum_value} 범위가 필요합니다.')
    if not isinstance(current_request_record['images'], list) or len(current_request_record['images']) > 1:
        raise ValueError('텍스트 생성은 기준 이미지 0장, 이미지 조건 생성은 1장만 허용합니다.')
    for current_image_text in current_request_record['images']:
        with Image.open(io.BytesIO(decode_reference_image(current_image_text))) as current_image_object:
            if current_image_object.format != 'PNG' or current_image_object.size != (832, 480):
                raise ValueError('기준 이미지는 832×480 RGB/RGBA PNG여야 합니다.')
    return {**current_request_record, 'prompt': current_request_record['prompt'].strip(), 'tag': 'wan22-ti2v'}
