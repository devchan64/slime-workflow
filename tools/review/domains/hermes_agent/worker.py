"""공용 GPU 예약 내에서 격리된 Hermes 코딩 작업을 실행한다."""
import json
import hashlib
import os
from pathlib import Path
import re
import select
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.writer_agent.prepare import RUNTIME_INSTALL_ROOT, RUNTIME_SERVER_PATH, calculate_file_digest
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.hermes_model_download import HERMES_MODEL_DIRECTORY, HERMES_MODEL_FILENAME, verify_hermes_model_integrity
from tools.review.domains.hermes_agent.runtime_integrity import verify_hermes_runtime_integrity
from tools.review.domains.hermes_agent.verification import validate_hermes_verification_modules
from tools.review.domains.hermes_agent.workspace_snapshot import copy_snapshot_source_files, collect_snapshot_change_diff

HERMES_RUNTIME_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.local/hermes-agent-runtime'
HERMES_SANDBOX_CLIENT = Path(__file__).with_name('sandbox_client.py')


def build_hermes_sandbox_environment():
    """호스트 인증정보를 PID 네임스페이스 안에 상속하지 않는다."""
    return {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/tmp', 'LANG':'C.UTF-8', 'PYTHONSAFEPATH':'1', 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHONUNBUFFERED':'1'}


def wait_hermes_gpu_reservation(worker_job_directory):
    """실행기 PID가 죽어도 회수할 수 있도록 그룹 등록 후에만 GPU를 사용한다."""
    worker_reservation_value = os.environ.get('SLIME_GPU_RESERVATION_PATH')
    worker_process_token = os.environ.get('SLIME_HERMES_PROCESS_TOKEN')
    if not worker_reservation_value or not worker_process_token or not re.fullmatch(r'[0-9a-f]{32}', worker_process_token):
        raise RuntimeError('공용 GPU 대기열 예약 없이 Hermes를 실행할 수 없습니다.')
    worker_reservation_path = Path(worker_reservation_value)
    worker_start_token = Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19]
    worker_deadline_value = time.monotonic() + 20
    while time.monotonic() < worker_deadline_value:
        try:
            worker_reservation_record = json.loads(worker_reservation_path.read_text())
            if worker_reservation_record.get('path') == str(worker_job_directory) and worker_reservation_record.get('service') == 'hermes-agent' and worker_reservation_record.get('worker_pgid') == os.getpgrp() and worker_reservation_record.get('worker_start_token') == worker_start_token and worker_reservation_record.get('worker_process_token') == worker_process_token:
                return
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise RuntimeError('공용 GPU 예약에 Hermes 프로세스 그룹을 등록하지 못했습니다.')


def relay_worker_model_connection(worker_client_socket, worker_server_port):
    try:
        with worker_client_socket, socket.create_connection(('127.0.0.1', worker_server_port), timeout=15) as worker_server_socket:
            while True:
                worker_readable_sockets, _, _ = select.select([worker_client_socket, worker_server_socket], [], [], 300)
                if not worker_readable_sockets:
                    return
                for worker_read_socket in worker_readable_sockets:
                    worker_payload_bytes = worker_read_socket.recv(65536)
                    if not worker_payload_bytes:
                        return
                    (worker_server_socket if worker_read_socket is worker_client_socket else worker_client_socket).sendall(worker_payload_bytes)
    except OSError:
        return


def serve_worker_model_proxy(worker_listen_socket, worker_server_port):
    while True:
        try:
            worker_client_socket, _ = worker_listen_socket.accept()
        except OSError:
            return
        threading.Thread(target=relay_worker_model_connection, args=(worker_client_socket, worker_server_port), daemon=True).start()


def wait_worker_model_ready(worker_server_process, worker_server_port, worker_log_path):
    worker_deadline_value = time.monotonic() + 240
    while time.monotonic() < worker_deadline_value:
        if worker_server_process.poll() is not None:
            raise RuntimeError('로컬 모델 서버 시작 실패: ' + worker_log_path.read_text(errors='replace')[-2000:])
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{worker_server_port}/health', timeout=2) as worker_http_response:
                if json.load(worker_http_response).get('status') == 'ok':
                    break
        except (urllib.error.URLError, TimeoutError):
            time.sleep(1)
    else:
        raise TimeoutError('로컬 모델 서버 준비 시간 초과')
    worker_offload_match = re.search(r'offloaded (\d+)/(\d+) layers to GPU', worker_log_path.read_text(errors='replace'))
    if not worker_offload_match or worker_offload_match.group(1) != worker_offload_match.group(2):
        raise RuntimeError('모든 모델 레이어의 GPU 적재를 확인하지 못했습니다.')
    return worker_offload_match.group(0)


def stop_hermes_model_process(worker_server_process):
    worker_server_process.terminate()
    try:
        worker_server_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker_server_process.kill()
        worker_server_process.wait()


