"""Normalize existing model manifests without treating declarations as proof."""
import json
from pathlib import Path
import re

from workflow.common.model_backup_service import read_model_source, read_backup_roots, latest_model_snapshot
from workflow.common.model_file_inventory import resolve_model_inventory_paths
from workflow.common.model_backup_targets import target_path

SHA256 = re.compile(r'^[0-9a-fA-F]{64}$')


def model_metadata(model, *, config_path=None, service_paths=None):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    source, _ = read_model_source(config_path)
    folder = target_path(source, model)
    origin = 'local'
    if folder.is_symlink():
        raise ValueError('모델 디렉터리를 찾을 수 없습니다.')
    if not folder.is_dir():
        _, backup, _ = read_backup_roots(config_path)
        snapshot = latest_model_snapshot(backup, model)
        if snapshot is None:
            folder = target_path(backup, model, layout_root=source)
            if folder.is_symlink() or not folder.is_dir():
                raise ValueError('모델과 백업을 찾을 수 없습니다.')
            origin = 'backup_directory'
        else:
            try:
                manifest = json.loads((snapshot / '.snapshot.json').read_text(encoding='utf-8'))
                saved = manifest.get('model_metadata')
                if not isinstance(saved, dict):
                    saved = {}
                result = {'version': 1, 'model': model, 'origin': 'backup_snapshot', 'snapshot_id': snapshot.name,
                          'manifest_state': saved.get('manifest_state', 'unavailable'),
                          'services': saved.get('services', []), 'declared_sources': saved.get('declared_sources', []),
                          'declared_files': saved.get('declared_files', []),
                          'note': '백업 시 저장한 선언값입니다. 현재 파일 검증 결과가 아닙니다.'}
                if any(not isinstance(result[name], list) for name in ('services', 'declared_sources', 'declared_files')):
                    raise ValueError('스냅샷 메타정보 형식 오류')
                return result
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise ValueError('백업 메타정보를 읽을 수 없습니다.') from error
    services = []
    paths = resolve_model_inventory_paths() if service_paths is None else service_paths
    for service, roots in paths.items():
        for path in roots:
            try:
                path = Path(path).resolve()
                if path == folder or path.is_relative_to(folder) or folder.is_relative_to(path):
                    services.append(service)
                    break
            except (OSError, ValueError):
                continue
    result = {'version': 1, 'model': model, 'origin': origin, 'services': sorted(services),
              'manifest_state': 'missing', 'declared_sources': [], 'declared_files': []}
    manifest = folder / 'manifest.json'
    preparation_record = False
    if not manifest.exists():
        manifest = folder / 'verified-manifest.json'
        if not manifest.exists():
            prepared = folder / 'prepared.json'
            if prepared.exists() or prepared.is_symlink():
                manifest = prepared
                preparation_record = True
            else:
                manifest = None
        if manifest is None:
            if model in ('hermes-agent', 'catalog-hermes-coding'):
                from workflow.common.hermes_model_download import HERMES_MODEL_FILENAME
                ready = folder / 'ready.sha256'
                try:
                    if not ready.exists() and not ready.is_symlink():
                        return result
                    if ready.is_symlink() or not ready.is_file() or ready.stat().st_size > 4096:
                        raise ValueError('준비 기록을 읽을 수 없습니다.')
                    record = json.loads(ready.read_text(encoding='utf-8'))
                    digest = record.get('sha256')
                    if (not isinstance(digest, str) or not SHA256.fullmatch(digest)
                            or type(record.get('size')) is not int or record['size'] < 0
                            or type(record.get('mtime_ns')) is not int):
                        raise ValueError('준비 기록 형식 오류')
                    result['manifest_state'] = 'ready_record'
                    result['declared_files'] = [{'path': HERMES_MODEL_FILENAME, 'sha256': digest.lower(),
                                                 'hash_origin': 'local_ready_record', 'repository': None,
                                                 'revision': None}]
                except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
                    result['manifest_state'] = 'unavailable'
            return result
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 4 * 1024 * 1024:
        result['manifest_state'] = 'unavailable'
        return result
    try:
        value = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError):
        result['manifest_state'] = 'unavailable'
        return result
    result['manifest_state'] = 'prepared_record' if preparation_record else 'read'

    def add_file(path, digest, repo=None, revision=None):
        if not isinstance(path, str) or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            return
        item_path = Path(path)
        if item_path.is_absolute() or '..' in item_path.parts:
            return
        # Some existing manifests use paths relative to .model instead of the model directory.
        if item_path.parts[:2] == ('.model', model):
            item_path = Path(*item_path.parts[2:])
        if not item_path.parts or item_path.parts[0] == '.model':
            return
        result['declared_files'].append({'path': item_path.as_posix(), 'sha256': digest.lower(),
                                         'hash_origin': 'local_preparation_record' if preparation_record else 'local_manifest', 'repository': repo, 'revision': revision})

    if isinstance(value, list):
        for entry in value:
            if isinstance(entry, dict):
                repo, revision = entry.get('repo'), entry.get('revision')
                add_file(entry.get('path'), entry.get('sha256'), repo, revision)
                if isinstance(repo, str) and isinstance(revision, str):
                    source_record = {'repository': repo, 'revision': revision}
                    if source_record not in result['declared_sources']:
                        result['declared_sources'].append(source_record)
    elif isinstance(value, dict):
        repo = value.get('repo') or value.get('repository') or value.get('model_id')
        revision = value.get('revision')
        if isinstance(repo, str) and isinstance(revision, str):
            result['declared_sources'].append({'repository': repo, 'revision': revision})
        if preparation_record:
            sources = value.get('sources', value.get('revisions', []))
            if isinstance(sources, list):
                for entry in sources:
                    if isinstance(entry, list) and len(entry) >= 2 and all(isinstance(part, str) for part in entry[:2]):
                        source_record = {'repository': entry[0], 'revision': entry[1]}
                        if source_record not in result['declared_sources']:
                            result['declared_sources'].append(source_record)
        hashes = value.get('sha256') or value.get('files')
        if isinstance(hashes, dict):
            for path, digest in hashes.items():
                add_file(path, digest, repo, revision)
        elif isinstance(hashes, list):
            for item in hashes:
                if isinstance(item, dict):
                    add_file(item.get('path'), item.get('sha256'), repo, revision)
    return result
