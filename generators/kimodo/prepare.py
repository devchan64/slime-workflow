"""고정 Kimodo·NF4 자료 다운로드. 실행 로그와 5초 heartbeat를 남긴다."""
import hashlib
import json
import subprocess
import threading
import time
import traceback
from datetime import datetime
from generators.kimodo.contracts import KIMODO_ASSET_CONFIG, KIMODO_MODEL_ROOT, KIMODO_SOURCE_ROOT, KIMODO_WORKSPACE_ROOT
from tools.review.common.generation_records import write_record_atomically


def prepare_kimodo_assets():
    from huggingface_hub import hf_hub_download
    current_log_root = KIMODO_WORKSPACE_ROOT/'.tmp/test/kimodo-prepare'/datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
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
        KIMODO_MODEL_ROOT.mkdir(parents=True,exist_ok=True)
        KIMODO_SOURCE_ROOT.parent.mkdir(parents=True,exist_ok=True)
        if not KIMODO_SOURCE_ROOT.exists():
            subprocess.run(['git','clone','https://github.com/nv-tlabs/kimodo.git',str(KIMODO_SOURCE_ROOT)],check=True)
        subprocess.run(['git','-C',str(KIMODO_SOURCE_ROOT),'checkout','--detach',KIMODO_ASSET_CONFIG['source_revision']],check=True)
        current_revision_text = subprocess.check_output(['git','-C',str(KIMODO_SOURCE_ROOT),'rev-parse','HEAD'],text=True).strip()
        if current_revision_text != KIMODO_ASSET_CONFIG['source_revision']:
            raise ValueError('소스 리비전 불일치')
        (KIMODO_SOURCE_ROOT.parent/'PINNED_REVISION').write_text(current_revision_text)
        current_file_hashes = {}
        for current_asset_record in KIMODO_ASSET_CONFIG['models']:
            for current_file_record in current_asset_record['files']:
                record_prepare_progress(f"download {current_asset_record['repository']} {current_file_record['path']}")
                current_file_path = hf_hub_download(current_asset_record['repository'],current_file_record['path'],revision=current_asset_record['revision'],local_dir=KIMODO_MODEL_ROOT/current_asset_record['role'])
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
