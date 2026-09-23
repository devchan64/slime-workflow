from pathlib import Path
import bpy,numpy as np,json,time,threading
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
DIRECTION_CAMERA_POINTS={'down_left':(4,-6,3),'down_right':(-4,-6,3),'up_left':(4,6,3),'up_right':(-4,6,3)}
OUTPUT_SAMPLE_FRAMES=[1,4,7,10,13,16,19,22]
POSE_BONE_NAMES=['head','neck01','upperarm01.R','lowerarm01.R','wrist.R','upperarm01.L','lowerarm01.L','wrist.L','upperleg01.R','lowerleg01.R','foot.R','upperleg01.L','lowerleg01.L','foot.L']
CURRENT_PROGRESS_STATE={'stage':'prepare'}
def emit_render_heartbeat():
 while True:
  print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/asset-v4/heartbeat {CURRENT_PROGRESS_STATE}',flush=True);time.sleep(5)
threading.Thread(target=emit_render_heartbeat,daemon=True).start()
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.blend'))
current_rig_object=bpy.data.objects['AnnyAttributesRig']
current_body_object=bpy.data.objects['AnnyAttributesBody']
scene_render_value=bpy.context.scene
scene_render_value.render.engine='CYCLES';scene_render_value.cycles.samples=48
render_device_preferences=bpy.context.preferences.addons['cycles'].preferences
render_device_preferences.compute_device_type='CUDA';render_device_preferences.get_devices()
if not any(current_device_value.type=='CUDA' for current_device_value in render_device_preferences.devices):raise RuntimeError('CUDA 장치 없음')
for current_device_value in render_device_preferences.devices:current_device_value.use=current_device_value.type=='CUDA'
scene_render_value.cycles.device='GPU'
scene_render_value.render.resolution_x=512;scene_render_value.render.resolution_y=512;scene_render_value.render.resolution_percentage=100
scene_render_value.render.film_transparent=True
for current_object_value in bpy.data.objects:
 if current_object_value.type=='MESH' and current_object_value!=current_body_object:current_object_value.hide_render=True
scene_render_value.camera.data.ortho_scale=2.

# 카메라 기준 주광·약한 보조광으로 모든 방향에서 읽기 쉬운 음영을 유지한다.
scene_render_value.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.12
scene_render_value.view_settings.view_transform='AgX'
scene_render_value.view_settings.look='AgX - Medium High Contrast'
scene_render_value.cycles.use_denoising=True
for existing_light_object in list(bpy.data.objects):
 if existing_light_object.type=='LIGHT':bpy.data.objects.remove(existing_light_object,do_unlink=True)
LIGHTING_PROFILE_VALUES=[('PoseKey',(-2.5,-3.5,3.8),420,1.2),('PoseFill',(3.,-2.,1.6),65,2.5),('PoseRim',(1.5,2.5,3.),180,1.8)]
created_light_objects=[]
for light_profile_name,light_offset_values,light_energy_value,light_size_value in LIGHTING_PROFILE_VALUES:
 bpy.ops.object.light_add(type='AREA')
 current_light_object=bpy.context.object;current_light_object.name=light_profile_name
 current_light_object.data.energy=light_energy_value;current_light_object.data.size=light_size_value
 created_light_objects.append(current_light_object)

