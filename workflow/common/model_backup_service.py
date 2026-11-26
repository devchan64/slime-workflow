"""Local configuration and read-only model backup observations."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import stat

from workflow.common.model_backup_inventory import compare_inventories, inventory_model_tree, _identity
from workflow.common.model_backup_restore import CONFIG_PATH
from workflow.common.model_backup_mount import verify_smb_mount
from workflow.common.model_backup_targets import CATALOG_TARGETS, LEGACY_TARGETS, target_path, target_parts


def read_model_source(config_path=None):
    path = Path(config_path or CONFIG_PATH)
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
        source = Path(config['source_path'])
        if not source.is_absolute() or not source.is_dir():
            raise ValueError('모델 원본 경로에 접근할 수 없습니다.')
        return source.resolve(strict=True), config
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('모델 백업 설정을 읽을 수 없습니다.') from error


def read_backup_roots(config_path=None):
    source, config = read_model_source(config_path)
    try:
        backup = Path(config['local_mount_path'])
        if not backup.is_absolute() or not backup.is_dir():
            raise ValueError('백업 경로에 접근할 수 없습니다.')
        if str(backup).startswith('/run/user/'):
            mount_root = Path('/').joinpath(*backup.parts[1:5])
            if mount_root.name != 'gvfs' or not os.path.ismount(mount_root):
                raise ValueError('GVFS 백업 마운트를 확인할 수 없습니다.')
        verify_smb_mount(backup, config.get('samba_uri'))
        return source, backup.resolve(strict=True), config.get('samba_uri')
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('모델 백업 설정을 읽을 수 없습니다.') from error


def _directory_presence(root, name, *, layout_root=None):
    """Treat access errors as unknown, not as a missing directory."""
    try:
        return stat.S_ISDIR(target_path(root, name, layout_root=layout_root).lstat().st_mode)
    except FileNotFoundError:
        return False


def list_backup_models(config_path=None):
    source, config = read_model_source(config_path)
    try:
        _, backup, _ = read_backup_roots(config_path)
        backup_error = None
    except ValueError:
        backup = None
        backup_error = '백업 경로에 접근할 수 없습니다.'
    models = {}
    snapshot_names = None
    for item in sorted(source.iterdir(), key=lambda value: value.name):
        if item.is_dir() and not item.is_symlink():
            present = None
            if backup is not None:
                try:
                    present = stat.S_ISDIR((backup / item.name).lstat().st_mode)
                except FileNotFoundError:
                    present = False
                except OSError:
                    pass
            models[item.name] = {'name': item.name, 'local_present': True, 'backup_present': present, 'snapshot_present': None}
    if backup is not None:
        try:
            for item in backup.iterdir():
                if not item.name.startswith('.') and item.is_dir() and not item.is_symlink():
                    models.setdefault(item.name, {'name': item.name, 'local_present': False, 'backup_present': True, 'snapshot_present': None})
            snapshots = backup / '.model-backup-snapshots'
            try:
                snapshot_mode = snapshots.lstat().st_mode
            except FileNotFoundError:
                snapshot_names = set()
            else:
                if not stat.S_ISDIR(snapshot_mode):
                    raise ValueError('스냅샷 경로가 일반 디렉터리가 아닙니다.')
                snapshot_entries = list(snapshots.iterdir())
                snapshot_names = {item.name for item in snapshot_entries}
                for item in snapshot_entries:
                    if item.is_dir() and not item.is_symlink():
                        record = models.setdefault(item.name, {'name': item.name, 'local_present': False,
                                                               'backup_present': (backup / item.name).is_dir(), 'snapshot_present': None})
                        try:
                            record['snapshot_present'] = latest_model_snapshot(backup, item.name) is not None
                        except (OSError, ValueError):
                            record['snapshot_present'] = None
        except (OSError, ValueError):
            snapshot_names = None
            backup_error = '백업 목록 일부를 확인할 수 없습니다.'
    for name in CATALOG_TARGETS:
        try:
            local = _directory_presence(source, name)
        except (OSError, ValueError):
            local = None
        remote = None
        if backup is not None:
            try:
                remote = _directory_presence(backup, name, layout_root=source)
            except (OSError, ValueError):
                backup_error = '백업 목록 일부를 확인할 수 없습니다.'
        try:
            if local or remote or name in models:
                record = models.setdefault(name, {'name': name, 'local_present': local,
                                                   'backup_present': remote, 'snapshot_present': None})
                record.update(local_present=local, backup_present=remote)
                parts = target_parts(source, name)
                record['relative_path'] = '/'.join(parts)
                if len(parts) > 1:
                    record['parent_target'] = parts[0]
                else:
                    record['equivalent_target'] = parts[0]
                if name in LEGACY_TARGETS:
                    record['legacy_backup_present'] = None
                    if backup is not None:
                        try:
                            record['legacy_backup_present'] = _directory_presence(backup, LEGACY_TARGETS[name])
                        except (OSError, ValueError):
                            backup_error = '이관 전 백업 경로 일부를 확인할 수 없습니다.'
        except (OSError, ValueError):
            backup_error = '백업 목록 일부를 확인할 수 없습니다.'
    for name in CATALOG_TARGETS:
        try:
            parts = target_parts(source, name)
        except (OSError, ValueError):
            continue
        parent = models.get(parts[0])
        child = models.get(name)
        if len(parts) > 1 and parent is not None and child is not None and child.get('local_present') is True:
            parent.setdefault('included_targets', []).append(name)
    if snapshot_names is not None:
        for name, record in models.items():
            if name not in snapshot_names and record['snapshot_present'] is None:
                record['snapshot_present'] = False
    return {'models': sorted(models.values(), key=lambda item: item['name']), 'samba_uri': config.get('samba_uri'), 'backup_error': backup_error}


def latest_model_snapshot(backup, model):
    snapshot_parent = backup / '.model-backup-snapshots'
    if snapshot_parent.is_symlink():
        raise ValueError('스냅샷 경로에 심볼릭 링크를 사용할 수 없습니다.')
    snapshot_root = snapshot_parent / model
    try:
        root_mode = snapshot_root.lstat().st_mode
    except FileNotFoundError:
        if not backup.is_dir():
            raise ValueError('백업 경로 연결이 끊어졌습니다.') from None
        return None
    except OSError as error:
        raise ValueError('스냅샷 모델 경로를 확인할 수 없습니다.') from error
    if not stat.S_ISDIR(root_mode):
        raise ValueError('스냅샷 모델 경로가 일반 디렉터리가 아닙니다.')
    snapshots = []
    for item in snapshot_root.iterdir():
        if not re.fullmatch(r'[0-9a-f]{32}', item.name):
            continue
        manifest = item / '.snapshot.json'
        try:
            if not stat.S_ISDIR(item.lstat().st_mode):
                raise ValueError('스냅샷 경로가 일반 디렉터리가 아닙니다.')
            manifest_stat = manifest.lstat()
            if not stat.S_ISREG(manifest_stat.st_mode) or manifest_stat.st_size > 16 * 1024 * 1024:
                raise ValueError('스냅샷 매니페스트를 읽을 수 없습니다.')
            record = json.loads(manifest.read_text(encoding='utf-8'))
            if (record.get('version') != 1 or record.get('model') != model or record.get('job_id') != item.name
                    or not isinstance(record.get('created_at'), str) or not isinstance(record.get('files'), list)):
                raise ValueError('스냅샷 매니페스트 형식이 올바르지 않습니다.')
            created_at = datetime.fromisoformat(record['created_at'])
            if created_at.tzinfo is None or created_at.utcoffset() is None:
                raise ValueError('스냅샷 생성 시각에 시간대가 없습니다.')
            snapshots.append((created_at.astimezone(timezone.utc), item.name, item))
        except (OSError, UnicodeError, ValueError, AttributeError, TypeError) as error:
            raise ValueError('완료된 스냅샷을 확인할 수 없습니다: ' + item.name) from error
    return max(snapshots)[2] if snapshots else None


def compare_backup_model(model, config_path=None, *, hash_content=False, target='canonical', progress=None):
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    source, backup, uri = read_backup_roots(config_path)
    source_model = target_path(source, model)
    if source_model.is_symlink() or not source_model.is_dir():
        raise ValueError('모델 디렉터리를 찾을 수 없습니다.')
    if target not in ('canonical', 'latest_snapshot', 'legacy'):
        raise ValueError('백업 비교 대상이 올바르지 않습니다.')
    backup_model = target_path(backup, model, layout_root=source)
    if target == 'legacy':
        if model not in LEGACY_TARGETS:
            raise ValueError('이 모델에는 이전 공유 경로가 등록되지 않았습니다.')
        backup_model = target_path(backup, LEGACY_TARGETS[model])
    snapshot_id = None
    if target == 'latest_snapshot':
        backup_model = latest_model_snapshot(backup, model)
        if backup_model is None:
            raise ValueError('완료된 모델 스냅샷을 찾을 수 없습니다.')
        snapshot_id = backup_model.name
    source_progress = (lambda path, done, total: progress('원본 해시 확인', path, done, total)) if progress else None
    source_inventory = inventory_model_tree(source_model, containment_root=source, hash_content=hash_content, progress=source_progress)
    try:
        backup_stat = backup_model.lstat()
    except FileNotFoundError:
        # A removed share must not be interpreted as every model being absent.
        if not backup.is_dir():
            raise ValueError('백업 경로 연결이 끊어졌습니다.') from None
        backup_stat = None
    except OSError as error:
        raise ValueError('백업 모델 경로를 확인할 수 없습니다.') from error
    if backup_stat is not None and stat.S_ISLNK(backup_stat.st_mode):
        raise ValueError('백업 모델 경로에 심볼릭 링크를 사용할 수 없습니다.')
    if backup_stat is not None and stat.S_ISDIR(backup_stat.st_mode):
        backup_progress = (lambda path, done, total: progress('백업 해시 확인', path, done, total)) if progress else None
        backup_inventory = inventory_model_tree(backup_model, containment_root=backup, hash_content=hash_content, progress=backup_progress)
        if target == 'latest_snapshot':
            backup_inventory['files'].pop('.snapshot.json', None)
            if not hash_content:
                # A Samba server may not preserve nanosecond timestamps. Compare
                # against the original timestamps recorded when the snapshot
                # was made, while still checking the stored file's actual size.
                manifest = backup_model / '.snapshot.json'
                try:
                    before = manifest.lstat()
                    if not stat.S_ISREG(before.st_mode) or before.st_size > 16 * 1024 * 1024:
                        raise ValueError('스냅샷 매니페스트를 읽을 수 없습니다.')
                    with manifest.open('rb') as stream:
                        if _identity(os.fstat(stream.fileno())) != _identity(before):
                            raise ValueError('스냅샷 매니페스트가 변경됐습니다.')
                        record = json.load(stream)
                        if _identity(os.fstat(stream.fileno())) != _identity(before):
                            raise ValueError('스냅샷 매니페스트가 변경됐습니다.')
                    if (record.get('version') != 1 or record.get('model') != model
                            or record.get('job_id') != snapshot_id or not isinstance(record.get('files'), list)):
                        raise ValueError('스냅샷 매니페스트 형식이 올바르지 않습니다.')
                    entries = {}
                    for item in record['files']:
                        name, size, mtime = item['path'], item['size'], item['source_mtime_ns']
                        if (not isinstance(name, str) or not name or name.startswith('/') or '\\' in name
                                or '\x00' in name or any(part in ('', '.', '..') for part in name.split('/'))
                                or name == '.snapshot.json' or name in entries or type(size) is not int or size < 0
                                or type(mtime) is not int or mtime < 0):
                            raise ValueError('스냅샷 파일 목록이 올바르지 않습니다.')
                        entries[name] = (size, mtime)
                    for name, info in backup_inventory['files'].items():
                        entry = entries.get(name)
                        info['mtime_ns'] = entry[1] if entry and entry[0] == info['size'] else None
                    if _identity(manifest.lstat()) != _identity(before):
                        raise ValueError('스냅샷 매니페스트가 변경됐습니다.')
                except (OSError, UnicodeError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
                    raise ValueError('스냅샷 매니페스트를 읽을 수 없습니다.') from error
    elif backup_stat is not None:
        raise ValueError('백업 모델 경로가 디렉터리가 아닙니다.')
    else:
        backup_inventory = {'files': {}, 'errors': [], 'complete': True, 'comparison_basis': 'sha256' if hash_content else 'size_and_mtime'}
    return {'model': model, 'samba_uri': uri, 'target': target, 'snapshot_id': snapshot_id,
            **compare_inventories(source_inventory, backup_inventory)}


def verify_snapshot_manifest(model, config_path=None, *, progress=None):
    """Verify stored bytes against observed-at-backup hashes, without a local model."""
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    _, backup, uri = read_backup_roots(config_path)
    snapshot = latest_model_snapshot(backup, model)
    if snapshot is None:
        raise ValueError('완료된 모델 스냅샷을 찾을 수 없습니다.')
    manifest = snapshot / '.snapshot.json'
    try:
        before = manifest.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > 16 * 1024 * 1024:
            raise ValueError('스냅샷 매니페스트를 읽을 수 없습니다.')
        with manifest.open('rb') as stream:
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ValueError('검증 전 매니페스트가 변경됐습니다.')
            raw = stream.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ValueError('스냅샷 매니페스트 크기 제한을 초과했습니다.')
            record = json.loads(raw)
            if _identity(os.fstat(stream.fileno())) != _identity(before):
                raise ValueError('검증 중 매니페스트가 변경됐습니다.')
        if (not isinstance(record, dict) or record.get('version') != 1
                or record.get('model') != model or record.get('job_id') != snapshot.name
                or not isinstance(record.get('files'), list) or not record['files']):
            raise ValueError('스냅샷 식별 정보 또는 파일 목록이 올바르지 않습니다.')
        expected = {}
        for item in record['files']:
            path, size, digest = item['path'], item['size'], item['sha256']
            if (not isinstance(path, str) or not path or path.startswith('/') or '\\' in path or '\x00' in path
                    or any(part in ('', '.', '..') for part in path.split('/')) or path == '.snapshot.json'
                    or path in expected or type(size) is not int or size < 0
                    or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                raise ValueError('스냅샷 파일 목록이 올바르지 않습니다.')
            expected[path] = {'size': size, 'sha256': digest, 'hash_origin': 'observed_during_backup'}
        source_inventory = {'files': expected, 'errors': [], 'complete': True, 'comparison_basis': 'sha256'}
        backup_progress = (lambda path, done, total: progress('스냅샷 해시 확인', path, done, total)) if progress else None
        backup_inventory = inventory_model_tree(snapshot, containment_root=backup, hash_content=True, progress=backup_progress)
        backup_inventory['files'].pop('.snapshot.json', None)
        if _identity(manifest.lstat()) != _identity(before):
            raise ValueError('검증 중 매니페스트가 변경됐습니다.')
        return {'model': model, 'samba_uri': uri, 'target': 'snapshot_manifest', 'snapshot_id': snapshot.name,
                'note': '백업 당시 관측한 해시와 현재 스냅샷을 비교합니다. 공급처 원본 인증은 별도입니다.',
                **compare_inventories(source_inventory, backup_inventory)}
    except (OSError, UnicodeError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError('스냅샷 매니페스트를 검증할 수 없습니다.') from error
