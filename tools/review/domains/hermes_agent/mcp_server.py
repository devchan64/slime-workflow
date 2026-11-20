"""Codex가 공용 게이트웨이에 격리 Hermes 작업을 위임하는 MCP 어댑터."""
import json
from datetime import datetime, timezone
import os
import re
from pathlib import Path, PurePosixPath
import sys
import urllib.error
import urllib.request

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address

hermes_mcp_server = MCPServer('slime-hermes', instructions='Hermes는 관리도구 기능의 조회와 서비스별 위임을 지원합니다. 격리 작업은 관리도구 사본에서 수행하므로 diff와 로그를 검토하세요. 별도 관리 서비스 위임은 실제 생성기·데이터에 영향을 줄 수 있으므로 각 도구의 검토와 입력 계약을 확인하세요. 요청 식별자를 유지하고 결과가 불확실하면 원 서비스와 접수 기록을 확인하세요.')


class RejectHermesGatewayRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, current_request_value, current_response_file, current_status_code, current_status_message, current_header_values, current_redirect_url):
        raise ValueError('관리 게이트웨이의 리다이렉트는 허용하지 않습니다.')


def call_hermes_management_gateway(hermes_command_name, hermes_payload_record):
    """임의 원격지 연결이나 셸 실행 없이 관리 명령 봉투만 전송한다."""
    hermes_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
    hermes_request_bytes = json.dumps({'service':'hermes-agent', 'command':hermes_command_name, 'payload':hermes_payload_record}, ensure_ascii=False, allow_nan=False).encode('utf-8')
    hermes_http_request = urllib.request.Request(hermes_gateway_address + '/management/command', data=hermes_request_bytes, headers={'Content-Type':'application/json', 'Origin':hermes_gateway_address}, method='POST')
    hermes_http_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectHermesGatewayRedirect())
    try:
        with hermes_http_opener.open(hermes_http_request, timeout=30) as hermes_http_response:
            hermes_response_bytes = hermes_http_response.read(2_000_001)
    except urllib.error.HTTPError as hermes_http_error:
        with hermes_http_error:
            hermes_error_bytes = hermes_http_error.read(16_001)
        if len(hermes_error_bytes) > 16_000:
            hermes_error_message = '관리 게이트웨이 오류 응답이 너무 큽니다. 원 서비스에서 확인하세요.'
        else:
            try:
                hermes_error_message = json.loads(hermes_error_bytes).get('error', '관리 게이트웨이 요청 실패')
            except (ValueError, AttributeError):
                hermes_error_message = '관리 게이트웨이 요청 실패'
        raise ValueError(f'{hermes_http_error.code}: {hermes_error_message}') from hermes_http_error
    if len(hermes_response_bytes) > 2_000_000:
        raise ValueError('관리 게이트웨이 응답이 너무 큽니다.')
    hermes_response_record = json.loads(hermes_response_bytes)
    if not isinstance(hermes_response_record, dict):
        raise ValueError('관리 게이트웨이 응답이 객체가 아닙니다.')
    return hermes_response_record


