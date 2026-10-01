"""GUI 수명과 독립된 로컬 명령 게이트웨이·작업 서비스 서버."""
import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import signal
import sys
import threading
import traceback
from urllib.parse import urlsplit

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.management_transport import send_management_json_response, validate_management_http_request

from tools.review.common.management_environment import GATEWAY_SERVER_HOST, GATEWAY_SERVER_PORT
GATEWAY_HEARTBEAT_SECONDS = 5


def create_gateway_request_handler(dispatch_runtime_request):
    class GatewayRequestHandler(BaseHTTPRequestHandler):
        def handle_runtime_request(self):
            try:
                validate_management_http_request(self)
            except ValueError as request_validation_error:
                send_management_json_response(self, 400, {'error': str(request_validation_error)})
                return
            request_route_path = urlsplit(self.path).path
            if self.command == 'GET' and request_route_path == '/management/health':
                send_management_json_response(self, 200, {'status': 'ok', 'role': 'management-gateway', 'pid': os.getpid()})
                return
            if self.command == 'GET' and request_route_path in ('/management/gpu-status', '/management/gpu-queue'):
                from tools.review.common.gpu_status import read_gpu_status
                response_record_values = read_gpu_status()
                if request_route_path == '/management/gpu-queue':
                    from tools.review.common.gpu_job_queue import list_waiting_gpu_jobs
                    response_record_values = list_waiting_gpu_jobs() | {'gpu_status': response_record_values}
                send_management_json_response(self, 200, response_record_values)
                return
            if not dispatch_runtime_request(self):
                send_management_json_response(self, 404, {'error': '지원하지 않는 작업 경로'})

        do_GET = handle_runtime_request
        do_POST = handle_runtime_request

        def log_message(self, request_message_format, *request_message_arguments):
            self.server.emit_gateway_trace('request', (request_message_format % request_message_arguments).replace('\n', ' '))

    return GatewayRequestHandler


def create_gateway_trace_logger(gateway_log_path):
    """파일 로그는 필수로 기록하고 닫힌 콘솔 파이프는 HTTP 응답에 전파하지 않는다."""
    gateway_trace_lock = threading.Lock()
    console_output_active = True

    def emit_gateway_trace(trace_stage_name, trace_message_text):
        nonlocal console_output_active
        trace_line_text = f'{datetime.now().isoformat()}/management-gateway/{trace_stage_name} {trace_message_text}'
        with gateway_trace_lock:
            with gateway_log_path.open('a') as gateway_log_stream:
                gateway_log_stream.write(trace_line_text + '\n')
            if console_output_active:
                try:
                    print(trace_line_text, flush=True)
                except BrokenPipeError:
                    console_output_active = False
                    with gateway_log_path.open('a') as gateway_log_stream:
                        gateway_log_stream.write(f'{datetime.now().isoformat()}/management-gateway/console-detached 콘솔 파이프 종료 · 파일 로그 유지\n')
    return emit_gateway_trace


def run_management_gateway(server_port_number, writer_workspace_config=None):
    from tools.review.common.management_runtime import create_management_runtime
    gateway_stop_event = threading.Event()
    gateway_log_directory = WORKFLOW_ROOT_DIRECTORY / '.tmp/gateway-server-logs'
    gateway_log_directory.mkdir(parents=True, exist_ok=True)
    gateway_log_path = gateway_log_directory / f'{datetime.now():%Y-%m-%d_%H-%M-%S}-{os.getpid()}.log'

    emit_gateway_trace = create_gateway_trace_logger(gateway_log_path)

    def emit_gateway_heartbeat():
        while not gateway_stop_event.wait(GATEWAY_HEARTBEAT_SECONDS):
            emit_gateway_trace('heartbeat', f'pid={os.getpid()} port={server_port_number} log_bytes={gateway_log_path.stat().st_size}')

    def terminate_gateway_server(received_signal_number, current_stack_frame):
        raise KeyboardInterrupt

    management_service_runtime = None
    previous_signal_handler = signal.signal(signal.SIGTERM, terminate_gateway_server)
    try:
        management_service_runtime = create_management_runtime(writer_workspace_config)
        with ThreadingHTTPServer((GATEWAY_SERVER_HOST, server_port_number), create_gateway_request_handler(management_service_runtime.dispatch_runtime_request)) as gateway_http_server:
            gateway_http_server.emit_gateway_trace = emit_gateway_trace
            emit_gateway_trace('start', f'http://{GATEWAY_SERVER_HOST}:{server_port_number} pid={os.getpid()} log={gateway_log_path}')
            gateway_heartbeat_thread = threading.Thread(target=emit_gateway_heartbeat, daemon=True)
            gateway_heartbeat_thread.start()
            try:
                gateway_http_server.serve_forever(poll_interval=.5)
            except KeyboardInterrupt:
                emit_gateway_trace('stop', '게이트웨이 종료 · 별도 GPU 대기·실행 프로세스 유지')
            finally:
                gateway_stop_event.set()
                gateway_heartbeat_thread.join(timeout=1)
    except Exception:
        emit_gateway_trace('failure', traceback.format_exc())
        print('\n'.join(gateway_log_path.read_text().splitlines()[-20:]), flush=True)
        raise
    finally:
        try:
            if management_service_runtime is not None:
                management_service_runtime.close_runtime_services()
        finally:
            signal.signal(signal.SIGTERM, previous_signal_handler)


def parse_gateway_arguments(command_argument_values=None):
    gateway_argument_parser = argparse.ArgumentParser(description=__doc__)
    gateway_argument_parser.add_argument('--port', type=int, default=GATEWAY_SERVER_PORT)
    gateway_argument_parser.add_argument('--watch', action='store_true', help='게이트웨이·작업 서비스 코드 변경 시 게이트웨이만 재시작')
    gateway_argument_parser.add_argument('--writer-agent-config', type=Path, help='작가 에이전트 로컬 작업 공간 YAML')
    gateway_argument_values = gateway_argument_parser.parse_args(command_argument_values)
    if not 1024 <= gateway_argument_values.port <= 65535:
        gateway_argument_parser.error('포트는 1024~65535여야 합니다.')
    return gateway_argument_values


if __name__ == '__main__':
    gateway_argument_values = parse_gateway_arguments()
    if gateway_argument_values.watch:
        from tools.review.common.gateway_watch import run_gateway_watch_mode
        run_gateway_watch_mode(gateway_argument_values.port, gateway_argument_values.writer_agent_config)
    else:
        run_management_gateway(gateway_argument_values.port, gateway_argument_values.writer_agent_config)
