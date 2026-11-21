"""관리 환경 준비·GUI·게이트웨이 스크립트의 얇은 실행 진입점."""
import argparse
import os
import shlex
import shutil
from pathlib import Path
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.management.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment, resolve_management_ui_environment
from tools.management.common.management_process import ManagementLaunchLogger, run_logged_management_command
from tools.management.common.management_setup import prepare_management_environments

LAUNCHER_MODE_SCRIPT_PATHS = {
    'gui': 'tools/management/gui/serve.py',
    'gateway': 'tools/management/gateway/server.py',
    'snapshot': 'tools/management/maintenance/content_snapshot_worker.py',
}


def build_management_launch_command(launcher_mode_name, forwarded_argument_values):
    runtime_environment_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    selected_python_path = runtime_environment_path/'bin/python'
    if not selected_python_path.is_file():
        raise ValueError(f'관리 런타임이 없습니다: {selected_python_path}. scripts/setup_management.sh를 먼저 실행하세요.')
    selected_command_values = [str(selected_python_path), str(WORKFLOW_ROOT_DIRECTORY/LAUNCHER_MODE_SCRIPT_PATHS[launcher_mode_name])]
    if launcher_mode_name=='snapshot':
        return selected_command_values + list(forwarded_argument_values)
    selected_port_variable = 'REVIEW_SERVER_PORT' if launcher_mode_name == 'gui' else 'MANAGEMENT_GATEWAY_PORT'
    if os.environ.get(selected_port_variable):
        selected_command_values.extend(['--port', os.environ[selected_port_variable]])
    if launcher_mode_name == 'gui':
        explicit_source_selected = any(current_argument_text.split('=', 1)[0] in ('--root', '--walking', '--frontend-repo') for current_argument_text in forwarded_argument_values)
        if not explicit_source_selected and os.environ.get('FRONTEND_REPOSITORY_PATH'):
            selected_command_values.extend(['--frontend-repo', os.environ['FRONTEND_REPOSITORY_PATH']])
        if not any(current_argument_text in ('-h', '--help') for current_argument_text in forwarded_argument_values):
            management_environment_path = resolve_management_ui_environment()
            if not (management_environment_path/'bin/python').is_file():
                raise ValueError(f'관리 UI의 Python 환경이 없습니다: {management_environment_path}. scripts/setup_management.sh를 먼저 실행하세요.')
    return selected_command_values + list(forwarded_argument_values)


def print_hermes_codex_cli_guidance():
    """PATH에서 Codex를 찾지 못할 때 실행 가능한 경로와 등록 명령을 안내한다."""
    if shutil.which('codex'):
        return
    current_candidate_values=[os.environ.get('CODEX_CLI_PATH'),'/usr/lib/chatgpt/resources/codex','/opt/ChatGPT/resources/codex']
    current_executable_path=next((Path(current_candidate_value) for current_candidate_value in current_candidate_values if current_candidate_value and Path(current_candidate_value).is_absolute() and Path(current_candidate_value).is_file() and os.access(current_candidate_value,os.X_OK)),None)
    if current_executable_path is None:
        print('Codex CLI를 PATH 또는 알려진 앱 경로에서 찾지 못했습니다. Codex CLI 설치 또는 앱 설치 경로를 확인한 뒤 MCP 등록을 진행하세요.',flush=True)
        print('Codex MCP 안내: https://developers.openai.com/codex/mcp',flush=True)
        return
    current_executable_text=shlex.quote(str(current_executable_path))
    current_python_text=shlex.quote(str(WORKFLOW_ROOT_DIRECTORY/'.local/hermes-mcp/bin/python'))
    current_server_text=shlex.quote(str(WORKFLOW_ROOT_DIRECTORY/'tools/management/mcp/hermes_server.py'))
    print('Codex CLI가 PATH에 없어 앱의 실행 파일을 찾았습니다: '+str(current_executable_path),flush=True)
    print('먼저 등록 여부를 확인하세요:\n  '+current_executable_text+' mcp get slime-hermes',flush=True)
    print('등록되지 않은 경우에만 실행하세요:\n  '+current_executable_text+' mcp add slime-hermes -- '+current_python_text+' '+current_server_text,flush=True)
    print('이미 등록되어 있다면 다시 추가하지 않아도 됩니다. 새 도구는 MCP 연결을 다시 열고 확인하세요.',flush=True)


