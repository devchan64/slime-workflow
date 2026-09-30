"""서버·UI·실행기가 공유하는 경로와 로컬 접속 설정. 서비스 실행 의존성이 없다."""
import os
from pathlib import Path
from urllib.parse import urlsplit

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
GATEWAY_SERVER_HOST = '127.0.0.1'
GATEWAY_SERVER_PORT = 8771
DEFAULT_GATEWAY_ADDRESS = f'http://{GATEWAY_SERVER_HOST}:{GATEWAY_SERVER_PORT}'


def resolve_management_environment(environment_variable_name, default_directory_name):
    selected_directory_path = Path(os.environ.get(environment_variable_name, str(WORKFLOW_ROOT_DIRECTORY/default_directory_name))).expanduser()
    if not selected_directory_path.is_absolute():
        selected_directory_path = WORKFLOW_ROOT_DIRECTORY/selected_directory_path
    return selected_directory_path.absolute()


def validate_gateway_address(gateway_base_address):
    gateway_url_parts = urlsplit(gateway_base_address)
    if (gateway_url_parts.scheme != 'http' or gateway_url_parts.hostname != '127.0.0.1'
            or gateway_url_parts.username or gateway_url_parts.password
            or gateway_url_parts.path or gateway_url_parts.query or gateway_url_parts.fragment
            or gateway_url_parts.port is None or not 1024 <= gateway_url_parts.port <= 65535):
        raise ValueError('게이트웨이는 http://127.0.0.1:<1024~65535 포트>로 지정하세요.')
    return gateway_base_address
