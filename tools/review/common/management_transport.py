"""GUI의 동일 출처 API 중계. 작업 서비스를 가져오거나 실행하지 않는다."""
import http.client
import json
from urllib.parse import urlsplit

from tools.review.common.management_environment import validate_gateway_address
MAXIMUM_GATEWAY_BODY_BYTES = 40_200_000
GATEWAY_REQUEST_TIMEOUT_SECONDS = 30
GATEWAY_CONTROL_ROUTE_PATHS = (
    '/management/command', '/management/gpu-queue', '/management/gpu-status',
    '/management/record-folder/open', '/management/health',
)
PROXY_REMOVED_HEADER_NAMES = frozenset((
    'host', 'origin', 'connection', 'transfer-encoding', 'content-length',
    'proxy-connection', 'keep-alive', 'te', 'trailer', 'upgrade',
))


def is_management_runtime_request(request_path_value):
    from tools.review.common.management_gateway import MANAGEMENT_SERVICE_ROUTES
    request_route_path = urlsplit(request_path_value).path
    service_route_prefixes = tuple(service_route_value + '/' for service_route_value in MANAGEMENT_SERVICE_ROUTES.values()) + ('/writer-agent/',)
    return (request_route_path in GATEWAY_CONTROL_ROUTE_PATHS
            or request_route_path.startswith(service_route_prefixes))


def send_management_json_response(current_http_handler, response_status_code, response_record_values):
    response_payload_bytes = json.dumps(response_record_values, ensure_ascii=False).encode()
    current_http_handler.send_response(response_status_code)
    current_http_handler.send_header('Content-Type', 'application/json; charset=utf-8')
    current_http_handler.send_header('Content-Length', str(len(response_payload_bytes)))
    current_http_handler.send_header('Cache-Control', 'no-store')
    current_http_handler.end_headers()
    current_http_handler.wfile.write(response_payload_bytes)


def validate_management_http_request(current_http_handler):
    expected_origin_value = f'http://127.0.0.1:{current_http_handler.server.server_port}'
    if current_http_handler.headers.get('Host') != expected_origin_value.removeprefix('http://'):
        raise ValueError('허용하지 않는 Host')
    if current_http_handler.headers.get('Transfer-Encoding'):
        raise ValueError('Transfer-Encoding 요청은 허용하지 않습니다.')
    request_content_length = int(current_http_handler.headers.get('Content-Length', '0'))
    if current_http_handler.command == 'POST':
        if current_http_handler.headers.get('Origin') != expected_origin_value:
            raise ValueError('동일 출처 요청만 허용합니다.')
        if not 0 < request_content_length <= MAXIMUM_GATEWAY_BODY_BYTES:
            raise ValueError('요청 크기 오류')
    elif request_content_length:
        raise ValueError('조회 요청에는 본문을 보낼 수 없습니다.')
    return request_content_length


def proxy_management_request(current_http_handler, gateway_base_address):
    if not is_management_runtime_request(current_http_handler.path):
        return False
    try:
        validate_gateway_address(gateway_base_address)
        request_content_length = validate_management_http_request(current_http_handler)
    except ValueError as request_validation_error:
        send_management_json_response(current_http_handler, 400, {'error': str(request_validation_error)})
        return True
    gateway_url_parts = urlsplit(gateway_base_address)
    request_body_bytes = current_http_handler.rfile.read(request_content_length) if request_content_length else None
    request_header_values = {
        header_field_name: header_field_value
        for header_field_name, header_field_value in current_http_handler.headers.items()
        if header_field_name.lower() not in PROXY_REMOVED_HEADER_NAMES
        and not header_field_name.lower().startswith('x-forwarded-')
    }
    request_header_values['Host'] = gateway_url_parts.netloc
    if current_http_handler.command == 'POST':
        request_header_values['Origin'] = gateway_base_address
    gateway_connection_value = http.client.HTTPConnection(
        gateway_url_parts.hostname, gateway_url_parts.port, timeout=GATEWAY_REQUEST_TIMEOUT_SECONDS)
    try:
        gateway_connection_value.request(current_http_handler.command, current_http_handler.path,
                                         body=request_body_bytes, headers=request_header_values)
        gateway_response_value = gateway_connection_value.getresponse()
        response_payload_bytes = gateway_response_value.read()
    except (OSError, http.client.HTTPException) as gateway_connection_error:
        # 접수 여부가 불명확한 명령을 재전송하면 중복 작업이 생긴다. 자동 재시도하지 않는다.
        send_management_json_response(current_http_handler, 502, {
            'error': f'독립 게이트웨이 연결 실패: {gateway_base_address}. 상태를 확인하세요.',
            'detail': str(gateway_connection_error),
        })
        return True
    finally:
        gateway_connection_value.close()
    current_http_handler.send_response(gateway_response_value.status)
    for header_field_name, header_field_value in gateway_response_value.getheaders():
        if header_field_name.lower() not in PROXY_REMOVED_HEADER_NAMES:
            current_http_handler.send_header(header_field_name, header_field_value)
    current_http_handler.send_header('Content-Length', str(len(response_payload_bytes)))
    current_http_handler.end_headers()
    try:
        current_http_handler.wfile.write(response_payload_bytes)
    except (BrokenPipeError, ConnectionResetError):
        pass
    return True
