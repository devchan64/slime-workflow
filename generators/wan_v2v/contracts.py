"""Wan2.2 RGB V2V 고정 모델과 입력 계약."""
import base64
import binascii
import json
import importlib.util
import math
import subprocess
import tempfile
from pathlib import Path

V2V_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
V2V_JOB_STORAGE = V2V_WORKSPACE_ROOT / '.tmp/test/wan22-v2v'
V2V_MODEL_DIRECTORY = V2V_WORKSPACE_ROOT / '.model/wan22-v2v'
V2V_RUNTIME_DIRECTORY = V2V_WORKSPACE_ROOT / '.local/wan-v2v/DiffSynth-Studio'
V2V_MODEL_IDENTIFIER = 'Wan-AI/Wan2.2-T2V-A14B'
V2V_MODEL_REVISION = 'c8c270b13ee05bfa474194ac9fb07a5868a97cea'
V2V_RUNTIME_REVISION = 'fdad57bd94d3fbac8a72c44920dd0a23b719ebb9'
V2V_RUNTIME_DEPENDENCIES = ('modelscope','entropack','ftfy','peft','accelerate','transformers','torchvision')
V2V_MAXIMUM_BYTES = 32 * 1024 * 1024
V2V_FIXED_SETTINGS = {'cfg_scale': 5.0, 'sigma_shift': 5.0, 'switch_DiT_boundary': 0.875, 'tiled': True}
V2V_REQUIRED_FILES = (
    'Wan2.1_VAE.pth', 'models_t5_umt5-xxl-enc-bf16.pth',
    'google/umt5-xxl/spiece.model', 'google/umt5-xxl/tokenizer_config.json',
    *[f'{current_expert_name}/diffusion_pytorch_model-{current_shard_index:05d}-of-00006.safetensors'
      for current_expert_name in ('high_noise_model', 'low_noise_model') for current_shard_index in range(1, 7)],
)


def inspect_v2v_assets():
    current_missing_dependencies = [current_module_name for current_module_name in V2V_RUNTIME_DEPENDENCIES if importlib.util.find_spec(current_module_name) is None]
    current_missing_files = [current_file_name for current_file_name in V2V_REQUIRED_FILES
                             if not (V2V_MODEL_DIRECTORY/current_file_name).is_file()]
    try:
        current_manifest_record = json.loads((V2V_MODEL_DIRECTORY/'ready.sha256').read_text())
        if current_manifest_record['revision'] != V2V_MODEL_REVISION:
            raise ValueError('모델 revision 불일치')
        for current_file_name in V2V_REQUIRED_FILES:
            current_file_record = current_manifest_record['files'][current_file_name]
            if (V2V_MODEL_DIRECTORY/current_file_name).stat().st_size != current_file_record['bytes']:
                raise ValueError('모델 파일 크기 불일치: '+current_file_name)
    except (OSError, ValueError, KeyError, TypeError) as current_manifest_error:
        current_missing_files.append('모델 준비 기록: '+str(current_manifest_error))
    if not (V2V_RUNTIME_DIRECTORY/'.git').is_dir():
        current_missing_files.append('DiffSynth 고정 소스')
    elif subprocess.check_output(['git','-C',str(V2V_RUNTIME_DIRECTORY),'rev-parse','HEAD'],text=True).strip() != V2V_RUNTIME_REVISION:
        current_missing_files.append('DiffSynth revision 불일치')
    current_missing_files.extend('Python 의존성 누락: '+current_module_name for current_module_name in current_missing_dependencies)
    return {'ready': not current_missing_files, 'missing': current_missing_files,
            'message': '모델 파일 준비 완료 · 8GB V2V 추론 미검증' if not current_missing_files else '준비 필요: .venv/bin/python generators/wan_v2v/prepare.py · '+', '.join(current_missing_files)}


def validate_v2v_assets():
    current_asset_status = inspect_v2v_assets()
    if not current_asset_status['ready']:
        raise ValueError(current_asset_status['message'])


