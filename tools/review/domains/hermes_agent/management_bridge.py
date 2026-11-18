"""격리 Hermes에 한정된 읽기 전용 관측만 제공한다."""
import json
import socket

from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot, read_hermes_model_inventory, read_hermes_model_readiness, read_hermes_content_database_status, read_hermes_kimodo_build_status

from tools.review.domains.hermes_agent.capabilities import list_hermes_capability_catalog, list_management_service_registration, search_hermes_capability_catalog, search_management_service_registration
from tools.review.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog, read_hermes_world_map_catalog, read_hermes_building_catalog

HERMES_OBSERVER_REQUEST = b'gpu-queue\n'
HERMES_OBSERVER_MAX_REQUEST = 1024
HERMES_OBSERVER_MAX_RESPONSE = 262144


def handle_hermes_observer_connection(current_client_socket):
    """고정된 단일 요청만 처리하며 다른 명령과 임의 입력은 거절한다."""
    with current_client_socket:
        current_client_socket.settimeout(2)
        try:
            current_request_bytes = b''
            while b'\n' not in current_request_bytes and len(current_request_bytes) <= HERMES_OBSERVER_MAX_REQUEST:
                current_next_bytes = current_client_socket.recv(HERMES_OBSERVER_MAX_REQUEST + 1 - len(current_request_bytes))
                if not current_next_bytes:
                    break
                current_request_bytes += current_next_bytes
            if current_request_bytes == HERMES_OBSERVER_REQUEST:
                current_response_record = read_hermes_management_snapshot()
            elif current_request_bytes == b'content-database-status\n':
                current_response_record = read_hermes_content_database_status()
            elif current_request_bytes == b'kimodo-build-status\n':
                current_response_record = read_hermes_kimodo_build_status()
            elif current_request_bytes == b'model-inventory\n':
                current_response_record = read_hermes_model_inventory()
            elif current_request_bytes == b'world-map\n':
                try:
                    current_response_record = read_hermes_world_map_catalog()
                except (OSError, ValueError, TypeError):
                    current_response_record = {'error':'월드맵 원본 확인 실패'}
            elif current_request_bytes.startswith(b'world-map ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    current_map_identifier = current_request_bytes[len(b'world-map '):-1].decode('ascii')
                    current_response_record = read_hermes_world_map_catalog(current_map_identifier)
                except (ValueError, UnicodeDecodeError):
                    current_response_record = {'error':'월드맵 원본 확인 실패'}
            elif current_request_bytes == b'service-registration\n':
                current_response_record = list_management_service_registration()
            elif current_request_bytes.startswith(b'service-registration ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    current_search_request=parse_management_request_json(current_request_bytes[len(b'service-registration '):-1].decode('utf-8'))
                    current_response_record=search_management_service_registration(current_search_request)
                except (ValueError,TypeError,UnicodeDecodeError):
                    current_response_record={'error':'서비스 검색 실패: 검색어와 페이지를 확인하세요.'}

            elif current_request_bytes == b'capabilities\n':
                current_response_record = list_hermes_capability_catalog()
            elif current_request_bytes.startswith(b'capabilities ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    current_search_request=parse_management_request_json(current_request_bytes[len(b'capabilities '):-1].decode('utf-8'))
                    current_response_record=search_hermes_capability_catalog(current_search_request)
                except (ValueError,TypeError,UnicodeDecodeError):
                    current_response_record={'error':'기능 검색 실패: 검색어와 페이지를 확인하세요.'}

            elif current_request_bytes.startswith(b'source-history ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from generators.music.service_constants import AUDIO_SERVICE_NAMES
                    from tools.review.domains.hermes_agent.audio_operations import read_hermes_audio_source_history,read_hermes_generator_source_history
                    current_history_request=parse_management_request_json(current_request_bytes[len(b'source-history '):-1].decode('utf-8'))
                    if not isinstance(current_history_request,dict) or 'service' not in current_history_request or set(current_history_request)-{'service','offset','limit','snapshot'}:
                        raise ValueError('이력 조회 입력 오류')
                    current_service_name=current_history_request['service']
                    current_page_request={key:value for key,value in current_history_request.items() if key!='service'}
                    current_history_reader=read_hermes_audio_source_history if current_service_name in AUDIO_SERVICE_NAMES else read_hermes_generator_source_history
                    current_response_record=current_history_reader(current_service_name,current_page_request)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'원본 이력 조회 실패: 서비스와 페이지를 확인하세요.'}
            elif current_request_bytes.startswith(b'field-region ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.field_map_operations import read_hermes_field_region
                    current_region_request = parse_management_request_json(current_request_bytes[len(b'field-region '):-1].decode('utf-8'))
                    current_response_record = read_hermes_field_region(current_region_request)
                except (OSError, RuntimeError, ValueError, TypeError, KeyError, UnicodeDecodeError):
                    current_response_record = {'error':'야외 맵 영역 조회 실패: 맵 ID·리비전·범위를 확인하세요.'}
            elif any(current_request_bytes.startswith(current_prefix_value) for current_prefix_value in (b'sprite-catalog ',b'sprite-detail ')) and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.sprite_observer import read_hermes_sprite_catalog, read_hermes_sprite_sheet
                    current_request_kind,current_request_json=current_request_bytes[:-1].split(b' ',1)
                    current_sprite_request=parse_management_request_json(current_request_json.decode('utf-8'))
                    current_response_record=(read_hermes_sprite_catalog if current_request_kind==b'sprite-catalog' else read_hermes_sprite_sheet)(current_sprite_request)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'스프라이트 조회 실패: 등록 원본과 입력을 확인하세요.'}
            elif current_request_bytes.startswith(b'effect-catalog ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.effect_observer import list_hermes_effect_catalog
                    current_catalog_request=parse_management_request_json(current_request_bytes[len(b'effect-catalog '):-1].decode('utf-8'))
                    current_response_record=list_hermes_effect_catalog(current_catalog_request)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'이펙트 조회 실패: 콘텐츠 서비스 연결과 입력을 확인하세요.'}
            elif current_request_bytes.startswith(b'effect-detail ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.domains.hermes_agent.effect_observer import read_hermes_effect_detail
                    current_effect_identifier=current_request_bytes[len(b'effect-detail '):-1].decode('ascii')
                    current_response_record=read_hermes_effect_detail(current_effect_identifier)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'이펙트 조회 실패: 콘텐츠 서비스 연결과 입력을 확인하세요.'}
            elif current_request_bytes.startswith(b'building-catalog ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    current_catalog_request = parse_management_request_json(current_request_bytes[len(b'building-catalog '):-1].decode('utf-8'))
                    current_response_record = read_hermes_building_catalog(current_catalog_request)
                except (ValueError, TypeError, UnicodeDecodeError):
                    current_response_record = {'error':'건물 목록 조회 실패: 콘텐츠 서비스 연결을 확인하세요.'}
            elif current_request_bytes.startswith(b'billboard-catalog ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    current_catalog_request = parse_management_request_json(current_request_bytes[len(b'billboard-catalog '):-1].decode('utf-8'))
                    current_response_record = read_hermes_billboard_catalog(current_catalog_request)
                except (ValueError, TypeError, UnicodeDecodeError):
                    current_response_record = {'error':'빌보드 카탈로그 조회 실패'}
            elif current_request_bytes.startswith(b'model-readiness ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    current_service_name = current_request_bytes[len(b'model-readiness '):-1].decode('ascii')
                    current_response_record = read_hermes_model_readiness(current_service_name)
                except (ValueError, UnicodeDecodeError):
                    current_response_record = {'error':'지원하지 않는 모델 서비스'}
            else:
                current_response_record = {'error': '지원하지 않는 조회 요청'}
            current_response_bytes = json.dumps(current_response_record, ensure_ascii=False, allow_nan=False).encode('utf-8')
            if len(current_response_bytes) > HERMES_OBSERVER_MAX_RESPONSE:
                current_response_bytes = b'{"error":"response too large"}'
            current_client_socket.sendall(current_response_bytes + b'\n')
        except (OSError, ValueError, TypeError):
            return


def serve_hermes_observer_connections(current_listener_socket):
    """작업 수명 동안 연결을 순차 처리하며 소켓이 닫히면 종료한다."""
    while True:
        try:
            current_client_socket, _ = current_listener_socket.accept()
        except OSError:
            return
        handle_hermes_observer_connection(current_client_socket)
