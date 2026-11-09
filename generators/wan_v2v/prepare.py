"""고정된 공식 모델을 .model에 준비하고 전체 파일 해시를 기록한다."""
import hashlib
import json
import sys
import subprocess
import threading
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.wan_v2v.contracts import V2V_MODEL_DIRECTORY, V2V_MODEL_IDENTIFIER, V2V_MODEL_REVISION, V2V_RUNTIME_DIRECTORY, V2V_RUNTIME_REVISION, V2V_RUNTIME_DEPENDENCIES


def prepare_v2v_models():
    import importlib.util
    current_missing_dependencies = [current_module_name for current_module_name in V2V_RUNTIME_DEPENDENCIES if importlib.util.find_spec(current_module_name) is None]
    if current_missing_dependencies:
        raise RuntimeError('V2V 의존성 설치 필요 (.venv): '+', '.join(current_missing_dependencies))
    from huggingface_hub import snapshot_download
    current_stop_event=threading.Event()
    def report_prepare_progress():
        while not current_stop_event.wait(5):
            print(f'{datetime.now().isoformat()}/v2v/prepare 다운로드 진행 중 model={V2V_MODEL_IDENTIFIER} root={V2V_MODEL_DIRECTORY}',flush=True)
    threading.Thread(target=report_prepare_progress,daemon=True).start()
    try:
        if not V2V_RUNTIME_DIRECTORY.exists():
            V2V_RUNTIME_DIRECTORY.parent.mkdir(parents=True,exist_ok=True)
            subprocess.run(['git','clone','https://github.com/modelscope/DiffSynth-Studio.git',str(V2V_RUNTIME_DIRECTORY)],check=True)
            subprocess.run(['git','-C',str(V2V_RUNTIME_DIRECTORY),'checkout',V2V_RUNTIME_REVISION],check=True)
        current_runtime_revision=subprocess.check_output(['git','-C',str(V2V_RUNTIME_DIRECTORY),'rev-parse','HEAD'],text=True).strip()
        if current_runtime_revision!=V2V_RUNTIME_REVISION:
            raise RuntimeError('DiffSynth 소스 버전 불일치: 기존 소스를 자동 덮어쓰지 않습니다.')
        snapshot_download(V2V_MODEL_IDENTIFIER,revision=V2V_MODEL_REVISION,local_dir=V2V_MODEL_DIRECTORY,max_workers=2,allow_patterns=['high_noise_model/*','low_noise_model/*','google/umt5-xxl/*','Wan2.1_VAE.pth','models_t5_umt5-xxl-enc-bf16.pth'])
        current_file_hashes={}
        for current_model_file in sorted(V2V_MODEL_DIRECTORY.rglob('*')):
            if current_model_file.is_file() and '.cache' not in current_model_file.parts and current_model_file.name!='ready.sha256':
                current_file_digest=hashlib.sha256()
                with current_model_file.open('rb') as current_file_handle:
                    for current_file_chunk in iter(lambda:current_file_handle.read(8*1024*1024),b''):
                        current_file_digest.update(current_file_chunk)
                current_file_hashes[str(current_model_file.relative_to(V2V_MODEL_DIRECTORY))]={'sha256':current_file_digest.hexdigest(),'bytes':current_model_file.stat().st_size}
        (V2V_MODEL_DIRECTORY/'ready.sha256').write_text(json.dumps({'revision':V2V_MODEL_REVISION,'files':current_file_hashes}))
        print(f'{datetime.now().isoformat()}/v2v/ready {V2V_MODEL_DIRECTORY}',flush=True)
    finally:
        current_stop_event.set()

class PrepareTraceOutput:
    """화면과 준비 로그에 같은 진단을 남긴다."""
    def __init__(self,current_terminal_stream,current_log_stream):
        self.current_terminal_stream=current_terminal_stream
        self.current_log_stream=current_log_stream
    def write(self,current_output_text):
        self.current_terminal_stream.write(current_output_text)
        self.current_log_stream.write(current_output_text)
        self.current_log_stream.flush()
    def flush(self):
        self.current_terminal_stream.flush()
        self.current_log_stream.flush()


if __name__=='__main__':
    current_log_directory=Path(__file__).resolve().parents[2]/'.tmp/wan-v2v-prepare'
    current_log_directory.mkdir(parents=True,exist_ok=True)
    current_log_stream=(current_log_directory/(datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')).open('a')
    sys.stdout=PrepareTraceOutput(sys.stdout,current_log_stream)
    sys.stderr=PrepareTraceOutput(sys.stderr,current_log_stream)
    try:
        prepare_v2v_models()
    except BaseException:
        import traceback
        print(f'{datetime.now().isoformat()}/v2v/failed model_id={V2V_MODEL_IDENTIFIER} model_root={V2V_MODEL_DIRECTORY} runtime={V2V_RUNTIME_DIRECTORY} binary={sys.executable}',flush=True)
        traceback.print_exc()
        raise
