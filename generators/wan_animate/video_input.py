"""이미지·동작 영상 입력 검증. 영상 해독은 CPU, 모델 연산은 CUDA 작업자에서 한다."""
import base64
import io
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps

ANIMATE_DEFAULT_PROMPT_TEXT = '视频中的人在做动作'
ANIMATE_MAX_VIDEO_BYTES = 32 * 1024 * 1024
ANIMATE_VIDEO_INPUT_FIELDS = {'action','mode','images','driving_video','width','height','steps','seed','flow_shift','guidance_scale'}


def inspect_driving_video(current_video_path):
    current_runtime_python=Path(__file__).resolve().parents[2]/'.venv/bin/python'
    current_probe_script="import imageio_ffmpeg,json,sys; reader=imageio_ffmpeg.read_frames(sys.argv[1]); meta=next(reader); reader.close(); count,seconds=imageio_ffmpeg.count_frames_and_secs(sys.argv[1]); print(json.dumps(dict(width=meta['size'][0],height=meta['size'][1],fps=meta['fps'],frames=count)))"
    current_probe_result=subprocess.run([str(current_runtime_python),'-c',current_probe_script,str(current_video_path)],check=True,capture_output=True,text=True,timeout=30)
    current_stream_record=json.loads(current_probe_result.stdout)
    current_video_fps=current_stream_record['fps']
    current_frame_count=current_stream_record['frames']
    if not 1<=current_video_fps<=60 or not 1<=current_frame_count<=121:
        raise ValueError('현재 단일 구간 구현은 1~121프레임, 1~60fps 영상만 지원합니다. 공식 모델의 길이 제한은 아닙니다.')
    if current_stream_record['width']>4096 or current_stream_record['height']>4096:
        raise ValueError('입력 영상 해상도는 각 변 4096 이하이어야 합니다.')
    return current_frame_count,current_video_fps


def validate_animation_video_request(current_request_record):
    from generators.wan_animate.contracts import validate_animate_request
    from tools.review.domains.image.three_reference_generation import decode_reference_image
    if set(current_request_record)!=ANIMATE_VIDEO_INPUT_FIELDS or current_request_record['mode']!='animation':
        raise ValueError('애니메이션용 이미지·영상 요청 필드 오류. 인물 교체는 미구현입니다.')
    if not isinstance(current_request_record['images'],list) or len(current_request_record['images'])!=1:
        raise ValueError('캐릭터 참조 이미지 1장이 필요합니다.')
    current_encoded_video=current_request_record['driving_video']
    if not isinstance(current_encoded_video,str) or len(current_encoded_video)>ANIMATE_MAX_VIDEO_BYTES*4//3+4:
        raise ValueError('동작 영상은 MP4 32MiB 이하여야 합니다.')
    current_video_bytes=base64.b64decode(current_encoded_video,validate=True)
    if len(current_video_bytes)<12 or current_video_bytes[4:8]!=b'ftyp':
        raise ValueError('MP4 동작 영상을 첨부하세요.')
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(current_video_bytes)
        current_video_file.flush()
        current_frame_count,current_video_fps=inspect_driving_video(current_video_file.name)
    for current_dimension_name in ('width','height'):
        current_dimension_value=current_request_record[current_dimension_name]
        if type(current_dimension_value) is not int or not 64<=current_dimension_value<=1280 or current_dimension_value%16:
            raise ValueError('출력 해상도는 64~1280 범위의 16배수여야 합니다.')
    current_output_buffer=io.BytesIO()
    with Image.open(io.BytesIO(decode_reference_image(current_request_record['images'][0]))) as current_reference_image:
        current_reference_image=ImageOps.exif_transpose(current_reference_image).convert('RGB')
        current_reference_image=ImageOps.pad(current_reference_image,(current_request_record['width'],current_request_record['height']),color='white')
        current_reference_image.save(current_output_buffer,format='PNG')
    current_legacy_request={current_field_name:current_request_record[current_field_name] for current_field_name in ('action','width','height','steps','seed','flow_shift','guidance_scale')}
    current_legacy_request.update(images=[base64.b64encode(current_output_buffer.getvalue()).decode()],prompt=ANIMATE_DEFAULT_PROMPT_TEXT,frames=((current_frame_count+2)//4)*4+1,fps=16)
    current_validated_request=validate_animate_request(current_legacy_request)
    return {**current_validated_request,'mode':'animation','driving_video':current_encoded_video,'source_frames':current_frame_count,'fps':current_video_fps,'tag':'animate-q4-video'}
