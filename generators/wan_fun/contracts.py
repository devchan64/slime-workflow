"""Fun Control 고정 모델과 GUI·CLI 공용 입력 계약."""
from pathlib import Path
import io
import math
from PIL import Image
from tools.review.domains.image.three_reference_generation import decode_reference_image

FUN_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
FUN_JOB_STORAGE = FUN_WORKSPACE_ROOT / '.tmp/test/wan22-fun-control'
FUN_RUNTIME_DIRECTORY = FUN_WORKSPACE_ROOT / '.local/wan22-animate'
FUN_MODEL_REVISION = '26d412a4bec09e1324fc80654dcee0d58218db52'
FUN_MODEL_FILES = {
    'high': ('.model/wan22-fun-control/HighNoise/Wan2.2-Fun-A14B-Control_HighNoise-Q4_K_M.gguf', 9663556352),
    'low': ('.model/wan22-fun-control/LowNoise/Wan2.2-Fun-A14B-Control_LowNoise-Q4_K_M.gguf', 9663556352),
    'encoder': ('.model/wan22-animate-components/umt5-xxl-encoder-Q4_K_M.gguf', 3655145312),
    'vae': ('.model/wan22-animate-components/split_files/vae/wan_2.1_vae.safetensors', 253815318),
}
FUN_DEFAULT_SETTINGS = {'frames': 21, 'steps': 20, 'seed': 42, 'flow_shift': 5.0, 'guidance_scale': 6.0, 'switch_ratio': 0.5}
FUN_CONTROL_TYPES = ('pose', 'depth', 'canny', 'mlsd')


def inspect_fun_assets():
    missing_model_paths = []
    for current_model_name, expected_model_size in FUN_MODEL_FILES.values():
        current_model_path = FUN_WORKSPACE_ROOT / current_model_name
        if not current_model_path.is_file() or current_model_path.stat().st_size != expected_model_size:
            missing_model_paths.append(current_model_name)
    for current_runtime_name, expected_revision_text in [('ComfyUI', 'b8730510db30c8858e1e5d8e126ef19eac395560'), ('ComfyUI-GGUF', '6ea2651e7df66d7585f6ffee804b20e92fb38b8a')]:
        current_revision_path = FUN_RUNTIME_DIRECTORY / current_runtime_name / 'PINNED_REVISION'
        if not current_revision_path.is_file() or current_revision_path.read_text().strip() != expected_revision_text:
            missing_model_paths.append(str(current_revision_path))
    return {'ready': not missing_model_paths, 'missing': missing_model_paths, 'message': '모델 준비 완료 · 8GB 추론 미검증' if not missing_model_paths else '모델 준비 필요: ' + ', '.join(missing_model_paths)}


def validate_fun_assets():
    current_asset_status = inspect_fun_assets()
    if not current_asset_status['ready']:
        raise ValueError(current_asset_status['message'])


def validate_fun_request(current_request_record):
    required_field_names = {'action', 'prompt', 'negative_prompt', 'images', 'width', 'height', 'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale', 'switch_ratio', 'control_type'}
    if not isinstance(current_request_record, dict) or set(current_request_record) != required_field_names:
        raise ValueError('Fun Control 요청 필드가 맞지 않습니다.')
    if current_request_record['action'] != 'generate':
        raise ValueError('generate 요청이 필요합니다.')
    for current_field_name in ('prompt', 'negative_prompt'):
        if not isinstance(current_request_record[current_field_name], str) or len(current_request_record[current_field_name]) > 8000:
            raise ValueError('프롬프트는 8000자 이하 문자열이어야 합니다.')
    if not current_request_record['prompt'].strip():
        raise ValueError('장면 프롬프트를 입력하세요.')
    for current_field_name, minimum_field_value, maximum_field_value in [('frames', 5, 81), ('steps', 2, 100), ('seed', 0, 2147483647), ('width', 832, 832), ('height', 480, 480)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) is not int or not minimum_field_value <= current_field_value <= maximum_field_value:
            raise ValueError(f'{current_field_name}: {minimum_field_value}~{maximum_field_value} 정수가 필요합니다.')
    if (current_request_record['frames'] - 1) % 4:
        raise ValueError('프레임 수는 4n+1이어야 합니다.')
    for current_field_name, minimum_field_value, maximum_field_value in [('flow_shift', 0.1, 20), ('guidance_scale', 1, 10), ('switch_ratio', 0.1, 0.9)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) not in (int, float) or not math.isfinite(current_field_value) or not minimum_field_value <= current_field_value <= maximum_field_value:
            raise ValueError(f'{current_field_name}: {minimum_field_value}~{maximum_field_value} 범위가 필요합니다.')
    if current_request_record['control_type'] not in FUN_CONTROL_TYPES:
        raise ValueError('제어 영상 종류를 확인하세요.')
    if not isinstance(current_request_record['images'], list) or len(current_request_record['images']) != current_request_record['frames'] + 1:
        raise ValueError('외형 참조 1장과 출력 프레임 수만큼의 제어 프레임이 필요합니다.')
    for current_image_text in current_request_record['images']:
        with Image.open(io.BytesIO(decode_reference_image(current_image_text))) as current_image_object:
            if current_image_object.format != 'PNG' or current_image_object.size != (832, 480):
                raise ValueError('모든 입력은 832×480 PNG여야 합니다.')
    return {**current_request_record, 'prompt': current_request_record['prompt'].strip(), 'tag': 'wan22-fun-control'}
