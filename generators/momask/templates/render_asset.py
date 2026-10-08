from pathlib import Path
from skin_surface import apply_surface_correction
import bpy,numpy as np,json,time,threading
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
CAMERA_HORIZONTAL_OFFSET = 26 ** 0.5
DIRECTION_CAMERA_POINTS={'down_left':(CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'down_right':(-CAMERA_HORIZONTAL_OFFSET,-CAMERA_HORIZONTAL_OFFSET,3),'up_left':(CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3),'up_right':(-CAMERA_HORIZONTAL_OFFSET,CAMERA_HORIZONTAL_OFFSET,3)}
OUTPUT_SAMPLE_FRAMES=[1,4,7,10,13,16,19,22]
POSE_BONE_NAMES=['head','neck01','upperarm01.R','lowerarm01.R','wrist.R','upperarm01.L','lowerarm01.L','wrist.L','upperleg01.R','lowerleg01.R','foot.R','upperleg01.L','lowerleg01.L','foot.L']
CONDITION_RENDER_SIZE=512
CONDITION_RENDER_FORMAT_VERSION=1
CONDITION_PART_DEFINITIONS=(
 ('background',(0,0,0,0)),('head',(1,0,0,1)),('torso',(2,0,0,1)),
 ('upperarm_left',(3,0,0,1)),('lowerarm_left',(4,0,0,1)),('hand_left',(5,0,0,1)),
 ('upperarm_right',(6,0,0,1)),('lowerarm_right',(7,0,0,1)),('hand_right',(8,0,0,1)),
 ('upperleg_left',(9,0,0,1)),('lowerleg_left',(10,0,0,1)),('foot_left',(11,0,0,1)),
 ('upperleg_right',(12,0,0,1)),('lowerleg_right',(13,0,0,1)),('foot_right',(14,0,0,1)),
)
CURRENT_PROGRESS_STATE={'stage':'prepare'}

def configure_condition_compositor(scene_value):
 scene_value.use_nodes=True
 scene_value.view_layers[0].use_pass_z=True;scene_value.view_layers[0].use_pass_normal=True;scene_value.view_layers[0].use_pass_material_index=True
 compositor_tree_value=scene_value.node_tree;compositor_tree_value.nodes.clear()
 render_layer_node_value=compositor_tree_value.nodes.new('CompositorNodeRLayers')
 depth_output_node_value=compositor_tree_value.nodes.new('CompositorNodeOutputFile')
 normal_output_node_value=compositor_tree_value.nodes.new('CompositorNodeOutputFile')
 part_output_node_value=compositor_tree_value.nodes.new('CompositorNodeOutputFile')
 for output_node_value in (depth_output_node_value,normal_output_node_value,part_output_node_value):
  output_node_value.format.file_format='OPEN_EXR';output_node_value.format.color_depth='16';output_node_value.format.color_mode='RGBA'
 compositor_tree_value.links.new(render_layer_node_value.outputs['Depth'],depth_output_node_value.inputs[0])
 compositor_tree_value.links.new(render_layer_node_value.outputs['Normal'],normal_output_node_value.inputs[0])
 compositor_tree_value.links.new(render_layer_node_value.outputs['IndexMA'],part_output_node_value.inputs[0])
 return depth_output_node_value,normal_output_node_value,part_output_node_value

def finalize_condition_output(condition_output_root, file_prefix_value, output_frame_index):
 generated_output_paths=list(condition_output_root.glob(file_prefix_value+'*'))
 if len(generated_output_paths)!=1:raise RuntimeError(f'조건 패스 출력 개수 오류: {file_prefix_value}={len(generated_output_paths)}')
 resolved_output_path=condition_output_root/f'{file_prefix_value}{output_frame_index:04d}.exr'
 generated_output_paths[0].replace(resolved_output_path)
 return resolved_output_path.name

def resolve_part_category_name(vertex_group_name_value):
 normalized_group_name=vertex_group_name_value.lower().replace('.','_')
 side_name='left' if normalized_group_name.endswith('_l') or 'left' in normalized_group_name else 'right' if normalized_group_name.endswith('_r') or 'right' in normalized_group_name else None
 if 'head' in normalized_group_name:return 'head'
 if any(token_value in normalized_group_name for token_value in ('spine','pelvis','clavicle','neck','hip')):return 'torso'
 for segment_name in ('upperarm','lowerarm','wrist','hand','upperleg','lowerleg','foot','toe'):
  if segment_name in normalized_group_name:
   resolved_segment_name='hand' if segment_name in ('wrist','hand') else 'foot' if segment_name in ('foot','toe') else segment_name
   return f'{resolved_segment_name}_{side_name}' if side_name else 'torso'
 return 'torso'

def create_part_identifier_proxy(body_object_value):
 proxy_mesh_value=body_object_value.data.copy()
 proxy_object_value=bpy.data.objects.new('AnnyConditionPartIdentifier',proxy_mesh_value)
 bpy.context.scene.collection.objects.link(proxy_object_value)
 proxy_object_value.matrix_world=body_object_value.matrix_world.copy()
 copied_group_values={source_group_value.index:proxy_object_value.vertex_groups.new(name=source_group_value.name) for source_group_value in body_object_value.vertex_groups}
 for vertex_value in body_object_value.data.vertices:
  for assignment_value in vertex_value.groups:
   copied_group_values[assignment_value.group].add([vertex_value.index],assignment_value.weight,'REPLACE')
 armature_modifier_value=proxy_object_value.modifiers.new('AnnyConditionArmature','ARMATURE')
 armature_modifier_value.object=next((modifier_value.object for modifier_value in body_object_value.modifiers if modifier_value.type=='ARMATURE'),None)
 if armature_modifier_value.object is None:raise RuntimeError('부위 ID 프록시에 연결할 ANNY Armature가 없습니다.')
 proxy_mesh_value.materials.clear()
 part_index_values={part_name_value:index_value for index_value,(part_name_value,_) in enumerate(CONDITION_PART_DEFINITIONS)}
 for part_name_value,part_color_value in CONDITION_PART_DEFINITIONS:
  material_value=bpy.data.materials.new(f'AnnyCondition_{part_name_value}')
  material_value.use_nodes=True
  material_node_tree=material_value.node_tree;material_node_tree.nodes.clear()
  output_node_value=material_node_tree.nodes.new('ShaderNodeOutputMaterial')
  emission_node_value=material_node_tree.nodes.new('ShaderNodeEmission')
  emission_node_value.inputs['Color'].default_value=tuple(channel_value/255 for channel_value in part_color_value[:3])+(1,)
  emission_node_value.inputs['Strength'].default_value=1
  material_node_tree.links.new(emission_node_value.outputs['Emission'],output_node_value.inputs['Surface'])
  proxy_mesh_value.materials.append(material_value)
 vertex_category_names=[]
 for vertex_value in body_object_value.data.vertices:
  if not vertex_value.groups:
   vertex_category_names.append('torso');continue
  strongest_group_value=max(vertex_value.groups,key=lambda group_value:group_value.weight)
  vertex_category_names.append(resolve_part_category_name(body_object_value.vertex_groups[strongest_group_value.group].name))
 for polygon_value in proxy_mesh_value.polygons:
  category_vote_names=[vertex_category_names[vertex_index_value] for vertex_index_value in polygon_value.vertices]
  resolved_category_name=max(set(category_vote_names),key=category_vote_names.count)
  polygon_value.material_index=part_index_values[resolved_category_name]
 return proxy_object_value,part_index_values

def render_condition_buffers(scene_value, body_object_value, part_proxy_object_value, depth_output_node_value, normal_output_node_value, part_output_node_value, condition_output_root, output_frame_index):
 scene_value.use_nodes=True
 body_object_value.hide_render=False;part_proxy_object_value.hide_render=True
 depth_output_node_value.base_path=str(condition_output_root);normal_output_node_value.base_path=str(condition_output_root)
 part_output_node_value.mute=True
 depth_output_node_value.file_slots[0].path='depth-buffer-';normal_output_node_value.file_slots[0].path='normal-buffer-'
 scene_value.render.filepath=str(condition_output_root/f'rgba-{output_frame_index:04d}.png')
 bpy.ops.render.render(write_still=True)
 depth_file_name=finalize_condition_output(condition_output_root,'depth-buffer-',output_frame_index)
 normal_file_name=finalize_condition_output(condition_output_root,'normal-buffer-',output_frame_index)
 depth_output_node_value.mute=True;normal_output_node_value.mute=True;part_output_node_value.mute=False;part_output_node_value.base_path=str(condition_output_root);part_output_node_value.file_slots[0].path='part-id-buffer-'
 body_object_value.hide_render=True;part_proxy_object_value.hide_render=False
 bpy.ops.render.render()
 part_file_name=finalize_condition_output(condition_output_root,'part-id-buffer-',output_frame_index)
 scene_value.use_nodes=False
 body_object_value.hide_render=False;part_proxy_object_value.hide_render=True
 return {'depth_file':depth_file_name,'normal_file':normal_file_name,'part_file':part_file_name,'depth_range_m':[scene_value.camera.data.clip_start,scene_value.camera.data.clip_end]}
def emit_render_heartbeat():
 while True:
  print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/baseline-r2-momask/heartbeat {CURRENT_PROGRESS_STATE}',flush=True);time.sleep(5)
threading.Thread(target=emit_render_heartbeat,daemon=True).start()
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.blend'))
current_rig_object=bpy.data.objects['AnnyAttributesRig']
current_body_object=bpy.data.objects['AnnyAttributesBody']
(EXPERIMENT_OUTPUT_ROOT/'surface-correction.json').write_text(json.dumps(apply_surface_correction(current_body_object),indent=2))
scene_render_value=bpy.context.scene
scene_render_value.render.engine='CYCLES';scene_render_value.cycles.samples=64
render_device_preferences=bpy.context.preferences.addons['cycles'].preferences
render_device_preferences.compute_device_type='CUDA';render_device_preferences.get_devices()
if not any(current_device_value.type=='CUDA' for current_device_value in render_device_preferences.devices):raise RuntimeError('CUDA 장치 없음')
for current_device_value in render_device_preferences.devices:current_device_value.use=current_device_value.type=='CUDA'
scene_render_value.cycles.device='GPU'
scene_render_value.render.resolution_x=CONDITION_RENDER_SIZE;scene_render_value.render.resolution_y=CONDITION_RENDER_SIZE;scene_render_value.render.resolution_percentage=100
scene_render_value.render.film_transparent=True
for current_object_value in bpy.data.objects:
 if current_object_value.type=='MESH' and current_object_value!=current_body_object:current_object_value.hide_render=True
part_identifier_proxy,part_identifier_palette=create_part_identifier_proxy(current_body_object)
part_identifier_proxy.hide_render=True
depth_output_node,normal_output_node,part_output_node=configure_condition_compositor(scene_render_value)
scene_render_value.camera.data.ortho_scale=2.

# 카메라 기준 주광·약한 보조광으로 모든 방향에서 읽기 쉬운 음영을 유지한다.
scene_render_value.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.035
scene_render_value.view_settings.view_transform='AgX'
scene_render_value.view_settings.look='AgX - High Contrast'
scene_render_value.cycles.use_denoising=True
for existing_light_object in list(bpy.data.objects):
 if existing_light_object.type=='LIGHT':bpy.data.objects.remove(existing_light_object,do_unlink=True)
LIGHTING_PROFILE_VALUES=[('PoseKey',(-3.,-3.5,3.8),500,0.75),('PoseFill',(3.,-2.,1.6),35,2.5),('PoseRim',(1.5,2.5,3.),160,1.5)]
created_light_objects=[]
for light_profile_name,light_offset_values,light_energy_value,light_size_value in LIGHTING_PROFILE_VALUES:
 bpy.ops.object.light_add(type='AREA')
 current_light_object=bpy.context.object;current_light_object.name=light_profile_name
 current_light_object.data.energy=light_energy_value;current_light_object.data.size=light_size_value
 created_light_objects.append(current_light_object)

direction_frame_records={};condition_frame_records={}
for current_direction_name,current_camera_position in DIRECTION_CAMERA_POINTS.items():
 (EXPERIMENT_OUTPUT_ROOT/current_direction_name).mkdir()
 condition_output_root=EXPERIMENT_OUTPUT_ROOT/current_direction_name/'conditions';condition_output_root.mkdir()
 direction_frame_records[current_direction_name]=[]
 condition_frame_records[current_direction_name]=[]
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
  condition_record_value=render_condition_buffers(scene_render_value,current_body_object,part_identifier_proxy,depth_output_node,normal_output_node,part_output_node,condition_output_root,current_sample_index+1)
  scene_render_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/current_direction_name/f'preview-{current_sample_index+1:04d}.png')
  bpy.ops.render.render(write_still=True)
  condition_frame_records[current_direction_name].append({'sample_index':current_sample_index+1,'source_frame':current_frame_number,'rgba':f'conditions/rgba-{current_sample_index+1:04d}.png','depth':f'conditions/{condition_record_value.pop("depth_file")}','normal':f'conditions/{condition_record_value.pop("normal_file")}','part_id':f'conditions/{condition_record_value.pop("part_file")}',**condition_record_value})
