"""프로세스 간 현재 다운로드와 제한된 최근 결과 상태."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import uuid

MODEL_DOWNLOAD_RECORD_ROOT = Path(__file__).resolve().parents[3] / '.local/model-downloads'
MODEL_DOWNLOAD_RECENT_LIMIT = 20


@contextmanager
def lock_download_status_store(record_root_path):
    record_root_path.mkdir(parents=True, exist_ok=True)
    with (record_root_path / '.status.lock').open('a') as current_lock_file:
        fcntl.flock(current_lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(current_lock_file, fcntl.LOCK_UN)


def collect_current_download_status(record_root_path):
    """진행 중인 상태와 모델별 최근 종료 상태만 남긴다. 잠금 안에서 호출한다."""
    current_active_values = []
    current_terminal_values = []
    for current_record_path in record_root_path.glob('*.json'):
        try:
            if current_record_path.is_symlink() or not current_record_path.is_file():
                continue
            current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
            if not isinstance(current_record_value, dict) or not isinstance(current_record_value.get('model'), str):
                continue
            current_status_value = current_record_value.get('status')
            if current_status_value == 'running':
                current_process_value = current_record_value.get('pid')
                if isinstance(current_process_value, bool) or not isinstance(current_process_value, int) or current_process_value <= 0:
                    continue
                try:
                    os.kill(current_process_value, 0)
                except ProcessLookupError:
                    current_record_value['status'] = 'interrupted'
                    current_status_value = 'interrupted'
                except PermissionError:
                    pass
            if current_status_value == 'running':
                current_active_values.append(current_record_value)
            elif current_status_value in ('completed', 'failed', 'interrupted'):
                current_terminal_values.append((current_record_path, current_record_value))
        except (OSError, ValueError, TypeError):
            continue
    current_terminal_values.sort(key=lambda current_item_value: str(current_item_value[1].get('updated_at', '')), reverse=True)
    current_recent_values = []
    current_model_names = set()
    for current_record_path, current_record_value in current_terminal_values:
        current_model_name = current_record_value['model']
        if current_model_name not in current_model_names and len(current_recent_values) < MODEL_DOWNLOAD_RECENT_LIMIT:
            current_recent_values.append(current_record_value)
            current_model_names.add(current_model_name)
        else:
            try:
                current_record_path.unlink()
            except FileNotFoundError:
                pass
    current_active_values.sort(key=lambda current_item_value: str(current_item_value.get('updated_at', '')), reverse=True)
    return current_active_values + current_recent_values


class ModelDownloadRecord:
    def __init__(self, model_identifier_value, record_root_path=MODEL_DOWNLOAD_RECORD_ROOT):
        self.record_root_path = record_root_path
        self.record_file_path = record_root_path / (uuid.uuid4().hex + '.json')
        self.record_payload_value = {'model': model_identifier_value, 'status': 'running', 'pid': os.getpid(), 'bytes': 0, 'total_bytes': None, 'stage': '준비'}

    def update(self, **record_field_values):
        self.record_payload_value.update(record_field_values, updated_at=datetime.now(timezone.utc).isoformat())
        with lock_download_status_store(self.record_root_path):
            current_temporary_path = self.record_file_path.with_suffix('.tmp')
            current_temporary_path.write_text(json.dumps(self.record_payload_value, ensure_ascii=False), encoding='utf-8')
            os.replace(current_temporary_path, self.record_file_path)
            if self.record_payload_value.get('status') in ('completed', 'failed'):
                collect_current_download_status(self.record_root_path)


@contextmanager
def track_model_download(model_identifier_value, record_root_path=MODEL_DOWNLOAD_RECORD_ROOT):
    current_download_record = ModelDownloadRecord(model_identifier_value, record_root_path)
    current_download_record.update()
    try:
        yield current_download_record
    except BaseException:
        current_download_record.update(status='failed')
        raise
    else:
        current_download_record.update(status='completed')


def list_model_download_records(record_root_path=MODEL_DOWNLOAD_RECORD_ROOT):
    with lock_download_status_store(record_root_path):
        return collect_current_download_status(record_root_path)
