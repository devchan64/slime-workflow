#!/usr/bin/env python3
"""고정 ROCm 환경을 준비하고 로컬 문서 작업을 실행한다."""
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
RUNTIME_INSTALL_ROOT = WORKFLOW_REPOSITORY_ROOT / '.local/writer-agent'
RUNTIME_PYTHON_PATH = RUNTIME_INSTALL_ROOT / 'venv/bin/python'
MODEL_DOWNLOAD_ROOT = WORKFLOW_REPOSITORY_ROOT / '.model/writer-agent'
from workflow.common.hermes_model_download import (HERMES_MODEL_DIRECTORY, HERMES_MODEL_FILENAME,
    HERMES_MODEL_REVISION, HERMES_MODEL_SHA256, HERMES_MODEL_DOWNLOAD_URL, current_hermes_model_directory)
from workflow.common.model_storage_layout import resolve_writer_embedding_directory
_INITIAL_MODEL_DOWNLOAD_ROOT = MODEL_DOWNLOAD_ROOT


def embedding_model_directory():
    if MODEL_DOWNLOAD_ROOT != _INITIAL_MODEL_DOWNLOAD_ROOT:
        return MODEL_DOWNLOAD_ROOT
    return resolve_writer_embedding_directory(WORKFLOW_REPOSITORY_ROOT / '.model')
MODEL_UPSTREAM_NAME = 'Qwen/Qwen3.8-27B'
MODEL_DOWNLOAD_NAME = HERMES_MODEL_FILENAME
MODEL_DOWNLOAD_REVISION = HERMES_MODEL_REVISION
MODEL_DOWNLOAD_SHA256 = HERMES_MODEL_SHA256
MODEL_DOWNLOAD_URL = HERMES_MODEL_DOWNLOAD_URL
GENERATION_MODEL_PATH = HERMES_MODEL_DIRECTORY / HERMES_MODEL_FILENAME
_INITIAL_GENERATION_MODEL_PATH = GENERATION_MODEL_PATH


def generation_model_path():
    if GENERATION_MODEL_PATH != _INITIAL_GENERATION_MODEL_PATH:
        return GENERATION_MODEL_PATH
    return current_hermes_model_directory() / HERMES_MODEL_FILENAME
EMBEDDING_MODEL_NAME = 'Qwen/Qwen3-Embedding-0.6B-GGUF'
EMBEDDING_DOWNLOAD_NAME = 'Qwen3-Embedding-0.6B-f16.gguf'
EMBEDDING_DOWNLOAD_REVISION = '370f27d7550e0def9b39c1f16d3fbaa13aa67728'
EMBEDDING_DOWNLOAD_SHA256 = '421a27e58d165478cc7acb984a688c2aa41404968b0203e7cd743ece44c54340'
EMBEDDING_DOWNLOAD_URL = f'https://huggingface.co/{EMBEDDING_MODEL_NAME}/resolve/{EMBEDDING_DOWNLOAD_REVISION}/{EMBEDDING_DOWNLOAD_NAME}'
SOURCE_RELEASE_NAME = 'b10964'
SOURCE_ARCHIVE_SHA256 = '4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe'
SOURCE_DOWNLOAD_URL = f'https://codeload.github.com/ggml-org/llama.cpp/tar.gz/refs/tags/{SOURCE_RELEASE_NAME}'
RUNTIME_SERVER_PATH = RUNTIME_INSTALL_ROOT / f'llama.cpp-{SOURCE_RELEASE_NAME}/build-rocm/bin/llama-server'
TRACE_HEARTBEAT_SECONDS = 4
CURRENT_LOG_PATH = None


