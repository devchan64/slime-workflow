"""격리된 Hermes의 고정 관리 상태 조회 명령."""
import json
import socket
import sys

HERMES_OBSERVER_MAX_RESPONSE = 262144


def read_sandbox_management_status(current_request_kind='gpu-queue', current_service_name=None):
    """고정 소켓과 고정 요청만 사용한다."""
    if current_request_kind in ('billboard-catalog', 'building-catalog', 'field-region', 'effect-catalog', 'sprite-catalog', 'sprite-detail', 'capabilities', 'service-registration', 'source-history') and current_service_name is not None:
        if not isinstance(current_service_name, str) or len(current_service_name.encode('utf-8')) > 800 or '\n' in current_service_name:
            raise ValueError('빌보드 검색 입력 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'effect-detail':
        import re
        if not isinstance(current_service_name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,95}',current_service_name):
            raise ValueError('이펙트 ID 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'world-map' and current_service_name is not None:
        import re
        if not isinstance(current_service_name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_service_name):
            raise ValueError('맵 ID 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'model-readiness':
        import re
        if not isinstance(current_service_name, str) or not re.fullmatch(r'[a-z0-9-]{1,40}', current_service_name):
            raise ValueError('모델 서비스 식별자 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind not in ('gpu-queue', 'model-inventory', 'service-registration', 'capabilities', 'world-map', 'content-database-status', 'kimodo-build-status') or current_service_name is not None:
        raise ValueError('지원하지 않는 관리 조회')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as current_client_socket:
        current_client_socket.settimeout(30)
        current_client_socket.connect('/control/management-status.sock')
        current_client_socket.sendall((current_request_kind + '\n').encode('utf-8'))
        current_response_bytes = b''
        while b'\n' not in current_response_bytes and len(current_response_bytes) <= HERMES_OBSERVER_MAX_RESPONSE:
            current_next_bytes = current_client_socket.recv(min(65536, HERMES_OBSERVER_MAX_RESPONSE + 1 - len(current_response_bytes)))
            if not current_next_bytes:
                break
            current_response_bytes += current_next_bytes
        if len(current_response_bytes) > HERMES_OBSERVER_MAX_RESPONSE or not current_response_bytes.endswith(b'\n'):
            raise ValueError('관리 상태 응답 크기 또는 종료 형식 오류')
        current_response_record = json.loads(current_response_bytes)
        if not isinstance(current_response_record, dict):
            raise ValueError('관리 상태 응답 형식 오류')
        if 'error' in current_response_record:
            current_allowed_errors = ('원본 이력 조회 실패: 서비스와 페이지를 확인하세요.', '스프라이트 조회 실패: 등록 원본과 입력을 확인하세요.', '이펙트 조회 실패: 콘텐츠 서비스 연결과 입력을 확인하세요.', '야외 맵 영역 조회 실패: 맵 ID·리비전·범위를 확인하세요.', '건물 목록 조회 실패: 콘텐츠 서비스 연결을 확인하세요.', '빌보드 카탈로그 조회 실패', '월드맵 원본 확인 실패', '지원하지 않는 모델 서비스', '지원하지 않는 조회 요청', '기능 검색 실패: 검색어와 페이지를 확인하세요.', '서비스 검색 실패: 검색어와 페이지를 확인하세요.')
            current_error_message = current_response_record['error']
            raise ValueError(current_error_message if current_error_message in current_allowed_errors else '관리 상태 조회가 거절됐습니다.')
        return current_response_record


if __name__ == '__main__':
    if not (len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ('model-inventory', 'service-registration', 'capabilities', 'world-map', 'content-database-status', 'kimodo-build-status')) or (len(sys.argv) == 3 and sys.argv[1] in ('model-readiness', 'billboard-catalog', 'building-catalog', 'field-region', 'world-map', 'effect-catalog', 'effect-detail', 'sprite-catalog', 'sprite-detail', 'capabilities', 'service-registration', 'source-history'))):
        sys.exit('지원하지 않는 관리 조회입니다.')
    try:
        print(json.dumps(read_sandbox_management_status(sys.argv[1] if len(sys.argv) > 1 else 'gpu-queue', sys.argv[2] if len(sys.argv) == 3 else None), ensure_ascii=False))
    except (OSError, ValueError, TypeError) as current_observer_error:
        sys.exit('관리 상태 조회 실패: ' + str(current_observer_error))
