"""별도 프로세스에서 GPU 메모리와 공용 실행 잠금을 기다리는 영속 작업 대기열."""
import argparse
import errno
from datetime import datetime, timezone
import hashlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import signal
import stat
import uuid

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.queue_generation_telemetry import QueueGenerationTelemetry
from tools.review.common.gpu_memory_history import read_worker_memory, save_memory_observation, estimate_required_memory, identify_execution_command
from tools.review.common.host_memory_guard import start_animate_memory_guard, read_memory_field_kib, HOST_MEMORY_RESERVE_KIB
GPU_QUEUE_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.tmp/gpu-queue'
GPU_MEMORY_REQUIREMENTS = {'momask': 4096, 'character-animation': 6144, 'image': 6144}
GPU_MEMORY_REQUIREMENTS['wan-fun'] = 30000
GPU_MEMORY_REQUIREMENTS['wan-fun-prepare'] = 6144  # 공유 ROCm 환경 변경은 다른 대기열 작업과 겹치지 않는다.
GPU_MEMORY_REQUIREMENTS['writer-agent'] = 16384
GPU_MEMORY_REQUIREMENTS['hermes-agent'] = 32768
GPU_MEMORY_REQUIREMENTS['kimodo-cache-check'] = 1024  # 모델 적재 없이 장치와 캐시 식별자만 확인한다.
GPU_EXCLUSIVE_SERVICES = frozenset(('hermes-agent', 'wan-fun-prepare', 'management-setup', 'kimodo-cache-check'))
GPU_MEMORY_REQUIREMENTS['prompt-translation'] = 16384  # 번역 후 작가 AI 의미 검토 모델을 순차 사용한다.
GPU_MEMORY_REQUIREMENTS['flux3-evaluation'] = 36864  # 768×1152 편집 시험에서 관측한 32812 MiB 피크에 여유를 둔다.
GPU_MEMORY_REQUIREMENTS['flux-expression'] = 45056  # 768×512 표정 작업 관측 피크 39166 MiB에 여유를 둔다.
GPU_MEMORY_REQUIREMENTS['flux-image'] = 57344  # 2참조 768×1152 실험 관측 피크 51679 MiB에 여유를 둔다.
# HY-Motion의 초기 예약은 실측 전 보수적 값이며 완료 후 공용 이력의 peak로 갱신한다.
# 음악 모델의 초기 예약값. 실제 관측 피크는 공용 메모리 이력이 갱신한다.
GPU_MEMORY_REQUIREMENTS.update({'music-minimax':7000,'music-magenta':7000,'music-heartmula':20000,'sfx-dasheng-audiogen':20000})
GPU_POLL_INTERVAL = 2
HERMES_PIDFD_GROUP_FLAG = 4  # Linux PIDFD_SIGNAL_PROCESS_GROUP
# 실측 프로세스 최대 사용량과 현재 여유를 직접 비교한다.
# 고정 여유분 추가 차감은 단독 실행이 가능한 작업도 무기한 차단한다.


def read_gpu_memory():
    memory_query_result = subprocess.run(['amd-smi', 'metric', '-m', '--json'], capture_output=True, text=True, check=True, timeout=10)
    current_memory_values = json.loads(memory_query_result.stdout)['gpu_data'][0]['mem_usage']
    current_memory_domain = select_gpu_memory_domain(current_memory_values)
    current_total_memory = int(current_memory_values[f'total_{current_memory_domain}']['value'])
    current_free_memory = max(0, int(current_memory_values[f'free_{current_memory_domain}']['value']))
    return current_total_memory, current_free_memory


def select_gpu_memory_domain(current_memory_values):
    """이 호스트의 ROCm 장치 한도로 보고되는 더 큰 풀을 선택한다."""
    return 'vram' if int(current_memory_values.get('total_vram', {'value':0})['value']) > int(current_memory_values['total_gtt']['value']) else 'gtt'


def read_gpu_memory_domain():
    current_memory_result = subprocess.run(['amd-smi', 'metric', '-m', '--json'], capture_output=True, text=True, check=True, timeout=10)
    return select_gpu_memory_domain(json.loads(current_memory_result.stdout)['gpu_data'][0]['mem_usage'])


def read_host_available_memory():
    """GTT는 시스템 RAM을 사용하므로 실제 사용 가능한 RAM도 확인한다."""
    return read_memory_field_kib('/proc/meminfo', 'MemAvailable') // 1024


def calculate_gpu_pool_capacity(current_memory_domain,current_gpu_free_mib,current_host_available_mib):
    """공유 GTT 사용에도 시스템 RAM 보호 여유를 남긴다."""
    if current_memory_domain not in ('gtt','vram') or any(type(current_value) is not int or current_value<0 for current_value in (current_gpu_free_mib,current_host_available_mib)):
        raise ValueError('GPU 또는 호스트 메모리 정보 오류')
    current_host_reserve_mib=HOST_MEMORY_RESERVE_KIB//1024
    if current_memory_domain=='gtt':
        return min(current_gpu_free_mib,max(0,current_host_available_mib-current_host_reserve_mib))
    return current_gpu_free_mib if current_host_available_mib>=current_host_reserve_mib else 0


def launch_gpu_process(command_argument_values, generation_job_path, generation_service_name, **process_option_values):
    generation_job_path = Path(generation_job_path).resolve()
    generation_request_record = {'command': command_argument_values, 'service': generation_service_name}
    write_record_atomically(generation_job_path/'gpu-command.json', generation_request_record)
    write_record_atomically(generation_job_path/'status.json', {'status':'queued', 'message':'GPU 실행 대기'})
    try:
        return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--job-dir', str(generation_job_path)], **process_option_values)
    except Exception as process_launch_error:
        write_record_atomically(generation_job_path/'status.json', {'status':'failed', 'error':str(process_launch_error)})
        raise


def fingerprint_resume_job_records(current_job_directory):
    """저장 요청·상태·실행 명령이 모두 있을 때만 바이트 확인값을 만든다."""
    current_job_directory = Path(current_job_directory)
    current_fingerprint_hash = hashlib.sha256()
    for current_record_name in ('request.json','status.json','gpu-command.json'):
        current_record_path = current_job_directory / current_record_name
        if current_record_path.is_symlink():
            raise ValueError('재개 기록은 심볼릭 링크일 수 없습니다.')
        try:
            current_record_bytes = current_record_path.read_bytes()
        except FileNotFoundError as current_record_error:
            raise ValueError('검토할 재개 요청·상태·실행 명령 기록이 모두 필요합니다.') from current_record_error
        current_fingerprint_hash.update(current_record_name.encode('ascii') + b'\x00')
        current_fingerprint_hash.update(b'present\x00' + len(current_record_bytes).to_bytes(8,'big') + current_record_bytes)
    return current_fingerprint_hash.hexdigest()


def open_gpu_resume_lock(current_job_directory):
    """재개·취소 공용 잠금을 심볼릭 링크 추종 없이 연다."""
    current_lock_path=Path(current_job_directory)/'resume.lock'
    try:
        current_lock_descriptor=os.open(current_lock_path,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW,0o666)
    except OSError as current_lock_error:
        if current_lock_error.errno==errno.ELOOP:
            raise ValueError('재개 잠금 경로가 심볼릭 링크입니다.') from current_lock_error
        raise
    return os.fdopen(current_lock_descriptor,'a')


