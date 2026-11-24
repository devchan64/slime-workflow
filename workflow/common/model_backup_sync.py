"""Create independently verifiable model backup snapshots without replacing files."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

from workflow.common.model_backup_inventory import inventory_model_tree, compare_inventories, _identity
from workflow.common.model_backup_service import read_backup_roots, latest_model_snapshot


def sync_snapshot(model, job_id, *, roots=None, progress=None, model_info=None, phase=None):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    if not isinstance(job_id, str) or not re.fullmatch(r'[0-9a-f]{32}', job_id):
        raise ValueError('백업 작업 ID가 올바르지 않습니다.')
    source_root, backup_root, _ = roots if roots is not None else read_backup_roots()
    source_root, backup_root = Path(source_root).resolve(strict=True), Path(backup_root).resolve(strict=True)
    model_root = source_root / model
    if model_root.is_symlink() or not model_root.is_dir():
        raise ValueError('모델 디렉터리를 찾을 수 없습니다.')
    inventory = inventory_model_tree(model_root, containment_root=source_root)
    if not inventory['complete']:
        raise ValueError('모델 파일 전체를 확인할 수 없습니다: ' + str(inventory['errors'][:3]))

    latest = latest_model_snapshot(backup_root, model)
    if latest is not None:
        snapshot_inventory = inventory_model_tree(latest, containment_root=backup_root)
        snapshot_inventory['files'].pop('.snapshot.json', None)
        same_sizes = (snapshot_inventory['complete'] and inventory['files'].keys() == snapshot_inventory['files'].keys()
                      and all(item['size'] == snapshot_inventory['files'][name]['size'] for name, item in inventory['files'].items()))
        with (latest / '.snapshot.json').open(encoding='utf-8') as stream:
            previous_manifest = json.load(stream)
        metadata = model_info if model_info is not None else {'state': 'unavailable'}
        if same_sizes and previous_manifest.get('model_metadata') == metadata:
            source_progress = (lambda path, done, total: phase('원본 해시 확인', path, done, total)) if phase else None
            backup_progress = (lambda path, done, total: phase('기존 스냅샷 해시 확인', path, done, total)) if phase else None
            original_hashes = inventory_model_tree(model_root, containment_root=source_root, hash_content=True, progress=source_progress)
            snapshot_hashes = inventory_model_tree(latest, containment_root=backup_root, hash_content=True, progress=backup_progress)
            snapshot_hashes['files'].pop('.snapshot.json', None)
            checked = compare_inventories(original_hashes, snapshot_hashes)
            final_inventory = inventory_model_tree(model_root, containment_root=source_root)
            if (checked['complete'] and final_inventory['complete'] and final_inventory['files'] == inventory['files']
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
    staging.mkdir()
    total = sum(item['size'] for item in inventory['files'].values())
    completed = 0
    files = []
    for relative, observed in inventory['files'].items():
        source = (model_root / relative).resolve(strict=True)
        source.relative_to(source_root)
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        before = source.stat()
        if (before.st_size != observed['size'] or before.st_mtime_ns != observed['mtime_ns']
                or f'{before.st_dev}:{before.st_ino}:{before.st_ctime_ns}' != observed['change_token']):
            raise ValueError('백업 전 원본 파일이 변경됐습니다: ' + relative)
        with source.open('rb') as reader, destination.open('xb') as writer:
            if _identity(os.fstat(reader.fileno())) != _identity(before):
                raise ValueError('백업 전 원본 파일이 교체됐습니다: ' + relative)
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
        with destination.open('rb') as reader:
            copied_hash = hashlib.file_digest(reader, 'sha256').hexdigest()
        if copied_hash != digest.hexdigest():
            raise ValueError('백업 파일의 SHA-256이 일치하지 않습니다: ' + relative)
        files.append({'path': relative, 'size': before.st_size, 'source_mtime_ns': before.st_mtime_ns,
                      'sha256': copied_hash, 'hash_origin': 'observed_during_backup'})
    final_inventory = inventory_model_tree(model_root, containment_root=source_root)
    if not final_inventory['complete'] or final_inventory['files'] != inventory['files']:
        raise ValueError('백업 중 모델 파일 목록 또는 파일 상태가 변경됐습니다.')
    manifest = {'version': 1, 'model': model, 'job_id': job_id,
                'created_at': datetime.now(timezone.utc).isoformat(), 'files': files,
                'model_metadata': model_info if model_info is not None else {'state': 'unavailable'},
                'model_metadata_note': '작업 시작 시 로컬에서 조회한 선언값이며 파일 해시와 별도입니다.'}
    with (staging / '.snapshot.json').open('x', encoding='utf-8') as output:
        json.dump(manifest, output, ensure_ascii=False)
    staging.rename(final)
    return {'model': model, 'snapshot_id': job_id, 'file_count': len(files), 'bytes': completed,
            'logical_bytes': completed, 'reused': False, 'path': str(final), 'verification': 'sha256_after_copy'}
