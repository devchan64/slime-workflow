"""Session-owned, fail-closed delivery to a running agent's control socket."""
import json
import os
from pathlib import Path
import socket
import stat

from .live_instruction_store import submit, transition


def deliver(manager, store, payload):
    if set(payload) != {'session_id', 'request_id', 'job_id', 'mode', 'text'}:
        raise ValueError('지시 요청 형식 오류')
    session_id, request_id, job_id = payload['session_id'], payload['request_id'], payload['job_id']
    session = store.read_session_record(session_id)
    if not any(message.get('job_id') == job_id for message in session.get('messages', [])):
        raise ValueError('현재 세션의 작업이 아닙니다.')
    job = manager.resolve_hermes_job_path(job_id)
    status_path = job / 'status.json'
    if status_path.is_symlink() or not status_path.is_file():
        raise ValueError('작업 상태를 확인할 수 없습니다.')
    status = json.loads(status_path.read_text())
    row = submit(store, session_id, request_id, job_id, payload['mode'], payload['text'])
    if row['state'] != 'pending':
        return row
    if status.get('status') != 'running':
        return transition(store, session_id, request_id, 'pending', 'undelivered')
    control = job / 'live-control'
    endpoint = control / 'agent.sock'
    if control.is_symlink() or not control.is_dir():
        return transition(store, session_id, request_id, 'pending', 'undelivered')
    connection = None
    try:
        if not stat.S_ISSOCK(endpoint.lstat().st_mode):
            raise OSError('not a socket')
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(2)
        # Linux AF_UNIX paths are limited to 107 bytes; use a held directory fd.
        directory_fd = os.open(control, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            connection.connect(f'/proc/self/fd/{directory_fd}/agent.sock')
        finally:
            os.close(directory_fd)
    except OSError:
        if connection is not None:
            connection.close()
        return transition(store, session_id, request_id, 'pending', 'undelivered')
    with connection:
        transition(store, session_id, request_id, 'pending', 'delivering')
        try:
            connection.sendall(json.dumps({key: payload[key] for key in ('request_id', 'mode', 'text')}, ensure_ascii=False).encode() + b'\n')
            reply = b''
            while not reply.endswith(b'\n') and len(reply) <= 4096:
                part = connection.recv(4096)
                if not part:
                    break
                reply += part
            answer = json.loads(reply)
            if not isinstance(answer, dict) or answer.get('request_id') != request_id or answer.get('state') not in ('accepted', 'undelivered', 'unknown'):
                raise ValueError('잘못된 지시 응답')
            state = answer['state']
        except (OSError, ValueError, TypeError):
            state = 'unknown'
    return transition(store, session_id, request_id, 'delivering', state)


def settle(manager, store, session_id, rows):
    """Settle from explicit receipts; unknown outcomes are never replayed."""
    for row in rows:
        state = row.get('state')
        if state not in ('accepted', 'delivering', 'pending', 'unknown'):
            continue
        try:
            job = manager.resolve_hermes_job_path(row['job_id'])
            path = job / 'live-control' / 'settled.json'
            receipt = None
            if not path.parent.is_symlink() and not path.is_symlink() and path.is_file() and path.stat().st_size <= 100000:
                receipts = json.loads(path.read_text())
                if isinstance(receipts, list):
                    receipt = next((item for item in receipts if isinstance(item, dict) and item.get('request_id') == row['request_id']), None)
            if state in ('accepted', 'delivering', 'unknown') and receipt and receipt.get('state') in ('applied', 'undelivered'):
                row.update(transition(store, session_id, row['request_id'], state, receipt['state']))
                continue
            status_path = job / 'status.json'
            if status_path.is_symlink() or not status_path.is_file():
                continue
            status = json.loads(status_path.read_text())
            if state != 'unknown' and isinstance(status, dict) and status.get('status') in ('completed', 'failed', 'cancelled', 'canceled'):
                outcome = 'undelivered' if state == 'pending' else 'unknown'
                row.update(transition(store, session_id, row['request_id'], state, outcome))
        except (ValueError, OSError, TypeError, KeyError):
            continue
    return rows
