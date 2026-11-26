"""공식 BF16 확산 모델과 텍스트 인코더를 다운로드하고 SHA-256으로 검증한다. GPU 추론은 실행하지 않는다."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import fcntl
import shutil
import sys
import threading
import traceback
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES, vace_model_path, vace_model_records, VACE_MODEL_IDENTIFIER, VACE_MODEL_REVISION, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION, VACE_ENCODER_REMOTE_FILES, validate_vace_assets


def prepare_shared_vae(path, size, expected_hash, repository, revision, remote_name):
    """Restore the pinned VAE from backup before attempting a Hub download."""
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        from workflow.common.model_backup_restore import restore_verified_backup
        if not restore_verified_backup(path, expected_hash, size):
            from workflow.common.model_http_download import download_verified_http
            url = f'https://huggingface.co/{repository}/resolve/{revision}/{remote_name}'
            download_verified_http(url, path, expected_hash, 'wan22-vace/vae', expected_total_bytes=size)
    import hashlib
    with path.open('rb') as stream:
        if path.stat().st_size != size or hashlib.file_digest(stream, 'sha256').hexdigest() != expected_hash:
            raise ValueError('공용 VAE 모델 크기 또는 SHA-256 불일치')


def prepare_vace_models():
    from workflow.common.model_download_records import track_model_download
    current_lock_path = VACE_WORKSPACE_ROOT/'.model/wan22-vace/.prepare.lock'
    current_lock_path.parent.mkdir(parents=True, exist_ok=True)
    with current_lock_path.open('a') as current_lock_stream:
        fcntl.flock(current_lock_stream, fcntl.LOCK_EX)
        with track_model_download('wan22-vace') as current_shared_record:
            return execute_vace_preparation(current_shared_record)


def execute_vace_preparation(current_shared_record):
    current_record_root = VACE_WORKSPACE_ROOT / '.tmp/test/wan22-vace-prepare' / datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S')
    current_record_root.mkdir(parents=True)
    current_stop_event = threading.Event()
    current_progress_record = {'stage': 'start', 'bytes': 0}
    current_log_lock = threading.Lock()
    def write_prepare_trace(current_stage_name, current_message_text):
        current_log_line = f'{datetime.now().isoformat()}/wan22-vace/{current_stage_name} {current_message_text}'
        with current_log_lock:
            print(current_log_line, flush=True)
            with (current_record_root / 'execution.log').open('a') as current_log_stream:
                current_log_stream.write(current_log_line + '\n')
    def emit_prepare_heartbeat():
        while not current_stop_event.wait(5):
            write_prepare_trace('heartbeat', str(current_progress_record))
    current_heartbeat_thread = threading.Thread(target=emit_prepare_heartbeat, daemon=True)
    current_heartbeat_thread.start()
    try:
        write_prepare_trace('start', f'model_id={VACE_MODEL_IDENTIFIER} model_root=.model/wan22-vace binary={sys.executable}')
        required_download_bytes = sum(VACE_MODEL_FILES[current_model_key][1] for current_model_key in ('high', 'low', 'encoder', 'tokenizer', 'vae') if not vace_model_path(current_model_key, root=VACE_WORKSPACE_ROOT, files=VACE_MODEL_FILES).exists()) + 1_000_000_000
        if shutil.disk_usage(VACE_WORKSPACE_ROOT).free < required_download_bytes:
            raise RuntimeError(f'모델 준비 여유 공간 부족: {required_download_bytes}바이트 필요')
        for current_model_key in ('high', 'low', 'encoder', 'tokenizer'):
            current_model_name, expected_model_size, expected_model_hash = VACE_MODEL_FILES[current_model_key]
            current_model_path = vace_model_path(current_model_key, root=VACE_WORKSPACE_ROOT, files=VACE_MODEL_FILES)
            current_model_path.parent.mkdir(parents=True, exist_ok=True)
            current_partial_path = current_model_path.with_suffix('.partial')
            current_remote_name = (VACE_WORKSPACE_ROOT / current_model_name).relative_to(VACE_WORKSPACE_ROOT / ('.model/wan22-vace-official' if current_model_key in ('high', 'low') else '.model/wan22-vace')).as_posix()
            current_remote_url = f'https://huggingface.co/{VACE_MODEL_IDENTIFIER}/resolve/{VACE_MODEL_REVISION}/{current_remote_name}'
            if current_model_key in VACE_ENCODER_REMOTE_FILES:
                current_remote_url = f'https://huggingface.co/{VACE_ENCODER_IDENTIFIER}/resolve/{VACE_ENCODER_REVISION}/{VACE_ENCODER_REMOTE_FILES[current_model_key]}'
            from workflow.common.model_http_download import download_verified_http
            current_progress_record.update(stage=f'download-{current_model_key}', bytes=0, total_bytes=expected_model_size)
            current_shared_record.update(**current_progress_record)
            download_verified_http(current_remote_url, current_model_path, expected_model_hash, 'wan22-vace/'+current_model_key,
                                   current_partial_path=current_partial_path, expected_total_bytes=expected_model_size)
            if current_model_path.stat().st_size != expected_model_size:
                raise ValueError(f'모델 크기 불일치: {current_model_path}')
            current_progress_record.update(stage=f'verified-{current_model_key}', bytes=expected_model_size, total_bytes=expected_model_size)
            current_shared_record.update(**current_progress_record)
            write_prepare_trace('verified', str(current_model_path))
        from generators.wan_fun.prepare import FUN_SHARED_MODEL_SOURCES
        current_repository_name, current_revision_value, current_remote_name, current_expected_hash = FUN_SHARED_MODEL_SOURCES['vae']
        current_vae_path = vace_model_path('vae', root=VACE_WORKSPACE_ROOT, files=VACE_MODEL_FILES)
        prepare_shared_vae(current_vae_path, VACE_MODEL_FILES['vae'][1], current_expected_hash,
                           current_repository_name, current_revision_value, current_remote_name)
        from generators.wan_vace.official_prepare import prepare_official_runtime
        current_progress_record.update(stage='official-runtime', bytes=0, total_bytes=None)
        current_shared_record.update(**current_progress_record)
        prepare_official_runtime()
        validate_vace_assets()
        current_progress_record.update(stage='준비 완료', bytes=0, total_bytes=None)
        current_shared_record.update(**current_progress_record)
        (current_record_root / 'result.json').write_text(json.dumps({'status': 'completed', 'model_id': VACE_MODEL_IDENTIFIER, 'revision': VACE_MODEL_REVISION, 'files': vace_model_records(root=VACE_WORKSPACE_ROOT, files=VACE_MODEL_FILES)}, ensure_ascii=False))
        write_prepare_trace('completed', str(current_record_root))
    except BaseException:
        write_prepare_trace('failed', traceback.format_exc())
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join()


if __name__ == '__main__':
    prepare_vace_models()
