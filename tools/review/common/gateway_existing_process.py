"""스크립트 시작 시 기존 게이트웨이를 확인하고 사용자 동의 후 종료한다."""
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time
from urllib.request import urlopen

GATEWAY_SHUTDOWN_TIMEOUT = 20


def confirm_existing_gateway(server_port_number, workflow_root_directory, launcher_trace_logger):
    try:
        with socket.create_connection(('127.0.0.1', server_port_number), timeout=1):
            pass
    except ConnectionRefusedError:
        return True
    with urlopen(f'http://127.0.0.1:{server_port_number}/management/health', timeout=3) as gateway_health_response:
        gateway_health_record = json.load(gateway_health_response)
    existing_gateway_pid = gateway_health_record.get('pid')
    if gateway_health_record.get('role') != 'management-gateway' or type(existing_gateway_pid) is not int or existing_gateway_pid <= 1:
        raise ValueError('포트 점유자가 관리 게이트웨이인지 확인할 수 없습니다. 자동 종료하지 않습니다.')
    existing_process_path = Path(f'/proc/{existing_gateway_pid}')
    existing_command_bytes = (existing_process_path / 'cmdline').read_bytes()
    expected_script_bytes = str(workflow_root_directory / 'tools/review/gateway_server.py').encode()
    if existing_process_path.stat().st_uid != os.getuid() or expected_script_bytes not in existing_command_bytes.split(b'\0'):
        raise ValueError('같은 사용자·저장소의 게이트웨이가 아닙니다. 종료하지 않습니다.')
    launcher_trace_logger.emit_launch_trace('existing', f'port={server_port_number} pid={existing_gateway_pid}')
    if not sys.stdin.isatty():
        raise ValueError('기존 게이트웨이가 실행 중입니다. 대화형 터미널에서 다시 실행해 종료 여부를 선택하세요.')
    selected_answer_text = input(f'기존 게이트웨이(PID {existing_gateway_pid})를 종료하고 다시 시작할까요? 작가 작업은 종료될 수 있으며 별도 GPU 작업은 유지됩니다. [y/N] ')
    if selected_answer_text.strip().lower() not in ('y', 'yes'):
        launcher_trace_logger.emit_launch_trace('keep', '기존 게이트웨이 유지 · 새 실행 취소')
        return False
    # 확인 중 PID 재사용이나 실행 파일 변경이 발생하면 중단한다.
    if (existing_process_path / 'cmdline').read_bytes() != existing_command_bytes:
        raise ValueError('확인 중 기존 프로세스가 변경되었습니다. 다시 실행하세요.')
    os.kill(existing_gateway_pid, signal.SIGTERM)
    shutdown_deadline_time = time.monotonic() + GATEWAY_SHUTDOWN_TIMEOUT
    next_heartbeat_time = time.monotonic()
    while time.monotonic() < shutdown_deadline_time:
        try:
            with socket.create_connection(('127.0.0.1', server_port_number), timeout=1):
                pass
        except ConnectionRefusedError:
            launcher_trace_logger.emit_launch_trace('released', f'port={server_port_number} 기존 게이트웨이 종료 확인')
            return True
        if time.monotonic() >= next_heartbeat_time:
            launcher_trace_logger.emit_launch_trace('heartbeat', '기존 게이트웨이 포트 해제 대기')
            next_heartbeat_time = time.monotonic() + 5
        time.sleep(.2)
    raise TimeoutError('기존 게이트웨이가 20초 안에 포트를 해제하지 않았습니다. 강제 종료하지 않습니다.')
