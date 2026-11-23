"""대화 접수와 공용 GPU 티켓을 같은 접수 순서로 관측한다."""
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from workflow.domains.hermes_agent.session_store import HERMES_SESSION_ID_PATTERN, HERMES_SESSION_REQUEST_PATTERN


def _chat_order(row):
    order = row.get('queue_order_ns')
    if order is None:
        created = datetime.fromisoformat(row['created_at'])
        if created.tzinfo is None or created.utcoffset() is None:
            raise ValueError('대화 대기 시각을 확인할 수 없습니다.')
        delta = created.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        order = (delta.days * 86400 + delta.seconds) * 1_000_000_000 + delta.microseconds * 1000
    if type(order) is not int or order <= 0:
        raise ValueError('대화 대기 순서를 확인할 수 없습니다.')
    return order


def session_queue_file_fingerprints(session_storage_root):
    """원자적 파일 교체를 감지해 서로 다른 시점의 결과가 섞이지 않게 한다."""
    if session_storage_root.is_symlink() or not session_storage_root.is_dir():
        raise ValueError('대화 대기열 경로 오류')
    session_record_paths = list(session_storage_root.glob('[0-9a-f]' * 32 + '.json'))
    if len(session_record_paths) > 10000:
        raise ValueError('대화 대기열 기록이 너무 많습니다.')
    session_file_fingerprints = {}
    for session_record_path in session_record_paths:
        if session_record_path.is_symlink():
            raise ValueError('대화 대기열 경로 오류')
        session_file_metadata = session_record_path.stat()
        session_file_fingerprints[session_record_path.name] = (session_file_metadata.st_ino, session_file_metadata.st_size, session_file_metadata.st_mtime_ns)
    return session_file_fingerprints