def preview_gpu_resume_records(current_job_directory,current_service_name,current_expected_command,current_validate_request):
    """공용 잠금 아래 저장 기록을 확인하며 GPU 작업을 시작하지 않는다."""
    current_job_directory=Path(current_job_directory)
    if not isinstance(current_service_name,str) or not current_service_name or not isinstance(current_expected_command,list) or not callable(current_validate_request):
        raise ValueError('재개 검토 인자 오류')
    current_resume_lock=current_job_directory/'resume.lock'
    current_execution_lock=current_job_directory/'execution.lock'
    if current_resume_lock.is_symlink() or current_execution_lock.is_symlink():
        raise ValueError('재개 잠금 경로가 올바르지 않습니다.')
    with open_gpu_resume_lock(current_job_directory) as current_resume_handle:
        fcntl.flock(current_resume_handle,fcntl.LOCK_EX)
        with current_execution_lock.open('a') as current_execution_handle:
            try:
                fcntl.flock(current_execution_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError as current_execution_error:
                raise ValueError('이전 실행이 종료되지 않았습니다.') from current_execution_error
            current_fingerprint_value=fingerprint_resume_job_records(current_job_directory)
            current_status_record=json.loads((current_job_directory/'status.json').read_text())
            if not isinstance(current_status_record,dict) or current_status_record.get('status') not in ('failed','cancelled','paused'):
                raise ValueError('일시정지·취소·실패 작업만 재개를 검토할 수 있습니다.')
            current_request_record=json.loads((current_job_directory/'request.json').read_text())
            current_validate_request(current_request_record)
            current_command_record=json.loads((current_job_directory/'gpu-command.json').read_text())
            if not isinstance(current_command_record,dict) or set(current_command_record)!={'command','service'} or current_command_record.get('service')!=current_service_name or current_command_record.get('command')!=current_expected_command:
                raise ValueError('재개 실행 명령이 선택한 서비스와 작업에 일치하지 않습니다.')
            if fingerprint_resume_job_records(current_job_directory)!=current_fingerprint_value:
                raise ValueError('재개 검토 중 작업 기록이 변경됐습니다.')
            return {'status':current_status_record['status'],'expected_resume_fingerprint':current_fingerprint_value}


def open_gpu_resume_log(current_job_directory):
    """재개 로그는 링크나 특수 파일을 열지 않는다."""
    current_log_descriptor=os.open(Path(current_job_directory)/'worker.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
    try:
        if not stat.S_ISREG(os.fstat(current_log_descriptor).st_mode):
            raise ValueError('재개 로그는 일반 파일이어야 합니다.')
        return os.fdopen(current_log_descriptor,'a')
    except BaseException:
        os.close(current_log_descriptor)
        raise


def resume_gpu_generation(generation_job_path, legacy_command_record=None, expected_resume_fingerprint=None, expected_resume_service=None, expected_resume_command=None, resume_validation_callback=None, resume_locked_preflight_callback=None):
    generation_job_path = Path(generation_job_path)
    if resume_validation_callback is not None and (not callable(resume_validation_callback) or expected_resume_fingerprint is None or expected_resume_service is None or expected_resume_command is None):
        raise ValueError('재개 추가 검증에는 작업 확인값과 서비스·실행 명령이 필요합니다.')
    if resume_locked_preflight_callback is not None and not callable(resume_locked_preflight_callback):
        raise ValueError('재개 잠금 검증 함수 오류')
    with open_gpu_resume_lock(generation_job_path) as resume_lock_handle:
        fcntl.flock(resume_lock_handle, fcntl.LOCK_EX)
        if expected_resume_fingerprint is not None:
            import re
            if not isinstance(expected_resume_fingerprint,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_resume_fingerprint) or fingerprint_resume_job_records(generation_job_path)!=expected_resume_fingerprint:
                raise ValueError('검토한 재개 작업 기록이 변경됐습니다. 다시 확인하세요.')
        generation_status_record = json.loads((generation_job_path/'status.json').read_text())
        if generation_status_record['status'] not in ('failed', 'cancelled', 'paused'):
            raise ValueError('일시정지·취소·실패 작업만 재개할 수 있습니다.')
        current_execution_path = generation_job_path / 'execution.lock'
        if current_execution_path.is_symlink():
            raise ValueError('작업 실행 잠금 경로가 심볼릭 링크입니다.')
        with current_execution_path.open('a') as current_execution_handle:
            try:
                fcntl.flock(current_execution_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as current_execution_error:
                raise ValueError('이전 실행의 최종 기록 저장 중입니다. 종료 후 다시 재개하세요.') from current_execution_error
            if expected_resume_fingerprint is not None and fingerprint_resume_job_records(generation_job_path)!=expected_resume_fingerprint:
                raise ValueError('검토한 재개 작업 기록이 변경됐습니다. 다시 확인하세요.')
            generation_status_record = json.loads((generation_job_path/'status.json').read_text())
            if generation_status_record['status'] not in ('failed', 'cancelled', 'paused'):
                raise ValueError('일시정지·취소·실패 작업만 재개할 수 있습니다.')
            if resume_validation_callback is not None:
                resume_validation_callback(generation_job_path)
                if fingerprint_resume_job_records(generation_job_path)!=expected_resume_fingerprint:
                    raise ValueError('검토한 재개 작업 기록이 변경됐습니다. 다시 확인하세요.')
            if resume_locked_preflight_callback is not None:
                resume_locked_preflight_callback(generation_job_path)
        # 새 실행기가 같은 잠금을 획득할 수 있도록 접수 전에 확인 잠금을 해제한다.
        current_command_path = generation_job_path / 'gpu-command.json'
        try:
            current_command_descriptor = os.open(current_command_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            generation_command_record = legacy_command_record
        except OSError as current_command_error:
            raise ValueError('재개 실행 명령 기록을 확인할 수 없습니다.') from current_command_error
        else:
            with os.fdopen(current_command_descriptor, 'rb') as current_command_stream:
                current_command_stat = os.fstat(current_command_stream.fileno())
                if not stat.S_ISREG(current_command_stat.st_mode) or current_command_stat.st_size > 1024 * 1024:
                    raise ValueError('재개 실행 명령 기록은 크기가 제한된 일반 파일이어야 합니다.')
                current_command_bytes = current_command_stream.read(1024 * 1024 + 1)
                if len(current_command_bytes) > 1024 * 1024:
                    raise ValueError('재개 실행 명령 기록은 크기가 제한된 일반 파일이어야 합니다.')
                generation_command_record = json.loads(current_command_bytes)
        if generation_command_record is None:
            raise ValueError('재개할 작업의 실행 명령 기록이 없습니다.')
        if not isinstance(generation_command_record, dict) or set(generation_command_record) != {'command', 'service'}:
            raise ValueError('재개 실행 명령 기록의 필드가 올바르지 않습니다.')
        current_command_arguments = generation_command_record['command']
        current_service_name = generation_command_record['service']
        if not isinstance(current_command_arguments, list) or not current_command_arguments or any(not isinstance(current_argument_value, str) or '\x00' in current_argument_value for current_argument_value in current_command_arguments) or not current_command_arguments[0].strip():
            raise ValueError('재개 실행 명령은 실행 파일을 포함한 문자열 목록이어야 합니다.')
        if not isinstance(current_service_name, str) or not current_service_name.strip():
            raise ValueError('재개 실행 명령의 서비스 이름이 올바르지 않습니다.')
        if expected_resume_service is not None and (not isinstance(expected_resume_service,str) or current_service_name != expected_resume_service):
            raise ValueError('재개 실행 명령의 서비스가 선택한 서비스와 다릅니다.')
        if expected_resume_command is not None and (not isinstance(expected_resume_command,list) or current_command_arguments != expected_resume_command):
            raise ValueError('재개 실행 명령이 검증된 작업 명령과 다릅니다.')
        # 로그를 열 수 없는 경우 기존 종료 상태와 요청 표시를 유지한다.
        with open_gpu_resume_log(generation_job_path) as generation_log_handle:
            (generation_job_path/'cancel.request').unlink(missing_ok=True)
            (generation_job_path/'pause.request').unlink(missing_ok=True)
            (generation_job_path/'stage-pause.json').unlink(missing_ok=True)
            write_record_atomically(generation_job_path/'status.json', {'status':'queued', 'message':'GPU 실행 대기'})
            try:
                launch_gpu_process(generation_command_record['command'], generation_job_path, generation_command_record['service'], stdout=generation_log_handle, stderr=subprocess.STDOUT, start_new_session=True)
            except (OSError,ValueError) as current_launch_error:
                write_record_atomically(generation_job_path/'status.json', {'status':'failed', 'error':str(current_launch_error)})
                raise
    return {'id':generation_job_path.name, 'status':'queued'}


def cancel_gpu_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    with open_gpu_resume_lock(generation_job_path) as resume_lock_handle:
        fcntl.flock(resume_lock_handle, fcntl.LOCK_EX)
        generation_status_record = json.loads((generation_job_path/'status.json').read_text())
        if generation_status_record['status'] not in ('running', 'queued', 'paused'):
            raise ValueError('대기·실행·검수 대기 작업만 중지할 수 있습니다.')
        (generation_job_path/'cancel.request').touch()
        if generation_status_record['status'] == 'paused':
            generation_status_record = {'status':'cancelled','message':'사용자가 중지했습니다. 완료한 단계 결과는 유지됩니다.'}
            write_record_atomically(generation_job_path/'status.json', generation_status_record)
    return {'status':generation_status_record['status'], 'cancel_requested':True}


def list_gpu_queue_record_paths(current_directory_path):
    """대기·예약 목록 확인 오류를 빈 목록으로 바꾸지 않는다."""
    return [current_record_path for current_record_path in current_directory_path.iterdir() if current_record_path.name.endswith('.json')]


GPU_OBSERVATION_MAXIMUM_FILES = 1000
GPU_OBSERVATION_MAXIMUM_ENTRIES = 5000
GPU_OBSERVATION_MAXIMUM_BYTES = 1048576


def read_bounded_gpu_observation_bytes(current_observation_path,current_maximum_bytes):
    """관측 전용: 일반 파일을 제한해 읽고 조회 중 변경을 거부한다."""
    current_descriptor_value=os.open(current_observation_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(current_descriptor_value,'rb') as current_file_handle:
        current_before_stat=os.fstat(current_file_handle.fileno())
        if not stat.S_ISREG(current_before_stat.st_mode):raise ValueError('GPU 관측 파일 형식 오류')
        current_file_bytes=current_file_handle.read(current_maximum_bytes+1)
        current_after_stat=os.fstat(current_file_handle.fileno())
    if len(current_file_bytes)>current_maximum_bytes or (current_before_stat.st_dev,current_before_stat.st_ino,current_before_stat.st_size,current_before_stat.st_mtime_ns)!=(current_after_stat.st_dev,current_after_stat.st_ino,current_after_stat.st_size,current_after_stat.st_mtime_ns):
        raise ValueError('GPU 관측 파일 크기 또는 변경 오류')
    return current_file_bytes,current_after_stat


def read_gpu_priority_order(observation_limits=False):
    """기록이 없는 경우만 기본 순서를 사용하고 읽기 실패는 전달한다."""
    current_priority_path = GPU_QUEUE_DIRECTORY / 'priority-order'
    if current_priority_path.is_symlink():raise ValueError('GPU 우선순위 기록 경로 오류')
    try:
        current_priority_values=json.loads(read_bounded_gpu_observation_bytes(current_priority_path,GPU_OBSERVATION_MAXIMUM_BYTES)[0]) if observation_limits else json.loads(current_priority_path.read_text())
    except FileNotFoundError:
        current_priority_values={}
    if not isinstance(current_priority_values,dict) or any(not isinstance(current_key,str) or type(current_value) is not int for current_key,current_value in current_priority_values.items()):
        raise ValueError('GPU 우선순위 기록 형식 오류')
    return current_priority_values


def read_priority_tickets(observation_limits=False):
    """티켓 경로는 유지하고 영속 우선순위로 정렬한다."""
    current_priority_values=read_gpu_priority_order(observation_limits=True) if observation_limits else read_gpu_priority_order()
    try:
        if observation_limits:
            current_ticket_paths=[]
            with os.scandir(GPU_QUEUE_DIRECTORY) as current_directory_entries:
                for current_entry_count,current_directory_entry in enumerate(current_directory_entries,start=1):
                    if current_entry_count>GPU_OBSERVATION_MAXIMUM_ENTRIES:raise ValueError('GPU 대기 경로 항목 수 초과')
                    if current_directory_entry.name.endswith('.json'):
                        current_ticket_paths.append(GPU_QUEUE_DIRECTORY/current_directory_entry.name)
                        if len(current_ticket_paths)>GPU_OBSERVATION_MAXIMUM_FILES:raise ValueError('GPU 대기 기록 수 초과')
        else:
            current_ticket_paths=list_gpu_queue_record_paths(GPU_QUEUE_DIRECTORY)
    except FileNotFoundError:
        return []
    return sorted(current_ticket_paths, key=lambda current_ticket_path: (current_priority_values.get(current_ticket_path.name, 0), current_ticket_path.name))



def validate_gpu_ticket_process_identifier(current_ticket_record):
    """시그널 0 조회 전 양의 정수 PID만 허용한다."""
    if not isinstance(current_ticket_record,dict) or type(current_ticket_record.get('pid')) is not int or not 0<current_ticket_record['pid']<=2147483647:
        raise ValueError('GPU 대기 실행기 PID 오류')
    return current_ticket_record['pid']


def inspect_gpu_ticket_executor_identity(current_ticket_record):
    """시작 식별값이 있는 티켓은 PID 재사용을 거부하고 구버전은 미확인으로 둔다."""
    current_process_identifier=validate_gpu_ticket_process_identifier(current_ticket_record)
    if 'pid_start_token' not in current_ticket_record:
        if 'boot_id' in current_ticket_record:raise ValueError('GPU 대기 실행기 식별 정보 오류')
        return 'unverified'
    current_start_token=current_ticket_record['pid_start_token']
    if not isinstance(current_start_token,str) or not current_start_token.isascii() or not current_start_token.isdigit():
        raise ValueError('GPU 대기 실행기 식별 정보 오류')
    current_boot_identifier=current_ticket_record.get('boot_id')
    if 'boot_id' in current_ticket_record and current_boot_identifier is None:
        raise ValueError('GPU 대기 실행기 부팅 식별 정보 오류')
    try:
        current_process_fields=Path(f'/proc/{current_process_identifier}/stat').read_text().rpartition(') ')[2].split()
        if current_process_fields[0] in ('Z','X') or current_process_fields[19]!=current_start_token:
            raise ValueError('GPU 대기 실행기 신원이 일치하지 않습니다.')
    except (OSError,IndexError) as current_identity_error:
        raise ValueError('GPU 대기 실행기 신원을 확인할 수 없습니다.') from current_identity_error
    if current_boot_identifier is None:return 'unverified'
    try:
        if not isinstance(current_boot_identifier,str) or str(uuid.UUID(current_boot_identifier))!=current_boot_identifier:
            raise ValueError('GPU 대기 실행기 부팅 식별 정보 오류')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip()!=current_boot_identifier:
            raise ValueError('GPU 대기 실행기 부팅 신원이 일치하지 않습니다.')
    except OSError as current_boot_error:
        raise ValueError('GPU 대기 실행기 부팅 신원을 확인할 수 없습니다.') from current_boot_error
    return 'verified'


def fingerprint_gpu_queue_ticket(current_ticket_path,observation_limits=False):
    """티켓 교체를 감지할 불투명 식별자를 만들며 경로 원문은 반환하지 않는다."""
    current_ticket_path=Path(current_ticket_path)
    if current_ticket_path.is_symlink() or not current_ticket_path.is_file():
        raise ValueError('대기 티켓을 확인할 수 없습니다.')
    if observation_limits:
        current_ticket_bytes,current_after_stat=read_bounded_gpu_observation_bytes(current_ticket_path,65536)
        current_before_stat=current_after_stat
    else:
        with current_ticket_path.open('rb') as current_ticket_stream:
            current_before_stat=os.fstat(current_ticket_stream.fileno())
            current_ticket_bytes=current_ticket_stream.read(65537)
            current_after_stat=os.fstat(current_ticket_stream.fileno())
    if len(current_ticket_bytes)>65536 or (current_before_stat.st_dev,current_before_stat.st_ino,current_before_stat.st_size,current_before_stat.st_mtime_ns)!=(current_after_stat.st_dev,current_after_stat.st_ino,current_after_stat.st_size,current_after_stat.st_mtime_ns):
        raise ValueError('대기 티켓이 변경됐거나 크기가 너무 큽니다.')
    current_identity_text=f'{current_ticket_path.name}:{current_after_stat.st_dev}:{current_after_stat.st_ino}:{current_after_stat.st_size}:{current_after_stat.st_mtime_ns}:'
    return hashlib.sha256(current_identity_text.encode('utf-8')+current_ticket_bytes).hexdigest()


def is_gpu_control_requested(current_control_path):
    """신호 파일이 실제로 없을 때만 요청이 없다고 판단한다."""
    try:
        current_control_path.lstat()
    except FileNotFoundError:
        return False
    return True


def prioritize_waiting_generation(current_job_identifier,current_expected_service=None,current_expected_ticket_revision=None):
    """실행 예약과 같은 잠금으로 대기 작업만 맨 앞으로 옮긴다."""
    if not isinstance(current_job_identifier, str) or not current_job_identifier or Path(current_job_identifier).name != current_job_identifier:
        raise ValueError('생성 ID 형식 오류')
    GPU_QUEUE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with (GPU_QUEUE_DIRECTORY / 'execution.lock').open('a') as current_queue_lock:
        fcntl.flock(current_queue_lock, fcntl.LOCK_EX)
        current_matching_tickets = []
        for current_ticket_path in read_priority_tickets():
            current_ticket_record = json.loads(current_ticket_path.read_text())
            current_job_directory = Path(current_ticket_record['path'])
            if current_job_directory.name != current_job_identifier:
                continue
            if json.loads((current_job_directory / 'status.json').read_text())['status'] != 'queued' or is_gpu_control_requested(current_job_directory / 'cancel.request') or is_gpu_control_requested(current_job_directory / 'pause.request'):
                raise ValueError('중지 요청이 없는 GPU 대기 작업만 우선 실행할 수 있습니다.')
            os.kill(validate_gpu_ticket_process_identifier(current_ticket_record), 0)
            inspect_gpu_ticket_executor_identity(current_ticket_record)
            current_matching_tickets.append((current_ticket_path,current_job_directory))
        if len(current_matching_tickets) != 1:
            raise ValueError('유일한 대기 티켓을 찾을 수 없습니다. 실행이 시작됐거나 대기 등록 중입니다. 상태를 갱신하세요.')
        current_ticket_path,current_job_directory=current_matching_tickets[0]
        if current_expected_ticket_revision is not None:
            import re
            if not isinstance(current_expected_ticket_revision,str) or not re.fullmatch(r'[a-f0-9]{64}',current_expected_ticket_revision) or fingerprint_gpu_queue_ticket(current_ticket_path)!=current_expected_ticket_revision:
                raise ValueError('검토한 대기 티켓이 변경됐습니다. 다시 확인하세요.')
        if current_expected_service is not None:
            if not isinstance(current_expected_service,str) or not current_expected_service:
                raise ValueError('요청 서비스 확인 필요')
            current_command_path=current_job_directory/'gpu-command.json'
            if current_command_path.is_symlink() or not current_command_path.is_file():
                raise ValueError('대기 작업의 서비스 기록을 확인할 수 없습니다.')
            current_command_record=json.loads(current_command_path.read_text())
            current_queue_service=current_command_record.get('service') if isinstance(current_command_record,dict) else None
            if current_queue_service in ('image','flux-image'):
                current_source_service=identify_gpu_queue_source(current_job_directory,current_queue_service)
            elif is_dedicated_gpu_source_verifiable(current_queue_service):
                current_source_service=identify_dedicated_gpu_reservation_source(str(current_job_directory),current_queue_service)
            else:
                current_source_service='wan22-fun-control' if current_queue_service=='wan-fun' else current_queue_service
            if current_source_service!=current_expected_service:
                raise ValueError('요청 서비스와 대기 작업의 소유 서비스가 일치하지 않습니다.')
        current_priority_path = GPU_QUEUE_DIRECTORY / 'priority-order'
        current_priority_values = read_gpu_priority_order()
        current_priority_values[current_ticket_path.name] = min([0, *current_priority_values.values()]) - 1
        write_record_atomically(current_priority_path, current_priority_values)
        return {'id': current_job_identifier, 'status': 'queued', 'queue_position': 1, 'message': '대기열 맨 앞으로 이동했습니다. 실행 중 작업은 유지하며 GPU 메모리가 확보되면 실행합니다.'}


def is_hermes_status_query(waiting_job_directory):
    """명시적인 단일 조회 지시만 다른 생성 작업과 함께 실행한다."""
    import re
    try:
        request_record = json.loads((waiting_job_directory / 'request.json').read_text())
        if not isinstance(request_record, dict) or request_record.get('verification_modules') != []:
            return False
        prompt = request_record.get('prompt')
        if not isinstance(prompt, str):
            return False
        return re.fullmatch(
            r'(?:사용할 도구: [^\r\n]+ \([a-z0-9-]+\)\n)?'
            r'(?:(?:GPU|모델|작업|다운로드|대기열|생성)\s*)?(?:상태|이력|대기열)\s*(?:조회|확인)(?:해\s*줘|해주세요)?[.!?]?',
            prompt.strip(), re.IGNORECASE,
        ) is not None
    except (OSError, ValueError):
        return False


def select_runnable_ticket(available_memory_mib, current_memory_domain=None, active_service_names=()):
    """잠금 안에서 접수 순서대로 확인해 메모리가 맞는 첫 작업을 선택한다."""
    if GPU_EXCLUSIVE_SERVICES.intersection(active_service_names) or 'unreadable' in active_service_names:
        return None
    try:
        current_waiting_tickets=read_priority_tickets()
    except (OSError,ValueError,TypeError,AttributeError):
        return None
    for waiting_ticket_path in current_waiting_tickets:
        try:
            waiting_ticket_record = json.loads(waiting_ticket_path.read_text())
            try:
                current_ticket_pid=validate_gpu_ticket_process_identifier(waiting_ticket_record)
                os.kill(current_ticket_pid, 0)
                inspect_gpu_ticket_executor_identity(waiting_ticket_record)
            except ValueError:
                return None
            waiting_job_directory = Path(waiting_ticket_record['path'])
            if is_gpu_control_requested(waiting_job_directory/'cancel.request') or is_gpu_control_requested(waiting_job_directory/'pause.request'):
                continue
            waiting_command_record = json.loads((waiting_job_directory/'gpu-command.json').read_text())
        except FileNotFoundError:
            try:
                waiting_ticket_path.lstat()
            except FileNotFoundError:
                continue
            except OSError:
                return None
            return None
        except ProcessLookupError:
            continue
        except (OSError,ValueError,TypeError,KeyError):
            return None
        if not isinstance(waiting_command_record,dict) or not isinstance(waiting_command_record.get('service'),str) or waiting_command_record['service'] not in GPU_MEMORY_REQUIREMENTS or not isinstance(waiting_command_record.get('command'),list):
            return None
        if waiting_command_record['service'] in GPU_EXCLUSIVE_SERVICES and active_service_names:
            if waiting_command_record['service'] != 'hermes-agent' or not is_hermes_status_query(waiting_job_directory):
                continue
        waiting_memory_estimate = estimate_required_memory(
            waiting_command_record['service'], GPU_MEMORY_REQUIREMENTS[waiting_command_record['service']],
            identify_execution_command(waiting_command_record['command'], waiting_job_directory, current_memory_domain))
        if waiting_memory_estimate['required_memory_mib'] <= available_memory_mib:
            return waiting_ticket_path
    return None


def calculate_queue_revision():
    """실행기·메모리 추정·호스트 보호 기준의 변경을 감지한다."""
    source_file_paths = [Path(__file__), Path(__file__).with_name('gpu_memory_history.py'), Path(__file__).with_name('host_memory_guard.py')]
    return hashlib.sha256(b''.join(source_file_path.read_bytes() for source_file_path in source_file_paths)).hexdigest()


def reload_waiting_executor(queue_ticket_path, initial_source_revision):
    """대기 중에만 동일 PID로 교체하여 부모 감시와 접수 순서를 유지한다."""
    if calculate_queue_revision() == initial_source_revision:
        return
    replacement_environment_values = dict(os.environ, SLIME_GPU_QUEUE_TICKET=str(queue_ticket_path.resolve()))
    os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], replacement_environment_values)


def stop_hermes_worker_process_group(worker_process_identifier, worker_pid_descriptor):
    """모델 서버와 격리 프로세스가 사라질 때까지 GPU 예약을 유지한다."""
    try:
        signal.pidfd_send_signal(worker_pid_descriptor, signal.SIGKILL, None, HERMES_PIDFD_GROUP_FLAG)
    except ProcessLookupError:
        # 리더가 종료됐더라도 같은 그룹의 자식이 남았는지 확인한다.
        pass
    while True:
        remaining_group_processes = []
        for current_process_path in Path('/proc').glob('[0-9]*/stat'):
            try:
                current_stat_fields = current_process_path.read_text().rpartition(') ')[2].split()
                if int(current_stat_fields[2]) == worker_process_identifier and current_stat_fields[0] not in ('Z', 'X'):
                    remaining_group_processes.append(current_process_path)
            except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
                continue
        if not remaining_group_processes:
            return
        time.sleep(.1)


def open_verified_hermes_process_group(reservation_record_value):
    """시작 시각과 임의 토큰이 일치하는 리더의 안정적인 PID 핸들을 연다."""
    worker_group_identifier = reservation_record_value.get('worker_pgid')
    worker_start_token = reservation_record_value.get('worker_start_token')
    worker_process_token = reservation_record_value.get('worker_process_token')
    if type(worker_group_identifier) is not int or not 1<worker_group_identifier<=2147483647 or not isinstance(worker_start_token, str) or not isinstance(worker_process_token, str) or len(worker_process_token) != 32 or any(worker_hex_digit not in '0123456789abcdef' for worker_hex_digit in worker_process_token):
        return None
    try:
        worker_pid_descriptor = os.pidfd_open(worker_group_identifier)
    except (OSError, AttributeError):
        return None
    try:
        worker_process_path = Path(f'/proc/{worker_group_identifier}')
        worker_stat_fields = (worker_process_path / 'stat').read_text().rpartition(') ')[2].split()
        worker_environment_values = (worker_process_path / 'environ').read_bytes().split(b'\0')
        worker_expected_entry = ('SLIME_HERMES_PROCESS_TOKEN=' + worker_process_token).encode('ascii')
        if worker_stat_fields[0] in ('Z', 'X') or worker_stat_fields[19] != worker_start_token or int(worker_stat_fields[2]) != worker_group_identifier or int(worker_stat_fields[3]) != worker_group_identifier or worker_expected_entry not in worker_environment_values:
            os.close(worker_pid_descriptor)
            return None
        return worker_pid_descriptor
    except (OSError, ValueError, IndexError):
        os.close(worker_pid_descriptor)
        return None


def recover_stale_hermes_reservation(reservation_record_value):
    """실행기가 죽은 Hermes 예약은 하위 그룹 종료를 확인한 뒤에만 회수한다."""
    if reservation_record_value.get('cleanup_unverified') is True:
        # 작업 그룹 종료를 확인하지 못한 예약은 운영자가 확인할 때까지 보존한다.
        return False
    if reservation_record_value.get('service') != 'hermes-agent':
        # 실행기 종료만으로 다른 서비스의 하위 GPU 프로세스 종료를 입증할 수 없다.
        return False
    worker_pid_descriptor = open_verified_hermes_process_group(reservation_record_value)
    if worker_pid_descriptor is None:
        return False
    try:
        stop_hermes_worker_process_group(reservation_record_value['worker_pgid'], worker_pid_descriptor)
    except OSError:
        return False
    finally:
        os.close(worker_pid_descriptor)
    worker_job_value = reservation_record_value.get('path')
    if isinstance(worker_job_value, str):
        worker_job_path = Path(worker_job_value)
        worker_status_path = worker_job_path / 'status.json'
        if worker_job_path.resolve().is_relative_to(WORKFLOW_ROOT_DIRECTORY / '.tmp/test') and not worker_status_path.is_symlink() and worker_status_path.is_file():
            worker_status_record = json.loads(worker_status_path.read_text())
            if worker_status_record.get('status') in ('queued', 'running'):
                write_record_atomically(worker_status_path, {'status':'failed', 'error':'GPU 대기열 실행기가 종료되어 Hermes 하위 프로세스를 정리했습니다.'})
    return True


def is_gpu_queue_executor_alive(queue_process_identifier, queue_start_token=None):
    """종료된 좀비와 PID 재사용을 살아 있는 실행기로 간주하지 않는다."""
    if type(queue_process_identifier) is not int or not 0<queue_process_identifier<=2147483647:
        raise ValueError('GPU 예약 실행기 PID 오류')
    try:
        os.kill(queue_process_identifier, 0)
    except ProcessLookupError:
        return False
    try:
        queue_stat_fields = Path(f'/proc/{queue_process_identifier}/stat').read_text().rpartition(') ')[2].split()
        return queue_stat_fields[0] not in ('Z', 'X') and (queue_start_token is None or queue_stat_fields[19] == queue_start_token)
    except FileNotFoundError:
        return False
    except (OSError, IndexError):
        return True


def execute_queued_generation(generation_job_path):
    """최종 관측 기록까지 삭제와 겹치지 않도록 실행 수명 잠금을 유지한다."""
    current_execution_lock = Path(generation_job_path) / 'execution.lock'
    if current_execution_lock.is_symlink():
        raise ValueError('작업 실행 잠금 경로가 심볼릭 링크입니다.')
    with current_execution_lock.open('a') as current_execution_handle:
        fcntl.flock(current_execution_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return execute_locked_generation(generation_job_path)


def execute_locked_generation(generation_job_path):
    generation_job_path = Path(generation_job_path)
    generation_command_record = json.loads((generation_job_path/'gpu-command.json').read_text())
    GPU_QUEUE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    initial_source_revision = calculate_queue_revision()
    inherited_ticket_value = os.environ.pop('SLIME_GPU_QUEUE_TICKET', None)
    queue_ticket_path = Path(inherited_ticket_value) if inherited_ticket_value else GPU_QUEUE_DIRECTORY/f'{time.time_ns():020d}-{os.getpid()}.json'
    if inherited_ticket_value:
        inherited_ticket_record = json.loads(queue_ticket_path.read_text())
        if (queue_ticket_path.resolve().parent != GPU_QUEUE_DIRECTORY.resolve() or not isinstance(inherited_ticket_record,dict)
                or set(inherited_ticket_record)-{'pid','path','pid_start_token','boot_id'} or inherited_ticket_record.get('pid')!=os.getpid()
                or inherited_ticket_record.get('path')!=str(generation_job_path)):
            raise ValueError('대기열 갱신 티켓이 현재 작업과 일치하지 않습니다.')
        inspect_gpu_ticket_executor_identity(inherited_ticket_record)
    current_ticket_record={'pid':os.getpid(), 'path':str(generation_job_path)}
    try:
        current_ticket_start=Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()[19]
        if current_ticket_start.isascii() and current_ticket_start.isdigit():current_ticket_record['pid_start_token']=current_ticket_start
    except (OSError,IndexError):
        pass
    if 'pid_start_token' in current_ticket_record:
        try:
            current_boot_identifier=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
            if str(uuid.UUID(current_boot_identifier))==current_boot_identifier:current_ticket_record['boot_id']=current_boot_identifier
        except (OSError,ValueError):
            pass
    write_record_atomically(queue_ticket_path,current_ticket_record)
    active_reservation_directory = GPU_QUEUE_DIRECTORY/'active'
    active_reservation_directory.mkdir(exist_ok=True)
    active_reservation_path = active_reservation_directory/queue_ticket_path.name
    peak_memory_mib = 0
    memory_sample_count = 0
    memory_measurement_error = None
    last_memory_sample_time = 0
    generation_worker_process = None
    hermes_worker_pid_descriptor = None
    hermes_group_signal_supported = False
    current_writer_cleanup_unverified = False
    current_memory_guard = None
    current_telemetry_recorder = None
    current_memory_domain = None
    signal.signal(signal.SIGTERM, lambda *_: (generation_job_path/"cancel.request").touch())
    try:
        with (GPU_QUEUE_DIRECTORY/'execution.lock').open('a') as gpu_execution_handle:
            while True:
                if (generation_job_path/'cancel.request').exists():
                    write_record_atomically(generation_job_path/'status.json', {'status':'cancelled'})
                    return 0
                if (generation_job_path/'pause.request').exists():
                    write_record_atomically(generation_job_path/'status.json', {'status':'paused','message':'대기 중 일시정지'})
                    return 0
                reload_waiting_executor(queue_ticket_path, initial_source_revision)
                # 죽은 대기 프로세스의 표만 제거한다. 생성 기록은 보존한다.
                for previous_ticket_path in GPU_QUEUE_DIRECTORY.glob('*.json'):
                    try:
                        current_previous_ticket=json.loads(previous_ticket_path.read_text())
                        os.kill(validate_gpu_ticket_process_identifier(current_previous_ticket),0)
                    except ProcessLookupError: previous_ticket_path.unlink(missing_ok=True)
                    except (OSError,ValueError,TypeError,KeyError): pass
                try:
                    queued_ticket_values = read_priority_tickets()
                    queue_position_value = queued_ticket_values.index(queue_ticket_path)+1
                except (OSError,ValueError,TypeError,AttributeError):
                    write_record_atomically(generation_job_path/'status.json',{'status':'queued','message':'GPU 대기열 순서를 확인할 수 없어 대기 중입니다. 기록을 확인하세요.'})
                    time.sleep(GPU_POLL_INTERVAL)
                    continue
                current_memory_domain = read_gpu_memory_domain()
                memory_total_value, memory_free_value = read_gpu_memory()
                memory_estimate_record = estimate_required_memory(generation_command_record['service'], GPU_MEMORY_REQUIREMENTS[generation_command_record['service']], identify_execution_command(generation_command_record['command'], generation_job_path, current_memory_domain))
                required_memory_value = memory_estimate_record['required_memory_mib']
                if memory_total_value < required_memory_value:
                    raise ValueError(f'GPU 전체 메모리 {memory_total_value} MiB: 요구량 {required_memory_value} MiB보다 작습니다.')
                execution_lock_acquired = False
                available_memory_value = 0
                reserved_memory_value = 0
                try:
                    fcntl.flock(gpu_execution_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    execution_lock_acquired = True
                except BlockingIOError:
                    pass
                if execution_lock_acquired:
                    try:
                        active_service_names = []
                        try:
                            current_reservation_paths=list_gpu_queue_record_paths(active_reservation_directory)
                        except OSError:
                            active_service_names.append('unreadable')
                            current_reservation_paths=[]
                        for reservation_path in current_reservation_paths:
                            try:
                                if reservation_path.is_symlink():raise ValueError('예약 경로 오류')
                                reservation_record = json.loads(reservation_path.read_text())
                                if (not isinstance(reservation_record,dict) or type(reservation_record.get('pid')) is not int or not 0<reservation_record['pid']<=2147483647
                                        or type(reservation_record.get('required_memory_mib')) is not int or reservation_record['required_memory_mib']<0
                                        or ('path' in reservation_record and not isinstance(reservation_record['path'],str))
                                        or ('service' in reservation_record and not isinstance(reservation_record['service'],str))
                                        or ('pid_start_token' in reservation_record and (not isinstance(reservation_record['pid_start_token'],str) or not reservation_record['pid_start_token'].isascii() or not reservation_record['pid_start_token'].isdigit()))):
                                    raise ValueError('GPU 예약 형식 오류')
                            except FileNotFoundError:
                                continue
                            except (OSError, ValueError, TypeError):
                                active_service_names.append('unreadable')
                                continue
                            try:
                                current_reservation_alive=is_gpu_queue_executor_alive(reservation_record['pid'], reservation_record.get('pid_start_token'))
                                if not current_reservation_alive:
                                    if not recover_stale_hermes_reservation(reservation_record):
                                        active_service_names.append('unreadable')
                                        continue
                                    reservation_path.unlink(missing_ok=True)
                                    continue
                            except (OSError,ValueError,TypeError,KeyError):
                                active_service_names.append('unreadable')
                                continue
                            # 구형 실행기의 고정 예약도 완료된 동일 명령 측정값으로 갱신한다.
                            reservation_job_directory = Path(reservation_record['path']) if 'path' in reservation_record else None
                            if reservation_job_directory and (reservation_job_directory/'gpu-command.json').exists():
                                try:
                                    reservation_command_record = json.loads((reservation_job_directory/'gpu-command.json').read_text())
                                    reservation_memory_estimate = estimate_required_memory(reservation_command_record['service'], GPU_MEMORY_REQUIREMENTS[reservation_command_record['service']], identify_execution_command(reservation_command_record['command'], reservation_job_directory, current_memory_domain))
                                    if reservation_memory_estimate['samples']:
                                        reservation_record['required_memory_mib'] = reservation_memory_estimate['required_memory_mib']
                                        write_record_atomically(reservation_path, reservation_record)
                                except (OSError,ValueError,TypeError,KeyError,AttributeError):
                                    active_service_names.append('unreadable')
                                    continue
                            else:
                                reservation_command_record = {}
                            active_service_names.append(reservation_record.get('service') or reservation_command_record.get('service') or 'unknown')
                            # 실측 여유에는 이미 사용 중인 메모리가 반영되어 있다.
                            try:
                                measured_reservation_mib = read_worker_memory(reservation_record['pid'], current_memory_domain=current_memory_domain)
                            except (OSError, ValueError, subprocess.SubprocessError):
                                measured_reservation_mib = 0
                            reserved_memory_value += max(0, reservation_record['required_memory_mib']-measured_reservation_mib)
                        # 아직 사용하지 않은 예약분만 차감해 모델 로딩 여유를 확보한다.
                        memory_total_value, memory_free_value = read_gpu_memory()
                        host_available_memory = read_host_available_memory()
                        current_pool_available = calculate_gpu_pool_capacity(current_memory_domain,memory_free_value,host_available_memory)
                        available_memory_value = max(0, current_pool_available-reserved_memory_value)
                        if select_runnable_ticket(available_memory_value, current_memory_domain, active_service_names) == queue_ticket_path:
                            current_queue_stat = Path(f'/proc/{os.getpid()}/stat').read_text().rpartition(') ')[2].split()
                            current_reservation_record={'pid':os.getpid(), 'pid_start_token':current_queue_stat[19], 'path':str(generation_job_path), 'service':generation_command_record['service'], 'required_memory_mib':required_memory_value}
                            if 'boot_id' in current_ticket_record:current_reservation_record['boot_id']=current_ticket_record['boot_id']
                            write_record_atomically(active_reservation_path,current_reservation_record)
                            queue_ticket_path.unlink(missing_ok=True)
                            break
                    finally:
                        fcntl.flock(gpu_execution_handle, fcntl.LOCK_UN)
                queue_status_record = {'status':'queued', 'queue_position':queue_position_value, 'memory_domain':current_memory_domain, 'free_memory_mib':memory_free_value, 'host_available_memory_mib':read_host_available_memory(), 'required_memory_mib':required_memory_value, 'reserved_memory_mib':reserved_memory_value, 'available_memory_mib':available_memory_value, 'memory_estimate':memory_estimate_record, 'message':'GPU 또는 시스템 메모리 여유 또는 실행 가능한 앞선 작업 대기'}
                write_record_atomically(generation_job_path/'status.json', queue_status_record)
                print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/gpu-queue/wait {queue_status_record}', flush=True)
                time.sleep(GPU_POLL_INTERVAL)
            queue_ticket_path.unlink(missing_ok=True)
            current_telemetry_recorder = QueueGenerationTelemetry(generation_job_path, identify_execution_command(generation_command_record['command'], generation_job_path))
            current_telemetry_recorder.capture_generation_memory()
            current_telemetry_recorder.save_generation_metrics()
            write_record_atomically(generation_job_path/'status.json', {'status':'running', 'memory_estimate':memory_estimate_record})
            current_telemetry_recorder.start_generation_telemetry()
            worker_process_token = uuid.uuid4().hex
            worker_environment_values = dict(os.environ, SLIME_GPU_RESERVATION_PATH=str(active_reservation_path.resolve()))
            if worker_process_token is not None:
                worker_environment_values['SLIME_HERMES_PROCESS_TOKEN'] = worker_process_token
            generation_worker_process = subprocess.Popen(generation_command_record['command'], start_new_session=True, env=worker_environment_values)
            if generation_command_record['service'] == 'hermes-agent':
                hermes_worker_pid_descriptor = os.pidfd_open(generation_worker_process.pid)
                signal.pidfd_send_signal(hermes_worker_pid_descriptor, 0, None, HERMES_PIDFD_GROUP_FLAG)
                hermes_group_signal_supported = True
                worker_stat_fields = Path(f'/proc/{generation_worker_process.pid}/stat').read_text().rpartition(') ')[2].split()
                fcntl.flock(gpu_execution_handle, fcntl.LOCK_EX)
                try:
                    current_reservation_record = json.loads(active_reservation_path.read_text())
                    current_reservation_record['worker_pgid'] = generation_worker_process.pid
                    current_reservation_record['worker_start_token'] = worker_stat_fields[19]
                    current_reservation_record['worker_process_token'] = worker_process_token
                    write_record_atomically(active_reservation_path, current_reservation_record)
                finally:
                    fcntl.flock(gpu_execution_handle, fcntl.LOCK_UN)
            if generation_command_record['service']!='hermes-agent':
                try:
                    current_writer_stat_fields=Path(f'/proc/{generation_worker_process.pid}/stat').read_text().rpartition(') ')[2].split()
                    if int(current_writer_stat_fields[2])!=generation_worker_process.pid or int(current_writer_stat_fields[3])!=generation_worker_process.pid:
                        raise ValueError('작업 그룹 식별 오류')
                    fcntl.flock(gpu_execution_handle,fcntl.LOCK_EX)
                    try:
                        current_reservation_record=json.loads(active_reservation_path.read_text())
                        current_reservation_record.update(worker_pgid=generation_worker_process.pid,worker_start_token=current_writer_stat_fields[19],worker_process_token=worker_process_token)
                        write_record_atomically(active_reservation_path,current_reservation_record)
                    finally:
                        fcntl.flock(gpu_execution_handle,fcntl.LOCK_UN)
                except (OSError,ValueError,TypeError,IndexError):
                    # 식별을 기록하지 못해도 이후 정리 미확인 예약은 자동 회수하지 않는다.
                    pass
            if generation_command_record['service']=='hermes-agent':
                current_memory_guard = start_animate_memory_guard(generation_worker_process,current_include_group=True,
                    current_terminate_callback=lambda:signal.pidfd_send_signal(hermes_worker_pid_descriptor,signal.SIGKILL,None,HERMES_PIDFD_GROUP_FLAG))
            elif generation_command_record['service']=='writer-agent' and generation_command_record['command'][1:3]==['-m','generators.writer_agent.jobs']:
                current_memory_guard = start_animate_memory_guard(generation_worker_process, current_include_group=True)
            elif len(generation_command_record['command'])>1 and Path(generation_command_record['command'][1]).resolve()==WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/migraphx_build_worker.py':
                current_memory_guard = start_animate_memory_guard(generation_worker_process, current_include_group=True)
            elif len(generation_command_record['command']) > 1 and any(Path(current_argument_value).resolve() in (WORKFLOW_ROOT_DIRECTORY/'generators/wan_animate2/worker.py', WORKFLOW_ROOT_DIRECTORY/'generators/wan_fun/worker.py', WORKFLOW_ROOT_DIRECTORY/'generators/wan_vace/worker.py', WORKFLOW_ROOT_DIRECTORY/'generators/kimodo/worker.py', WORKFLOW_ROOT_DIRECTORY/'generators/image/run_flux_image.py', WORKFLOW_ROOT_DIRECTORY/'generators/image/run_flux_expression.py', WORKFLOW_ROOT_DIRECTORY/'generators/music/worker.py', WORKFLOW_ROOT_DIRECTORY/'generators/prompt_translation/worker.py') for current_argument_value in generation_command_record['command'][1:3]):
                if generation_command_record['service']=='prompt-translation':
                    current_memory_guard = start_animate_memory_guard(generation_worker_process, current_include_group=True)
                else:
                    current_memory_guard = start_animate_memory_guard(generation_worker_process)
            while generation_worker_process.poll() is None:
                if (generation_job_path/'cancel.request').exists():
                    if generation_command_record['service'] == 'writer-agent':
                        # 종료 확인 전에 실행기가 죽어도 예약이 자동 해제되지 않도록 기록한다.
                        current_writer_cleanup_unverified = True
                        fcntl.flock(gpu_execution_handle, fcntl.LOCK_EX)
                        try:
                            current_reservation_record=json.loads(active_reservation_path.read_text())
                            current_reservation_record.update(cleanup_unverified=True,worker_pgid=generation_worker_process.pid)
                            write_record_atomically(active_reservation_path,current_reservation_record)
                        finally:
                            fcntl.flock(gpu_execution_handle, fcntl.LOCK_UN)
                        current_writer_pid_descriptor=os.pidfd_open(generation_worker_process.pid)
                        try:
                            stop_hermes_worker_process_group(generation_worker_process.pid,current_writer_pid_descriptor)
                        finally:
                            os.close(current_writer_pid_descriptor)
                        generation_worker_process.wait()
                        current_writer_cleanup_unverified = False
                        break
                    if generation_command_record['service'] == 'hermes-agent':
                        try:
                            signal.pidfd_send_signal(hermes_worker_pid_descriptor, signal.SIGTERM, None, HERMES_PIDFD_GROUP_FLAG)
                        except ProcessLookupError:
                            pass
                    else:
                        os.killpg(generation_worker_process.pid, signal.SIGTERM)
                    try: generation_worker_process.wait(timeout=30 if generation_command_record['service'] == 'hermes-agent' else 5)
                    except subprocess.TimeoutExpired:
                        if generation_command_record['service'] == 'hermes-agent':
                            try:
                                signal.pidfd_send_signal(hermes_worker_pid_descriptor, signal.SIGKILL, None, HERMES_PIDFD_GROUP_FLAG)
                            except ProcessLookupError:
                                pass
                        else:
                            os.killpg(generation_worker_process.pid, signal.SIGKILL)
                        generation_worker_process.wait()
                    break
                if time.monotonic()-last_memory_sample_time >= GPU_POLL_INTERVAL:
                    last_memory_sample_time = time.monotonic()
                    try:
                        peak_memory_mib = max(peak_memory_mib, read_worker_memory(generation_worker_process.pid, current_memory_domain=current_memory_domain))
                        memory_sample_count += 1
                    except (OSError, ValueError, subprocess.SubprocessError) as measurement_error:
                        memory_measurement_error = str(measurement_error)
                time.sleep(.25)
            generation_exit_value = generation_worker_process.returncode
            if generation_command_record['service'] == 'hermes-agent':
                stop_hermes_worker_process_group(generation_worker_process.pid, hermes_worker_pid_descriptor)
            if current_memory_guard is not None:
                current_memory_guard[0].set()
                current_memory_guard[1].join()
            generation_status_record = json.loads((generation_job_path/'status.json').read_text())
            if (generation_job_path/'cancel.request').exists(): generation_status_record = {'status':'cancelled'}
            elif current_memory_guard is not None and current_memory_guard[2].get('error'):
                generation_status_record = {'status':'failed', 'exit_code':generation_exit_value, 'error':current_memory_guard[2]['error']}
            elif generation_exit_value == 0 and (generation_job_path/'stage-pause.json').exists():
                generation_status_record = {'status':'paused','message':'단계 결과를 확인한 뒤 다음 단계로 진행하세요.'}
            elif generation_status_record['status'] in ('running','queued'):
                generation_status_record = {'status':'completed' if generation_exit_value == 0 else 'failed', 'exit_code':generation_exit_value}
            if generation_status_record.get('status') == 'completed':
                generation_status_record.setdefault('completed_at', datetime.now(timezone.utc).isoformat())
            write_record_atomically(generation_job_path/'status.json', generation_status_record)
            return generation_exit_value
    except Exception as generation_error_value:
        write_record_atomically(generation_job_path/'status.json', {'status':'failed', 'error':str(generation_error_value)})
        print(f'GPU 대기 실행 실패: {generation_error_value}', flush=True)
        return 1
    finally:
        if current_memory_guard is not None:
            current_memory_guard[0].set()
            current_memory_guard[1].join()
        queue_ticket_path.unlink(missing_ok=True)
        if generation_worker_process is not None and generation_command_record['service'] == 'hermes-agent':
            try:
                if hermes_worker_pid_descriptor is not None and hermes_group_signal_supported:
                    stop_hermes_worker_process_group(generation_worker_process.pid, hermes_worker_pid_descriptor)
                elif generation_worker_process.poll() is None:
                    generation_worker_process.kill()
                generation_worker_process.wait()
            finally:
                if hermes_worker_pid_descriptor is not None:
                    os.close(hermes_worker_pid_descriptor)
        elif generation_worker_process is not None and generation_worker_process.poll() is None:
            os.killpg(generation_worker_process.pid, signal.SIGKILL)
            generation_worker_process.wait()
        if not current_writer_cleanup_unverified:
            active_reservation_path.unlink(missing_ok=True)
        try:
            if generation_worker_process is not None:
                final_status = json.loads((generation_job_path/'status.json').read_text())['status']
                observation_record = save_memory_observation(generation_command_record['service'], generation_job_path, peak_memory_mib, memory_sample_count, final_status, memory_measurement_error, identify_execution_command(generation_command_record['command'], generation_job_path, current_memory_domain))
                write_record_atomically(generation_job_path/'gpu-memory.json', observation_record)
        finally:
            if current_telemetry_recorder is not None:
                current_final_status = json.loads((generation_job_path/'status.json').read_text())['status']
                current_telemetry_recorder.finish_generation_telemetry(current_final_status)


if __name__ == '__main__':
    queue_argument_parser = argparse.ArgumentParser()
    queue_argument_parser.add_argument('--job-dir', required=True)
    sys.exit(execute_queued_generation(queue_argument_parser.parse_args().job_dir))



def identify_gpu_queue_source(current_job_path,current_queue_service,current_workflow_root=None):
    """허용된 작업 루트와 원본 티켓 경로가 일치하면 서비스 ID만 반환한다."""
    import re
    from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
    current_root_path=Path(current_workflow_root or WORKFLOW_ROOT_DIRECTORY)
    current_storage_paths={'kimodo':'kimodo','dwpose':'dwpose','wan22-vace':'wan22-vace','wan22-animate2':'wan22-animate2','qwen-21':'qwen-image-21','qwen-21-circular':'qwen-image-21-circular','mannequin-generator':'mannequin-generator','prop-generator':'prop-generator','vegetation-generator':'vegetation-generator','expression':'expression-generator','seamless-tile':'seamless-tile-generator','floor-tile':'qwen-image-2512/floor-tile','billboard-generator':'billboard-generator','building-generator':'building-generator'}
    current_expected_service='image'
    if current_queue_service=='flux-image':
        current_storage_paths={name:name+'-generator' for name in FLUX_IMAGE_PROFILE_RECORDS}
        current_expected_service='flux-image'
    if current_queue_service!=current_expected_service:
        return None
    current_path_value=Path(current_job_path)
    if not current_path_value.is_absolute() or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',current_path_value.name):
        return None
    try:
        if current_root_path.is_symlink() or not current_root_path.is_dir():return None
        current_base_path=current_root_path/'.tmp'/'test'
        if (current_root_path/'.tmp').is_symlink() or current_base_path.is_symlink() or not current_base_path.is_dir():return None
        current_source_values=[]
        for current_service_name,current_directory_name in current_storage_paths.items():
            current_storage_path=current_base_path/current_directory_name
            if current_storage_path.is_symlink() or not current_storage_path.is_dir() or current_storage_path.resolve()!=current_storage_path.absolute():continue
            current_expected_path=current_storage_path/current_path_value.name
            if current_expected_path.is_symlink() or not current_expected_path.is_dir():continue
            if current_path_value==current_expected_path and current_path_value.resolve()==current_expected_path.resolve():
                current_source_values.append(current_service_name)
        return current_source_values[0] if len(current_source_values)==1 else None
    except (OSError,ValueError,RuntimeError):
        return None



def is_dedicated_gpu_source_verifiable(current_queue_service):
    """원 서비스 작업 루트를 지정해 검증할 수 있는 대기열 서비스다."""
    from generators.music.service_constants import AUDIO_SERVICE_NAMES
    return current_queue_service in (*AUDIO_SERVICE_NAMES,'prompt-translation','wan-fun','wan-fun-prepare','flux-expression','review-capture')


def identify_dedicated_gpu_reservation_source(current_job_path,current_queue_service,current_workflow_root=None):
    """독립 대기열 서비스의 등록된 작업 디렉터리를 검증한다."""
    import re
    from generators.music.service_constants import AUDIO_SERVICE_NAMES
    current_source_directories={current_audio_name:current_audio_name for current_audio_name in AUDIO_SERVICE_NAMES}
    current_source_directories.update({'prompt-translation':'prompt-translation','wan-fun':'wan22-fun-control','wan-fun-prepare':'wan22-fun-control','flux-expression':'flux-expression-generator','review-capture':'review-capture'})
    current_directory_name=current_source_directories.get(current_queue_service)
    if current_directory_name is None or not isinstance(current_job_path,str):return None
    current_root_path=Path(current_workflow_root or WORKFLOW_ROOT_DIRECTORY)
    current_path_value=Path(current_job_path)
    if not current_path_value.is_absolute() or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',current_path_value.name):return None
    try:
        current_temporary_root=current_root_path/'.tmp'
        current_base_root=current_temporary_root/'test'
        current_service_root=current_base_root/current_directory_name
        current_expected_path=current_service_root/current_path_value.name
        for current_path_part in (current_root_path,current_temporary_root,current_base_root,current_service_root,current_expected_path):
            if current_path_part.is_symlink() or not current_path_part.is_dir():return None
        if current_path_value!=current_expected_path or current_path_value.resolve()!=current_expected_path.resolve():return None
        return 'wan22-fun-control' if current_queue_service in ('wan-fun','wan-fun-prepare') else current_queue_service
    except (OSError,ValueError,RuntimeError):
        return None



def verify_writer_queue_job_path(current_job_path):
    """설정된 작가 저장소의 작업 경로인지 부작용 없이 확인한다."""
    import yaml
    from generators.writer_agent.documents import DEFAULT_WORKSPACE_CONFIG, UniqueDocumentLoader, WORKSPACE_REQUIRED_FIELDS
    from generators.writer_agent.jobs import JOB_IDENTIFIER_PATTERN
    current_job_path=Path(current_job_path)
    if not current_job_path.is_absolute() or not JOB_IDENTIFIER_PATTERN.fullmatch(current_job_path.name):return False
    current_config_path=Path(os.environ.get('SLIME_WRITER_WORKSPACE_CONFIG',str(DEFAULT_WORKSPACE_CONFIG)))
    if not current_config_path.is_absolute():raise ValueError('작가 작업 공간 설정 경로 오류')
    try:current_resolved_config=current_config_path.resolve(strict=True)
    except (OSError,RuntimeError) as current_path_error:raise ValueError('작가 작업 공간 설정 경로를 확인할 수 없습니다.') from current_path_error
    current_config_bytes,_=read_bounded_gpu_observation_bytes(current_resolved_config,GPU_OBSERVATION_MAXIMUM_BYTES)
    try:current_config_record=yaml.load(current_config_bytes,Loader=UniqueDocumentLoader)
    except yaml.YAMLError as current_config_error:raise ValueError('작가 작업 공간 설정을 확인할 수 없습니다.') from current_config_error
    if not isinstance(current_config_record,dict) or set(current_config_record)!=WORKSPACE_REQUIRED_FIELDS or type(current_config_record.get('schema_version')) is not int or current_config_record['schema_version']!=1:return False
    current_root_value=current_config_record.get('state_root')
    if not isinstance(current_root_value,str) or not Path(current_root_value).is_absolute():return False
    try:current_state_root=Path(current_root_value).resolve()
    except (OSError,RuntimeError) as current_path_error:raise ValueError('작가 작업 저장소 경로를 확인할 수 없습니다.') from current_path_error
    current_jobs_root=current_state_root/'jobs'
    current_expected_path=current_jobs_root/current_job_path.name
    if not current_state_root.is_dir() or current_jobs_root.is_symlink() or not current_jobs_root.is_dir() or current_expected_path.is_symlink() or not current_expected_path.is_dir():return False
    if current_job_path!=current_expected_path or current_job_path.resolve()!=current_expected_path:return False
    try:current_rechecked_path=current_config_path.resolve(strict=True)
    except (OSError,RuntimeError) as current_path_error:raise ValueError('작가 작업 공간 설정 경로가 조회 중 변경됐습니다.') from current_path_error
    if current_rechecked_path!=current_resolved_config:raise ValueError('작가 작업 공간 설정 경로가 조회 중 변경됐습니다.')
    current_rechecked_bytes,_=read_bounded_gpu_observation_bytes(current_resolved_config,GPU_OBSERVATION_MAXIMUM_BYTES)
    if current_rechecked_bytes!=current_config_bytes:raise ValueError('작가 작업 공간 설정이 조회 중 변경됐습니다.')
    return True


def list_waiting_gpu_jobs(include_source_identity=False,observation_limits=False):
    """살아 있는 대기 실행기의 작업 목록만 읽는다."""
    waiting_job_records=[]
    for waiting_ticket_path in (read_priority_tickets(observation_limits=True) if observation_limits else read_priority_tickets()):
        try:
            current_before_revision=(fingerprint_gpu_queue_ticket(waiting_ticket_path,observation_limits=True) if observation_limits else fingerprint_gpu_queue_ticket(waiting_ticket_path)) if include_source_identity else None
            waiting_ticket_record=json.loads(read_bounded_gpu_observation_bytes(waiting_ticket_path,65536)[0]) if observation_limits else json.loads(waiting_ticket_path.read_text())
            current_ticket_pid=validate_gpu_ticket_process_identifier(waiting_ticket_record) if include_source_identity or observation_limits else waiting_ticket_record['pid']
            os.kill(current_ticket_pid,0)
            waiting_job_directory=Path(waiting_ticket_record['path'])
            current_external_job=not waiting_job_directory.resolve().is_relative_to(WORKFLOW_ROOT_DIRECTORY/'.tmp')
            if observation_limits and current_external_job:
                try:current_writer_verified=verify_writer_queue_job_path(waiting_job_directory)
                except (OSError,RuntimeError) as current_path_error:raise ValueError('대기 티켓의 작업 경로와 서비스를 확인할 수 없습니다.') from current_path_error
                if not current_writer_verified:raise ValueError('대기 티켓의 작업 경로와 서비스를 확인할 수 없습니다.')
            waiting_status_record=json.loads(read_bounded_gpu_observation_bytes(waiting_job_directory/'status.json',GPU_OBSERVATION_MAXIMUM_BYTES)[0]) if observation_limits else json.loads((waiting_job_directory/'status.json').read_text())
            if (include_source_identity or observation_limits) and (not isinstance(waiting_status_record,dict) or waiting_status_record.get('status') not in ('queued','running','completed','failed','cancelled','canceled','paused')):
                raise ValueError('대기 티켓의 작업 상태를 확인할 수 없습니다.')
            if waiting_status_record['status']!='queued':continue
            waiting_command_record=json.loads(read_bounded_gpu_observation_bytes(waiting_job_directory/'gpu-command.json',GPU_OBSERVATION_MAXIMUM_BYTES)[0]) if observation_limits else json.loads((waiting_job_directory/'gpu-command.json').read_text())
            if (include_source_identity or observation_limits) and (not isinstance(waiting_command_record,dict) or not isinstance(waiting_command_record.get('service'),str) or not waiting_command_record['service'].strip()):
                raise ValueError('대기 티켓의 작업 서비스 형식을 확인할 수 없습니다.')
            if observation_limits and not current_external_job and waiting_command_record['service']=='writer-agent':
                try:current_writer_verified=verify_writer_queue_job_path(waiting_job_directory)
                except (OSError,RuntimeError) as current_path_error:raise ValueError('대기 티켓의 작업 경로와 서비스를 확인할 수 없습니다.') from current_path_error
                if not current_writer_verified:raise ValueError('대기 티켓의 작업 경로와 서비스를 확인할 수 없습니다.')
            if current_external_job and waiting_command_record.get('service')!='writer-agent':
                if observation_limits:raise ValueError('대기 티켓의 작업 경로와 서비스를 확인할 수 없습니다.')
                continue
            waiting_job_record={'id':waiting_job_directory.name,'service':waiting_command_record['service']}
            if include_source_identity:
                waiting_job_record['executor_identity']=inspect_gpu_ticket_executor_identity(waiting_ticket_record)
                current_after_revision=fingerprint_gpu_queue_ticket(waiting_ticket_path,observation_limits=True) if observation_limits else fingerprint_gpu_queue_ticket(waiting_ticket_path)
                if current_before_revision!=current_after_revision:
                    raise ValueError('대기 티켓이 조회 중 변경됐습니다.')
                waiting_job_record['ticket_revision']=current_after_revision
                current_source_service=identify_gpu_queue_source(waiting_job_directory,waiting_command_record['service'])
                if current_source_service is None and is_dedicated_gpu_source_verifiable(waiting_command_record['service']):
                    current_source_service=identify_dedicated_gpu_reservation_source(str(waiting_job_directory),waiting_command_record['service'])
                if current_source_service is not None:
                    waiting_job_record['source_service']=current_source_service
            waiting_job_records.append(waiting_job_record)
        except FileNotFoundError:
            if not include_source_identity and not observation_limits:
                continue
            try:
                waiting_ticket_path.lstat()
            except FileNotFoundError:
                continue
            raise ValueError('살아 있는 대기 티켓의 작업 기록을 확인할 수 없습니다.')
        except ProcessLookupError:
            continue
    return {'jobs':waiting_job_records}
