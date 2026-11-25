"""Narrow session-bound mutation socket for MiniMax form editing."""
import json
import socket

from workflow.domains.hermes_agent.minimax_form_action import apply_requested_form_update, submit_requested_form, confirm_question_handoff

MAX_REQUEST = 40000
MAX_RESPONSE = 4096


def handle_form_connection(client, session_id, user_prompt, dispatch):
    with client:
        client.settimeout(30)
        try:
            data = b''
            while b'\n' not in data and len(data) <= MAX_REQUEST:
                chunk = client.recv(min(4096, MAX_REQUEST + 1 - len(data)))
                if not chunk: break
                data += chunk
            if len(data) > MAX_REQUEST or not data.endswith(b'\n') or data.count(b'\n') != 1:
                raise ValueError('폼 수정 요청 형식 오류')
            from workflow.common.management_gateway import parse_management_request_json
            payload = parse_management_request_json(data[:-1])
            if isinstance(payload, dict) and payload.get('operation') == 'submit':
                result = submit_requested_form(session_id, user_prompt, {key:value for key,value in payload.items() if key != 'operation'}, dispatch)
            elif isinstance(payload, dict) and payload.get('operation') == 'confirm-handoff':
                result = confirm_question_handoff(session_id, user_prompt, {key:value for key,value in payload.items() if key != 'operation'}, dispatch)
            else:
                result = apply_requested_form_update(session_id, user_prompt, payload, dispatch)
        except (OSError, RuntimeError, ValueError, TypeError, KeyError):
            result = {'error':'폼 처리 결과를 확인할 수 없습니다. 기존 접수와 현재 폼을 다시 조회하세요.'}
        encoded = json.dumps(result, ensure_ascii=False).encode('utf-8')
        if len(encoded) > MAX_RESPONSE:
            encoded = b'{"error":"response too large"}'
        try: client.sendall(encoded + b'\n')
        except OSError: pass


def serve_form_connections(listener, session_id, user_prompt, dispatch):
    while True:
        try: client, _ = listener.accept()
        except OSError: return
        handle_form_connection(client, session_id, user_prompt, dispatch)
