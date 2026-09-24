from pathlib import Path
import sys,os,json,threading,time,datetime,hashlib,shutil,subprocess
import numpy as np
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
WORKFLOW_SOURCE_ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_SOURCE_ROOT/'.local/anny-runtime'))
os.environ['ANNY_CACHE_DIR']=str(WORKFLOW_SOURCE_ROOT/'.model/anny')
def emit_progress_trace():
 while True:
  print(f'{datetime.datetime.now().isoformat()}/anny-attributes/heartbeat 입력 검증·CUDA 생성 진행',flush=True)
  time.sleep(5)
def reject_duplicate_fields(field_pair_values):
 output_field_values={}
 for current_field_name,current_field_value in field_pair_values:
  if current_field_name in output_field_values:raise ValueError(f'중복 필드 {current_field_name}')
  output_field_values[current_field_name]=current_field_value
 return output_field_values
threading.Thread(target=emit_progress_trace,daemon=True).start()
import argparse
argument_parser=argparse.ArgumentParser();argument_parser.add_argument('--attributes',type=Path,required=True);argument_parser.add_argument('--output-dir',type=Path,required=True);argument_parser.add_argument('--mesh-only',action='store_true');argument_parser.add_argument('--rotation-y',type=float,default=0);args=argument_parser.parse_args();EXPERIMENT_OUTPUT_ROOT=args.output_dir.resolve();EXPERIMENT_OUTPUT_ROOT.mkdir(parents=True,exist_ok=False);input_source_path=args.attributes.resolve()
(EXPERIMENT_OUTPUT_ROOT/'view.json').write_text(json.dumps({'rotation_y':args.rotation_y}))
input_attribute_values=json.loads(input_source_path.read_text(),object_pairs_hook=reject_duplicate_fields)
required_field_names={'phenotype_kwargs','local_changes_kwargs','facial_actions','pose_parameterization','pose_parameters'}
if set(input_attribute_values)!=required_field_names:raise ValueError('입력 최상위 필드 불일치')
if input_attribute_values['pose_parameterization']!='local-ref':raise ValueError('지원 pose_parameterization은 local-ref')
import torch,anny
if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
model_source_value=anny.Anny(rig='anny',topology='anny',local_changes='default',facial_actions='all',skinning_method='lbs').to(device='cuda',dtype=torch.float32)
for current_field_name,allowed_label_values,minimum_value,maximum_value in [('phenotype_kwargs',model_source_value.phenotype_labels,0,1),('local_changes_kwargs',model_source_value.local_change_labels,-1,1),('facial_actions',model_source_value.facial_action_labels,0,1)]:
 current_field_values=input_attribute_values[current_field_name]
 if not isinstance(current_field_values,dict) or set(current_field_values)-set(allowed_label_values):raise ValueError(f'알 수 없는 속성 {current_field_name}')
 for current_label_name,current_numeric_value in current_field_values.items():
  if type(current_numeric_value) not in (int,float) or not np.isfinite(current_numeric_value) or not minimum_value<=current_numeric_value<=maximum_value:raise ValueError(f'속성 범위 오류 {current_label_name}')
if set(input_attribute_values['pose_parameters'])!=set(model_source_value.bone_labels):raise ValueError('포즈 본 목록 불일치')
pose_tensor_values={}
for current_bone_name,current_matrix_values in input_attribute_values['pose_parameters'].items():
 current_matrix_array=np.asarray(current_matrix_values,dtype=np.float32)
 if current_matrix_array.shape!=(4,4) or not np.isfinite(current_matrix_array).all():raise ValueError('포즈 행렬 오류')
 if not np.allclose(current_matrix_array[3],[0,0,0,1]) or not np.allclose(current_matrix_array[:3,:3].T@current_matrix_array[:3,:3],np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(current_matrix_array[:3,:3]),1):raise ValueError('포즈 강체 회전 오류')
 pose_tensor_values[current_bone_name]=torch.as_tensor(current_matrix_array,device='cuda').unsqueeze(0)
with torch.no_grad():
 model_output_values=model_source_value(phenotype_kwargs=input_attribute_values['phenotype_kwargs'],local_changes_kwargs=input_attribute_values['local_changes_kwargs'],facial_actions=input_attribute_values['facial_actions'],pose_parameterization='local-ref',pose_parameters=pose_tensor_values)
source_vertex_array=model_output_values['vertices'][0].cpu().numpy()
np.savez(EXPERIMENT_OUTPUT_ROOT/'anny-rest-rig.npz',vertices=source_vertex_array,faces=model_source_value.faces.cpu().numpy(),bone_matrices=model_output_values['bone_poses'][0].cpu().numpy(),bone_parents=np.array(model_source_value.bone_parents),bone_names=np.array(model_source_value.bone_labels),weights=model_source_value.vertex_bone_weights.cpu().numpy(),indices=model_source_value.vertex_bone_indices.cpu().numpy())
resolved_phenotype_values={current_label_name:input_attribute_values['phenotype_kwargs'].get(current_label_name,.5) for current_label_name in model_source_value.phenotype_labels}
result_output_values={'status':'generated','model':'anny==0.6.0','input_sha256':hashlib.sha256(input_source_path.read_bytes()).hexdigest(),'requested_local_changes':input_attribute_values['local_changes_kwargs'],'requested_phenotypes':input_attribute_values['phenotype_kwargs'],'resolved_phenotypes':resolved_phenotype_values,'pose_parameterization':'local-ref','pose_bones':len(pose_tensor_values),'postprocess':'없음; Blender 검수 출력만 전신 높이 1.6m로 균일 정규화','source_height':float(np.ptp(source_vertex_array[:,2])),'head_ratio':float(np.ptp(source_vertex_array[:,2])/(source_vertex_array[:,2].max()-source_vertex_array[5155,2])),'vertices':len(source_vertex_array),'triangles':len(model_source_value.faces),'device':torch.cuda.get_device_name(0)}
(EXPERIMENT_OUTPUT_ROOT/'generation.json').write_text(json.dumps(result_output_values,ensure_ascii=False,indent=2))
print(result_output_values,flush=True)
(EXPERIMENT_OUTPUT_ROOT/'mesh.pending').write_text(json.dumps({'vertices':source_vertex_array.tolist(),'faces':model_source_value.faces.cpu().numpy().tolist()},separators=(',',':')))
(EXPERIMENT_OUTPUT_ROOT/'mesh.pending').replace(EXPERIMENT_OUTPUT_ROOT/'mesh.json')
if args.mesh_only:
 print('웹 프리뷰 메시 생성 완료',flush=True)
 sys.exit(0)
preview_script=WORKFLOW_SOURCE_ROOT/'generators/animation/render_anny_attribute_preview_blender.py';shutil.copy2(preview_script,EXPERIMENT_OUTPUT_ROOT/'render_preview.py');subprocess.run([str(WORKFLOW_SOURCE_ROOT/'.local/blender-runtime/bin/python'),str(EXPERIMENT_OUTPUT_ROOT/'render_preview.py')],cwd=EXPERIMENT_OUTPUT_ROOT,check=True)