def emit_runtime_trace(current_stage_name, current_message_text):
    """동일한 내용을 콘솔과 실행 로그에 기록한다."""
    current_trace_line = f'[{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/writer-agent/{current_stage_name}] {current_message_text}'
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
            raise RuntimeError('다른 작가 에이전트 GPU 작업 또는 환경 준비가 진행 중입니다.') from current_lock_error
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
    from workflow.common.model_http_download import download_verified_http
    emit_runtime_trace('download', f'시작: {current_target_path.name}')
    download_verified_http(current_download_url, current_target_path, expected_sha256_value, 'writer-agent/' + current_target_path.name)
    emit_runtime_trace('download', f'완료: {current_target_path}')


def inspect_gpu_environment(minimum_memory_mib=12288):
    """ROCm 장치와 공용 GPU 메모리 측정값을 확인한다."""
    from workflow.common.gpu_job_queue import read_gpu_memory, read_gpu_memory_domain, read_host_available_memory
    current_rocminfo_result = subprocess.run(['rocminfo'], capture_output=True, text=True, check=True, timeout=30)
    if 'gfx1151' not in current_rocminfo_result.stdout:
        raise RuntimeError('지원 대상 gfx1151 ROCm GPU를 확인할 수 없습니다.')
    current_total_memory, current_free_memory = read_gpu_memory()
    if read_gpu_memory_domain() == 'gtt':
        current_free_memory = min(current_free_memory, read_host_available_memory())
    emit_runtime_trace('gpu', f'gfx1151 total={current_total_memory}MiB free={current_free_memory}MiB')
    if current_free_memory < minimum_memory_mib:
        raise RuntimeError(f'GPU 여유 메모리가 {minimum_memory_mib}MiB 미만입니다.')
    return 'gfx1151'


def prepare_runtime_environment():
    """호스트 ROCm으로 고정 llama.cpp 서버와 모델을 준비한다."""
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('현재 자동 준비 지원 환경은 Linux x86_64 ROCm입니다.')
    current_gpu_architecture = inspect_gpu_environment()
    current_rocm_root = Path(os.environ.get('ROCM_PATH', '/opt/rocm'))
    current_hip_compiler = current_rocm_root/'bin/hipcc'
    current_uv_path = shutil.which('uv')
    if not current_uv_path:
        current_uv_candidate = WORKFLOW_REPOSITORY_ROOT / '.venv/bin/uv'
        if current_uv_candidate.is_file() and os.access(current_uv_candidate, os.X_OK):
            current_uv_path = str(current_uv_candidate)
    if not current_hip_compiler.is_file() or not current_uv_path or not shutil.which('g++'):
        raise RuntimeError('ROCm hipcc, uv와 g++가 필요합니다.')
    if not RUNTIME_PYTHON_PATH.exists():
        execute_logged_command([current_uv_path, 'venv', '--python', sys.executable, str(RUNTIME_PYTHON_PATH.parent.parent)])
    execute_logged_command([current_uv_path, 'pip', 'sync', '--python', str(RUNTIME_PYTHON_PATH), '--require-hashes', str(WORKFLOW_MODULE_ROOT / 'requirements.lock')])
    current_build_environment = os.environ.copy()
    current_build_environment['PATH'] = str(RUNTIME_PYTHON_PATH.parent) + ':' + str(current_rocm_root/'bin') + ':' + current_build_environment.get('PATH', '')
    source_archive_path = RUNTIME_INSTALL_ROOT / f'{SOURCE_RELEASE_NAME}.tar.gz'
    download_verified_file(SOURCE_DOWNLOAD_URL, source_archive_path, SOURCE_ARCHIVE_SHA256)
    source_directory_path = RUNTIME_INSTALL_ROOT / f'llama.cpp-{SOURCE_RELEASE_NAME}'
    if not source_directory_path.exists():
        with tarfile.open(source_archive_path) as source_archive_handle:
            source_archive_handle.extractall(RUNTIME_INSTALL_ROOT, filter='data')
    current_build_directory = source_directory_path/'build-rocm'
    execute_logged_command([str(RUNTIME_PYTHON_PATH.parent/'cmake'), '-S', str(source_directory_path), '-B', str(current_build_directory), '-G', 'Ninja', '-DGGML_HIP=ON', '-DGGML_CUDA=OFF', '-DGGML_NATIVE=OFF', '-DLLAMA_CURL=OFF', '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF', '-DCMAKE_BUILD_TYPE=Release', f'-DCMAKE_HIP_COMPILER={current_rocm_root}/llvm/bin/clang++', f'-DAMDGPU_TARGETS={current_gpu_architecture}'], current_build_environment)
    execute_logged_command([str(RUNTIME_PYTHON_PATH.parent/'cmake'), '--build', str(current_build_directory), '--target', 'llama-server', '-j', '4'], current_build_environment)
    download_verified_file(MODEL_DOWNLOAD_URL, generation_model_path(), MODEL_DOWNLOAD_SHA256)
    prepare_embedding_model()
    prepared_manifest_data = {'backend': 'rocm', 'gpu_architecture': current_gpu_architecture, 'model_upstream_name': MODEL_UPSTREAM_NAME, 'model_download_revision': MODEL_DOWNLOAD_REVISION, 'model_file_sha256': MODEL_DOWNLOAD_SHA256, 'embedding_file_sha256': EMBEDDING_DOWNLOAD_SHA256, 'server_release_name': SOURCE_RELEASE_NAME, 'server_binary_sha256': calculate_file_digest(RUNTIME_SERVER_PATH), 'runtime_library_paths': [str(current_rocm_root/'lib')], 'requirements_file_sha256': calculate_file_digest(WORKFLOW_MODULE_ROOT/'requirements.lock')}
    (RUNTIME_INSTALL_ROOT/'prepared.json').write_text(json.dumps(prepared_manifest_data, indent=2)+'\n')
    emit_runtime_trace('prepared', f'model_id={MODEL_UPSTREAM_NAME} model_path={generation_model_path()} binary_path={RUNTIME_SERVER_PATH}')


