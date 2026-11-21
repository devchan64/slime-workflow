"""격리 네트워크에서 로컬 추론 소켓만 Hermes에 연결한다."""
import os
import json
import select
import socket
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path


CONTEXT_FILE_MAX_CHARS = 40000


def configure_sandbox_home(home=Path('/tmp/hermes-home')):
    """호스트 설정을 상속하지 않고 문맥 준비와 실행에 동일한 한도를 쓴다."""
    home.mkdir(parents=True, exist_ok=True)
    (home / 'config.yaml').write_text(f'context_file_max_chars: {CONTEXT_FILE_MAX_CHARS}\n', encoding='utf-8')


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


def post_model_json(base_url, route, data):
    payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(base_url + route, data=payload,
                                     headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def count_model_tokens(base_url, prompt, system_prompt, tools):
    rendered = post_model_json(base_url, '/apply-template', {'messages': [
        {'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': prompt}], 'tools': tools})
    if not isinstance(rendered, dict) or not isinstance(rendered.get('prompt'), str):
        raise ValueError('모델 대화 템플릿을 확인할 수 없습니다.')
    result = post_model_json(base_url, '/tokenize', {'content': rendered['prompt'], 'add_special': True})
    if not isinstance(result, dict) or not isinstance(result.get('tokens'), list):
        raise ValueError('모델 토큰 수를 확인할 수 없습니다.')
    return len(result['tokens'])


def prepare_sandbox_context(port):
    directory = Path('/control/context')
    if not directory.is_dir():
        return '/control/query.txt'
    # The bridge supplies a private copy of the session snapshot, never the session store itself.
    os.environ.update({'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp',
                       'HERMES_HOME': '/tmp/hermes-home', 'TERMINAL_CWD': '/workspace',
                       'PYTHONPATH': '/runtime', 'PYTHONUNBUFFERED': '1', 'HERMES_API_TIMEOUT': '300'})
    sys.path.insert(0, '/runtime')
    sys.path.insert(0, '/control')
    from context_runtime import prepare_context_request
    with (directory / 'input.json').open(encoding='utf-8') as stream:
        context = json.load(stream)
    query = Path('/control/query.txt').read_text(encoding='utf-8')
    base_url = f'http://127.0.0.1:{port}'
    from run_agent import AIAgent
    agent = AIAgent(model='hermes-local', provider='custom', base_url=base_url + '/v1', api_key='none',
                    max_iterations=20, enabled_toolsets=['terminal', 'file'], quiet_mode=True, platform='cli')
    try:
        system_prompt, tools = agent._build_system_prompt(None), agent.tools
    finally:
        agent.close()
    def progress(value):
        temporary = directory / 'progress.tmp'
        temporary.write_text(json.dumps(value), encoding='utf-8')
        temporary.replace(directory / 'progress.json')
    result = prepare_context_request(context['messages'], query, lambda text: count_model_tokens(base_url, text, system_prompt, tools),
                                     base_url + '/v1', automatic=context['automatic'], force=context.get('force', False), on_progress=progress)
    Path('/tmp/hermes-context-query.txt').write_text(result['query'], encoding='utf-8')
    with (directory / 'result.json').open('w', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False)
    return '/tmp/hermes-context-query.txt'


def execute_sandbox_hermes_session():
    configure_sandbox_home()
    with socket.socket() as sandbox_listen_socket:
        sandbox_listen_socket.bind(('127.0.0.1', 0))
        sandbox_listen_socket.listen()
        sandbox_listen_port = sandbox_listen_socket.getsockname()[1]
        threading.Thread(target=serve_sandbox_model_proxy, args=(sandbox_listen_socket,), daemon=True).start()
        query_path = prepare_sandbox_context(sandbox_listen_port)
        if '--context-only' in sys.argv:
            return 0
        sandbox_environment_values = {'PATH':'/usr/local/bin:/usr/bin:/bin', 'HOME':'/tmp', 'HERMES_HOME':'/tmp/hermes-home', 'TERMINAL_CWD':'/workspace', 'PYTHONPATH':'/control:/runtime', 'PYTHONUNBUFFERED':'1', 'HERMES_API_TIMEOUT':'300'}
        sandbox_hermes_arguments = ['/runtime/.venv/bin/python', '/control/live_instruction_launcher.py', 'chat', '--oneshot', '--query-file', query_path, '--format', 'stream-json', '--provider', 'custom', '--base-url', f'http://127.0.0.1:{sandbox_listen_port}/v1', '--api-key', 'none', '--model', 'hermes-local', '--max-turns', '20', '--toolsets', 'terminal,file', '--ignore-user-config', '--in', '/workspace', '--source', 'tool']
        return subprocess.run(sandbox_hermes_arguments, env=sandbox_environment_values, cwd='/workspace', timeout=1200).returncode


if __name__ == '__main__':
    sys.exit(execute_sandbox_hermes_session())
