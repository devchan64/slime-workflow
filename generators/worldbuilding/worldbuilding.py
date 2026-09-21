#!/usr/bin/env python3
"""고정 CUDA 환경을 준비하고 로컬 문서 작업을 실행한다."""
from __future__ import annotations

import argparse
import fcntl
import contextlib
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import traceback
import urllib.request
from zoneinfo import ZoneInfo

WORKFLOW_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_MODULE_ROOT = Path(__file__).resolve().parent
RUNTIME_INSTALL_ROOT = WORKFLOW_REPOSITORY_ROOT / '.local/worldbuilding'
RUNTIME_PYTHON_PATH = RUNTIME_INSTALL_ROOT / 'venv/bin/python'
MODEL_DOWNLOAD_ROOT = WORKFLOW_REPOSITORY_ROOT / '.model/worldbuilding'
MODEL_UPSTREAM_NAME = 'Qwen/Qwen3.5-4B'
MODEL_DOWNLOAD_NAME = 'Qwen_Qwen3.5-4B-Q4_K_M.gguf'
MODEL_DOWNLOAD_REVISION = '4168f45a16a1290d65a4ec0fa312ae917a4c15d6'
MODEL_DOWNLOAD_SHA256 = '13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983'
MODEL_DOWNLOAD_URL = f'https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/resolve/{MODEL_DOWNLOAD_REVISION}/{MODEL_DOWNLOAD_NAME}'
SOURCE_RELEASE_NAME = 'b10964'
SOURCE_ARCHIVE_SHA256 = '4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe'
SOURCE_DOWNLOAD_URL = f'https://codeload.github.com/ggml-org/llama.cpp/tar.gz/refs/tags/{SOURCE_RELEASE_NAME}'
RUNTIME_SERVER_PATH = RUNTIME_INSTALL_ROOT / f'llama.cpp-{SOURCE_RELEASE_NAME}/build/bin/llama-server'
TRACE_HEARTBEAT_SECONDS = 4
CURRENT_LOG_PATH = None


def emit_runtime_trace(current_stage_name, current_message_text):
    """동일한 내용을 콘솔과 실행 로그에 기록한다."""
    current_trace_line = f'[{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/worldbuilding/{current_stage_name}] {current_message_text}'
    print(current_trace_line, flush=True)
    if CURRENT_LOG_PATH is not None:
        with CURRENT_LOG_PATH.open('a', encoding='utf-8') as current_log_stream:
            current_log_stream.write(current_trace_line + '\n')


@contextlib.contextmanager
def trace_runtime_progress(current_stage_name, current_detail_callback=lambda: '실행 중'):
    """장기 실행의 진행 상황을 4초마다 남긴다."""
    stop_heartbeat_event = threading.Event()
    heartbeat_start_time = time.monotonic()
    def emit_heartbeat_loop():
        while not stop_heartbeat_event.wait(TRACE_HEARTBEAT_SECONDS):
            emit_runtime_trace(current_stage_name, f'경과={time.monotonic()-heartbeat_start_time:.0f}s {current_detail_callback()}')
    heartbeat_worker_thread = threading.Thread(target=emit_heartbeat_loop, daemon=True)
    heartbeat_worker_thread.start()
    try:
        yield
    finally:
        stop_heartbeat_event.set()
        heartbeat_worker_thread.join()