def hash_hermes_verification_controls(worker_workspace_path):
    """에이전트가 공용 회귀 실행기를 바꾸면 독립 검증으로 취급하지 않는다."""
    worker_control_hashes = {}
    for worker_control_name in ('tools/review/tests/run_management_audit.py', 'tools/review/tests/run_music_regression.py'):
        worker_control_path = worker_workspace_path
        for worker_path_part in Path(worker_control_name).parts:
            worker_control_path = worker_control_path / worker_path_part
            if worker_control_path.is_symlink():
                raise ValueError('독립 검증 실행기 경로에 심볼릭 링크가 있습니다.')
        with worker_control_path.open('rb') as worker_control_stream:
            worker_control_hashes[worker_control_name] = hashlib.file_digest(worker_control_stream, 'sha256').hexdigest()
    return worker_control_hashes


def execute_hermes_independent_verification(worker_job_directory, worker_workspace_path, worker_project_environment, worker_module_names):
    """지정된 공용 회귀 모듈만 외부망·GPU 없이 최종 사본에서 실행한다."""
    worker_module_names = validate_hermes_verification_modules(worker_module_names)
    worker_verification_arguments = ['bwrap', '--die-with-parent', '--unshare-all', '--clearenv', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--ro-bind', '/bin', '/bin', '--ro-bind', '/etc/ssl', '/etc/ssl', '--size', '2147483648', '--tmpfs', '/tmp', '--bind', str(worker_workspace_path), '/workspace', '--ro-bind', str(worker_workspace_path / '.git'), '/workspace/.git', '--ro-bind', str(worker_project_environment), '/workspace/.venv', '--proc', '/proc', '--dev', '/dev', '--chdir', '/workspace', '--setenv', 'HOME', '/tmp', '--setenv', 'PATH', '/usr/local/bin:/usr/bin:/bin', '--setenv', 'PYTHONSAFEPATH', '1', '--setenv', 'PYTHONDONTWRITEBYTECODE', '1', '--setenv', 'PYTHONUNBUFFERED', '1', '--', '/workspace/.venv/bin/python', 'tools/review/tests/run_management_audit.py']
    for worker_module_name in worker_module_names:
        worker_verification_arguments.extend(['--module', worker_module_name])
    with (worker_job_directory / 'verification.log').open('w', encoding='utf-8') as worker_verification_stream:
        try:
            worker_verification_result = subprocess.run(worker_verification_arguments, stdout=worker_verification_stream, stderr=subprocess.STDOUT, env=build_hermes_sandbox_environment(), timeout=300)
        except subprocess.TimeoutExpired:
            worker_verification_stream.write('\n독립 검증 시간 초과\n')
            return {'status':'timed_out', 'modules':worker_module_names, 'exit_code':None}
    return {'status':'passed' if worker_verification_result.returncode == 0 else 'failed', 'modules':worker_module_names, 'exit_code':worker_verification_result.returncode}


def execute_hermes_gpu_job(worker_job_directory):
    worker_job_directory = Path(worker_job_directory).resolve(strict=True)
    wait_hermes_gpu_reservation(worker_job_directory)
    worker_request_record = json.loads((worker_job_directory / 'request.json').read_text())
    worker_verification_modules = validate_hermes_verification_modules(worker_request_record.get('verification_modules', []))
    verify_hermes_model_integrity()
    worker_manifest_record = json.loads((RUNTIME_INSTALL_ROOT / 'prepared.json').read_text())
    if calculate_file_digest(RUNTIME_SERVER_PATH) != worker_manifest_record['server_binary_sha256']:
        raise RuntimeError('추론 서버 바이너리 SHA-256 불일치')
    verify_hermes_runtime_integrity(HERMES_RUNTIME_DIRECTORY)
    worker_workspace_path = worker_job_directory / 'workspace'
    worker_baseline_record = copy_snapshot_source_files(WORKFLOW_ROOT_DIRECTORY, worker_workspace_path)
    worker_project_environment = WORKFLOW_ROOT_DIRECTORY / '.venv'
    if worker_project_environment.is_symlink() or not (worker_project_environment / 'bin/python').is_file():
        raise ValueError('관리도구의 읽기 전용 Python 환경을 찾을 수 없습니다.')
    (worker_workspace_path / '.venv').mkdir()
    write_record_atomically(worker_job_directory / 'baseline.json', worker_baseline_record)
    worker_control_hashes = hash_hermes_verification_controls(worker_workspace_path) if worker_verification_modules else {}
    (worker_job_directory / 'query.txt').write_text(worker_request_record['prompt'], encoding='utf-8')
    with socket.socket() as worker_port_socket:
        worker_port_socket.bind(('127.0.0.1', 0))
        worker_server_port = worker_port_socket.getsockname()[1]
    worker_server_arguments = [str(RUNTIME_SERVER_PATH), '-m', str(HERMES_MODEL_DIRECTORY / HERMES_MODEL_FILENAME), '--alias', 'hermes-local', '--host', '127.0.0.1', '--port', str(worker_server_port), '-ngl', 'all', '--fit', 'off', '-c', '64000', '-np', '1', '-b', '256', '-ub', '128', '--jinja', '--no-context-shift', '--verbosity', '4']
    worker_environment_values = dict(os.environ, LD_LIBRARY_PATH=':'.join(worker_manifest_record['runtime_library_paths']), HIP_VISIBLE_DEVICES='0')
    worker_log_path = worker_job_directory / 'server.log'
    worker_socket_path = worker_job_directory / 'model-proxy.sock'
    worker_offload_value = None
    worker_agent_exit_code = None
    worker_verification_record = {'status':'not_run' if worker_verification_modules else 'not_requested', 'modules':worker_verification_modules, 'exit_code':None}
    with worker_log_path.open('w', encoding='utf-8') as worker_log_stream:
        worker_server_process = subprocess.Popen(worker_server_arguments, stdout=worker_log_stream, stderr=subprocess.STDOUT, env=worker_environment_values)
        try:
            worker_offload_value = wait_worker_model_ready(worker_server_process, worker_server_port, worker_log_path)
            with socket.socket(socket.AF_UNIX) as worker_listen_socket:
                os.chdir(worker_job_directory)
                worker_listen_socket.bind('model-proxy.sock')
                worker_listen_socket.listen()
                threading.Thread(target=serve_worker_model_proxy, args=(worker_listen_socket, worker_server_port), daemon=True).start()
                worker_sandbox_arguments = ['bwrap', '--die-with-parent', '--unshare-all', '--clearenv', '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64', '--ro-bind', '/bin', '/bin', '--ro-bind', '/etc/ssl', '/etc/ssl', '--size', '2147483648', '--tmpfs', '/tmp', '--dir', '/control', '--ro-bind', str(HERMES_RUNTIME_DIRECTORY), '/runtime', '--bind', str(worker_workspace_path), '/workspace', '--ro-bind', str(worker_workspace_path / '.git'), '/workspace/.git', '--ro-bind', str(worker_project_environment), '/workspace/.venv', '--ro-bind', str(worker_socket_path), '/control/model-proxy.sock', '--ro-bind', str(worker_job_directory / 'query.txt'), '/control/query.txt', '--ro-bind', str(HERMES_SANDBOX_CLIENT), '/control/client.py', '--proc', '/proc', '--dev', '/dev', '--', '/runtime/.venv/bin/python', '/control/client.py']
                with (worker_job_directory / 'hermes-events.jsonl').open('w') as worker_event_stream:
                    worker_sandbox_process = subprocess.Popen(worker_sandbox_arguments, stdout=worker_event_stream, env=build_hermes_sandbox_environment())
                    try:
                        worker_agent_exit_code = worker_sandbox_process.wait(timeout=1250)
                    except BaseException:
                        worker_sandbox_process.terminate()
                        try:
                            worker_sandbox_process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            worker_sandbox_process.kill()
                            worker_sandbox_process.wait()
                        raise
            if worker_agent_exit_code:
                raise RuntimeError(f'Hermes 작업 실패: 종료 코드 {worker_agent_exit_code}')
            if worker_verification_record['modules']:
                stop_hermes_model_process(worker_server_process)
                try:
                    worker_controls_unchanged = hash_hermes_verification_controls(worker_workspace_path) == worker_control_hashes
                except (OSError, ValueError):
                    worker_controls_unchanged = False
                if not worker_controls_unchanged:
                    worker_verification_record = {'status':'failed', 'modules':worker_verification_modules, 'exit_code':None, 'reason':'공용 회귀 실행기가 변경됐습니다.'}
                    (worker_job_directory / 'verification.log').write_text('공용 회귀 실행기가 변경되어 독립 검증을 실행하지 않았습니다.\n')
                    raise RuntimeError('공용 회귀 실행기가 변경되어 독립 검증을 실행할 수 없습니다.')
                worker_verification_record = execute_hermes_independent_verification(worker_job_directory, worker_workspace_path, worker_project_environment, worker_verification_record['modules'])
                if worker_verification_record['status'] != 'passed':
                    raise RuntimeError('최종 독립 회귀 검증에 실패했습니다. verification.log를 확인하세요.')
        finally:
            stop_hermes_model_process(worker_server_process)
            worker_diff_bytes = collect_snapshot_change_diff(worker_workspace_path, worker_baseline_record['baseline_commit'])
            (worker_job_directory / 'change.diff').write_bytes(worker_diff_bytes)
            write_record_atomically(worker_job_directory / 'result.json', {'agent_exit_code':worker_agent_exit_code, 'gpu_offload':worker_offload_value, 'baseline':worker_baseline_record, 'diff_bytes':len(worker_diff_bytes), 'verification':worker_verification_record, 'partial':worker_agent_exit_code != 0 or worker_verification_record['status'] in ('not_run', 'failed', 'timed_out')})


def interrupt_hermes_gpu_job(worker_signal_number, worker_signal_frame):
    raise KeyboardInterrupt('Hermes 작업이 중지되었습니다.')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, interrupt_hermes_gpu_job)
    execute_hermes_gpu_job(sys.argv[1])
