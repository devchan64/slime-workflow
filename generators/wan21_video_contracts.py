"""Strict request contracts for the separate Wan 2.1 video generators."""
import io
import math
from pathlib import Path
from PIL import Image
from workflow.domains.image.three_reference_generation import decode_reference_image

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
RUNTIME = ROOT / '.local/wan22-animate/ComfyUI'


def validate_request(request, mode):
    if mode not in ('t2v', 'i2v'):
        raise ValueError('지원하지 않는 영상 생성 종류입니다.')
    fields = {'action', 'prompt', 'negative_prompt', 'images', 'width', 'height', 'frames', 'steps', 'seed', 'flow_shift', 'guidance_scale', 'acceleration', 'action_lora', 'action_strength'}
    if not isinstance(request, dict) or not fields <= set(request) or set(request)-fields-{'action_variant'} or request.get('action') != 'generate':
        raise ValueError('영상 생성 요청 필드가 맞지 않습니다.')
    variant=request.get('action_variant','fight')
    if variant not in (('fight','attack_high','attack_low') if mode=='i2v' else ('fight',)):
        raise ValueError('지원하지 않는 동작 LoRA 종류입니다.')
    for name in ('prompt', 'negative_prompt'):
        if not isinstance(request[name], str) or len(request[name]) > 8000:
            raise ValueError('프롬프트는 8000자 이하 문자열이어야 합니다.')
    if not request['prompt'].strip():
        raise ValueError('프롬프트를 입력하세요.')
    for name, low, high in [('width',832,832), ('height',480,480), ('frames',5,129), ('steps',2,100), ('seed',0,2147483647)]:
        if type(request[name]) is not int or not low <= request[name] <= high:
            raise ValueError(f'{name} 범위가 올바르지 않습니다.')
    if (request['frames'] - 1) % 4:
        raise ValueError('프레임 수는 4n+1이어야 합니다.')
    for name, low, high in [('flow_shift',0.1,20), ('guidance_scale',1,10), ('action_strength',0,2)]:
        value=request[name]
        if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{name} 범위가 올바르지 않습니다.')
    if type(request['acceleration']) is not bool or type(request['action_lora']) is not bool:
        raise ValueError('LoRA 선택은 불리언이어야 합니다.')
    if request['acceleration'] and (request['steps'] != 4 or request['guidance_scale'] != 1):
        raise ValueError('4스텝 가속 LoRA는 4스텝과 CFG 1을 사용합니다.')
    if request['action_lora'] and request['action_strength'] <= 0:
        raise ValueError('동작 LoRA 강도는 0보다 커야 합니다.')
    images=request['images']
    if not isinstance(images,list) or len(images) != (1 if mode == 'i2v' else 0):
        raise ValueError('I2V는 첫 프레임 한 장이 필요하며 T2V는 이미지를 받지 않습니다.')
    if images:
        with Image.open(io.BytesIO(decode_reference_image(images[0]))) as image:
            if image.size != (832,480):
                raise ValueError('첫 프레임은 832×480 PNG여야 합니다.')
    return {**request, 'action_variant':variant, 'prompt':request['prompt'].strip(), 'tag':'wan21-'+mode}