def observe_unified_queue(store, session_id):
    """GPU 예약과 대화 기록을 잠금 아래 읽으며 다른 세션의 내용은 공개하지 않는다."""
    from workflow.common import gpu_job_queue
    from workflow.common.gpu_chat_admission import hold_gpu_queue_lock, list_chat_queue_intents_locked
    if not isinstance(session_id, str) or not HERMES_SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError('대화 세션 ID 오류')
    session_storage_root = store.session_storage_root
    with store.hold_session_storage_lock():
        store.read_session_record_locked(session_id)
        session_file_fingerprints = session_queue_file_fingerprints(session_storage_root)
        session_queue_snapshots = [(Path(session_file_name).stem, store.read_session_record_locked(Path(session_file_name).stem))
                                   for session_file_name in session_file_fingerprints]
    queue_root = Path(gpu_job_queue.GPU_QUEUE_DIRECTORY)
    if queue_root.is_symlink():
        raise ValueError('GPU 대기열 경로 오류')
    queue_exists = queue_root.exists()
    lock = hold_gpu_queue_lock(queue_root) if queue_exists else nullcontext()
    with lock:
        gpu_rows = gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True, include_order=True)['jobs'] if queue_exists else []
        queue_intent_records = list_chat_queue_intents_locked(queue_root) if queue_exists else []
        queue_intents_by_resident = {record['resident_id']:record for record in queue_intent_records}
    with store.hold_session_storage_lock():
        if session_queue_file_fingerprints(session_storage_root) != session_file_fingerprints:
            raise ValueError('대화 대기열이 조회 중 변경됐습니다. 다시 조회하세요.')
    chat_rows = []
    chat_job_session_links = {}
    for chat_session_identifier, session_queue_record in session_queue_snapshots:
        session_message_records = session_queue_record.get('messages', [])
        if not isinstance(session_message_records, list) or any(not isinstance(session_message_record, dict) for session_message_record in session_message_records):
            raise ValueError('대화 메시지 형식 오류')
        for session_message_record in session_message_records:
            linked_job_identifier = session_message_record.get('job_id')
            linked_request_identifier = session_message_record.get('request_id')
            if session_message_record.get('role') != 'user' or linked_job_identifier is None or linked_request_identifier is None:
                continue
            if not isinstance(linked_job_identifier, str) or not isinstance(linked_request_identifier, str) or not HERMES_SESSION_REQUEST_PATTERN.fullmatch(linked_request_identifier):
                raise ValueError('대화 작업 연결 형식 오류')
            linked_chat_identity = (chat_session_identifier, linked_request_identifier)
            if linked_job_identifier in chat_job_session_links and chat_job_session_links[linked_job_identifier] != linked_chat_identity:
                raise ValueError('대화 작업이 여러 요청에 연결되어 있습니다.')
            chat_job_session_links[linked_job_identifier] = linked_chat_identity
        session_queue_rows = session_queue_record.get('chat_queue', [])
        if not isinstance(session_queue_rows, list) or any(not isinstance(chat_request_record, dict) for chat_request_record in session_queue_rows):
            raise ValueError('대화 대기열 형식 오류')
        for chat_request_record in session_queue_rows:
            if chat_request_record.get('state') not in ('queued', 'dispatching'):
                continue
            chat_request_identifier = chat_request_record.get('request_id')
            if not isinstance(chat_request_identifier, str) or not HERMES_SESSION_REQUEST_PATTERN.fullmatch(chat_request_identifier):
                raise ValueError('대화 대기 요청 ID 오류')
            chat_request_order = _chat_order(chat_request_record)
            chat_resident_identifier = 'start_' + hashlib.sha256((chat_session_identifier + ':' + chat_request_identifier).encode()).hexdigest()
            queue_intent_record = queue_intents_by_resident.get(chat_resident_identifier)
            if queue_intent_record is not None and (queue_intent_record['session_id'], queue_intent_record['request_id'], queue_intent_record['order_ns']) != (chat_session_identifier, chat_request_identifier, chat_request_order):
                raise ValueError('공용 대화 대기열 순서가 일치하지 않습니다.')
            chat_rows.append({'kind':'chat', 'id':chat_request_identifier, 'own_session':chat_session_identifier == session_id,
                              'state':chat_request_record['state'], 'order_ns':str(chat_request_order), 'priority':0,
                              'indexed':queue_intent_record is not None, '_resident_id':chat_resident_identifier, '_session_id':chat_session_identifier})
            if len(chat_rows) > 1000:
                raise ValueError('대화 대기 요청이 너무 많아 공용 순서를 확인할 수 없습니다.')
    if not queue_exists and queue_root.exists():
        raise ValueError('GPU 대기열이 조회 중 생성됐습니다. 다시 조회하세요.')
    by_resident = {row['_resident_id']:row for row in chat_rows}
    chat_rows_by_request = {(chat_queue_row['_session_id'], chat_queue_row['id']):chat_queue_row for chat_queue_row in chat_rows}
    results = []
    for row in gpu_rows:
        chat = by_resident.get(row['id']) if row['service'] == 'hermes-agent' else None
        linked_chat_identity = chat_job_session_links.get(row['id']) if row['service'] == 'hermes-agent' and row.get('session_job') is True else None
        if chat is None and linked_chat_identity is not None:
            chat = chat_rows_by_request.get(linked_chat_identity)
            if chat is None:
                results.append({'kind':'chat', 'id':linked_chat_identity[1], 'own_session':linked_chat_identity[0] == session_id,
                                'state':'gpu_queued', 'order_ns':row['order_ns'], 'priority':row['priority'],
                                'indexed':True, 'ticket_id':row['id'], **({'wait_reason':row['wait_reason']} if 'wait_reason' in row else {})})
                continue
        if chat is not None:
            chat['priority'] = row['priority']
            chat['state'] = 'gpu_queued'
            chat['ticket_id'] = row['id']
            if 'wait_reason' in row:
                chat['wait_reason'] = row['wait_reason']
        else:
            results.append({'kind':'task', 'id':row['id'], 'service':row.get('source_service', row['service']),
                            'state':'gpu_queued', 'order_ns':row['order_ns'], 'priority':row['priority'],
                            **({'wait_reason':row['wait_reason']} if 'wait_reason' in row else {})})
    for row in chat_rows:
        row.pop('_resident_id')
        row.pop('_session_id')
        results.append(row)
    results.sort(key=lambda row:(row['priority'], int(row['order_ns']), row['kind'], row['id']))
    return {'session_id':session_id, 'entries':results,
            'note':'접수 순서입니다. 선행 작업, GPU 메모리와 예약 조건에 따라 실행 순서는 달라질 수 있습니다.'}
