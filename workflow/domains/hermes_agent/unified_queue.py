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


def observe_unified_queue(store, session_id):
    """GPU 예약과 대화 기록을 잠금 아래 읽으며 다른 세션의 내용은 공개하지 않는다."""
    from workflow.common import gpu_job_queue
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    if not isinstance(session_id, str) or not HERMES_SESSION_ID_PATTERN.fullmatch(session_id):
        raise ValueError('대화 세션 ID 오류')
    queue_root = Path(gpu_job_queue.GPU_QUEUE_DIRECTORY)
    if queue_root.is_symlink():
        raise ValueError('GPU 대기열 경로 오류')
    queue_exists = queue_root.exists()
    lock = hold_writer_reservation_queue_lock() if queue_exists else nullcontext()
    with lock:
        gpu_rows = gpu_job_queue.list_waiting_gpu_jobs(include_source_identity=True, observation_limits=True, include_order=True)['jobs'] if queue_exists else []
        root = store.session_storage_root
        if root.is_symlink() or not root.is_dir():
            raise ValueError('대화 대기열 경로 오류')
        with store.hold_session_storage_lock():
            paths = list(root.glob('[0-9a-f]' * 32 + '.json'))
            if len(paths) > 10000:
                raise ValueError('대화 대기열 기록이 너무 많습니다.')
            chat_rows = []
            for path in paths:
                session = store.read_session_record_locked(path.stem)
                queue = session.get('chat_queue', [])
                if not isinstance(queue, list) or any(not isinstance(row, dict) for row in queue):
                    raise ValueError('대화 대기열 형식 오류')
                for row in queue:
                    if row.get('state') not in ('queued', 'dispatching'):
                        continue
                    request_id = row.get('request_id')
                    if not isinstance(request_id, str) or not HERMES_SESSION_REQUEST_PATTERN.fullmatch(request_id):
                        raise ValueError('대화 대기 요청 ID 오류')
                    order = _chat_order(row)
                    resident_id = 'start_' + hashlib.sha256((path.stem + ':' + request_id).encode()).hexdigest()
                    chat_rows.append({'kind':'chat', 'id':request_id, 'own_session':path.stem == session_id,
                                      'state':row['state'], 'order_ns':str(order), 'priority':0,
                                      '_resident_id':resident_id})
                    if len(chat_rows) > 1000:
                        raise ValueError('대화 대기 요청이 너무 많아 공용 순서를 확인할 수 없습니다.')
        if not queue_exists and queue_root.exists():
            raise ValueError('GPU 대기열이 조회 중 생성됐습니다. 다시 조회하세요.')
    by_resident = {row['_resident_id']:row for row in chat_rows}
    results = []
    for row in gpu_rows:
        chat = by_resident.get(row['id']) if row['service'] == 'hermes-agent' else None
        if chat is not None:
            chat['priority'] = row['priority']
            chat['state'] = 'gpu_queued'
            chat['ticket_id'] = row['id']
        else:
            results.append({'kind':'task', 'id':row['id'], 'service':row['service'],
                            'state':'gpu_queued', 'order_ns':row['order_ns'], 'priority':row['priority']})
    for row in chat_rows:
        row.pop('_resident_id')
        results.append(row)
    results.sort(key=lambda row:(row['priority'], int(row['order_ns']), row['kind'], row['id']))
    return {'session_id':session_id, 'entries':results,
            'note':'접수 순서입니다. 선행 작업, GPU 메모리와 예약 조건에 따라 실행 순서는 달라질 수 있습니다.'}
