"""Persist pending chat requests separately from completed conversation turns."""
from datetime import datetime, timezone
import re

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.session_store import HermesSessionStore

_REQUEST_ID = re.compile(r'[A-Za-z0-9_-]{8,80}')
_MAX_QUEUED = 50


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        raise ValueError('대기 메시지는 1~8000자여야 합니다.')
    return value


def enqueue(store: HermesSessionStore, session_id, request_id, prompt, model_profile=None):
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise ValueError('접수 ID 형식 오류')
    prompt = _text(prompt)
    from workflow.common.hermes_model_routing import MODEL_FLOORS_MIB
    if model_profile is not None and (not isinstance(model_profile, str) or model_profile not in MODEL_FLOORS_MIB):
        raise ValueError('지원하지 않는 Hermes 모델입니다.')
    with store.hold_session_storage_lock():
        session = store.read_session_record_locked(session_id)
        queue = session.setdefault('chat_queue', [])
        if not isinstance(queue, list) or any(not isinstance(row, dict) for row in queue):
            raise ValueError('대기열 기록 형식 오류')
        prior = next((row for row in queue if row.get('request_id') == request_id), None)
        if prior is not None:
            if prior.get('original_prompt') != prompt or prior.get('model_profile') != model_profile:
                raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            return {'request': dict(prior), 'duplicate': True}
        if any(row.get('request_id') == request_id for row in session['messages']):
            raise ValueError('이미 처리된 접수 ID입니다.')
        if sum(row.get('state') == 'queued' for row in queue) >= _MAX_QUEUED:
            raise ValueError('대기열 한도에 도달했습니다.')
        now = datetime.now(timezone.utc).isoformat()
        row = {'request_id':request_id, 'original_prompt':prompt, 'prompt':prompt,
               'revision':1, 'state':'queued', 'created_at':now}
        if model_profile is not None:
            row['model_profile'] = model_profile
        queue.append(row)
        session['updated_at'] = now
        write_record_atomically(store.resolve_session_record_path(session_id), session)
        return {'request': dict(row), 'duplicate': False}


def update(store: HermesSessionStore, session_id, request_id, revision, prompt=None, cancel=False):
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id) or type(revision) is not int or revision < 1 or type(cancel) is not bool:
        raise ValueError('대기 요청 또는 버전 형식 오류')
    if not cancel:
        prompt = _text(prompt)
    elif prompt is not None:
        raise ValueError('취소 요청에는 메시지를 전달할 수 없습니다.')
    with store.hold_session_storage_lock():
        session = store.read_session_record_locked(session_id)
        queue = session.get('chat_queue', [])
        if not isinstance(queue, list) or any(not isinstance(item, dict) for item in queue):
            raise ValueError('대기열 기록 형식 오류')
        row = next((item for item in queue if item.get('request_id') == request_id), None)
        if row is None or row.get('state') != 'queued' or row.get('revision') != revision:
            raise ValueError('대기 요청이 변경됐거나 실행을 시작했습니다. 다시 조회하세요.')
        if cancel:
            row['state'] = 'cancelled'
        else:
            row['prompt'] = prompt
        row['revision'] += 1
        session['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_record_atomically(store.resolve_session_record_path(session_id), session)
        return dict(row)


def transition(store, session_id, request_id, old_state, new_state, job_id=None):
    with store.hold_session_storage_lock():
        session = store.read_session_record_locked(session_id)
        row = next((item for item in session.get('chat_queue', []) if item.get('request_id') == request_id), None)
        if row is None or row.get('state') != old_state:
            raise ValueError('대기 요청 상태가 변경됐습니다.')
        row['state'] = new_state
        row['revision'] += 1
        if job_id is not None:
            row['job_id'] = job_id
        session['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_record_atomically(store.resolve_session_record_path(session_id), session)
        return dict(row)
