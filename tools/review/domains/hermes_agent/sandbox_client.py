"""격리 네트워크에서 로컬 추론 소켓만 Hermes에 연결한다."""
import os
import select
import socket
import subprocess
import sys
import threading


def relay_sandbox_model_connection(sandbox_client_socket):
    try:
        with sandbox_client_socket, socket.socket(socket.AF_UNIX) as sandbox_server_socket:
            sandbox_server_socket.connect('/control/model-proxy.sock')
            while True:
                sandbox_readable_sockets, _, _ = select.select([sandbox_client_socket, sandbox_server_socket], [], [], 300)
                if not sandbox_readable_sockets:
                    return
                for sandbox_read_socket in sandbox_readable_sockets:
                    sandbox_payload_bytes = sandbox_read_socket.recv(65536)
                    if not sandbox_payload_bytes:
                        return
                    (sandbox_server_socket if sandbox_read_socket is sandbox_client_socket else sandbox_client_socket).sendall(sandbox_payload_bytes)
    except OSError:
        return


def serve_sandbox_model_proxy(sandbox_listen_socket):
    while True:
        try:
            sandbox_client_socket, _ = sandbox_listen_socket.accept()
        except OSError:
            return
        threading.Thread(target=relay_sandbox_model_connection, args=(sandbox_client_socket,), daemon=True).start()


def execute_sandbox_hermes_session():
    with socket.socket() as sandbox_listen_socket:
        sandbox_listen_socket.bind(('127.0.0.1', 0))
        sandbox_listen_socket.listen()
        sandbox_listen_port = sandbox_listen_socket.getsockname()[1]
        threading.Thread(target=serve_sandbox_model_proxy, args=(sandbox_listen_socket,), daemon=True).start()
        sandbox_environment_values = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/tmp', 'HERMES_HOME':'/tmp/hermes-home', 'TERMINAL_CWD':'/workspace', 'PYTHONPATH':'/runtime', 'PYTHONUNBUFFERED':'1', 'HERMES_API_TIMEOUT':'300'}
        sandbox_hermes_arguments = ['/runtime/.venv/bin/python', '-m', 'hermes_cli.main', 'chat', '--oneshot', '--query-file', '/control/query.txt', '--format', 'stream-json', '--provider', 'custom', '--base-url', f'http://127.0.0.1:{sandbox_listen_port}/v1', '--api-key', 'none', '--model', 'hermes-local', '--max-turns', '20', '--toolsets', 'terminal,file', '--ignore-user-config', '--in', '/workspace', '--source', 'tool']
        return subprocess.run(sandbox_hermes_arguments, env=sandbox_environment_values, cwd='/workspace', timeout=1200).returncode


if __name__ == '__main__':
    sys.exit(execute_sandbox_hermes_session())
