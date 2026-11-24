"""Copy and publish the FLUX visual model while preserving its original path."""
import json
import os
from pathlib import Path
import shutil
import stat
from datetime import datetime, timezone

from workflow.common.model_backup_inventory import inventory_model_tree
from workflow.domains.image.flux_visual_review import MODEL_ID, REVISION


def _scan_no_links(root):
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        for name in dirs + files:
            mode = (Path(directory) / name).lstat().st_mode
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError('심볼릭 링크 또는 일반 파일이 아닌 항목은 이관하지 않습니다.')


def copy_published_model(root, name, model_id, revision, required_files):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('모델 루트를 확인할 수 없습니다.')
    if not isinstance(name, str) or not name or name in ('.', '..') or '/' in name or '\\' in name:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    source, parent = root / name, root / 'models'
    destination = parent / name
    if source.is_symlink() or not source.is_dir() or parent.is_symlink():
        raise ValueError('원본 또는 대상 경로를 확인할 수 없습니다.')
    if (source / '.catalog-migration.json').exists():
        raise ValueError('원본에 이관 표시가 이미 있습니다.')
    _scan_no_links(source)
    before = inventory_model_tree(source, hash_content=True)
    if not before['complete'] or not set(required_files) <= before['files'].keys():
        raise ValueError('원본 파일을 검증하지 못했습니다.')
    parent.mkdir(exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError('대상 상위 경로가 올바르지 않습니다.')
    destination.mkdir()  # Exclusive reservation. Failures leave it unpublished.
    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=False)
    _scan_no_links(source)
    _scan_no_links(destination)
    after = inventory_model_tree(source, hash_content=True)
    copied = inventory_model_tree(destination, hash_content=True)
    if not after['complete'] or not copied['complete'] or before['files'] != after['files']:
        raise ValueError('복사 중 원본이 변경되었거나 파일 확인이 실패했습니다.')
    if set(after['files']) != set(copied['files']) or any(
            (info['sha256'], info['size']) != (copied['files'][name]['sha256'], copied['files'][name]['size'])
            for name, info in after['files'].items()):
        raise ValueError('복사본이 원본과 일치하지 않습니다.')
    marker = {'schema_version': 1, 'model_id': model_id, 'revision': revision, 'state': 'verified',
              'file_count': len(copied['files']), 'verified_at': datetime.now(timezone.utc).isoformat(),
              'verification': 'source-copy-sha256'}
    temporary = destination / '.catalog-migration.pending'
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(marker, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, destination / '.catalog-migration.json')
    temporary.unlink()
    return {'source': str(source), 'destination': str(destination), 'files': len(copied['files']),
            'bytes': sum(item['size'] for item in copied['files'].values()), 'source_preserved': True}


def copy_visual_model(root):
    return copy_published_model(root, 'flux-report-vision', MODEL_ID, REVISION,
                                ('config.json', 'model.safetensors'))
