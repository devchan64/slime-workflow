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
            return int(current_field_parts[1])
    raise ValueError(f'메모리 필드 누락: {current_field_name}')


def monitor_animate_host_memory(current_worker_process, current_stop_event, current_guard_result):
    """시스템 RAM 부족 시 해당 작업 프로세스 그룹만 종료한다."""
    while not current_stop_event.is_set() and current_worker_process.poll() is None:
        try:
            current_available_kib = read_memory_field_kib('/proc/meminfo', 'MemAvailable')
            current_worker_rss_kib = read_memory_field_kib(f'/proc/{current_worker_process.pid}/status', 'VmRSS')
        except (OSError, ValueError) as current_read_error:
            if current_worker_process.poll() is not None:
                return
            current_guard_result['error'] = f'시스템 RAM 감시 실패: {current_read_error}'
        else:
            if current_available_kib >= HOST_MEMORY_RESERVE_KIB or current_worker_rss_kib < HOST_WORKER_MINIMUM_RSS_KIB:
                current_stop_event.wait(HOST_MEMORY_POLL_SECONDS)
                continue
            current_guard_result['error'] = (f'시스템 RAM 보호: 사용 가능 {current_available_kib // 1024} MiB, '
                f'작업 RSS {current_worker_rss_kib // 1024} MiB; 여유 {HOST_MEMORY_RESERVE_KIB // 1024} MiB 미만')
        print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/host-memory-guard/failure {current_guard_result["error"]}', flush=True)
        try:
            os.killpg(current_worker_process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        return


def start_animate_memory_guard(current_worker_process):
    """GPU 조회가 지연되어도 RAM 감시가 독립적으로 진행되게 한다."""
    current_stop_event = threading.Event()
    current_guard_result = {}
    current_guard_thread = threading.Thread(target=monitor_animate_host_memory,
        args=(current_worker_process, current_stop_event, current_guard_result), daemon=True)
    current_guard_thread.start()
    return current_stop_event, current_guard_thread, current_guard_result
