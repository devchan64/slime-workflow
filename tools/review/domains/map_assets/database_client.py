"""관리 게이트웨이에서만 사용하는 백엔드 콘텐츠 HTTP 클라이언트."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

CONTENT_REQUEST_TIMEOUT_SECONDS = 20
CONTENT_RESPONSE_MAXIMUM_BYTES = 32 * 1024 * 1024


class RejectContentServiceRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def execute_content_api_request(current_http_method,current_relative_route,current_request_payload=None):
    current_service_origin=os.environ.get('SLIME_CONTENT_SERVICE_ORIGIN','')
    current_origin_parts=urlsplit(current_service_origin)
    if (current_origin_parts.scheme not in ('http','https') or not current_origin_parts.hostname
            or current_origin_parts.username or current_origin_parts.password
            or current_origin_parts.path not in ('','/') or current_origin_parts.query or current_origin_parts.fragment):
        raise ValueError('SLIME_CONTENT_SERVICE_ORIGIN에 콘텐츠 API origin을 지정하세요.')
    if current_origin_parts.scheme=='http' and current_origin_parts.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('외부 콘텐츠 API에는 HTTPS가 필요합니다.')
    if not current_relative_route.startswith('/internal/v1/content/'):
        raise ValueError('허용되지 않은 콘텐츠 API 경로입니다.')
    current_secret_path=os.environ.get('SLIME_CONTENT_SERVICE_SECRET_FILE')
    if not current_secret_path:
        raise ValueError('SLIME_CONTENT_SERVICE_SECRET_FILE 설정이 필요합니다.')
    current_service_secret=Path(current_secret_path).read_text().strip()
    if not current_service_secret or '\n' in current_service_secret or '\r' in current_service_secret:
        raise ValueError('콘텐츠 서비스 인증 파일이 올바르지 않습니다.')
    current_request_bytes=None if current_request_payload is None else json.dumps(current_request_payload,allow_nan=False).encode()
    current_http_request=Request(current_service_origin.rstrip('/')+current_relative_route,data=current_request_bytes,
        method=current_http_method,headers={'Authorization':'Bearer '+current_service_secret,'Content-Type':'application/json'})
    try:
        with build_opener(RejectContentServiceRedirect()).open(current_http_request,timeout=CONTENT_REQUEST_TIMEOUT_SECONDS) as current_http_response:
            current_response_bytes=current_http_response.read(CONTENT_RESPONSE_MAXIMUM_BYTES+1)
        if len(current_response_bytes)>CONTENT_RESPONSE_MAXIMUM_BYTES:
            raise ValueError('콘텐츠 API 응답 크기 초과')
        current_response_record=json.loads(current_response_bytes)
        if not isinstance(current_response_record,dict):
            raise ValueError('콘텐츠 API 응답은 객체여야 합니다.')
        return current_response_record
    except HTTPError as current_http_error:
        current_error_body=current_http_error.read(4096).decode('utf-8',errors='replace')
        raise ValueError(f'콘텐츠 API 오류 ({current_http_error.code}): {current_error_body}') from current_http_error
    except URLError as current_transport_error:
        raise RuntimeError('콘텐츠 API 연결 실패: '+str(current_transport_error.reason)) from current_transport_error