(EXPERIMENT_OUTPUT_ROOT/'openpose-keypoints.json').write_text(json.dumps({'format':'COCO18-compatible 14 projected rig points; head center substitutes nose; eyes/ears omitted','source':'MoMask motion retargeted to ANNY','source_frames':OUTPUT_SAMPLE_FRAMES,'frames':direction_frame_records},indent=2))
(EXPERIMENT_OUTPUT_ROOT/'condition-buffers.json').write_text(json.dumps({'schema_version':CONDITION_RENDER_FORMAT_VERSION,'source':'MoMask motion retargeted to ANNY','resolution':[CONDITION_RENDER_SIZE,CONDITION_RENDER_SIZE],'coordinate_space':'same camera projection as preview PNG','depth':'16-bit OpenEXR camera-space Z; clip range in depth_range_m','normal':'16-bit OpenEXR camera-space normal','part_id':{'encoding':'16-bit OpenEXR Material Index','palette':part_identifier_palette},'skeleton':'openpose-keypoints.json; same pixel coordinate space','frames':condition_frame_records},ensure_ascii=False,indent=2))
# 시작·끝 표면 차이 측정: 일반 모션의 닫힌 루프를 가정하지 않는다.
endpoint_vertex_arrays=[]
for current_frame_number in [scene_render_value.frame_start,scene_render_value.frame_end]:
 scene_render_value.frame_set(current_frame_number);bpy.context.view_layer.update()
 current_evaluated_body=current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
 endpoint_vertex_arrays.append(np.array([(current_evaluated_body.matrix_world@current_vertex_value.co)[:] for current_vertex_value in current_evaluated_body.data.vertices]))
