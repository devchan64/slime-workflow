"""Read-only model inventory and backup comparison.

The inventory describes observations, not a trusted model manifest. Hashes
are calculated only when requested and are never labelled as upstream hashes.
"""
import hashlib
import os
from pathlib import Path
import stat


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _file_info(path, hash_content, progress=None):
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('일반 파일이 아닙니다')
    result = {'size': before.st_size, 'mtime_ns': before.st_mtime_ns,
              'change_token': f'{before.st_dev}:{before.st_ino}:{before.st_ctime_ns}'}
    if hash_content:
        digest = hashlib.sha256()
        read_bytes = 0
        with path.open('rb') as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ValueError('검증 전 파일이 변경됐습니다')
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                read_bytes += len(chunk)
                if progress:
                    progress(read_bytes, before.st_size)
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ValueError('검증 중 파일이 변경됐습니다')
        if _identity(path.stat()) != _identity(before):
            raise ValueError('검증 중 파일이 교체됐습니다')
        result['sha256'] = digest.hexdigest()
        result['hash_origin'] = 'observed'
    return result


def inventory_model_tree(root, *, hash_content=False, containment_root=None, progress=None):
    """Observe files and links without traversing outside root or hiding errors."""
    root = Path(root).resolve(strict=True)
    boundary = Path(containment_root).resolve(strict=True) if containment_root else root
    root.relative_to(boundary)
    if not root.is_dir():
        raise ValueError('모델 경로가 디렉터리가 아닙니다')
    files, errors = {}, []

    def visit(directory, relative, ancestors):
        try:
            actual = directory.resolve(strict=True)
            actual.relative_to(boundary)
            info = actual.stat()
            key = (info.st_dev, info.st_ino)
            if key in ancestors:
                raise ValueError('순환 심볼릭 링크')
            with os.scandir(directory) as entries:
                names = sorted(entry.name for entry in entries)
            for name in names:
                path, child = directory / name, relative / name
                try:
                    resolved = path.resolve(strict=True)
                    resolved.relative_to(boundary)
                    if resolved.is_dir():
                        visit(path, child, ancestors | {key})
                    else:
                        callback = (lambda done, total: progress(child.as_posix(), done, total)) if progress else None
                        files[child.as_posix()] = _file_info(path, hash_content, callback)
                except (OSError, ValueError) as error:
                    errors.append({'path': child.as_posix(), 'reason': str(error)})
        except (OSError, ValueError) as error:
            errors.append({'path': relative.as_posix(), 'reason': str(error)})

    visit(root, Path('.'), set())
    return {'files': files, 'errors': errors, 'complete': not errors,
            'comparison_basis': 'sha256' if hash_content else 'size_and_mtime'}


def compare_inventories(source, backup):
    """Compare observations; unmatched backup files are never deletion requests."""
    if source['comparison_basis'] != backup['comparison_basis']:
        raise ValueError('비교 기준이 일치하지 않습니다')
    basis = source['comparison_basis']
    changes = []
    for name in sorted(source['files'].keys() | backup['files'].keys()):
        left, right = source['files'].get(name), backup['files'].get(name)
        if left is None:
            status = 'backup_only' if source['complete'] else 'unknown'
        elif right is None:
            status = 'missing' if backup['complete'] else 'unknown'
        elif basis == 'sha256':
            status = 'verified' if left['size'] == right['size'] and left['sha256'] == right['sha256'] else 'different'
        else:
            status = 'matches_metadata' if left['size'] == right['size'] and left['mtime_ns'] == right['mtime_ns'] else 'different'
        changes.append({'path': name, 'status': status, 'source': left, 'backup': right})
    return {'comparison_basis': basis, 'complete': source['complete'] and backup['complete'],
            'source_errors': source['errors'], 'backup_errors': backup['errors'], 'files': changes}
