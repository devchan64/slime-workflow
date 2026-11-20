"""준비된 단계를 기존 생성기 접수 명령으로 보내고 번역 완료를 관측한다."""
import os
from tools.review.common.management_environment import DEFAULT_GATEWAY_ADDRESS, validate_gateway_address
from tools.review.common.management_gateway import execute_management_command


def call_workflow_management_command(current_command_name, current_payload_record):
    management_gateway_address = validate_gateway_address(os.environ.get(
        "SLIME_MANAGEMENT_GATEWAY_URL", DEFAULT_GATEWAY_ADDRESS))
    return execute_management_command("hermes-agent", current_command_name, current_payload_record,
                                      management_gateway_address)


def advance_workflow_run(workflow_run_store, workflow_run_identifier, gateway_command_handler=call_workflow_management_command):
    for current_step_record in workflow_run_store.list_run_step_records(workflow_run_identifier):
        current_step_identifier = current_step_record["step_id"]
        if current_step_record["state"] == "submitting":
            translation_step_selected = current_step_record["category"] == "translation"
            expected_service_name = "prompt-translation" if translation_step_selected else "flux-image"
            status_command_name = "hermes-translation-status" if translation_step_selected else "hermes-flux-delegation-status"
            current_status_record = gateway_command_handler(status_command_name, {
                "request_id": current_step_record["request_id"]})
            current_receipt_record = current_status_record.get("receipt") or {}
            if (current_receipt_record.get("state") != "accepted"
                    or current_receipt_record.get("service") != expected_service_name
                    or current_receipt_record.get("request_id") != current_step_record["request_id"]
                    or not current_receipt_record.get("job_id")):
                continue
            observed_job_state = (current_status_record.get("job") or {}).get("status")
            if observed_job_state in ("failed", "cancelled", "canceled"):
                terminal_state_name = "failed" if observed_job_state == "failed" else "cancelled"
                workflow_run_store.close_unsuccessful_step(workflow_run_identifier, current_step_record, terminal_state_name)
            elif observed_job_state == "completed":
                if translation_step_selected:
                    workflow_run_store.record_translation_completion(workflow_run_identifier, current_step_identifier,
                        current_receipt_record["job_id"], current_status_record)
                else:
                    workflow_run_store.record_flux_completion(workflow_run_identifier, current_step_identifier,
                                                              current_status_record)
            continue
        claimed_step_record = workflow_run_store.claim_ready_step(workflow_run_identifier, current_step_identifier)
        if claimed_step_record is not None:
            current_command_name = {"translation": "hermes-delegate-translation",
                                    "image": "hermes-delegate-flux-image"}[current_step_record["category"]]
            gateway_command_handler(current_command_name, claimed_step_record)
