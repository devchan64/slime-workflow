"""고정 TI2V Q4 모델을 원자적으로 다운로드하고 SHA-256을 검증한다."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import threading
import traceback
import urllib.request
from zoneinfo import ZoneInfo

TI2V_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TI2V_WORKSPACE_ROOT))
from generators.wan_ti2v.contracts import TI2V_DOWNLOAD_RECORDS, TI2V_MODEL_FILES, TI2V_MODEL_IDENTIFIER, TI2V_MODEL_REVISION, TI2V_MODEL_SIZES, validate_ti2v_assets

TI2V_DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024


def prepare_ti2v_models():
    current_started_time = datetime.now(ZoneInfo('Asia/Seoul'))
    current_record_root = TI2V_WORKSPACE_ROOT / '.tmp/test/wan22-ti2v-prepare' / current_started_time.strftime('%Y-%m-%d_%H-%M-%S')
    current_record_root.mkdir(parents=True, exist_ok=False)
    current_log_path = current_record_root / 'execution.log'
    current_progress_record = {'stage': 'prepare', 'bytes': 0, 'file': '', 'status': 'running'}
    current_stop_event = threading.Event()

    def write_prepare_trace(current_stage_name, current_message_text):
        current_log_line = f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/ti2v-prepare/{current_stage_name} {current_message_text}'
        with current_log_path.open('a') as current_log_handle:
            current_log_handle.write(current_log_line + '\n')
        print(current_log_line, flush=True)

    def emit_prepare_heartbeat():
        while not current_stop_event.wait(5):
            write_prepare_trace('heartbeat', json.dumps(current_progress_record, ensure_ascii=False))

    current_heartbeat_thread = threading.Thread(target=emit_prepare_heartbeat, daemon=True)
    current_heartbeat_thread.start()
    try:
        write_prepare_trace('start', f'model_id={TI2V_MODEL_IDENTIFIER} revision={TI2V_MODEL_REVISION} model_root={TI2V_WORKSPACE_ROOT / ".model/wan22-ti2v"} binary={sys.executable} output={current_record_root}')
        for current_model_name, (current_remote_name, current_expected_hash) in TI2V_DOWNLOAD_RECORDS.items():
            current_model_path = TI2V_WORKSPACE_ROOT / TI2V_MODEL_FILES[current_model_name]
            current_model_path.parent.mkdir(parents=True, exist_ok=True)
            current_progress_record.update(file=str(current_model_path), bytes=0, stage='download')
            if not current_model_path.exists():
                current_download_path = current_model_path.with_suffix(current_model_path.suffix + '.partial')
                current_download_url = f'https://huggingface.co/{TI2V_MODEL_IDENTIFIER}/resolve/{TI2V_MODEL_REVISION}/{current_remote_name}'
                with urllib.request.urlopen(current_download_url, timeout=60) as current_download_stream, current_download_path.open('wb') as current_output_stream:
                    while current_chunk_bytes := current_download_stream.read(TI2V_DOWNLOAD_CHUNK_BYTES):
                        current_output_stream.write(current_chunk_bytes)
                        current_progress_record['bytes'] += len(current_chunk_bytes)
            else:
                current_download_path = current_model_path
            current_progress_record['stage'] = 'verify'
            if current_download_path.stat().st_size != TI2V_MODEL_SIZES[current_model_name]:
                raise ValueError(f'모델 크기 불일치: {current_download_path}')
            with current_download_path.open('rb') as current_model_stream:
                current_actual_hash = hashlib.file_digest(current_model_stream, 'sha256').hexdigest()
            if current_actual_hash != current_expected_hash:
                raise ValueError(f'모델 SHA-256 불일치: {current_download_path}')
            if current_download_path != current_model_path:
                current_download_path.replace(current_model_path)
            write_prepare_trace('verified', f'model_path={current_model_path} sha256={current_actual_hash}')
        validate_ti2v_assets()
        current_progress_record['status'] = 'completed'
        write_prepare_trace('complete', '모델·공유 인코더·고정 런타임 준비 완료')
    except BaseException:
        current_progress_record['status'] = 'failed'
        write_prepare_trace('failed', traceback.format_exc())
        print('\n'.join(current_log_path.read_text().splitlines()[-20:]), flush=True)
        raise
    finally:
        current_stop_event.set()
        current_heartbeat_thread.join(timeout=6)
        (current_record_root / 'result.json').write_text(json.dumps(current_progress_record, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    prepare_ti2v_models()