endpoint_max_error=float(np.abs(endpoint_vertex_arrays[0]-endpoint_vertex_arrays[1]).max())
print(f'시작·끝 표면 차이 {endpoint_max_error}; 루프 여부는 별도 검수')
(EXPERIMENT_OUTPUT_ROOT/'loop-validation.json').write_text(json.dumps({'status':'measured_review_required','endpoint_max_error_m':endpoint_max_error,'frames_per_direction':len(OUTPUT_SAMPLE_FRAMES),'directions':len(DIRECTION_CAMERA_POINTS),'total_pose_frames':len(OUTPUT_SAMPLE_FRAMES)*len(DIRECTION_CAMERA_POINTS)},indent=2))
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/baseline-r2-momask/complete',flush=True)

motion_bone_names=['root','upperleg01.L','upperleg01.R','spine05','lowerleg01.L','lowerleg01.R','spine03','foot.L','foot.R','spine01','toe3-1.L','toe3-1.R','neck01','clavicle.L','clavicle.R','head','upperarm01.L','upperarm01.R','lowerarm01.L','lowerarm01.R','wrist.L','wrist.R']
target_joint_frames=[]
for current_frame_number in range(scene_render_value.frame_start,scene_render_value.frame_end+1):
 scene_render_value.frame_set(current_frame_number);bpy.context.view_layer.update()
 target_joint_frames.append([(current_rig_object.matrix_world@current_rig_object.pose.bones[current_bone_name].head)[:] for current_bone_name in motion_bone_names])
target_joint_frames=np.array(target_joint_frames)[:,:,[0,2,1]];target_joint_frames[:,:,2]*=-1
target_rest_points=np.array([current_rig_object.data.bones[current_bone_name].head_local[:] for current_bone_name in motion_bone_names])[:,[0,2,1]];target_rest_points[:,2]*=-1
source_loop_bundle=np.load(EXPERIMENT_OUTPUT_ROOT/'inputs/mannequin-motion.npz')
np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'mannequin-motion.npz',joints=target_joint_frames,rest=target_rest_points,contacts=source_loop_bundle['contacts'],sample_indices=np.array(OUTPUT_SAMPLE_FRAMES)-1)
