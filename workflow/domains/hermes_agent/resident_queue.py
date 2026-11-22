"""상주 모델을 공용 GPU 대기열에 한 번만 접수한다.

아직 사용자 명령에 공개하지 않는다. 접수 결과가 불확실하면 재접수하지 않는다.
"""
from contextlib import contextmanager, nullcontext
import fcntl
import http.client
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import sys

from workflow.common.generation_records import write_record_atomically
from workflow.common.gpu_job_queue import launch_gpu_process
from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record

ROOT = Path(__file__).resolve().parents[3]
RESIDENT_ROOT = ROOT / '.local/hermes-agent/residents'
_ID = re.compile(r'[A-Za-z0-9_-]{8,80}\Z')
_SESSION = re.compile(r'[a-f0-9]{32}\Z')


@contextmanager
def _lock(root):
    if root.is_symlink():
        raise ValueError('상주 모델 경로 오류')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(root / '.lock', os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'a') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('상주 모델 잠금 형식 오류')
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def enqueue_resident_once(request_id, session_id, *, root=RESIDENT_ROOT, launcher=launch_gpu_process, recovered_failure_id=None, queue_order_ns=None):
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id) or not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('상주 모델 접수 ID 또는 세션 ID 오류')
    if queue_order_ns is not None:
        import time
        if type(queue_order_ns) is not int or not 0 < queue_order_ns <= time.time_ns():
            raise ValueError('상주 모델 대기 순서 오류')
    root = Path(root)
    with _lock(root):
        directory = root / request_id
        if directory.is_symlink():
            raise ValueError('상주 모델 작업 경로 오류')
        if directory.exists():
            request = read_bounded_delegation_record(directory / 'request.json')
            receipt = read_bounded_delegation_record(directory / 'launch.json')
            if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
                    or request.get('context') != {'session_id':session_id}
                    or not isinstance(receipt, dict) or receipt.get('id') != request_id
                    or receipt.get('state') not in ('dispatching', 'accepted')):
                raise ValueError('기존 상주 모델 접수가 일치하지 않습니다.')
            if recovered_failure_id is not None:
                if request.get('recovered_failure_id') != recovered_failure_id:
                    raise ValueError('재적재 원 실패 작업이 일치하지 않습니다.')
                previous = root / recovered_failure_id
                if previous.is_symlink() or not previous.is_dir():
                    raise ValueError('복구할 실패 상주 작업을 찾을 수 없습니다.')
                if receipt['state'] == 'accepted':
                    write_record_atomically(previous / 'recovery.json', {'session_id':session_id, 'failed_id':recovered_failure_id, 'retry_id':request_id})
            return {'state':'unknown' if receipt['state'] == 'dispatching' else 'accepted', 'id':request_id, 'duplicate':True}
        recovered_verified = recovered_failure_id is None
        # 다른 접수 ID라도 같은 세션의 상주 모델을 중복 적재하지 않는다.
        for previous in root.iterdir():
            if previous.name == '.lock':
                continue
            if previous.is_symlink() or not previous.is_dir() or not _ID.fullmatch(previous.name):
                raise ValueError('기존 상주 모델 목록을 확인할 수 없습니다.')
            existing = read_bounded_delegation_record(previous / 'request.json')
            if not isinstance(existing, dict) or not isinstance(existing.get('context'), dict):
                raise ValueError('기존 상주 모델 요청을 확인할 수 없습니다.')
            if existing['context'].get('session_id') != session_id:
                continue
            if previous.name == recovered_failure_id:
                if not inspect_failed_resident_cleanup(previous.name, session_id, root=root, _root_locked=True):
                    raise ValueError('실패한 상주 작업의 정리를 확인할 수 없습니다.')
                recovered_verified = True
                continue
            successor_id = _verified_recovery_successor(root, previous.name, session_id)
            if successor_id:
                successor = root / successor_id
                successor_status = read_bounded_delegation_record(successor / 'status.json')
                successor_resident = read_bounded_delegation_record(successor / 'resident-status.json')
                if (isinstance(successor_status, dict) and (successor_status.get('status') == 'completed' or (successor_status.get('status') == 'failed' and type(successor_status.get('exit_code')) is int and successor_status['exit_code'] == 0))
                        and isinstance(successor_resident, dict) and successor_resident.get('status') == 'stopped'):
                    continue
            try:
                previous_status = read_bounded_delegation_record(previous / 'status.json')
                previous_resident = read_bounded_delegation_record(previous / 'resident-status.json')
            except (OSError, ValueError):
                raise ValueError('이 세션의 기존 상주 모델 종료를 확인할 수 없습니다.')
            clean_exit = isinstance(previous_status, dict) and (previous_status.get('status') == 'completed' or (previous_status.get('status') == 'failed' and type(previous_status.get('exit_code')) is int and previous_status['exit_code'] == 0))
            if not clean_exit or not isinstance(previous_resident, dict) or previous_resident.get('status') != 'stopped':
                raise ValueError('이 세션의 기존 상주 모델이 종료되지 않았습니다.')
        if not recovered_verified:
            raise ValueError('복구할 실패 상주 작업을 찾을 수 없습니다.')
        def launch_verified():
            directory.mkdir(mode=0o700)
            request = {'model_profile':'qwen3.8-27b', 'context':{'session_id':session_id}, 'release_token':secrets.token_hex(16)}
            if queue_order_ns is not None:
                request['queue_order_ns'] = queue_order_ns
            if recovered_failure_id is not None:
                request['recovered_failure_id'] = recovered_failure_id
            write_record_atomically(directory / 'request.json', request)
            receipt = {'id':request_id, 'state':'dispatching'}
            write_record_atomically(directory / 'launch.json', receipt)
            with (directory / 'worker.log').open('a', encoding='utf-8') as log:
                launcher([sys.executable, str(ROOT / 'workflow/domains/hermes_agent/resident_worker.py'), str(directory.resolve())],
                         directory, 'hermes-agent', stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True, cwd=ROOT)
            write_record_atomically(directory / 'launch.json', {'id':request_id, 'state':'accepted'})
            if recovered_failure_id is not None:
                write_record_atomically(root / recovered_failure_id / 'recovery.json', {'session_id':session_id, 'failed_id':recovered_failure_id, 'retry_id':request_id})
            return True
        if recovered_failure_id is not None:
            if not inspect_failed_resident_cleanup(recovered_failure_id, session_id, root=root, _root_locked=True, _on_verified=launch_verified):
                raise ValueError('실패한 상주 작업의 정리를 확인할 수 없습니다.')
        else:
            launch_verified()
        return {'state':'accepted', 'id':request_id, 'duplicate':False}


