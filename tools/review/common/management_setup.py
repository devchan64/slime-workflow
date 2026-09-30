"""명시적 setup 명령에서만 가상환경과 의존성을 준비한다."""
import sys
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment
from tools.review.common.management_process import run_logged_management_command

MANAGEMENT_ENVIRONMENT_RECORDS = (
    ('VIRTUAL_ENVIRONMENT_PATH', '.venv', 'requirements.txt'),
    ('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv-management', 'tools/review/ui/gradio/requirements.txt'),
)


def prepare_management_environments(launcher_trace_logger):
    for environment_variable_name, default_directory_name, dependency_manifest_path in MANAGEMENT_ENVIRONMENT_RECORDS:
        environment_directory_path = resolve_management_environment(environment_variable_name, default_directory_name)
        selected_python_path = environment_directory_path/'bin/python'
        if selected_python_path.is_file() and not (environment_directory_path/'pyvenv.cfg').is_file():
            raise ValueError(f'가상환경 설정이 없습니다: {environment_directory_path}/pyvenv.cfg. 시스템 Python에는 설치하지 않습니다.')
        if not selected_python_path.is_file():
            run_logged_management_command([sys.executable, '-m', 'venv', str(environment_directory_path)], launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'ensurepip', '--upgrade'], launcher_trace_logger)
        # Gradio 의존성이 GPU 모델 라이브러리의 버전 제약을 변경하지 않도록 분리한다.
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(WORKFLOW_ROOT_DIRECTORY/dependency_manifest_path)], launcher_trace_logger)
