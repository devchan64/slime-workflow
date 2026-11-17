"""기존 게이트웨이와 GUI 실행기를 독립 프로세스로 시작한다."""
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
from zoneinfo import ZoneInfo

from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, DEFAULT_GATEWAY_ADDRESS, validate_gateway_address

STACK_START_TIMEOUT_SECONDS = 90
STACK_HEARTBEAT_SECONDS = 5


def check_management_stack_port(port_number_value):
    """바인드 가능 여부를 확인하며 다른 프로세스는 건드리지 않는다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as port_probe_socket:
        port_probe_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            port_probe_socket.bind(('127.0.0.1', port_number_value))
        except OSError as port_check_error:
            raise ValueError(f'{port_number_value} 포트를 사용할 수 없습니다. 기존 프로세스는 유지합니다: {port_check_error}') from port_check_error


def wait_management_stack_endpoint(stack_process_handle, endpoint_url_value, expected_service_role, stack_launch_token, stack_log_path):
    stack_deadline_time = time.monotonic() + STACK_START_TIMEOUT_SECONDS
    stack_heartbeat_time = time.monotonic() + STACK_HEARTBEAT_SECONDS
    stack_http_opener = build_opener(ProxyHandler({}))
    while time.monotonic() < stack_deadline_time:
        if stack_process_handle.poll() is not None:
            raise RuntimeError(f'시작 프로세스가 종료됐습니다: exit={stack_process_handle.returncode}, 로그={stack_log_path}')
        try:
            with stack_http_opener.open(endpoint_url_value, timeout=1) as stack_http_response:
                if stack_http_response.status == 200:
                    stack_health_record = json.loads(stack_http_response.read(4096))
                    if (isinstance(stack_health_record, dict) and stack_health_record.get('role') == expected_service_role
                            and stack_health_record.get('status') == 'ok' and stack_health_record.get('launch_token') == stack_launch_token):
                        if expected_service_role == 'management-gui':
                            with stack_http_opener.open('http://127.0.0.1:8770/management/', timeout=10) as stack_page_response:
                                if stack_page_response.status != 200:
                                    continue
                        return
        except (OSError, ValueError, TypeError):
            pass
        if time.monotonic() >= stack_heartbeat_time:
            print(f'시작 응답 대기 중: {endpoint_url_value} · 로그={stack_log_path}', flush=True)
            stack_heartbeat_time = time.monotonic() + STACK_HEARTBEAT_SECONDS
        time.sleep(.25)
    raise TimeoutError(f'시작 응답 시간 초과: {endpoint_url_value}. 프로세스는 자동 종료하지 않습니다. 로그={stack_log_path}')


def start_management_stack():
    """사용 중인 포트는 인계하지 않고 두 서비스를 독립 실행한다."""
    gateway_port_value = int(os.environ.get('MANAGEMENT_GATEWAY_PORT', '8771'))
    gui_port_value = int(os.environ.get('REVIEW_SERVER_PORT', '8770'))
    gateway_address_value = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
    if gui_port_value != 8770 or urlsplit(gateway_address_value).port != gateway_port_value or gateway_port_value == gui_port_value:
        raise ValueError('GUI는 8770을 사용하며 게이트웨이 포트와 주소가 일치해야 합니다.')
    for stack_mode_name in ('gateway', 'gui'):
        from tools.review.common.management_launcher import build_management_launch_command
        build_management_launch_command(stack_mode_name, ['--no-takeover'] if stack_mode_name == 'gui' else [])
    stack_log_directory = WORKFLOW_ROOT_DIRECTORY / '.tmp/management-stack'
    stack_log_directory.mkdir(parents=True, exist_ok=True)
    with (stack_log_directory / 'start.lock').open('a') as stack_lock_stream:
        fcntl.flock(stack_lock_stream, fcntl.LOCK_EX)
        check_management_stack_port(gateway_port_value)
        check_management_stack_port(gui_port_value)
        stack_run_stamp = datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S-%f')
        stack_launcher_path = WORKFLOW_ROOT_DIRECTORY / 'tools/review/common/management_launcher.py'
        for stack_mode_name, stack_url_value, stack_expected_role in (('gateway', gateway_address_value + '/management/health', 'management-gateway'), ('gui', 'http://127.0.0.1:8770/management/gui-health', 'management-gui')):
            stack_log_path = stack_log_directory / f'{stack_run_stamp}-{stack_mode_name}.log'
            stack_arguments_list = [sys.executable, str(stack_launcher_path), stack_mode_name]
            stack_launch_token = secrets.token_hex(16)
            if stack_mode_name == 'gui':
                stack_arguments_list.append('--no-takeover')
            with stack_log_path.open('xb') as stack_output_stream:
                stack_process_handle = subprocess.Popen(stack_arguments_list, cwd=WORKFLOW_ROOT_DIRECTORY, stdin=subprocess.DEVNULL, stdout=stack_output_stream, stderr=subprocess.STDOUT, start_new_session=True, env={**os.environ, 'SLIME_MANAGEMENT_STACK_TOKEN': stack_launch_token})
            print(f'{stack_mode_name} 시작 요청 · PID={stack_process_handle.pid} · 로그={stack_log_path}', flush=True)
            wait_management_stack_endpoint(stack_process_handle, stack_url_value, stack_expected_role, stack_launch_token, stack_log_path)
            print(f'{stack_mode_name} HTTP 응답 확인: {stack_url_value}', flush=True)
    return 0
