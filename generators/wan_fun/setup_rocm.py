"""AMD ROCm 전용 환경과 Fun Control 자산을 준비한다."""
from pathlib import Path
import fcntl
import os
import re
import subprocess
import sys

from workflow.common.management_process import ManagementLaunchLogger, run_logged_management_command

FUN_WORKSPACE_DIRECTORY = Path(__file__).resolve().parents[2]
FUN_ENVIRONMENT_DIRECTORY = FUN_WORKSPACE_DIRECTORY / '.local/venvs/wan-fun-rocm'
FUN_PYTHON_EXECUTABLE = FUN_ENVIRONMENT_DIRECTORY / 'bin/python'
FUN_PYTORCH_INDEX = 'https://stable.repo.amd.com/rocm/whl-next/'
FUN_MIGRAPHX_INDEX = 'https://stable.repo.amd.com/rocm/migraphx/whl-next/'
FUN_ONNX_INDEX = 'https://stable.repo.amd.com/rocm/onnxruntime/whl-next/'
FUN_ROCM_CONSTRAINTS_PATH = Path(__file__).with_name('rocm-constraints.txt')
FUN_MIGRAPHX_CONSTRAINTS_PATH = Path(__file__).with_name('migraphx-constraints.txt')
FUN_REQUIRED_ROCM_PACKAGES = frozenset(('torch', 'torchvision', 'torchaudio', 'migraphx', 'migraphx-libs', 'onnxruntime-ep-migraphx'))


def read_fun_rocm_constraints():
    """공유 ROCm 패키지의 고정 버전만 허용한다."""
    current_package_versions = {}
    for current_constraints_path in (FUN_ROCM_CONSTRAINTS_PATH, FUN_MIGRAPHX_CONSTRAINTS_PATH):
        for current_constraint_line in current_constraints_path.read_text(encoding='utf-8').splitlines():
            current_constraint_line = current_constraint_line.strip()
            if not current_constraint_line or current_constraint_line.startswith('#'):
                continue
            current_constraint_match = re.fullmatch(r'([a-z0-9-]+)==([A-Za-z0-9.+_-]+)', current_constraint_line)
            if not current_constraint_match:
                raise ValueError('ROCm 제약 파일 형식 오류')
            current_package_name, current_package_version = current_constraint_match.groups()
            if current_package_name not in FUN_REQUIRED_ROCM_PACKAGES or current_package_name in current_package_versions:
                raise ValueError('ROCm 제약 파일의 알 수 없거나 중복된 패키지')
            current_package_versions[current_package_name] = current_package_version
    if current_package_versions.keys() != FUN_REQUIRED_ROCM_PACKAGES:
        raise ValueError('ROCm 제약 파일의 필수 패키지 누락')
    return current_package_versions


def build_fun_package_preflight():
    """기존 호환되지 않는 GPU 패키지를 자동 교체하지 않는다."""
    return ("import importlib.metadata as package_metadata; expected_package_versions=" + repr(read_fun_rocm_constraints()) + "\n"
        "for current_package_name, expected_package_version in expected_package_versions.items():\n"
        " try: current_package_version=package_metadata.version(current_package_name)\n"
        " except package_metadata.PackageNotFoundError: continue\n"
        " if current_package_version != expected_package_version: raise SystemExit('기존 ROCm 패키지를 교체하지 않습니다: '+current_package_name+' '+current_package_version+' != '+expected_package_version)\n")


