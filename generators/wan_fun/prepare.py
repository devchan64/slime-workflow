"""고정 Fun Control 모델을 다운로드하고 공용 실행 자산을 확인한다."""
import shutil
import hashlib
import subprocess
import sys
import threading
import traceback
from datetime import datetime

from generators.wan_fun.contracts import FUN_MODEL_FILES, FUN_MODEL_IDENTIFIER, FUN_MODEL_REVISION, FUN_RUNTIME_DIRECTORY, FUN_WORKSPACE_ROOT, inspect_fun_assets

FUN_MODEL_DIRECTORY = FUN_WORKSPACE_ROOT / '.model/wan22-fun-control'
FUN_PREPARE_LOG_DIRECTORY = FUN_WORKSPACE_ROOT / '.tmp/test/wan22-fun-control-prepare'
FUN_SHARED_MODEL_SOURCES = {
    'encoder': ('Comfy-Org/Wan-2.1', '2bb519992ec7fb8ca66f6807335f67a92bf13e0b', 'split_files/text_encoders/umt5_xxl_fp16.safetensors', '7b8850f1961e1cf8a77cca4c964a358d303f490833c6c087d0cff4b2f99db2af'),
    'vae': ('Comfy-Org/Wan-2.1', '2bb519992ec7fb8ca66f6807335f67a92bf13e0b', 'split_files/vae/wan_2.1_vae.safetensors', '2fc39d31359a4b0a64f55876d8ff7fa8d780956ae2cb13463b0223e15148976b'),
}
FUN_RUNTIME_SOURCES = {
    'ComfyUI': ('https://github.com/Comfy-Org/ComfyUI.git', 'b8730510db30c8858e1e5d8e126ef19eac395560'),
}
FUN_DIFFUSION_HASHES = {'high': 'e4be07ca25d67aaf3461ef87fbb5ad8762f602a5efa620aea9dc250ac2747a9d',
                        'low': 'd82bc21cd703e089eee4f6fabc25e90ebbd00965623fdc5e83d46d01dbeac2c3'}


