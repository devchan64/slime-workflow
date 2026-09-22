from pathlib import Path
import threading,time,traceback,json,sys
from huggingface_hub import snapshot_download
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
MODEL_STORAGE_ROOT=EXPERIMENT_OUTPUT_ROOT.parents[1]/'.model/hunyuan3d-2mv'
MODEL_REPOSITORY_ID='tencent/Hunyuan3D-2mv'
MODEL_REVISION_HASH='3a761b539b29fe4ff64714813aa9560fd66f5de0'
HEARTBEAT_STOP_EVENT=threading.Event()
def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/hunyuan-prepare/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):
  model_file_values=list(MODEL_STORAGE_ROOT.rglob('*')) if MODEL_STORAGE_ROOT.exists() else []
  write_trace_message('heartbeat',f'파일={len(model_file_values)} bytes={sum(model_file_value.stat().st_size for model_file_value in model_file_values if model_file_value.is_file())}')
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:
 write_trace_message('start',f'model_id={MODEL_REPOSITORY_ID} model_root={MODEL_STORAGE_ROOT} binary={sys.executable}')
 model_resolved_path=snapshot_download(MODEL_REPOSITORY_ID,revision=MODEL_REVISION_HASH,local_dir=str(MODEL_STORAGE_ROOT),allow_patterns=['hunyuan3d-dit-v2-mv/config.yaml','hunyuan3d-dit-v2-mv/model.fp16.safetensors','LICENSE','README.md'])
 (EXPERIMENT_OUTPUT_ROOT/'model-prepare.json').write_text(json.dumps({'status':'prepared','model_id':MODEL_REPOSITORY_ID,'revision':MODEL_REVISION_HASH,'model_root':model_resolved_path},indent=2))
 write_trace_message('complete',model_resolved_path)
except Exception:
 write_trace_message('failure',traceback.format_exc());raise
finally:HEARTBEAT_STOP_EVENT.set()
