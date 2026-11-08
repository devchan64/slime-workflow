"""SOMA 원본 영상의 길이·용량을 접수 전에 검증한다."""
import base64
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


def validate_direct_control_video(current_encoded_video,current_frame_count):
    """처리된 포즈는 재검출·리사이즈·시간 변환 없이 사용할 수 있어야 한다."""
    validate_fun_driving_video(current_encoded_video,current_frame_count)
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(base64.b64decode(current_encoded_video,validate=True))
        current_video_file.flush()
        current_video_capture = cv2.VideoCapture(current_video_file.name)
        try:
            if abs(current_video_capture.get(cv2.CAP_PROP_FPS)-16)>0.01 or (int(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)),int(current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)))!=(832,480):
                raise ValueError('직접 입력 MP4는 832×480 · 16fps여야 합니다.')
        finally:
            current_video_capture.release()


def validate_processed_pose_video(current_encoded_video,current_frame_count):
    return validate_direct_control_video(current_encoded_video,current_frame_count)


def decode_processed_pose_video(current_job_root,current_attempt_root,current_request_record):
    import hashlib
    from PIL import Image
    current_video_kind = 'rgb' if current_request_record.get('input_mode') == 'rgb-video' else 'pose'
    current_video_filename = current_video_kind+'-input.mp4'
    current_video_path = current_job_root/current_video_filename
    if current_request_record[current_video_kind+'_video_file']!=current_video_filename or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record[current_video_kind+'_video_sha256']:
        raise ValueError('제어 MP4 입력 사본 해시 불일치')
    current_output_paths = []
    current_video_capture = cv2.VideoCapture(str(current_video_path))
    try:
        for current_frame_index in range(current_request_record['frames']):
            current_frame_ready,current_frame_image = current_video_capture.read()
            if not current_frame_ready:
                raise ValueError('제어 MP4 프레임 부족')
            current_output_path = current_attempt_root/f'control-{current_frame_index:03d}.png'
            Image.fromarray(cv2.cvtColor(current_frame_image,cv2.COLOR_BGR2RGB)).save(current_output_path)
            current_output_paths.append(current_output_path)
    finally:
        current_video_capture.release()
    return current_output_paths