@contextlib.contextmanager
def lock_gpu_runtime():
    """워크스페이스가 달라도 준비·추론은 한 번에 하나만 실행한다."""
    with (RUNTIME_INSTALL_ROOT/'runtime.lock').open('a') as runtime_lock_stream:
        try:
            fcntl.flock(runtime_lock_stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as current_lock_error:
            raise RuntimeError('다른 세계관 GPU 작업 또는 환경 준비가 진행 중입니다.') from current_lock_error
        try:
            yield
        finally:
            fcntl.flock(runtime_lock_stream,fcntl.LOCK_UN)


def calculate_file_digest(current_file_path):
    """대용량 파일도 순차 해시한다."""
    current_digest_value = hashlib.sha256()
    with current_file_path.open('rb') as current_file_stream:
        for current_byte_chunk in iter(lambda: current_file_stream.read(8 * 1024 * 1024), b''):
            current_digest_value.update(current_byte_chunk)
    return current_digest_value.hexdigest()


def execute_logged_command(current_command_parts, current_environment_values=None, current_working_directory=None):
    """외부 명령의 로그·heartbeat·실패 원인을 보존한다."""
    command_output_path = CURRENT_LOG_PATH.with_suffix('.command.log')
    emit_runtime_trace('command', ' '.join(str(current_part_value) for current_part_value in current_command_parts))
    with command_output_path.open('a', encoding='utf-8') as command_output_stream:
        command_process_handle = subprocess.Popen(current_command_parts, stdout=command_output_stream, stderr=subprocess.STDOUT, env=current_environment_values, cwd=current_working_directory)
        try:
            with trace_runtime_progress('command', lambda: f'pid={command_process_handle.pid} 로그바이트={command_output_path.stat().st_size}'):
                command_result_code = command_process_handle.wait()
        except BaseException:
            command_process_handle.terminate()
            command_process_handle.wait()
            raise
    if command_result_code:
        print('\n'.join(command_output_path.read_text(errors='replace').splitlines()[-30:]))
        raise RuntimeError(f'명령 실패({command_result_code}): {current_command_parts}; 로그={command_output_path}')


def download_verified_file(current_download_url, current_target_path, expected_sha256_value):
    """고정 해시의 다운로드만 원자적으로 확정한다."""
    current_target_path.parent.mkdir(parents=True, exist_ok=True)
    if current_target_path.exists():
        with trace_runtime_progress('verify'):
            if calculate_file_digest(current_target_path) != expected_sha256_value:
                raise ValueError(f'기존 파일 해시 불일치: {current_target_path}')
        return
    partial_download_path = current_target_path.with_suffix(current_target_path.suffix + '.partial')
    emit_runtime_trace('download', f'시작: {current_target_path.name}')
    with trace_runtime_progress('download', lambda: f'수신바이트={partial_download_path.stat().st_size if partial_download_path.exists() else 0}'):
        with urllib.request.urlopen(current_download_url, timeout=60) as response_stream_handle, partial_download_path.open('wb') as target_stream_handle:
            shutil.copyfileobj(response_stream_handle, target_stream_handle, 1024 * 1024)
        if calculate_file_digest(partial_download_path) != expected_sha256_value:
            raise ValueError(f'다운로드 해시 불일치: {partial_download_path}')
        partial_download_path.replace(current_target_path)
    emit_runtime_trace('download', f'완료: {current_target_path}')


def inspect_gpu_environment():
    """CUDA 호스트에서 GPU 가용성을 확인한다. CPU 추론은 허용하지 않는다."""
    if not shutil.which('nvidia-smi'):
        raise RuntimeError('nvidia-smi가 없습니다. 샌드박스 밖의 NVIDIA GPU 호스트에서 실행하세요.')
    gpu_command_result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,driver_version,compute_cap', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True)
    gpu_result_fields = [current_field_text.strip() for current_field_text in gpu_command_result.stdout.splitlines()[0].split(',')]
    emit_runtime_trace('gpu', gpu_command_result.stdout.strip())
    if len(gpu_result_fields) != 5 or float(gpu_result_fields[2]) < 4096:
        raise RuntimeError('GPU 여유 메모리가 4096MiB 미만이거나 GPU 정보를 해석할 수 없습니다.')
    return gpu_result_fields


def prepare_runtime_environment():
    """시스템 드라이버를 바꾸지 않고 전용 Python·CUDA·서버·모델을 준비한다."""
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('현재 자동 준비 지원 환경은 Linux x86_64 NVIDIA CUDA입니다.')
    current_gpu_fields = inspect_gpu_environment()
    if not shutil.which('uv') or not shutil.which('g++'):
        raise RuntimeError('호스트에 uv와 g++가 필요합니다.')
    if not RUNTIME_PYTHON_PATH.exists():
        execute_logged_command(['uv', 'venv', '--python', sys.executable, str(RUNTIME_PYTHON_PATH.parent.parent)])
    execute_logged_command(['uv', 'pip', 'sync', '--python', str(RUNTIME_PYTHON_PATH), '--require-hashes', str(WORKFLOW_MODULE_ROOT / 'requirements.lock')])
    runtime_python_site = subprocess.check_output([str(RUNTIME_PYTHON_PATH), '-c', 'import site; print(site.getsitepackages()[0])'], text=True).strip()
    cuda_compiler_paths = list(Path(runtime_python_site).rglob('bin/nvcc'))
    if len(cuda_compiler_paths) != 1:
        raise RuntimeError(f'CUDA nvcc 경로를 하나로 결정할 수 없습니다: {cuda_compiler_paths}')
    cuda_toolkit_root = cuda_compiler_paths[0].parent.parent
    if not (cuda_toolkit_root / 'lib64').exists():
        (cuda_toolkit_root / 'lib64').symlink_to('lib', target_is_directory=True)
    for cuda_library_path in (cuda_toolkit_root / 'lib').glob('*.so.*'):
        cuda_link_path = cuda_library_path.with_name(cuda_library_path.name.split('.so.')[0] + '.so')
        if not cuda_link_path.exists():
            cuda_link_path.symlink_to(cuda_library_path.name)
    runtime_process_environment = os.environ.copy()
    runtime_process_environment['PATH'] = str(RUNTIME_PYTHON_PATH.parent) + ':' + str(cuda_toolkit_root / 'bin') + ':' + runtime_process_environment.get('PATH', '')
    runtime_process_environment['LD_LIBRARY_PATH'] = str(cuda_toolkit_root / 'lib')
    source_archive_path = RUNTIME_INSTALL_ROOT / f'{SOURCE_RELEASE_NAME}.tar.gz'
    download_verified_file(SOURCE_DOWNLOAD_URL, source_archive_path, SOURCE_ARCHIVE_SHA256)
    source_directory_path = RUNTIME_INSTALL_ROOT / f'llama.cpp-{SOURCE_RELEASE_NAME}'
    if not source_directory_path.exists():
        with tarfile.open(source_archive_path) as source_archive_handle:
            source_archive_handle.extractall(RUNTIME_INSTALL_ROOT, filter='data')
    execute_logged_command([str(RUNTIME_PYTHON_PATH.parent / 'cmake'), '-S', str(source_directory_path), '-B', str(source_directory_path / 'build'), '-G', 'Ninja', '-DGGML_CUDA=ON', '-DGGML_NATIVE=OFF', '-DLLAMA_CURL=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF', '-DCMAKE_BUILD_TYPE=Release', f'-DCMAKE_CUDA_COMPILER={cuda_compiler_paths[0]}', f'-DCUDAToolkit_ROOT={cuda_toolkit_root}', f'-DCMAKE_CUDA_ARCHITECTURES={current_gpu_fields[4].replace(".", "")}'], runtime_process_environment)
    execute_logged_command([str(RUNTIME_PYTHON_PATH.parent / 'cmake'), '--build', str(source_directory_path / 'build'), '--target', 'llama-server', '-j', '4'], runtime_process_environment)
    download_verified_file(MODEL_DOWNLOAD_URL, MODEL_DOWNLOAD_ROOT / MODEL_DOWNLOAD_NAME, MODEL_DOWNLOAD_SHA256)
    prepared_manifest_data = {'model_upstream_name': MODEL_UPSTREAM_NAME, 'model_download_revision': MODEL_DOWNLOAD_REVISION, 'model_file_sha256': MODEL_DOWNLOAD_SHA256, 'server_release_name': SOURCE_RELEASE_NAME, 'server_binary_sha256': calculate_file_digest(RUNTIME_SERVER_PATH), 'runtime_library_paths': [str(current_library_path) for current_library_path in Path(runtime_python_site).rglob('lib') if 'nvidia' in str(current_library_path)], 'requirements_file_sha256': calculate_file_digest(WORKFLOW_MODULE_ROOT / 'requirements.lock')}
    (RUNTIME_INSTALL_ROOT / 'prepared.json').write_text(json.dumps(prepared_manifest_data, indent=2) + '\n')
    emit_runtime_trace('prepared', f'model_id={MODEL_UPSTREAM_NAME} model_root={MODEL_DOWNLOAD_ROOT} model_path={MODEL_DOWNLOAD_ROOT / MODEL_DOWNLOAD_NAME} binary_path={RUNTIME_SERVER_PATH}')


def configure_document_workspace():
    """운영자가 지정한 비공개 문서 루트를 로컬 YAML 설정으로 저장한다."""
    configuration_argument_parser=argparse.ArgumentParser(description='세계관 문서 연결 설정')
    configuration_argument_parser.add_argument('configuration_action_name',choices=['configure'])
    configuration_argument_parser.add_argument('--document-root',required=True,type=Path,dest='source_document_root')
    configuration_argument_parser.add_argument('--state-root',required=True,type=Path,dest='private_state_root')
    configuration_argument_parser.add_argument('--write-root',action='append',required=True,dest='allowed_write_roots')
    configuration_argument_parser.add_argument('--required-source',action='append',required=True,dest='required_source_paths')
    configuration_argument_parser.add_argument('--protected-document',action='append',required=True,dest='protected_document_paths')
    configuration_argument_parser.add_argument('--catalog',default='',dest='managed_catalog_path')
    configuration_argument_values=configuration_argument_parser.parse_args()
    if not configuration_argument_values.source_document_root.is_dir():
        raise ValueError('문서 루트가 없습니다.')
    workspace_configuration_data={'workspace_schema_version':1,'source_document_root':str(configuration_argument_values.source_document_root.resolve()),'private_state_root':str(configuration_argument_values.private_state_root.resolve()),'allowed_write_roots':configuration_argument_values.allowed_write_roots,'required_source_paths':configuration_argument_values.required_source_paths,'protected_document_paths':configuration_argument_values.protected_document_paths,'managed_catalog_path':configuration_argument_values.managed_catalog_path}
    configuration_output_lines=[]
    for configuration_field_name,configuration_field_value in workspace_configuration_data.items():
        if isinstance(configuration_field_value,list):
            configuration_output_lines.append(configuration_field_name+':')
            configuration_output_lines.extend('  - '+json.dumps(current_path_value,ensure_ascii=False) for current_path_value in configuration_field_value)
        else:
            configuration_output_lines.append(configuration_field_name+': '+json.dumps(configuration_field_value,ensure_ascii=False))
    workspace_configuration_path=RUNTIME_INSTALL_ROOT/'workspace.yaml'
    if workspace_configuration_path.exists():
        raise FileExistsError(f'기존 설정은 덮어쓰지 않습니다. 직접 검토하여 수정하세요: {workspace_configuration_path}')
    workspace_configuration_path.write_text('\n'.join(configuration_output_lines)+'\n')
    emit_runtime_trace('configure',f'문서 연결 설정: {workspace_configuration_path}')


def run_worldbuilding_command():
    """준비 명령 이후 전용 환경으로 실행을 전달한다."""
    global CURRENT_LOG_PATH
    os.umask(0o077)
    RUNTIME_INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
    CURRENT_LOG_PATH = RUNTIME_INSTALL_ROOT / f'command-{datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d-%H%M%S-%f")}.log'
    if len(sys.argv) > 1 and sys.argv[1] == 'configure':
        configure_document_workspace()
        return
    if len(sys.argv) > 1 and sys.argv[1] == 'prepare':
        if len(sys.argv) != 2:
            raise ValueError('prepare는 모델·런타임 변경 인자를 받지 않습니다.')
        with lock_gpu_runtime():
            prepare_runtime_environment()
        return
    if Path(sys.prefix).resolve() != RUNTIME_PYTHON_PATH.parent.parent.resolve():
        if not RUNTIME_PYTHON_PATH.exists():
            raise RuntimeError('먼저 python3 generators/worldbuilding/worldbuilding.py prepare를 실행하세요.')
        os.execv(str(RUNTIME_PYTHON_PATH), [str(RUNTIME_PYTHON_PATH), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.modules["worldbuilding"] = sys.modules[__name__]
    from runtime import execute_document_command
    execute_document_command()


if __name__ == '__main__':
    try:
        run_worldbuilding_command()
    except Exception:
        emit_runtime_trace('failed', f'model_id={MODEL_UPSTREAM_NAME} model_root={MODEL_DOWNLOAD_ROOT} model_path={MODEL_DOWNLOAD_ROOT / MODEL_DOWNLOAD_NAME} binary_path={RUNTIME_SERVER_PATH}')
        current_failure_text = traceback.format_exc()
        if CURRENT_LOG_PATH:
            with CURRENT_LOG_PATH.open('a') as current_log_stream:
                current_log_stream.write(current_failure_text)
            print('\n'.join(CURRENT_LOG_PATH.read_text().splitlines()[-30:]), file=sys.stderr)
        else:
            print(current_failure_text, file=sys.stderr)
        sys.exit(1)
