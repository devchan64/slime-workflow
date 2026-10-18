"""효과음 전용 가상환경 설치. 모델 다운로드와 GPU 생성은 수행하지 않는다."""
from pathlib import Path
import shutil
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command


def install_effects_runtime():
    current_uv_executable = shutil.which('uv')
    if current_uv_executable is None:
        raise FileNotFoundError('uv가 필요합니다. 공식 설치 안내: https://docs.astral.sh/uv/getting-started/installation/')
    current_runtime_root = WORKFLOW_ROOT_DIRECTORY/'.venv-sfx-dasheng'
    current_python_path = current_runtime_root/'bin/python'
    current_install_commands = []
    if not current_python_path.is_file():
        current_install_commands.append([current_uv_executable, 'venv', '--python', '3.12', str(current_runtime_root)])
    current_install_commands.extend([
        [current_uv_executable, 'pip', 'install', '--python', str(current_python_path), '--index-url', 'https://download.pytorch.org/whl/cu128', 'torch==2.8.0', 'torchaudio==2.8.0'],
        [current_uv_executable, 'pip', 'install', '--python', str(current_python_path), '-r', str(Path(__file__).with_name('requirements.txt'))],
    ])
    current_trace_logger = ManagementLaunchLogger('dasheng-audio-setup')
    try:
        for current_command_values in current_install_commands:
            current_result_code = run_logged_management_command(current_command_values, current_trace_logger)
            if current_result_code:
                raise RuntimeError(f'효과음 실행 환경 설치 실패: exit={current_result_code} log={current_trace_logger.output_log_path}')
        current_trace_logger.emit_launch_trace('complete', f'실행 환경 설치 완료: {current_python_path}; 모델 준비는 관리페이지에서 실행하세요.')
    finally:
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    install_effects_runtime()
