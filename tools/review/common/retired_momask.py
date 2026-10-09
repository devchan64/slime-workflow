"""폐기된 MoMask 주소를 차단한다. 작업 저장소에는 접근하지 않는다."""
import json
from urllib.parse import urlsplit

RETIRED_MOMASK_MESSAGE = 'MoMask 포즈 생성기와 과거 기록은 폐기되었습니다. HY-Motion을 사용하세요.'


def reject_retired_record_access(generation_record_identifier):
    raise ValueError(RETIRED_MOMASK_MESSAGE)


class RetiredMoMaskHandler:
    def handle(self, current_http_handler):
        current_request_path = urlsplit(current_http_handler.path).path
        if current_request_path != '/momask-generator' and not current_request_path.startswith('/momask-generator/'):
            return False
        current_response_status = 410
        current_response_message = RETIRED_MOMASK_MESSAGE
        if current_http_handler.headers.get('Host') != f'127.0.0.1:{current_http_handler.server.server_port}':
            current_response_status = 400
            current_response_message = '허용하지 않는 Host'
        current_response_bytes = json.dumps({'error': current_response_message}, ensure_ascii=False).encode()
        current_http_handler.send_response(current_response_status)
        current_http_handler.send_header('Content-Type', 'application/json; charset=utf-8')
        current_http_handler.send_header('Content-Length', str(len(current_response_bytes)))
        current_http_handler.send_header('Cache-Control', 'no-store')
        current_http_handler.end_headers()
        current_http_handler.wfile.write(current_response_bytes)
        return True
