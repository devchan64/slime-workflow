"""Guarded, journaled relocation of the VACE BF16 UMT5 checkpoint."""
import fcntl
import hashlib
import json
import os
from pathlib import Path

from workflow.common.model_storage_move import _rename_noreplace


def _verify(path, size, digest):
    if path.is_symlink() or not path.is_file():
        raise ValueError('인코더 파일을 확인할 수 없습니다.')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            or before.st_size != size or actual != digest):
        raise ValueError('인코더 크기·해시가 다르거나 검사 중 변경됐습니다.')
    return before


def move_vace_encoder(project_root, journal, validate, *, expected_size, expected_sha256):
    """The caller must exclude independent readers and writers first."""
    project_root, journal = Path(project_root), Path(journal)
    root = project_root/'.model'
    source = root/'wan22-vace/models_t5_umt5-xxl-enc-bf16.pth'
    target = root/'umt5-xxl-encoder-bf16'/source.name
    queue, backup = project_root/'.tmp/gpu-queue', project_root/'.local/hermes/model-backup-verification'
    if not callable(validate) or not journal.is_absolute() or journal.exists() or journal.is_symlink():
        raise ValueError('이관 검증 또는 기록이 올바르지 않습니다.')
    for path in (project_root, root, source.parent, queue, queue/'active', backup):
        if path.is_symlink() or not path.is_dir():
            raise ValueError('이관 또는 잠금 경로를 확인할 수 없습니다.')
    if target.parent.exists() or target.parent.is_symlink():
        raise ValueError('대상 경로가 이미 존재합니다.')
    with os.fdopen(os.open(queue/'execution.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK), 'r+') as queue_lock:
        fcntl.flock(queue_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if any((queue/'active').iterdir()):
            raise ValueError('GPU 작업 예약이 남아 있습니다.')
        with os.fdopen(os.open(backup/'worker.lock', os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK), 'r+') as backup_lock:
            fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            info = _verify(source, expected_size, expected_sha256)
            record = {'source': str(source), 'target': str(target), 'device': info.st_dev, 'inode': info.st_ino,
                      'size': expected_size, 'sha256': expected_sha256,
                      'rollback': '기록된 inode 확인 후 기존 경로로 덮어쓰기 없이 이동'}
            with journal.open('x', encoding='utf-8') as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            target.parent.mkdir()
            moved = False
            try:
                current = source.lstat()
                if source.is_symlink() or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError('인코더 파일이 이관 직전 교체됐습니다.')
                _rename_noreplace(source, target)
                moved = True
                after = _verify(target, expected_size, expected_sha256)
                if (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError('이관된 파일 식별자가 다릅니다.')
                validate()
            except BaseException:
                if moved:
                    current = target.lstat()
                    if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                        raise RuntimeError('파일이 바뀌어 자동 복구를 중단했습니다. 이관 기록을 확인하세요.')
                    _rename_noreplace(target, source)
                target.parent.rmdir()
                raise
            return record
