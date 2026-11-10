"""명시적 setup 명령에서만 가상환경과 의존성을 준비한다."""
import os
import sys
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment
from tools.review.common.management_process import run_logged_management_command

MANAGEMENT_ENVIRONMENT_RECORDS = (
    ('VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/review/ui/gradio/requirements.txt'),
)


def prepare_management_environments(launcher_trace_logger):
    current_environment_records = list(MANAGEMENT_ENVIRONMENT_RECORDS)
    if 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH' in os.environ:
        current_shared_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
        current_gradio_path = resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv')
        if current_shared_path != current_gradio_path:
            current_environment_records.append(('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/review/ui/gradio/requirements.txt'))
    for environment_variable_name, default_directory_name, dependency_manifest_path in current_environment_records:
        environment_directory_path = resolve_management_environment(environment_variable_name, default_directory_name)
        selected_python_path = environment_directory_path/'bin/python'
        if selected_python_path.is_file() and not (environment_directory_path/'pyvenv.cfg').is_file():
            raise ValueError(f'가상환경 설정이 없습니다: {environment_directory_path}/pyvenv.cfg. 시스템 Python에는 설치하지 않습니다.')
        if not selected_python_path.is_file():
            run_logged_management_command([sys.executable, '-m', 'venv', str(environment_directory_path)], launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'ensurepip', '--upgrade'], launcher_trace_logger)
        # 공용 환경의 모델 패키지 제약과 GUI 의존성을 함께 확인한다.
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(WORKFLOW_ROOT_DIRECTORY/dependency_manifest_path)], launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'check'], launcher_trace_logger)
