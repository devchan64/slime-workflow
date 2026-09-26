"""Qwen 2511 고정 참조 입력의 검증·작업 저장."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import base64
import binascii
import io
from PIL import Image

REFERENCE_IMAGE_LIMIT = 3_000_000
WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[4]
ALLOWED_REFERENCE_JOB_ROOTS = (
    WORKFLOW_ROOT_PATH/'.tmp/test/qwen-image-2511-three-reference',
    WORKFLOW_ROOT_PATH/'.tmp/test/qwen-image-2512/tile-map',
)


def validate_three_reference_job_path(current_job_root):
    resolved_job_root = Path(current_job_root).resolve()
    if not any(resolved_job_root.is_relative_to(allowed_job_root) for allowed_job_root in ALLOWED_REFERENCE_JOB_ROOTS):
        raise ValueError('작업 경로 오류')
    return resolved_job_root


def validate_three_reference_request(current_request_record):
    if isinstance(current_request_record,dict) and current_request_record.get('action')=='generate':
        current_request_record=dict(current_request_record)
        current_request_record.setdefault('seed',10107)
        if type(current_request_record['seed']) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('seed는 0~4294967295 범위의 정수여야 합니다.')
    if not isinstance(current_request_record,dict) or set(current_request_record)!={'action','prompt','images','steps','width','height','seed'} or current_request_record['action']!='generate':
        raise ValueError('3참조 요청 필드 오류')
    if not isinstance(current_request_record['prompt'],str) or not 1<=len(current_request_record['prompt'].strip())<=8000:
        raise ValueError('프롬프트는 1~8000자여야 합니다.')
    if not isinstance(current_request_record['images'],list) or not 0 <= len(current_request_record['images']) <= 3:
        raise ValueError('텍스트 생성은 참조 0장, 참조 생성은 1~3장이 필요합니다.')
    for current_size_key in ('width','height'):
        current_size_value=current_request_record[current_size_key]
        if type(current_size_value) is not int or not 256 <= current_size_value <= 1664 or current_size_value % 16:
            raise ValueError('출력 크기는 256~1664 범위의 16 배수여야 합니다.')
    resolve_reference_settings(current_request_record['steps'])
    for current_image_text in current_request_record['images']:
        decode_reference_image(current_image_text)
    return current_request_record


def decode_reference_image(current_image_text):
    if not isinstance(current_image_text,str) or len(current_image_text)>REFERENCE_IMAGE_LIMIT*4//3+4:
        raise ValueError('참조 이미지 크기 제한 초과')
    try:
        current_image_bytes=base64.b64decode(current_image_text,validate=True)
        with Image.open(io.BytesIO(current_image_bytes)) as current_image_value:
            if current_image_value.format!='PNG' or current_image_value.size!=(512,512) or current_image_value.mode not in ('RGB','RGBA'):
                raise ValueError('참조는 512×512 RGB/RGBA PNG여야 합니다.')
            current_image_value.load()
            if current_image_value.mode=='RGBA' and current_image_value.getextrema()[3]!=(255,255):
                raise ValueError('투명 이미지는 배경을 합성한 뒤 입력하세요.')
    except (binascii.Error,OSError) as current_error_value:
        raise ValueError('참조 PNG를 읽을 수 없습니다.') from current_error_value
    return current_image_bytes


def save_three_reference_inputs(current_job_root,current_request_record):
    for current_image_index,current_image_text in enumerate(current_request_record['images'],1):
        (current_job_root/f'reference-{current_image_index}.png').write_bytes(decode_reference_image(current_image_text))
    return {'action':'generate','prompt':current_request_record['prompt'],'width':current_request_record['width'],'height':current_request_record['height'],'seed':current_request_record.get('seed',10107),'steps':current_request_record['steps'],'references':[f'reference-{current_image_index}.png' for current_image_index in range(1,len(current_request_record['images'])+1)]}


def resolve_reference_settings(selected_inference_steps):
    if type(selected_inference_steps) is not int or selected_inference_steps not in (4,30):
        raise ValueError('생성 스텝은 4(Lightning) 또는 30(표준)이어야 합니다.')
    return {'selected_inference_steps':selected_inference_steps,
            'enable_anypose_adapter':False,
            'enable_lightning_adapter':False,
            'enable_standalone_lightning_adapter':selected_inference_steps==4}