def prepare_fun_control_models():
    from huggingface_hub import hf_hub_download
    import torch
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('ROCm PyTorch와 접근 가능한 AMD GPU가 필요합니다.')

    FUN_PREPARE_LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    current_log_path = FUN_PREPARE_LOG_DIRECTORY / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.log')
    current_stop_event = threading.Event()
    current_log_lock = threading.Lock()

    def write_prepare_trace(current_stage_name, current_message_text):
        current_log_line = f'{datetime.now().isoformat()}/wan-fun-prepare/{current_stage_name} {current_message_text}'
        with current_log_lock:
            print(current_log_line, flush=True)
            with current_log_path.open('a', encoding='utf-8') as current_log_stream:
                current_log_stream.write(current_log_line + '\n')

    def emit_prepare_heartbeat():
        while not current_stop_event.wait(5):
            current_download_bytes = sum(current_file_path.stat().st_size for current_file_path in FUN_MODEL_DIRECTORY.rglob('*.incomplete') if current_file_path.is_file())
            write_prepare_trace('heartbeat', f'model_root={FUN_MODEL_DIRECTORY} downloading_bytes={current_download_bytes}')

    current_heartbeat_thread = threading.Thread(target=emit_prepare_heartbeat, daemon=True)
    current_heartbeat_thread.start()
    try:
        write_prepare_trace('start', f'model_id={FUN_MODEL_IDENTIFIER} revision={FUN_MODEL_REVISION} model_root={FUN_MODEL_DIRECTORY} binary={sys.executable}')
        current_missing_bytes = sum(current_size for current_path, current_size in FUN_MODEL_FILES.values()
                                    if not (FUN_WORKSPACE_ROOT / current_path).is_file())
        if shutil.disk_usage(FUN_WORKSPACE_ROOT).free < current_missing_bytes:
            raise RuntimeError(f'모델 다운로드 공간 부족: {current_missing_bytes}바이트 필요')
        for current_model_stage in ('high', 'low'):
            current_relative_path, current_expected_size = FUN_MODEL_FILES[current_model_stage]
            current_model_path = FUN_WORKSPACE_ROOT / current_relative_path
            current_remote_path = current_model_path.relative_to(FUN_MODEL_DIRECTORY).as_posix()
            write_prepare_trace('download', f'model_id={FUN_MODEL_IDENTIFIER} model_path={current_model_path}')
            current_download_path = hf_hub_download(repo_id=FUN_MODEL_IDENTIFIER, filename=current_remote_path,
                revision=FUN_MODEL_REVISION, local_dir=FUN_MODEL_DIRECTORY)
            if current_model_path.stat().st_size != current_expected_size:
                raise ValueError(f'모델 파일 크기 불일치: {current_download_path}')
            with current_model_path.open('rb') as current_model_stream:
                if hashlib.file_digest(current_model_stream, 'sha256').hexdigest() != FUN_DIFFUSION_HASHES[current_model_stage]:
                    raise ValueError(f'모델 해시 불일치: {current_model_path}')
            write_prepare_trace('verified', f'model_path={current_model_path} bytes={current_expected_size}')
        for current_model_stage, current_source_record in FUN_SHARED_MODEL_SOURCES.items():
            current_repository_name, current_revision_hash, current_remote_path, current_expected_hash = current_source_record
            current_relative_path, current_expected_size = FUN_MODEL_FILES[current_model_stage]
            current_model_path = FUN_WORKSPACE_ROOT / current_relative_path
            write_prepare_trace('download', f'model_id={current_repository_name} model_path={current_model_path}')
            if not current_model_path.exists():
                hf_hub_download(repo_id=current_repository_name, filename=current_remote_path,
                    revision=current_revision_hash, local_dir=FUN_WORKSPACE_ROOT / '.model/wan22-animate-components')
            with current_model_path.open('rb') as current_model_stream:
                current_model_hash = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
            if current_model_path.stat().st_size != current_expected_size or current_model_hash != current_expected_hash:
                raise ValueError(f'공용 모델 크기·해시 불일치: {current_model_path}')
            write_prepare_trace('verified', f'model_path={current_model_path} sha256={current_model_hash}')
        FUN_RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True)
        for current_runtime_name, current_runtime_source in FUN_RUNTIME_SOURCES.items():
            current_repository_url, current_revision_hash = current_runtime_source
            current_runtime_path = FUN_RUNTIME_DIRECTORY / current_runtime_name
            if not current_runtime_path.exists():
                subprocess.run(['git', 'clone', '--no-checkout', current_repository_url, str(current_runtime_path)], check=True)
                subprocess.run(['git', '-C', str(current_runtime_path), 'checkout', '--detach', current_revision_hash], check=True)
            current_actual_revision = subprocess.check_output(['git', '-C', str(current_runtime_path), 'rev-parse', 'HEAD'], text=True).strip()
            if current_actual_revision != current_revision_hash:
                raise ValueError(f'기존 실행 환경 리비전 불일치: {current_runtime_path}')
            if subprocess.check_output(['git', '-C', str(current_runtime_path), 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
                raise ValueError(f'기존 실행 환경에 수정 사항이 있습니다: {current_runtime_path}')
            write_prepare_trace('runtime', f'path={current_runtime_path} revision={current_revision_hash}')
        for current_runtime_name in FUN_RUNTIME_SOURCES:
            current_requirements_path = FUN_RUNTIME_DIRECTORY / current_runtime_name / 'requirements.txt'
            if current_requirements_path.is_file():
                write_prepare_trace('dependencies', f'binary={sys.executable} requirements={current_requirements_path}')
                subprocess.run([sys.executable, '-m', 'pip', 'install', '--constraint', str(FUN_WORKSPACE_ROOT / 'generators/wan_fun/rocm-constraints.txt'), '-r', str(current_requirements_path)], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'check'], check=True)
        for current_runtime_name, current_runtime_source in FUN_RUNTIME_SOURCES.items():
            (FUN_RUNTIME_DIRECTORY / current_runtime_name / 'PINNED_REVISION').write_text(current_runtime_source[1] + '\n', encoding='utf-8')
        current_asset_status = inspect_fun_assets()
        if not current_asset_status['ready']:
            raise RuntimeError(current_asset_status['message'])
        write_prepare_trace('complete', f'model_root={FUN_MODEL_DIRECTORY}')
    except BaseException:
        write_prepare_trace('failure', traceback.format_exc())
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join()


if __name__ == '__main__':
    prepare_fun_control_models()
