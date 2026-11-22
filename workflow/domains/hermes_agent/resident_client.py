"""상주 모델 작업 수명 동안 사용권을 유지하는 내부 클라이언트."""
from contextlib import contextmanager
import os
from pathlib import Path
import select
import socket
import stat
import threading


def connect_resident_socket(directory, name, *, timeout=5):
    """긴 작업 경로도 상대 소켓 경로로 연결하고 심볼릭 링크는 거부한다."""
    if name not in ('resident-lease.sock', 'resident-model.sock'):
        raise ValueError('상주 모델 소켓 이름 오류')
    directory = Path(directory)
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    client = socket.socket(socket.AF_UNIX)
    try:
        metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if not stat.S_ISSOCK(metadata.st_mode):
            raise ValueError('상주 모델 소켓 형식 오류')
        client.settimeout(timeout)
        client.connect(f'/proc/self/fd/{descriptor}/{name}')
        return client
    except BaseException:
        client.close()
        raise
    finally:
        os.close(descriptor)


@contextmanager
def hold_resident_lease(directory):
    """수락된 연결이 살아 있는 동안만 해당 대화의 GPU 사용권이 유지된다."""
    with connect_resident_socket(directory, 'resident-lease.sock') as client:
        response = b''
        while len(response) < 3:
            fragment = client.recv(3 - len(response))
            if not fragment:
                break
            response += fragment
        if response != b'OK\n':
            raise RuntimeError('상주 모델 사용권을 확인할 수 없습니다.')
        client.settimeout(None)
        yield


def _relay_resident_connection(client, directory):
    try:
        with client, connect_resident_socket(directory, 'resident-model.sock', timeout=15) as server:
            server.settimeout(None)
            while True:
                readable, _, _ = select.select([client, server], [], [], 300)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (server if source is client else client).sendall(data)
    except (OSError, ValueError):
        return


def serve_resident_model_proxy(listener, directory):
    """사용권 보유자가 격리된 대화에 제공하는 유닉스 소켓 중계기."""
    while True:
        try:
            client, _ = listener.accept()
        except OSError:
            return
        threading.Thread(target=_relay_resident_connection, args=(client, directory), daemon=True).start()