def read_v2v_frames(current_video_path, current_frame_count):
    """원본 FPS·순서를 보존하며 요청한 앞쪽 프레임을 디코딩한다."""
    import cv2
    from PIL import Image
    current_video_capture = cv2.VideoCapture(str(current_video_path))
    try:
        current_frame_rate = current_video_capture.get(cv2.CAP_PROP_FPS)
        if not current_video_capture.isOpened() or not math.isfinite(current_frame_rate) or not 1 <= current_frame_rate <= 60:
            raise ValueError('MP4 디코딩 또는 FPS 오류 (1~60fps 필요)')
        current_frame_images = []
        for current_frame_index in range(current_frame_count):
            current_read_success, current_frame_array = current_video_capture.read()
            if not current_read_success:
                raise ValueError(f'입력 영상 길이 부족: {current_frame_index}/{current_frame_count}프레임')
            if current_frame_array.shape[:2] != (480,832):
                raise ValueError('입력 영상은 832×480이어야 합니다. 자동 리사이즈하지 않습니다.')
            current_frame_images.append(Image.fromarray(cv2.cvtColor(current_frame_array,cv2.COLOR_BGR2RGB)))
        return current_frame_images, current_frame_rate
    finally:
        current_video_capture.release()


def validate_v2v_request(current_request_record):
    current_required_fields = {'action','input_video','prompt','negative_prompt','frames','steps','seed','width','height','denoising_strength'}
    if not isinstance(current_request_record,dict) or set(current_request_record) != current_required_fields:
        raise ValueError('V2V 요청 필드 불일치: RGB MP4와 프롬프트만 입력합니다.')
    if current_request_record['action'] != 'generate':
        raise ValueError('generate 요청만 지원합니다.')
    for current_field_name,current_minimum_value,current_maximum_value in [('frames',5,81),('steps',2,50),('seed',0,2147483647),('width',832,832),('height',480,480)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) is not int or not current_minimum_value <= current_field_value <= current_maximum_value:
            raise ValueError(f'{current_field_name}: 정수 {current_minimum_value}~{current_maximum_value} 필요')
    if (current_request_record['frames']-1)%4:
        raise ValueError('프레임은 4n+1이어야 합니다.')
    current_strength_value = current_request_record['denoising_strength']
    if type(current_strength_value) not in (int,float) or not math.isfinite(current_strength_value) or not 0 < current_strength_value < 1:
        raise ValueError('변경 강도는 0 초과 1 미만이어야 합니다. 1은 입력 영상 정보를 보존하지 않습니다.')
    for current_field_name in ('prompt','negative_prompt'):
        current_prompt_value = current_request_record[current_field_name]
        if not isinstance(current_prompt_value,str) or len(current_prompt_value)>8000 or (current_field_name=='prompt' and not current_prompt_value.strip()):
            raise ValueError('프롬프트는 최대 8000자이며 양성 지시는 필수입니다.')
    current_video_value = current_request_record['input_video']
    if not isinstance(current_video_value,str) or len(current_video_value)>V2V_MAXIMUM_BYTES*4//3+4:
        raise ValueError('입력 MP4는 32MiB 이하입니다.')
    try:
        current_video_bytes = base64.b64decode(current_video_value,validate=True)
    except (binascii.Error,ValueError) as current_decode_error:
        raise ValueError('입력 MP4 base64 오류') from current_decode_error
    if len(current_video_bytes)>V2V_MAXIMUM_BYTES or current_video_bytes[4:8]!=b'ftyp':
        raise ValueError('32MiB 이하 MP4 컨테이너가 필요합니다.')
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(current_video_bytes)
        current_video_file.flush()
        read_v2v_frames(current_video_file.name,current_request_record['frames'])
    # 공용 참조 스냅샷 계약을 재사용하지만 이미지 조건은 제공하지 않는다.
    return {**current_request_record,'images':[]}
