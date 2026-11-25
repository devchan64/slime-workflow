"""Restore a hash-verified model file from the locally configured backup."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


CONFIG_PATH = Path(__file__).resolve().parents[2] / '.local/hermes/model-backup.json'
# Existing backup data predates the reorganized installation. This is a
# one-way lookup alias only; content still has to match the caller's hash.
LEGACY_BACKUP_PREFIXES = {('models', 'flux-report-vision'): ('flux-report-vision',),
                          ('models', 'trellis-dinov2'): ('trellis-dinov2',),
                          ('models', 'trellis-image-large'): ('trellis-image-large',),
                          ('models', 'hermes-coding'): ('hermes-agent',),
                          ('models', 'qwen3-embedding-0.6b'): ('writer-agent',),
                          ('models', 'translategemma-4b'): ('prompt-translation',),
                          ('models', 'audio', 'heartmula'): ('music', 'music-heartmula'),
                          ('models', 'audio', 'dasheng-audiogen'): ('music', 'sfx-dasheng-audiogen'),
                          ('cache', 'huggingface'): ('huggingface',)}

# The flattened paths may need files from either earlier layout. These aliases
# only select candidates; the caller's trusted digest still verifies all bytes.
FLATTENED_BACKUP_PREFIXES = {
    ('qwen3.8-27b-iq4-xs',): (('hermes-coding',), ('models', 'hermes-coding'), ('hermes-agent',)),
    ('heartmula-oss-3b', 'generation'): (('audio', 'heartmula', 'bundle'), ('models', 'audio', 'heartmula', 'bundle'), ('music', 'music-heartmula', 'bundle')),
    ('heartmula-oss-3b',): (('audio', 'heartmula', 'bundle', 'HeartMuLa-oss-3B'), ('models', 'audio', 'heartmula', 'bundle', 'HeartMuLa-oss-3B'), ('music', 'music-heartmula', 'bundle', 'HeartMuLa-oss-3B')),
    ('heartcodec-oss',): (('audio', 'heartmula', 'bundle', 'HeartCodec-oss'), ('models', 'audio', 'heartmula', 'bundle', 'HeartCodec-oss'), ('music', 'music-heartmula', 'bundle', 'HeartCodec-oss')),
    ('heartcodec-reference-encoder',): (('audio', 'heartmula', 'codec-reference-encoder'), ('models', 'audio', 'heartmula', 'codec-reference-encoder'), ('music', 'music-heartmula', 'codec-reference-encoder')),
    ('dasheng-audiogen',): (('audio', 'dasheng-audiogen', 'model'), ('models', 'audio', 'dasheng-audiogen', 'model'), ('music', 'sfx-dasheng-audiogen', 'model')),
    ('flan-t5-large',): (('audio', 'dasheng-audiogen', 'text-encoder'), ('models', 'audio', 'dasheng-audiogen', 'text-encoder'), ('music', 'sfx-dasheng-audiogen', 'text-encoder')),
    ('dasheng-tokenizer',): (('audio', 'dasheng-audiogen', 'audio-tokenizer'), ('models', 'audio', 'dasheng-audiogen', 'audio-tokenizer'), ('music', 'sfx-dasheng-audiogen', 'audio-tokenizer')),
    ('demucs',): (('audio', 'demucs'), ('audio', 'heartmula', 'demucs'), ('models', 'audio', 'heartmula', 'demucs'), ('music', 'music-heartmula', 'demucs')),
    ('audio', 'demucs'): (('audio', 'heartmula', 'demucs'), ('models', 'audio', 'heartmula', 'demucs'), ('music', 'music-heartmula', 'demucs')),
    ('hermes-coding',): (('models', 'hermes-coding'), ('hermes-agent',)),
    ('qwen3-embedding-0.6b',): (('models', 'qwen3-embedding-0.6b'), ('writer-agent',)),
    ('translategemma-4b',): (('models', 'translategemma-4b'), ('prompt-translation',)),
    ('audio', 'heartmula'): (('models', 'audio', 'heartmula'), ('music', 'music-heartmula')),
    ('audio', 'dasheng-audiogen'): (('models', 'audio', 'dasheng-audiogen'), ('music', 'sfx-dasheng-audiogen')),
    ('flux-report-vision',): (('models', 'flux-report-vision'),),
}


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


def _completed_snapshots(directory):
    """Find usable snapshot directories without following invalid entries."""
    try:
        if directory.is_symlink() or not directory.is_dir():
            return []
        entries = []
        for entry in directory.iterdir():
            try:
                if (entry.is_symlink() or not entry.is_dir() or len(entry.name) != 32
                        or any(char not in '0123456789abcdef' for char in entry.name)
                        or not (entry / '.snapshot.json').is_file()):
                    continue
                entries.append((entry.stat().st_mtime_ns, entry))
            except OSError:
                continue
        return [entry for _, entry in sorted(entries, key=lambda item: item[0], reverse=True)]
    except OSError:
        return []


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
        resolved_backup_root = backup_root.resolve(strict=True)
        Path(target).resolve().relative_to(source_root)
        relative = Path(backup_source_target or target).resolve().relative_to(source_root)
        relatives = [relative]
        for new_prefix, old_prefix in LEGACY_BACKUP_PREFIXES.items():
            if relative.parts[:len(new_prefix)] == new_prefix and len(relative.parts) > len(new_prefix):
                relatives.append(Path(*old_prefix, *relative.parts[len(new_prefix):]))
        for new_prefix, old_prefixes in FLATTENED_BACKUP_PREFIXES.items():
            if relative.parts[:len(new_prefix)] == new_prefix and len(relative.parts) > len(new_prefix):
                relatives.extend(Path(*old_prefix, *relative.parts[len(new_prefix):]) for old_prefix in old_prefixes)
        candidates = []
        for lookup in relatives:
            candidates.append(backup_root / lookup)
            if len(lookup.parts) > 1:
                snapshots = backup_root / '.model-backup-snapshots' / lookup.parts[0]
                for snapshot in _completed_snapshots(snapshots):
                    candidates.append(snapshot.joinpath(*lookup.parts[1:]))
        from workflow.common.model_backup_targets import CATALOG_TARGETS, target_parts
        for name, parts in CATALOG_TARGETS.items():
            # Snapshots created after a move are rooted at the current target;
            # older snapshots may still use the original catalog layout.
            try:
                current_parts = target_parts(source_root, name)
            except (OSError, ValueError):
                current_parts = parts
            for prefix in dict.fromkeys((current_parts, parts)):
                for lookup in relatives:
                    if lookup.parts[:len(prefix)] != prefix or len(lookup.parts) <= len(prefix):
                        continue
                    snapshots = backup_root / '.model-backup-snapshots' / name
                    for snapshot in _completed_snapshots(snapshots):
                        candidates.append(snapshot.joinpath(*lookup.parts[len(prefix):]))
    except FileNotFoundError:
        return False
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        if outcome:
            outcome('백업 설정 또는 경로 확인 실패')
        return False

    for candidate in candidates:
        temporary = None
        try:
            try:
                candidate.resolve(strict=True).relative_to(resolved_backup_root)
            except (OSError, ValueError):
                if outcome:
                    outcome('백업 경로 밖의 파일 또는 접근할 수 없는 파일을 건너뜀')
                continue
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
