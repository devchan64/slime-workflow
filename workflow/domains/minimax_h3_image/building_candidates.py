"""Completed image candidates for building review, separate from registered assets."""
import base64
import hashlib
import fcntl
import time
from contextlib import contextmanager
import io
import json
import os
import re
import tempfile
from pathlib import Path
from PIL import Image, UnidentifiedImageError

JOB = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$')
MAX_BYTES = 20 * 1024 * 1024
CANDIDATE_TTL_SECONDS = 7 * 24 * 60 * 60

@contextmanager
def _locked(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError("임시 저장소를 확인할 수 없습니다.")
    with (root / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

def _expires(path, record):
    value = record.get("expires_at")
    if value is None:  # Existing candidates use their original creation file time.
        return path.stat().st_mtime + CANDIDATE_TTL_SECONDS
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 < value < 4102444800:
        raise ValueError("후보 보존 기한을 확인할 수 없습니다.")
    return value

def _id(value):
    if not isinstance(value, str) or not JOB.fullmatch(value):
        raise ValueError('작업 ID를 확인하세요.')
    return value

def _safe_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('파일을 확인할 수 없습니다.')
    return path.read_bytes()

def send_candidate(source_root, candidate_root, job):
    with _locked(candidate_root):
        return _send_candidate(source_root, candidate_root, job)

def _send_candidate(source_root, candidate_root, job):
    job = _id(job)
    source = Path(source_root) / job
    if source.is_symlink() or not source.is_dir():
        raise ValueError('생성 작업을 확인할 수 없습니다.')
    status = json.loads(_safe_file(source / 'status.json'))
    if status.get('status') != 'completed':
        raise ValueError('완료된 이미지 작업만 검토로 보낼 수 있습니다.')
    data = _safe_file(source / 'result.png')
    if len(data) > MAX_BYTES or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('생성 결과 PNG를 확인할 수 없습니다.')
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != 'PNG' or image.width * image.height > 40_000_000:
                raise ValueError('생성 결과 PNG 크기를 확인할 수 없습니다.')
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError('생성 결과 PNG가 손상됐습니다.') from error
    digest = hashlib.sha256(data).hexdigest()
    root = Path(candidate_root)
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError('임시 저장소를 확인할 수 없습니다.')
    # One immutable file per content hash; metadata and image are committed together.
    target = root / (job + '-' + digest + '.json')
    record = {'id': job, 'source_service': 'minimax-h3-image', 'sha256': digest, 'image_base64': base64.b64encode(data).decode('ascii'), 'expires_at': time.time() + CANDIDATE_TTL_SECONDS}
    if target.exists():
        try:
            existing = _read_candidate(root, job, digest)
        except CandidateExpired:
            pass
        else:
            return {'id': job, 'sha256': existing['sha256'], 'expires_at': existing['expires_at'], 'already_exists': True}
    fd, temp = tempfile.mkstemp(prefix='.candidate-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False)
        try:
            os.link(temp, target)
        except FileExistsError:
            _read_candidate(root, job, digest)
    finally:
        os.unlink(temp)
    return {'id': job, 'sha256': digest, 'expires_at': record['expires_at'], 'already_exists': False}

class CandidateExpired(ValueError):
    pass

def read_candidate(candidate_root, job, digest):
    with _locked(candidate_root):
        return _read_candidate(candidate_root, job, digest)

def _read_candidate(candidate_root, job, digest):
    job = _id(job)
    if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
        raise ValueError('후보 해시를 확인하세요.')
    root = Path(candidate_root)
    if root.is_symlink():
        raise ValueError('임시 저장소를 확인할 수 없습니다.')
    path = root / (job + '-' + digest + '.json')
    record = json.loads(_safe_file(path))
    if not isinstance(record, dict):
        raise ValueError('후보 기록을 확인할 수 없습니다.')
    expires = _expires(path, record)
    if time.time() >= expires:
        path.unlink()
        raise CandidateExpired('임시 후보의 7일 보존 기간이 만료됐습니다. 생성 이력에서 다시 검수로 보내세요.')
    record['expires_at'] = expires
    try:
        data = base64.b64decode(record['image_base64'], validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('후보 이미지가 손상됐습니다.') from error
    if record.get('id') != job or record.get('source_service') != 'minimax-h3-image' or record.get('sha256') != digest or len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != digest or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('후보 이미지가 손상됐습니다.')
    return record
