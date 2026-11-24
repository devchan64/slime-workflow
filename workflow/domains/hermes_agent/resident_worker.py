"""공용 GPU 예약에서 3.8 서버를 유지하고 연결이 끝난 뒤 안전하게 내린다.

이 작업자는 아직 서비스 접수나 대화 경로에 연결되지 않았다. 작업 디렉터리와
release 요청의 소유권은 호출 측에서 검증해야 한다.
"""
import json
import os
from pathlib import Path
import re
import select
import socket
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from workflow.common.generation_records import write_record_atomically
from workflow.common.model_prepare_process import hold_hermes_model_usage_guard
from workflow.domains.hermes_agent import worker


def _release_requested(path, token):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024:
            return False
        request = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return False
    return request == {'token': token}


def _run_proxy(server_process, port, directory, token, offload):
    """연결 접수를 중지하고 이미 접수된 연결이 끝난 뒤 반환한다."""
    state_path = directory / 'resident-status.json'
    lock = threading.Lock()
    state = {'active': 0, 'leases': 0}

    def publish(status):
        write_record_atomically(state_path, {'status': status, 'model': 'qwen3.8-27b',
            'worker_pid': os.getpid(), 'server_pid': server_process.pid, 'offload': offload})

    def relay(client):
        try:
            worker.relay_worker_model_connection(client, port)
        finally:
            with lock:
                state['active'] -= 1

    def hold_lease(client):
        try:
            with client:
                client.sendall(b'OK\n')
                while client.recv(1024):
                    pass
        except OSError:
            pass
        finally:
            with lock:
                state['leases'] -= 1

    # Linux Unix socket paths are limited to 108 bytes; this process owns its cwd.
    os.chdir(directory)
    with socket.socket(socket.AF_UNIX) as listener, socket.socket(socket.AF_UNIX) as lease_listener:
        listener.bind('resident-model.sock')
        os.chmod('resident-model.sock', 0o600)
        listener.listen(8)
        lease_listener.bind('resident-lease.sock')
        os.chmod('resident-lease.sock', 0o600)
        lease_listener.listen(8)
        draining = False
        publish('ready')
        while True:
            if server_process.poll() is not None:
                raise RuntimeError('상주 모델 서버가 예기치 않게 종료되었습니다.')
            if not draining and _release_requested(directory / 'release.request', token):
                draining = True
                lease_listener.close()
                publish('draining')
            if draining:
                with lock:
                    if not state['active'] and not state['leases']:
                        return
            readable, _, _ = select.select([listener] if draining else [listener, lease_listener], [], [], .2)
            for ready_listener in readable:
                client, _ = ready_listener.accept()
                if ready_listener is lease_listener:
                    with lock:
                        state['leases'] += 1
                    threading.Thread(target=hold_lease, args=(client,), daemon=True).start()
                else:
                    with lock:
                        # 해제 중에는 기존 대화의 사용권이 있어야 새 추론 연결을 받는다.
                        if draining and not state['leases']:
                            client.close()
                            continue
                        state['active'] += 1
                    threading.Thread(target=relay, args=(client,), daemon=True).start()


def run_resident_worker(job_directory):
    directory = Path(job_directory).resolve(strict=True)
    request_path = directory / 'request.json'
    if request_path.is_symlink() or request_path.stat().st_size > 4096:
        raise ValueError('상주 모델 요청 형식 오류')
    request = json.loads(request_path.read_text(encoding='utf-8'))
    token = request.get('release_token') if isinstance(request, dict) else None
    if (not isinstance(request, dict) or request.get('model_profile') != 'qwen3.8-27b'
            or not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{32}', token)):
        raise ValueError('상주 모델 요청 형식 오류')
    worker.wait_hermes_gpu_reservation(directory)
    with hold_hermes_model_usage_guard(ROOT, inference=True):
        if not os.access('/dev/kfd', os.R_OK | os.W_OK) or not any(os.access(path, os.R_OK | os.W_OK) for path in Path('/dev/dri').glob('renderD*')):
            raise RuntimeError('ROCm GPU 장치에 접근할 수 없습니다. CPU 모델 적재를 시작하지 않습니다.')
        worker.verify_hermes_model_integrity()
        worker.verify_hermes_runtime_integrity(worker.HERMES_RUNTIME_DIRECTORY)
        manifest = json.loads((worker.RUNTIME_INSTALL_ROOT / 'prepared.json').read_text())
        if worker.calculate_file_digest(worker.RUNTIME_SERVER_PATH) != manifest['server_binary_sha256']:
            raise RuntimeError('추론 서버 바이너리 SHA-256 불일치')
        with socket.socket() as port_socket:
            port_socket.bind(('127.0.0.1', 0))
            port = port_socket.getsockname()[1]
        arguments = [str(worker.RUNTIME_SERVER_PATH), '-m', str(worker.current_hermes_model_directory() / worker.HERMES_MODEL_FILENAME),
                     '--alias', 'hermes-local', '--host', '127.0.0.1', '--port', str(port), '-ngl', 'all',
                     '--fit', 'off', '-c', '64000', '-np', '1', '-b', '256', '-ub', '128',
                     '--jinja', '--no-context-shift', '--verbosity', '4']
        runtime_temp_directory = ROOT / '.tmp' / 'hermes-resident-runtime-tmp'
        if runtime_temp_directory.is_symlink():
            raise ValueError('상주 모델 임시 디렉터리 오류')
        runtime_temp_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not runtime_temp_directory.is_dir() or runtime_temp_directory.stat().st_uid != os.geteuid():
            raise ValueError('상주 모델 임시 디렉터리 소유권 오류')
        environment = dict(os.environ, LD_LIBRARY_PATH=':'.join([str(worker.RUNTIME_SERVER_PATH.parent), *manifest['runtime_library_paths']]), HIP_VISIBLE_DEVICES='0', TMPDIR=str(runtime_temp_directory))
        server = None
        try:
            write_record_atomically(directory / 'resident-status.json', {'status':'loading', 'model':'qwen3.8-27b', 'worker_pid':os.getpid()})
            with (directory / 'server.log').open('w', encoding='utf-8') as log:
                server = subprocess.Popen(arguments, stdout=log, stderr=subprocess.STDOUT, env=environment)
                offload = worker.wait_worker_model_ready(server, port, directory / 'server.log')
                _run_proxy(server, port, directory, token, offload)
            worker.stop_hermes_model_process(server)
            server = None
            write_record_atomically(directory / 'resident-status.json', {'status':'stopped', 'model':'qwen3.8-27b', 'worker_pid':os.getpid()})
        except BaseException:
            write_record_atomically(directory / 'resident-status.json', {'status':'failed', 'model':'qwen3.8-27b', 'worker_pid':os.getpid()})
            raise
        finally:
            if server is not None:
                worker.stop_hermes_model_process(server)
            (directory / 'resident-model.sock').unlink(missing_ok=True)
            (directory / 'resident-lease.sock').unlink(missing_ok=True)


if __name__ == '__main__':
    run_resident_worker(sys.argv[1])
