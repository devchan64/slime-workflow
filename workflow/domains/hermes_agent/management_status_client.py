"""격리된 Hermes의 고정 관리 상태 조회 명령."""
import json
import socket
import sys

HERMES_OBSERVER_MAX_RESPONSE = 262144


def read_sandbox_management_status(current_request_kind='gpu-queue', current_service_name=None):
    """고정 소켓과 고정 요청만 사용한다."""
    if current_request_kind == 'translation-evidence':
        if not isinstance(current_service_name,str) or len(current_service_name.encode('utf-8'))>78000 or '\n' in current_service_name:
            raise ValueError('번역 근거 검색 입력 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'map-database-receipt' and current_service_name is not None:
        if not isinstance(current_service_name,str) or len(current_service_name.encode('utf-8'))>4000 or '\n' in current_service_name:
            raise ValueError('맵 DB 접수 입력 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind in ('legacy-anchor-history', 'expression-catalog', 'billboard-catalog', 'building-catalog', 'field-region', 'effect-catalog', 'sprite-catalog', 'sprite-detail', 'capabilities', 'service-registration', 'source-history', 'audio-source-status', 'video-source-status', 'flux-source-status', 'image-source-status', 'character-source-status', 'reservation-inspect', 'capture-status', 'writer-search-paths', 'writer-job-search-paths', 'writer-job-review', 'writer-job-material', 'capture-map-check', 'flux-resume-preview', 'video-resume-preview', 'cleanup-preview') and current_service_name is not None:
        if not isinstance(current_service_name, str) or len(current_service_name.encode('utf-8')) > 800 or '\n' in current_service_name:
            raise ValueError('빌보드 검색 입력 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'kimodo-resume-preview':
        import re
        if not isinstance(current_service_name,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_service_name):
            raise ValueError('Kimodo 작업 ID 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'effect-detail':
        import re
        if not isinstance(current_service_name,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,95}',current_service_name):
            raise ValueError('이펙트 ID 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind in ('world-map','city-map','city-source') and current_service_name is not None:
        import re
        if not isinstance(current_service_name,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}',current_service_name):
            raise ValueError('맵 ID 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'model-backup-compare':
        if not isinstance(current_service_name, str) or not current_service_name or len(current_service_name.encode('utf-8')) > 200 or '\n' in current_service_name:
            raise ValueError('모델 이름 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind == 'model-readiness':
        import re
        if not isinstance(current_service_name, str) or not re.fullmatch(r'[a-z0-9-]{1,40}', current_service_name):
            raise ValueError('모델 서비스 식별자 형식 오류')
        current_request_kind += ' ' + current_service_name
    elif current_request_kind not in ('gpu-queue', 'model-inventory', 'model-download-status', 'model-backup-models', 'model-backup-history', 'service-registration', 'capabilities', 'world-map', 'content-database-status', 'kimodo-build-status', 'writer-index-status', 'sprite-pending-status') or current_service_name is not None:
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
            current_allowed_errors = ('표정 목록 조회 실패: 검색어와 페이지를 확인하세요.', '원본 이력 조회 실패: 서비스와 페이지를 확인하세요.', '스프라이트 조회 실패: 등록 원본과 입력을 확인하세요.', '이펙트 조회 실패: 콘텐츠 서비스 연결과 입력을 확인하세요.', '야외 맵 영역 조회 실패: 맵 ID·리비전·범위를 확인하세요.', '건물 목록 조회 실패: 콘텐츠 서비스 연결을 확인하세요.', '빌보드 카탈로그 조회 실패', '월드맵 원본 확인 실패', '지원하지 않는 모델 서비스', '지원하지 않는 조회 요청', '기능 검색 실패: 검색어와 페이지를 확인하세요.', '서비스 검색 실패: 검색어와 페이지를 확인하세요.', '예약 신원 조회 실패: 서비스와 작업 ID를 확인하세요.', '캡처 상태 조회 실패: 접수 ID와 서비스를 확인하세요.')
            current_allowed_errors += ('캡처 맵 등록 조회 실패: 맵 ID와 등록 원본을 확인하세요.',)
            current_allowed_errors += ('모델 백업 조회 실패: 게이트웨이와 백업 연결을 확인하세요.',)
            current_allowed_errors += ('맵 DB 접수 조회 실패: 요청 ID·해시와 에셋 서비스를 확인하세요.',)
            current_allowed_errors += ('Kimodo 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.','FLUX 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.','영상 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.','정리 미리보기를 확인할 수 없습니다. 원 서비스 상태를 확인하세요.')
            current_allowed_errors += ('도시 원본 조회 실패: 맵 ID와 등록 원본을 확인하세요.', '도시 맵 조회 실패: 맵 ID와 콘텐츠 DB 상태를 확인하세요.', '조회 응답 크기 제한 초과: 원 도구에서 확인하세요.')
            current_allowed_errors += ('작가 작업 조회 실패: 작업 ID와 원 서비스를 확인하세요.', '작가 검색 경로 조회 실패: 접수 ID를 확인하세요.', '작가 검색 경로 조회 실패: 작업 ID와 검색 기록을 확인하세요.', '작가 자료 조회 실패: 작업 ID·자료 종류·페이지 지문을 확인하세요.', '작가 색인 상태 조회 실패: 작가 서비스를 확인하세요.', '모델 다운로드 상태 조회 실패', '번역 근거 조회 실패: 검색 원문과 작가 색인 상태를 확인하세요.', '번역 근거 조회 실패: 작가 색인이 오래되어 갱신이 필요합니다.', '번역 근거 조회 실패: 작가 색인이 준비되지 않았습니다.')
            current_allowed_errors += ('오디오 원본 상태 조회 실패: 서비스와 작업 ID를 확인하세요.',)
            current_allowed_errors += ('영상 원본 상태 조회 실패: 서비스와 작업 ID를 확인하세요.', 'FLUX 원본 상태 조회 실패: 서비스와 작업 ID를 확인하세요.', '이미지 원본 상태 조회 실패: 서비스와 작업 ID를 확인하세요.', '캐릭터 원본 상태 조회 실패: 작업 ID를 확인하세요.')
            current_allowed_errors += ('과거 앵커 이력 조회 실패: 대상과 페이지를 확인하세요.',)
            current_error_message = current_response_record['error']
            raise ValueError(current_error_message if current_error_message in current_allowed_errors else '관리 상태 조회가 거절됐습니다.')
        return current_response_record


if __name__ == '__main__':
    if not (len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ('model-inventory', 'model-download-status', 'model-backup-models', 'model-backup-history', 'service-registration', 'capabilities', 'world-map', 'content-database-status', 'kimodo-build-status', 'writer-index-status', 'sprite-pending-status')) or (len(sys.argv) == 3 and sys.argv[1] in ('model-backup-compare', 'model-readiness', 'legacy-anchor-history', 'expression-catalog', 'billboard-catalog', 'building-catalog', 'field-region', 'city-map', 'city-source', 'kimodo-resume-preview', 'flux-resume-preview', 'video-resume-preview', 'cleanup-preview', 'world-map', 'effect-catalog', 'effect-detail', 'sprite-catalog', 'sprite-detail', 'capabilities', 'service-registration', 'source-history', 'audio-source-status', 'video-source-status', 'flux-source-status', 'image-source-status', 'character-source-status', 'reservation-inspect', 'capture-status', 'writer-search-paths', 'writer-job-search-paths', 'writer-job-review', 'writer-job-material', 'map-database-receipt', 'capture-map-check', 'translation-evidence'))):
        sys.exit('지원하지 않는 관리 조회입니다.')
    try:
        print(json.dumps(read_sandbox_management_status(sys.argv[1] if len(sys.argv) > 1 else 'gpu-queue', sys.argv[2] if len(sys.argv) == 3 else None), ensure_ascii=False))
    except (OSError, ValueError, TypeError) as current_observer_error:
        sys.exit('관리 상태 조회 실패: ' + str(current_observer_error))
