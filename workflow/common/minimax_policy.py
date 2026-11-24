"""실행 중인 게이트웨이의 헤르메스 MiniMax 우선 정책을 조회한다."""
import json
import os
from urllib.request import ProxyHandler, build_opener
from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address


def read_minimax_preference():
    """조회 실패나 구형 게이트웨이는 None으로 구분한다."""
    try:
        address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        with build_opener(ProxyHandler({})).open(address + '/management/health', timeout=2) as response:
            record = json.loads(response.read(4096))
        value = record.get('minimax_preferred') if record.get('role') == 'management-gateway' else None
        return value if type(value) is bool else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None
