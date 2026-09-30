"""명시적 setup 명령에서만 가상환경과 의존성을 준비한다."""
import sys
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment
from tools.review.common.management_process import run_logged_management_command

MANAGEMENT_ENVIRONMENT_RECORDS = (
    ('VIRTUAL_ENVIRONMENT_PATH', '.venv'),
    ('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv-management'),
)


def prepare_management_environments(launcher_trace_logger):
    for environment_variable_name, default_directory_name in MANAGEMENT_ENVIRONMENT_RECORDS:
        environment_directory_path = resolve_management_environment(environment_variable_name, default_directory_name)
        selected_python_path = environment_directory_path/'bin/python'
        if selected_python_path.is_file() and not (environment_directory_path/'pyvenv.cfg').is_file():
            raise ValueError(f'가상환경 설정이 없습니다: {environment_directory_path}/pyvenv.cfg. 시스템 Python에는 설치하지 않습니다.')
        if not selected_python_path.is_file():
            run_logged_management_command([sys.executable, '-m', 'venv', str(environment_directory_path)], launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'ensurepip', '--upgrade'], launcher_trace_logger)
        # 기존 두 환경의 공통 검수 의존성 계약을 유지한다. 실행 스크립트는 설치하지 않는다.
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(WORKFLOW_ROOT_DIRECTORY/'requirements.txt')], launcher_trace_logger)