def request_resident_release(request_id, session_id, *, root=RESIDENT_ROOT):
    """공용 예약과 작업자 신원이 확인된 상주 모델에만 정상 종료를 요청한다."""
    from workflow.common import gpu_job_queue
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id) or not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('상주 모델 접수 ID 또는 세션 ID 오류')
    root = Path(root)
    with _lock(root):
        directory = root / request_id
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError('상주 모델 작업 경로 오류')
        request = read_bounded_delegation_record(directory / 'request.json')
        receipt = read_bounded_delegation_record(directory / 'launch.json')
        status = read_bounded_delegation_record(directory / 'resident-status.json')
        token = request.get('release_token') if isinstance(request, dict) else None
        if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
                or request.get('context') != {'session_id':session_id} or not isinstance(token, str)
                or not re.fullmatch(r'[a-f0-9]{32}', token) or receipt != {'id':request_id, 'state':'accepted'}
                or not isinstance(status, dict) or status.get('model') != 'qwen3.8-27b'
                or status.get('status') not in ('ready', 'draining') or type(status.get('worker_pid')) is not int):
            raise ValueError('상주 모델의 요청 또는 실행 상태를 확인할 수 없습니다.')
        with hold_writer_reservation_queue_lock() as active_root:
            matches = []
            for path in active_root.glob('*.json'):
                record = read_bounded_delegation_record(path)
                if not isinstance(record, dict) or not isinstance(record.get('path'), str) or not isinstance(record.get('service'), str):
                    raise ValueError('GPU 예약 목록을 확인할 수 없습니다.')
                if record['path'] == str(directory.resolve()):
                    matches.append(record)
            if len(matches) != 1 or matches[0]['service'] != 'hermes-agent' or matches[0].get('worker_pgid') != status['worker_pid']:
                raise ValueError('상주 모델의 GPU 예약을 확인할 수 없습니다.')
            record = matches[0]
            if gpu_job_queue.inspect_gpu_ticket_executor_identity(record) != 'verified':
                raise ValueError('GPU 예약 실행기를 확인할 수 없습니다.')
            descriptor = gpu_job_queue.open_verified_hermes_process_group(record)
            if descriptor is None:
                raise ValueError('상주 모델 작업자 신원을 확인할 수 없습니다.')
            try:
                release_path = directory / 'release.request'
                if release_path.is_symlink():
                    raise ValueError('상주 모델 종료 요청 경로 오류')
                write_record_atomically(release_path, {'token':token})
            finally:
                os.close(descriptor)
        return {'state':'requested', 'id':request_id}


