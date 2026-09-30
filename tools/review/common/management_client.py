"""GUI 전용 HTTP 명령 클라이언트. 로컬 작업 서비스로 우회하지 않는다."""
import os
from tools.review.common.management_gateway import execute_management_command
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address


def execute_remote_management_command(service_command_name, operation_command_name, command_payload_value):
    gateway_base_address = validate_gateway_address(os.environ.get('SLIME_MANAGEMENT_GATEWAY_URL', DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command(service_command_name, operation_command_name, command_payload_value, gateway_base_address)
