"""관리 환경 준비·GUI·게이트웨이 스크립트의 얇은 실행 진입점."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment
from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command
from tools.review.common.management_setup import prepare_management_environments

LAUNCHER_MODE_SCRIPT_PATHS = {
    'gui': 'tools/review/serve.py',
    'gateway': 'tools/review/gateway_server.py',
}


def build_management_launch_command(launcher_mode_name, forwarded_argument_values):
    runtime_environment_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    selected_python_path = runtime_environment_path/'bin/python'
    if not selected_python_path.is_file():
        raise ValueError(f'관리 런타임이 없습니다: {selected_python_path}. scripts/setup_management.sh를 먼저 실행하세요.')
    selected_command_values = [str(selected_python_path), str(WORKFLOW_ROOT_DIRECTORY/LAUNCHER_MODE_SCRIPT_PATHS[launcher_mode_name])]
    selected_port_variable = 'REVIEW_SERVER_PORT' if launcher_mode_name == 'gui' else 'MANAGEMENT_GATEWAY_PORT'
    if os.environ.get(selected_port_variable):
        selected_command_values.extend(['--port', os.environ[selected_port_variable]])
    if launcher_mode_name == 'gui':
        explicit_source_selected = any(current_argument_text.split('=', 1)[0] in ('--root', '--walking', '--frontend-repo') for current_argument_text in forwarded_argument_values)
        if not explicit_source_selected and os.environ.get('FRONTEND_REPOSITORY_PATH'):
            selected_command_values.extend(['--frontend-repo', os.environ['FRONTEND_REPOSITORY_PATH']])
        if not any(current_argument_text in ('-h', '--help') for current_argument_text in forwarded_argument_values):
            management_environment_path = resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv-management')
            if not (management_environment_path/'bin/python').is_file():
                raise ValueError(f'Gradio 환경이 없습니다: {management_environment_path}. scripts/setup_management.sh를 먼저 실행하세요.')
    return selected_command_values + list(forwarded_argument_values)


def run_management_launcher(command_argument_values=None):
    launcher_argument_parser = argparse.ArgumentParser(description=__doc__)
    launcher_argument_parser.add_argument('mode', choices=('setup', 'gui', 'gateway'))
    launcher_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    launcher_argument_values = launcher_argument_parser.parse_args(command_argument_values)
    if launcher_argument_values.mode == 'setup' and launcher_argument_values.arguments:
        if launcher_argument_values.arguments in (['--help'], ['-h']):
            print('환경 준비: scripts/setup_management.sh · 실행 시 의존성을 설치하지 않습니다.')
            return 0
        launcher_argument_parser.error('setup은 추가 인자를 받지 않습니다.')
    launcher_trace_logger = ManagementLaunchLogger(launcher_argument_values.mode)
    try:
        launcher_trace_logger.emit_launch_trace('start', f'root={WORKFLOW_ROOT_DIRECTORY} log={launcher_trace_logger.output_log_path}')
        if launcher_argument_values.mode == 'setup':
            prepare_management_environments(launcher_trace_logger)
        else:
            selected_command_values = build_management_launch_command(launcher_argument_values.mode, launcher_argument_values.arguments)
            run_logged_management_command(selected_command_values, launcher_trace_logger)
        return 0
    except Exception as launcher_error_value:
        launcher_trace_logger.emit_launch_trace('failure', traceback.format_exc())
        print('최근 실행 로그:\n' + '\n'.join(launcher_trace_logger.recent_output_lines), file=sys.stderr, flush=True)
        if isinstance(launcher_error_value, subprocess.CalledProcessError):
            return launcher_error_value.returncode if launcher_error_value.returncode > 0 else 128 - launcher_error_value.returncode
        return 1
    finally:
        launcher_trace_logger.close_launch_log()


if __name__ == '__main__':
    raise SystemExit(run_management_launcher())
