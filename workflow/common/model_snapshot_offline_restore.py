"""Restore a completed snapshot without contacting a model provider."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import time

from workflow.common.model_backup_service import latest_model_snapshot, read_backup_roots
from workflow.common.model_backup_inventory import inventory_model_tree
from workflow.common.model_backup_targets import FLATTENED_TARGETS, target_path
from workflow.common.model_storage_move import _rename_noreplace


def list_snapshot_versions(model, *, roots=None):
    """List snapshot declarations without asserting file integrity."""
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    _, backup, _ = roots if roots is not None else read_backup_roots()
    backup = Path(backup).resolve(strict=True)
    parent = backup/'.model-backup-snapshots'
    directory = parent/model
    if parent.is_symlink() or directory.is_symlink():
        raise ValueError('스냅샷 경로에 심볼릭 링크를 사용할 수 없습니다.')
    try:
        directory_mode = directory.lstat().st_mode
    except FileNotFoundError:
        return []
    if not stat.S_ISDIR(directory_mode):
        raise ValueError('스냅샷 경로가 디렉터리가 아닙니다.')
    versions = []
    for snapshot in sorted(directory.iterdir()):
        if not re.fullmatch(r'[0-9a-f]{32}', snapshot.name):
            continue
        try:
            if snapshot.is_symlink() or not snapshot.is_dir():
                raise ValueError('스냅샷 경로 오류')
            with _open_snapshot_file(snapshot, '.snapshot.json') as stream:
                if os.fstat(stream.fileno()).st_size > 16*1024*1024:
                    raise ValueError('매니페스트 크기 오류')
                record = json.loads(stream.read(16*1024*1024 + 1))
            if (not isinstance(record, dict) or record.get('version') != 1 or record.get('model') != model
                    or record.get('job_id') != snapshot.name or not isinstance(record.get('created_at'), str)
                    or not isinstance(record.get('files'), list)):
                raise ValueError('매니페스트 형식 오류')
            paths = [item.get('path') if isinstance(item, dict) else None for item in record['files']]
            if any(not isinstance(path, str) or not path for path in paths):
                raise ValueError('매니페스트 파일 경로 오류')
            versions.append({'snapshot_id': snapshot.name, 'created_at': record['created_at'],
                             'file_count': len(paths),
                             'partial_file_count': sum(path.endswith(('.incomplete', '.partial')) for path in paths),
                             'state': 'declared'})
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            versions.append({'snapshot_id': snapshot.name, 'state': 'unavailable'})
    return versions


def _open_snapshot_file(snapshot, name):
    """Open each path component without following symlinks, including races."""
    parts = Path(name).parts
    directory = os.open(snapshot, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('스냅샷 파일이 일반 파일이 아닙니다.')
            return os.fdopen(fd, 'rb')
        except BaseException:
            os.close(fd)
            raise
    finally:
        os.close(directory)


def restore_snapshot_offline(model, *, snapshot_id=None, roots=None, progress=None):
    """Restore only into an absent model directory, verifying every snapshot file.

    Snapshot hashes establish consistency with the recorded backup, not origin.
    """
    if not isinstance(model, str) or not model or model in ('.', '..') or '/' in model or '\\' in model or '\x00' in model:
        raise ValueError('모델 이름이 올바르지 않습니다.')
    source, backup, _ = roots if roots is not None else read_backup_roots()
    source, backup = Path(source).resolve(strict=True), Path(backup).resolve(strict=True)
    destination = target_path(source, model)
    # Older catalog targets fall back to their historic nested directory when
    # neither installation exists. A restore after deletion must instead use
    # the current flattened layout, while still refusing any existing install.
    if model in FLATTENED_TARGETS and not destination.exists() and not destination.is_symlink():
        destination = source.joinpath(*FLATTENED_TARGETS[model])
    relative = destination.relative_to(source)
    for index in range(1, len(relative.parts) + 1):
        part = source.joinpath(*relative.parts[:index])
        if part.is_symlink():
            raise ValueError('복원 경로에 심볼릭 링크를 사용할 수 없습니다.')
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('기존 모델 디렉터리를 덮어쓸 수 없습니다: ' + str(destination))
    if not destination.parent.is_dir():
        raise ValueError('복원 대상의 상위 디렉터리가 없습니다.')
    if snapshot_id is None:
        snapshot = latest_model_snapshot(backup, model)
    else:
        if not isinstance(snapshot_id, str) or not re.fullmatch(r'[0-9a-f]{32}', snapshot_id):
            raise ValueError('완료 스냅샷 ID가 올바르지 않습니다.')
        parent = backup/'.model-backup-snapshots'/model
        snapshot = parent/snapshot_id
        if (parent.parent.is_symlink() or parent.is_symlink() or snapshot.is_symlink()
                or not snapshot.is_dir() or not (snapshot/'.snapshot.json').is_file()):
            raise ValueError('완료된 모델 스냅샷을 찾을 수 없습니다.')
    if snapshot is None:
        raise ValueError('완료된 모델 스냅샷을 찾을 수 없습니다.')
    manifest = snapshot/'.snapshot.json'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 16*1024*1024:
        raise ValueError('스냅샷 매니페스트를 확인할 수 없습니다.')
    with _open_snapshot_file(snapshot, '.snapshot.json') as stream:
        manifest_identity = os.fstat(stream.fileno())
        if manifest_identity.st_size > 16*1024*1024:
            raise ValueError('스냅샷 매니페스트가 너무 큽니다.')
        data = json.loads(stream.read(16*1024*1024 + 1))
        manifest_read_after = os.fstat(stream.fileno())
        if (manifest_identity.st_dev, manifest_identity.st_ino, manifest_identity.st_size,
                manifest_identity.st_mtime_ns, manifest_identity.st_ctime_ns) != (manifest_read_after.st_dev,
                manifest_read_after.st_ino, manifest_read_after.st_size, manifest_read_after.st_mtime_ns, manifest_read_after.st_ctime_ns):
            raise ValueError('읽는 중 스냅샷 매니페스트가 변경됐습니다.')
    if (not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1
            or data.get('model') != model or data.get('job_id') != snapshot.name
            or not isinstance(data.get('files'), list) or not data['files']):
        raise ValueError('스냅샷 식별 정보 또는 파일 목록이 올바르지 않습니다.')
    entries = {}
    for item in data['files']:
        if not isinstance(item, dict):
            raise ValueError('스냅샷 파일 기록이 올바르지 않습니다.')
        name, size, digest = item.get('path'), item.get('size'), item.get('sha256')
        mtime = item.get('source_mtime_ns')
        if (not isinstance(name, str) or not name or name.startswith('/') or '\\' in name or '\x00' in name
                or any(part in ('', '.', '..') for part in name.split('/')) or name == '.snapshot.json'
                or name in entries or type(size) is not int or size < 0
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)
                or (mtime is not None and (type(mtime) is not int or mtime < 0))):
            raise ValueError('스냅샷 파일 기록이 올바르지 않습니다.')
        entries[name] = (size, digest, mtime)
    inventory = inventory_model_tree(snapshot, containment_root=backup)
    inventory['files'].pop('.snapshot.json', None)
    if (not inventory['complete'] or inventory['files'].keys() != entries.keys()
            or any(inventory['files'][name]['size'] != record[0] for name, record in entries.items())):
        raise ValueError('스냅샷 파일 목록 또는 크기 불일치')
    total = sum(size for size, _, _ in entries.values())
    if shutil.disk_usage(destination.parent).free < total:
        raise OSError('복원할 로컬 디스크 공간이 부족합니다.')
    with tempfile.TemporaryDirectory(prefix='.snapshot-restore-', dir=destination.parent) as temporary:
        stage = Path(temporary)/'model'
        stage.mkdir()
        done = 0
        timestamp_mismatches = []
        for name, (size, expected, mtime) in entries.items():
            output_path = stage/name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            count = 0
            with _open_snapshot_file(snapshot, name) as reader, output_path.open('xb') as writer:
                before = os.fstat(reader.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('스냅샷 파일이 일반 파일이 아닙니다.')
                for chunk in iter(lambda: reader.read(8*1024*1024), b''):
                    writer.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                    if progress: progress(name, done+count, total)
                writer.flush()
                os.fsync(writer.fileno())
                after = os.fstat(reader.fileno())
                if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ValueError('복원 중 스냅샷 파일이 변경됐습니다.')
            if count != size or digest.hexdigest() != expected:
                raise ValueError('스냅샷 파일 크기 또는 SHA-256 불일치: '+name)
            with output_path.open('rb') as verification:
                if hashlib.file_digest(verification, 'sha256').hexdigest() != expected:
                    raise ValueError('복원 파일 SHA-256 불일치: '+name)
            if mtime is not None:
                os.utime(output_path, ns=(mtime, mtime))
                if output_path.stat().st_mtime_ns != mtime:
                    timestamp_mismatches.append(name)
            done += count
        manifest_after = manifest.stat()
        if manifest.is_symlink() or (manifest_identity.st_dev, manifest_identity.st_ino, manifest_identity.st_size,
                manifest_identity.st_mtime_ns, manifest_identity.st_ctime_ns) != (manifest_after.st_dev,
                manifest_after.st_ino, manifest_after.st_size, manifest_after.st_mtime_ns, manifest_after.st_ctime_ns):
            raise ValueError('복원 중 스냅샷 매니페스트가 변경됐습니다.')
        _rename_noreplace(stage, destination)
    partial_files = sorted(name for name in entries if name.endswith(('.incomplete', '.partial')))
    note = '백업 당시 기록한 해시와 일치합니다. 공급처 원본 인증은 별도입니다.'
    if partial_files:
        note += ' 미완료 확장자 파일이 포함되어 있으므로 모델 준비 상태를 별도로 확인하세요.'
    return {'model':model, 'snapshot_id':snapshot.name, 'path':str(destination), 'files':len(entries),
            'bytes':total, 'verification':'snapshot_manifest_sha256',
            'timestamp_mismatches':timestamp_mismatches,
            'partial_files':partial_files, 'note':note}


def main():
    parser = argparse.ArgumentParser(description='인터넷 없이 Samba 모델 스냅샷을 빈 모델 경로에 복원')
    parser.add_argument('model', help='백업 대상 이름')
    parser.add_argument('--snapshot-id', help='복원할 완료 스냅샷 ID (생략하면 최신)')
    parser.add_argument('--list', action='store_true', help='파일 검증 없이 완료 스냅샷 목록만 조회')
    args = parser.parse_args()
    if args.list:
        if args.snapshot_id:
            parser.error('--list와 --snapshot-id는 함께 사용할 수 없습니다.')
        print(json.dumps(list_snapshot_versions(args.model), ensure_ascii=False, indent=2))
        return
    last_report = [0.0]
    def report(name, done, total):
        now = time.monotonic()
        if now - last_report[0] >= 5:
            print(f'복원 중 {done}/{total} 바이트 · {name}', file=sys.stderr, flush=True)
            last_report[0] = now
    result = restore_snapshot_offline(args.model, snapshot_id=args.snapshot_id, progress=report)
    try:
        from workflow.common.model_restore_history import write_restore_record
        write_restore_record(result)
        result['history_recorded'] = True
    except (OSError, ValueError):
        result['history_recorded'] = False
        result['history_warning'] = '복원은 완료됐지만 로컬 복원 이력을 기록하지 못했습니다.'
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
