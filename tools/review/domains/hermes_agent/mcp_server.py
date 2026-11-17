"""Codex가 공용 게이트웨이에 격리 Hermes 작업을 위임하는 MCP 어댑터."""
import json
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

hermes_mcp_server = MCPServer('slime-hermes', instructions='Hermes는 격리된 관리도구 사본에서 작업합니다. 요청 식별자를 유지해 중복 접수를 방지하고 완료 후 diff와 로그를 검토하세요.')


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


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_coding_task(job_identifier_value: str) -> dict:
    """접수된 작업의 상태·검토용 diff·로그를 조회한다."""
    return run_hermes_mcp_command('hermes-detail', {'id':job_identifier_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def list_hermes_coding_tasks() -> dict:
    """공용 기록의 Hermes 작업 이력을 조회한다."""
    return run_hermes_mcp_command('hermes-history', {})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False))
def read_hermes_task_diff(job_identifier_value: str, byte_offset_value: int = 0, byte_limit_value: int = 65536) -> dict:
    """종료된 작업의 전체 diff를 정확한 바이트 범위의 base64 조각으로 읽는다."""
    return run_hermes_mcp_command('hermes-diff', {'id':job_identifier_value, 'offset':byte_offset_value, 'limit':byte_limit_value})


@hermes_mcp_server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
def cancel_hermes_coding_task(job_identifier_value: str) -> dict:
    """해당 작업에 중지 요청을 보낸다. 실제 종료는 별도로 조회한다."""
    return run_hermes_mcp_command('hermes-cancel', {'id':job_identifier_value})


if __name__ == '__main__':
    hermes_mcp_server.run(transport='stdio')
