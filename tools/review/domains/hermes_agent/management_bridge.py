"""격리 Hermes에 한정된 읽기 전용 관측만 제공한다."""
import json
import socket

from tools.review.domains.hermes_agent.management_observer import read_hermes_management_snapshot, read_hermes_model_inventory, read_hermes_model_readiness, read_hermes_content_database_status, read_hermes_kimodo_build_status

from tools.review.domains.hermes_agent.capabilities import list_hermes_capability_catalog, list_management_service_registration, search_hermes_capability_catalog, search_management_service_registration
from tools.review.domains.hermes_agent.asset_observer import read_hermes_billboard_catalog, read_hermes_world_map_catalog, read_hermes_building_catalog

HERMES_OBSERVER_REQUEST = b'gpu-queue\n'
HERMES_OBSERVER_MAX_REQUEST = 80000
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
            if len(current_request_bytes)>HERMES_OBSERVER_MAX_REQUEST or (len(current_request_bytes)>1024 and not current_request_bytes.startswith(b'translation-evidence ')):
                current_response_record={'error':'지원하지 않는 조회 요청'}
            elif current_request_bytes == HERMES_OBSERVER_REQUEST:
                current_response_record = read_hermes_management_snapshot()
            elif current_request_bytes == b'sprite-pending-status\n':
                from tools.review.domains.hermes_agent.sprite_pending_observer import inspect_hermes_sprite_pending_status
                current_response_record=inspect_hermes_sprite_pending_status()
            elif current_request_bytes == b'writer-index-status\n':
                try:
                    from tools.review.domains.hermes_agent.writer_operations import read_hermes_writer_index_status
                    current_response_record=read_hermes_writer_index_status()
                except (OSError,RuntimeError,ValueError,TypeError,KeyError):
                    current_response_record={'error':'작가 색인 상태 조회 실패: 작가 서비스를 확인하세요.'}
            elif current_request_bytes.startswith(b'capture-map-check ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.capture_delegation import inspect_capture_map_registration
                    current_capture_request=parse_management_request_json(current_request_bytes[len(b'capture-map-check '):-1].decode('utf-8'))
                    if not isinstance(current_capture_request,dict) or set(current_capture_request)!={'map'}:
                        raise ValueError('맵 확인 입력 오류')
                    current_response_record=inspect_capture_map_registration({'service':'map-review','settings':current_capture_request})
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'캡처 맵 등록 조회 실패: 맵 ID와 등록 원본을 확인하세요.'}
            elif current_request_bytes.startswith(b'map-database-receipt ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.map_assets.database_client import read_content_map_receipt_by_hash
                    current_receipt_request=parse_management_request_json(current_request_bytes[len(b'map-database-receipt '):-1].decode('utf-8'))
                    if not isinstance(current_receipt_request,dict) or set(current_receipt_request)!={'database_request_id','request_sha256'}:
                        raise ValueError('맵 DB 접수 입력 오류')
                    current_response_record=read_content_map_receipt_by_hash(current_receipt_request['database_request_id'],current_receipt_request['request_sha256'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'맵 DB 접수 조회 실패: 요청 ID·해시와 에셋 서비스를 확인하세요.'}
            elif current_request_bytes == b'content-database-status\n':
                current_response_record = read_hermes_content_database_status()
            elif current_request_bytes == b'kimodo-build-status\n':
                current_response_record = read_hermes_kimodo_build_status()
            elif current_request_bytes == b'model-download-status\n':
                try:
                    from tools.review.domains.hermes_agent.management_observer import read_hermes_model_download_status
                    current_response_record=read_hermes_model_download_status()
                except (OSError,RuntimeError,ValueError,TypeError,KeyError):
                    current_response_record={'error':'모델 다운로드 상태 조회 실패'}
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

            elif current_request_bytes.startswith(b'expression-catalog ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.expression_observer import read_hermes_expression_catalog
                    current_catalog_request=parse_management_request_json(current_request_bytes[len(b'expression-catalog '):-1].decode('utf-8'))
                    current_response_record=read_hermes_expression_catalog(current_catalog_request)
                except (OSError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'표정 목록 조회 실패: 검색어와 페이지를 확인하세요.'}
            elif current_request_bytes.startswith(b'translation-evidence ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.translation_operations import search_hermes_translation_evidence
                    current_evidence_request=parse_management_request_json(current_request_bytes[len(b'translation-evidence '):-1].decode('utf-8'))
                    if not isinstance(current_evidence_request,dict) or set(current_evidence_request)!={'text'}:
                        raise ValueError('번역 근거 검색 입력 오류')
                    current_response_record=search_hermes_translation_evidence(current_evidence_request['text'])
                except ValueError as current_evidence_error:
                    if '문서 추가·수정·삭제 이후 색인이 오래되었습니다' in str(current_evidence_error):
                        current_response_record={'error':'번역 근거 조회 실패: 작가 색인이 오래되어 갱신이 필요합니다.'}
                    elif '먼저 학습 명령으로 문서 RAG를 구성하세요' in str(current_evidence_error):
                        current_response_record={'error':'번역 근거 조회 실패: 작가 색인이 준비되지 않았습니다.'}
                    else:
                        current_response_record={'error':'번역 근거 조회 실패: 검색 원문과 작가 색인 상태를 확인하세요.'}
                except (OSError,RuntimeError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'번역 근거 조회 실패: 검색 원문과 작가 색인 상태를 확인하세요.'}
            elif current_request_bytes.startswith(b'writer-search-paths ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.writer_operations import read_hermes_writer_search_paths
                    current_writer_request=parse_management_request_json(current_request_bytes[len(b'writer-search-paths '):-1].decode('utf-8'))
                    if not isinstance(current_writer_request,dict) or set(current_writer_request)!={'request_id'}:
                        raise ValueError('작가 검색 입력 오류')
                    current_response_record=read_hermes_writer_search_paths(current_writer_request['request_id'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'작가 검색 경로 조회 실패: 접수 ID를 확인하세요.'}
            elif current_request_bytes.startswith(b'writer-job-search-paths ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.writer_operations import read_writer_job_search_paths
                    current_writer_request=parse_management_request_json(current_request_bytes[len(b'writer-job-search-paths '):-1].decode('utf-8'))
                    if not isinstance(current_writer_request,dict) or set(current_writer_request)!={'job_id'}:
                        raise ValueError('작가 검색 입력 오류')
                    current_response_record=read_writer_job_search_paths(current_writer_request['job_id'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'작가 검색 경로 조회 실패: 작업 ID와 검색 기록을 확인하세요.'}
            elif current_request_bytes.startswith(b'writer-job-material ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.writer_operations import read_writer_job_material_page
                    from generators.writer_agent.material_pages import validate_writer_material_request
                    current_writer_request=parse_management_request_json(current_request_bytes[len(b'writer-job-material '):-1].decode('utf-8'))
                    validate_writer_material_request(current_writer_request)
                    current_response_record=read_writer_job_material_page(current_writer_request)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'작가 자료 조회 실패: 작업 ID·자료 종류·페이지 지문을 확인하세요.'}
            elif current_request_bytes.startswith(b'writer-job-review ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.writer_operations import read_writer_job_review
                    current_writer_request=parse_management_request_json(current_request_bytes[len(b'writer-job-review '):-1].decode('utf-8'))
                    if not isinstance(current_writer_request,dict) or set(current_writer_request)!={'job_id'}:
                        raise ValueError('작가 작업 입력 오류')
                    current_response_record={'job_id':current_writer_request['job_id'],'job':read_writer_job_review(current_writer_request['job_id'])}
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'작가 작업 조회 실패: 작업 ID와 원 서비스를 확인하세요.'}
            elif current_request_bytes.startswith(b'capture-status ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY
                    from tools.review.domains.hermes_agent.capture_status import read_capture_delegation_status
                    from tools.review.domains.hermes_agent.delegation_store import HermesDelegationStore
                    current_capture_request=parse_management_request_json(current_request_bytes[len(b'capture-status '):-1].decode('utf-8'))
                    if not isinstance(current_capture_request,dict) or set(current_capture_request)!={'service','request_id'}:
                        raise ValueError('캡처 상태 입력 오류')
                    current_response_record=read_capture_delegation_status(HermesDelegationStore(),current_capture_request['request_id'],current_capture_request['service'],WORKFLOW_ROOT_DIRECTORY)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'캡처 상태 조회 실패: 접수 ID와 서비스를 확인하세요.'}
            elif current_request_bytes.startswith(b'reservation-inspect ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.reservation_observer import inspect_generator_reservation_identity
                    current_inspection_request=parse_management_request_json(current_request_bytes[len(b'reservation-inspect '):-1].decode('utf-8'))
                    if not isinstance(current_inspection_request,dict) or set(current_inspection_request)!={'service','job_id'}:
                        raise ValueError('예약 조회 입력 오류')
                    current_response_record=inspect_generator_reservation_identity(current_inspection_request['service'],current_inspection_request['job_id'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'예약 신원 조회 실패: 서비스와 작업 ID를 확인하세요.'}
            elif current_request_bytes.startswith(b'source-history ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from generators.music.service_constants import AUDIO_SERVICE_NAMES
                    from tools.review.domains.hermes_agent.audio_operations import read_hermes_audio_source_history,read_hermes_generator_source_history
                    current_history_request=parse_management_request_json(current_request_bytes[len(b'source-history '):-1].decode('utf-8'))
                    if not isinstance(current_history_request,dict) or 'service' not in current_history_request or set(current_history_request)-{'service','offset','limit','snapshot','query'}:
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
            elif current_request_bytes.startswith(b'cleanup-preview ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.domains.hermes_agent.cleanup_preview_observer import read_hermes_cleanup_preview
                    current_service_name=current_request_bytes[len(b'cleanup-preview '):-1].decode('ascii')
                    current_response_record=read_hermes_cleanup_preview(current_service_name)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'정리 미리보기를 확인할 수 없습니다. 원 서비스 상태를 확인하세요.'}
            elif current_request_bytes.startswith(b'video-resume-preview ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.video_resume_operations import preview_hermes_video_resume
                    current_video_request=parse_management_request_json(current_request_bytes[len(b'video-resume-preview '):-1].decode('utf-8'))
                    if not isinstance(current_video_request,dict) or set(current_video_request)!={'service','job_id'}:raise ValueError('영상 검토 입력 오류')
                    current_response_record=preview_hermes_video_resume(current_video_request['service'],current_video_request['job_id'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'영상 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.'}
            elif current_request_bytes.startswith(b'flux-resume-preview ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.common.management_gateway import parse_management_request_json
                    from tools.review.domains.hermes_agent.flux_resume_operations import preview_hermes_flux_resume
                    current_flux_request=parse_management_request_json(current_request_bytes[len(b'flux-resume-preview '):-1].decode('utf-8'))
                    if not isinstance(current_flux_request,dict) or set(current_flux_request)!={'service','job_id'}:raise ValueError('FLUX 검토 입력 오류')
                    current_response_record=preview_hermes_flux_resume(current_flux_request['service'],current_flux_request['job_id'])
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'FLUX 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.'}
            elif current_request_bytes.startswith(b'kimodo-resume-preview ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.domains.hermes_agent.kimodo_resume_operations import preview_hermes_kimodo_resume
                    from tools.review.domains.hermes_agent.delegation_store import validate_service_job_identifier
                    current_job_identifier=current_request_bytes[len(b'kimodo-resume-preview '):-1].decode('ascii')
                    if not validate_service_job_identifier('kimodo',current_job_identifier):raise ValueError('Kimodo 작업 ID 오류')
                    current_response_record=preview_hermes_kimodo_resume(current_job_identifier)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'Kimodo 재개 검토 실패: 작업과 원 서비스 상태를 확인하세요.'}
            elif current_request_bytes.startswith(b'city-source ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n')==1:
                try:
                    from tools.review.domains.hermes_agent.city_map_operations import read_hermes_city_source
                    current_city_identifier=current_request_bytes[len(b'city-source '):-1].decode('ascii')
                    current_response_record=read_hermes_city_source(current_city_identifier)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'도시 원본 조회 실패: 맵 ID와 등록 원본을 확인하세요.'}
            elif current_request_bytes.startswith(b'city-map ') and current_request_bytes.endswith(b'\n') and current_request_bytes.count(b'\n') == 1:
                try:
                    from tools.review.domains.hermes_agent.city_map_operations import load_hermes_city_map
                    from tools.review.domains.hermes_agent.field_map_operations import HERMES_FIELD_MAP_PATTERN
                    current_city_identifier=current_request_bytes[len(b'city-map '):-1].decode('ascii')
                    if not HERMES_FIELD_MAP_PATTERN.fullmatch(current_city_identifier):raise ValueError('도시 ID 오류')
                    current_response_record=load_hermes_city_map(current_city_identifier)
                except (OSError,RuntimeError,ValueError,TypeError,KeyError,UnicodeDecodeError):
                    current_response_record={'error':'도시 맵 조회 실패: 맵 ID와 콘텐츠 DB 상태를 확인하세요.'}
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
            if len(current_response_bytes) + 1 > HERMES_OBSERVER_MAX_RESPONSE:
                current_response_bytes = json.dumps({'error':'조회 응답 크기 제한 초과: 원 도구에서 확인하세요.'},ensure_ascii=False).encode('utf-8')
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