direction_frame_records={}
for current_direction_name,current_camera_position in DIRECTION_CAMERA_POINTS.items():
 (EXPERIMENT_OUTPUT_ROOT/current_direction_name).mkdir()
 direction_frame_records[current_direction_name]=[]
 for current_sample_index,current_frame_number in enumerate(OUTPUT_SAMPLE_FRAMES):
  CURRENT_PROGRESS_STATE.update(direction=current_direction_name,frame=current_frame_number)
  scene_render_value.frame_set(current_frame_number);bpy.context.view_layer.update()
  current_follow_position=current_rig_object.location.copy();current_follow_position.z=0
  current_target_position=current_follow_position+Vector((0,0,.8))
  scene_render_value.camera.location=current_follow_position+Vector(current_camera_position)
  scene_render_value.camera.rotation_euler=(current_target_position-scene_render_value.camera.location).to_track_quat('-Z','Y').to_euler()
  bpy.context.view_layer.update()
  camera_forward_vector=(current_target_position-scene_render_value.camera.location).normalized()
  camera_right_vector=camera_forward_vector.cross(Vector((0,0,1))).normalized()
  camera_front_vector=Vector((-camera_forward_vector.x,-camera_forward_vector.y,0)).normalized()
  for current_light_object,current_light_profile in zip(created_light_objects,LIGHTING_PROFILE_VALUES):
   light_horizontal_offset,light_depth_offset,light_vertical_offset=current_light_profile[1]
   current_light_object.location=current_follow_position+camera_right_vector*light_horizontal_offset-camera_front_vector*light_depth_offset+Vector((0,0,light_vertical_offset))
   current_light_object.rotation_euler=(current_target_position-current_light_object.location).to_track_quat('-Z','Y').to_euler()
  current_keypoint_values=[]
  for current_bone_name in POSE_BONE_NAMES:
   current_pose_bone=current_rig_object.pose.bones[current_bone_name]
   current_joint_position=current_pose_bone.head
   if current_bone_name=='head':current_joint_position=(current_pose_bone.head+current_pose_bone.tail)/2
   current_world_position=current_rig_object.matrix_world@current_joint_position
   current_projected_point=world_to_camera_view(scene_render_value,scene_render_value.camera,current_world_position)
   current_keypoint_values.append([current_projected_point.x*512,(1-current_projected_point.y)*512])
  if not np.isfinite(current_keypoint_values).all() or np.min(current_keypoint_values)<0 or np.max(current_keypoint_values)>512:raise ValueError('투영 범위 오류')
  direction_frame_records[current_direction_name].append(current_keypoint_values)
  scene_render_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'preview-{current_sample_index+1:04d}.png')
  bpy.ops.render.render(write_still=True)
(EXPERIMENT_OUTPUT_ROOT/'openpose-keypoints.json').write_text(json.dumps({'format':'COCO18-compatible 14 projected rig points; head center substitutes nose; eyes/ears omitted','source':'MoMask-derived loop retargeted to ANNY104','source_frames':OUTPUT_SAMPLE_FRAMES,'frames':direction_frame_records},indent=2))
# 닫힌 루프 표면 검증
endpoint_vertex_arrays=[]
for current_frame_number in [1,25]:
 scene_render_value.frame_set(current_frame_number);bpy.context.view_layer.update()
 current_evaluated_body=current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
 endpoint_vertex_arrays.append(np.array([(current_evaluated_body.matrix_world@current_vertex_value.co)[:] for current_vertex_value in current_evaluated_body.data.vertices]))
endpoint_max_error=float(np.abs(endpoint_vertex_arrays[0]-endpoint_vertex_arrays[1]).max())
if endpoint_max_error>1e-5:raise ValueError(f'루프 끝점 불일치 {endpoint_max_error}')
(EXPERIMENT_OUTPUT_ROOT/'loop-validation.json').write_text(json.dumps({'status':'passed','endpoint_max_error_m':endpoint_max_error,'frames_per_direction':8,'directions':4,'total_pose_frames':32},indent=2))
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/asset-v4/complete',flush=True)

motion_bone_names=['root','upperleg01.L','upperleg01.R','spine05','lowerleg01.L','lowerleg01.R','spine03','foot.L','foot.R','spine01','toe3-1.L','toe3-1.R','neck01','clavicle.L','clavicle.R','head','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R']
target_joint_frames=[]
for current_frame_number in range(1,26):
 scene_render_value.frame_set(current_frame_number);bpy.context.view_layer.update()
 target_joint_frames.append([(current_rig_object.matrix_world@current_rig_object.pose.bones[current_bone_name].head)[:] for current_bone_name in motion_bone_names])
target_joint_frames=np.array(target_joint_frames)[:,:,[0,2,1]];target_joint_frames[:,:,2]*=-1
target_rest_points=np.array([current_rig_object.data.bones[current_bone_name].head_local[:] for current_bone_name in motion_bone_names])[:,[0,2,1]];target_rest_points[:,2]*=-1
source_loop_bundle=np.load(EXPERIMENT_OUTPUT_ROOT/'inputs/mannequin-motion.npz')
np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'mannequin-motion.npz',joints=target_joint_frames,rest=target_rest_points,contacts=source_loop_bundle['contacts'],sample_indices=np.arange(8)*3)
