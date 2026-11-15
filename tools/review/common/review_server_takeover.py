"""동일 저장소의 기존 GUI 서버만 정상 종료해 포트를 인계받는다."""
from pathlib import Path
import os
import signal
import sys
import psutil

SERVER_STOP_TIMEOUT_SECONDS = 10


def matches_review_server(current_process_value, current_script_path):
    current_command_values = current_process_value.cmdline()
    while len(current_command_values) > 1 and current_command_values[1] in ('-u', '-B', '-E', '-s', '-S', '-I'):
        current_command_values = [current_command_values[0], *current_command_values[2:]]
    return len(current_command_values) > 1 and Path(current_command_values[1]).is_absolute() and Path(current_command_values[1]).resolve() == current_script_path.resolve() and current_process_value.uids().real == os.getuid()


def release_review_server_port(current_port_number, current_script_path):
    current_self_process = psutil.Process()
    current_parent_process = current_self_process.parent()
    # watch가 시작한 자식은 부모의 포트 인계 절차를 반복하지 않는다.
    if current_parent_process and matches_review_server(current_parent_process, current_script_path) and '--watch' in current_parent_process.cmdline():
        return
    current_listener_pids = {current_connection.pid for current_connection in psutil.net_connections(kind='tcp') if current_connection.status == psutil.CONN_LISTEN and current_connection.laddr.port == current_port_number}
    current_stop_processes = {}
    for current_listener_pid in current_listener_pids:
        if current_listener_pid is None:
            raise RuntimeError(f'{current_port_number} 포트 소유자를 확인할 수 없어 종료하지 않습니다.')
        current_listener_process = psutil.Process(current_listener_pid)
        if not matches_review_server(current_listener_process, current_script_path):
            current_creation_time = current_listener_process.create_time()
            current_command_text = ' '.join(current_listener_process.cmdline()) or current_listener_process.name()
            if not sys.stdin.isatty():
                raise RuntimeError(f'{current_port_number} 포트를 다른 프로그램이 사용 중입니다: PID={current_listener_pid} 명령={current_command_text}. 대화형 터미널에서 다시 실행하세요.')
            selected_answer_text = input(f'{current_port_number} 포트 사용 프로세스를 강제 종료하고 실행할까요? PID={current_listener_pid} 명령={current_command_text} [y/N] ')
            if selected_answer_text.strip().lower() not in ('y', 'yes'):
                raise RuntimeError('포트 점유 프로세스를 유지하여 GUI 실행을 취소했습니다.')
            current_listener_process = psutil.Process(current_listener_pid)
            if current_listener_process.create_time() != current_creation_time or not any(
                current_connection.pid == current_listener_pid and current_connection.status == psutil.CONN_LISTEN and current_connection.laddr.port == current_port_number
                for current_connection in psutil.net_connections(kind='tcp')
            ):
                raise RuntimeError('확인 중 포트 점유 프로세스가 변경되었습니다. 다시 실행하세요.')
            current_listener_process.kill()
            try:
                current_listener_process.wait(timeout=SERVER_STOP_TIMEOUT_SECONDS)
            except psutil.TimeoutExpired as current_timeout_error:
                raise RuntimeError(f'포트 점유 프로세스 종료 시간 초과: PID={current_listener_pid}') from current_timeout_error
            continue
        current_owner_process = current_listener_process.parent()
        if current_owner_process and matches_review_server(current_owner_process, current_script_path) and '--watch' in current_owner_process.cmdline():
            current_stop_processes[current_owner_process.pid] = current_owner_process
        current_stop_processes[current_listener_pid] = current_listener_process
    # 감시자를 먼저 멈춰 서버 자동 재생성을 차단한다. 게이트웨이·GPU 작업은 건드리지 않는다.
    for current_stop_process in current_stop_processes.values():
        try:
            print(f'GUI 포트 인계: port={current_port_number} PID={current_stop_process.pid} 정상 종료 요청', flush=True)
            current_stop_process.send_signal(signal.SIGINT)
        except psutil.NoSuchProcess:
            pass
    _, current_alive_processes = psutil.wait_procs(list(current_stop_processes.values()), timeout=SERVER_STOP_TIMEOUT_SECONDS)
    if current_alive_processes:
        raise RuntimeError(f'기존 GUI 정상 종료 시간 초과: {[current_process.pid for current_process in current_alive_processes]} · 강제 종료하지 않습니다.')
