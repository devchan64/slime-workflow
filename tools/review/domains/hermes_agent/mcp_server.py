"""Codex가 공용 게이트웨이에 격리 Hermes 작업을 위임하는 MCP 어댑터."""
import json
from datetime import datetime, timezone
import os
from pathlib import Path
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
        hermes_error_bytes = hermes_http_error.read(16_000)
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
    """격리 코딩 작업을 접수한다. 선택한 공용 회귀 모듈은 최종 수정 후 독립 실행한다. 응답 유실 시 같은 식별자를 사용한다."""
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
    """세션의 이전 완료 작업 문맥을 포함해 격리 Hermes 작업을 접수한다."""
    hermes_request_record = {'session_id': session_identifier_value, 'request_id': request_identifier_value, 'prompt': message_text_value}
    if verification_module_names:
        hermes_request_record['verification_modules'] = verification_module_names
    return run_hermes_mcp_command('hermes-session-submit', hermes_request_record)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_session_view(session_identifier_value: str) -> dict:
    """최근 세션 메시지와 연결된 작업의 상태·최종 응답을 조회한다."""
    return run_hermes_mcp_command('hermes-session-view', {'session_id': session_identifier_value})


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
    """동작·영상 상태와 검증된 결과 경로를 조회한다. 기존 작업 복구가 따를 수 있다."""
    return run_hermes_mcp_command('hermes-video-status',{'request_id':request_identifier_value,'service':video_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_video_receipts(video_service_name: str) -> dict:
    """동작·영상 서비스별 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-video-history',{'service':video_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_video(request_identifier_value: str, video_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 동작·영상 작업에 중지를 요청한다."""
    return run_hermes_mcp_command('hermes-video-cancel',{'request_id':request_identifier_value,'service':video_service_name,'job_id':job_identifier_value})


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
    """오디오 작업 상태와 검증된 동일 출처 결과 경로를 조회한다."""
    return run_hermes_mcp_command('hermes-audio-status',{'request_id':request_identifier_value,'service':audio_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_audio_receipts(audio_service_name: str) -> dict:
    """오디오 서비스별 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-audio-history',{'service':audio_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_audio_source_history(audio_service_name: str, offset_value: int = 0, limit_value: int = 10, snapshot_value: str | None = None) -> dict:
    """기존 오디오 생성기의 원본 이력과 기록 상태를 조회한다. 후속 페이지에는 snapshot이 필요하다."""
    current_request_value={'service':audio_service_name,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:
        current_request_value['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-audio-source-history',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_generator_source_history(generator_service_name: str, offset_value: int = 0, limit_value: int = 10, snapshot_value: str | None = None) -> dict:
    """FLUX·Kimodo·DWPose·Wan·번역·작가의 원본 이력과 기록 상태를 복구 없이 조회한다."""
    current_request_value={'service':generator_service_name,'offset':offset_value,'limit':limit_value}
    if snapshot_value is not None:
        current_request_value['snapshot']=snapshot_value
    return run_hermes_mcp_command('hermes-generator-source-history',current_request_value)


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_audio(request_identifier_value: str, audio_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 오디오 작업에 중지를 요청한다."""
    return run_hermes_mcp_command('hermes-audio-cancel',{'request_id':request_identifier_value,'service':audio_service_name,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_flux_profile(request_identifier_value: str, profile_service_name: str, request_record_value: dict) -> dict:
    """사용자가 요청한 FLUX 프로필 작업을 기존 참조·크기 검증과 공용 GPU 대기열에 접수한다."""
    return run_hermes_mcp_command('hermes-delegate-flux-profile',{'request_id':request_identifier_value,'service':profile_service_name,'request':request_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_flux_profile_status(request_identifier_value: str, profile_service_name: str) -> dict:
    """접수된 프로필 작업 상태를 조회한다. 기존 서비스의 복구가 따를 수 있다."""
    return run_hermes_mcp_command('hermes-flux-profile-status',{'request_id':request_identifier_value,'service':profile_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_flux_profile_receipts(profile_service_name: str) -> dict:
    """해당 FLUX 프로필의 Hermes 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-flux-profile-history',{'service':profile_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_flux_profile(request_identifier_value: str, profile_service_name: str, job_identifier_value: str) -> dict:
    """사용자가 확인한 FLUX 프로필 작업에 중지를 요청한다."""
    return run_hermes_mcp_command('hermes-flux-profile-cancel',{'request_id':request_identifier_value,'service':profile_service_name,'job_id':job_identifier_value})


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
def read_hermes_writer_status(request_identifier_value: str) -> dict:
    """작가 AI 접수와 제한된 제안 diff를 읽는다. 전체 근거와 적용은 작가 AI 화면에서 확인한다."""
    return run_hermes_mcp_command('hermes-writer-status',{'request_id':request_identifier_value})


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
    return run_hermes_mcp_command('hermes-writer-cancel',{'request_id':request_identifier_value,'job_id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_writer_receipts() -> dict:
    """Hermes의 작가 AI 위임 접수 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-writer-history',{})


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
    """사용자가 확인한 번역 작업에 중지를 요청한다."""
    return run_hermes_mcp_command('hermes-translation-cancel',{'request_id':request_identifier_value,'job_id':job_identifier_value})


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


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_sprite_anchor(request_identifier_value: str, draft_record_value: dict, preview_token_value: str, review_digest_value: str) -> dict:
    """사용자가 시트 재패킹과 변경 내용을 확인한 앵커를 저장한다."""
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
def load_hermes_city_map(map_identifier_value: str) -> dict:
    """도시 맵 DB 원장과 세대·리비전을 읽는다. 로컬 잠금이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-city-load',{'map':map_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def preview_hermes_city_map(draft_record_value: dict) -> dict:
    """도시 초안을 기존 편집기로 검증하고 임시 기록을 남긴다."""
    return run_hermes_mcp_command('hermes-city-preview',{'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_city_map(request_identifier_value: str, draft_record_value: dict, preview_token_value: str) -> dict:
    """사용자가 승인한 도시 원장을 콘텐츠 DB에 저장한다. 응답 유실 시 같은 ID를 유지한다."""
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


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_field_region(map_identifier_value: str, column_value: int = 0, row_value: int = 0, width_value: int = 8, height_value: int = 8, offset_value: int = 0, limit_value: int = 20, revision_value: str | None = None) -> dict:
    """야외 맵의 제한된 영역과 배치 페이지를 읽는다. blocked는 최종 통행 판정이 아니다."""
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
    """야외 맵 초안을 기존 편집기로 검증한다. 로컬 임시 초안 기록이 생긴다."""
    return run_hermes_mcp_command('hermes-field-preview', {'draft':draft_record_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=True, open_world_hint=False))
def save_hermes_field_map(request_identifier_value: str, draft_record_value: dict, preview_token_value: str) -> dict:
    """사용자가 승인한 야외 맵 초안을 저장한다. 원본·등록부·잠금과 카탈로그가 바뀔 수 있다. 응답 유실 시 같은 ID를 유지한다."""
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
    """사용자가 명시한 모델을 준비한다. 다운로드·디스크 사용·서비스별 GPU 작업이 발생할 수 있다. 응답 유실 시 같은 ID를 유지하고 상태를 확인한다."""
    return run_hermes_mcp_command('hermes-model-prepare', {'request_id':request_identifier_value, 'service':model_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_preparation_receipt(request_identifier_value: str, model_service_name: str) -> dict:
    """모델 준비 접수 기록을 읽는다. 모델 준비 완료 여부는 별도 조회한다."""
    return run_hermes_mcp_command('hermes-model-prepare-status', {'request_id':request_identifier_value, 'service':model_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_kimodo_build_status() -> dict:
    """Kimodo MIGraphX 빌드 기록을 조회한다. 캐시 유효성과 작업 생존 여부는 별도 확인한다."""
    return run_hermes_mcp_command('hermes-kimodo-build-status', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_model_readiness(model_service_name: str) -> dict:
    """서비스 판정과 별도 파일·다운로드 상태를 조회한다. 누락은 확인 불가이며 로컬 잠금이 생길 수 있다."""
    return run_hermes_mcp_command('hermes-model-readiness', {'service':model_service_name})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_content_database_status() -> dict:
    """콘텐츠 DB 저장 세대와 원장 반영 상태를 조회한다. 서비스 연결 실패는 미확인으로 표시한다."""
    return run_hermes_mcp_command('hermes-content-database-status', {})


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
    return run_hermes_mcp_command('hermes-delegation-cancel', {'request_id': request_identifier_value, 'job_id': confirmed_job_identifier})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_delegation_status(request_identifier_value: str) -> dict:
    """위임 접수 ID로 확인 필요 또는 기존 작업 ID를 조회한다. 재접수하지 않는다."""
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
    """FLUX 위임 접수와 기존 서비스 작업 상태를 조회한다. 상태 조회가 복구를 수행할 수 있다."""
    return run_hermes_mcp_command('hermes-flux-delegation-status', {'request_id':request_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_flux_delegation(request_identifier_value: str, confirmed_job_identifier: str) -> dict:
    """FLUX 위임 기록과 확인한 작업 ID가 일치할 때 중지 요청한다. 실제 종료는 별도로 확인한다."""
    return run_hermes_mcp_command('hermes-flux-delegation-cancel', {'request_id':request_identifier_value, 'job_id':confirmed_job_identifier})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def delegate_hermes_kimodo_generation(request_identifier_value: str, generation_request_record: dict) -> dict:
    """요청된 Kimodo 생성을 공용 대기열에 접수한다. 같은 ID는 동일 입력에만 재사용하며 unknown은 자동 재접수하지 않는다. 완료는 Kimodo에서 확인한다."""
    return run_hermes_mcp_command('hermes-delegate-kimodo', {'request_id': request_identifier_value, 'request': generation_request_record})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_management_status() -> dict:
    """동일한 모델 준비·GPU·대기열 관측을 조회한다. GPU 추론은 시작하지 않는다."""
    return run_hermes_mcp_command('hermes-management-status', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_gpu_queue_status() -> dict:
    """기존 게이트웨이의 GPU 상태와 대기 작업을 조회한다. 조회만 하며 GPU 측정은 짧게 캐시될 수 있다."""
    try:
        hermes_gateway_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
        hermes_http_request = urllib.request.Request(hermes_gateway_address + '/management/gpu-queue', headers={'Origin': hermes_gateway_address}, method='GET')
        hermes_http_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectHermesGatewayRedirect())
        with hermes_http_opener.open(hermes_http_request, timeout=30) as hermes_http_response:
            hermes_response_bytes = hermes_http_response.read(2_000_001)
        if len(hermes_response_bytes) > 2_000_000:
            raise ValueError('관리 게이트웨이 응답이 너무 큽니다.')
        hermes_status_record = json.loads(hermes_response_bytes)
        if not isinstance(hermes_status_record, dict) or not isinstance(hermes_status_record.get('jobs'), list) or not isinstance(hermes_status_record.get('gpu_status'), dict):
            raise ValueError('GPU 상태 응답 형식이 올바르지 않습니다.')
        return {'queried_at': datetime.now(timezone.utc).isoformat(), 'detail': 'GPU 측정은 공용 상태 조회의 짧은 캐시를 사용할 수 있습니다.', 'jobs': hermes_status_record['jobs'], 'gpu_status': hermes_status_record['gpu_status']}
    except (OSError, ValueError, TypeError) as hermes_gateway_error:
        raise ToolError('GPU 대기열 조회 실패: ' + str(hermes_gateway_error)) from hermes_gateway_error


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_coding_task(job_identifier_value: str) -> dict:
    """해당 작업에 중지 요청을 보낸다. 실제 종료는 별도로 조회한다."""
    return run_hermes_mcp_command('hermes-cancel', {'id':job_identifier_value})


if __name__ == '__main__':
    hermes_mcp_server.run(transport='stdio')
