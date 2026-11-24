"""MiniMax H3 Ref2VA 영상 편집 입력과 저장 사본 계약."""
import base64
import binascii
import hashlib
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
JOB_STORAGE = ROOT / '.tmp/test/minimax-h3-ref2va'
PYTHON = ROOT / '.local/venvs/wan-fun-rocm/bin/python'
MAX_VIDEO_BYTES = 27 * 1024 * 1024


def decode_video_attachment(value):
    if not isinstance(value, str) or len(value) > ((MAX_VIDEO_BYTES + 2) // 3) * 4:
        raise ValueError('입력 영상은 27MiB 이하 MP4여야 합니다.')
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('입력 영상의 인코딩이 올바르지 않습니다.') from error
    if len(data) > MAX_VIDEO_BYTES or len(data) < 12 or data[4:8] != b'ftyp':
        raise ValueError('입력 영상은 27MiB 이하 MP4여야 합니다.')
    return data


def validate_video_content(data):
    # 영상 디코더의 결과를 검사하며 컨테이너 헤더만으로 입력을 승인하지 않는다.
    import cv2
    with tempfile.NamedTemporaryFile(suffix='.mp4') as temporary:
        temporary.write(data)
        temporary.flush()
        capture = cv2.VideoCapture(temporary.name)
        try:
            if not capture.isOpened():
                raise ValueError('입력 영상을 열 수 없습니다.')
            if (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (832, 480):
                raise ValueError('입력 영상은 832×480이어야 합니다.')
            if abs(capture.get(cv2.CAP_PROP_FPS) - 24) > .01:
                raise ValueError('입력 영상은 24fps여야 합니다.')
            count = 0
            while count <= 124:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame is None or frame.shape[:2] != (480, 832):
                    raise ValueError('입력 영상 프레임이 올바르지 않습니다.')
                count += 1
            if count != 124:
                raise ValueError('입력 영상은 정확히 124프레임이어야 합니다.')
        finally:
            capture.release()


def validate_request(request):
    fields = {'action', 'prompt', 'images', 'edit_video', 'width', 'height', 'frames', 'steps', 'seed'}
    if not isinstance(request, dict) or set(request) != fields or request.get('action') != 'generate':
        raise ValueError('Ref2VA 요청 필드가 올바르지 않습니다.')
    if not isinstance(request['prompt'], str) or not 1 <= len(request['prompt'].strip()) <= 8000:
        raise ValueError('편집 프롬프트를 1~8000자로 입력하세요.')
    if request['images'] != []:
        raise ValueError('Ref2VA 영상 편집은 별도 이미지 참조를 지원하지 않습니다.')
    if any(type(request[k]) is not int or request[k] != v for k, v in {'width': 832, 'height': 480, 'frames': 124, 'steps': 8}.items()):
        raise ValueError('832×480, 124프레임, Turbo 8스텝 설정이 필요합니다.')
    if type(request['seed']) is not int or not 0 <= request['seed'] <= 2147483647:
        raise ValueError('시드는 0~2147483647의 정수여야 합니다.')
    validate_video_content(decode_video_attachment(request['edit_video']))
    return {**request, 'prompt': request['prompt'].strip(), 'tag': 'minimax-h3-ref2va'}


def save_video_input(job_root, request):
    saved = dict(request)
    data = decode_video_attachment(saved.pop('edit_video'))
    (Path(job_root) / 'edit-video.mp4').write_bytes(data)
    saved['edit_video_file'] = 'edit-video.mp4'
    saved['edit_video_sha256'] = hashlib.sha256(data).hexdigest()
    return saved
