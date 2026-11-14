"""프로세스 간 모델 다운로드 상태 기록. 각 실행은 별도 파일을 소유한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

MODEL_DOWNLOAD_RECORD_ROOT = Path(__file__).resolve().parents[3] / '.local/model-downloads'


class ModelDownloadRecord:
    def __init__(self, model_identifier_value, record_root_path=MODEL_DOWNLOAD_RECORD_ROOT):
        self.record_root_path = record_root_path
        self.record_file_path = record_root_path / (uuid.uuid4().hex + '.json')
        self.record_payload_value = {'model': model_identifier_value, 'status': 'running', 'pid': os.getpid(), 'bytes': 0, 'total_bytes': None, 'stage': '준비'}

    def update(self, **record_field_values):
        self.record_payload_value.update(record_field_values, updated_at=datetime.now(timezone.utc).isoformat())
        self.record_root_path.mkdir(parents=True, exist_ok=True)
        current_temporary_path = self.record_file_path.with_suffix('.tmp')
        current_temporary_path.write_text(json.dumps(self.record_payload_value, ensure_ascii=False), encoding='utf-8')
        os.replace(current_temporary_path, self.record_file_path)


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
    current_record_values = []
    for current_record_path in record_root_path.glob('*.json'):
        try:
            current_record_value = json.loads(current_record_path.read_text(encoding='utf-8'))
            if current_record_value.get('status') == 'running':
                try:
                    os.kill(current_record_value['pid'], 0)
                except ProcessLookupError:
                    current_record_value['status'] = 'interrupted'
                except PermissionError:
                    pass
            current_record_values.append(current_record_value)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sorted(current_record_values, key=lambda record_value: record_value.get('updated_at', ''), reverse=True)
