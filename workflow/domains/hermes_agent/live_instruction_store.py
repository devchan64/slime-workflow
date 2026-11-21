"""Durable receipts for instructions addressed to one active Hermes turn.

A delivery with an uncertain outcome must never be replayed automatically.
"""
from datetime import datetime, timezone
import re

from workflow.common.generation_records import write_record_atomically

_ID = re.compile(r'[A-Za-z0-9_-]{8,80}\Z')
_STATES = {'pending', 'delivering', 'accepted', 'applied', 'undelivered', 'unknown'}
_TRANSITIONS = {
    'pending': {'delivering', 'undelivered'},
    'delivering': {'accepted', 'applied', 'undelivered', 'unknown'},
    'accepted': {'applied', 'undelivered', 'unknown'},
    'unknown': {'applied', 'undelivered'}, 'applied': set(), 'undelivered': set(),
}


def submit(store, session_id, request_id, job_id, mode, text):
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
        raise ValueError('지시 접수 ID 형식 오류')
    if not isinstance(job_id, str) or not _ID.fullmatch(job_id):
        raise ValueError('작업 ID 형식 오류')
    if mode not in ('steer', 'redirect') or not isinstance(text, str) or not text.strip() or len(text) > 8000:
        raise ValueError('지시 형식 오류')
    with store.hold_session_storage_lock():
        record = store.read_session_record_locked(session_id)
        rows = record.setdefault('live_instructions', [])
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('지시 기록 형식 오류')
        existing = next((row for row in rows if row.get('request_id') == request_id), None)
        if existing is not None:
            if (existing.get('job_id'), existing.get('mode'), existing.get('text')) != (job_id, mode, text):
                raise ValueError('같은 접수 ID를 다른 지시에 사용할 수 없습니다.')
            return dict(existing)
        if len(rows) >= 200:
            raise ValueError('이 세션의 실행 중 지시 기록 한도에 도달했습니다.')
        now = datetime.now(timezone.utc).isoformat()
        row = {'request_id': request_id, 'job_id': job_id, 'mode': mode, 'text': text,
               'state': 'pending', 'created_at': now, 'updated_at': now}
        rows.append(row)
        write_record_atomically(store.resolve_session_record_path(session_id), record)
        return dict(row)


def transition(store, session_id, request_id, expected, state):
    if expected not in _STATES or state not in _TRANSITIONS[expected]:
        raise ValueError('허용되지 않는 지시 상태 전환')
    with store.hold_session_storage_lock():
        record = store.read_session_record_locked(session_id)
        row = next((item for item in record.get('live_instructions', []) if item.get('request_id') == request_id), None)
        if row is None or row.get('state') != expected:
            raise ValueError('지시 상태가 변경되었습니다.')
        row['state'] = state
        row['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_record_atomically(store.resolve_session_record_path(session_id), record)
        return dict(row)