def prepare_embedding_model():
    inspect_gpu_environment(1024)
    download_verified_file(EMBEDDING_DOWNLOAD_URL,embedding_model_directory()/EMBEDDING_DOWNLOAD_NAME,EMBEDDING_DOWNLOAD_SHA256)
    emit_runtime_trace('prepared',f'embedding_model={EMBEDDING_MODEL_NAME} model_path={embedding_model_directory()/EMBEDDING_DOWNLOAD_NAME}')


def inspect_writer_model_files():
    """고정 모델 두 파일의 마지막 검증 결과와 현재 파일 식별자를 확인한다."""
    current_receipt_path = WORKFLOW_REPOSITORY_ROOT/'.local/model-preparation/writer-model/files.json'
    try:
        current_receipt_record = json.loads(current_receipt_path.read_text())
        for current_file_name, current_expected_hash in ((MODEL_DOWNLOAD_NAME, MODEL_DOWNLOAD_SHA256), (EMBEDDING_DOWNLOAD_NAME, EMBEDDING_DOWNLOAD_SHA256)):
            current_file_path = generation_model_path() if current_file_name == MODEL_DOWNLOAD_NAME else embedding_model_directory()/current_file_name
            current_file_stat = current_file_path.stat()
            current_file_record = current_receipt_record[current_file_name]
            if (not current_file_path.is_file() or current_file_path.is_symlink() or current_file_record !=
                    {'sha256': current_expected_hash, 'size': current_file_stat.st_size, 'mtime_ns': current_file_stat.st_mtime_ns, 'ctime_ns': current_file_stat.st_ctime_ns}):
                return False
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def prepare_writer_model_files():
    """작가 문서 작업 공간 없이 고정 모델 파일만 다운로드하고 검증한다."""
    from workflow.common.generation_records import write_record_atomically
    RUNTIME_INSTALL_ROOT.mkdir(parents=True, exist_ok=True)
    with lock_gpu_runtime():
        current_file_specs = ((MODEL_DOWNLOAD_URL, MODEL_DOWNLOAD_NAME, MODEL_DOWNLOAD_SHA256),
                              (EMBEDDING_DOWNLOAD_URL, EMBEDDING_DOWNLOAD_NAME, EMBEDDING_DOWNLOAD_SHA256))
        current_receipt_record = {}
        for current_file_url, current_file_name, current_expected_hash in current_file_specs:
            current_file_path = generation_model_path() if current_file_name == MODEL_DOWNLOAD_NAME else embedding_model_directory()/current_file_name
            download_verified_file(current_file_url, current_file_path, current_expected_hash)
            current_file_stat = current_file_path.stat()
            current_receipt_record[current_file_name] = {'sha256': current_expected_hash, 'size': current_file_stat.st_size,
                                                         'mtime_ns': current_file_stat.st_mtime_ns, 'ctime_ns': current_file_stat.st_ctime_ns}
        current_receipt_path = WORKFLOW_REPOSITORY_ROOT/'.local/model-preparation/writer-model/files.json'
        current_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        write_record_atomically(current_receipt_path, current_receipt_record)


