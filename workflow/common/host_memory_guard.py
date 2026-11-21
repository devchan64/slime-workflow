"""영상 생성 작업의 시스템 메모리 압박을 독립적으로 감시한다."""
import os
from pathlib import Path
import signal
import threading
import time

HOST_MEMORY_RESERVE_KIB = 6 * 1024 * 1024
HOST_WORKER_MINIMUM_RSS_KIB = 8 * 1024 * 1024
HOST_MEMORY_POLL_SECONDS = 0.2


def read_memory_field_kib(current_file_path, current_field_name):
    """Linux 메모리 정보를 KiB 단위로 읽고 누락을 명시적으로 거절한다."""
    for current_line_text in Path(current_file_path).read_text().splitlines():
        current_field_parts = current_line_text.split()
        if current_field_parts and current_field_parts[0] == current_field_name + ':':
            if len(current_field_parts) != 3 or current_field_parts[2] != 'kB':
                raise ValueError(f'메모리 필드 형식 오류: {current_field_name}')
            current_memory_value=int(current_field_parts[1])
            if current_memory_value<0:
                raise ValueError(f'음수 메모리 필드: {current_field_name}')
            return current_memory_value
    raise ValueError(f'메모리 필드 누락: {current_field_name}')


def read_worker_group_rss_kib(current_worker_identifier):
    """같은 프로세스 그룹의 RSS를 합산한다. 종료 중인 프로세스는 제외한다."""
    current_total_rss=0
    current_found_leader=False
    for current_stat_path in Path('/proc').glob('[0-9]*/stat'):
        try:
            current_process_identifier=int(current_stat_path.parent.name)
            if os.getpgid(current_process_identifier)!=current_worker_identifier:
                continue
            current_process_fields=current_stat_path.read_text().rsplit(') ',1)[1].split()
            if int(current_process_fields[2])!=current_worker_identifier or current_process_fields[0]=='Z':
                continue
            if current_process_identifier==current_worker_identifier:
                current_found_leader=True
            current_total_rss+=read_memory_field_kib(current_stat_path.parent/'status','VmRSS')
        except (FileNotFoundError,ProcessLookupError):
            continue
        except (IndexError,ValueError) as current_parse_error:
            # A child can exit between reading stat and status, losing VmRSS when it
            # becomes a zombie. Ignore it only after independently confirming that.
            try:
                current_status_text = (current_stat_path.parent/'status').read_text()
                current_is_zombie = any(line.split()[:2] in (['State:', 'Z'], ['State:', 'X']) for line in current_status_text.splitlines())
                current_same_group = os.getpgid(current_process_identifier) == current_worker_identifier
            except (FileNotFoundError, ProcessLookupError):
                continue
            if not current_same_group or (current_is_zombie and current_process_identifier != current_worker_identifier):
                continue
            raise ValueError(f'작업 프로세스 그룹 메모리 확인 실패 (PID {current_process_identifier}): {current_parse_error}') from current_parse_error
    if not current_found_leader:
        raise ValueError('작업 프로세스 그룹 리더를 확인할 수 없습니다.')
    return current_total_rss


def monitor_animate_host_memory(current_worker_process, current_stop_event, current_guard_result, current_include_group=False, current_terminate_callback=None):
    """시스템 RAM 부족 시 해당 작업 프로세스 그룹만 종료한다."""
    while not current_stop_event.is_set() and current_worker_process.poll() is None:
        current_host_read_complete = False
        try:
            current_available_kib = read_memory_field_kib('/proc/meminfo', 'MemAvailable')
            current_host_read_complete = True
            current_worker_rss_kib = read_worker_group_rss_kib(current_worker_process.pid) if current_include_group else read_memory_field_kib(f'/proc/{current_worker_process.pid}/status', 'VmRSS')
        except (OSError, ValueError) as current_read_error:
            if current_worker_process.poll() is not None:
                return
            if current_host_read_complete:
                try:
                    current_process_status = Path(f'/proc/{current_worker_process.pid}/status').read_text()
                except FileNotFoundError:
                    return
                except OSError:
                    current_process_status = ''
                if any(current_status_line.split()[:2] == ['State:', 'Z'] for current_status_line in current_process_status.splitlines()):
                    return
            current_guard_result['error'] = f'시스템 RAM 감시 실패: {current_read_error}'
        else:
            if current_available_kib >= HOST_MEMORY_RESERVE_KIB or current_worker_rss_kib < HOST_WORKER_MINIMUM_RSS_KIB:
                current_stop_event.wait(HOST_MEMORY_POLL_SECONDS)
                continue
            current_guard_result['error'] = (f'시스템 RAM 보호: 사용 가능 {current_available_kib // 1024} MiB, '
                f'작업 RSS {current_worker_rss_kib // 1024} MiB; 여유 {HOST_MEMORY_RESERVE_KIB // 1024} MiB 미만')
        if current_worker_process.poll() is not None:
            current_guard_result.pop('error',None)
            return
        print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/host-memory-guard/failure {current_guard_result["error"]}', flush=True)
        try:
            if current_terminate_callback is None:
                os.killpg(current_worker_process.pid, signal.SIGKILL)
            else:
                current_terminate_callback()
        except ProcessLookupError:
            pass
        return


def start_animate_memory_guard(current_worker_process, current_include_group=False, current_terminate_callback=None):
    """GPU 조회가 지연되어도 RAM 감시가 독립적으로 진행되게 한다."""
    current_stop_event = threading.Event()
    current_guard_result = {}
    current_guard_thread = threading.Thread(target=monitor_animate_host_memory,
        args=(current_worker_process, current_stop_event, current_guard_result, current_include_group, current_terminate_callback), daemon=True)
    current_guard_thread.start()
    return current_stop_event, current_guard_thread, current_guard_result
