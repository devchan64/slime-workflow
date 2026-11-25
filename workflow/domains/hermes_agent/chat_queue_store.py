"""Persist pending chat requests separately from completed conversation turns."""
from datetime import datetime, timezone
import re
import time

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.session_store import HermesSessionStore

_REQUEST_ID = re.compile(r'[A-Za-z0-9_-]{8,80}')
_MAX_QUEUED = 50


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 12000:
        raise ValueError('대기 메시지는 1~12000자여야 합니다.')
    return value


def enqueue(store: HermesSessionStore, session_id, request_id, prompt, model_profile=None, *, require_resident=False):
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise ValueError('접수 ID 형식 오류')
    prompt = _text(prompt)
    if type(require_resident) is not bool:
        raise ValueError('상주 모델 요청 형식 오류')
    from workflow.common.hermes_model_routing import COMPLEX_MODEL, MODEL_FLOORS_MIB
    if model_profile is not None and (not isinstance(model_profile, str) or model_profile not in MODEL_FLOORS_MIB):
        raise ValueError('지원하지 않는 Hermes 모델입니다.')
    with store.hold_session_storage_lock():
        session = store.read_session_record_locked(session_id)
        if request_id in session.get('withdrawn_requests', []):
            raise ValueError('철회된 대화 요청입니다.')
        queue = session.setdefault('chat_queue', [])
        if not isinstance(queue, list) or any(not isinstance(row, dict) for row in queue):
            raise ValueError('대기열 기록 형식 오류')
        prior = next((row for row in queue if row.get('request_id') == request_id), None)
        if prior is not None:
            legacy_implicit_model = (require_resident and model_profile == COMPLEX_MODEL and prior.get('model_profile') is None
                                     and prior.get('state') in ('queued', 'dispatching')
                                     and not any(session_message_record.get('request_id') == request_id for session_message_record in session['messages']))
            if prior.get('original_prompt') != prompt or (prior.get('model_profile') != model_profile and not legacy_implicit_model):
                raise ValueError('같은 접수 ID를 다른 요청에 사용할 수 없습니다.')
            duplicate_request_record = dict(prior)
            if legacy_implicit_model:
                duplicate_request_record['model_profile'] = COMPLEX_MODEL
            return {'request': duplicate_request_record, 'duplicate': True}
        if any(row.get('request_id') == request_id for row in session['messages']):
            raise ValueError('이미 처리된 접수 ID입니다.')
        if sum(row.get('state') == 'queued' for row in queue) >= _MAX_QUEUED:
            raise ValueError('대기열 한도에 도달했습니다.')
        now = datetime.now(timezone.utc).isoformat()
        row = {'request_id':request_id, 'original_prompt':prompt, 'prompt':prompt,
               'revision':1, 'state':'queued', 'created_at':now, 'dflash_enabled':session.get('dflash_enabled') is True}
        if model_profile is not None:
            row['model_profile'] = model_profile
        if require_resident:
            row['require_resident'] = True
            row['queue_order_ns'] = time.time_ns()
        queue.append(row)
        session['updated_at'] = now
        write_record_atomically(store.resolve_session_record_path(session_id), session)
        return {'request': dict(row), 'duplicate': False}