def prepare_new_writer_environment():
    """GPU 잠금 안에서 기존 환경을 다시 확인한 뒤 최초 준비한다."""
    current_protected_paths = (RUNTIME_PYTHON_PATH.parent.parent,
        RUNTIME_INSTALL_ROOT / ('llama.cpp-' + SOURCE_RELEASE_NAME),
        RUNTIME_INSTALL_ROOT / (SOURCE_RELEASE_NAME + '.tar.gz'),
        RUNTIME_INSTALL_ROOT / 'prepared.json')
    if RUNTIME_INSTALL_ROOT.is_symlink() or any(current_path_value.exists() or current_path_value.is_symlink() for current_path_value in current_protected_paths):
        raise ValueError('기존 작가 실행 환경이 발견되어 자동 변경하지 않습니다.')
    prepare_runtime_environment()


def execute_writer_preparation(current_argument_values, current_prepare_callback=None):
    global CURRENT_LOG_PATH
    if current_prepare_callback is None:
        current_prepare_callback = prepare_runtime_environment
    current_argument_values.run_dir.mkdir(parents=True,exist_ok=True)
    CURRENT_LOG_PATH=current_argument_values.run_dir/'execution.log'
    RUNTIME_INSTALL_ROOT.mkdir(parents=True,exist_ok=True)
    from generators.writer_agent.jobs import update_job_status, read_process_identity
    from workflow.common.generation_records import write_record_atomically
    current_preparation_lock = os.fdopen(current_argument_values.lock_fd, 'a') if current_argument_values.lock_fd is not None else contextlib.nullcontext()
    with current_preparation_lock:
        update_job_status(current_argument_values.run_dir,'preparing',process_id=os.getpid(),process_identity=read_process_identity(os.getpid()))
        if current_argument_values.status_path:
            write_record_atomically(current_argument_values.status_path, {'status': 'running'})
        try:
            with lock_gpu_runtime():
                current_prepare_callback()
        except BaseException as current_prepare_error:
            emit_runtime_trace('failed',traceback.format_exc())
            update_job_status(current_argument_values.run_dir,'failed',error=str(current_prepare_error))
            if current_argument_values.status_path:
                write_record_atomically(current_argument_values.status_path, {'status': 'failed'})
            raise
        else:
            update_job_status(current_argument_values.run_dir,'completed',summary='환경 준비 완료',error='')
            if current_argument_values.status_path:
                write_record_atomically(current_argument_values.status_path, {'status': 'completed'})


if __name__ == '__main__':
    current_argument_parser=argparse.ArgumentParser(description='작가 에이전트 고정 GPU 환경 준비')
    current_argument_parser.add_argument('--run-dir',type=Path,required=True)
    current_argument_parser.add_argument('--status-path',type=Path)
    current_argument_parser.add_argument('--lock-fd',type=int)
    current_argument_parser.add_argument('--new-only', action='store_true')
    current_argument_values=current_argument_parser.parse_args()
    execute_writer_preparation(current_argument_values, prepare_new_writer_environment if current_argument_values.new_only else None)