def _healthy_resident_socket(directory):
    from workflow.domains.hermes_agent.resident_client import connect_resident_socket
    client = connect_resident_socket(directory, 'resident-model.sock', timeout=2)
    try:
        client.sendall(b'GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n')
        response = http.client.HTTPResponse(client)
        response.begin()
        if response.status != 200:
            return False
        return json.loads(response.read(4097)).get('status') == 'ok'
    except (OSError, ValueError, AttributeError, http.client.HTTPException):
        return False
    finally:
        client.close()


def _server_is_child(server_pid, worker_pid):
    if type(server_pid) is not int or server_pid <= 1 or type(worker_pid) is not int:
        return False
    try:
        fields = Path(f'/proc/{server_pid}/stat').read_text().rpartition(') ')[2].split()
        return fields[0] not in ('Z', 'X') and int(fields[1]) == worker_pid
    except (OSError, ValueError, IndexError):
        return False


def inspect_failed_resident_cleanup(request_id, session_id, *, root=RESIDENT_ROOT, gpu_idle=None, _root_locked=False, _on_verified=None):
    """실패한 상주 실행기의 종료와 대기열·예약 부재를 읽기 전용으로 확인한다."""
    from workflow.common import gpu_job_queue
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    from workflow.domains.hermes_agent.gpu_handoff_kimodo import _gpu_idle_fresh
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id) or not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('상주 모델 접수 ID 또는 세션 ID 오류')
    idle = gpu_idle or _gpu_idle_fresh
    root = Path(root)
    try:
        if root.is_symlink() or not root.is_dir():
            return False
        with nullcontext() if _root_locked else _lock(root):
            directory = root / request_id
            if directory.is_symlink() or not directory.is_dir():
                return False
            request = read_bounded_delegation_record(directory / 'request.json')
            launch = read_bounded_delegation_record(directory / 'launch.json')
            if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
                    or request.get('context') != {'session_id':session_id}
                    or launch != {'id':request_id,'state':'accepted'}):
                return False
            descriptor = os.open(directory / 'execution.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, 'r') as lock:
                if not stat.S_ISREG(os.fstat(lock.fileno()).st_mode):
                    return False
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return False
                status = read_bounded_delegation_record(directory / 'status.json')
                if not isinstance(status, dict) or status.get('status') != 'failed' or type(status.get('exit_code')) is not int or status['exit_code'] == 0:
                    return False
                target = str(directory.resolve())
                with hold_writer_reservation_queue_lock() as active_root:
                    for path in list(active_root.glob('*.json')) + list(gpu_job_queue.GPU_QUEUE_DIRECTORY.glob('*.json')):
                        record = read_bounded_delegation_record(path)
                        if not isinstance(record, dict) or not isinstance(record.get('path'), str):
                            return False
                        if record['path'] == target:
                            return False
                    if idle() is not True or read_bounded_delegation_record(directory / 'status.json') != status:
                        return False
                    return True if _on_verified is None else _on_verified()
    except (OSError, ValueError, TypeError):
        return False
def inspect_resident(request_id, session_id, *, root=RESIDENT_ROOT):
    """예약, 소유 프로세스 및 헬스를 대조해 현재 상주 상태를 관측한다."""
    from workflow.common import gpu_job_queue
    from workflow.domains.hermes_agent.writer_reservation import hold_writer_reservation_queue_lock
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id) or not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('상주 모델 접수 ID 또는 세션 ID 오류')
    root = Path(root)
    with _lock(root):
        directory = root / request_id
        try:
            directory.lstat()
        except FileNotFoundError:
            return {'state':'not_found'}
        if directory.is_symlink() or not directory.is_dir():
            return {'state':'unknown'}
        try:
            request = read_bounded_delegation_record(directory / 'request.json')
            receipt = read_bounded_delegation_record(directory / 'launch.json')
            if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
                    or request.get('context') != {'session_id':session_id} or not isinstance(receipt, dict)
                    or receipt.get('id') != request_id or receipt.get('state') not in ('dispatching', 'accepted')):
                return {'state':'unknown'}
            if receipt['state'] == 'dispatching':
                return {'state':'unknown'}
            queue_status = read_bounded_delegation_record(directory / 'status.json')
            if not isinstance(queue_status, dict):
                return {'state':'unknown'}
            state = queue_status.get('status')
            if state == 'queued':
                return {'state':'queued'}
            if state not in ('running', 'completed', 'failed', 'cancelled'):
                return {'state':'unknown'}
            try:
                status = read_bounded_delegation_record(directory / 'resident-status.json')
            except FileNotFoundError:
                return {'state':'running' if state == 'running' else 'unknown'}
            if not isinstance(status, dict) or status.get('model') != 'qwen3.8-27b':
                return {'state':'unknown'}
            healthy = _healthy_resident_socket(directory) if state == 'running' and status.get('status') == 'ready' else False
            with hold_writer_reservation_queue_lock() as active_root:
                if read_bounded_delegation_record(directory / 'resident-status.json') != status:
                    return {'state':'unknown'}
                matches = []
                for path in active_root.glob('*.json'):
                    record = read_bounded_delegation_record(path)
                    if not isinstance(record, dict) or not isinstance(record.get('path'), str) or not isinstance(record.get('service'), str):
                        return {'state':'unknown'}
                    if record['path'] == str(directory.resolve()):
                        matches.append(record)
                if not matches and (state == 'completed' or (state == 'failed' and type(queue_status.get('exit_code')) is int and queue_status['exit_code'] == 0)) and status.get('status') == 'stopped':
                    return {'state':'released'}
                if not matches and state == 'running' and status.get('status') == 'stopped':
                    # 작업 상태를 읽은 뒤 예약이 정리되는 경우의 일시적인 관측이다.
                    latest = read_bounded_delegation_record(directory / 'status.json')
                    if isinstance(latest, dict) and latest.get('status') == 'completed':
                        return {'state':'released'}
                    return {'state':'running'}
                if len(matches) != 1 or matches[0]['service'] != 'hermes-agent':
                    return {'state':'unknown'}
                record = matches[0]
                if (record.get('worker_pgid') != status.get('worker_pid')
                        or gpu_job_queue.inspect_gpu_ticket_executor_identity(record) != 'verified'):
                    return {'state':'unknown'}
                if status.get('status') == 'stopped' and state in ('running', 'completed'):
                    # 서버는 정상 종료했고 실행기가 최종 상태와 예약을 정리 중이다.
                    return {'state':'running'}
                descriptor = gpu_job_queue.open_verified_hermes_process_group(record)
                if descriptor is None:
                    return {'state':'unknown'}
                try:
                    if state != 'running' or status.get('status') in ('loading', 'draining', 'stopped'):
                        return {'state':'running'}
                    offload = status.get('offload')
                    match = re.fullmatch(r'offloaded (\d+)/(\d+) layers to GPU', offload) if isinstance(offload, str) else None
                    if (status.get('status') != 'ready' or not match or int(match.group(1)) <= 0
                            or match.group(1) != match.group(2) or not _server_is_child(status.get('server_pid'), status.get('worker_pid'))
                            or not healthy):
                        return {'state':'unknown'}
                    return {'state':'ready', 'model':'qwen3.8-27b', 'gpu_loaded':True, 'reservation_verified':True}
                finally:
                    os.close(descriptor)
        except (OSError, ValueError, TypeError):
            return {'state':'unknown'}


