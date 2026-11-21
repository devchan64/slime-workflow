"""새 Kimodo 전용 ROCm 환경을 준비한다. 모델은 다운로드하지 않는다."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.kimodo.contracts import KIMODO_ENVIRONMENT_PYTHON, KIMODO_SOURCE_ROOT
from generators.kimodo.prepare import prepare_kimodo_source_repository
from generators.wan_fun.setup_rocm import (FUN_MIGRAPHX_CONSTRAINTS_PATH, FUN_MIGRAPHX_INDEX,
    FUN_ONNX_INDEX, FUN_PYTORCH_INDEX, FUN_ROCM_CONSTRAINTS_PATH,
    build_fun_gpu_validation, read_fun_rocm_constraints)
from tools.management.common.management_environment import resolve_management_environment
from tools.management.common.management_process import ManagementLaunchLogger, run_logged_management_command


def prepare_kimodo_runtime_environment():
    """기존 전용 환경을 덮어쓰지 않고 검증된 공식 소스 사본으로 준비한다."""
    current_environment_path = KIMODO_ENVIRONMENT_PYTHON.parent.parent
    if current_environment_path.exists() or current_environment_path.is_symlink():
        raise ValueError('기존 Kimodo 환경을 자동 변경하지 않습니다. 상태를 확인하고 별도로 보존하세요.')
    current_management_path = resolve_management_environment('VIRTUAL_ENVIRONMENT_PATH', '.venv')
    current_uv_path = current_management_path / 'bin/uv'
    current_uv_executable = str(current_uv_path) if current_uv_path.is_file() and os.access(current_uv_path, os.X_OK) else shutil.which('uv')
    if not current_uv_executable:
        raise ValueError('uv가 필요합니다. 먼저 setup --scope management를 실행하세요.')
    current_python_path = current_management_path / 'bin/python'
    if not current_python_path.is_file():
        raise ValueError('관리 Python이 없습니다. 먼저 setup --scope management를 실행하세요.')
    current_source_revision = prepare_kimodo_source_repository()
    current_package_versions = read_fun_rocm_constraints()
    current_constraints_values = ['-c', str(FUN_ROCM_CONSTRAINTS_PATH), '-c', str(FUN_MIGRAPHX_CONSTRAINTS_PATH)]
    current_runtime_python = str(KIMODO_ENVIRONMENT_PYTHON)
    current_trace_logger = ManagementLaunchLogger('kimodo-rocm-setup')
    try:
        current_temp_directory = WORKFLOW_ROOT_DIRECTORY / '.tmp'
        current_temp_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='kimodo-source-build-', dir=current_temp_directory) as current_build_directory:
            current_build_path = Path(current_build_directory)
            current_source_copy = current_build_path / 'source'
            current_source_copy.mkdir()
            current_archive_path = current_build_path / 'source.tar'
            with current_archive_path.open('wb') as current_archive_stream:
                subprocess.run(['git', '-C', str(KIMODO_SOURCE_ROOT), 'archive', '--format=tar', current_source_revision], stdout=current_archive_stream, check=True)
            with tarfile.open(current_archive_path) as current_archive_file:
                current_archive_file.extractall(current_source_copy, filter='data')
            current_setup_commands = [
                [current_uv_executable, 'venv', '--python', str(current_python_path), str(current_environment_path)],
                [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, '--index-url', FUN_PYTORCH_INDEX,
                 'torch[device-gfx1151]==' + current_package_versions['torch'], 'torchvision[device-gfx1151]==' + current_package_versions['torchvision'],
                 'torchaudio==' + current_package_versions['torchaudio']],
                [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, *current_constraints_values,
                 '--index-url', FUN_MIGRAPHX_INDEX, 'migraphx==' + current_package_versions['migraphx'], 'migraphx-libs==' + current_package_versions['migraphx-libs']],
                [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, *current_constraints_values,
                 '--extra-index-url', FUN_ONNX_INDEX, 'onnxruntime-ep-migraphx==' + current_package_versions['onnxruntime-ep-migraphx'], 'onnx'],
                [current_uv_executable, 'pip', 'install', '--python', current_runtime_python, *current_constraints_values,
                 '-r', str(WORKFLOW_ROOT_DIRECTORY / 'generators/kimodo/requirements.txt')],
            ]
            for current_command_values in current_setup_commands:
                run_logged_management_command(current_command_values, current_trace_logger)
            current_pybind_path = subprocess.check_output([current_runtime_python, '-m', 'pybind11', '--cmakedir'], text=True).strip()
            current_build_search_path = os.pathsep.join(filter(None, (current_pybind_path, os.environ.get('CMAKE_PREFIX_PATH', ''))))
            current_build_binary_path = str(current_environment_path / 'bin') + os.pathsep + os.environ.get('PATH', '')
            run_logged_management_command(['env', 'SKIP_MOTION_CORRECTION_IN_SETUP=0', 'CMAKE_PREFIX_PATH=' + current_build_search_path,
                'PATH=' + current_build_binary_path, current_uv_executable, 'pip', 'install', '--python', current_runtime_python,
                *current_constraints_values, '--no-build-isolation', str(current_source_copy)], current_trace_logger)
            run_logged_management_command([current_uv_executable, 'pip', 'check', '--python', current_runtime_python], current_trace_logger)
            current_site_directory = Path(subprocess.check_output([current_runtime_python, '-c', "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True).strip())
            current_onnx_directory = current_site_directory / 'onnxruntime/capi'
            current_library_link = current_onnx_directory / 'libonnxruntime.so.1'
            if not current_library_link.exists():
                current_library_link.symlink_to('libonnxruntime.so.1.29.0')
            current_library_path = os.pathsep.join(filter(None, (str(current_onnx_directory), str(current_site_directory / 'migraphx_libs'), os.environ.get('LD_LIBRARY_PATH', ''))))
            run_logged_management_command(['env', 'LD_LIBRARY_PATH=' + current_library_path, current_runtime_python, '-c',
                'import motion_correction._motion_correction; import kimodo; from generators.wan_fun.vendor.videox_fun.dwpose_utils.wholebody import Wholebody\n' + build_fun_gpu_validation()], current_trace_logger)
        current_trace_logger.emit_launch_trace('complete', 'Kimodo ROCm 환경 준비 완료. 모델은 별도로 준비하세요.')
    except BaseException as current_setup_error:
        current_trace_logger.emit_launch_trace('failure', f'{type(current_setup_error).__name__}: {current_setup_error}')
        raise
    finally:
        current_trace_logger.close_launch_log()


if __name__ == '__main__':
    prepare_kimodo_runtime_environment()
