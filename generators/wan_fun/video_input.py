"""SOMA 원본 영상의 길이·용량을 접수 전에 검증한다."""
import base64
import tempfile
import cv2

FUN_VIDEO_MAXIMUM_BYTES = 32*1024*1024


def validate_fun_driving_video(current_encoded_video, current_frame_count):
    if not isinstance(current_encoded_video, str) or len(current_encoded_video)>FUN_VIDEO_MAXIMUM_BYTES*4//3+4:
        raise ValueError('SOMA 렌더 영상은 MP4 32MiB 이하여야 합니다.')
    current_video_bytes = base64.b64decode(current_encoded_video, validate=True)
    if len(current_video_bytes)<12 or current_video_bytes[4:8] != b'ftyp':
        raise ValueError('SOMA 렌더 MP4 파일이 필요합니다.')
    with tempfile.NamedTemporaryFile(suffix='.mp4') as current_video_file:
        current_video_file.write(current_video_bytes)
        current_video_file.flush()
        current_video_capture = cv2.VideoCapture(current_video_file.name)
        try:
            current_video_fps = current_video_capture.get(cv2.CAP_PROP_FPS)
            current_source_frames = current_video_capture.get(cv2.CAP_PROP_FRAME_COUNT)
            if not current_video_capture.isOpened() or not 1<=current_video_fps<=60:
                raise ValueError('SOMA 영상 디코딩 또는 FPS 오류')
            if round((current_frame_count-1)*current_video_fps/16)>=current_source_frames:
                raise ValueError('SOMA 영상이 출력 시간보다 짧습니다. 16fps 시간 기준으로 충분한 모션을 입력하세요.')
            if max(current_video_capture.get(cv2.CAP_PROP_FRAME_WIDTH), current_video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))>4096:
                raise ValueError('SOMA 입력 해상도는 각 변 4096 이하이어야 합니다.')
        finally:
            current_video_capture.release()