@contextmanager
def hold_verified_resident_lease(request_id, session_id, *, root=RESIDENT_ROOT):
    """같은 세션의 확인된 GPU 예약에 사용권을 얻고 수명 내내 보유한다."""
    from workflow.domains.hermes_agent.resident_client import hold_resident_lease
    if inspect_resident(request_id, session_id, root=root).get('state') != 'ready':
        raise ValueError('사용 가능한 상주 모델을 확인할 수 없습니다.')
    with hold_resident_lease(Path(root) / request_id):
        if inspect_resident(request_id, session_id, root=root).get('state') != 'ready':
            raise ValueError('상주 모델 사용권을 얻는 중 상태가 변경되었습니다.')
        yield


def _verified_recovery_successor(root, failed_id, session_id):
    try:
        failed = root / failed_id
        marker = read_bounded_delegation_record(failed / 'recovery.json')
        if (not isinstance(marker, dict) or set(marker) != {'session_id','failed_id','retry_id'}
                or marker['session_id'] != session_id or marker['failed_id'] != failed_id
                or not isinstance(marker['retry_id'], str) or not _ID.fullmatch(marker['retry_id'])
                or marker['retry_id'] == failed_id):
            return None
        successor = root / marker['retry_id']
        if successor.is_symlink() or not successor.is_dir():
            return None
        request = read_bounded_delegation_record(successor / 'request.json')
        launch = read_bounded_delegation_record(successor / 'launch.json')
        if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
                or request.get('context') != {'session_id':session_id} or request.get('recovered_failure_id') != failed_id
                or launch != {'id':marker['retry_id'], 'state':'accepted'}):
            return None
        return marker['retry_id']
    except (OSError, ValueError, TypeError):
        return None


