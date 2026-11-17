"""Hermes 대화 세션의 로컬 기록과 중복 요청을 관리한다."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import re
import threading
import uuid

from tools.review.common.generation_records import write_record_atomically

HERMES_SESSION_ROOT = Path(__file__).resolve().parents[4] / '.local/hermes-agent/sessions'
HERMES_SESSION_ID_PATTERN = re.compile(r'[0-9a-f]{32}')
HERMES_SESSION_REQUEST_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}')
HERMES_SESSION_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')
HERMES_SESSION_MAX_MESSAGES = 200


class HermesSessionStore:
    """작업 기록은 소유하지 않고 사용자 메시지와 작업 ID만 연결한다."""

    def __init__(self, session_storage_root=HERMES_SESSION_ROOT):
        self.session_storage_root = Path(session_storage_root)
        self.session_thread_lock = threading.RLock()

    @contextmanager
    def hold_session_storage_lock(self):
        if self.session_storage_root.is_symlink():
            raise ValueError('세션 저장 경로에 심볼릭 링크를 사용할 수 없습니다.')
        self.session_storage_root.mkdir(parents=True, exist_ok=True)
        current_lock_path = self.session_storage_root / '.sessions.lock'
        if current_lock_path.is_symlink():
            raise ValueError('세션 잠금 경로에 심볼릭 링크를 사용할 수 없습니다.')
        with self.session_thread_lock, current_lock_path.open('a') as current_lock_stream:
            fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
            yield

    def resolve_session_record_path(self, session_identifier_value):
        if not isinstance(session_identifier_value, str) or not HERMES_SESSION_ID_PATTERN.fullmatch(session_identifier_value):
            raise ValueError('세션 ID 형식 오류')
        current_record_path = self.session_storage_root / (session_identifier_value + '.json')
        if current_record_path.is_symlink():
            raise ValueError('세션 기록은 심볼릭 링크일 수 없습니다.')
        return current_record_path

    def read_session_record_locked(self, session_identifier_value):
        current_record_path = self.resolve_session_record_path(session_identifier_value)
        if not current_record_path.is_file():
            raise ValueError('세션을 찾을 수 없습니다.')
        current_session_record = json.loads(current_record_path.read_text(encoding='utf-8'))
        if not isinstance(current_session_record, dict) or current_session_record.get('version') != 1 or current_session_record.get('id') != session_identifier_value or not isinstance(current_session_record.get('messages'), list):
            raise ValueError('세션 기록 형식 오류')
        return current_session_record

    def create_session_record(self, session_identifier_value=None):
        with self.hold_session_storage_lock():
            current_session_identifier = session_identifier_value if session_identifier_value is not None else uuid.uuid4().hex
            current_created_timestamp = datetime.now(timezone.utc).isoformat()
            current_session_record = {'version': 1, 'id': current_session_identifier, 'created_at': current_created_timestamp, 'updated_at': current_created_timestamp, 'messages': []}
            current_record_path = self.resolve_session_record_path(current_session_identifier)
            if current_record_path.exists():
                return self.read_session_record_locked(current_session_identifier)
            write_record_atomically(current_record_path, current_session_record)
            return current_session_record

    def read_session_record(self, session_identifier_value):
        with self.hold_session_storage_lock():
            return self.read_session_record_locked(session_identifier_value)

    def list_session_records(self):
        with self.hold_session_storage_lock():
            current_session_summaries = []
            for current_record_path in self.session_storage_root.glob('*.json'):
                current_session_identifier = current_record_path.stem
                if not HERMES_SESSION_ID_PATTERN.fullmatch(current_session_identifier):
                    continue
                current_session_record = self.read_session_record_locked(current_session_identifier)
                current_session_summaries.append({'id': current_session_identifier, 'created_at': current_session_record['created_at'], 'updated_at': current_session_record['updated_at'], 'message_count': len(current_session_record['messages'])})
            current_session_summaries.sort(key=lambda current_session_record: (current_session_record['updated_at'], current_session_record['id']), reverse=True)
            return {'sessions': current_session_summaries[:100], 'truncated': len(current_session_summaries) > 100}

    def append_session_request(self, session_identifier_value, request_identifier_value, request_message_text, execution_prompt_text=None, verification_module_names=None, context_truncated=False):
        if not isinstance(request_identifier_value, str) or not HERMES_SESSION_REQUEST_PATTERN.fullmatch(request_identifier_value):
            raise ValueError('접수 식별자 형식 오류')
        if not isinstance(request_message_text, str) or not request_message_text.strip() or len(request_message_text) > 12000:
            raise ValueError('메시지는 1~12000자여야 합니다.')
        with self.hold_session_storage_lock():
            current_session_record = self.read_session_record_locked(session_identifier_value)
            for current_message_record in current_session_record['messages']:
                if current_message_record.get('request_id') == request_identifier_value:
                    if current_message_record.get('text') != request_message_text or current_message_record.get('verification_modules', []) != (verification_module_names or []):
                        raise ValueError('같은 접수 식별자를 다른 메시지에 사용할 수 없습니다.')
                    return {'message': current_message_record, 'duplicate': True}
            if len(current_session_record['messages']) >= HERMES_SESSION_MAX_MESSAGES:
                raise ValueError('세션 메시지 한도에 도달했습니다. 새 세션을 시작하세요.')
            current_created_timestamp = datetime.now(timezone.utc).isoformat()
            current_message_record = {'id': uuid.uuid4().hex, 'request_id': request_identifier_value, 'role': 'user', 'text': request_message_text, 'created_at': current_created_timestamp, 'job_id': None, 'execution_prompt': execution_prompt_text if execution_prompt_text is not None else request_message_text, 'verification_modules': verification_module_names or [], 'context_truncated': context_truncated}
            current_session_record['messages'].append(current_message_record)
            current_session_record['updated_at'] = current_created_timestamp
            write_record_atomically(self.resolve_session_record_path(session_identifier_value), current_session_record)
            return {'message': current_message_record, 'duplicate': False}

    def attach_session_job(self, session_identifier_value, request_identifier_value, job_identifier_value):
        if not isinstance(job_identifier_value, str) or not HERMES_SESSION_JOB_PATTERN.fullmatch(job_identifier_value):
            raise ValueError('작업 ID 형식 오류')
        with self.hold_session_storage_lock():
            current_session_record = self.read_session_record_locked(session_identifier_value)
            current_message_record = next((current_message_record for current_message_record in current_session_record['messages'] if current_message_record.get('request_id') == request_identifier_value), None)
            if current_message_record is None:
                raise ValueError('세션 메시지를 찾을 수 없습니다.')
            if current_message_record['job_id'] not in (None, job_identifier_value):
                raise ValueError('메시지에 다른 작업이 이미 연결되어 있습니다.')
            if current_message_record['job_id'] is None:
                current_message_record['job_id'] = job_identifier_value
                current_session_record['updated_at'] = datetime.now(timezone.utc).isoformat()
                write_record_atomically(self.resolve_session_record_path(session_identifier_value), current_session_record)
            return current_message_record
