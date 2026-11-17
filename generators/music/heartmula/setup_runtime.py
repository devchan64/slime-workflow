"""새 HeartMuLa 전용 ROCm 환경을 준비한다. 모델은 다운로드하지 않는다."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.music.heartmula.runtime import HEARTMULA_LIBRARY_REVISION
from generators.wan_fun.setup_rocm import FUN_PYTORCH_INDEX, FUN_ROCM_CONSTRAINTS_PATH, read_fun_rocm_constraints
from tools.review.common.management_environment import resolve_management_environment
from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command

HEARTMULA_RUNTIME_DIRECTORY = WORKFLOW_ROOT_DIRECTORY / '.venv-music-heartmula'
HEARTMULA_REQUIREMENTS_PATH = Path(__file__).with_name('requirements-rocm.txt')


def inspect_heartmula_dependency_exceptions(current_uv_executable, current_runtime_python, current_trace_logger):
    """HeartLib의 알려진 공식 메타데이터 불일치와 다른 충돌을 구분한다."""
    current_check_result = subprocess.run([current_uv_executable, 'pip', 'check', '--python', current_runtime_python],
        capture_output=True, text=True, timeout=60, check=False)
    current_check_output = current_check_result.stdout + current_check_result.stderr
    current_issue_lines = [current_line_text for current_line_text in current_check_output.splitlines() if current_line_text.startswith('The package `')]
    current_allowed_packages = {'numpy', 'torch', 'torchaudio', 'torchvision', 'tqdm', 'traitlets', 'traittypes', 'ipykernel', 'bitsandbytes', 'modelscope'}
    current_issue_patterns = [re.match(r'^The package `heartlib` requires `([A-Za-z0-9_.-]+)', current_issue_text) for current_issue_text in current_issue_lines]
    if current_check_result.returncode and (not current_issue_lines or any(not current_issue_match or current_issue_match.group(1).lower() not in current_allowed_packages for current_issue_match in current_issue_patterns)):
        raise ValueError('HeartLib 외 다른 의존성 불일치가 있습니다: ' + current_check_output[-4000:])
    for current_issue_text in current_issue_lines:
        current_trace_logger.emit_launch_trace('metadata-warning', current_issue_text)
    return len(current_issue_lines)


def prepare_heartmula_runtime_environment():
    """기존 음악 환경은 건드리지 않고 선택된 ROCm 실행 경로를 준비한다."""
    if HEARTMULA_RUNTIME_DIRECTORY.exists() or HEARTMULA_RUNTIME_DIRECTORY.is_symlink():
        raise ValueError('기존 HeartMuLa 환경을 자동 변경하지 않습니다. 상태를 확인하고 별도로 보존하세요.')
    current_management_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_management_python = current_management_path / 'bin/python'
    current_uv_path = current_management_path / 'bin/uv'
    current_uv_executable = str(current_uv_path) if current_uv_path.is_file() and os.access(current_uv_path, os.X_OK) else shutil.which('uv')
    if not current_management_python.is_file() or not current_uv_executable:
        raise ValueError('관리 Python과 uv가 필요합니다. 먼저 setup --scope management를 실행하세요.')
    current_runtime_python = str(HEARTMULA_RUNTIME_DIRECTORY / 'bin/python')
    current_package_versions = read_fun_rocm_constraints()
    current_trace_logger = ManagementLaunchLogger('heartmula-rocm-setup')
    try:
        current_setup_commands = [
            [current_uv_executable, 'venv', '--python', str(current_management_python), str(HEARTMULA_RUNTIME_DIRECTORY)],
            [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, '--index-url', FUN_PYTORCH_INDEX,
             'torch[device-gfx1151]==' + current_package_versions['torch'], 'torchvision[device-gfx1151]==' + current_package_versions['torchvision'],
             'torchaudio==' + current_package_versions['torchaudio']],
            [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, '-c', str(FUN_ROCM_CONSTRAINTS_PATH), '-r', str(HEARTMULA_REQUIREMENTS_PATH)],
            [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, '--no-deps',
             'heartlib @ git+https://github.com/HeartMuLa/heartlib.git@' + HEARTMULA_LIBRARY_REVISION],
        ]
        for current_command_values in current_setup_commands:
            run_logged_management_command(current_command_values, current_trace_logger)
        current_exception_count = inspect_heartmula_dependency_exceptions(current_uv_executable, current_runtime_python, current_trace_logger)
        current_validation_code = ("import json,sys,importlib.metadata as m,torch,heartlib,torchtune,demucs,lameenc; "
            "revision=json.loads(m.distribution('heartlib').read_text('direct_url.json'))['vcs_info']['commit_id']; "
            "sys.exit('HeartLib 소스 리비전 불일치') if revision != " + repr(HEARTMULA_LIBRARY_REVISION) + " else None; "
            "sys.exit('BF16 ROCm GPU가 필요합니다') if not (torch.version.hip and torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else None; "
            "print(torch.cuda.get_device_name(0))")
        run_logged_management_command([current_runtime_python, '-c', current_validation_code], current_trace_logger)
        current_trace_logger.emit_launch_trace('complete', f'HeartMuLa 실행 환경 준비 완료. HeartLib 메타데이터 불일치 {current_exception_count}건은 로그를 확인하세요. 모델은 별도로 준비합니다.')
    except BaseException as current_setup_error:
        current_trace_logger.emit_launch_trace('failure', f'{type(current_setup_error).__name__}: {current_setup_error}')
        raise
    finally:
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    prepare_heartmula_runtime_environment()
