"""검수 캡처의 정규화와 중복 방지 기반. 실제 캡처 실행 경로에는 연결하지 않는다."""

import threading

from workflow.domains.character_review.capture import validate_capture_settings
from workflow.domains.map_review.capture import validate_map_capture_settings


CAPTURE_MAP_REGISTRATION_LOCK = threading.Lock()


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


def inspect_capture_map_registration(current_proposal_record):
    """맵 캡처 제안의 등록 여부만 읽으며 캡처나 GPU 실행은 하지 않는다."""
    import yaml
    if not isinstance(current_proposal_record,dict) or set(current_proposal_record)!={'service','settings'}:
        raise ValueError('캡처 제안 형식 오류')
    current_service_name=current_proposal_record['service']
    current_settings_record=normalize_capture_delegation_request(current_service_name,current_proposal_record['settings'])
    if current_service_name!='map-review':
        return {'status':'not_applicable'}
    if not CAPTURE_MAP_REGISTRATION_LOCK.acquire(blocking=False):
        return {'status':'unavailable','map':current_settings_record['map']}
    try:
        from workflow.common.map_asset_sources import load_review_map_menu
        current_menu_records=load_review_map_menu()
        if not isinstance(current_menu_records,list) or any(not isinstance(current_map_record,dict) or not isinstance(current_map_record.get('id'),str) for current_map_record in current_menu_records):
            raise ValueError('맵 목록 형식 오류')
        current_map_identifiers=[current_map_record['id'] for current_map_record in current_menu_records]
        if len(current_map_identifiers)!=len(set(current_map_identifiers)):
            raise ValueError('맵 목록 중복')
        return {'status':'registered' if current_settings_record['map'] in current_map_identifiers else 'not_registered','map':current_settings_record['map']}
    except (OSError,ValueError,TypeError,KeyError,RuntimeError,yaml.YAMLError):
        return {'status':'unavailable','map':current_settings_record['map']}
    finally:
        CAPTURE_MAP_REGISTRATION_LOCK.release()
