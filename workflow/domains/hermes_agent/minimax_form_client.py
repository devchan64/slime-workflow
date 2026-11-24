"""Fixed MiniMax form update client for the isolated Hermes worker."""
import json
import socket
import sys


def update_form(payload):
    encoded = json.dumps(payload, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(encoded) > 40000 or b'\n' in encoded:
        raise ValueError('폼 수정 요청 크기 오류')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(30)
        client.connect('/control/minimax-form.sock')
        client.sendall(encoded + b'\n')
        data = b''
        while b'\n' not in data and len(data) <= 4096:
            chunk = client.recv(4097 - len(data))
            if not chunk: break
            data += chunk
    if not data.endswith(b'\n') or len(data) > 4096:
        raise ValueError('폼 수정 응답을 확인할 수 없습니다.')
    result = json.loads(data)
    if not isinstance(result, dict) or 'error' in result:
        raise ValueError('폼 처리 결과를 확인할 수 없습니다. 기존 접수와 현재 폼을 다시 조회하세요.')
    return result


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2: raise ValueError('폼 수정 JSON 하나가 필요합니다.')
        print(json.dumps(update_form(json.loads(sys.argv[1])), ensure_ascii=False))
    except (OSError, ValueError, TypeError) as error:
        sys.exit('폼 수정 실패: ' + str(error))
