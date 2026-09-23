from pathlib import Path
import sys,os,json,threading,time,datetime
import numpy as np
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
WORKFLOW_SOURCE_ROOT=EXPERIMENT_OUTPUT_ROOT.parents[2]
sys.path.insert(0,str(WORKFLOW_SOURCE_ROOT/'.local/anny-runtime'))
os.environ['ANNY_CACHE_DIR']=str(WORKFLOW_SOURCE_ROOT/'.model/anny')
def emit_progress_trace():
 while True:
  print(f'{datetime.datetime.now().isoformat()}/anny/heartbeat 체형 탐색·리그 추출 진행',flush=True)
  time.sleep(5)
threading.Thread(target=emit_progress_trace,daemon=True).start()
import torch,anny
from anny.face_segmentation import get_face_segmentation_mask
if not torch.cuda.is_available(): raise RuntimeError('CUDA 사용 불가')
model_source_value=anny.Anny(rig='anny',topology='anny',local_changes='default',skinning_method='lbs').to(device='cuda',dtype=torch.float32)
head_face_mask=get_face_segmentation_mask(model_source_value,['head'])
head_vertex_indices=torch.unique(model_source_value.faces[head_face_mask.cpu()])
shape_parameter_values={'gender':0.5,'age':0.12,'muscle':0.25,'weight':0.45,'height':0.5,'proportions':0.5}
def evaluate_body_ratio(current_age_value):
 local_parameter_values={'head-scale-vert-incr':current_age_value,'head-scale-horiz-incr':current_age_value,'head-scale-depth-incr':current_age_value}
 with torch.no_grad():
  current_model_output=model_source_value(phenotype_kwargs=shape_parameter_values,local_changes_kwargs=local_parameter_values)
 current_vertex_array=current_model_output['vertices'][0]
 current_head_array=current_vertex_array[head_vertex_indices]
 current_ratio_value=((current_vertex_array[:,2].max()-current_vertex_array[:,2].min())/(current_vertex_array[:,2].max()-current_vertex_array[5155,2])).item()
 return current_ratio_value,current_model_output
for current_age_value in [0.,0.1,0.2,0.3,0.5,1.]:
 current_ratio_value,_=evaluate_body_ratio(current_age_value)
 print('head_scale',current_age_value,'ratio',current_ratio_value,flush=True)
lower_age_value,upper_age_value=0.,1.
if not evaluate_body_ratio(lower_age_value)[0] > 5 > evaluate_body_ratio(upper_age_value)[0]: raise ValueError('5등신을 끼우는 age 구간이 없음')
for current_step_index in range(24):
 midpoint_age_value=(lower_age_value+upper_age_value)/2
 current_ratio_value,current_model_output=evaluate_body_ratio(midpoint_age_value)
 if current_ratio_value>5: lower_age_value=midpoint_age_value
 else: upper_age_value=midpoint_age_value
final_ratio_value,final_model_output=evaluate_body_ratio((lower_age_value+upper_age_value)/2)
final_vertex_array=final_model_output['vertices'][0].cpu().numpy()
final_bone_matrices=final_model_output['bone_poses'][0].cpu().numpy()
head_index_array=head_vertex_indices.cpu().numpy()
chin_vertex_index=5155
np.savez(EXPERIMENT_OUTPUT_ROOT/'anny-rest-rig.npz',vertices=final_vertex_array,faces=model_source_value.faces.cpu().numpy(),bone_matrices=final_bone_matrices,bone_parents=np.array(model_source_value.bone_parents),bone_names=np.array(model_source_value.bone_labels),weights=model_source_value.vertex_bone_weights.cpu().numpy(),indices=model_source_value.vertex_bone_indices.cpu().numpy(),head_indices=head_index_array)
result_output_record={'status':'generated','anny_version':anny.__version__,'device':torch.cuda.get_device_name(0),'parameters':shape_parameter_values,'head_scale_parameter':(lower_age_value+upper_age_value)/2,'head_ratio':final_ratio_value,'head_measurement':'Crown maximum Z to fixed anterior under-chin vertex 5155; rest-pose vertical measurement','chin_vertex_index':chin_vertex_index,'chin_position':final_vertex_array[chin_vertex_index].tolist(),'height':float(np.ptp(final_vertex_array[:,2])),'vertices':len(final_vertex_array),'triangles':len(model_source_value.faces),'bones':model_source_value.bone_count,'cache':os.environ['ANNY_CACHE_DIR']}
(EXPERIMENT_OUTPUT_ROOT/'generation.json').write_text(json.dumps(result_output_record,ensure_ascii=False,indent=2))
print(result_output_record,flush=True)
