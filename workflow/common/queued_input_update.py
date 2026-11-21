"""Atomic queued-request update guarded by the GPU reservation lock."""
import fcntl
import hashlib
import json
from pathlib import Path

from workflow.common.generation_records import write_record_atomically
from workflow.common.gpu_job_queue import inspect_gpu_ticket_executor_identity, list_gpu_queue_record_paths


def request_revision(request):
    return hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def update_waiting_request(job_dir, queue_dir, expected_revision, update):
    """Update one request under the reservation lock; callback must validate all changes.

    This low-level primitive does not update attachments or history indexes; callers
    must supply a transaction that preserves those resources before exposing it.
    """
    job_dir, queue_dir = Path(job_dir), Path(queue_dir)
    if job_dir.is_symlink() or not job_dir.is_dir() or queue_dir.is_symlink() or not queue_dir.is_dir():
        raise ValueError('작업 또는 대기열 경로를 확인할 수 없습니다.')
    lock = queue_dir / 'execution.lock'
    if lock.is_symlink() or not lock.is_file():
        raise ValueError('대기열 잠금을 확인할 수 없습니다.')
    with lock.open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        status_path, request_path = job_dir/'status.json', job_dir/'request.json'
        if status_path.is_symlink() or request_path.is_symlink():
            raise ValueError('작업 기록 경로를 확인할 수 없습니다.')
        status = json.loads(status_path.read_text())
        if not isinstance(status, dict) or status.get('status') != 'queued':
            raise ValueError('대기 중인 작업만 수정할 수 있습니다.')
        if (job_dir/'cancel.request').exists() or (job_dir/'pause.request').exists():
            raise ValueError('중단 또는 일시정지 요청이 있는 작업은 수정할 수 없습니다.')
        job_path = str(job_dir.resolve(strict=True))
        matches = []
        for path in list_gpu_queue_record_paths(queue_dir):
            if path.is_symlink():
                raise ValueError('대기열 기록을 확인할 수 없습니다.')
            ticket = json.loads(path.read_text())
            if not isinstance(ticket, dict) or not isinstance(ticket.get('path'), str):
                raise ValueError('대기열 기록을 확인할 수 없습니다.')
            if ticket['path'] == job_path:
                matches.append(ticket)
        if len(matches) != 1 or inspect_gpu_ticket_executor_identity(matches[0]) != 'verified':
            raise ValueError('실행 대기 티켓의 신원을 확인할 수 없습니다.')
        active_dir = queue_dir/'active'
        if active_dir.is_symlink():
            raise ValueError('실행 예약을 확인할 수 없습니다.')
        for path in list_gpu_queue_record_paths(active_dir) if active_dir.exists() else []:
            if path.is_symlink():
                raise ValueError('실행 예약을 확인할 수 없습니다.')
            record = json.loads(path.read_text())
            if not isinstance(record, dict) or not isinstance(record.get('path'), str):
                raise ValueError('실행 예약을 확인할 수 없습니다.')
            if record['path'] == job_path:
                raise ValueError('이미 실행 예약된 작업은 수정할 수 없습니다.')
        original = json.loads(request_path.read_text())
        if not isinstance(original, dict) or request_revision(original) != expected_revision:
            raise ValueError('입력이 변경되었습니다. 다시 조회해 주세요.')
        replacement = update(original)
        if not isinstance(replacement, dict):
            raise ValueError('수정된 입력을 확인할 수 없습니다.')
        write_record_atomically(request_path, replacement)
        return request_revision(replacement)
