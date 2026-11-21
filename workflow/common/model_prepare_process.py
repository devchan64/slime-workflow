"""게이트웨이와 수명이 분리된 모델 준비 프로세스."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import stat
from contextlib import contextmanager, nullcontext

from workflow.common.generation_records import write_record_atomically


def inspect_detached_preparation(current_state_root):
    current_state_root.mkdir(parents=True, exist_ok=True)
    with (current_state_root/'worker.lock').open('a') as current_lock_file:
        try:
            fcntl.flock(current_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'running'
        else:
            fcntl.flock(current_lock_file, fcntl.LOCK_UN)
    current_status_path = current_state_root/'status.json'
    try:
        current_status_value = json.loads(current_status_path.read_text(encoding='utf-8')).get('status', 'idle')
    except (OSError, ValueError, AttributeError):
        return 'idle'
    return 'failed' if current_status_value == 'running' else current_status_value if current_status_value in ('idle', 'failed', 'completed') else 'failed'


def start_detached_preparation(current_state_root, current_command_prefix, current_working_root, return_process_value=False, current_log_path=None, current_usage_guard=None):
    current_state_root.mkdir(parents=True, exist_ok=True)
    current_lock_file = (current_state_root/'worker.lock').open('a')
    try:
        try:
            fcntl.flock(current_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None if return_process_value else {'preparation_status': 'running'}
        with (current_usage_guard if current_usage_guard is not None else nullcontext(None)) as current_usage_handle:
            current_status_path = current_state_root/'status.json'
            write_record_atomically(current_status_path, {'status': 'running'})
            try:
                with (current_log_path or current_state_root/'worker.log').open('ab') as current_log_file:
                    current_pass_descriptors = (current_lock_file.fileno(),) + ((current_usage_handle.fileno(),) if current_usage_handle is not None else ())
                    current_process_handle = subprocess.Popen([*current_command_prefix, '--status-path', str(current_status_path), '--lock-fd', str(current_lock_file.fileno())],
                        cwd=current_working_root, stdout=current_log_file, stderr=subprocess.STDOUT,
                        start_new_session=True, pass_fds=current_pass_descriptors)
            except BaseException:
                write_record_atomically(current_status_path, {'status': 'failed'})
                raise
            return current_process_handle if return_process_value else {'preparation_status': 'running'}
    finally:
        current_lock_file.close()


def resolve_model_preparation_root(current_working_root, current_profile_name):
    from workflow.common.model_prepare_worker import MODEL_PREPARATION_PROFILES
    if current_profile_name not in MODEL_PREPARATION_PROFILES:
        raise ValueError('등록되지 않은 모델 준비 종류입니다.')
    return Path(current_working_root)/'.local/model-preparation'/current_profile_name


@contextmanager
def hold_registered_preparation_guard(current_working_root,current_profile_name):
    """모델 준비 시작과 짧은 임계 구간이 겹치지 않도록 공용 잠금을 잡는다."""
    current_state_root=resolve_model_preparation_root(current_working_root,current_profile_name)
    if current_state_root.is_symlink():raise ValueError('모델 준비 경로에 심볼릭 링크를 사용할 수 없습니다.')
    current_state_root.mkdir(parents=True,exist_ok=True)
    try:current_lock_descriptor=os.open(current_state_root/'worker.lock',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
    except OSError as current_lock_error:raise ValueError('모델 준비 잠금을 확인할 수 없습니다.') from current_lock_error
    with os.fdopen(current_lock_descriptor,'a') as current_lock_handle:
        if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):raise ValueError('모델 준비 잠금은 일반 파일이어야 합니다.')
        try:fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:raise ValueError('모델 준비가 진행 중입니다.') from current_lock_error
        yield


class HermesModelUsageBusy(ValueError):
    """Hermes 모델 사용 잠금이 다른 준비 또는 실행에 점유되었다."""


@contextmanager
def hold_hermes_model_usage_guard(current_working_root):
    """Hermes 모델 준비와 추론을 별도 잠금으로 상호 배제한다."""
    current_state_root = resolve_model_preparation_root(current_working_root, 'hermes-model')
    if current_state_root.is_symlink():
        raise ValueError('모델 사용 잠금 경로 오류')
    current_state_root.mkdir(parents=True, exist_ok=True)
    try:
        current_lock_descriptor = os.open(current_state_root/'model-use.lock', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
    except OSError as current_lock_error:
        raise ValueError('Hermes 모델 사용 잠금을 확인할 수 없습니다.') from current_lock_error
    with os.fdopen(current_lock_descriptor, 'a') as current_lock_handle:
        if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):
            raise ValueError('Hermes 모델 사용 잠금은 일반 파일이어야 합니다.')
        try:
            fcntl.flock(current_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:
            raise HermesModelUsageBusy('Hermes 모델이 준비 또는 실행 중입니다. 종료 후 다시 시도하세요.') from current_lock_error
        yield current_lock_handle


def inspect_registered_preparation(current_working_root, current_profile_name):
    return inspect_detached_preparation(resolve_model_preparation_root(current_working_root, current_profile_name))


def inspect_registered_preparation_strict(current_working_root, current_profile_name):
    """준비 상태 기록의 손상·접근 실패를 유휴 상태와 구별한다."""
    current_state_root = resolve_model_preparation_root(current_working_root, current_profile_name)
    if current_state_root.is_symlink():
        raise ValueError('모델 준비 경로에 심볼릭 링크를 사용할 수 없습니다.')
    current_state_root.mkdir(parents=True, exist_ok=True)
    current_lock_descriptor = os.open(current_state_root/'worker.lock', os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
    with os.fdopen(current_lock_descriptor, 'a') as current_lock_handle:
        if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):
            raise ValueError('모델 준비 잠금은 일반 파일이어야 합니다.')
        try:
            fcntl.flock(current_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 'running'
        try:
            try:
                current_status_descriptor = os.open(current_state_root/'status.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            except FileNotFoundError:
                return 'idle'
            with os.fdopen(current_status_descriptor, 'rb') as current_status_stream:
                current_status_stat = os.fstat(current_status_stream.fileno())
                if not stat.S_ISREG(current_status_stat.st_mode) or current_status_stat.st_size > 65536:
                    raise ValueError('모델 준비 상태 파일 오류')
                current_status_bytes = current_status_stream.read(65537)
                if len(current_status_bytes) > 65536:
                    raise ValueError('모델 준비 상태 파일 오류')
                current_status_record = json.loads(current_status_bytes)
            if not isinstance(current_status_record, dict) or current_status_record.get('status') not in ('idle','failed','completed','running'):
                raise ValueError('모델 준비 상태 기록 오류')
            return 'failed' if current_status_record['status'] == 'running' else current_status_record['status']
        finally:
            fcntl.flock(current_lock_handle, fcntl.LOCK_UN)


def start_registered_preparation(current_working_root, current_profile_name):
    import sys
    current_state_root = resolve_model_preparation_root(current_working_root, current_profile_name)
    current_usage_guard = hold_hermes_model_usage_guard(current_working_root) if current_profile_name == 'hermes-model' else None
    return start_detached_preparation(current_state_root, [sys.executable, '-m', 'workflow.common.model_prepare_worker', '--profile', current_profile_name], current_working_root, current_usage_guard=current_usage_guard)
