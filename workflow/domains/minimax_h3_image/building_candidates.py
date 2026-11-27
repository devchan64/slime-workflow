"""Completed image candidates for building review, separate from registered assets."""
import base64
import hashlib
import io
import json
import os
import re
import tempfile
from pathlib import Path
from PIL import Image, UnidentifiedImageError

JOB = re.compile(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}$')
MAX_BYTES = 20 * 1024 * 1024

def _id(value):
    if not isinstance(value, str) or not JOB.fullmatch(value):
        raise ValueError('작업 ID를 확인하세요.')
    return value

def _safe_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('파일을 확인할 수 없습니다.')
    return path.read_bytes()

def send_candidate(source_root, candidate_root, job):
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
    record = {'id': job, 'source_service': 'minimax-h3-image', 'sha256': digest, 'image_base64': base64.b64encode(data).decode('ascii')}
    if target.exists():
        existing = read_candidate(root, job, digest)
        return {'id': job, 'sha256': existing['sha256'], 'already_exists': True}
    fd, temp = tempfile.mkstemp(prefix='.candidate-', dir=root)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False)
        try:
            os.link(temp, target)
        except FileExistsError:
            read_candidate(root, job, digest)
    finally:
        os.unlink(temp)
    return {'id': job, 'sha256': digest, 'already_exists': False}

def read_candidate(candidate_root, job, digest):
    job = _id(job)
    if not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
        raise ValueError('후보 해시를 확인하세요.')
    root = Path(candidate_root)
    if root.is_symlink():
        raise ValueError('임시 저장소를 확인할 수 없습니다.')
    record = json.loads(_safe_file(root / (job + '-' + digest + '.json')))
    try:
        data = base64.b64decode(record['image_base64'], validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise ValueError('후보 이미지가 손상됐습니다.') from error
    if record.get('id') != job or record.get('source_service') != 'minimax-h3-image' or record.get('sha256') != digest or len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != digest or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('후보 이미지가 손상됐습니다.')
    return record
