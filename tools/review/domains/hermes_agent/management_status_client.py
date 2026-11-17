"""격리된 Hermes의 고정 관리 상태 조회 명령."""
import json
import socket
import sys

HERMES_OBSERVER_MAX_RESPONSE = 262144


def read_sandbox_management_status():
    """고정 소켓과 고정 요청만 사용한다."""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as current_client_socket:
        current_client_socket.settimeout(30)
        current_client_socket.connect('/control/management-status.sock')
        current_client_socket.sendall(b'gpu-queue\n')
        current_response_bytes = b''
        while b'\n' not in current_response_bytes and len(current_response_bytes) <= HERMES_OBSERVER_MAX_RESPONSE:
            current_next_bytes = current_client_socket.recv(min(65536, HERMES_OBSERVER_MAX_RESPONSE + 1 - len(current_response_bytes)))
            if not current_next_bytes:
                break
            current_response_bytes += current_next_bytes
        if len(current_response_bytes) > HERMES_OBSERVER_MAX_RESPONSE or not current_response_bytes.endswith(b'\n'):
            raise ValueError('관리 상태 응답 크기 또는 종료 형식 오류')
        current_response_record = json.loads(current_response_bytes)
        if not isinstance(current_response_record, dict) or 'error' in current_response_record:
            raise ValueError('관리 상태 조회가 거절됐습니다.')
        return current_response_record


if __name__ == '__main__':
    if len(sys.argv) != 1:
        sys.exit('관리 상태 조회는 인자를 받지 않습니다.')
    try:
        print(json.dumps(read_sandbox_management_status(), ensure_ascii=False))
    except (OSError, ValueError, TypeError) as current_observer_error:
        sys.exit('관리 상태 조회 실패: ' + str(current_observer_error))
