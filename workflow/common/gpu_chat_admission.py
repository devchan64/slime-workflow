"""대화 접수와 상주 모델 GPU 티켓 생성 사이의 짧은 순서 보존 기록."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from workflow.common.generation_records import write_record_atomically

_SESSION_ID_PATTERN = re.compile(r'[a-f0-9]{32}\Z')
_REQUEST_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{8,80}\Z')
_MARKER_FILE_PATTERN = re.compile(r'start_[a-f0-9]{64}\.json\Z')
_ATOMIC_TEMP_FILE_PATTERN = re.compile(r'start_[a-f0-9]{64}\.json\.[a-f0-9]{32}\.tmp\Z')
_ADMISSION_LEASE_NANOSECONDS = 5_000_000_000


@contextmanager
def hold_gpu_queue_lock(queue_root_directory, *, acquire_without_wait=False):
    queue_root_path = Path(queue_root_directory)
    if queue_root_path.is_symlink():
        raise ValueError('GPU 대기열 경로 오류')
    queue_root_path.mkdir(parents=True, exist_ok=True)
    queue_lock_descriptor = os.open(queue_root_path / 'execution.lock', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
    with os.fdopen(queue_lock_descriptor, 'a') as queue_lock_stream:
        if not stat.S_ISREG(os.fstat(queue_lock_stream.fileno()).st_mode):
            raise ValueError('GPU 대기열 잠금 오류')
        fcntl.flock(queue_lock_stream, fcntl.LOCK_EX | (fcntl.LOCK_NB if acquire_without_wait else 0))
        yield queue_root_path


def derive_chat_resident_identifier(chat_session_identifier, chat_request_identifier):
    if not isinstance(chat_session_identifier, str) or not _SESSION_ID_PATTERN.fullmatch(chat_session_identifier) or not isinstance(chat_request_identifier, str) or not _REQUEST_ID_PATTERN.fullmatch(chat_request_identifier):
        raise ValueError('대화 접수 ID 오류')
    return 'start_' + hashlib.sha256((chat_session_identifier + ':' + chat_request_identifier).encode()).hexdigest()


def ensure_gpu_active_directory(queue_root_path):
    """대화가 최초 접수여도 기존 GPU 예약 관측 경로를 사용할 수 있게 한다."""
    active_reservation_directory = queue_root_path / 'active'
    if active_reservation_directory.is_symlink():
        raise ValueError('GPU 활성 예약 경로 오류')
    active_reservation_directory.mkdir(exist_ok=True)


def register_chat_queue_intent(queue_root_directory, chat_session_identifier, chat_request_identifier, queue_order_nanoseconds):
    """대화 요청의 공용 대기열 색인을 멱등으로 저장한다. 메시지 본문은 저장하지 않는다."""
    from workflow.common.gpu_job_queue import read_bounded_gpu_observation_bytes
    resident_request_identifier = derive_chat_resident_identifier(chat_session_identifier, chat_request_identifier)
    if type(queue_order_nanoseconds) is not int or not 0 < queue_order_nanoseconds <= time.time_ns():
        raise ValueError('대화 접수 순서 오류')
    expected_intent_record = {'version':1, 'session_id':chat_session_identifier, 'request_id':chat_request_identifier,
                              'resident_id':resident_request_identifier, 'order_ns':queue_order_nanoseconds}
    with hold_gpu_queue_lock(queue_root_directory) as queue_root_path:
        ensure_gpu_active_directory(queue_root_path)
        intent_directory_path = queue_root_path / 'chat-intents'
        if intent_directory_path.is_symlink():
            raise ValueError('공용 대화 대기열 경로 오류')
        intent_directory_path.mkdir(mode=0o700, exist_ok=True)
        intent_record_path = intent_directory_path / (resident_request_identifier + '.json')
        try:
            existing_intent_record = json.loads(read_bounded_gpu_observation_bytes(intent_record_path, 4096)[0])
        except FileNotFoundError:
            write_record_atomically(intent_record_path, expected_intent_record)
        else:
            if existing_intent_record != expected_intent_record:
                raise ValueError('공용 대화 대기열 접수 기록이 일치하지 않습니다.')
    return expected_intent_record


def retire_chat_queue_intent(queue_root_directory, chat_session_identifier, chat_request_identifier, queue_order_nanoseconds):
    """종료·취소된 대화의 일치하는 공용 색인만 제거한다."""
    from workflow.common.gpu_job_queue import read_bounded_gpu_observation_bytes
    resident_request_identifier = derive_chat_resident_identifier(chat_session_identifier, chat_request_identifier)
    with hold_gpu_queue_lock(queue_root_directory) as queue_root_path:
        intent_directory_path = queue_root_path / 'chat-intents'
        if intent_directory_path.is_symlink():
            raise ValueError('공용 대화 대기열 경로 오류')
        intent_record_path = intent_directory_path / (resident_request_identifier + '.json')
        try:
            existing_intent_record = json.loads(read_bounded_gpu_observation_bytes(intent_record_path, 4096)[0])
        except FileNotFoundError:
            return
        expected_intent_record = {'version':1, 'session_id':chat_session_identifier, 'request_id':chat_request_identifier,
                                  'resident_id':resident_request_identifier, 'order_ns':queue_order_nanoseconds}
        if existing_intent_record != expected_intent_record:
            raise ValueError('제거할 공용 대화 대기열 기록이 일치하지 않습니다.')
        intent_record_path.unlink()


def list_chat_queue_intents_locked(queue_root_directory):
    """GPU 대기열 잠금 아래에서 대화 색인을 검증해 읽는다."""
    from workflow.common.gpu_job_queue import read_bounded_gpu_observation_bytes
    intent_directory_path = Path(queue_root_directory) / 'chat-intents'
    if intent_directory_path.is_symlink():
        raise ValueError('공용 대화 대기열 경로 오류')
    if not intent_directory_path.exists():
        return []
    if not intent_directory_path.is_dir():
        raise ValueError('공용 대화 대기열 경로 오류')
    intent_record_paths = list(intent_directory_path.iterdir())
    if len(intent_record_paths) > 10000:
        raise ValueError('공용 대화 대기열 기록이 너무 많습니다.')
    queue_intent_records = []
    for intent_record_path in intent_record_paths:
        if _ATOMIC_TEMP_FILE_PATTERN.fullmatch(intent_record_path.name):
            continue
        if not _MARKER_FILE_PATTERN.fullmatch(intent_record_path.name):
            raise ValueError('공용 대화 대기열 파일 오류')
        current_intent_record = json.loads(read_bounded_gpu_observation_bytes(intent_record_path, 4096)[0])
        if (not isinstance(current_intent_record, dict)
                or set(current_intent_record) != {'version','session_id','request_id','resident_id','order_ns'}
                or type(current_intent_record['version']) is not int or current_intent_record['version'] != 1
                or current_intent_record['resident_id'] != intent_record_path.stem
                or derive_chat_resident_identifier(current_intent_record['session_id'], current_intent_record['request_id']) != intent_record_path.stem
                or type(current_intent_record['order_ns']) is not int or current_intent_record['order_ns'] <= 0):
            raise ValueError('공용 대화 대기열 기록 오류')
        queue_intent_records.append(current_intent_record)
    return queue_intent_records


def begin_chat_admission(queue_root_directory, chat_session_identifier, chat_request_identifier, queue_order_nanoseconds):
    """상주 모델 접수 직전 GPU 대기 순서에 임시 예약을 만든다."""
    if type(queue_order_nanoseconds) is not int or not 0 < queue_order_nanoseconds <= time.time_ns():
        raise ValueError('대화 접수 순서 오류')
    resident_request_identifier = derive_chat_resident_identifier(chat_session_identifier, chat_request_identifier)
    owner_process_fields = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()
    current_boot_identifier = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    current_admission_record = {'version':1, 'session_id':chat_session_identifier, 'request_id':chat_request_identifier, 'resident_id':resident_request_identifier,
              'order_ns':queue_order_nanoseconds, 'boot_id':current_boot_identifier,
              'pid':os.getpid(), 'pid_start_token':owner_process_fields[19], 'pid_namespace':os.readlink('/proc/self/ns/pid')}
    with hold_gpu_queue_lock(queue_root_directory) as queue_root_path:
        ensure_gpu_active_directory(queue_root_path)
        admission_directory_path = queue_root_path / 'chat-admissions'
        if admission_directory_path.is_symlink():
            raise ValueError('대화 접수 순서 경로 오류')
        admission_directory_path.mkdir(mode=0o700, exist_ok=True)
        admission_record_path = admission_directory_path / (resident_request_identifier + '.json')
        if admission_record_path.is_symlink():
            raise ValueError('대화 접수 순서 기록 오류')
        # GPU 잠금을 기다린 시간은 접수 보호 구간을 소모하지 않는다.
        current_admission_record['created_monotonic_ns'] = time.monotonic_ns()
        current_admission_record['created_wall_ns'] = time.time_ns()
        write_record_atomically(admission_record_path, current_admission_record)
    return resident_request_identifier


def clear_chat_admission_locked(queue_root_directory, resident_request_identifier, chat_session_identifier, queue_order_nanoseconds):
    """실제 GPU 티켓을 같은 잠금 안에서 생성한 뒤 일치하는 임시 기록만 제거한다."""
    from workflow.common.gpu_job_queue import read_bounded_gpu_observation_bytes
    admission_directory_path = Path(queue_root_directory) / 'chat-admissions'
    if admission_directory_path.is_symlink():
        raise ValueError('대화 접수 순서 경로 오류')
    admission_record_path = admission_directory_path / (resident_request_identifier + '.json')
    try:
        current_admission_record = json.loads(read_bounded_gpu_observation_bytes(admission_record_path, 4096)[0])
    except FileNotFoundError:
        return
    if not isinstance(current_admission_record, dict) or (current_admission_record.get('resident_id'),current_admission_record.get('session_id'),current_admission_record.get('order_ns')) != (resident_request_identifier,chat_session_identifier,queue_order_nanoseconds):
        raise ValueError('대화 접수와 GPU 티켓 순서가 다릅니다.')
    admission_record_path.unlink()


def has_recent_resident_progress(admission_record_value, workflow_root_directory, current_wall_nanoseconds):
    """모델 실행기 생성 파일이 최근 갱신된 동안만 짧은 순서 보호를 연장한다."""
    from workflow.common.gpu_job_queue import read_bounded_gpu_observation_bytes
    admission_created_wall = admission_record_value.get('created_wall_ns')
    if type(admission_created_wall) is not int or admission_created_wall <= 0:
        return False
    resident_root_directory = Path(workflow_root_directory) / '.local/hermes-agent/residents'
    resident_job_directory = resident_root_directory / admission_record_value['resident_id']
    try:
        if resident_root_directory.is_symlink() or resident_job_directory.is_symlink() or not resident_job_directory.is_dir():
            return False
        resident_request_path = resident_job_directory / 'request.json'
        resident_request_record = json.loads(read_bounded_gpu_observation_bytes(resident_request_path, 4096)[0])
        if (not isinstance(resident_request_record, dict) or resident_request_record.get('model_profile') != 'qwen3.8-27b'
                or resident_request_record.get('context') != {'session_id':admission_record_value['session_id']}
                or type(resident_request_record.get('queue_order_ns')) is not int
                or resident_request_record['queue_order_ns'] != admission_record_value['order_ns']):
            return False
        for progress_file_name in ('request.json', 'launch.json', 'gpu-command.json', 'execution.lock'):
            progress_file_path = resident_job_directory / progress_file_name
            try:
                progress_file_metadata = progress_file_path.lstat()
            except FileNotFoundError:
                continue
            progress_age_nanoseconds = current_wall_nanoseconds - progress_file_metadata.st_mtime_ns
            if (stat.S_ISREG(progress_file_metadata.st_mode) and progress_file_metadata.st_mtime_ns >= admission_created_wall
                    and 0 <= progress_age_nanoseconds <= _ADMISSION_LEASE_NANOSECONDS):
                return True
        return False
    except (OSError, ValueError, TypeError, KeyError):
        return False


def list_live_chat_admissions(queue_root_directory, workflow_root_directory):
    """짧은 접수 구간만 관측한다. 죽었거나 만료된 실행기의 기록은 대기를 막지 않는다."""
    from workflow.common.gpu_job_queue import gpu_ticket_execution_lock_held, inspect_gpu_ticket_executor_identity, read_bounded_gpu_observation_bytes, validate_gpu_ticket_process_identifier
    admission_directory_path = Path(queue_root_directory) / 'chat-admissions'
    if admission_directory_path.is_symlink():
        raise ValueError('대화 접수 순서 경로 오류')
    if not admission_directory_path.exists():
        return []
    if not admission_directory_path.is_dir():
        raise ValueError('대화 접수 순서 경로 오류')
    admission_record_paths = list(admission_directory_path.iterdir())
    if len(admission_record_paths) > 10000:
        raise ValueError('대화 접수 순서 기록이 너무 많습니다.')
    current_boot_identifier = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    current_monotonic_nanoseconds = time.monotonic_ns()
    current_wall_nanoseconds = time.time_ns()
    live_admission_records = []
    for admission_record_path in admission_record_paths:
        if _ATOMIC_TEMP_FILE_PATTERN.fullmatch(admission_record_path.name):
            continue
        if not _MARKER_FILE_PATTERN.fullmatch(admission_record_path.name):
            raise ValueError('대화 접수 순서 파일 오류')
        try:
            current_admission_record = json.loads(read_bounded_gpu_observation_bytes(admission_record_path, 4096)[0])
            if (not isinstance(current_admission_record, dict) or current_admission_record.get('version') != 1
                    or not isinstance(current_admission_record.get('session_id'), str) or not _SESSION_ID_PATTERN.fullmatch(current_admission_record['session_id'])
                    or not isinstance(current_admission_record.get('request_id'), str) or not _REQUEST_ID_PATTERN.fullmatch(current_admission_record['request_id'])
                    or current_admission_record.get('resident_id') != admission_record_path.stem
                    or derive_chat_resident_identifier(current_admission_record['session_id'], current_admission_record['request_id']) != admission_record_path.stem
                    or type(current_admission_record.get('order_ns')) is not int or current_admission_record['order_ns'] <= 0
                    or type(current_admission_record.get('created_monotonic_ns')) is not int):
                raise ValueError('대화 접수 순서 기록 오류')
            admission_elapsed_nanoseconds = current_monotonic_nanoseconds - current_admission_record['created_monotonic_ns']
            if current_admission_record.get('boot_id') != current_boot_identifier or admission_elapsed_nanoseconds < 0:
                continue
            if (admission_elapsed_nanoseconds > _ADMISSION_LEASE_NANOSECONDS
                    and not has_recent_resident_progress(current_admission_record, workflow_root_directory, current_wall_nanoseconds)):
                continue
            owner_process_identifier = validate_gpu_ticket_process_identifier(current_admission_record)
            try:
                os.kill(owner_process_identifier, 0)
            except ProcessLookupError:
                resident_job_directory = Path(workflow_root_directory) / '.local/hermes-agent/residents' / current_admission_record['resident_id']
                if (not has_recent_resident_progress(current_admission_record, workflow_root_directory, current_wall_nanoseconds)
                        or not gpu_ticket_execution_lock_held({'path':str(resident_job_directory)})):
                    continue
            else:
                if inspect_gpu_ticket_executor_identity(current_admission_record) != 'verified':
                    raise ValueError('대화 접수 실행기 신원 오류')
            session_record_path = Path(workflow_root_directory) / '.local/hermes-agent/sessions' / (current_admission_record['session_id'] + '.json')
            current_session_record = json.loads(read_bounded_gpu_observation_bytes(session_record_path, 16 * 1024 * 1024)[0])
            session_queue_rows = current_session_record.get('chat_queue') if isinstance(current_session_record, dict) else None
            if (not isinstance(current_session_record, dict) or current_session_record.get('version') != 1 or current_session_record.get('id') != current_admission_record['session_id']
                    or not isinstance(session_queue_rows, list) or any(not isinstance(matching_request_record, dict) for matching_request_record in session_queue_rows)):
                raise ValueError('대화 대기열 형식 오류')
            matching_request_record = next((matching_request_record for matching_request_record in session_queue_rows if matching_request_record.get('request_id') == current_admission_record['request_id']), None)
            if matching_request_record is None or matching_request_record.get('state') not in ('queued','dispatching'):
                continue
            if (matching_request_record.get('require_resident') is not True or type(matching_request_record.get('queue_order_ns')) is not int
                    or matching_request_record['queue_order_ns'] != current_admission_record['order_ns']):
                raise ValueError('대화 접수 순서가 일치하지 않습니다.')
            live_admission_records.append(current_admission_record)
            if len(live_admission_records) > 1000:
                raise ValueError('활성 대화 접수 순서 기록이 너무 많습니다.')
        except FileNotFoundError:
            continue
        except (OSError, TypeError, KeyError, IndexError, json.JSONDecodeError) as admission_record_error:
            raise ValueError('대화 접수 순서를 확인할 수 없습니다.') from admission_record_error
    return live_admission_records
