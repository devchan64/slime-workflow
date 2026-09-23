from pathlib import Path
import bpy, numpy as np, json, hashlib, time, threading
from mathutils import Vector, Matrix
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
CURRENT_PROGRESS_STATE={'stage':'start','frame':0}
RENDER_SAMPLE_FRAMES=list(range(1,97,2))
def emit_progress_heartbeat():
 while True:
  print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/heartbeat {CURRENT_PROGRESS_STATE}',flush=True);time.sleep(5)
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/start output={EXPERIMENT_OUTPUT_ROOT} inputs={EXPERIMENT_OUTPUT_ROOT / "inputs"}',flush=True)
source_motion_path=EXPERIMENT_OUTPUT_ROOT/'inputs/mannequin-motion.npz'
source_manifest_record=json.loads((EXPERIMENT_OUTPUT_ROOT/'inputs/artifact.json').read_text())
assert hashlib.sha256(source_motion_path.read_bytes()).hexdigest()==source_manifest_record['files']['mannequin-motion.npz']
source_motion_bundle=np.load(source_motion_path,allow_pickle=False)
assert set(source_motion_bundle.files)=={'joints','rest','contacts','sample_indices'}
source_joint_frames=source_motion_bundle['joints']
assert source_joint_frames.shape==(25,22,3) and np.isfinite(source_joint_frames).all()
source_joint_frames=source_joint_frames[:,:,[0,2,1]].copy();source_joint_frames[:,:,1]*=-1
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'inputs/anny-reference-fit-rig.blend'))
rig_object_value=bpy.data.objects['AnnyAttributesRig'];body_object_value=bpy.data.objects['AnnyAttributesBody']
rig_object_value.animation_data_clear();rig_object_value.location=(0,0,0)
for current_pose_bone in rig_object_value.pose.bones:
 current_pose_bone.matrix_basis=Matrix.Identity(4);current_pose_bone.rotation_mode='QUATERNION'
scene_render_value=bpy.context.scene;scene_render_value.frame_start=1;scene_render_value.frame_end=25;scene_render_value.render.fps=20
rest_bone_positions={current_bone_value.name:current_bone_value.head_local.copy() for current_bone_value in rig_object_value.data.bones}
rest_bone_rotations={current_bone_value.name:current_bone_value.matrix_local.to_quaternion() for current_bone_value in rig_object_value.data.bones}
segment_mapping_values={}
for current_side_label,current_joint_ids in [('L',[1,4,7,10,16,18,20]),('R',[2,5,8,11,17,19,21])]:
 current_hip_index,current_knee_index,current_ankle_index,current_toe_index,current_shoulder_index,current_elbow_index,current_wrist_index=current_joint_ids
 for current_prefix_name,current_start_name,current_end_name,current_source_start,current_source_end in [
 ('upperleg','upperleg01','lowerleg01',current_hip_index,current_knee_index),('lowerleg','lowerleg01','foot',current_knee_index,current_ankle_index),('upperarm','upperarm01','lowerarm01',current_shoulder_index,current_elbow_index),('lowerarm','lowerarm01','wrist',current_elbow_index,current_wrist_index),('foot','foot','toe3-1',current_ankle_index,current_toe_index)]:
  for current_bone_name in rest_bone_positions:
   if current_bone_name.startswith(current_prefix_name) and current_bone_name.endswith('.'+current_side_label):segment_mapping_values[current_bone_name]=(current_start_name+'.'+current_side_label,current_end_name+'.'+current_side_label,current_source_start,current_source_end)
def calculate_body_rotation(current_joint_points,current_upper_index):
 body_lateral_axis=Vector(current_joint_points[2]-current_joint_points[1])*-1
 if current_upper_index==9:body_lateral_axis=Vector(current_joint_points[16]-current_joint_points[17])
 body_vertical_axis=Vector(current_joint_points[current_upper_index]-current_joint_points[0]).normalized()
 body_lateral_axis=(body_lateral_axis-body_vertical_axis*body_lateral_axis.dot(body_vertical_axis)).normalized()
 body_depth_axis=body_vertical_axis.cross(body_lateral_axis).normalized()
 return Matrix((body_lateral_axis,body_depth_axis,body_vertical_axis)).transposed().to_quaternion()
def collect_surface_vertices():
 current_evaluated_body=body_object_value.evaluated_get(bpy.context.evaluated_depsgraph_get())
 current_vertex_values=np.empty(len(current_evaluated_body.data.vertices)*3)
 current_evaluated_body.data.vertices.foreach_get('co',current_vertex_values)
 current_world_matrix=np.array(current_evaluated_body.matrix_world)
 return current_vertex_values.reshape(-1,3)@current_world_matrix[:3,:3].T+current_world_matrix[:3,3]
