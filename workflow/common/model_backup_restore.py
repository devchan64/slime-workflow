"""Restore a hash-verified model file from the locally configured backup."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


CONFIG_PATH = Path(__file__).resolve().parents[2] / '.local/hermes/model-backup.json'


def _default_file_mode():
    """Respect the process umask without changing its process-wide value."""
    try:
        with open('/proc/self/status', encoding='ascii') as status:
            for line in status:
                if line.startswith('Umask:'):
                    return 0o666 & ~int(line.split()[1], 8)
    except (OSError, UnicodeError, ValueError, IndexError):
        pass
    return 0o600


def restore_verified_backup(target, expected_sha256, expected_size=None, report=None, outcome=None, backup_source_target=None, hash_type='sha256'):
    """Copy an absent file only after validating its complete expected digest."""
    if hash_type not in ('sha256', 'git-sha1') or (hash_type == 'git-sha1' and expected_size is None):
        raise ValueError('지원하지 않는 백업 해시 형식입니다.')
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        source_root = Path(config['source_path']).resolve(strict=True)
        backup_root = Path(config['local_mount_path'])
        if not backup_root.is_absolute() or not backup_root.is_dir():
            if outcome:
                outcome('백업 경로에 접근할 수 없음')
            return False
        # GVFS paths are meaningful only while the user's FUSE mount exists.
        if str(backup_root).startswith('/run/user/'):
            mount_root = Path('/').joinpath(*backup_root.parts[1:5])
            if mount_root.name != 'gvfs' or not os.path.ismount(mount_root):
                if outcome:
                    outcome('백업 마운트를 확인할 수 없음')
                return False
        from workflow.common.model_backup_mount import verify_smb_mount
        verify_smb_mount(backup_root, config.get('samba_uri'))
        Path(target).resolve().relative_to(source_root)
        relative = Path(backup_source_target or target).resolve().relative_to(source_root)
        candidates = [backup_root / relative]
        if len(relative.parts) > 1:
            snapshots = backup_root / '.model-backup-snapshots' / relative.parts[0]
            if snapshots.is_dir() and not snapshots.is_symlink():
                for snapshot in sorted(snapshots.iterdir(), key=lambda item: item.stat().st_mtime_ns, reverse=True):
                    if snapshot.is_symlink() or not snapshot.is_dir() or len(snapshot.name) != 32 or any(char not in '0123456789abcdef' for char in snapshot.name):
                        continue
                    if not (snapshot / '.snapshot.json').is_file():
                        continue
                    candidates.append(snapshot.joinpath(*relative.parts[1:]))
    except FileNotFoundError:
        return False
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        if outcome:
            outcome('백업 설정 또는 경로 확인 실패')
        return False

    for candidate in candidates:
        temporary = None
        try:
            if not candidate.is_file():
                continue
            if expected_size is not None and candidate.stat().st_size != expected_size:
                if outcome:
                    outcome('백업 파일 크기 불일치')
                continue
            digest = hashlib.sha256() if hash_type == 'sha256' else hashlib.sha1(usedforsecurity=False)
            if hash_type == 'git-sha1':
                digest.update(f'blob {expected_size}\0'.encode('ascii'))
            count = 0
            with candidate.open('rb') as source, tempfile.NamedTemporaryFile(dir=Path(target).parent, prefix='.backup-restore-', delete=False) as output:
                temporary = Path(output.name)
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                    if report:
                        report(count)
            if digest.hexdigest() != expected_sha256 or (expected_size is not None and count != expected_size):
                if outcome:
                    outcome('백업 파일 해시 불일치')
                continue
            os.chmod(temporary, _default_file_mode())
            try:
                os.link(temporary, target)
            except FileExistsError:
                return False
            return True
        except OSError:
            if outcome:
                outcome('백업 파일 복원 실패')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return False