def prepare_legacy_chat_request(session_store_instance, chat_session_identifier):
    """미접수된 기존 Qwen 요청만 최초 접수 시각을 보존해 공용 경로로 옮긴다."""
    from workflow.common.hermes_model_routing import COMPLEX_MODEL
    with session_store_instance.hold_session_storage_lock():
        session_queue_record = session_store_instance.read_session_record_locked(chat_session_identifier)
        session_queue_rows = session_queue_record.get('chat_queue', [])
        if not isinstance(session_queue_rows, list) or any(not isinstance(chat_request_record, dict) for chat_request_record in session_queue_rows):
            raise ValueError('대기열 기록 형식 오류')
        pending_request_record = next((chat_request_record for chat_request_record in session_queue_rows if chat_request_record.get('state') in ('queued', 'dispatching')), None)
        if pending_request_record is None:
            return None
        if 'dflash_enabled' not in pending_request_record:
            pending_request_record['dflash_enabled'] = session_queue_record.get('dflash_enabled') is True
            write_record_atomically(session_store_instance.resolve_session_record_path(chat_session_identifier), session_queue_record)
        if ('require_resident' in pending_request_record or pending_request_record.get('model_profile') not in (None, COMPLEX_MODEL)
                or any(session_message_record.get('request_id') == pending_request_record.get('request_id') for session_message_record in session_queue_record['messages'])):
            return dict(pending_request_record)
        if 'queue_order_ns' in pending_request_record:
            raise ValueError('기존 대화 대기 순서의 출처를 확인할 수 없습니다.')
        try:
            request_created_time = datetime.fromisoformat(pending_request_record['created_at'])
            if request_created_time.tzinfo is None or request_created_time.utcoffset() is None:
                raise ValueError('대화 접수 시각에 시간대가 없습니다.')
            request_time_delta = request_created_time.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
            request_order_nanoseconds = (request_time_delta.days * 86400 + request_time_delta.seconds) * 1_000_000_000 + request_time_delta.microseconds * 1000
            if not 0 < request_order_nanoseconds <= time.time_ns():
                raise ValueError('대화 접수 시각이 유효하지 않습니다.')
        except (KeyError, TypeError, OverflowError) as request_time_error:
            raise ValueError('대화 접수 시각을 확인할 수 없습니다.') from request_time_error
        pending_request_record.update(require_resident=True, queue_order_ns=request_order_nanoseconds)
        write_record_atomically(session_store_instance.resolve_session_record_path(chat_session_identifier), session_queue_record)
        return dict(pending_request_record)


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
        if row.get('edit_token'):
            raise ValueError('수정 중인 대기 요청입니다.')
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
        if row is None or row.get('state') != old_state or (new_state == 'dispatching' and row.get('edit_token')):
            raise ValueError('대기 요청 상태가 변경됐거나 수정 중입니다.')
        row['state'] = new_state
        row['revision'] += 1
        if job_id is not None:
            row['job_id'] = job_id
        session['updated_at'] = datetime.now(timezone.utc).isoformat()
        write_record_atomically(store.resolve_session_record_path(session_id), session)
        return dict(row)


def edit(store, session_id, request_id, revision, action, token, prompt=None):
    """대기열에 편집 잠금을 저장하고 명시적으로 저장 또는 취소한다."""
    if not isinstance(request_id,str) or not _REQUEST_ID.fullmatch(request_id) or type(revision) is not int or revision<1 or action not in ('begin','save','cancel') or not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{32}',token):
        raise ValueError('대기 요청 편집 형식 오류')
    if action == 'save': prompt=_text(prompt)
    elif prompt is not None: raise ValueError('편집 입력 형식 오류')
    with store.hold_session_storage_lock():
        session=store.read_session_record_locked(session_id)
        row=next((item for item in session.get('chat_queue',[]) if item.get('request_id')==request_id),None)
        if not isinstance(row,dict) or row.get('state')!='queued' or row.get('revision')!=revision:
            raise ValueError('대기 요청이 변경됐거나 실행을 시작했습니다.')
        owner=row.get('edit_token')
        if action=='begin':
            if owner and owner!=token: raise ValueError('다른 화면에서 수정 중입니다.')
            if owner==token: return dict(row)
            row['edit_token']=token
        else:
            if owner!=token: raise ValueError('편집 소유권을 확인할 수 없습니다.')
            if action=='save': row['prompt']=prompt
            row.pop('edit_token',None)
        row['revision']+=1
        session['updated_at']=datetime.now(timezone.utc).isoformat()
        write_record_atomically(store.resolve_session_record_path(session_id),session)
        return dict(row)
