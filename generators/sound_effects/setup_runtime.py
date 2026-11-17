"""효과음 전용 가상환경 설치. 모델 다운로드와 GPU 생성은 수행하지 않는다."""
from pathlib import Path
import shutil
import subprocess
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command
from tools.review.common.management_environment import resolve_management_environment

EFFECTS_ROCM_INDEX_URL = 'https://stable.repo.amd.com/rocm/whl-next/'
EFFECTS_ROCM_CONSTRAINTS_PATH = WORKFLOW_ROOT_DIRECTORY/'generators/wan_fun/rocm-constraints.txt'


def build_effects_rocm_validation():
    """최적화 모드에서도 ROCm·BF16 확인을 생략하지 않는다."""
    return ("import sys, torch; "
        "sys.exit('BF16 ROCm GPU가 필요합니다') if not (torch.version.hip and torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else None; "
        "print(torch.cuda.get_device_name(0))")


def install_effects_runtime():
    selected_management_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    selected_management_uv = selected_management_path / 'bin/uv'
    current_uv_executable = str(selected_management_uv) if selected_management_uv.is_file() else shutil.which('uv')
    if current_uv_executable is None:
        raise FileNotFoundError('uv가 필요합니다. 공식 설치 안내: https://docs.astral.sh/uv/getting-started/installation/')
    current_runtime_root = WORKFLOW_ROOT_DIRECTORY/'.venv-sfx-dasheng'
    current_python_path = current_runtime_root/'bin/python'
    if current_runtime_root.is_symlink():
        raise ValueError('효과음 환경이 심볼릭 링크입니다. 자동으로 변경하지 않습니다.')
    if current_python_path.is_file() and not (current_runtime_root / 'pyvenv.cfg').is_file():
        raise ValueError('효과음 가상환경 설정이 없어 자동으로 변경하지 않습니다.')
    current_install_commands = []
    if not current_python_path.is_file():
        if current_runtime_root.exists() and any(current_runtime_root.iterdir()):
            raise ValueError('기존 효과음 환경이 불완전하거나 비어 있지 않습니다. 자동으로 덮어쓰지 않습니다.')
        selected_management_python = selected_management_path / 'bin/python'
        current_install_commands.append([current_uv_executable, 'venv', '--python', str(selected_management_python) if selected_management_python.is_file() else sys.executable, str(current_runtime_root)])
    current_trace_logger = ManagementLaunchLogger('dasheng-audio-setup')
    try:
        for current_command_values in current_install_commands:
            current_result_code = run_logged_management_command(current_command_values, current_trace_logger)
            if current_result_code:
                raise RuntimeError(f'효과음 실행 환경 설치 실패: exit={current_result_code} log={current_trace_logger.output_log_path}')
        current_probe_command = [str(current_python_path), '-c', "import importlib.metadata as m; print(m.version('torch') if m.packages_distributions().get('torch') else '')"]
        current_installed_version = subprocess.check_output(current_probe_command, text=True).strip()
        if current_installed_version and current_installed_version != '2.13.0+rocm10.0.0':
            raise RuntimeError(f'기존 PyTorch 빌드를 교체하지 않습니다: {current_installed_version}. 별도 ROCm 환경을 준비하세요.')
        if not current_installed_version:
            current_install_commands = [[current_uv_executable, 'pip', 'install', '--python', str(current_python_path), '--index-url', EFFECTS_ROCM_INDEX_URL,
                'torch[device-gfx1151]==2.13.0+rocm10.0.0', 'torchaudio==2.11.0.2+rocm10.0.0']]
        else:
            current_install_commands = []
        current_install_commands.append([current_uv_executable, 'pip', 'install', '--python', str(current_python_path), '-c', str(EFFECTS_ROCM_CONSTRAINTS_PATH), '-r', str(Path(__file__).with_name('requirements.txt'))])
        current_install_commands.append([str(current_python_path), '-c', build_effects_rocm_validation()])
        for current_command_values in current_install_commands:
            current_result_code = run_logged_management_command(current_command_values, current_trace_logger)
            if current_result_code:
                raise RuntimeError(f'효과음 실행 환경 설치·검증 실패: exit={current_result_code} log={current_trace_logger.output_log_path}')
        current_trace_logger.emit_launch_trace('complete', f'실행 환경 설치 완료: {current_python_path}; 모델 준비는 관리페이지에서 실행하세요.')
    finally:
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    install_effects_runtime()
