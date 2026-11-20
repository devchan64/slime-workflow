"""관리 게이트웨이에서만 사용하는 백엔드 콘텐츠 HTTP 클라이언트."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlencode
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
    current_request_headers={'Content-Type':'application/json'}
    if current_secret_path:
        current_service_secret=Path(current_secret_path).read_text().strip()
        if not current_service_secret or '\n' in current_service_secret or '\r' in current_service_secret:
            raise ValueError('콘텐츠 서비스 인증 파일이 올바르지 않습니다.')
        current_request_headers['Authorization']='Bearer '+current_service_secret
    elif current_origin_parts.hostname not in ('127.0.0.1','localhost','::1'):
        raise ValueError('원격 콘텐츠 API에는 SLIME_CONTENT_SERVICE_SECRET_FILE이 필요합니다.')
    current_request_bytes=None if current_request_payload is None else json.dumps(current_request_payload,allow_nan=False).encode()
    current_http_request=Request(current_service_origin.rstrip('/')+current_relative_route,data=current_request_bytes,
        method=current_http_method,headers=current_request_headers)
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
        with current_http_error:
            current_error_bytes=current_http_error.read(4097)
        current_error_body=current_error_bytes[:4096].decode('utf-8',errors='replace')
        if len(current_error_bytes)>4096:current_error_body+=' [오류 응답 일부만 표시]'
        raise ValueError(f'콘텐츠 API 오류 ({current_http_error.code}): {current_error_body}') from current_http_error
    except URLError as current_transport_error:
        raise RuntimeError(f'콘텐츠 API 연결 실패: {current_service_origin} · {current_transport_error.reason}. 콘텐츠 API를 먼저 실행하고 연결 설정(serviceOrigin)을 확인한 뒤 관리도구를 다시 시작하세요.') from current_transport_error


def read_content_map_change_receipt(current_request_payload):
    """저장 요청을 재전송하지 않고 같은 입력의 DB 접수 기록만 확인한다."""
    import hashlib
    if not isinstance(current_request_payload,dict) or set(current_request_payload)!={'requestId','expectedGeneration','documents'}:
        raise ValueError('맵 변경 원본 요청이 필요합니다.')
    current_request_identifier=current_request_payload['requestId']
    if not isinstance(current_request_identifier,str) or not 1<=len(current_request_identifier)<=180 or type(current_request_payload['expectedGeneration']) is not int or not isinstance(current_request_payload['documents'],list) or not 1<=len(current_request_payload['documents'])<=10:
        raise ValueError('맵 변경 요청 형식 오류')
    try:
        current_request_bytes=json.dumps(current_request_payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()
    except (ValueError,TypeError) as current_serialization_error:
        raise ValueError('맵 변경 요청 직렬화 오류') from current_serialization_error
    current_request_hash=hashlib.sha256(current_request_bytes).hexdigest()
    return read_content_map_receipt_by_hash(current_request_identifier,current_request_hash)


def read_content_map_receipt_by_hash(current_request_identifier,current_request_hash):
    """보관한 요청 ID·해시로 DB 기록만 읽는다. 저장이나 재접수는 하지 않는다."""
    import re
    if not isinstance(current_request_identifier,str) or not 1<=len(current_request_identifier)<=180 or not isinstance(current_request_hash,str) or not re.fullmatch('[a-f0-9]{64}',current_request_hash):
        raise ValueError('맵 변경 접수 ID 또는 요청 해시 오류')
    current_query_text=urlencode({'requestId':current_request_identifier,'requestSha256':current_request_hash})
    current_receipt_record=execute_content_api_request('GET','/internal/v1/content/map-change-receipt?'+current_query_text)
    if not isinstance(current_receipt_record,dict) or set(current_receipt_record)!={'state'} or current_receipt_record['state'] not in ('matched','mismatch','not_found'):
        raise ValueError('맵 변경 접수 응답 오류')
    return {'state':current_receipt_record['state'],'request_sha256':current_request_hash,'note':'DB 접수 조회 시점의 결과입니다. not_found는 진행 중인 커밋의 부재나 파일 동기화를 보장하지 않습니다.'}
