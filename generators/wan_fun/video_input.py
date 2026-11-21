"""SOMA 원본 영상의 길이·용량을 접수 전에 검증한다."""
import base64
from pathlib import Path
from generators.wan_fun.contracts import FUN_MAX_FRAME_COUNT
import tempfile
import cv2

FUN_VIDEO_MAXIMUM_BYTES = 32*1024*1024


def validate_fun_driving_video(current_encoded_video, current_frame_count):
    if not isinstance(current_encoded_video, str) or len(current_encoded_video)>FUN_VIDEO_MAXIMUM_BYTES*4//3+4:
        raise ValueError('입력 영상은 MP4 32MiB 이하여야 합니다.')
    current_video_bytes = base64.b64decode(current_encoded_video, validate=True)
    if len(current_video_bytes)<12 or current_video_bytes[4:8] != b'ftyp':
        raise ValueError('MP4 파일이 필요합니다.')
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(current_video_bytes)
        current_video_file.flush()
        current_video_capture = cv2.VideoCapture(current_video_file.name)
        try:
            current_video_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
            current_source_frames = current_video_capture.get(cv2.CAP_PROP_FRAME_COUNT)
            if not current_video_capture.isOpened() or not 1<=current_video_fps<=60:
                raise ValueError('입력 영상 디코딩 또는 FPS 오류')
            if round((current_frame_count-1)*current_video_fps/16)>=current_source_frames:
                raise ValueError('입력 영상이 출력 시간보다 짧습니다. 16fps 시간 기준으로 충분한 모션을 입력하세요.')
            if max(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH), current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))>4096:
                raise ValueError('입력 해상도는 각 변 4096 이하이어야 합니다.')
        finally:
            current_video_capture.release()


def validate_processed_pose_video(current_encoded_video,current_frame_count):
    """처리된 포즈는 재검출·리사이즈·시간 변환 없이 사용할 수 있어야 한다."""
    validate_fun_driving_video(current_encoded_video,current_frame_count)
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(base64.b64decode(current_encoded_video,validate=True))
        current_video_file.flush()
        current_video_capture = cv2.VideoCapture(current_video_file.name)
        try:
            if abs(current_video_capture.get(cv2.CAP_PROP_FPS)-16)>0.01 or (int(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))!=(832,480):
                raise ValueError('처리된 포즈 MP4는 832×480 · 16fps여야 합니다. Kimodo DWPose 출력을 사용하세요.')
        finally:
            current_video_capture.release()


def decode_processed_pose_video(current_job_root,current_attempt_root,current_request_record):
    import hashlib
    from PIL import Image
    current_video_path = current_job_root/'pose-input.mp4'
    if current_request_record['pose_video_file']!='pose-input.mp4' or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record['pose_video_sha256']:
        raise ValueError('포즈 MP4 입력 사본 해시 불일치')
    current_output_paths = []
    current_video_capture = cv2.VideoCapture(str(current_video_path))
    try:
        for current_frame_index in range(current_request_record['frames']):
            current_frame_ready,current_frame_image = current_video_capture.read()
            if not current_frame_ready:
                raise ValueError('포즈 MP4 프레임 부족')
            current_output_path = current_attempt_root/f'control-{current_frame_index:03d}.png'
            Image.fromarray(cv2.cvtColor(current_frame_image,cv2.COLOR_BGR2RGB)).save(current_output_path)
            current_output_paths.append(current_output_path)
    finally:
        current_video_capture.release()
    return current_output_paths


def inspect_fun_pose_video(current_video_path):
    """업로드 영상의 조건과 추천 프레임 수를 확인한다."""
    if not current_video_path:
        return None, '포즈 MP4를 첨부하세요.'
    try:
        current_video_file = Path(current_video_path)
        if current_video_file.stat().st_size > FUN_VIDEO_MAXIMUM_BYTES:
            return None, '영상이 32MiB를 초과합니다. 크기를 줄여 다시 첨부하세요.'
        with current_video_file.open('rb') as current_video_stream:
            if current_video_stream.read(8)[4:8] != b'ftyp':
                return None, 'MP4 영상을 첨부하세요.'
        current_video_capture = cv2.VideoCapture(str(current_video_file))
        try:
            if not current_video_capture.isOpened():
                return None, '영상을 읽을 수 없습니다. MP4를 다시 첨부하세요.'
            current_frame_rate = current_video_capture.get(cv2.CAP_PROP_FPS)
            current_frame_count = int(current_video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame_width = int(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            current_frame_height = int(current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            current_video_capture.release()
        current_description_text = f'입력: {current_frame_width}×{current_frame_height} · {current_frame_rate:.2f}fps · {current_frame_count}프레임.'
        if (current_frame_width, current_frame_height) != (832, 480) or not 15.99 <= current_frame_rate <= 16.01:
            return None, current_description_text + ' 832×480·16fps로 변환해 다시 첨부하세요.'
        current_recommended_count = min(FUN_MAX_FRAME_COUNT, 1 + 4 * ((current_frame_count - 1) // 4))
        if current_recommended_count < 5:
            return None, current_description_text + ' 최소 5프레임의 영상을 첨부하세요.'
        return current_recommended_count, current_description_text + f' 사용 가능 · 최대 {current_recommended_count}프레임 선택 가능.'
    except (OSError, ValueError, OverflowError):
        return None, '영상 정보를 읽을 수 없습니다. MP4를 다시 첨부하세요.'
