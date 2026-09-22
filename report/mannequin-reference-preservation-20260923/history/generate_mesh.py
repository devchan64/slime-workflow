"""참조 이미지에서 CUDA Hunyuan3D 기본 메시를 생성한다."""
from pathlib import Path
import os,sys,time,threading,json,traceback,hashlib
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
WORKFLOW_SOURCE_ROOT=EXPERIMENT_OUTPUT_ROOT.parents[1]
MODEL_STORAGE_ROOT=WORKFLOW_SOURCE_ROOT/'.model/hunyuan3d-2mv'
MODEL_SUBFOLDER_NAME='hunyuan3d-dit-v2-mv'
INPUT_REFERENCE_PATH=EXPERIMENT_OUTPUT_ROOT/'front.png'
OUTPUT_MODEL_PATH=EXPERIMENT_OUTPUT_ROOT/'hunyuan-mannequin-raw.glb'
INFERENCE_RANDOM_SEED=20260923
INFERENCE_SAMPLE_STEPS=75
MESH_OCTREE_RESOLUTION=512
HEARTBEAT_STOP_EVENT=threading.Event()
CURRENT_STAGE_RECORD={'stage':'load','step':0}
os.environ['HF_HOME']=str(WORKFLOW_SOURCE_ROOT/'.model/huggingface')
sys.path.insert(0,str(WORKFLOW_SOURCE_ROOT/'.local/hunyuan3d-source'))
def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/hunyuan-mannequin/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):
  write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))
def record_inference_step(step_index_value,timestep_value,output_tensor_values):
 CURRENT_STAGE_RECORD.update(stage='decode' if int(step_index_value)+1==INFERENCE_SAMPLE_STEPS else 'diffusion',step=int(step_index_value)+1)
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:
 import torch
 import numpy as np
 from PIL import Image
 from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
 if not torch.cuda.is_available():raise RuntimeError('샌드박스 밖 CUDA 사용 불가: CPU 추론 금지')
 prepare_result_record=json.loads((EXPERIMENT_OUTPUT_ROOT/'model-prepare.json').read_text())
 if prepare_result_record['status']!='prepared':raise RuntimeError('모델 준비가 완료되지 않음')
 write_trace_message('start',f'model={MODEL_STORAGE_ROOT} input={INPUT_REFERENCE_PATH} gpu={torch.cuda.get_device_name(0)}')
 generation_pipeline_value=Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(str(MODEL_STORAGE_ROOT),subfolder=MODEL_SUBFOLDER_NAME,variant='fp16',use_safetensors=True,device='cpu',dtype=torch.float16)
 generation_pipeline_value.components={component_name_value:getattr(generation_pipeline_value,component_name_value) for component_name_value in ['conditioner','model','vae']}
 generation_pipeline_value.enable_model_cpu_offload(device='cuda')
 generation_pipeline_value.enable_flashvdm(enabled=True,adaptive_kv_selection=False,mc_algo='mc',replace_vae=False)
 generation_pipeline_value.device=torch.device('cuda')
 write_trace_message('device','가중치만 RAM에 대기; conditioner/model/vae의 추론 실행 장치는 CUDA')
 reference_image_value={view_name_value:Image.open(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}.png').convert('RGBA') for view_name_value in ['front','left','back']}
 CURRENT_STAGE_RECORD.update(stage='inference')
 generated_latent_values=generation_pipeline_value(image=reference_image_value,num_inference_steps=INFERENCE_SAMPLE_STEPS,generator=torch.Generator(device='cuda').manual_seed(INFERENCE_RANDOM_SEED),output_type='latent',callback=record_inference_step,callback_steps=1)
 if tuple(generated_latent_values.shape)!=(1,3072,64) or not torch.isfinite(generated_latent_values).all():raise ValueError('형상 latent 출력 형식 오류')
 torch.save(generated_latent_values.detach().cpu(),EXPERIMENT_OUTPUT_ROOT/'shape-latents.pt')
 CURRENT_STAGE_RECORD.update(stage='mesh-decode')
 write_trace_message('decode','형상 latent 보존 완료; 512 해상도 메시 추출 시작')
 with torch.inference_mode():
  output_mesh_values=generation_pipeline_value._export(generated_latent_values,output_type='trimesh',box_v=1.01,mc_level=0.0,num_chunks=4096,octree_resolution=MESH_OCTREE_RESOLUTION,mc_algo='mc',enable_pbar=True)
 if not isinstance(output_mesh_values,list) or len(output_mesh_values)!=1:raise ValueError('모델 출력 메시 수 불일치')
 generated_mesh_value=output_mesh_values[0]
 if generated_mesh_value is None or not np.isfinite(generated_mesh_value.vertices).all() or len(generated_mesh_value.faces)==0:raise ValueError('유효하지 않은 생성 메시')
 generated_mesh_value.export(OUTPUT_MODEL_PATH)
 generated_mesh_value.export(EXPERIMENT_OUTPUT_ROOT/'hunyuan-mannequin-raw.ply')
 result_record_value={'status':'generated_raw_mesh','model':prepare_result_record,'inputs':json.loads((EXPERIMENT_OUTPUT_ROOT/'input-preparation.json').read_text()),'seed':INFERENCE_RANDOM_SEED,'steps':INFERENCE_SAMPLE_STEPS,'octree_resolution':MESH_OCTREE_RESOLUTION,'vertices':len(generated_mesh_value.vertices),'faces':len(generated_mesh_value.faces),'bounds':generated_mesh_value.bounds.tolist(),'output':str(OUTPUT_MODEL_PATH),'gpu':torch.cuda.get_device_name(0),'rigged':False}
 (EXPERIMENT_OUTPUT_ROOT/'generation.json').write_text(json.dumps(result_record_value,ensure_ascii=False,indent=2))
 write_trace_message('complete',str(result_record_value))
except Exception:
 write_trace_message('failure',traceback.format_exc())
 (EXPERIMENT_OUTPUT_ROOT/'generation.json').write_text(json.dumps({'status':'failed','error':traceback.format_exc()},ensure_ascii=False))
 raise
finally:HEARTBEAT_STOP_EVENT.set()
