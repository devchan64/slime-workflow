"""Retain the original DINO model outside the active model tree by rename."""
import hashlib
import json
import os
from pathlib import Path

from workflow.domains.trellis_experiment.offline_loader import DINO_FILENAME, DINO_SHA256


def retain_dino_original(root, expected_hash=DINO_SHA256):
    root = Path(root)
    source = root / 'trellis-dinov2'
    active = root / 'models/trellis-dinov2' / DINO_FILENAME
    retained_root = root.parent / '.local/model-catalog/retained'
    if any(p.is_symlink() for p in (root, source, root / 'models', active.parent, active)):
        raise ValueError('모델 경로에 심볼릭 링크가 있습니다.')
    if not source.is_dir() or {p.name for p in source.iterdir()} != {DINO_FILENAME}:
        raise ValueError('원본 구성이 예상과 다릅니다.')
    original = source / DINO_FILENAME
    if original.is_symlink() or not original.is_file() or not active.is_file():
        raise ValueError('원본 또는 현재 설치본을 확인할 수 없습니다.')
    identities = {}
    for path in (original, active):
        before = path.stat()
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = os.fstat(stream.fileno())
        if digest != expected_hash or (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('가중치 해시 또는 상태가 다릅니다.')
        identities[path] = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    for path in (root.parent / '.local', root.parent / '.local/model-catalog', retained_root):
        if path.is_symlink():
            raise ValueError('보존 경로에 심볼릭 링크가 있습니다.')
        path.mkdir(exist_ok=True)
    if source.stat().st_dev != retained_root.stat().st_dev:
        raise ValueError('보존 경로가 다른 파일시스템입니다.')
    reservation = retained_root / 'trellis-dinov2'
    reservation.mkdir()  # Refuse an existing transaction or retained original.
    record = {'source': str(source), 'retained': str(reservation / 'original'),
              'active': str(active), 'sha256': expected_hash,
              'rollback': '보존된 original 디렉터리를 기존 source 경로로 이동'}
    with (reservation / 'transaction.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    if {p.name for p in source.iterdir()} != {DINO_FILENAME}:
        raise ValueError('원본 구성이 변경됐습니다.')
    for path, expected in identities.items():
        info = path.lstat()
        if path.is_symlink() or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != expected:
            raise ValueError('가중치가 확인 후 변경됐습니다.')
    os.rename(source, reservation / 'original')
    return record