def run_hermes_mcp_command(hermes_command_name, hermes_payload_record):
    try:
        return call_hermes_management_gateway(hermes_command_name, hermes_payload_record)
    except (OSError, ValueError) as hermes_gateway_error:
        raise ToolError('Hermes 관리 명령 실패: ' + str(hermes_gateway_error)) from hermes_gateway_error


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_coding_task(request_identifier_value: str, coding_prompt_text: str, verification_module_names: list[str] | None = None) -> dict:
    """운영 조회·제안 또는 격리 코드 작업을 접수한다. 코드 변경은 격리 사본에 남고 선택한 공용 회귀 모듈은 최종 수정 후 독립 실행한다. 응답 유실 시 같은 식별자를 사용한다. 추론은 GPU 대기열을 사용한다. 배타 예약은 관리도구 대기열에만 적용되며 외부 GPU 작업과 성능 경합이 가능하다."""
    hermes_request_record = {'request_id':request_identifier_value, 'prompt':coding_prompt_text}
    if verification_module_names:
        hermes_request_record['verification_modules'] = verification_module_names
    return run_hermes_mcp_command('hermes-submit', hermes_request_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_coding_task(job_identifier_value: str) -> dict:
    """접수된 작업의 상태·검토용 diff·로그를 조회한다."""
    return run_hermes_mcp_command('hermes-detail', {'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_coding_tasks() -> dict:
    """공용 기록의 Hermes 작업 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_coding_tasks_page(offset_value: int = 0, limit_value: int = 30, snapshot_value: str | None = None, query_text: str = '', status_name: str = '전체') -> dict:
    """Hermes 작업을 최근순으로 조회한다. 다음 페이지에는 첫 조회의 snapshot을 전달한다."""
    current_payload_record={'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:
        current_payload_record['snapshot']=snapshot_value
    if query_text:
        current_payload_record['query']=query_text
    if status_name!='전체':
        current_payload_record['status']=status_name
    return run_hermes_mcp_command('hermes-history',current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_task_diff(job_identifier_value: str, byte_offset_value: int = 0, byte_limit_value: int = 65536) -> dict:
    """종료된 작업의 전체 diff를 정확한 바이트 범위의 base64 조각으로 읽는다."""
    return run_hermes_mcp_command('hermes-diff', {'id':job_identifier_value, 'offset':byte_offset_value, 'limit':byte_limit_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def create_hermes_session(session_identifier_value: str) -> dict:
    """32자리 소문자 16진수 ID로 세션을 만들거나 기존 세션을 반환한다."""
    return run_hermes_mcp_command('hermes-session-create', {'session_id': session_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_session(session_identifier_value: str) -> dict:
    """세션 메시지와 연결된 작업 ID를 조회한다."""
    return run_hermes_mcp_command('hermes-session-read', {'session_id': session_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_session_message(session_identifier_value: str, request_identifier_value: str, message_text_value: str, verification_module_names: list[str] | None = None) -> dict:
    """세션의 이전 완료 작업 문맥을 포함해 격리 Hermes 작업을 접수한다. 추론은 GPU 대기열을 사용한다. 배타 예약은 관리도구 대기열에만 적용되며 외부 GPU 작업과 성능 경합이 가능하다."""
    hermes_request_record = {'session_id': session_identifier_value, 'request_id': request_identifier_value, 'prompt': message_text_value}
    if verification_module_names:
        hermes_request_record['verification_modules'] = verification_module_names
    return run_hermes_mcp_command('hermes-session-submit', hermes_request_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_expression_presets(query_value: str = '', offset_value: int = 0, limit_value: int = 20, snapshot_value: str | None = None) -> dict:
    """표정 프리셋 ID와 이름을 검색한다. 후속 페이지는 첫 응답의 snapshot을 사용한다."""
    current_payload_record={'query':query_value,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_payload_record['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-expression-catalog',current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_service_receipt(request_identifier_value: str, service_name: str) -> dict:
    """접수 ID·서비스·접수 상태를 확인한다. 원 작업의 생존·결과를 확인하거나 복구·생성을 실행하지 않는다. Kimodo는 별도 접수 조회를 사용한다."""
    return run_hermes_mcp_command('hermes-service-receipt',{'request_id':request_identifier_value,'service':service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_sessions_page(offset_value: int = 0, limit_value: int = 30, snapshot_value: str | None = None, query_text: str = '') -> dict:
    """세션을 최근 갱신순으로 조회하며 다음 페이지에는 목록 확인값을 전달한다."""
    current_payload_record={'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_payload_record['snapshot']=snapshot_value
    if query_text:current_payload_record['query']=query_text
    return run_hermes_mcp_command('hermes-session-list',current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_session_view(session_identifier_value: str, offset_value: int = 0, snapshot_value: str | None = None) -> dict:
    """최근 메시지부터 20건씩 조회한다. 이전 페이지에는 첫 응답의 snapshot이 필요하다."""
    current_payload_record={'session_id':session_identifier_value}
    if offset_value:current_payload_record['offset']=offset_value
    if snapshot_value is not None:current_payload_record['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-session-view',current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_sessions() -> dict:
    """최근 세션의 식별자와 메시지 수를 조회한다."""
    return run_hermes_mcp_command('hermes-session-list', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_management_service_registration() -> dict:
    """게이트웨이에 등록된 서비스와 명령을 조회한다. 등록은 실행 가능·권한을 뜻하지 않는다."""
    return run_hermes_mcp_command('hermes-service-registration', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def search_hermes_management_services(search_text_value: str = '', offset_value: int = 0, limit_value: int = 5) -> dict:
    """등록 서비스와 연결 기능을 한국어 기능명·명령으로 검색한다. 등록은 실행 권한이 아니다."""
    return run_hermes_mcp_command('hermes-service-registration', {'query':search_text_value,'offset':offset_value,'limit':limit_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_world_map(map_identifier_value: str | None = None) -> dict:
    """등록 원본과 맵 간 연결을 조회한다. 맵 ID를 지정하면 해당 맵만 반환한다."""
    return run_hermes_mcp_command('hermes-world-map', {'map':map_identifier_value} if map_identifier_value is not None else {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_video_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 동작·영상 서비스와 모드 제안을 읽는다. 첨부·생성은 별도다."""
    return run_hermes_mcp_command('hermes-video-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_video(request_identifier_value: str, video_service_name: str, request_record_value: dict) -> dict:
    """사용자가 요청한 DWPose 또는 Wan 작업을 기존 입력 검증과 GPU 대기열로 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-video',{'request_id':request_identifier_value,'service':video_service_name,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_video_status(request_identifier_value: str, video_service_name: str) -> dict:
    """동작·영상 상태와 검증된 결과 경로를 조회한다. 결과 경로는 형식만 확인하며 파일 존재나 재생 가능성은 확인하지 않는다. 중단 작업 기록의 복구가 따를 수 있으므로 접수 여부만 확인하려면 접수 전용 조회를 사용한다."""
    return run_hermes_mcp_command('hermes-video-status',{'request_id':request_identifier_value,'service':video_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_video_receipts(video_service_name: str) -> dict:
    """동작·영상 서비스별 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-video-history',{'service':video_service_name})


def execute_hermes_cancellation_command(current_command_name,current_request_payload):
    """중지 응답이 불확실해도 이미 접수됐을 수 있으므로 재전송하지 않는다."""
    try:
        current_response_record=run_hermes_mcp_command(current_command_name,current_request_payload)
        if (not isinstance(current_response_record,dict) or current_response_record.get('cancel_requested') is not True
                or current_response_record.get('job_id')!=current_request_payload.get('job_id')):
            raise ValueError('중지 응답 대상 또는 접수 상태 오류')
        return current_response_record
    except Exception:
        raise ToolError('중지 요청 결과를 확인할 수 없습니다. 같은 작업의 실제 상태를 확인하고 자동으로 다시 요청하지 마세요.') from None


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_video(request_identifier_value: str, video_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 동작·영상 작업에 중지를 요청한다. 요청 접수 후 실제 종료 여부는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-video-cancel',{'request_id':request_identifier_value,'service':video_service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_video_resume_proposal(job_identifier_value: str) -> dict:
    """완료된 대화 작업에서 영상 재개 제안을 읽는다. GPU 작업은 실행하지 않는다."""
    return run_hermes_mcp_command('hermes-video-resume-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_video_resume(service_name: str, job_identifier_value: str) -> dict:
    """DWPose·Animate2·VACE·Wan Fun 작업의 재개 입력을 검토한다. 모델 준비 충돌을 확인하며 GPU 작업은 실행하지 않는다."""
    return run_hermes_mcp_command('hermes-video-resume-preview',{'service':service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_video_resume(request_identifier_value: str, service_name: str, job_identifier_value: str, expected_resume_fingerprint: str) -> dict:
    """사용자가 검토한 영상 작업을 재개 접수한다. 불명확하면 원 서비스와 접수 ID를 확인한다."""
    return run_hermes_mcp_command('hermes-video-resume-submit',{'request_id':request_identifier_value,'service':service_name,'job_id':job_identifier_value,'expected_resume_fingerprint':expected_resume_fingerprint})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_video_resume_receipt(request_identifier_value: str) -> dict:
    """영상 재개 접수 기록을 조회한다. 실제 실행·완료는 원 서비스에서 확인한다."""
    return run_hermes_mcp_command('hermes-video-resume-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_flux_resume(request_identifier_value: str, service_name: str, job_identifier_value: str, expected_resume_fingerprint: str) -> dict:
    """검토한 FLUX 작업을 재개 접수한다. 불명확하면 같은 접수 ID와 원 서비스 상태를 확인한다."""
    return run_hermes_mcp_command('hermes-flux-resume-submit',{'request_id':request_identifier_value,'service':service_name,'job_id':job_identifier_value,'expected_resume_fingerprint':expected_resume_fingerprint})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_resume_receipt(request_identifier_value: str) -> dict:
    """FLUX 재개 접수 기록만 조회한다. 실제 실행·완료는 원 서비스에서 확인한다."""
    return run_hermes_mcp_command('hermes-flux-resume-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_resume_proposal(job_identifier_value: str) -> dict:
    """완료된 대화 작업의 FLUX 재개 제안을 읽는다. 재개하지 않는다."""
    return run_hermes_mcp_command('hermes-flux-resume-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_flux_resume(service_name: str, job_identifier_value: str) -> dict:
    """FLUX 기존 작업의 저장 요청·참조를 재개 전 검토한다. 재개 접수나 GPU 사용은 하지 않는다."""
    return run_hermes_mcp_command('hermes-flux-resume-preview',{'service':service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_kimodo_resume(request_identifier_value: str, job_identifier_value: str, expected_resume_fingerprint: str) -> dict:
    """검토한 Kimodo 작업을 GPU 대기열에 재개 접수한다. 불명확하면 같은 접수 ID를 조회한다."""
    return run_hermes_mcp_command('hermes-kimodo-resume-submit',{'request_id':request_identifier_value,'job_id':job_identifier_value,'expected_resume_fingerprint':expected_resume_fingerprint})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_resume_receipt(request_identifier_value: str) -> dict:
    """Kimodo 재개 접수 기록을 조회한다. 실행·완료 상태는 별도다."""
    return run_hermes_mcp_command('hermes-kimodo-resume-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_resume_proposal(job_identifier_value: str) -> dict:
    """완료된 대화 작업의 Kimodo 재개 제안을 읽는다. 재개는 하지 않는다."""
    return run_hermes_mcp_command('hermes-kimodo-resume-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_kimodo_resume(job_identifier_value: str) -> dict:
    """Kimodo 재개를 검토한다. 반환된 결합 확인값으로 접수하며 실제 GPU 가용성은 별도다."""
    return run_hermes_mcp_command('hermes-kimodo-resume-preview',{'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_translation_resume(job_identifier_value: str) -> dict:
    """번역 재개 기록을 확인하고 접수에 필요한 확인값을 반환한다. GPU 작업은 실행하지 않는다."""
    return run_hermes_mcp_command('hermes-translation-resume-preview',{'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_translation_resume(request_identifier_value: str, job_identifier_value: str, expected_resume_fingerprint: str) -> dict:
    """확인한 번역 작업을 GPU 대기열에 재접수한다. 다른 GPU 작업과 경합할 수 있다. 응답이 불확실하면 접수와 원 서비스 상태를 확인하고 새 ID로 재접수하지 않는다."""
    return run_hermes_mcp_command('hermes-translation-resume-submit',{'request_id':request_identifier_value,'job_id':job_identifier_value,'expected_resume_fingerprint':expected_resume_fingerprint})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_translation_resume_receipt(request_identifier_value: str) -> dict:
    """번역 재개 접수 기록을 확인한다. 접수 상태는 작업 완료나 GPU 종료를 보장하지 않는다."""
    return run_hermes_mcp_command('hermes-translation-resume-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_audio_resume(service_name: str, job_identifier_value: str) -> dict:
    """음악·효과음 재개 기록과 모델 다운로드를 확인한다. 대상이 모델 준비 작업이면 다른 준비 작업도 확인한다. unknown은 확인 불가이며 GPU 가용성은 보장하지 않는다."""
    return run_hermes_mcp_command('hermes-audio-resume-preview',{'service':service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_audio_resume(request_identifier_value: str, service_name: str, job_identifier_value: str, expected_resume_fingerprint: str) -> dict:
    """확인한 음악·효과음 작업을 GPU 대기열에 재접수한다. 다른 GPU 작업과 경합할 수 있다. 응답이 불확실하면 접수와 원 서비스 상태를 확인하고 새 ID로 재접수하지 않는다."""
    return run_hermes_mcp_command('hermes-audio-resume-submit',{'request_id':request_identifier_value,'service':service_name,'job_id':job_identifier_value,'expected_resume_fingerprint':expected_resume_fingerprint})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_audio_resume_receipt(request_identifier_value: str) -> dict:
    """음악·효과음 재개 접수 기록을 확인한다. 접수 상태는 작업 완료나 GPU 종료를 보장하지 않는다."""
    return run_hermes_mcp_command('hermes-audio-resume-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def submit_hermes_queue_priority(request_identifier_value: str, service_name: str, job_identifier_value: str, ticket_revision_value: str) -> dict:
    """검토한 대기 작업을 우선 실행한다. 결과 불명 시 같은 접수 기록을 확인한다."""
    return run_hermes_mcp_command('hermes-priority-submit', {'request_id':request_identifier_value,'service':service_name,'id':job_identifier_value,'ticket_revision':ticket_revision_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_queue_priority_receipt(request_identifier_value: str) -> dict:
    """GPU 우선 실행 접수 기록을 읽고 대기 순서는 변경하지 않는다."""
    return run_hermes_mcp_command('hermes-priority-receipt', {'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_queue_priority(service_name: str, job_identifier_value: str) -> dict:
    """원 서비스가 확인된 대기 작업의 우선 실행 대상을 조회하며 순서를 변경하지 않는다."""
    return run_hermes_mcp_command('hermes-priority-preview', {'service':service_name,'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 작가 요청 제안을 검증해 읽는다. 생성·적용은 하지 않는다."""
    return run_hermes_mcp_command('hermes-writer-proposal', {'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_audio_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 음악·효과음 제안을 읽는다. 생성은 하지 않는다."""
    return run_hermes_mcp_command('hermes-audio-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_audio(request_identifier_value: str, audio_service_name: str, request_record_value: dict) -> dict:
    """사용자가 요청한 HeartMuLa 음악 또는 Dasheng 효과음을 기존 GPU 대기열에 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-audio',{'request_id':request_identifier_value,'service':audio_service_name,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_audio_status(request_identifier_value: str, audio_service_name: str) -> dict:
    """오디오 작업 상태와 검증된 동일 출처 결과 경로를 조회한다. 결과 경로는 형식만 확인하며 파일 존재나 재생 가능성은 확인하지 않는다."""
    return run_hermes_mcp_command('hermes-audio-status',{'request_id':request_identifier_value,'service':audio_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_audio_receipts(audio_service_name: str) -> dict:
    """오디오 서비스별 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-audio-history',{'service':audio_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_audio_source_history(audio_service_name: str, offset_value: int = 0, limit_value: int = 10, snapshot_value: str | None = None, query_text: str = '') -> dict:
    """기존 오디오 생성기의 원본 이력과 기록 상태를 조회한다. 후속 페이지에는 snapshot이 필요하다."""
    from tools.review.domains.hermes_agent.audio_operations import validate_hermes_source_history_request
    validate_hermes_source_history_request({'offset':offset_value,'limit':limit_value,'snapshot':snapshot_value,'query':query_text})
    current_request_value={'service':audio_service_name,'offset':offset_value,'limit':limit_value}
    if query_text:current_request_value['query']=query_text
    if snapshot_value is not None:
        current_request_value['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-audio-source-history',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_cleanup(generator_service_name: str) -> dict:
    """이력 정리 후보·차단 수를 조회한다. 숨긴 작업까지 전체 순회할 수 있으며 삭제하지 않는다."""
    return run_hermes_mcp_command('hermes-cleanup-preview',{'service':generator_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_generator_source_history(generator_service_name: str, offset_value: int = 0, limit_value: int = 10, snapshot_value: str | None = None, query_text: str = '') -> dict:
    """생성기·번역·작가 이력을 조회한다. 후속 페이지에는 같은 검색어와 snapshot이 필요하다."""
    from tools.review.domains.hermes_agent.audio_operations import validate_hermes_source_history_request
    validate_hermes_source_history_request({'offset':offset_value,'limit':limit_value,'snapshot':snapshot_value,'query':query_text})
    current_request_value={'service':generator_service_name,'offset':offset_value,'limit':limit_value}
    if query_text:current_request_value['query']=query_text
    if snapshot_value is not None:
        current_request_value['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-generator-source-history',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_audio(request_identifier_value: str, audio_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 오디오 작업에 중지를 요청한다. 요청 접수 후 실제 종료 여부는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-audio-cancel',{'request_id':request_identifier_value,'service':audio_service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_flux_profile(request_identifier_value: str, profile_service_name: str, request_record_value: dict) -> dict:
    """사용자가 요청한 FLUX 프로필 작업을 기존 참조·크기 검증과 공용 GPU 대기열에 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-flux-profile',{'request_id':request_identifier_value,'service':profile_service_name,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_profile_status(request_identifier_value: str, profile_service_name: str) -> dict:
    """접수된 프로필 작업 상태를 조회한다. 결과 경로는 형식만 확인하며 파일 존재나 재생 가능성은 확인하지 않는다. 기존 서비스의 복구가 따를 수 있다."""
    return run_hermes_mcp_command('hermes-flux-profile-status',{'request_id':request_identifier_value,'service':profile_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_flux_profile_receipts(profile_service_name: str) -> dict:
    """해당 FLUX 프로필의 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-flux-profile-history',{'service':profile_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_flux_profile(request_identifier_value: str, profile_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 FLUX 프로필 작업에 중지를 요청한다. 요청 접수 후 실제 종료 여부는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-flux-profile-cancel',{'request_id':request_identifier_value,'service':profile_service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def apply_hermes_writer_proposal(request_identifier_value: str, writer_request_identifier: str, job_identifier_value: str, proposal_hash_value: str) -> dict:
    """사용자가 전체 diff와 근거를 명시적으로 승인한 작가 제안을 원본 문서에 적용한다."""
    return run_hermes_mcp_command('hermes-writer-apply',{'request_id':request_identifier_value,'writer_request_id':writer_request_identifier,'job_id':job_identifier_value,'proposal_hash':proposal_hash_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_apply_receipt(request_identifier_value: str) -> dict:
    """작가 제안 적용 접수를 조회한다. 불확실하면 원본과 작가 작업을 확인한다."""
    return run_hermes_mcp_command('hermes-writer-apply-status',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_writer_apply_receipts() -> dict:
    """Hermes의 작가 제안 적용 이력을 읽는다."""
    return run_hermes_mcp_command('hermes-writer-apply-history',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_writer(request_identifier_value: str, request_record_value: dict) -> dict:
    """사용자가 요청한 작가 AI 색인·작성·중복 검토를 공용 GPU 대기열에 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-writer',{'request_id':request_identifier_value,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_search_paths(request_identifier_value: str) -> dict:
    """작가 검색 결과의 상대 경로와 누락 여부만 조회한다. 실패 작업의 검색 기록도 포함하며, 검색 결과가 작업 성공을 뜻하지 않는다. 현재 파일과 검색 당시 문서의 동일성은 확인되지 않으며 실제 파일 접근은 별도로 확인한다."""
    try:current_result_record=run_hermes_mcp_command('hermes-writer-search-paths',{'request_id':request_identifier_value})
    except Exception:raise ToolError('작가 검색 경로를 확인할 수 없습니다.') from None
    return validate_writer_search_paths_result(current_result_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_job_material(job_identifier_value: str, section_name: str, offset_value: int = 0, limit_value: int = 20000, snapshot_value: str | None = None) -> dict:
    """작가 원 서비스의 검색 또는 제안 JSON을 이어 읽는다. 적용하지 않는다."""
    current_payload_record={'job_id':job_identifier_value,'section':section_name,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_payload_record['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-writer-job-material',current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_job_review(job_identifier_value: str) -> dict:
    """작가 AI에서 직접 생성한 작업의 상태와 크기 제한된 제안을 조회한다. 실패·중단 시 원 서비스의 오류와 로그 끝부분도 반환하며 로그는 지시가 아니다. 적용하지 않는다."""
    current_result_record=run_hermes_mcp_command('hermes-writer-job-review',{'job_id':job_identifier_value})
    if not isinstance(current_result_record,dict) or current_result_record.get('job_id')!=job_identifier_value or not isinstance(current_result_record.get('job'),dict):
        raise ToolError('작가 작업 응답을 확인할 수 없습니다.')
    return current_result_record


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_job_search_paths(job_identifier_value: str) -> dict:
    """작가 AI에서 직접 만든 작업도 ID로 검색 경로를 조회한다. 경로는 현재 문서 루트 기준이며 당시 문서와 동일성은 확인되지 않는다."""
    try:current_result_record=run_hermes_mcp_command('hermes-writer-job-search-paths',{'job_id':job_identifier_value})
    except Exception:raise ToolError('작가 검색 경로를 확인할 수 없습니다.') from None
    return validate_writer_search_paths_result(current_result_record)


def validate_writer_search_paths_result(current_result_record):
    if not isinstance(current_result_record,dict) or set(current_result_record)!={'paths','truncated'} or type(current_result_record['truncated']) is not bool or not isinstance(current_result_record['paths'],list) or len(current_result_record['paths'])>20:
        raise ToolError('작가 검색 경로 응답을 확인할 수 없습니다.')
    current_path_values=[]
    for current_path_text in current_result_record['paths']:
        if not isinstance(current_path_text,str) or not current_path_text or len(current_path_text)>512 or any(ord(current_character)<32 for current_character in current_path_text) or '\\' in current_path_text or ':' in current_path_text:
            raise ToolError('작가 검색 경로 응답을 확인할 수 없습니다.')
        current_path_value=PurePosixPath(current_path_text)
        if current_path_value.is_absolute() or any(current_part.startswith('.') for current_part in current_path_value.parts) or current_path_value.as_posix()!=current_path_text or current_path_text in current_path_values:
            raise ToolError('작가 검색 경로 응답을 확인할 수 없습니다.')
        current_path_values.append(current_path_text)
    return {'paths':current_path_values,'truncated':current_result_record['truncated']}


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_index_status() -> dict:
    '''작가 문서 색인의 최신 상태를 조회한다. 갱신 작업이나 GPU를 실행하지 않는다.'''
    return run_hermes_mcp_command('hermes-writer-index-status',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_status(request_identifier_value: str) -> dict:
    """작가 AI 접수와 제한된 제안 diff를 읽는다. 전체 근거와 적용은 작가 AI 화면에서 확인한다."""
    return run_hermes_mcp_command('hermes-writer-status',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def inspect_hermes_generator_reservation(service_name: str, job_identifier_value: str) -> dict:
    """생성기 GPU 예약과 작업자 리더를 조회한다. 프로세스 종료·예약 해제는 하지 않는다."""
    return run_hermes_mcp_command('hermes-generator-reservation-inspect',{'service':service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def recover_hermes_generator_reservation(request_identifier_value: str, service_name: str, job_identifier_value: str, review_digest_value: str, outside_processes_checked: bool) -> dict:
    """사용자가 별도 GPU 프로세스를 확인한 뒤 검토한 생성기 작업자 그룹을 강제 종료하고 예약을 해제한다."""
    return run_hermes_mcp_command('hermes-generator-reservation-recover',{'request_id':request_identifier_value,'service':service_name,'job_id':job_identifier_value,'review_sha256':review_digest_value,'outside_processes_checked':outside_processes_checked})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_generator_reservation_receipt(request_identifier_value: str) -> dict:
    """생성기 예약 정리의 접수 결과를 조회한다. 확인 불가 결과는 재실행하지 않는다."""
    return run_hermes_mcp_command('hermes-generator-reservation-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def recover_hermes_writer_reservation(request_identifier_value: str, job_identifier_value: str, review_digest_value: str, outside_processes_checked: bool) -> dict:
    """별도 그룹 GPU 프로세스를 확인한 뒤 검토된 작가 그룹을 강제 종료하고 예약을 해제한다."""
    return run_hermes_mcp_command('hermes-writer-reservation-recover',{'request_id':request_identifier_value,'job_id':job_identifier_value,'review_sha256':review_digest_value,'outside_processes_checked':outside_processes_checked})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_writer_reservation_receipt(request_identifier_value: str) -> dict:
    """작가 GPU 예약 정리 접수를 조회한다."""
    return run_hermes_mcp_command('hermes-writer-reservation-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_writer_reservation(job_identifier_value: str) -> dict:
    """실행기가 종료된 작가 GPU 예약의 작업자 신원을 확인한다. 프로세스나 예약은 변경하지 않는다."""
    return run_hermes_mcp_command('hermes-writer-reservation-preview',{'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_writer(request_identifier_value: str, job_identifier_value: str) -> dict:
    """접수 기록과 작업 ID가 일치하는 작가 AI 작업에 중지를 요청한다. 실제 종료는 별도 확인한다."""
    return execute_hermes_cancellation_command('hermes-writer-cancel',{'request_id':request_identifier_value,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_writer_receipts() -> dict:
    """Hermes의 작가 AI 위임 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-writer-history',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def search_hermes_translation_evidence(source_text_value: str) -> dict:
    '''작가 AI 색인에서 번역 관련 문서 근거를 조회한다. 검색 결과는 승인 용어가 아니다.'''
    return run_hermes_mcp_command('hermes-translation-evidence',{'text':source_text_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_translation_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 번역 제안을 읽는다. 번역을 실행하지 않는다."""
    return run_hermes_mcp_command('hermes-translation-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_translation(request_identifier_value: str, request_record_value: dict) -> dict:
    """사용자가 요청한 영어·중국어 간체 번역을 기존 GPU 대기열에 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-translation',{'request_id':request_identifier_value,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_translation_status(request_identifier_value: str) -> dict:
    """번역 접수·결과와 용어 및 조건 검토 항목을 조회한다."""
    return run_hermes_mcp_command('hermes-translation-status',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_translation_receipts() -> dict:
    """Hermes가 위임한 번역 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-translation-history',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_translation(request_identifier_value: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 번역 작업에 중지를 요청한다. 요청 접수 후 실제 종료 여부는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-translation-cancel',{'request_id':request_identifier_value,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
def render_hermes_sprite_clip(draft_record_value: dict, preview_token_value: str, review_digest_value: str, clip_identifier_value: str) -> dict:
    """등록 클립의 프레임 순서·지속 시간으로 앵커 검수 GIF를 생성한다."""
    return run_hermes_mcp_command('hermes-sprite-clip-playback',{'draft':draft_record_value,'token':preview_token_value,'review_sha256':review_digest_value,'clip':clip_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
def render_hermes_sprite_playback(draft_record_value: dict, preview_token_value: str, review_digest_value: str, fps_value: int = 8) -> dict:
    """검토한 앵커 초안으로 균일 FPS의 임시 GIF를 생성한다."""
    return run_hermes_mcp_command('hermes-sprite-playback',{'draft':draft_record_value,'token':preview_token_value,'review_sha256':review_digest_value,'fps':fps_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_sprite_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 미신뢰 스프라이트 앵커 제안을 읽는다."""
    return run_hermes_mcp_command('hermes-sprite-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
def preview_hermes_sprite_anchor(draft_record_value: dict) -> dict:
    """앵커 변경을 검토하고 임시 출력 시트를 생성한다."""
    return run_hermes_mcp_command('hermes-sprite-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_sprite_pending_status() -> dict:
    '''중단된 스프라이트 저장의 대상·백업 해시를 확인한다. 복구하지 않는다.'''
    return run_hermes_mcp_command('hermes-sprite-pending-status',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_sprite_anchor(request_identifier_value: str, draft_record_value: dict, preview_token_value: str, review_digest_value: str) -> dict:
    """확인한 앵커를 저장한다. 기존 중단·사용 중·확인 불가는 접수 전 blocked를 반환한다."""
    return run_hermes_mcp_command('hermes-sprite-save',{'request_id':request_identifier_value,'draft':draft_record_value,'token':preview_token_value,'review_sha256':review_digest_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_sprite_anchor_receipt(request_identifier_value: str) -> dict:
    """스프라이트 저장의 접수 상태를 확인한다."""
    return run_hermes_mcp_command('hermes-sprite-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_sprite_catalog(query_value: str = '', offset_value: int = 0, limit_value: int = 20) -> dict:
    """에셋 저장소에 등록된 스프라이트 시트를 검색한다."""
    return run_hermes_mcp_command('hermes-sprite-catalog',{'query':query_value,'offset':offset_value,'limit':limit_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_sprite_sheet(path_value: str, offset_value: int = 0, limit_value: int = 20, snapshot_value: str | None = None) -> dict:
    """등록 스프라이트의 해시와 프레임·앵커를 읽는다. 이미지 바이트는 제외한다."""
    current_request_record={'path':path_value,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_request_record['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-sprite-detail',current_request_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_kimodo_keyframes(query_value: str = '', offset_value: int = 0, limit_value: int = 20, snapshot_value: str | None = None) -> dict:
    """Kimodo 키프레임을 검색한다. 후속 페이지는 첫 응답의 snapshot을 전달한다."""
    current_request_value={'query':query_value,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_request_value['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-kimodo-keyframes',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def validate_hermes_kimodo_keyframes(keyframe_placements_value: list[dict], frame_count_value: int) -> dict:
    """키프레임 원본과 골격 구조를 검증한다. 접수 시 다시 검증한다."""
    return run_hermes_mcp_command('hermes-kimodo-keyframe-validate',{'keyframes':keyframe_placements_value,'frames':frame_count_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_keyframe_preview(keyframe_identifier_value: str) -> dict:
    """Kimodo가 해시 검증한 키프레임 PNG와 해시를 읽는다."""
    return run_hermes_mcp_command('hermes-kimodo-keyframe-preview',{'keyframe_id':keyframe_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_effect_proposal(job_identifier_value: str) -> dict:
    """완료 답변의 이펙트 좌표 제안만 읽는다. 원본 검증과 사용자 검토는 별도다."""
    return run_hermes_mcp_command('hermes-effect-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_effect_registration(draft_record_value: dict) -> dict:
    """신규 이펙트와 등록 원본·웨이포인트 시트 규격을 검토한다."""
    return run_hermes_mcp_command('hermes-effect-register-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def register_hermes_effect(request_identifier_value: str, draft_record_value: dict, review_sha256_value: str) -> dict:
    """사용자가 검토한 신규 이펙트를 콘텐츠 DB에 등록한다."""
    return run_hermes_mcp_command('hermes-effect-register',{'request_id':request_identifier_value,'draft':draft_record_value,'review_sha256':review_sha256_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_effect_registration_receipt(request_identifier_value: str) -> dict:
    """등록 접수 상태를 확인한다. unknown이면 자동 재등록하지 않는다."""
    return run_hermes_mcp_command('hermes-effect-register-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_waypoint_replacement(draft_record_value: dict) -> dict:
    """교체 대상과 등록 원본·해시를 검토한다. 실제 외형과 사용 맵은 별도 확인한다."""
    return run_hermes_mcp_command('hermes-waypoint-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def replace_hermes_waypoint(request_identifier_value: str, draft_record_value: dict, review_sha256_value: str) -> dict:
    """사용자가 변경·영향을 확인한 경우에만 기존 이펙트를 교체한다."""
    return run_hermes_mcp_command('hermes-waypoint-replace',{'request_id':request_identifier_value,'draft':draft_record_value,'review_sha256':review_sha256_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_waypoint_receipt(request_identifier_value: str) -> dict:
    """교체 접수 상태를 확인한다. unknown이면 재접수하지 않는다."""
    return run_hermes_mcp_command('hermes-waypoint-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_effect_edit(draft_record_value: dict) -> dict:
    """현재 원본과 변경할 좌표를 비교한다."""
    return run_hermes_mcp_command('hermes-effect-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_effect_edit(request_identifier_value: str, draft_record_value: dict, preview_token_value: str) -> dict:
    """사용자가 확인한 이펙트 공용 좌표를 조건부 저장한다."""
    return run_hermes_mcp_command('hermes-effect-save',{'request_id':request_identifier_value,'draft':draft_record_value,'token':preview_token_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_effect_edit_receipt(request_identifier_value: str) -> dict:
    """이펙트 저장 접수를 조회한다."""
    return run_hermes_mcp_command('hermes-effect-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_effect_catalog(query_value: str = '', offset_value: int = 0, limit_value: int = 20) -> dict:
    """콘텐츠 DB의 검수 가능한 이펙트 목록을 조회한다. 로컬 잠금이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-effect-catalog',{'query':query_value,'offset':offset_value,'limit':limit_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_effect_detail(effect_identifier_value: str) -> dict:
    """이펙트 좌표와 시트 정보를 읽고 이미지와 로컬 경로는 제외한다."""
    return run_hermes_mcp_command('hermes-effect-detail',{'id':effect_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_billboard_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 미신뢰 빌보드 제안을 읽는다. 현재값 재확인과 검토가 필요하다."""
    return run_hermes_mcp_command('hermes-billboard-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def load_hermes_billboard_edit(texture_identifier_value: str) -> dict:
    """빌보드 공용 속성과 revision을 불러온다."""
    return run_hermes_mcp_command('hermes-billboard-load',{'texture':texture_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_billboard_edit(draft_record_value: dict) -> dict:
    """변경 전후와 맵 경고를 검토한다. 임시 검증 기록이 생성된다."""
    return run_hermes_mcp_command('hermes-billboard-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_billboard_edit(request_identifier_value: str, draft_record_value: dict, preview_token_value: str, review_digest_value: str) -> dict:
    """사용자가 변경과 경고를 확인한 빌보드 속성을 저장한다."""
    return run_hermes_mcp_command('hermes-billboard-save',{'request_id':request_identifier_value,'draft':draft_record_value,'token':preview_token_value,'review_sha256':review_digest_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_billboard_edit_receipt(request_identifier_value: str) -> dict:
    """빌보드 저장 접수 상태를 조회한다."""
    return run_hermes_mcp_command('hermes-billboard-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_building_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 작업의 건물 앵커 변경 제안을 읽는다."""
    return run_hermes_mcp_command('hermes-building-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_preparation_proposal(job_identifier_value: str) -> dict:
    """완료된 작업의 모델 준비 제안을 읽는다. 다운로드나 GPU 실행은 하지 않는다."""
    return run_hermes_mcp_command('hermes-model-preparation-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_city_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 작업의 도시 맵 변경 제안을 읽는다."""
    return run_hermes_mcp_command('hermes-city-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_city_source(map_identifier_value: str) -> dict:
    """DB 연결 없이 검증된 도시 맵 에셋 원본을 조회한다. DB 세대·리비전과 실행 서비스 반영은 확인하지 않는다."""
    current_result_record=run_hermes_mcp_command('hermes-city-source',{'map':map_identifier_value})
    if (not isinstance(current_result_record,dict) or current_result_record.get('map')!=map_identifier_value
            or not isinstance(current_result_record.get('document'),dict)
            or current_result_record['document'].get('managementId')!='config.city-layouts.'+map_identifier_value
            or not isinstance(current_result_record['document'].get('data'),dict)
            or current_result_record['document']['data'].get('cityId')!=map_identifier_value
            or not isinstance(current_result_record.get('source_sha256'),str)
            or not re.fullmatch(r'[a-f0-9]{64}',current_result_record['source_sha256'])):
        raise ToolError('도시 맵 원본 응답을 확인할 수 없습니다.')
    return current_result_record


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def load_hermes_city_map(map_identifier_value: str) -> dict:
    """도시 맵 DB 원장과 세대·리비전을 읽는다. 로컬 잠금이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-city-load',{'map':map_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_city_map(draft_record_value: dict) -> dict:
    """도시 초안을 검증하고 임시 기록을 남긴다. source_alignment는 DB 문서와 원본·등록부·잠금의 조회 시점 비교이며 실행 중인 서비스 반영은 확인하지 않는다. save_available은 false이며 신규 저장은 중단되어 있다."""
    return run_hermes_mcp_command('hermes-city-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_city_map(request_identifier_value: str, draft_record_value: dict, preview_token_value: str) -> dict:
    """도시 맵 신규 저장은 원본·등록부·백엔드 잠금 동기화가 구현될 때까지 차단된다. 기존 접수의 동일 요청 재조회는 유지한다."""
    return run_hermes_mcp_command('hermes-city-save',{'request_id':request_identifier_value,'draft':draft_record_value,'token':preview_token_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_city_map_receipt(request_identifier_value: str) -> dict:
    """도시 맵 저장 접수 상태를 확인한다."""
    return run_hermes_mcp_command('hermes-city-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_city_map_receipts() -> dict:
    """도시 맵 저장 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-city-history',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_field_map_receipt(request_identifier_value: str) -> dict:
    """야외 맵 저장 접수 상태를 확인한다. 접수 불명 시 원본을 살펴본다."""
    return run_hermes_mcp_command('hermes-field-receipt', {'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_field_map_receipts() -> dict:
    """야외 맵 저장 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-field-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_field_map_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 야외 셀 제안을 읽는다. 원본 리비전과 기존 편집기 검증이 별도로 필요하다."""
    return run_hermes_mcp_command('hermes-field-proposal',{'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_field_region(map_identifier_value: str, column_value: int = 0, row_value: int = 0, width_value: int = 8, height_value: int = 8, offset_value: int = 0, limit_value: int = 20, revision_value: str | None = None) -> dict:
    """등록 에셋에서 야외 맵 영역과 배치 페이지를 읽는다. asset: 지문은 페이지 조회 전용이며 편집 리비전이 아니다. blocked는 최종 통행 판정이 아니다."""
    current_request_value = {'map':map_identifier_value,'column':column_value,'row':row_value,'width':width_value,'height':height_value,'offset':offset_value,'limit':limit_value}
    if revision_value is not None:
        current_request_value['revision'] = revision_value
    return run_hermes_mcp_command('hermes-field-region',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def load_hermes_field_map(map_identifier_value: str) -> dict:
    """야외 맵 편집 원본과 리비전을 읽는다. 로컬 잠금 파일이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-field-load', {'map':map_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_field_map(draft_record_value: dict) -> dict:
    """야외 맵 초안을 기존 편집기로 검증한다. save_available이 false면 저장이 차단되며 save_block_reason이 database면 DB 모드 제한, interrupted면 이전 저장 중단이다. 사유 미제공이나 null은 확인 불가다. false와 null에서 신규 저장을 보류하며 true도 이후 저장 성공을 보장하지 않는다. 로컬 임시 초안 기록이 생긴다."""
    return run_hermes_mcp_command('hermes-field-preview', {'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_field_map(request_identifier_value: str, draft_record_value: dict, preview_token_value: str) -> dict:
    """사용자가 승인한 야외 맵 초안을 저장한다. 파일 모드에서는 원본·등록부·잠금과 카탈로그가 바뀔 수 있고 DB 모드 신규 저장은 중단된다. 응답 유실 시 같은 ID를 유지한다."""
    return run_hermes_mcp_command('hermes-field-save', {'request_id':request_identifier_value,'draft':draft_record_value,'token':preview_token_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_building_anchor(draft_record_value: dict) -> dict:
    """건물 앵커 전후 값과 사용 맵을 검토한다. 콘텐츠 세대와 현재값을 확인한다."""
    return run_hermes_mcp_command('hermes-building-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_building_anchor(request_identifier_value: str, draft_record_value: dict, review_digest_value: str) -> dict:
    """검토된 건물 앵커를 저장한다. 응답 유실 시 접수를 확인한다."""
    return run_hermes_mcp_command('hermes-building-save',{'request_id':request_identifier_value,'draft':draft_record_value,'review_sha256':review_digest_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_building_anchor_receipt(request_identifier_value: str) -> dict:
    """건물 앵커 저장 접수를 확인한다."""
    return run_hermes_mcp_command('hermes-building-receipt',{'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_building_catalog(search_text_value: str = '', offset_value: int = 0, limit_value: int = 20, snapshot_value: str | None = None) -> dict:
    """건물 원본·사용 맵·표시 속성 조회. 후속 페이지는 같은 snapshot을 전달한다. 로컬 잠금이 생길 수 있다."""
    current_payload_record={'query':search_text_value,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:current_payload_record['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-building-catalog', current_payload_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_billboard_catalog(category_name: str | None = None, search_text_value: str = '', offset_value: int = 0, limit_value: int = 20) -> dict:
    """등록 빌보드의 용도·표시 속성·맵 참조를 조회한다. 로컬 잠금 파일이 생성될 수 있다."""
    current_request_record = {'query':search_text_value, 'offset':offset_value, 'limit':limit_value}
    if category_name is not None:
        current_request_record['category'] = category_name
    return run_hermes_mcp_command('hermes-billboard-catalog', current_request_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_model_preparation_receipts() -> dict:
    """최근 모델 준비 접수 기록을 조회한다. 모델 완료 상태는 별도로 확인한다."""
    return run_hermes_mcp_command('hermes-model-prepare-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=True))
def prepare_hermes_managed_model(request_identifier_value: str, model_service_name: str) -> dict:
    """사용자가 명시한 모델을 준비한다. 다운로드·디스크 사용·서비스별 GPU 작업이 발생할 수 있다. Hermes 모델의 blocked/model_in_use 또는 preparation_unknown은 접수 전 차단이며 기록이 없다. 응답 유실 시 같은 ID를 유지하고 상태를 확인한다."""
    current_result_record = run_hermes_mcp_command('hermes-model-prepare', {'request_id':request_identifier_value, 'service':model_service_name})
    if (not isinstance(current_result_record,dict) or current_result_record.get('request_id') != request_identifier_value
            or current_result_record.get('service') != model_service_name or current_result_record.get('state') not in ('accepted','unknown','blocked')
            or (current_result_record.get('state') == 'blocked' and (model_service_name != 'hermes-model' or current_result_record.get('reason') not in ('model_in_use','preparation_unknown')))):
        raise ToolError('모델 준비 접수 결과를 확인할 수 없습니다. 같은 요청 ID와 원 서비스 상태를 확인하고 자동 재접수하지 마세요.')
    return current_result_record


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_preparation_receipt(request_identifier_value: str, model_service_name: str) -> dict:
    """요청 ID와 서비스가 포함된 모델 준비 접수 기록을 읽는다. 응답 당시 기록이며 현재 모델 준비 완료 여부는 별도 조회한다."""
    return run_hermes_mcp_command('hermes-model-prepare-status', {'request_id':request_identifier_value, 'service':model_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_capture_proposal(hermes_job_identifier: str) -> dict:
    """완료된 대화의 캡처 제안과 맵 등록 여부를 읽는다. 등록 상태는 실행 가능성을 뜻하지 않으며 캡처 실행은 지원하지 않는다."""
    return run_hermes_mcp_command('hermes-capture-proposal', {'id':hermes_job_identifier})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_capture_status(request_identifier_value: str, capture_service_name: str) -> dict:
    """검수 캡처 접수와 검증된 작업 상태를 읽는다. 캡처 실행은 지원하지 않는다."""
    return run_hermes_mcp_command('hermes-capture-status', {'request_id':request_identifier_value, 'service':capture_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_build_status() -> dict:
    """Kimodo MIGraphX 빌드 기록을 조회한다. 캐시 유효성과 작업 생존 여부는 별도 확인한다."""
    return run_hermes_mcp_command('hermes-kimodo-build-status', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_readiness(model_service_name: str) -> dict:
    """서비스 판정과 별도 파일·다운로드 상태를 조회한다. 누락은 확인 불가이며 로컬 잠금이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-model-readiness', {'service':model_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_map_database_receipt(database_request_identifier: str, request_sha256_value: str) -> dict:
    """DB 접수의 ID·요청 해시 일치만 확인한다. not_found도 재접수 안전을 보장하지 않으며 파일 동기화는 별도다."""
    return run_hermes_mcp_command('hermes-map-database-receipt',{'database_request_id':database_request_identifier,'request_sha256':request_sha256_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_content_database_status() -> dict:
    """콘텐츠 DB·원장과 맵 원본·중단 저장 상태를 조회한다. local_map_mode는 Hermes 서비스 프로세스 설정이며 원 서비스나 백엔드의 실제 모드를 보장하지 않는다. 백업 해시 비교는 복구 완료를 뜻하지 않는다."""
    return run_hermes_mcp_command('hermes-content-database-status', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_download_status() -> dict:
    '''관리도구에 기록된 모델 다운로드 상태를 조회한다. 기록 정리와 다운로드 실행은 하지 않는다.'''
    return run_hermes_mcp_command('hermes-model-download-status',{})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_inventory() -> dict:
    """모델별 파일 수와 용량을 조회한다. 파일 존재는 준비 완료를 뜻하지 않는다."""
    return run_hermes_mcp_command('hermes-model-inventory', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_management_capabilities() -> dict:
    """주요 관리 명령의 입력·영향·GPU·재시도와 실제 연결 범위를 조회한다."""
    return run_hermes_mcp_command('hermes-capabilities', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_delegation_receipts() -> dict:
    """최근 위임 접수 ID, 상태와 작업 ID를 조회한다. 입력은 반환하지 않는다."""
    return run_hermes_mcp_command('hermes-delegation-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_job_status(request_identifier_value: str) -> dict:
    """위임 접수 ID의 Kimodo 상태를 읽는다. 기존 Kimodo 서비스가 중단 작업을 복구 표시할 수 있다."""
    return run_hermes_mcp_command('hermes-delegation-job-status', {'request_id': request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_kimodo_delegation(request_identifier_value: str, confirmed_job_identifier: str) -> dict:
    """해당 위임 기록과 작업 ID가 일치할 때 중지를 요청한다. 실제 종료는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-delegation-cancel', {'request_id': request_identifier_value, 'job_id': confirmed_job_identifier})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_delegation_status(request_identifier_value: str) -> dict:
    """Kimodo 접수 ID·서비스와 확인 필요 또는 작업 ID를 조회한다. 작업 상태·생존·결과를 확인하거나 복구·생성을 실행하지 않는다."""
    return run_hermes_mcp_command('hermes-delegation-status', {'request_id': request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변에서 검증된 Kimodo 입력 제안을 조회한다. 생성하지 않는다."""
    return run_hermes_mcp_command('hermes-kimodo-proposal', {'id': job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_proposal(job_identifier_value: str) -> dict:
    """완료된 Hermes 답변의 검증된 FLUX 제안을 읽는다. 생성하지 않는다."""
    return run_hermes_mcp_command('hermes-flux-proposal', {'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_flux_generation(request_identifier_value: str, generation_request_record: dict) -> dict:
    """사용자가 요청한 FLUX 이미지 생성을 위임한다. 요청은 action=generate, prompt, images(PNG base64 목록), width, height, steps=16, seed를 포함한다. 같은 ID·입력만 재시도하고 불확실하면 이력을 확인한다."""
    return run_hermes_mcp_command('hermes-delegate-flux-image', {'request_id':request_identifier_value, 'request':generation_request_record})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_flux_delegations() -> dict:
    """FLUX 위임 접수 이력을 조회한다. 입력과 해시는 반환하지 않는다."""
    return run_hermes_mcp_command('hermes-flux-delegation-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_delegation(request_identifier_value: str) -> dict:
    """FLUX 위임 접수와 기존 서비스 작업 상태를 조회한다. 결과 경로는 형식만 확인하며 파일 존재나 재생 가능성은 확인하지 않는다. 상태 조회가 복구를 수행할 수 있다."""
    return run_hermes_mcp_command('hermes-flux-delegation-status', {'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_flux_delegation(request_identifier_value: str, confirmed_job_identifier: str) -> dict:
    """FLUX 위임 기록과 확인한 작업 ID가 일치할 때 중지 요청한다. 실제 종료는 별도로 확인한다."""
    return execute_hermes_cancellation_command('hermes-flux-delegation-cancel', {'request_id':request_identifier_value, 'job_id':confirmed_job_identifier})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_kimodo_generation(request_identifier_value: str, generation_request_record: dict) -> dict:
    """요청된 Kimodo 생성을 공용 대기열에 접수한다. 같은 ID는 동일 입력에만 재사용하며 unknown은 자동 재접수하지 않는다. 완료는 Kimodo에서 확인한다."""
    return run_hermes_mcp_command('hermes-delegate-kimodo', {'request_id': request_identifier_value, 'request': generation_request_record})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_management_status() -> dict:
    """동일한 모델 준비·GPU·대기열 관측을 조회한다. GPU 추론은 시작하지 않는다."""
    return run_hermes_mcp_command('hermes-management-status', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_gpu_queue_status() -> dict:
    """제한된 대기열 관측과 기존 GPU 상태 형식을 반환한다. 관측 과정에서 로컬 잠금을 만들 수 있다."""
    try:
        hermes_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        hermes_management_record=run_hermes_mcp_command('hermes-management-status',{})
        hermes_queue_record=hermes_management_record.get('queue') if isinstance(hermes_management_record,dict) else None
        if not isinstance(hermes_queue_record,dict) or hermes_queue_record.get('status')!='available' or not isinstance(hermes_queue_record.get('jobs'),list):
            raise ValueError('GPU 대기열을 확인할 수 없습니다.')
        hermes_job_records=hermes_queue_record['jobs']
        if any(not isinstance(current_job_record,dict) or not isinstance(current_job_record.get('id'),str) or not isinstance(current_job_record.get('service'),str) for current_job_record in hermes_job_records):
            raise ValueError('GPU 대기열 응답 형식이 올바르지 않습니다.')
        hermes_http_request = urllib.request.Request(hermes_gateway_address + '/management/gpu-status', headers={'Origin':hermes_gateway_address}, method='GET')
        hermes_http_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectHermesGatewayRedirect())
        with hermes_http_opener.open(hermes_http_request, timeout=30) as hermes_http_response:
            hermes_response_bytes = hermes_http_response.read(2_000_001)
        if len(hermes_response_bytes) > 2_000_000:
            raise ValueError('관리 게이트웨이 응답이 너무 큽니다.')
        hermes_gpu_record = json.loads(hermes_response_bytes)
        if not isinstance(hermes_gpu_record, dict):
            raise ValueError('GPU 상태 응답 형식이 올바르지 않습니다.')
        return {'queried_at': datetime.now(timezone.utc).isoformat(), 'detail': 'GPU 측정은 공용 상태 조회의 짧은 캐시를 사용할 수 있습니다. 대기열 관측은 로컬 잠금을 만들 수 있습니다.', 'jobs': [{'id':current_job_record['id'],'service':current_job_record['service']} for current_job_record in hermes_job_records], 'gpu_status': hermes_gpu_record}
    except (OSError, ValueError, TypeError) as hermes_gateway_error:
        raise ToolError('GPU 대기열 조회 실패: ' + str(hermes_gateway_error)) from hermes_gateway_error


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_coding_task(job_identifier_value: str) -> dict:
    """해당 작업에 중지 요청을 보낸다. 실제 종료는 별도로 조회한다."""
    current_cancel_response=run_hermes_mcp_command('hermes-cancel', {'id':job_identifier_value})
    if not isinstance(current_cancel_response,dict) or current_cancel_response.get('id')!=job_identifier_value or current_cancel_response.get('cancel_requested') is not True or current_cancel_response.get('status') not in ('queued','running','cancelled'):
        raise ToolError('중지 접수를 확인할 수 없습니다. 같은 작업의 실제 상태를 확인하고 자동으로 다시 요청하지 마세요.')
    return current_cancel_response


if __name__ == '__main__':
    hermes_mcp_server.run(transport='stdio')
