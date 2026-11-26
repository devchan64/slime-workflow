"""Compare historical snapshot hashes across model roots with current local files.

This is an explicit read-only investigation, not a deletion or deduplication tool.
"""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from workflow.common.model_backup_service import latest_model_snapshot, read_backup_roots
from workflow.common.model_backup_inventory import _identity
from workflow.common.model_snapshot_offline_restore import _open_snapshot_file


def survey_duplicates(source, backup, *, minimum_bytes=1024 * 1024):
    source, backup = Path(source).resolve(strict=True), Path(backup).resolve(strict=True)
    groups, errors = defaultdict(list), []
    roots = sorted(p for p in source.iterdir() if p.is_dir() and not p.is_symlink() and not p.name.startswith('.'))
    for root in roots:
        try:
            snapshot = latest_model_snapshot(backup, root.name)
            if snapshot is None:
                raise ValueError('완료 스냅샷 없음')
            manifest = snapshot / '.snapshot.json'
            if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size > 16 * 1024 * 1024:
                raise ValueError('매니페스트 확인 불가')
            with _open_snapshot_file(snapshot, '.snapshot.json') as stream:
                before = _identity(os.fstat(stream.fileno()))
                record = json.load(stream)
                if _identity(os.fstat(stream.fileno())) != before:
                    raise ValueError('매니페스트 변경 감지')
            if (_identity(manifest.lstat()) != before or record.get('model') != root.name
                    or record.get('job_id') != snapshot.name or record.get('version') != 1
                    or not isinstance(record.get('files'), list)):
                raise ValueError('매니페스트 식별 정보 오류')
            seen, candidates = set(), []
            for entry in record['files']:
                if not isinstance(entry, dict):
                    raise ValueError('매니페스트 항목 오류')
                path, size, digest = entry.get('path'), entry.get('size'), entry.get('sha256')
                if (not isinstance(path, str) or not path or path.startswith('/') or '\\' in path or '\x00' in path
                        or any(part in ('', '.', '..') for part in path.split('/')) or path in seen
                        or type(size) is not int or size < 0 or not isinstance(digest, str)
                        or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                    raise ValueError('매니페스트 항목 오류')
                seen.add(path)
                if size > minimum_bytes:
                    candidates.append(((digest, size), (root.name, path)))
            for key, candidate in candidates:
                groups[key].append(candidate)
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError) as error:
            errors.append({'root': root.name, 'reason': str(error)})
    result = []
    for (digest, size), paths in groups.items():
        if len({root for root, _ in paths}) < 2:
            continue
        observations = []
        for root, relative in sorted(paths):
            path = source / root / relative
            observation = {'path': f'{root}/{relative}', 'state': 'unavailable'}
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(source)
                before = resolved.stat()
                if not stat.S_ISREG(before.st_mode):
                    raise ValueError('일반 파일이 아님')
                with resolved.open('rb') as stream:
                    if _identity(os.fstat(stream.fileno())) != _identity(before):
                        raise ValueError('파일 변경 감지')
                    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if _identity(os.fstat(stream.fileno())) != _identity(before):
                        raise ValueError('파일 변경 감지')
                if _identity(resolved.stat()) != _identity(before) or path.resolve(strict=True) != resolved:
                    raise ValueError('파일 변경 감지')
                observation.update(state='matches' if actual == digest and before.st_size == size else 'different',
                                   via_link=resolved != path, device=before.st_dev, inode=before.st_ino,
                                   allocated_bytes=before.st_blocks * 512)
            except (OSError, ValueError) as error:
                observation['reason'] = str(error)
            observations.append(observation)
        result.append({'size': size, 'sha256': digest, 'paths': observations})
    result.sort(key=lambda item: (-item['size'], item['sha256']))
    return {'version': 1, 'observed_at': datetime.now(timezone.utc).isoformat(),
            'root': str(source), 'minimum_bytes_exclusive': minimum_bytes, 'roots': len(roots),
            'errors': errors, 'groups': result,
            'note': '동일 해시는 삭제 가능성이나 서비스 호환성을 뜻하지 않습니다.'}


def main():
    source, backup, _ = read_backup_roots()
    print(json.dumps(survey_duplicates(source, backup), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