def run_management_launcher(command_argument_values=None):
    launcher_argument_parser = argparse.ArgumentParser(
        prog='./workflow.sh', description='SLIME 관리도구 통합 명령',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""scripts 디렉터리에서 실행하는 주요 명령

  ./workflow.sh start                      게이트웨이와 관리 화면 시작
  ./workflow.sh doctor                     설치 및 서비스 상태 조회
  ./workflow.sh setup --scope management   관리 Python 환경 준비
  ./workflow.sh gui --watch                관리 화면 실행 및 변경 감시
  ./workflow.sh gateway                    게이트웨이 단독 실행
  ./workflow.sh command kimodo history     Kimodo 생성 이력 조회

개별 명령의 옵션은 ./workflow.sh <명령> --help 로 확인하세요.""")
    launcher_argument_parser.add_argument('mode', choices=('setup', 'gui', 'gateway', 'snapshot', 'doctor', 'test', 'command', 'help', 'start', 'model'))
    launcher_argument_parser.add_argument('arguments', nargs=argparse.REMAINDER)
    launcher_argument_values = launcher_argument_parser.parse_args(command_argument_values)
    if launcher_argument_values.mode == 'start':
        start_argument_parser = argparse.ArgumentParser(prog='workflow start', description='비어 있는 포트에서 게이트웨이와 GUI를 독립 실행합니다.')
        start_argument_parser.parse_args(launcher_argument_values.arguments)
        from tools.management.common.management_stack import start_management_stack
        try:
            return start_management_stack()
        except (OSError, ValueError, RuntimeError) as stack_start_error:
            print(f'통합 시작 실패: {stack_start_error}', file=sys.stderr)
            return 1
    if launcher_argument_values.mode in ('command', 'help', 'model'):
        if (launcher_argument_values.mode == 'help' or
                any(current_argument_text in ('-h', '--help') for current_argument_text in launcher_argument_values.arguments)):
            current_manager_path = WORKFLOW_ROOT_DIRECTORY / 'tools/manager.py'
            current_runtime_python = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
            current_help_command = ([str(current_runtime_python), '-I', '-B'] if current_runtime_python.is_file() else [sys.executable, '-I', '-S', '-B'])
            return subprocess.run([*current_help_command, str(current_manager_path), launcher_argument_values.mode, *launcher_argument_values.arguments], check=False).returncode
        current_runtime_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
        if not current_runtime_path.is_file():
            launcher_argument_parser.error('관리 Python 환경이 없습니다. setup --scope management를 먼저 실행하세요.')
        current_manager_path = WORKFLOW_ROOT_DIRECTORY / 'tools/manager.py'
        return subprocess.run([str(current_runtime_path), str(current_manager_path), launcher_argument_values.mode, *launcher_argument_values.arguments], check=False).returncode
    if launcher_argument_values.mode == 'doctor':
        doctor_argument_parser = argparse.ArgumentParser(prog='workflow doctor', description='환경을 변경하지 않고 준비 상태를 확인합니다.')
        doctor_argument_parser.add_argument('--inventory', action='store_true', help='등록된 모델 파일 수·용량도 읽기 전용으로 확인합니다.')
        doctor_argument_parser.add_argument('--dependencies', action='store_true', help='생성기 패키지 의존성 메타데이터도 읽기 전용으로 확인합니다.')
        doctor_argument_values = doctor_argument_parser.parse_args(launcher_argument_values.arguments)
        from tools.management.common.management_diagnostics import inspect_management_environment
        return inspect_management_environment(doctor_argument_values.inventory, doctor_argument_values.dependencies)
    if launcher_argument_values.mode in ('gui', 'gateway') and any(current_argument_text in ('-h', '--help') for current_argument_text in launcher_argument_values.arguments):
        current_script_path = WORKFLOW_ROOT_DIRECTORY / LAUNCHER_MODE_SCRIPT_PATHS[launcher_argument_values.mode]
        return subprocess.run([sys.executable, '-I', '-S', '-B', str(current_script_path), *launcher_argument_values.arguments], check=False).returncode
    if launcher_argument_values.mode == 'test':
        if (launcher_argument_values.arguments in (['-h'], ['--help'], ['--list-all']) or
                len(launcher_argument_values.arguments) == 2 and launcher_argument_values.arguments[0] == '--list-group'):
            from tools.management.tests.run_management_audit import run_management_audit_cli
            return run_management_audit_cli(launcher_argument_values.arguments)
        current_runtime_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
        if not current_runtime_path.is_file():
            launcher_argument_parser.error('관리 Python 환경이 없습니다. setup --scope management를 먼저 실행하세요.')
        current_test_path = WORKFLOW_ROOT_DIRECTORY / 'tools/management/tests/run_management_audit.py'
        return subprocess.run([str(current_runtime_path), str(current_test_path), *launcher_argument_values.arguments], check=False).returncode
    selected_setup_scope = 'legacy'
    if launcher_argument_values.mode == 'setup':
        setup_argument_parser = argparse.ArgumentParser(prog='workflow setup', description='선택한 환경만 명시적으로 준비합니다.')
        setup_argument_parser.add_argument('--scope', choices=('legacy', 'management', 'image', 'renderer', 'hermes-runtime', 'hermes-mcp', 'wan-fun-runtime', 'sfx-runtime', 'kimodo-runtime', 'heartmula-runtime', 'writer-runtime'), default='legacy')
        setup_argument_parser.add_argument('--plan', action='store_true', help='변경 없이 준비 대상과 다운로드를 표시합니다.')
        current_setup_arguments = setup_argument_parser.parse_args(launcher_argument_values.arguments)
        selected_setup_scope = current_setup_arguments.scope
        from tools.management.common.management_setup_plan import print_management_setup_plan
        print_management_setup_plan(selected_setup_scope)
        if current_setup_arguments.plan:
            return 0
    launcher_trace_logger = ManagementLaunchLogger(launcher_argument_values.mode)
    try:
        launcher_trace_logger.emit_launch_trace('start', f'root={WORKFLOW_ROOT_DIRECTORY} log={launcher_trace_logger.output_log_path}')
        if launcher_argument_values.mode == 'setup':
            prepare_management_environments(launcher_trace_logger, selected_setup_scope)
            if selected_setup_scope == 'hermes-mcp':
                print_hermes_codex_cli_guidance()
        else:
            from tools.management.common.content_launch_config import apply_content_launch_configuration
            apply_content_launch_configuration()
            selected_command_values = build_management_launch_command(launcher_argument_values.mode, launcher_argument_values.arguments)
            if launcher_argument_values.mode == 'gateway' and not any(current_argument_text in ('-h', '--help') for current_argument_text in launcher_argument_values.arguments):
                from tools.management.gateway.server import parse_gateway_arguments
                from tools.management.common.gateway_existing_process import confirm_existing_gateway
                gateway_launch_options = parse_gateway_arguments(selected_command_values[2:])
                if not confirm_existing_gateway(gateway_launch_options.port, WORKFLOW_ROOT_DIRECTORY, launcher_trace_logger):
                    return 0
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
    # 실행·콘텐츠 설정은 선택한 관리 환경의 의존성을 사용한다.
    # 진단과 설치는 site 실행 없이 시작해 깨진 환경도 복구할 수 있다.
    if (len(sys.argv) > 1 and sys.argv[1] in ('gui', 'gateway', 'snapshot') and
            not (sys.argv[1] in ('gui', 'gateway') and any(current_argument_text in ('-h', '--help') for current_argument_text in sys.argv[2:]))):
        selected_runtime_directory = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
        selected_runtime_python = selected_runtime_directory / 'bin/python'
        if selected_runtime_python.is_file() and (sys.flags.no_site or Path(sys.prefix).resolve() != selected_runtime_directory.resolve()):
            os.execv(str(selected_runtime_python), [str(selected_runtime_python), '-I', '-B', str(Path(__file__).resolve()), *sys.argv[1:]])
    raise SystemExit(run_management_launcher())
