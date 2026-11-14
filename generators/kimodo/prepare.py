"""고정 Kimodo·비양자화 인코더 자료 다운로드. 실행 로그와 5초 heartbeat를 남긴다."""
import fcntl
import hashlib
import os
import subprocess
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from generators.kimodo.contracts import KIMODO_ASSET_CONFIG, KIMODO_ENVIRONMENT_PYTHON, read_converted_encoder_files, KIMODO_MODEL_ROOT, KIMODO_SOURCE_ROOT, KIMODO_WORKSPACE_ROOT, inspect_motion_correction_runtime, inspect_kimodo_assets
from tools.review.common.generation_records import write_record_atomically


def prepare_kimodo_assets():
    if not KIMODO_ENVIRONMENT_PYTHON.is_file():
        raise ValueError('Kimodo ROCm 실행 환경을 먼저 준비하세요: .local/venvs/kimodo-rocm')
    KIMODO_MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    with (KIMODO_MODEL_ROOT/'.prepare.lock').open('a') as current_prepare_lock:
        fcntl.flock(current_prepare_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current_asset_status = inspect_kimodo_assets()
        if current_asset_status['missing'] == ['공식 후처리 motion_correction 실행 환경']:
            install_kimodo_official_runtime()
            return
        download_kimodo_pinned_assets()


def install_kimodo_official_runtime():
    """공식 setup으로 후처리 확장을 빌드하며 ROCm 의존성은 교체하지 않는다."""
    if inspect_motion_correction_runtime():
        return
    print('Kimodo 공식 setup: motion_correction 네이티브 확장 준비', flush=True)
    current_python_executable = str(KIMODO_ENVIRONMENT_PYTHON)
    current_pybind_check = subprocess.run([current_python_executable, '-c', 'import pybind11'], capture_output=True, check=False)
    if current_pybind_check.returncode:
        subprocess.run([current_python_executable, '-m', 'pip', 'install', '--no-deps', 'pybind11>=3,<4'], check=True)
    current_pybind_directory = subprocess.check_output([current_python_executable, '-m', 'pybind11', '--cmakedir'], text=True).strip()
    current_build_environment = os.environ.copy()
    current_build_environment['SKIP_MOTION_CORRECTION_IN_SETUP'] = '0'
    current_build_environment['CMAKE_PREFIX_PATH'] = os.pathsep.join(filter(None, (current_pybind_directory, current_build_environment.get('CMAKE_PREFIX_PATH', ''))))
    subprocess.run([current_python_executable, '-m', 'pip', 'install', '--no-deps', '--no-build-isolation', str(KIMODO_SOURCE_ROOT)],
                   cwd=KIMODO_WORKSPACE_ROOT, env=current_build_environment, check=True)
    if not inspect_motion_correction_runtime():
        raise RuntimeError('Kimodo 공식 setup 후 motion_correction 확장을 불러올 수 없습니다.')


def download_kimodo_pinned_assets():
    current_log_root = KIMODO_WORKSPACE_ROOT/'.tmp/test/kimodo-prepare'/datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
    current_log_root.mkdir(parents=True)
    current_stop_event = threading.Event()
    current_start_time = time.monotonic()
    def record_prepare_progress(current_message_text):
        current_log_line = f'{datetime.now().isoformat()}/kimodo/prepare {current_message_text}'
        print(current_log_line,flush=True)
        with (current_log_root/'prepare.log').open('a') as current_log_stream:
            current_log_stream.write(current_log_line+'\n')
    def record_prepare_heartbeat():
        while not current_stop_event.wait(5):
            record_prepare_progress(f'heartbeat elapsed={time.monotonic()-current_start_time:.1f}s 모델 자료 준비 중')
    current_heartbeat_thread = threading.Thread(target=record_prepare_heartbeat,daemon=True)
    current_heartbeat_thread.start()
    try:
        from tools.review.common.model_huggingface_download import tracked_hf_hub_download as hf_hub_download
        current_blob_path = KIMODO_MODEL_ROOT/'ollama/llama3-8b-instruct-fp16.gguf'
        try:
            read_converted_encoder_files(current_verify_hashes=True)
        except (OSError, ValueError, KeyError, TypeError):
            record_prepare_progress('Ollama FP16 다운로드 및 변환')
            subprocess.run([
                str(KIMODO_ENVIRONMENT_PYTHON), '-m', 'generators.kimodo.ollama_encoder',
                str(current_blob_path), str(KIMODO_MODEL_ROOT/'encoder-base-ollama'),
            ], cwd=KIMODO_WORKSPACE_ROOT, check=True)
            read_converted_encoder_files()
        KIMODO_SOURCE_ROOT.parent.mkdir(parents=True,exist_ok=True)
        if not KIMODO_SOURCE_ROOT.exists():
            subprocess.run(['git','clone','https://github.com/nv-tlabs/kimodo.git',str(KIMODO_SOURCE_ROOT)],check=True)
        subprocess.run(['git','-C',str(KIMODO_SOURCE_ROOT),'checkout','--detach',KIMODO_ASSET_CONFIG['source_revision']],check=True)
        current_revision_text = subprocess.check_output(['git','-C',str(KIMODO_SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip()
        if current_revision_text != KIMODO_ASSET_CONFIG['source_revision']:
            raise ValueError('소스 리비전 불일치')
        (KIMODO_SOURCE_ROOT.parent/'PINNED_REVISION').write_text(current_revision_text)
        install_kimodo_official_runtime()
        current_file_hashes = {}
        for current_asset_record in KIMODO_ASSET_CONFIG['models']:
            for current_file_record in current_asset_record['files']:
                record_prepare_progress(f"download {current_asset_record['repository']} {current_file_record['path']}")
                current_file_path = hf_hub_download(current_asset_record['repository'],current_file_record['path'],revision=current_asset_record['revision'],local_dir=KIMODO_MODEL_ROOT/current_asset_record['role'],token=False)
                if Path(current_file_path).stat().st_size != current_file_record['size']:
                    raise ValueError(f'모델 파일 크기 불일치: {current_file_path}')
                with open(current_file_path,'rb') as current_file_stream:
                    current_file_hash = hashlib.file_digest(current_file_stream,'sha256').hexdigest()
                if current_file_record['sha256'] and current_file_hash != current_file_record['sha256']:
                    raise ValueError(f'가중치 해시 불일치: {current_file_path}')
                current_file_hashes[str(current_file_path)] = current_file_hash
        write_record_atomically(KIMODO_MODEL_ROOT/'prepared.json',{'source_revision':current_revision_text,'models':KIMODO_ASSET_CONFIG['models'],'files':current_file_hashes})
        write_record_atomically(current_log_root/'result.json',{'status':'completed','model_root':str(KIMODO_MODEL_ROOT)})
        record_prepare_progress(f'완료 model_root={KIMODO_MODEL_ROOT}')
    except BaseException:
        record_prepare_progress(traceback.format_exc())
        write_record_atomically(current_log_root/'result.json',{'status':'failed','model_root':str(KIMODO_MODEL_ROOT)})
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join()

if __name__ == '__main__':
    prepare_kimodo_assets()
