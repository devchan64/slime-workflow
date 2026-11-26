"""Local observations of completed offline restores; not provider authentication."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile

HISTORY_DIR = Path(__file__).resolve().parents[2] / '.local/model-catalog/restore-history'


def write_restore_record(result, *, directory=HISTORY_DIR):
    model, snapshot = result.get('model'), result.get('snapshot_id')
    if (not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', model)
            or not isinstance(snapshot, str) or not re.fullmatch(r'[0-9a-f]{32}', snapshot)
            or result.get('verification') != 'snapshot_manifest_sha256'
            or type(result.get('files')) is not int or result['files'] <= 0
            or type(result.get('bytes')) is not int or result['bytes'] < 0
            or not isinstance(result.get('timestamp_mismatches'), list)
            or not isinstance(result.get('partial_files'), list)
            or len(result['timestamp_mismatches']) > result['files']
            or len(result['partial_files']) > result['files']):
        raise ValueError('복원 관측 기록이 올바르지 않습니다.')
    record = {'version': 1, 'model': model, 'snapshot_id': snapshot,
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'files': result['files'], 'bytes': result['bytes'],
              'timestamp_mismatches': len(result['timestamp_mismatches']),
              'partial_files': len(result['partial_files']),
              'verification': 'snapshot_manifest_sha256'}
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, prefix='.restore-', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, directory / f'{model}.json')
    finally:
        temporary.unlink(missing_ok=True)
    return record


def read_restore_record(model, *, directory=HISTORY_DIR):
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', model):
        return None
    path = Path(directory) / f'{model}.json'
    try:
        if path.is_symlink() or path.stat().st_size > 8192:
            return None
        record = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or record.get('version') != 1 or record.get('model') != model
                or not isinstance(record.get('snapshot_id'), str) or not re.fullmatch(r'[0-9a-f]{32}', record['snapshot_id'])
                or not isinstance(record.get('observed_at'), str) or record.get('verification') != 'snapshot_manifest_sha256'
                or any(type(record.get(key)) is not int or record[key] < 0 for key in ('files', 'bytes', 'partial_files', 'timestamp_mismatches'))
                or record['files'] == 0 or record['partial_files'] > record['files']
                or record['timestamp_mismatches'] > record['files']):
            return None
        observed = datetime.fromisoformat(record['observed_at'])
        if observed.tzinfo is None or observed.utcoffset() is None:
            return None
        return record
    except (OSError, ValueError, TypeError):
        return None
