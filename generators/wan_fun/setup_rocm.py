"""AMD ROCm 전용 환경과 Fun Control 자산을 준비한다."""
from pathlib import Path
import fcntl
import os
import subprocess
import sys

from tools.review.common.management_process import ManagementLaunchLogger, run_logged_management_command

FUN_WORKSPACE_DIRECTORY = Path(__file__).resolve().parents[2]
FUN_ENVIRONMENT_DIRECTORY = FUN_WORKSPACE_DIRECTORY / '.local/venvs/wan-fun-rocm'
FUN_PYTHON_EXECUTABLE = FUN_ENVIRONMENT_DIRECTORY / 'bin/python'
FUN_PYTORCH_INDEX = 'https://stable.repo.amd.com/rocm/whl-next/'
FUN_MIGRAPHX_INDEX = 'https://stable.repo.amd.com/rocm/migraphx/whl-next/'
FUN_ONNX_INDEX = 'https://stable.repo.amd.com/rocm/onnxruntime/whl-next/'


def setup_fun_rocm_environment():
    # Xet의 희소 부분 파일은 길이만으로 이어받을 접두 구간을 판별할 수 없다.
    # 모델 준비 하위 프로세스는 공용 HTTP 복구 경로를 사용한다.
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    current_trace_logger = ManagementLaunchLogger('wan-fun-rocm-setup')
    current_lock_path = FUN_WORKSPACE_DIRECTORY / '.local/wan-fun-rocm-setup.lock'
    current_lock_path.parent.mkdir(parents=True, exist_ok=True)
    current_lock_stream = current_lock_path.open('a')
    try:
        try:
            fcntl.flock(current_lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:
            raise RuntimeError('모델 준비가 이미 진행 중입니다.') from current_lock_error
        if not FUN_PYTHON_EXECUTABLE.is_file():
            run_logged_management_command([sys.executable, '-m', 'venv', str(FUN_ENVIRONMENT_DIRECTORY)], current_trace_logger)
        current_python_path = str(FUN_PYTHON_EXECUTABLE)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '--index-url', FUN_PYTORCH_INDEX,
            'torch[device-gfx1151]==2.13.0+rocm10.0.0', 'torchvision[device-gfx1151]==0.28.0+rocm10.0.0',
            'torchaudio==2.11.0.2+rocm10.0.0'], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '--index-url', FUN_MIGRAPHX_INDEX,
            'migraphx==2.17.0+rocm10.0.0', 'migraphx-libs==2.17.0+rocm10.0.0'], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '--extra-index-url', FUN_ONNX_INDEX,
            'onnxruntime-ep-migraphx==1.0.0+rocm10.0.0', 'huggingface_hub', 'opencv-python-headless',
            'imageio', 'imageio-ffmpeg', 'onnx', 'onnxsim', 'safetensors', 'pyyaml', 'matplotlib'], current_trace_logger)
        current_site_directory = Path(subprocess.check_output([current_python_path, '-c',
            "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True).strip())
        current_onnx_directory = current_site_directory / 'onnxruntime/capi'
        current_library_link = current_onnx_directory / 'libonnxruntime.so.1'
        if not current_library_link.exists():
            current_library_link.symlink_to('libonnxruntime.so.1.29.0')
        current_library_paths = [str(current_onnx_directory), str(current_site_directory / 'migraphx_libs')]
        if os.environ.get('LD_LIBRARY_PATH'):
            current_library_paths.append(os.environ['LD_LIBRARY_PATH'])
        os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(current_library_paths)
        run_logged_management_command([current_python_path, '-c',
            "import torch, migraphx, onnxruntime as ort, onnxruntime_ep_migraphx as plugin\n"
            "assert torch.version.hip and torch.cuda.is_available(), 'ROCm GPU를 사용할 수 없습니다'\n"
            "assert torch.ones(1, device='cuda').item() == 1\n"
            "for name, path in zip(plugin.get_ep_names(), plugin.get_library_paths()): ort.register_execution_provider_library(name, path)\n"
            "assert any(device.ep_name == 'MIGraphXExecutionProvider' and device.device.type == ort.OrtHardwareDeviceType.GPU for device in ort.get_ep_devices()), 'MIGraphX GPU를 사용할 수 없습니다'\n"
            "print(torch.cuda.get_device_name(0), flush=True)"], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'generators.wan_fun.prepare_pose'], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'generators.wan_fun.prepare'], current_trace_logger)
        current_trace_logger.emit_launch_trace('complete', 'ROCm 모델 준비 완료')
    except BaseException as current_setup_error:
        current_trace_logger.emit_launch_trace('failure', f'{type(current_setup_error).__name__}: {current_setup_error}')
        raise
    finally:
        current_lock_stream.close()
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    setup_fun_rocm_environment()
