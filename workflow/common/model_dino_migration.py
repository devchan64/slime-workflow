"""Publish a hash-pinned DINOv2 copy without removing the old installation."""
import hashlib
import os
from pathlib import Path
import tempfile

from workflow.domains.trellis_experiment.offline_loader import DINO_FILENAME, DINO_SHA256


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def copy_dino_model(root, expected_hash=DINO_SHA256):
    root = Path(root)
    source = root / 'trellis-dinov2' / DINO_FILENAME
    parent = root / 'models' / 'trellis-dinov2'
    if root.is_symlink() or source.parent.is_symlink() or source.is_symlink() or not source.is_file():
        raise ValueError('DINOv2 원본을 확인할 수 없습니다.')
    if (root / 'models').is_symlink() or parent.is_symlink():
        raise ValueError('대상 경로에 심볼릭 링크가 있습니다.')
    parent.mkdir(parents=True, exist_ok=True)
    if (root / 'models').is_symlink() or parent.is_symlink():
        raise ValueError('대상 경로가 변경됐습니다.')
    destination = parent / DINO_FILENAME
    temporary = None
    try:
        before = source.stat()
        digest = hashlib.sha256()
        with source.open('rb') as reader, tempfile.NamedTemporaryFile(dir=parent, prefix='.dino-copy-', delete=False) as writer:
            temporary = Path(writer.name)
            if _identity(os.fstat(reader.fileno())) != _identity(before):
                raise ValueError('원본이 변경됐습니다.')
            while chunk := reader.read(1024 * 1024):
                digest.update(chunk)
                writer.write(chunk)
            writer.flush()
            os.fsync(writer.fileno())
            if _identity(os.fstat(reader.fileno())) != _identity(before):
                raise ValueError('복사 중 원본이 변경됐습니다.')
        if _identity(source.stat()) != _identity(before) or digest.hexdigest() != expected_hash:
            raise ValueError('원본 해시 또는 상태가 일치하지 않습니다.')
        with temporary.open('rb') as reader:
            if hashlib.file_digest(reader, 'sha256').hexdigest() != expected_hash:
                raise ValueError('복사본 해시가 일치하지 않습니다.')
        os.chmod(temporary, before.st_mode & 0o777)
        os.link(temporary, destination)  # No replacement of an existing file.
        return {'source': str(source), 'destination': str(destination), 'size': before.st_size,
                'sha256': expected_hash, 'source_preserved': True}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
