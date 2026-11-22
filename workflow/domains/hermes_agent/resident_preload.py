"""선택한 대화의 Qwen 상주 선적재 정책. 판단이 불확실하면 접수하지 않는다."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat

from workflow.common.generation_records import write_record_atomically
from workflow.domains.hermes_agent.resident_queue import RESIDENT_ROOT

POLICY_ROOT = RESIDENT_ROOT.parent / 'resident-preload'


@contextmanager
def locked_policy(root=None):
    root = Path(root or POLICY_ROOT)
    if root.is_symlink():
        raise ValueError('선적재 정책 경로 오류')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_uid != os.geteuid() or root.stat().st_mode & 0o077:
        raise ValueError('선적재 정책은 개인 디렉터리에 저장해야 합니다.')
    fd = os.open(root / '.lock', os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'a') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError('선적재 정책 잠금 오류')
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield root


def read_policy(root):
    from workflow.domains.hermes_agent.delegation_store import read_bounded_delegation_record
    path = root / 'policy.json'
    if not path.exists() and not path.is_symlink():
        return None
    record = read_bounded_delegation_record(path)
    if (not isinstance(record, dict) or set(record) != {'session_id', 'enabled', 'pending_id'}
            or not isinstance(record['session_id'], str) or not re.fullmatch('[a-f0-9]{32}', record['session_id'])
            or type(record['enabled']) is not bool or (record['pending_id'] is not None
            and (not isinstance(record['pending_id'], str) or not re.fullmatch('[a-f0-9]{32}', record['pending_id'])))):
        raise ValueError('선적재 정책 형식 오류')
    return record


def save_policy(root, session_id, enabled):
    if not isinstance(session_id, str) or not re.fullmatch('[a-f0-9]{32}', session_id) or type(enabled) is not bool:
        raise ValueError('선적재 정책 입력 오류')
    write_record_atomically(root / 'policy.json', {'session_id':session_id, 'enabled':enabled, 'pending_id':None})


def preload_if_idle(root=None):
    """실제 GPU와 대기·예약이 모두 비었을 때만 같은 요청 ID로 접수한다."""
    from workflow.common.gpu_status import read_gpu_status
    from workflow.common import gpu_job_queue
    from workflow.domains.hermes_agent.resident_queue import find_session_resident, ensure_session_resident
    from workflow.domains.hermes_agent.session_store import HermesSessionStore
    from workflow.domains.hermes_agent.service import validate_hermes_runtime_ready
    with locked_policy(root) as policy_root:
        policy = read_policy(policy_root)
        if not policy or not policy['enabled']:
            return 'disabled'
        session = policy['session_id']
        HermesSessionStore().read_session_record(session)
        if find_session_resident(session):
            if policy['pending_id'] is not None:
                save_policy(policy_root, session, True)
            return 'resident'
        gpu = read_gpu_status()
        if gpu.get('status') != 'idle' or gpu.get('processes') != []:
            return 'busy'
        queue = gpu_job_queue.GPU_QUEUE_DIRECTORY
        if gpu_job_queue.read_priority_tickets() or (queue / 'active').exists() and gpu_job_queue.list_gpu_queue_record_paths(queue / 'active'):
            return 'busy'
        validate_hermes_runtime_ready('qwen3.8-27b')
        if policy['pending_id'] is None:
            policy['pending_id'] = secrets.token_hex(16)
            write_record_atomically(policy_root / 'policy.json', policy)
        result = ensure_session_resident(session, policy['pending_id'])
        return result['state']
