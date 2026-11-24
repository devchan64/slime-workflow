"""Preserve a verified source installation outside the active model tree."""
import json
import os
from pathlib import Path

from workflow.common.model_backup_inventory import inventory_model_tree
from workflow.common.model_visual_migration import _scan_no_links
from workflow.domains.image.flux_visual_review import resolve_visual_model
from workflow.domains.trellis_experiment.offline_loader import resolve_trellis_model


def retain_published_original(root, name):
    resolvers = {'flux-report-vision': resolve_visual_model, 'trellis-image-large': resolve_trellis_model}
    if name not in resolvers:
        raise ValueError('지원하지 않는 모델입니다.')
    root = Path(root)
    source = root / name
    active = root / 'models' / name
    resolver = resolvers[name]
    if root.is_symlink() or source.is_symlink() or not source.is_dir() or resolver(root) != active:
        raise ValueError('원본 또는 게시된 활성 설치본을 확인할 수 없습니다.')
    _scan_no_links(source)
    _scan_no_links(active)
    before = inventory_model_tree(source, hash_content=True)
    copied = inventory_model_tree(active, hash_content=True)
    source_files = before['files']
    active_files = {key: value for key, value in copied['files'].items() if key != '.catalog-migration.json'}
    if (not before['complete'] or not copied['complete'] or set(source_files) != set(active_files)
            or any((info['sha256'], info['size']) != (active_files[name]['sha256'], active_files[name]['size'])
                   for name, info in source_files.items())):
        raise ValueError('원본과 활성 설치본이 일치하지 않습니다.')
    retained_root = root.parent / '.local/model-catalog/retained'
    for path in (root.parent / '.local', root.parent / '.local/model-catalog', retained_root):
        if path.is_symlink():
            raise ValueError('보존 경로에 심볼릭 링크가 있습니다.')
        path.mkdir(exist_ok=True)
    if source.stat().st_dev != retained_root.stat().st_dev:
        raise ValueError('보존 경로가 다른 파일시스템입니다.')
    reservation = retained_root / name
    reservation.mkdir()
    record = {'source': str(source), 'retained': str(reservation / 'original'), 'active': str(active),
              'file_count': len(source_files), 'verification': 'source-copy-sha256',
              'rollback': '보존된 original 디렉터리를 기존 source 경로로 이동'}
    with (reservation / 'transaction.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    _scan_no_links(source)
    after = inventory_model_tree(source, hash_content=True)
    _scan_no_links(active)
    active_after = inventory_model_tree(active, hash_content=True)
    if (not after['complete'] or not active_after['complete'] or before['files'] != after['files']
            or copied['files'] != active_after['files'] or resolver(root) != active):
        raise ValueError('원본 또는 활성 설치본이 확인 중 변경됐습니다.')
    os.rename(source, reservation / 'original')
    return record


def retain_visual_original(root):
    return retain_published_original(root, 'flux-report-vision')
