"""고정된 공식 모델을 .model에 준비하고 전체 파일 해시를 기록한다."""
import fcntl
import hashlib
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path
if __name__ == '__main__' and not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tools.review.common.generation_records import write_record_atomically
from generators.wan_animate2.contracts import ANIMATE_MODEL_DIRECTORY, ANIMATE_MODEL_IDENTIFIER, ANIMATE_MODEL_REVISION, ANIMATE_RUNTIME_DIRECTORY, ANIMATE_RUNTIME_REVISION


def prepare_animate_models():
    ANIMATE_MODEL_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with (ANIMATE_MODEL_DIRECTORY/'.prepare.lock').open('a') as current_prepare_lock:
        fcntl.flock(current_prepare_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        download_animate_pinned_assets()


def download_animate_pinned_assets():
    from huggingface_hub import snapshot_download
    current_stop_event=threading.Event()
    def report_prepare_progress():
        while not current_stop_event.wait(5):
            print(f'{datetime.now().isoformat()}/animate2/prepare 다운로드 진행 중 model={ANIMATE_MODEL_IDENTIFIER} root={ANIMATE_MODEL_DIRECTORY}',flush=True)
    threading.Thread(target=report_prepare_progress,daemon=True).start()
    try:
        if not ANIMATE_RUNTIME_DIRECTORY.exists():
            ANIMATE_RUNTIME_DIRECTORY.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['git','clone','https://github.com/huggingface/diffusers.git',str(ANIMATE_RUNTIME_DIRECTORY)],check=True)
            subprocess.run(['git','-C',str(ANIMATE_RUNTIME_DIRECTORY),'checkout',ANIMATE_RUNTIME_REVISION],check=True)
        current_runtime_revision=subprocess.check_output(['git','-C',str(ANIMATE_RUNTIME_DIRECTORY),'rev-parse','HEAD'],text=True).strip()
        if current_runtime_revision!=ANIMATE_RUNTIME_REVISION:
            raise RuntimeError('Diffusers 소스 버전 불일치: 기존 소스를 자동 덮어쓰지 않습니다.')
        snapshot_download(ANIMATE_MODEL_IDENTIFIER,revision=ANIMATE_MODEL_REVISION,local_dir=ANIMATE_MODEL_DIRECTORY,max_workers=2)
        current_file_hashes={}
        for current_model_file in sorted(ANIMATE_MODEL_DIRECTORY.rglob('*')):
            if current_model_file.is_file() and '.cache' not in current_model_file.parts and current_model_file.name not in ('ready.sha256', '.prepare.lock'):
                current_file_digest=hashlib.sha256()
                with current_model_file.open('rb') as current_file_handle:
                    for current_file_chunk in iter(lambda:current_file_handle.read(8*1024*1024),b''):
                        current_file_digest.update(current_file_chunk)
                current_file_hashes[str(current_model_file.relative_to(ANIMATE_MODEL_DIRECTORY))]={'sha256':current_file_digest.hexdigest(),'bytes':current_model_file.stat().st_size}
        write_record_atomically(ANIMATE_MODEL_DIRECTORY/'ready.sha256', {'revision':ANIMATE_MODEL_REVISION,'files':current_file_hashes})
        print(f'{datetime.now().isoformat()}/animate2/ready {ANIMATE_MODEL_DIRECTORY}',flush=True)
    finally:
        current_stop_event.set()

if __name__=='__main__':
    prepare_animate_models()