def find_session_resident(session_id, *, root=RESIDENT_ROOT):
    """같은 세션의 유일한 활성 상주 모델을 찾는다. 모호하면 새 모델을 띄우지 않는다."""
    if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ValueError('대화 세션 ID 오류')
    root = Path(root)
    if root.is_symlink():
        raise ValueError('상주 모델 경로 오류')
    if not root.exists():
        return None
    if not root.is_dir():
        raise ValueError('상주 모델 경로 오류')
    candidates = []
    for directory in root.iterdir():
        if directory.name == '.lock':
            continue
        if directory.is_symlink() or not directory.is_dir() or not _ID.fullmatch(directory.name):
            raise ValueError('상주 모델 목록을 확인할 수 없습니다.')
        request = read_bounded_delegation_record(directory / 'request.json')
        if not isinstance(request, dict) or not isinstance(request.get('context'), dict):
            raise ValueError('상주 모델 요청을 확인할 수 없습니다.')
        if request['context'].get('session_id') != session_id:
            continue
        state = inspect_resident(directory.name, session_id, root=root).get('state')
        if state in ('queued', 'running', 'ready'):
            candidates.append(directory.name)
        elif state != 'released' and not _verified_recovery_successor(root, directory.name, session_id):
            raise ValueError('이 세션의 상주 모델 상태를 확인할 수 없습니다.')
    if len(candidates) > 1:
        raise ValueError('이 세션의 상주 모델이 둘 이상입니다. 상태를 확인하세요.')
    return candidates[0] if candidates else None


def ensure_no_other_active_residents(resident_id, *, root=RESIDENT_ROOT):
    """양도 승인 잠금 아래에서 다른 세션의 대기·실행 접수를 거부한다."""
    root = Path(root)
    if not root.exists():
        raise ValueError('상주 모델 목록을 확인할 수 없습니다.')
    with _lock(root):
        for directory in root.iterdir():
            if directory.name == '.lock':
                continue
            if directory.is_symlink() or not directory.is_dir() or not _ID.fullmatch(directory.name):
                raise ValueError('상주 모델 목록을 확인할 수 없습니다.')
            if directory.name == resident_id:
                continue
            receipt = read_bounded_delegation_record(directory / 'launch.json')
            if not isinstance(receipt, dict) or receipt.get('id') != directory.name or receipt.get('state') != 'accepted':
                raise ValueError('다른 상주 모델의 접수 상태를 확인할 수 없습니다.')
            status = read_bounded_delegation_record(directory / 'status.json')
            if not isinstance(status, dict) or status.get('status') not in ('queued','running','completed','failed','cancelled'):
                raise ValueError('다른 상주 모델의 실행 상태를 확인할 수 없습니다.')
            if status['status'] in ('queued','running'):
                raise ValueError('다른 상주 모델이 대기 또는 실행 중입니다. 해당 작업이 끝난 뒤 다시 검토하세요.')


def ensure_session_resident(session_id, request_id, *, root=RESIDENT_ROOT, handoff_store=None, launcher=launch_gpu_process, queue_order_ns=None):
    """사용자가 선택한 3.8 대화의 상주 모델을 한 번만 접수한다."""
    import hashlib
    from workflow.domains.hermes_agent.gpu_handoff_store import GpuHandoffStore
    if not isinstance(request_id, str) or not _ID.fullmatch(request_id):
        raise ValueError('대화 접수 ID 오류')
    def ensure():
        existing = find_session_resident(session_id, root=root)
        if existing:
            return {'state':'accepted', 'id':existing, 'duplicate':True}
        resident_id = 'start_' + hashlib.sha256((session_id + ':' + request_id).encode()).hexdigest()
        return enqueue_resident_once(resident_id, session_id, root=root, launcher=launcher, queue_order_ns=queue_order_ns)
    return (handoff_store or GpuHandoffStore()).run_without_open_session_handoff(session_id, ensure, all_sessions=True)
