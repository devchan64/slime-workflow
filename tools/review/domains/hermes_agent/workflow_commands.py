"""대화 세션별 워크플로우의 관리 게이트웨이 명령."""
import re

from .workflow_catalog import read_workflow_generator_catalog
from .workflow_run_store import WorkflowRunStore


def execute_workflow_command(workflow_root_directory, current_command_name, current_payload_record):
    if current_command_name == "hermes-workflow-catalog":
        if current_payload_record:
            raise ValueError("카탈로그 조회에는 입력이 필요하지 않습니다.")
        return {"generators": read_workflow_generator_catalog()}
    required_field_names = {"session_id", "run_id"}
    if current_command_name == "hermes-workflow-list":
        required_field_names = {"session_id", "category", "state"}
    elif current_command_name == "hermes-workflow-register":
        required_field_names.add("steps")
    elif current_command_name not in ("hermes-workflow-view", "hermes-workflow-cancel"):
        raise ValueError("지원하지 않는 워크플로우 명령입니다.")
    if current_payload_record.keys() != required_field_names:
        raise ValueError("워크플로우 명령 필드를 확인하세요.")
    for current_field_name in required_field_names.intersection({"session_id", "run_id"}):
        current_identifier_value = current_payload_record[current_field_name]
        if not isinstance(current_identifier_value, str) or not re.fullmatch("[a-f0-9]{32}", current_identifier_value):
            raise ValueError("세션과 실행 ID는 32자리 소문자 16진수입니다.")
    workflow_storage_directory = workflow_root_directory / ".local" / "hermes-workflows"
    workflow_storage_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    workflow_run_store = WorkflowRunStore(workflow_storage_directory / "runs.sqlite3")
    if current_command_name == "hermes-workflow-list":
        return workflow_run_store.find_session_workflow_steps(current_payload_record["session_id"],
            current_payload_record["category"], current_payload_record["state"])
    workflow_run_identifier = current_payload_record["run_id"]
    conversation_session_identifier = current_payload_record["session_id"]
    if current_command_name == "hermes-workflow-register":
        workflow_run_store.register_workflow_run(workflow_run_identifier, conversation_session_identifier,
                                                 current_payload_record["steps"])
    if current_command_name == "hermes-workflow-cancel":
        workflow_run_store.request_workflow_cancellation(workflow_run_identifier, conversation_session_identifier)
    return workflow_run_store.read_session_run_view(workflow_run_identifier, conversation_session_identifier)
