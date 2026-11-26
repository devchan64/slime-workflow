"""Create independently verifiable model backup snapshots without replacing files."""
from datetime import datetime, timezone
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from workflow.common.model_backup_inventory import inventory_model_tree, compare_inventories, _identity
from workflow.common.model_backup_service import read_backup_roots, latest_model_snapshot
from workflow.common.model_backup_targets import target_path
from workflow.common.model_storage_move import _rename_noreplace



def _resume_parent(staging, relative):
    """Open staging directories without following replacement symlinks."""
    parts = relative.split('/')
    if any(part in ('', '.', '..') or '\x00' in part for part in parts):
        raise ValueError('미완료 백업 경로가 올바르지 않습니다.')
    fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise

def sync_snapshot(model, job_id, *, roots=None, progress=None, model_info=None, phase=None, resume=False):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    if not isinstance(job_id, str) or not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('백업 작업 ID가 올바르지 않습니다.')
    source_root, backup_root, _ = roots if roots is not None else read_backup_roots()
    source_root, backup_root = Path(source_root).resolve(strict=True), Path(backup_root).resolve(strict=True)
    model_root = target_path(source_root, model)
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError('모델 디렉터리를 찾을 수 없습니다.')
    inventory = inventory_model_tree(model_root, containment_root=source_root)
    if not inventory['complete']:
        raise ValueError('모델 파일 전체를 확인할 수 없습니다: ' + str(inventory['errors'][:3]))
    if not inventory['files']:
        raise ValueError('백업할 모델 파일이 없습니다.')

    latest = latest_model_snapshot(backup_root, model)
    if latest is not None and not resume:
        snapshot_inventory = inventory_model_tree(latest, containment_root=backup_root)
        snapshot_inventory['files'].pop('.snapshot.json', None)
        same_sizes = (snapshot_inventory['complete'] and inventory['files'].keys() == snapshot_inventory['files'].keys()
                      and all(item['size'] == snapshot_inventory['files'][name]['size'] for name, item in inventory['files'].items()))
        manifest_path = latest / '.snapshot.json'
        manifest_before = manifest_path.lstat()
        if not stat.S_ISREG(manifest_before.st_mode) or manifest_before.st_size > 16 * 1024 * 1024:
            raise ValueError('기존 스냅샷 매니페스트를 확인할 수 없습니다.')
        with manifest_path.open(encoding='utf-8') as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(manifest_before):
                raise ValueError('기존 스냅샷 매니페스트가 변경됐습니다.')
            previous_manifest = json.load(stream)
            if _identity(os.fstat(stream.fileno())) != _identity(manifest_before):
                raise ValueError('기존 스냅샷 매니페스트가 변경됐습니다.')
        metadata = model_info if model_info is not None else {'state': 'unavailable'}
        if (not isinstance(previous_manifest, dict) or previous_manifest.get('version') != 1
                or previous_manifest.get('model') != model or previous_manifest.get('job_id') != latest.name):
            raise ValueError('기존 스냅샷 식별 정보가 올바르지 않습니다.')
        if same_sizes and previous_manifest.get('model_metadata') == metadata:
            source_progress = (lambda path, done, total: phase('원본 해시 확인', path, done, total)) if phase else None
            backup_progress = (lambda path, done, total: phase('기존 스냅샷 해시 확인', path, done, total)) if phase else None
            original_hashes = inventory_model_tree(model_root, containment_root=source_root, hash_content=True, progress=source_progress)
            snapshot_hashes = inventory_model_tree(latest, containment_root=backup_root, hash_content=True, progress=backup_progress)
            snapshot_hashes['files'].pop('.snapshot.json', None)
            checked = compare_inventories(original_hashes, snapshot_hashes)
            final_inventory = inventory_model_tree(model_root, containment_root=source_root)
            records = previous_manifest.get('files')
            manifest_matches = (isinstance(records, list) and len(records) == len(snapshot_hashes['files'])
                and all(isinstance(record, dict) and isinstance(record.get('path'), str)
                        and record['path'] in snapshot_hashes['files']
                        and type(record.get('size')) is int
                        and record.get('size') == snapshot_hashes['files'][record['path']]['size']
                        and record.get('sha256') == snapshot_hashes['files'][record['path']]['sha256']
                        and type(record.get('source_mtime_ns')) is int
                        and record['source_mtime_ns'] == inventory['files'][record['path']]['mtime_ns']
                        for record in records)
                and len({record['path'] for record in records}) == len(records))
            if _identity(manifest_path.lstat()) != _identity(manifest_before):
                raise ValueError('기존 스냅샷 매니페스트가 변경됐습니다.')
            if (checked['complete'] and final_inventory['complete'] and final_inventory['files'] == inventory['files']
                    and manifest_matches
                    and all(item['status'] == 'verified' for item in checked['files'])):
                return {'model': model, 'snapshot_id': latest.name, 'file_count': len(inventory['files']), 'bytes': 0,
                        'logical_bytes': sum(item['size'] for item in inventory['files'].values()), 'reused': True,
                        'path': str(latest), 'verification': 'sha256_comparison'}

    snapshots = backup_root / '.model-backup-snapshots'
    if snapshots.is_symlink():
        raise ValueError('백업 스냅샷 경로가 심볼릭 링크입니다.')
    snapshots.mkdir(exist_ok=True)
    snapshots = snapshots / model
    if snapshots.is_symlink():
        raise ValueError('백업 모델 경로가 심볼릭 링크입니다.')
    snapshots.mkdir(exist_ok=True)
    staging = snapshots / ('.pending-' + job_id)
    final = snapshots / job_id
    if resume:
        if staging.is_symlink() or not staging.is_dir() or final.exists() or final.is_symlink():
            raise ValueError('재개할 미완료 스냅샷을 확인할 수 없습니다.')
        for directory, dirs, names in os.walk(staging, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
            for name in dirs + names:
                path = Path(directory) / name
                info = path.lstat()
                mode = info.st_mode
                if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                    raise ValueError('미완료 스냅샷에 안전하지 않은 경로가 있습니다.')
                if stat.S_ISREG(mode) and info.st_nlink != 1:
                    raise ValueError('미완료 백업 파일의 하드링크를 사용할 수 없습니다.')
                if stat.S_ISREG(mode) and path.relative_to(staging).as_posix() not in inventory['files']:
                    raise ValueError('미완료 스냅샷에 예상하지 못한 파일이 있습니다.')
    else:
        staging.mkdir()
    total = sum(item['size'] for item in inventory['files'].values())
    completed = 0
    resumed_bytes = 0
    files = []
    for relative, observed in inventory['files'].items():
        source = (model_root / relative).resolve(strict=True)
        source.relative_to(source_root)
        destination = staging / relative
        stack = ExitStack()
        if resume:
            parent_fd, leaf = _resume_parent(staging, relative)
            stack.callback(os.close, parent_fd)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
        with stack:
            digest = hashlib.sha256()
            before = source.stat()
            if (before.st_size != observed['size'] or before.st_mtime_ns != observed['mtime_ns']
                    or f'{before.st_dev}:{before.st_ino}:{before.st_ctime_ns}' != observed['change_token']):
                raise ValueError('백업 전 원본 파일이 변경됐습니다: ' + relative)
            with source.open('rb') as reader:
                if _identity(os.fstat(reader.fileno())) != _identity(before):
                    raise ValueError('백업 전 원본 파일이 교체됐습니다: ' + relative)
                try:
                    previous = os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False) if resume else None
                except FileNotFoundError:
                    previous = None
                if resume and previous is not None:
                    if not stat.S_ISREG(previous.st_mode):
                        raise ValueError('미완료 백업 파일 경로가 안전하지 않습니다: ' + relative)
                    if previous.st_nlink != 1:
                        raise ValueError('미완료 백업 파일의 하드링크를 사용할 수 없습니다: ' + relative)
                    if previous.st_size > before.st_size:
                        raise ValueError('미완료 백업 파일이 원본보다 큽니다: ' + relative)
                    with os.fdopen(os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd), 'rb') as partial:
                        if _identity(os.fstat(partial.fileno())) != _identity(previous):
                            raise ValueError('미완료 백업 파일이 변경됐습니다: ' + relative)
                        checked_prefix = 0
                        while chunk := partial.read(1024 * 1024):
                            if reader.read(len(chunk)) != chunk:
                                raise ValueError('미완료 백업과 원본의 내용이 다릅니다: ' + relative)
                            digest.update(chunk)
                            completed += len(chunk)
                            resumed_bytes += len(chunk)
                            checked_prefix += len(chunk)
                            if phase:
                                phase('기존 부분 대조', relative, checked_prefix, previous.st_size)
                        if _identity(os.fstat(partial.fileno())) != _identity(previous):
                            raise ValueError('미완료 백업 파일이 검증 중 변경됐습니다: ' + relative)
                    if progress:
                        progress(completed, total, relative)
                    fd = os.open(leaf, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=parent_fd)
                    if _identity(os.fstat(fd)) != _identity(previous):
                        os.close(fd)
                        raise ValueError('미완료 백업 파일이 교체됐습니다: ' + relative)
                    writer = os.fdopen(fd, 'ab')
                else:
                    writer = (os.fdopen(os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=parent_fd), 'wb')
                              if resume else destination.open('xb'))
                with writer:
                    while chunk := reader.read(1024 * 1024):
                        writer.write(chunk)
                        digest.update(chunk)
                        completed += len(chunk)
                        if progress:
                            progress(completed, total, relative)
                if _identity(os.fstat(reader.fileno())) != _identity(before):
                    raise ValueError('백업 중 원본 파일이 변경됐습니다: ' + relative)
            if _identity(source.stat()) != _identity(before):
                raise ValueError('백업 중 원본 파일이 교체됐습니다: ' + relative)
            with (os.fdopen(os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd), 'rb')
                  if resume else destination.open('rb')) as reader:
                copied_digest = hashlib.sha256()
                verified_bytes = 0
                if phase:
                    phase('백업 사본 해시 확인', relative, verified_bytes, before.st_size)
                for chunk in iter(lambda: reader.read(8 * 1024 * 1024), b''):
                    copied_digest.update(chunk)
                    verified_bytes += len(chunk)
                    if phase:
                        phase('백업 사본 해시 확인', relative, verified_bytes, before.st_size)
                copied_hash = copied_digest.hexdigest()
            if copied_hash != digest.hexdigest():
                raise ValueError('백업 파일의 SHA-256이 일치하지 않습니다: ' + relative)
        files.append({'path': relative, 'size': before.st_size, 'source_mtime_ns': before.st_mtime_ns,
                      'sha256': copied_hash, 'hash_origin': 'observed_during_backup'})
    final_inventory = inventory_model_tree(model_root, containment_root=source_root)
    if not final_inventory['complete'] or final_inventory['files'] != inventory['files']:
        raise ValueError('백업 중 모델 파일 목록 또는 파일 상태가 변경됐습니다.')
    manifest = {'version': 1, 'model': model, 'job_id': job_id,
                'created_at': datetime.now(timezone.utc).isoformat(), 'files': files,
                'link_policy': 'follow_within_model_root_as_files',
                'link_policy_note': '모델 루트 내부 링크의 대상 파일을 복사하며 링크 관계는 복원하지 않습니다.',
                'model_metadata': model_info if model_info is not None else {'state': 'unavailable'},
                'model_metadata_note': '작업 시작 시 로컬에서 조회한 선언값이며 파일 해시와 별도입니다.'}
    with (staging / '.snapshot.json').open('x', encoding='utf-8') as output:
        json.dump(manifest, output, ensure_ascii=False)
    _rename_noreplace(staging, final)
    return {'model': model, 'snapshot_id': job_id, 'file_count': len(files), 'bytes': completed,
            'logical_bytes': completed, 'resumed_bytes': resumed_bytes, 'copied_bytes': completed - resumed_bytes,
            'reused': False, 'path': str(final), 'verification': 'sha256_after_copy'}
