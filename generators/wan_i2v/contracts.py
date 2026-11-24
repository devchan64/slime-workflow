"""Wan 2.2 I2V의 독립 요청 및 준비 상태 계약."""
from pathlib import Path
import io
import math
from PIL import Image
from generators.wan_i2v.assets import ROOT, DIRECTORY, FILES, inspect_assets
from workflow.domains.image.three_reference_generation import decode_reference_image

JOB_STORAGE = ROOT / '.tmp/test/wan22-i2v'
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
RUNTIME = ROOT / '.local/wan22-animate/ComfyUI'
SHARED_FILES = (
    (ROOT / '.model/wan22-animate-components/split_files/text_encoders/umt5_xxl_fp16.safetensors', 11366399385),
    (ROOT / '.model/wan22-animate-components/split_files/vae/wan_2.1_vae.safetensors', 253815318),
)
COMFY_REVISION = 'b8730510db30c8858e1e5d8e126ef19eac395560'


def inspect_runtime(*, verify_hash=False):
    missing = []
    for path, size in SHARED_FILES:
        try:
            if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                missing.append(str(path))
        except OSError:
            missing.append(str(path))
    if not PYTHON.is_file():
        missing.append(str(PYTHON))
    try:
        if (RUNTIME / 'PINNED_REVISION').read_text().strip() != COMFY_REVISION:
            missing.append('ComfyUI 고정 리비전 불일치')
    except OSError:
        missing.append('ComfyUI 고정 리비전 확인 불가')
    def files_present():
        for relative, _, _, _, size, _ in FILES:
            path = DIRECTORY / relative
            try:
                if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
                    return False
            except OSError:
                return False
        return True
    if not (inspect_assets() if verify_hash else files_present()):
        missing.append('Wan 2.2 I2V 및 LoRA 파일')
    return {'ready': not missing, 'missing': missing, 'message': ('파일 크기 확인 완료 · SHA-256은 실행 시 확인 · GPU 실행과 품질은 별도 검증' if not verify_hash else '파일 SHA-256 확인 완료 · GPU 실행과 품질은 별도 검증') if not missing else '준비 필요: ' + ', '.join(missing)}


def validate_request(request):
    fields = {'action', 'prompt', 'negative_prompt', 'images', 'width', 'height', 'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale', 'lora_mode', 'kungfu_strength'}
    if not isinstance(request, dict) or set(request) != fields or request['action'] != 'generate':
        raise ValueError('I2V 요청 필드가 맞지 않습니다.')
    for name in ('prompt', 'negative_prompt'):
        if not isinstance(request[name], str) or len(request[name]) > 8000:
            raise ValueError('프롬프트는 8000자 이하 문자열이어야 합니다.')
    if not request['prompt'].strip():
        raise ValueError('동작 프롬프트를 입력하세요.')
    for name, minimum, maximum in [('width', 832, 832), ('height', 480, 480), ('frames', 5, 129), ('steps', 2, 100), ('seed', 0, 2147483647)]:
        if type(request[name]) is not int or not minimum <= request[name] <= maximum:
            raise ValueError(f'{name} 범위가 올바르지 않습니다.')
    if (request['frames'] - 1) % 4:
        raise ValueError('프레임 수는 4n+1이어야 합니다.')
    for name, minimum, maximum in [('flow_shift', 0.1, 20), ('guidance_scale', 1, 10), ('kungfu_strength', 0, 2)]:
        value = request[name]
        if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f'{name} 범위가 올바르지 않습니다.')
    if request['lora_mode'] not in ('none', 'lightning'):
        raise ValueError('지원하지 않는 LoRA 조합입니다.')
    if 'lightning' in request['lora_mode'] and (request['steps'] != 4 or request['guidance_scale'] != 1):
        raise ValueError('Lightning 실험은 4스텝과 CFG 1을 사용합니다.')
    if not isinstance(request['images'], list) or len(request['images']) != 1:
        raise ValueError('첫 프레임 이미지 한 장이 필요합니다.')
    with Image.open(io.BytesIO(decode_reference_image(request['images'][0]))) as image:
        if image.size != (832, 480):
            raise ValueError('첫 프레임은 832×480 PNG여야 합니다.')
    return {**request, 'prompt': request['prompt'].strip(), 'tag': 'wan22-i2v'}
