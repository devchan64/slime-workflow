"""HY-Motion 명령과 허용된 원본·미리보기 파일만 제공하는 HTTP 어댑터."""
import json
import re
from urllib.parse import urlsplit

from tools.review.common.management_gateway import identify_management_command
from tools.review.common.management_transport import validate_management_http_request, send_management_json_response
from tools.review.domains.hy_motion.jobs import execute_hymotion_command, resolve_generation_directory, GENERATION_IDENTIFIER_PATTERN

SERVICE_ROUTE_PREFIX = '/hy-motion-generator'


def send_hymotion_bytes(current_http_handler, current_response_bytes, current_content_type):
    current_http_handler.send_response(200)
    current_http_handler.send_header('Content-Type', current_content_type)
    current_http_handler.send_header('Content-Length', str(len(current_response_bytes)))
    current_http_handler.send_header('Cache-Control', 'no-store')
    current_http_handler.end_headers()
    current_http_handler.wfile.write(current_response_bytes)


def parse_unique_fields(current_field_pairs):
    current_payload_values = {}
    for current_field_name, current_field_value in current_field_pairs:
        if current_field_name in current_payload_values:
            raise ValueError('중복 JSON 필드')
        current_payload_values[current_field_name] = current_field_value
    return current_payload_values


def handle_hymotion_request(current_http_handler):
    current_route_path = urlsplit(current_http_handler.path).path
    if not current_route_path.startswith(SERVICE_ROUTE_PREFIX + '/'):
        return False
    try:
        current_content_length = validate_management_http_request(current_http_handler)
        current_asset_match = re.fullmatch(SERVICE_ROUTE_PREFIX + r'/jobs/(' + GENERATION_IDENTIFIER_PATTERN + r')/result/(motion\.npz|provenance\.json|vnccs-package\.zip|vnccs-manifest\.json|retarget-quality\.json|(?:overview|down_left|down_right|up_left|up_right)\.gif|(?:perspective/)?(?:down_left|down_right|up_left|up_right)/frame-\d{4}(?:-rgb)?\.png)', current_route_path)
        if current_http_handler.command == 'GET' and current_asset_match:
            current_job_directory = resolve_generation_directory(current_asset_match[1])
            current_result_record = json.loads((current_job_directory / 'result.json').read_text())
            current_asset_path = current_job_directory / current_result_record['relative_path'] / current_asset_match[2]
            if not current_asset_path.resolve().is_relative_to(current_job_directory.resolve()) or current_asset_path.is_symlink():
                raise ValueError('결과 파일 경로 오류')
            current_content_type = {'.png': 'image/png', '.gif': 'image/gif', '.json': 'application/json', '.npz': 'application/octet-stream', '.zip': 'application/zip'}[current_asset_path.suffix]
            send_hymotion_bytes(current_http_handler, current_asset_path.read_bytes(), current_content_type)
            return True
        current_payload_values = json.loads(current_http_handler.rfile.read(current_content_length), object_pairs_hook=parse_unique_fields) if current_http_handler.command == 'POST' else getattr(current_http_handler, 'management_command_payload', {})
        if current_http_handler.command == 'POST' and current_http_handler.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('JSON 요청만 허용합니다.')
        current_command_match = identify_management_command(current_http_handler.path, current_http_handler.command, current_payload_values)
        if not current_command_match or current_command_match[0] != 'hy-motion':
            raise ValueError('지원하지 않는 HY-Motion 경로')
        current_command_result = execute_hymotion_command(current_command_match[1], current_command_match[2])
        if isinstance(current_command_result, str):
            send_hymotion_bytes(current_http_handler, current_command_result.encode(), 'text/plain; charset=utf-8')
        else:
            send_management_json_response(current_http_handler, 200, current_command_result)
    except (ValueError, TypeError, KeyError, OSError) as current_request_error:
        send_management_json_response(current_http_handler, 400, {'error': str(current_request_error)})
    return True
