"""준비된 단계를 기존 생성기 접수 명령으로 보내고 번역 완료를 관측한다."""
import os
from .workflow_catalog import WORKFLOW_GENERATOR_COMMANDS
from workflow.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from workflow.common.management_gateway import execute_management_command


def call_workflow_management_command(current_command_name, current_payload_record):
    management_gateway_address = validate_gateway_address(os.environ.get(
        "SLIME_MANAGEMENT_GATEWAY_URL", DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command("hermes-agent", current_command_name, current_payload_record,
                                      management_gateway_address)


def advance_workflow_run(workflow_run_store, workflow_run_identifier, gateway_command_handler=call_workflow_management_command):
    for current_step_record in workflow_run_store.list_run_step_records(workflow_run_identifier):
        current_step_identifier = current_step_record["step_id"]
        current_generator_commands = WORKFLOW_GENERATOR_COMMANDS.get(current_step_record["generator"])
        audio_step_selected = current_step_record["generator"] == "sfx-dasheng-audiogen"
        service_request_fields = {"service": current_step_record["generator"]} if audio_step_selected else {}
        if current_step_record["state"] == "submitting":
            expected_service_name = current_step_record["generator"]
            if current_generator_commands is None:
                workflow_run_store.record_source_observation(current_step_record["request_id"], "unknown")
                continue
            translation_step_selected = expected_service_name == "prompt-translation"
            status_command_name = current_generator_commands["status"]
            try:
                current_status_record = gateway_command_handler(status_command_name, {
                    **service_request_fields, "request_id": current_step_record["request_id"]})
            except (ValueError, OSError, RuntimeError):
                workflow_run_store.record_source_observation(current_step_record["request_id"], "unknown")
                continue
            current_receipt_record = current_status_record.get("receipt") if isinstance(current_status_record, dict) else None
            if (not isinstance(current_receipt_record, dict) or current_receipt_record.get("state") != "accepted"
                    or current_receipt_record.get("service") != expected_service_name
                    or current_receipt_record.get("request_id") != current_step_record["request_id"]
                    or not isinstance(current_receipt_record.get("job_id"), str) or not current_receipt_record["job_id"]
                    or current_step_record.get("source_job_id") not in (None, current_receipt_record["job_id"])):
                workflow_run_store.record_source_observation(current_step_record["request_id"], "unknown")
                continue
            observed_job_record = current_status_record.get("job")
            if (not isinstance(observed_job_record, dict) or
                    ("id" in observed_job_record and observed_job_record["id"] != current_receipt_record["job_id"])):
                workflow_run_store.record_source_observation(current_step_record["request_id"], "unknown")
                continue
            observed_job_state = observed_job_record.get("status")
            if observed_job_state not in ("queued", "running", "paused", "failed", "cancelled", "canceled", "completed"):
                observed_job_state = "unknown"
            workflow_run_store.record_source_observation(current_step_record["request_id"], observed_job_state,
                                                        current_receipt_record["job_id"])
            if (observed_job_state in ("queued", "running", "paused") and current_step_record["cancel_delivery"] == "pending"
                    and workflow_run_store.claim_pending_cancellation(current_step_record["request_id"])):
                cancel_command_name = current_generator_commands["cancel"]
                try:
                    cancel_response_record = gateway_command_handler(cancel_command_name, {
                        **service_request_fields, "request_id": current_step_record["request_id"], "job_id": current_receipt_record["job_id"]})
                except (ValueError, OSError, RuntimeError):
                    continue
                if (isinstance(cancel_response_record, dict) and cancel_response_record.get("cancel_requested") is True
                        and cancel_response_record.get("job_id") == current_receipt_record["job_id"]):
                    workflow_run_store.acknowledge_cancel_delivery(current_step_record["request_id"])
            if observed_job_state in ("failed", "cancelled", "canceled"):
                terminal_state_name = "failed" if observed_job_state == "failed" else "cancelled"
                workflow_run_store.close_unsuccessful_step(workflow_run_identifier, current_step_record, terminal_state_name)
            elif observed_job_state == "completed":
                try:
                    if translation_step_selected:
                        workflow_run_store.record_translation_completion(workflow_run_identifier, current_step_identifier,
                            current_receipt_record["job_id"], current_status_record)
                    elif expected_service_name == "kimodo":
                        workflow_run_store.record_kimodo_completion(workflow_run_identifier, current_step_identifier, current_status_record)
                    elif audio_step_selected:
                        workflow_run_store.record_effect_audio_completion(workflow_run_identifier, current_step_identifier, current_status_record)
                    else:
                        workflow_run_store.record_flux_completion(workflow_run_identifier, current_step_identifier,
                                                                  current_status_record)
                except (ValueError, FileNotFoundError):
                    workflow_run_store.block_unusable_result(workflow_run_identifier, current_step_record,
                        "완료 결과가 없거나 형식 검증에 실패했습니다. 원 서비스의 결과를 확인하세요.")
                except OSError:
                    workflow_run_store.record_source_observation(current_step_record["request_id"], "unknown")
            continue
        claimed_step_record = workflow_run_store.claim_ready_step(workflow_run_identifier, current_step_identifier)
        if claimed_step_record is not None:
            if current_generator_commands is None:
                workflow_run_store.block_unusable_result(workflow_run_identifier, current_step_record,
                    "등록된 생성기의 실행 어댑터가 없습니다.")
                continue
            try:
                gateway_command_handler(current_generator_commands["submit"], claimed_step_record | service_request_fields)
            except (ValueError, OSError, RuntimeError):
                workflow_run_store.record_source_observation(claimed_step_record["request_id"], "unknown")
