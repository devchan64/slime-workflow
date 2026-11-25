"""실제 Hermes 런타임과 격리 소켓으로 모의 모델의 문맥 정리 경로를 확인한다."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from workflow.domains.hermes_agent.worker import serve_worker_model_proxy

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / '.local/hermes-agent-runtime'
DOMAIN = ROOT / 'workflow/domains/hermes_agent'


class MockModel(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if self.path == '/apply-template':
            body = json.dumps({'prompt': json.dumps(request, ensure_ascii=False)}).encode()
            content_type = 'application/json'
        elif self.path == '/tokenize':
            body = json.dumps({'tokens': [0] * 24000}).encode()
            content_type = 'application/json'
        elif self.path == '/v1/chat/completions':
            common = {'id': 'mock', 'object': 'chat.completion.chunk', 'model': 'hermes-local'}
            chunk = {**common, 'choices': [{'index': 0, 'delta': {'role': 'assistant', 'content': '## Active Task\nUser asked: preserve task.\n## Decisions\nKeep context.'}, 'finish_reason': None}]}
            end = {**common, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]}
            body = ('data: ' + json.dumps(chunk) + '\n\ndata: ' + json.dumps(end) + '\n\ndata: [DONE]\n\n').encode()
            content_type = 'text/event-stream'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ContextSandboxTest(unittest.TestCase):
    def test_real_runtime_compresses_through_isolated_model_socket(self):
        if not shutil.which('bwrap') or not (RUNTIME / '.venv/bin/python').is_file():
            self.skipTest('bubblewrap 또는 고정 Hermes 런타임이 없습니다.')
        with tempfile.TemporaryDirectory(prefix='hermes-context-test-') as temp:
            root = Path(temp)
            (root / 'workspace').mkdir()
            exchange = root / 'exchange'; exchange.mkdir()
            messages = [{'role': 'user' if i % 2 == 0 else 'assistant', 'content': ('task sample %s ' % i) * 1000} for i in range(40)]
            (exchange / 'input.json').write_text(json.dumps({'messages': messages, 'automatic': True, 'force': True}))
            (root / 'query.txt').write_text('follow-up task')
            server = HTTPServer(('127.0.0.1', 0), MockModel)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                with socket.socket(socket.AF_UNIX) as listener:
                    listener.bind(str(root / 'model.sock')); listener.listen()
                    threading.Thread(target=serve_worker_model_proxy, args=(listener, server.server_port), daemon=True).start()
                    command = ['bwrap', '--die-with-parent', '--unshare-all', '--clearenv',
                               '--ro-bind', '/usr', '/usr', '--ro-bind', '/lib', '/lib', '--ro-bind', '/lib64', '/lib64',
                               '--ro-bind', '/etc/ssl', '/etc/ssl', '--tmpfs', '/tmp', '--dir', '/control',
                               '--ro-bind', str(RUNTIME), '/runtime', '--ro-bind', str(root / 'workspace'), '/workspace',
                               '--ro-bind', str(root / 'model.sock'), '/control/model-proxy.sock',
                               '--ro-bind', str(root / 'query.txt'), '/control/query.txt',
                               '--ro-bind', str(DOMAIN / 'sandbox_client.py'), '/control/client.py',
                               '--ro-bind', str(DOMAIN / 'context_runtime.py'), '/control/context_runtime.py',
                               '--bind', str(exchange), '/control/context', '--proc', '/proc', '--dev', '/dev',
                               '--', '/runtime/.venv/bin/python', '/control/client.py', '--context-only']
                    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'LANG': 'C.UTF-8',
                           'PYTHONPATH': '/runtime', 'HERMES_HOME': '/tmp/hermes-home', 'TERMINAL_CWD': '/workspace'}
                    completed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
                    if completed.returncode and ('No permissions to create a new namespace' in completed.stderr or 'Creating new namespace failed' in completed.stderr):
                        self.skipTest('현재 환경에서 bubblewrap 네임스페이스를 만들 수 없습니다.')
                    self.assertEqual(completed.returncode, 0, completed.stderr[-3000:])
                    result = json.loads((exchange / 'result.json').read_text())
                    self.assertEqual(result['state'], 'compressed')
                    self.assertEqual(result['threshold'], 24000)
                    self.assertLess(len(result['messages']), len(messages))
                    self.assertIn('follow-up task', result['query'])
            finally:
                server.shutdown(); server.server_close(); thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
