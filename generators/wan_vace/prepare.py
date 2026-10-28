"""고정 Q4 확산 모델과 BF16 텍스트 인코더를 다운로드하고 SHA-256으로 검증한다. GPU 추론은 실행하지 않는다."""
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import os
import shutil
import sys
import threading
import traceback
import urllib.request
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES, VACE_MODEL_IDENTIFIER, VACE_MODEL_REVISION, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION, VACE_ENCODER_REMOTE_FILES, validate_vace_assets


def prepare_vace_models():
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
        required_download_bytes = sum(VACE_MODEL_FILES[current_model_key][1] for current_model_key in ('high', 'low', 'encoder', 'tokenizer') if not (VACE_WORKSPACE_ROOT / VACE_MODEL_FILES[current_model_key][0]).exists()) + 1_000_000_000
        if shutil.disk_usage(VACE_WORKSPACE_ROOT).free < required_download_bytes:
            raise RuntimeError(f'모델 준비 여유 공간 부족: {required_download_bytes}바이트 필요')
        for current_model_key in ('high', 'low', 'encoder', 'tokenizer'):
            current_model_name, expected_model_size, expected_model_hash = VACE_MODEL_FILES[current_model_key]
            current_model_path = VACE_WORKSPACE_ROOT / current_model_name
            current_model_path.parent.mkdir(parents=True, exist_ok=True)
            current_partial_path = current_model_path.with_suffix('.partial')
            if not current_model_path.exists():
                current_remote_name = current_model_path.relative_to(VACE_WORKSPACE_ROOT / '.model/wan22-vace').as_posix()
                current_remote_url = f'https://huggingface.co/{VACE_MODEL_IDENTIFIER}/resolve/{VACE_MODEL_REVISION}/{current_remote_name}'
                if current_model_key in VACE_ENCODER_REMOTE_FILES:
                    current_remote_url = f'https://huggingface.co/{VACE_ENCODER_IDENTIFIER}/resolve/{VACE_ENCODER_REVISION}/{VACE_ENCODER_REMOTE_FILES[current_model_key]}'
                current_progress_record.update(stage=f'download-{current_model_key}', bytes=0)
                with urllib.request.urlopen(current_remote_url, timeout=120) as current_download_stream, current_partial_path.open('wb') as current_output_stream:
                    while current_download_chunk := current_download_stream.read(8 * 1024 * 1024):
                        current_output_stream.write(current_download_chunk)
                        current_progress_record['bytes'] += len(current_download_chunk)
                current_check_path = current_partial_path
            else:
                current_check_path = current_model_path
            current_progress_record['stage'] = f'verify-{current_model_key}'
            with current_check_path.open('rb') as current_model_stream:
                current_model_digest = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
            if current_check_path.stat().st_size != expected_model_size or current_model_digest != expected_model_hash:
                raise ValueError(f'모델 크기·해시 불일치: {current_check_path}')
            if current_check_path == current_partial_path:
                os.replace(current_partial_path, current_model_path)
            write_prepare_trace('verified', str(current_model_path))
        validate_vace_assets()
        (current_record_root / 'result.json').write_text(json.dumps({'status': 'completed', 'model_id': VACE_MODEL_IDENTIFIER, 'revision': VACE_MODEL_REVISION, 'files': VACE_MODEL_FILES}, ensure_ascii=False))
        write_prepare_trace('completed', str(current_record_root))
    except BaseException:
        write_prepare_trace('failed', traceback.format_exc())
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join()


if __name__ == '__main__':
    prepare_vace_models()