source_leg_length=float(np.linalg.norm(source_joint_frames[:,1]-source_joint_frames[:,4],axis=1).mean()+np.linalg.norm(source_joint_frames[:,4]-source_joint_frames[:,7],axis=1).mean())
target_leg_length=(rest_bone_positions['upperleg01.L']-rest_bone_positions['lowerleg01.L']).length+(rest_bone_positions['lowerleg01.L']-rest_bone_positions['foot.L']).length
motion_scale_value=target_leg_length/source_leg_length
foot_track_frames=[];ground_shift_values=[];surface_frame_values=[]
CURRENT_PROGRESS_STATE['stage']='retarget'
for current_frame_index,current_joint_points in enumerate(source_joint_frames):
 current_frame_number=current_frame_index+1;CURRENT_PROGRESS_STATE['frame']=current_frame_number;scene_render_value.frame_set(current_frame_number)
 for current_pose_bone in rig_object_value.pose.bones:current_pose_bone.matrix_basis=Matrix.Identity(4)
 rig_object_value.location=Vector((current_joint_points[0]-source_joint_frames[0,0])*motion_scale_value)
 bpy.context.view_layer.update()
 pelvis_rotation_value=calculate_body_rotation(current_joint_points,3)
 torso_rotation_value=calculate_body_rotation(current_joint_points,9)
 for current_pose_bone in rig_object_value.pose.bones:
  current_bone_name=current_pose_bone.name;target_rotation_value=None
  if current_bone_name=='root':target_rotation_value=pelvis_rotation_value@rest_bone_rotations[current_bone_name]
  elif current_bone_name.startswith('spine'):target_rotation_value=torso_rotation_value@rest_bone_rotations[current_bone_name]
  elif current_bone_name in segment_mapping_values:
   current_start_name,current_end_name,current_source_start,current_source_end=segment_mapping_values[current_bone_name]
   target_rest_vector=rest_bone_positions[current_end_name]-rest_bone_positions[current_start_name]
   current_motion_vector=Vector(current_joint_points[current_source_end]-current_joint_points[current_source_start])
   target_rotation_value=target_rest_vector.rotation_difference(current_motion_vector)@rest_bone_rotations[current_bone_name]
  if target_rotation_value is not None:
   current_pose_bone.matrix=Matrix.Translation(current_pose_bone.head)@target_rotation_value.to_matrix().to_4x4()
   current_pose_bone.location=(0,0,0);current_pose_bone.scale=(1,1,1)
   bpy.context.view_layer.update()
  current_pose_bone.keyframe_insert('rotation_quaternion',frame=current_frame_number)
 current_surface_points=collect_surface_vertices();assert np.isfinite(current_surface_points).all()
 current_ground_shift=-float(current_surface_points[:,2].min());ground_shift_values.append(current_ground_shift)
 rig_object_value.location.z+=current_ground_shift;rig_object_value.keyframe_insert('location',frame=current_frame_number)
 bpy.context.view_layer.update()
 surface_frame_values.append(collect_surface_vertices())
 foot_track_frames.append([list(rig_object_value.matrix_world@rig_object_value.pose.bones[current_foot_name].head) for current_foot_name in ['foot.L','foot.R','toe3-1.L','toe3-1.R']])
rig_object_value.animation_data.action.name='MoMaskLoop25_20fps'
scene_render_value.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');body_object_value.select_set(True);rig_object_value.select_set(True);bpy.context.view_layer.objects.active=rig_object_value
bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.glb'),use_selection=True,export_animations=True,export_all_influences=True)
np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'retarget-diagnostics.npz',foot_tracks=np.array(foot_track_frames),ground_shifts=np.array(ground_shift_values))
# 접촉 추정은 원본 발끝 높이·속도로 계산하며, IK로 수치를 감추지 않는다.
source_toe_positions=source_joint_frames[:,[10,11]]
source_toe_speeds=np.linalg.norm(np.diff(source_toe_positions[:,:,:2],axis=0),axis=2)*20
source_contact_mask=(source_toe_positions[:-1,:,2]<.06)&(source_toe_speeds<.20)
target_toe_speeds=np.linalg.norm(np.diff(np.array(foot_track_frames)[:,2:,:2],axis=0),axis=2)*20
contact_speed_values=target_toe_speeds[source_contact_mask]
review_result_record={'status':'generated_review_required','source_asset_id':'mannequin-walk','source_version':1,'source_sha256':source_manifest_record['files']['mannequin-motion.npz'],'frames':25,'fps':20,'bones':104,'motion_scale':motion_scale_value,'retarget_method':'HumanML3D 22 관절 방향을 ANNY 분할 본 전역 회전에 대응; 본 길이·가중치 유지','ground_method':'프레임별 최저 표면 높이 보정; 발 고정 IK 없음','contact_samples':int(source_contact_mask.sum()),'contact_toe_speed_mean_mps':float(contact_speed_values.mean()) if len(contact_speed_values) else None,'contact_toe_speed_max_mps':float(contact_speed_values.max()) if len(contact_speed_values) else None,'ground_shift_range_m':[min(ground_shift_values),max(ground_shift_values)],'finite_vertices':bool(np.isfinite(surface_frame_values).all()),'quality_warnings':['관절 위치 기반으로 축 비틀림을 완전히 복원할 수 없음','손가락·얼굴은 기본 자세 유지','원본은 이동 보행이며 반복 루프가 아님','접지 높이 보정은 발 고정 IK를 대체하지 않음']}
(EXPERIMENT_OUTPUT_ROOT/'review-metrics.json').write_text(json.dumps(review_result_record,ensure_ascii=False,indent=2))

bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.blend'))
