"""격리 Hermes에 한정된 읽기 전용 관측만 제공한다."""
import json
import socket

from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot

HERMES_OBSERVER_REQUEST = b'gpu-queue\n'
HERMES_OBSERVER_MAX_REQUEST = 64
HERMES_OBSERVER_MAX_RESPONSE = 262144


def handle_hermes_observer_connection(current_client_socket):
    """고정된 단일 요청만 처리하며 다른 명령과 임의 입력은 거절한다."""
    with current_client_socket:
        current_client_socket.settimeout(2)
        try:
            current_request_bytes = b''
            while b'\n' not in current_request_bytes and len(current_request_bytes) <= HERMES_OBSERVER_MAX_REQUEST:
                current_next_bytes = current_client_socket.recv(HERMES_OBSERVER_MAX_REQUEST + 1 - len(current_request_bytes))
                if not current_next_bytes:
                    break
                current_request_bytes += current_next_bytes
            if current_request_bytes != HERMES_OBSERVER_REQUEST:
                current_response_record = {'error': '지원하지 않는 조회 요청'}
            else:
                current_response_record = read_hermes_management_snapshot()
            current_response_bytes = json.dumps(current_response_record, ensure_ascii=False, allow_nan=False).encode('utf-8')
            if len(current_response_bytes) > HERMES_OBSERVER_MAX_RESPONSE:
                current_response_bytes = b'{"error":"response too large"}'
            current_client_socket.sendall(current_response_bytes + b'\n')
        except (OSError, ValueError, TypeError):
            return


def serve_hermes_observer_connections(current_listener_socket):
    """작업 수명 동안 연결을 순차 처리하며 소켓이 닫히면 종료한다."""
    while True:
        try:
            current_client_socket, _ = current_listener_socket.accept()
        except OSError:
            return
        handle_hermes_observer_connection(current_client_socket)
