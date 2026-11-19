"""검수 캡처의 정규화와 중복 방지 기반. 실제 캡처 실행 경로에는 연결하지 않는다."""

from tools.review.domains.character_review.capture import validate_capture_settings
from tools.review.domains.map_review.capture import validate_map_capture_settings


def normalize_capture_delegation_request(current_service_name, current_request_payload):
    """기존 캡처 검증기로 기본값을 포함한 입력을 고정한다."""
    if current_service_name == 'character-review':
        return validate_capture_settings(current_request_payload)
    if current_service_name == 'map-review':
        return validate_map_capture_settings(current_request_payload)
    raise ValueError('지원하지 않는 검수 캡처 서비스입니다.')


def prepare_capture_delegation_once(current_delegation_store, current_request_identifier, current_service_name, current_request_payload, current_submit_callback):
    """명시적으로 주입된 접수 함수만 사용하며 실제 GPU 작업을 직접 실행하지 않는다."""
    current_normalized_request = normalize_capture_delegation_request(current_service_name, current_request_payload)
    if not callable(current_submit_callback):
        raise ValueError('캡처 접수 함수가 필요합니다.')
    def validate_normalized_capture_request(current_request_record):
        if normalize_capture_delegation_request(current_service_name, current_request_record) != current_request_record:
            raise ValueError('캡처 입력이 정규화된 검토 내용과 다릅니다.')
    return current_delegation_store.execute_service_delegation_once(current_request_identifier, current_service_name, current_normalized_request, current_submit_callback, validate_normalized_capture_request)
