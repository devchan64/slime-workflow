"""Animate-2의 고정 모델과 RGB 동작 입력 계약."""
import base64
import io
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image

ANIMATE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ANIMATE_JOB_STORAGE = ANIMATE_WORKSPACE_ROOT / '.tmp/test/wan22-animate2'
ANIMATE_MODEL_DIRECTORY = ANIMATE_WORKSPACE_ROOT / '.model/wan22-animate2'
ANIMATE_RUNTIME_DIRECTORY = ANIMATE_WORKSPACE_ROOT / '.local/wan-animate2/diffusers'
ANIMATE_MODEL_IDENTIFIER = 'Wan-AI/Wan2.2-Animate-2-14B-Diffusers'
ANIMATE_MODEL_REVISION = '7d48412d7b903ff3a89f4f5a960d99e1899605a1'
ANIMATE_RUNTIME_REVISION = '8c54b38fea3d624d23d0e43c0c96037f080a79f9'
ANIMATE_MAXIMUM_BYTES = 32 * 1024 * 1024
ANIMATE_OUTPUT_FRAME_RATE = 16
ANIMATE_MAXIMUM_SEED_VALUE = 2147483647


def inspect_animate_video(path):
    """MP4의 영상 정보와 16fps 샘플링 시 사용 가능한 최대 프레임을 확인한다."""
    import cv2
    capture = cv2.VideoCapture(str(path))
    try:
        rate = capture.get(cv2.CAP_PROP_FPS)
        count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if not capture.isOpened() or not 1 <= rate <= 120 or count < 1 or width < 1 or height < 1:
            raise ValueError('영상 디코딩 실패 · 읽을 수 있는 MP4를 선택하세요.')
        frames = min(81, int(count / rate * ANIMATE_OUTPUT_FRAME_RATE))
        maximum = 1 + 4 * ((frames - 1) // 4)
        if maximum < 5:
            raise ValueError('16fps 기준 5프레임 이상의 영상이 필요합니다.')
        return {'width':int(width),'height':int(height),'fps':rate,'frame_count':int(count),'maximum_frames':maximum}
    finally:
        capture.release()


def inspect_animate_assets():
    current_missing_files = []
    for current_relative_path in ('modular_model_index.json', 'transformer/config.json', 'vae/config.json', 'ready.sha256'):
        if not (ANIMATE_MODEL_DIRECTORY/current_relative_path).is_file():
            current_missing_files.append(current_relative_path)
    current_manifest_path=ANIMATE_MODEL_DIRECTORY/'ready.sha256'
    if current_manifest_path.is_file():
        try:
            current_manifest_record=json.loads(current_manifest_path.read_text())
            if current_manifest_record['revision']!=ANIMATE_MODEL_REVISION:
                raise ValueError('모델 revision 불일치')
            if not current_manifest_record['files'] or 'modular_model_index.json' not in current_manifest_record['files']:
                raise ValueError('모델 파일 목록 누락')
            for current_relative_name,current_file_record in current_manifest_record['files'].items():
                current_asset_path=(ANIMATE_MODEL_DIRECTORY/current_relative_name).resolve()
                if not current_asset_path.is_relative_to(ANIMATE_MODEL_DIRECTORY.resolve()) or not current_asset_path.is_file() or current_asset_path.stat().st_size!=current_file_record['bytes']:
                    current_missing_files.append(current_relative_name)
        except (ValueError,KeyError,TypeError) as current_manifest_error:
            current_missing_files.append(str(current_manifest_error))
    if not (ANIMATE_RUNTIME_DIRECTORY/'.git').is_dir():
        current_missing_files.append('Diffusers 고정 소스')
    else:
        current_source_revision = subprocess.check_output(['git','-C',str(ANIMATE_RUNTIME_DIRECTORY),'rev-parse','HEAD'],text=True).strip()
        if current_source_revision != ANIMATE_RUNTIME_REVISION:
            current_missing_files.append('Diffusers 버전 불일치')
    return {'ready':not current_missing_files,'missing':current_missing_files,'message': '모델 파일 준비 완료 · 8GB 실행과 SOMA 동작 전사 품질은 미검증' if not current_missing_files else '준비 필요: '+', '.join(current_missing_files)}


def validate_animate_assets():
    current_model_status = inspect_animate_assets()
    if not current_model_status['ready']:
        raise ValueError(current_model_status['message'])


def validate_animate_request(current_request_record):
    current_required_fields = {'action','images','driving_video','prompt','frames','steps','seed','width','height'}
    if not isinstance(current_request_record,dict) or set(current_request_record)-{'lora_mode'}!=current_required_fields:
        raise ValueError('Animate-2 요청 필드 불일치')
    if current_request_record.get('lora_mode', 'none') not in ('none', 'lightx2v'):
        raise ValueError('지원하지 않는 Animate-2 LoRA 선택입니다.')
    if current_request_record['action']!='generate':
        raise ValueError('generate 요청만 지원합니다.')
    for current_field_name,current_minimum_value,current_maximum_value in [('frames',5,81),('steps',2,50),('seed',0,ANIMATE_MAXIMUM_SEED_VALUE),('width',832,832),('height',480,480)]:
        current_field_value=current_request_record[current_field_name]
        if type(current_field_value) is not int or not current_minimum_value<=current_field_value<=current_maximum_value:
            raise ValueError(f'{current_field_name}: 정수 {current_minimum_value}~{current_maximum_value} 필요')
    if (current_request_record['frames']-1)%4:
        raise ValueError('프레임은 4n+1이어야 합니다.')
    if not isinstance(current_request_record['prompt'],str) or not current_request_record['prompt'].strip() or len(current_request_record['prompt'])>8000:
        raise ValueError('외형·배경 프롬프트는 1~8000자여야 합니다.')
    if not isinstance(current_request_record['images'],list) or len(current_request_record['images'])!=1:
        raise ValueError('캐릭터 참조 PNG 1장이 필요합니다.')
    current_image_bytes=base64.b64decode(current_request_record['images'][0],validate=True)
    if len(current_image_bytes)>8*1024*1024:
        raise ValueError('참조 이미지는 8MiB 이하입니다.')
    with Image.open(io.BytesIO(current_image_bytes)) as current_image_object:
        if current_image_object.format!='PNG' or current_image_object.size!=(832,480):
            raise ValueError('참조 이미지는 832×480 PNG여야 합니다.')
    current_video_value=current_request_record['driving_video']
    if not isinstance(current_video_value,str) or len(current_video_value)>ANIMATE_MAXIMUM_BYTES*4//3+4:
        raise ValueError('RGB 동작 MP4는 32MiB 이하입니다.')
    current_video_bytes=base64.b64decode(current_video_value,validate=True)
    if current_video_bytes[4:8]!=b'ftyp':
        raise ValueError('MP4 컨테이너가 필요합니다.')
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(current_video_bytes)
        current_video_file.flush()
        if inspect_animate_video(current_video_file.name)['maximum_frames'] < current_request_record['frames']:
            raise ValueError('16fps 기준 입력 길이 부족')
    return dict(current_request_record)
