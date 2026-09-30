"""외부 프로세스의 출력·heartbeat·시그널·소유 프로세스 그룹 정리."""
import codecs
from collections import deque
from datetime import datetime
import os
import selectors
import shlex
import signal
import subprocess
import time
from zoneinfo import ZoneInfo
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY

LAUNCHER_HEARTBEAT_SECONDS = 5
LAUNCHER_STOP_TIMEOUT_SECONDS = 10
LAUNCHER_POLL_INTERVAL_SECONDS = .2
LAUNCHER_OUTPUT_CHUNK_BYTES = 65536
LAUNCHER_LOG_TAIL_LINES = 20


class ManagementLaunchLogger:
    """실행 로그와 실패 시 출력할 마지막 줄을 함께 유지한다."""

    def __init__(self, launcher_mode_name):
        log_directory_path = WORKFLOW_ROOT_DIRECTORY/'.tmp/management-launcher-logs'
        log_directory_path.mkdir(parents=True, exist_ok=True)
        launch_timestamp_text = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S-%f')
        self.launcher_mode_name = launcher_mode_name
        self.output_log_path = log_directory_path/f'{launch_timestamp_text}-{launcher_mode_name}-{os.getpid()}.log'
        self.output_log_stream = self.output_log_path.open('w', encoding='utf-8')
        self.recent_output_lines = deque(maxlen=LAUNCHER_LOG_TAIL_LINES)
        self.output_line_count = 0
        self.latest_output_text = '출력 대기'

    def write_process_output(self, process_output_text):
        self.output_log_stream.write(process_output_text)
        self.output_log_stream.flush()
        print(process_output_text, end='', flush=True)
        self.output_line_count += process_output_text.count('\n')
        self.recent_output_lines.extend(process_output_text.splitlines())
        if process_output_text.strip():
            self.latest_output_text = process_output_text.strip().splitlines()[-1][-240:]

    def emit_launch_trace(self, trace_stage_name, trace_message_text):
        self.write_process_output(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/management-{self.launcher_mode_name}/{trace_stage_name} {trace_message_text}\n')

    def close_launch_log(self):
        self.output_log_stream.close()


def signal_management_process_group(process_group_identifier, requested_signal_number):
    try:
        os.killpg(process_group_identifier, requested_signal_number)
    except ProcessLookupError:
        pass


def stop_management_process_group(command_process_handle):
    """직접 시작한 그룹만 종료하며 별도 세션의 GPU 작업은 보존한다."""
    signal_management_process_group(command_process_handle.pid, signal.SIGTERM)
    try:
        command_process_handle.wait(timeout=LAUNCHER_STOP_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        signal_management_process_group(command_process_handle.pid, signal.SIGKILL)
        command_process_handle.wait()
    finally:
        # 부모만 종료되고 SIGTERM을 무시한 같은 그룹의 자식도 남기지 않는다.
        signal_management_process_group(command_process_handle.pid, signal.SIGKILL)


def run_logged_management_command(command_argument_values, launcher_trace_logger):
    launcher_trace_logger.emit_launch_trace('command', shlex.join(command_argument_values))
    requested_signal_values = []
    command_process_handle = subprocess.Popen(
        command_argument_values, cwd=WORKFLOW_ROOT_DIRECTORY, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=True,
        env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    previous_signal_handlers = {}

    def forward_launcher_signal(received_signal_number, current_stack_frame):
        if not requested_signal_values:
            requested_signal_values.extend([received_signal_number, time.monotonic()])
            signal_management_process_group(command_process_handle.pid, signal.SIGTERM)

    for current_signal_number in (signal.SIGINT, signal.SIGTERM):
        previous_signal_handlers[current_signal_number] = signal.signal(current_signal_number, forward_launcher_signal)
    next_heartbeat_time = time.monotonic() + LAUNCHER_HEARTBEAT_SECONDS
    output_text_decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
    try:
        with selectors.DefaultSelector() as output_event_selector:
            output_event_selector.register(command_process_handle.stdout, selectors.EVENT_READ)
            while command_process_handle.poll() is None:
                for output_event_key, output_event_mask in output_event_selector.select(LAUNCHER_POLL_INTERVAL_SECONDS):
                    process_output_bytes = os.read(output_event_key.fd, LAUNCHER_OUTPUT_CHUNK_BYTES)
                    if process_output_bytes:
                        launcher_trace_logger.write_process_output(output_text_decoder.decode(process_output_bytes))
                    else:
                        output_event_selector.unregister(output_event_key.fileobj)
                if requested_signal_values and time.monotonic() - requested_signal_values[1] >= LAUNCHER_STOP_TIMEOUT_SECONDS:
                    signal_management_process_group(command_process_handle.pid, signal.SIGKILL)
                if time.monotonic() >= next_heartbeat_time:
                    latest_output_text = launcher_trace_logger.latest_output_text
                    launcher_trace_logger.emit_launch_trace('heartbeat', f'pid={command_process_handle.pid} lines={launcher_trace_logger.output_line_count} log_bytes={launcher_trace_logger.output_log_path.stat().st_size} recent={latest_output_text}')
                    launcher_trace_logger.latest_output_text = latest_output_text
                    next_heartbeat_time = time.monotonic() + LAUNCHER_HEARTBEAT_SECONDS
            # 종료한 서버가 남긴 GUI 자식만 정리한다. GPU 실행기는 별도 세션이다.
            signal_management_process_group(command_process_handle.pid, signal.SIGTERM)
            os.set_blocking(command_process_handle.stdout.fileno(), False)
            while True:
                try:
                    remaining_output_bytes = os.read(command_process_handle.stdout.fileno(), LAUNCHER_OUTPUT_CHUNK_BYTES)
                except BlockingIOError:
                    break
                if not remaining_output_bytes:
                    break
                launcher_trace_logger.write_process_output(output_text_decoder.decode(remaining_output_bytes))
            launcher_trace_logger.write_process_output(output_text_decoder.decode(b'', final=True))
    finally:
        try:
            stop_management_process_group(command_process_handle)
        finally:
            command_process_handle.stdout.close()
            for current_signal_number, previous_signal_handler in previous_signal_handlers.items():
                signal.signal(current_signal_number, previous_signal_handler)
    if requested_signal_values:
        launcher_trace_logger.emit_launch_trace('stop', f'사용자 종료 signal={requested_signal_values[0]}')
        raise SystemExit(128 + requested_signal_values[0])
    if command_process_handle.returncode:
        raise subprocess.CalledProcessError(command_process_handle.returncode, command_argument_values)
    launcher_trace_logger.emit_launch_trace('complete', f'exit={command_process_handle.returncode}')
