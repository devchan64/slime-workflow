"""Preserve an existing preparation record if a refresh fails."""
import fcntl
import os
from pathlib import Path
import stat
import tempfile


def guarded_refresh(model_root, callback):
    """Restore the previous record only if refresh failed and no record exists.

    The preparation lock is held for snapshot and restoration, but released
    around callback because the existing preparation takes the same lock.
    """
    root = Path(model_root)
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise ValueError('준비 기록 디렉터리에 심볼릭 링크를 사용할 수 없습니다.')
    root.mkdir(parents=True, exist_ok=True)
    record, lock = root/'prepared.json', root/'prepare.lock'
    if lock.is_symlink():
        raise ValueError('준비 잠금에 심볼릭 링크를 사용할 수 없습니다.')
    backup = None
    with lock.open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            info = record.lstat()
        except FileNotFoundError:
            info = None
        if info is not None:
            if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024 * 1024:
                raise ValueError('기존 준비 기록을 안전하게 보존할 수 없습니다.')
            with tempfile.NamedTemporaryFile(dir=root, prefix='.prepared-backup-', delete=False) as copy:
                backup = Path(copy.name)
                try:
                    with record.open('rb') as previous:
                        opened = os.fstat(previous.fileno())
                        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns):
                            raise ValueError('기존 준비 기록이 변경됐습니다.')
                        copy.write(previous.read(16 * 1024 * 1024 + 1))
                        after = os.fstat(previous.fileno())
                        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns):
                            raise ValueError('기존 준비 기록을 읽는 중 변경됐습니다.')
                    copy.flush()
                    os.fsync(copy.fileno())
                    os.chmod(backup, stat.S_IMODE(info.st_mode))
                except BaseException:
                    backup.unlink(missing_ok=True)
                    raise
    try:
        return callback()
    except BaseException as error:
        if backup is not None:
            try:
                with lock.open('a') as stream:
                    fcntl.flock(stream, fcntl.LOCK_EX)
                    try:
                        os.link(backup, record)
                    except FileExistsError:
                        pass
            except OSError as restore_error:
                error.add_note(f'이전 준비 기록 자동 복원 실패: {restore_error}; 보존 사본: {backup}')
                backup = None  # Leave the temporary copy for recovery.
        raise
    finally:
        if backup is not None:
            backup.unlink(missing_ok=True)
