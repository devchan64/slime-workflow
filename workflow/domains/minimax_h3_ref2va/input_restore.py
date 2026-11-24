"""Ref2VA 작업의 저장 입력을 무결성 확인 후 복원한다."""
import base64
import os
import stat
from pathlib import Path
from workflow.common.video_attachment_verification import verify_saved_video_attachments
from workflow.domains.hermes_agent.delegation_store import validate_service_job_identifier, read_bounded_delegation_record
from workflow.generators.minimax_h3_ref2va.contracts import MAX_VIDEO_BYTES, validate_request


def load_saved_input(root, job):
    root = Path(root)
    if not validate_service_job_identifier('minimax-h3-ref2va', job):
        raise ValueError('작업 ID가 올바르지 않습니다.')
    directory = root / job
    if root.is_symlink() or directory.is_symlink() or not directory.is_dir() or directory.resolve().parent != root.resolve():
        raise ValueError('작업 폴더를 확인할 수 없습니다.')
    saved = read_bounded_delegation_record(directory / 'request.json')
    verify_saved_video_attachments(directory, saved, ('edit_video',))
    descriptor = os.open(directory / 'edit-video.mp4', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as video:
        before = os.fstat(video.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_VIDEO_BYTES:
            raise ValueError('영상 사본을 확인할 수 없습니다.')
        content = video.read(MAX_VIDEO_BYTES + 1)
        after = os.fstat(video.fileno())
    import hashlib
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            or hashlib.sha256(content).hexdigest() != saved.get('edit_video_sha256')):
        raise ValueError('영상 사본이 변경되었습니다.')
    fields = ('action', 'prompt', 'width', 'height', 'frames', 'steps', 'seed')
    request = {key: saved[key] for key in fields}
    request.update(images=[], edit_video=base64.b64encode(content).decode('ascii'))
    validate_request(request)
    return {'id': job, 'request': request}