def build_fun_gpu_validation():
    """최적화 모드에서도 ROCm과 MIGraphX GPU 공급자를 확인한다."""
    return ("import sys, torch, migraphx, onnxruntime as ort, onnxruntime_ep_migraphx as plugin\n"
        "if not (torch.version.hip and torch.cuda.is_available()): raise SystemExit('ROCm GPU를 사용할 수 없습니다')\n"
        "if torch.ones(1, device='cuda').item() != 1: raise SystemExit('ROCm GPU 연산 검증 실패')\n"
        "for current_provider_name, current_provider_path in zip(plugin.get_ep_names(), plugin.get_library_paths()): ort.register_execution_provider_library(current_provider_name, current_provider_path)\n"
        "if not any(current_device_value.ep_name == 'MIGraphXExecutionProvider' and current_device_value.device.type == ort.OrtHardwareDeviceType.GPU for current_device_value in ort.get_ep_devices()): raise SystemExit('MIGraphX GPU를 사용할 수 없습니다')\n"
        "print(torch.cuda.get_device_name(0), flush=True)")


def setup_fun_rocm_environment(prepare_model_assets=True):
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
        if FUN_ENVIRONMENT_DIRECTORY.is_symlink():
            raise ValueError('ROCm 환경이 심볼릭 링크입니다. 자동으로 변경하지 않습니다.')
        if FUN_PYTHON_EXECUTABLE.is_file() and not (FUN_ENVIRONMENT_DIRECTORY / 'pyvenv.cfg').is_file():
            raise ValueError('ROCm 가상환경 설정이 없어 자동으로 변경하지 않습니다.')
        if not FUN_PYTHON_EXECUTABLE.is_file():
            if FUN_ENVIRONMENT_DIRECTORY.exists() and any(FUN_ENVIRONMENT_DIRECTORY.iterdir()):
                raise ValueError('기존 ROCm 환경이 불완전하거나 비어 있지 않습니다. 자동으로 덮어쓰지 않습니다.')
            run_logged_management_command([sys.executable, '-m', 'venv', str(FUN_ENVIRONMENT_DIRECTORY)], current_trace_logger)
        current_python_path = str(FUN_PYTHON_EXECUTABLE)
        current_package_versions = read_fun_rocm_constraints()
        run_logged_management_command([current_python_path, '-c', build_fun_package_preflight()], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '-c', str(FUN_ROCM_CONSTRAINTS_PATH), '-c', str(FUN_MIGRAPHX_CONSTRAINTS_PATH), '--index-url', FUN_PYTORCH_INDEX,
            'torch[device-gfx1151]==' + current_package_versions['torch'], 'torchvision[device-gfx1151]==' + current_package_versions['torchvision'],
            'torchaudio==' + current_package_versions['torchaudio']], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '-c', str(FUN_ROCM_CONSTRAINTS_PATH), '-c', str(FUN_MIGRAPHX_CONSTRAINTS_PATH), '--index-url', FUN_MIGRAPHX_INDEX,
            'migraphx==' + current_package_versions['migraphx'], 'migraphx-libs==' + current_package_versions['migraphx-libs']], current_trace_logger)
        run_logged_management_command([current_python_path, '-m', 'pip', 'install', '-c', str(FUN_ROCM_CONSTRAINTS_PATH), '-c', str(FUN_MIGRAPHX_CONSTRAINTS_PATH), '--extra-index-url', FUN_ONNX_INDEX,
            'onnxruntime-ep-migraphx==' + current_package_versions['onnxruntime-ep-migraphx'], 'huggingface_hub', 'opencv-python-headless',
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
        run_logged_management_command([current_python_path, '-c', build_fun_gpu_validation()], current_trace_logger)
        if prepare_model_assets:
            run_logged_management_command([current_python_path, '-m', 'generators.wan_fun.prepare_pose'], current_trace_logger)
            run_logged_management_command([current_python_path, '-m', 'generators.wan_fun.prepare'], current_trace_logger)
        current_trace_logger.emit_launch_trace('complete', 'ROCm 모델 준비 완료' if prepare_model_assets else 'ROCm 실행 환경 준비 완료')
    except BaseException as current_setup_error:
        current_trace_logger.emit_launch_trace('failure', f'{type(current_setup_error).__name__}: {current_setup_error}')
        raise
    finally:
        current_lock_stream.close()
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    setup_fun_rocm_environment()
