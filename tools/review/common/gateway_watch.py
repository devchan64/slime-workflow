"""게이트웨이 소스 변경 감시. GUI·실행 기록은 제외하고 기존 프로세스 실행기를 사용한다."""
import os
from pathlib import Path
import sys
import time
import traceback

from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY
from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command

GATEWAY_WATCH_SETTLE_SECONDS = .5
GATEWAY_WATCH_SOURCE_SUFFIXES = frozenset(('.py', '.yaml', '.yml', '.json'))
GATEWAY_WATCH_IGNORED_DIRECTORIES = frozenset(('__pycache__', 'node_modules', 'ui', 'tests'))
GATEWAY_WATCH_IGNORED_MODULES = frozenset((
    'gateway_watch.py', 'management_launcher.py', 'management_process.py', 'management_setup.py', 'management_client.py',
))


def collect_gateway_watch_paths(writer_workspace_config=None):
    return (
        WORKFLOW_ROOT_DIRECTORY/'tools/review/gateway_server.py',
        WORKFLOW_ROOT_DIRECTORY/'tools/review/common',
        WORKFLOW_ROOT_DIRECTORY/'tools/review/domains',
        WORKFLOW_ROOT_DIRECTORY/'generators/writer_agent',
        Path(writer_workspace_config) if writer_workspace_config is not None else WORKFLOW_ROOT_DIRECTORY/'.local/writer-agent/workspace.yaml',
    )


def snapshot_gateway_watch_paths(watched_source_paths):
    source_snapshot_records = []
    for watched_source_path in watched_source_paths:
        if watched_source_path.is_dir():
            selected_source_files = []
            for current_directory_path, child_directory_names, child_file_names in os.walk(watched_source_path):
                child_directory_names[:] = [directory_name_value for directory_name_value in child_directory_names if not directory_name_value.startswith('.') and directory_name_value not in GATEWAY_WATCH_IGNORED_DIRECTORIES]
                selected_source_files.extend(Path(current_directory_path)/file_name_value for file_name_value in child_file_names)
        else:
            selected_source_files = [watched_source_path]
        for selected_source_path in selected_source_files:
            if selected_source_path.suffix not in GATEWAY_WATCH_SOURCE_SUFFIXES or selected_source_path.name.startswith(('.', 'gradio_')) or selected_source_path.name in GATEWAY_WATCH_IGNORED_MODULES:
                continue
            try:
                selected_source_stat = selected_source_path.stat()
            except FileNotFoundError:
                # 편집기의 원자적 교체·새 파일 생성은 다음 스냅샷과 비교한다.
                continue
            if selected_source_path.is_file():
                source_snapshot_records.append((str(selected_source_path), selected_source_stat.st_mtime_ns, selected_source_stat.st_size))
    return tuple(sorted(source_snapshot_records))


def run_gateway_watch_mode(server_port_number, writer_workspace_config=None):
    gateway_command_values = [sys.executable, str(WORKFLOW_ROOT_DIRECTORY/'tools/review/gateway_server.py'), '--port', str(server_port_number)]
    if writer_workspace_config is not None:
        gateway_command_values.extend(['--writer-agent-config', str(Path(writer_workspace_config).absolute())])
    watched_source_paths = collect_gateway_watch_paths(writer_workspace_config)
    launcher_trace_logger = ManagementLaunchLogger('gateway-watch')
    try:
        launcher_trace_logger.emit_launch_trace('start', f'port={server_port_number} paths={[str(source_path_value) for source_path_value in watched_source_paths]} log={launcher_trace_logger.output_log_path}')
        while True:
            previous_source_snapshot = snapshot_gateway_watch_paths(watched_source_paths)
            pending_change_time = None

            def check_gateway_changes():
                nonlocal previous_source_snapshot, pending_change_time
                current_source_snapshot = snapshot_gateway_watch_paths(watched_source_paths)
                if current_source_snapshot != previous_source_snapshot:
                    previous_source_snapshot = current_source_snapshot
                    pending_change_time = time.monotonic()
                return pending_change_time is not None and time.monotonic() - pending_change_time >= GATEWAY_WATCH_SETTLE_SECONDS

            if not run_logged_management_command(gateway_command_values, launcher_trace_logger, check_gateway_changes):
                return
    except Exception:
        launcher_trace_logger.emit_launch_trace('failure', traceback.format_exc())
        print('최근 실행 로그:\n' + '\n'.join(launcher_trace_logger.recent_output_lines), file=sys.stderr, flush=True)
        raise
    finally:
        launcher_trace_logger.close_launch_log()
