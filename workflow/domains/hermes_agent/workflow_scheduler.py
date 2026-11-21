"""저장된 실행을 서비스 수명 동안 주기적으로 조정한다."""
import logging
import sqlite3

from .workflow_dispatch import advance_workflow_run, call_workflow_management_command


def run_workflow_scheduler(workflow_run_store, scheduler_stop_event, polling_interval_seconds=5,
                           gateway_command_handler=call_workflow_management_command):
    if polling_interval_seconds <= 0:
        raise ValueError("조회 간격은 양수여야 합니다.")
    scheduler_event_logger = logging.getLogger(__name__)
    while not scheduler_stop_event.is_set():
        try:
            active_run_identifiers = workflow_run_store.list_active_run_identifiers()
        except sqlite3.OperationalError as database_read_error:
            if getattr(database_read_error, "sqlite_errorcode", 0) & 255 not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise
            scheduler_event_logger.warning("워크플로우 DB 잠금으로 다음 조회 주기에 다시 확인합니다.")
            scheduler_stop_event.wait(polling_interval_seconds)
            continue
        for workflow_run_identifier in active_run_identifiers:
            if scheduler_stop_event.is_set():
                return
            try:
                advance_workflow_run(workflow_run_store, workflow_run_identifier, gateway_command_handler)
            except sqlite3.OperationalError as database_write_error:
                if getattr(database_write_error, "sqlite_errorcode", 0) & 255 not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                    raise
                scheduler_event_logger.warning("워크플로우 DB 잠금으로 단계 처리를 연기합니다 (%s)", workflow_run_identifier)
            except (ValueError, OSError, RuntimeError) as current_dispatch_error:
                scheduler_event_logger.warning("워크플로우 상태 확인 필요 (%s, %s)",
                                               workflow_run_identifier, type(current_dispatch_error).__name__)
        scheduler_stop_event.wait(polling_interval_seconds)


def start_gateway_workflow_scheduler(workflow_root_directory, server_port_number, scheduler_stop_event):
    from threading import Thread
    from workflow.common.management_environment import GATEWAY_SERVER_HOST
    from workflow.common.management_gateway import execute_management_command
    from .workflow_run_store import WorkflowRunStore

    workflow_storage_directory = workflow_root_directory / ".local" / "hermes-workflows"
    workflow_storage_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    workflow_run_store = WorkflowRunStore(workflow_storage_directory / "runs.sqlite3")
    local_gateway_address = f"http://{GATEWAY_SERVER_HOST}:{server_port_number}"

    def dispatch_gateway_command(current_command_name, current_payload_record):
        return execute_management_command("hermes-agent", current_command_name, current_payload_record,
                                          local_gateway_address)

    workflow_scheduler_thread = Thread(target=run_workflow_scheduler, name="hermes-workflow-scheduler",
        args=(workflow_run_store, scheduler_stop_event), kwargs={"gateway_command_handler": dispatch_gateway_command},
        daemon=True)
    workflow_scheduler_thread.start()
    return workflow_scheduler_thread
