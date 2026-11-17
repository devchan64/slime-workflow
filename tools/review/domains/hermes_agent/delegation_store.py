"""관리 작업 접수 결과와 불확실한 응답을 재접수 없이 확인한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import re
import threading

from tools.review.common.generation_records import write_record_atomically

HERMES_DELEGATION_ROOT = Path(__file__).resolve().parents[4] / '.local/hermes-agent/delegations'
HERMES_DELEGATION_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')
HERMES_DELEGATION_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_DELEGATION_THREAD_LOCK = threading.RLock()


class HermesDelegationStore:
    """접수 ID별 입력 해시와 서비스의 작업 ID만 보관한다."""

    def __init__(self, delegation_storage_root=HERMES_DELEGATION_ROOT):
        self.delegation_storage_root = Path(delegation_storage_root)

    @contextmanager
    def hold_delegation_storage_lock(self):
        if self.delegation_storage_root.is_symlink():
            raise ValueError('위임 저장 경로에 심볼릭 링크를 사용할 수 없습니다.')
        self.delegation_storage_root.mkdir(parents=True, exist_ok=True)
        current_lock_path = self.delegation_storage_root / '.delegations.lock'
        if current_lock_path.is_symlink():
            raise ValueError('위임 잠금 경로에 심볼릭 링크를 사용할 수 없습니다.')
        with HERMES_DELEGATION_THREAD_LOCK, current_lock_path.open('a') as current_lock_stream:
            fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
            yield

    def resolve_delegation_record_path(self, delegation_identifier_value):
        if not isinstance(delegation_identifier_value, str) or not HERMES_DELEGATION_ID_PATTERN.fullmatch(delegation_identifier_value):
            raise ValueError('위임 접수 식별자 형식 오류')
        current_path_value = self.delegation_storage_root / (delegation_identifier_value + '.json')
        if current_path_value.is_symlink():
            raise ValueError('위임 기록은 심볼릭 링크일 수 없습니다.')
        return current_path_value

    def read_delegation_status(self, delegation_identifier_value):
        """접수 ID로 저장된 결과만 읽는다. 생성 명령은 실행하지 않는다."""
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if not current_record_path.exists():
                return {'state': 'not_found'}
            current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
            if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != delegation_identifier_value or current_saved_record.get('state') not in ('dispatching', 'accepted'):
                raise ValueError('위임 기록 형식 오류')
            if current_saved_record['state'] == 'dispatching':
                return {'state': 'unknown', 'message': '접수 결과 확인 필요. Kimodo 이력과 실제 작업을 확인하고 자동 재접수하지 마세요.'}
            if not isinstance(current_saved_record.get('job_id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_saved_record['job_id']):
                raise ValueError('위임 작업 ID 형식 오류')
            return {'state': 'accepted', 'job_id': current_saved_record['job_id']}

    def list_delegation_receipts(self):
        """최근 접수 식별자와 확인 상태만 반환하며 입력·해시는 공개하지 않는다."""
        with self.hold_delegation_storage_lock():
            current_receipt_values = []
            for current_record_path in self.delegation_storage_root.glob('*.json'):
                current_receipt_identifier = current_record_path.stem
                if current_record_path.is_symlink() or not current_record_path.is_file() or not HERMES_DELEGATION_ID_PATTERN.fullmatch(current_receipt_identifier):
                    continue
                try:
                    current_updated_time = current_record_path.stat().st_mtime
                    current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
                    if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != current_receipt_identifier:
                        raise ValueError('위임 기록 형식 오류')
                    current_state_value = current_saved_record.get('state')
                    current_job_identifier = current_saved_record.get('job_id')
                    if current_state_value == 'dispatching':
                        current_state_value = 'unknown'
                        current_job_identifier = None
                    elif current_state_value != 'accepted' or not isinstance(current_job_identifier, str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_job_identifier):
                        raise ValueError('위임 작업 상태 오류')
                except (OSError, ValueError, TypeError, KeyError):
                    current_updated_time = 0
                    current_state_value = 'unavailable'
                    current_job_identifier = None
                current_receipt_values.append({'request_id': current_receipt_identifier, 'state': current_state_value, 'job_id': current_job_identifier, 'updated_at': datetime.fromtimestamp(current_updated_time, timezone.utc).isoformat() if current_updated_time else None, '_sort_time': current_updated_time})
            current_receipt_values.sort(key=lambda current_receipt_value: (current_receipt_value['_sort_time'], current_receipt_value['request_id']), reverse=True)
            for current_receipt_value in current_receipt_values:
                current_receipt_value.pop('_sort_time')
            return {'records': current_receipt_values[:100], 'truncated': len(current_receipt_values) > 100}

    def execute_delegation_once(self, delegation_identifier_value, delegation_request_record, delegation_submit_callback, delegation_validate_callback=None):
        """접수 전 기록한다. 결과 유실 시 재실행하지 않고 확인 필요를 반환한다."""
        if not isinstance(delegation_request_record, dict):
            raise ValueError('위임 입력은 객체여야 합니다.')
        current_serialized_value = json.dumps(delegation_request_record, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
        current_request_digest = hashlib.sha256(current_serialized_value).hexdigest()
        with self.hold_delegation_storage_lock():
            current_record_path = self.resolve_delegation_record_path(delegation_identifier_value)
            if current_record_path.exists():
                current_saved_record = json.loads(current_record_path.read_text(encoding='utf-8'))
                if not isinstance(current_saved_record, dict) or current_saved_record.get('version') != 1 or current_saved_record.get('id') != delegation_identifier_value or current_saved_record.get('state') not in ('dispatching', 'accepted'):
                    raise ValueError('위임 기록 형식 오류')
                if current_saved_record.get('request_sha256') != current_request_digest:
                    raise ValueError('같은 위임 식별자를 다른 입력에 사용할 수 없습니다.')
                if current_saved_record['state'] == 'dispatching':
                    return {'state': 'unknown', 'duplicate': True, 'message': '접수 결과가 확인되지 않았습니다. 생성기 이력을 확인하고 자동 재접수하지 마세요.'}
                if not isinstance(current_saved_record.get('job_id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_saved_record['job_id']):
                    raise ValueError('위임 작업 ID 형식 오류')
                return {'state': 'accepted', 'duplicate': True, 'job_id': current_saved_record['job_id']}
            if delegation_validate_callback is not None:
                delegation_validate_callback(delegation_request_record)
            current_saved_record = {'version': 1, 'id': delegation_identifier_value, 'request_sha256': current_request_digest, 'state': 'dispatching'}
            write_record_atomically(current_record_path, current_saved_record)
            current_response_record = delegation_submit_callback(delegation_request_record)
            if not isinstance(current_response_record, dict) or not isinstance(current_response_record.get('id'), str) or not HERMES_DELEGATION_JOB_PATTERN.fullmatch(current_response_record['id']):
                raise ValueError('접수 응답의 작업 ID를 확인할 수 없습니다. 자동 재접수하지 않습니다.')
            current_saved_record.update(state='accepted', job_id=current_response_record['id'])
            write_record_atomically(current_record_path, current_saved_record)
            return {'state': 'accepted', 'duplicate': False, 'job_id': current_saved_record['job_id']}
