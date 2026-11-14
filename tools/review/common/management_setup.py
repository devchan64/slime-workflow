"""명시적 setup 명령에서만 가상환경과 의존성을 준비한다."""
import os
import sys
import json
from pathlib import Path
from tools.review.common.management_environment import WORKFLOW_ROOT_DIRECTORY, resolve_management_environment
from tools.review.common.management_process import run_logged_management_command

IMAGE_ROCM_INDEX_URL = 'https://stable.repo.amd.com/rocm/whl-next/'
IMAGE_ENVIRONMENT_PATH = WORKFLOW_ROOT_DIRECTORY / '.venv'
IMAGE_CONSTRAINTS_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/constraints-rocm.txt'
IMAGE_REQUIREMENTS_PATH = WORKFLOW_ROOT_DIRECTORY / 'generators/image/requirements-runtime.txt'

MANAGEMENT_ENVIRONMENT_RECORDS = (
    ('VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/review/ui/gradio/requirements.txt'),
)


def prepare_virtual_environment(environment_directory_path, launcher_trace_logger):
    selected_python_path = environment_directory_path / 'bin/python'
    if selected_python_path.is_file() and not (environment_directory_path / 'pyvenv.cfg').is_file():
        raise ValueError(f'가상환경 설정이 없습니다: {environment_directory_path}/pyvenv.cfg. 시스템 Python에는 설치하지 않습니다.')
    if not selected_python_path.is_file():
        run_logged_management_command([sys.executable, '-m', 'venv', str(environment_directory_path)], launcher_trace_logger)
    run_logged_management_command([str(selected_python_path), '-m', 'ensurepip', '--upgrade'], launcher_trace_logger)
    return selected_python_path


def prepare_image_runtime_environment(image_python_path, launcher_trace_logger):
    """기존 PyTorch 빌드를 확인하고 고정된 gfx1151 ROCm 실행 환경을 준비한다."""
    current_preflight_code = (
        "import importlib.metadata as m, importlib.util; "
        "versions={n:m.version(n) for n in ('torch','torchvision') if importlib.util.find_spec(n)}; "
        "expected={'torch':'2.13.0+rocm10.0.0','torchvision':'0.28.0+rocm10.0.0'}; "
        "assert all(expected[n] == v for n,v in versions.items()), "
        "'기존 PyTorch 빌드를 교체하지 않습니다. 별도 환경에서 ROCm 설정을 확인하세요: '+str(versions)"
    )
    run_logged_management_command([str(image_python_path), '-c', current_preflight_code], launcher_trace_logger)
    current_platform_code = (
        "import sys, platform, subprocess; "
        "assert sys.platform == 'linux' and platform.machine() == 'x86_64' and sys.version_info[:2] == (3,14), "
        "'Qwen ROCm 자동 설치는 Linux x86_64 Python 3.14를 지원합니다'; "
        "r=subprocess.run(['rocminfo'],capture_output=True,text=True,check=True,timeout=30); "
        "assert 'gfx1151' in r.stdout, 'gfx1151 GPU를 확인할 수 없습니다. 호환되는 ROCm 환경을 별도로 구성하세요'"
    )
    run_logged_management_command([str(image_python_path), '-c', current_platform_code], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'install', '--disable-pip-version-check',
        '--index-url', IMAGE_ROCM_INDEX_URL, 'torch[device-gfx1151]==2.13.0+rocm10.0.0',
        'torchvision[device-gfx1151]==0.28.0+rocm10.0.0'], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'install', '--disable-pip-version-check',
        '-c', str(IMAGE_CONSTRAINTS_PATH), '-r', str(IMAGE_REQUIREMENTS_PATH)], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-c',
        "import torch, accelerate, transformers, safetensors; from diffusers import QwenImage21Pipeline; "
        "assert torch.version.hip, 'ROCm PyTorch가 아닙니다'; print('Qwen 이미지 실행 의존성 확인 완료')"], launcher_trace_logger)
    run_logged_management_command([str(image_python_path), '-m', 'pip', 'check'], launcher_trace_logger)


def prepare_management_environments(launcher_trace_logger):
    current_environment_records = list(MANAGEMENT_ENVIRONMENT_RECORDS)
    if 'MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH' in os.environ:
        current_shared_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
        current_gradio_path = resolve_management_environment('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv')
        if current_shared_path != current_gradio_path:
            current_environment_records.append(('MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH', '.venv', 'tools/review/ui/gradio/requirements.txt'))
    current_prepared_paths = set()
    # 이미지 작업자는 고정된 .venv를 사용한다. GUI 경로 설정과 구분한다.
    current_image_python = prepare_virtual_environment(IMAGE_ENVIRONMENT_PATH, launcher_trace_logger)
    current_prepared_paths.add(IMAGE_ENVIRONMENT_PATH)
    prepare_image_runtime_environment(current_image_python, launcher_trace_logger)
    for environment_variable_name, default_directory_name, dependency_manifest_path in current_environment_records:
        environment_directory_path = resolve_management_environment(environment_variable_name, default_directory_name)
        selected_python_path = (environment_directory_path / 'bin/python' if environment_directory_path in current_prepared_paths
                                else prepare_virtual_environment(environment_directory_path, launcher_trace_logger))
        current_prepared_paths.add(environment_directory_path)
        current_install_command = [str(selected_python_path), '-m', 'pip', 'install', '--disable-pip-version-check']
        if environment_directory_path == IMAGE_ENVIRONMENT_PATH:
            current_install_command += ['-c', str(IMAGE_CONSTRAINTS_PATH)]
        current_install_command += ['-r', str(WORKFLOW_ROOT_DIRECTORY / dependency_manifest_path)]
        run_logged_management_command(current_install_command, launcher_trace_logger)
        run_logged_management_command([str(selected_python_path), '-m', 'pip', 'check'], launcher_trace_logger)
    frontend_repository_path = Path(os.environ.get('FRONTEND_REPOSITORY_PATH', WORKFLOW_ROOT_DIRECTORY.parent / 'slime-frontend')).resolve()
    renderer_package_path = frontend_repository_path / 'packages/field-renderer/package.json'
    renderer_package_version = json.loads(renderer_package_path.read_text(encoding='utf-8'))['version']
    run_logged_management_command(['npm', '--prefix', str(frontend_repository_path), 'run', 'build:field-renderer'], launcher_trace_logger)
    renderer_bundle_directory = frontend_repository_path / '.tmp/field-renderer' / renderer_package_version
    shared_python_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv') / 'bin/python'
    run_logged_management_command([str(shared_python_path), str(WORKFLOW_ROOT_DIRECTORY / 'tools/review/install_field_renderer.py'), '--source', str(renderer_bundle_directory)], launcher_trace_logger)
