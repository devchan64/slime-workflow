from pathlib import Path
import sys,os,json,threading,time,datetime
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
WORKFLOW_SOURCE_ROOT=EXPERIMENT_OUTPUT_ROOT.parents[2]
sys.path.insert(0,str(WORKFLOW_SOURCE_ROOT/'.local/anny-runtime'))
os.environ['ANNY_CACHE_DIR']=str(WORKFLOW_SOURCE_ROOT/'.model/anny')
def emit_progress_trace():
 while True:
  print(f'{datetime.datetime.now().isoformat()}/anny/heartbeat 모델 준비·검사 진행',flush=True)
  time.sleep(5)
threading.Thread(target=emit_progress_trace,daemon=True).start()
import torch,anny
if not torch.cuda.is_available(): raise RuntimeError('CUDA 사용 불가')
print('model_id=anny==0.6.0 model_root='+os.environ['ANNY_CACHE_DIR'],flush=True)
model_source_value=anny.Anny(rig='anny',topology='anny',local_changes='default',skinning_method='lbs').to(device='cuda',dtype=torch.float32)
model_output_value=model_source_value(phenotype_kwargs={'age':0.3,'gender':0.5,'height':0.5,'weight':0.5,'muscle':0.3})
print('phenotypes',model_source_value.phenotype_labels)
print('local',model_source_value.local_change_labels)
print('bones',model_source_value.bone_labels)
print('parents',model_source_value.bone_parents)
print('output',{key:tuple(value.shape) for key,value in model_output_value.items() if hasattr(value,'shape')})
print('weights',model_source_value.vertex_bone_weights.shape,model_source_value.vertex_bone_indices.shape)
print('bounds',model_output_value['vertices'].amin(1),model_output_value['vertices'].amax(1))
