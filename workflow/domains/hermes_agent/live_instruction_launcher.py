"""Launch the pinned one-shot CLI with a job-local live-instruction socket."""
import json
import os
from pathlib import Path
import runpy
import socket
import sys

sys.path.insert(0, '/control')
from live_instruction_runtime import LiveInstructionRuntime

CONTROL = Path('/control/live')
SOCKET = CONTROL / 'agent.sock'
RECEIPT = CONTROL / 'settled.json'
MAX_REQUEST = 40000


def serve(runtime, listener):
    while True:
        try:
            connection, _ = listener.accept()
        except OSError:
            return
        with connection:
            connection.settimeout(2)
            try:
                raw = b''
                while b'\n' not in raw and len(raw) <= MAX_REQUEST:
                    part = connection.recv(4096)
                    if not part:
                        break
                    raw += part
                if len(raw) > MAX_REQUEST or raw.count(b'\n') != 1 or not raw.endswith(b'\n'):
                    raise ValueError('지시 요청 형식 오류')
                request = json.loads(raw)
                if not isinstance(request, dict) or set(request) != {'request_id', 'mode', 'text'}:
                    raise ValueError('지시 요청 형식 오류')
                result = runtime.submit(request['request_id'], request['mode'], request['text'])
                response = {'request_id': result['request_id'], 'state': result['state']}
            except (ValueError, TypeError, KeyError, OSError):
                response = {'error': '지시 요청을 처리할 수 없습니다.'}
            try:
                connection.sendall(json.dumps(response, ensure_ascii=False).encode() + b'\n')
            except OSError:
                pass


if __name__ == '__main__':
    sys.argv = ['hermes_cli.main', *sys.argv[1:]]
    runpy.run_module('hermes_cli.main', run_name='__main__')
