from pathlib import Path
import bpy,numpy as np,math,json,time,threading,datetime
from mathutils import Matrix,Vector
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
TARGET_BODY_HEIGHT=1.6

def emit_progress_trace():
 while True:
  print(f'{datetime.datetime.now().isoformat()}/anny-build/heartbeat 리그 구성·GPU 렌더 진행',flush=True)
  time.sleep(5)
threading.Thread(target=emit_progress_trace,daemon=True).start()
bpy.ops.wm.read_factory_settings(use_empty=True)
source_model_bundle=np.load(EXPERIMENT_OUTPUT_ROOT/'anny-rest-rig.npz',allow_pickle=False)
source_vertex_array=source_model_bundle['vertices'].copy()
source_bone_matrices=source_model_bundle['bone_matrices'].copy()
source_floor_value=float(source_vertex_array[:,2].min())
source_scale_value=TARGET_BODY_HEIGHT/np.ptp(source_vertex_array[:,2])
source_vertex_array[:,2]-=source_floor_value
source_vertex_array*=source_scale_value
source_bone_matrices[:,2,3]-=source_floor_value
source_bone_matrices[:,:3,3]*=source_scale_value
source_bone_names=source_model_bundle['bone_names'].tolist()
source_parent_indices=source_model_bundle['bone_parents']
body_mesh_data=bpy.data.meshes.new('AnnyBodySurface')
body_mesh_data.from_pydata(source_vertex_array.tolist(),[],source_model_bundle['faces'].tolist())
body_mesh_data.update()
body_mesh_object=bpy.data.objects.new('AnnyFiveHeadBody',body_mesh_data)
bpy.context.collection.objects.link(body_mesh_object)
for current_polygon_value in body_mesh_data.polygons: current_polygon_value.use_smooth=True
body_material_value=bpy.data.materials.new('NeutralIvory');body_material_value.diffuse_color=(.62,.57,.47,1);body_material_value.use_nodes=True
body_material_value.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.62,.57,.47,1)
body_material_value.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.6
body_mesh_data.materials.append(body_material_value)
rig_armature_data=bpy.data.armatures.new('AnnyOriginal104Bones')
rig_armature_object=bpy.data.objects.new('AnnyFiveHeadRig',rig_armature_data)
bpy.context.collection.objects.link(rig_armature_object)
bpy.context.view_layer.objects.active=rig_armature_object;rig_armature_object.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for current_bone_index,current_bone_name in enumerate(source_bone_names):
 current_edit_bone=rig_armature_data.edit_bones.new(current_bone_name)
 current_edit_bone.head=source_bone_matrices[current_bone_index,:3,3]
 current_edit_bone.tail=current_edit_bone.head+Vector((0,.05,0))
 current_edit_bone.matrix=Matrix(source_bone_matrices[current_bone_index].tolist())
 current_parent_index=int(source_parent_indices[current_bone_index])
 if current_parent_index>=0: current_edit_bone.parent=rig_armature_data.edit_bones[source_bone_names[current_parent_index]]
 current_child_indices=np.where(source_parent_indices==current_bone_index)[0]
 if len(current_child_indices): current_edit_bone.length=max(.015,float(np.linalg.norm(source_bone_matrices[current_child_indices[0],:3,3]-source_bone_matrices[current_bone_index,:3,3])))
bpy.ops.object.mode_set(mode='OBJECT')
for current_bone_name in source_bone_names: body_mesh_object.vertex_groups.new(name=current_bone_name)
for current_vertex_index,(current_bone_indices,current_bone_weights) in enumerate(zip(source_model_bundle['indices'],source_model_bundle['weights'])):
 for current_bone_index,current_weight_value in zip(current_bone_indices,current_bone_weights):
  if current_weight_value>0: body_mesh_object.vertex_groups[int(current_bone_index)].add([current_vertex_index],float(current_weight_value),'REPLACE')
armature_modifier_value=body_mesh_object.modifiers.new('AnnySkinning','ARMATURE');armature_modifier_value.object=rig_armature_object
body_mesh_object.parent=rig_armature_object
scene_render_value=bpy.context.scene
scene_render_value.frame_start=1;scene_render_value.frame_end=25;scene_render_value.render.fps=24
for current_frame_value in range(1,26):
 current_pose_amount=math.sin(math.pi*(current_frame_value-1)/24)**2
 for current_pose_bone in rig_armature_object.pose.bones:
  current_pose_bone.rotation_mode='QUATERNION';current_pose_bone.rotation_quaternion=(1,0,0,0)
 for current_bone_name,current_axis_name,current_angle_value in [('upperarm01.L','Y',-.85),('upperarm01.R','Y',.85),('lowerarm01.L','Z',-.7),('lowerarm01.R','Z',.7),('upperleg01.L','X',-.6),('lowerleg01.L','X',1.1)]:
  current_pose_bone=rig_armature_object.pose.bones[current_bone_name]
  current_rest_rotation=current_pose_bone.bone.matrix_local.to_3x3()
  current_pose_bone.rotation_quaternion=(current_rest_rotation.inverted()@Matrix.Rotation(current_angle_value*current_pose_amount,3,current_axis_name)@current_rest_rotation).to_quaternion()
 for current_pose_bone in rig_armature_object.pose.bones: current_pose_bone.keyframe_insert('rotation_quaternion',frame=current_frame_value)
rig_armature_object.animation_data.action.name='RigRangeCheck_NotWalk'
scene_render_value.frame_set(1);bpy.context.view_layer.update()
body_evaluated_object=body_mesh_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
rest_evaluated_array=np.array([current_vertex_value.co[:] for current_vertex_value in body_evaluated_object.data.vertices])
rest_error_value=float(np.abs(rest_evaluated_array-source_vertex_array).max())
if rest_error_value>1e-5: raise ValueError(f'Rest pose mismatch {rest_error_value}')
validation_result_record={'status':'passed','rest_max_error':rest_error_value,'weight_sum_max_error':float(np.abs(source_model_bundle['weights'].sum(1)-1).max()),'frames':25,'bones':104,'triangles':len(body_mesh_data.polygons),'motion_source':'수동 관절 가동 검사, 보행 리타게팅 아님','height':TARGET_BODY_HEIGHT}
for current_frame_value in range(1,26):
 scene_render_value.frame_set(current_frame_value);bpy.context.view_layer.update()
 current_evaluated_object=body_mesh_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
 if not np.isfinite(np.array([current_vertex_value.co[:] for current_vertex_value in current_evaluated_object.data.vertices])).all(): raise ValueError('비정상 변형 좌표')
scene_render_value.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');body_mesh_object.select_set(True);rig_armature_object.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'anny-five-head-rig.glb'),use_selection=True,export_animations=True,export_all_influences=True)
(EXPERIMENT_OUTPUT_ROOT/'validation.json').write_text(json.dumps(validation_result_record,ensure_ascii=False,indent=2))
scene_render_value.render.engine='CYCLES';scene_render_value.cycles.samples=24
render_device_preferences=bpy.context.preferences.addons['cycles'].preferences
render_device_preferences.compute_device_type='CUDA';render_device_preferences.get_devices()
if not any(current_device_value.type=='CUDA' for current_device_value in render_device_preferences.devices): raise RuntimeError('CUDA renderer unavailable')
for current_device_value in render_device_preferences.devices: current_device_value.use=current_device_value.type=='CUDA'
scene_render_value.cycles.device='GPU';scene_render_value.render.resolution_x=720;scene_render_value.render.resolution_y=820;scene_render_value.render.resolution_percentage=100
scene_render_value.world=bpy.data.worlds.new('StudioWorld');scene_render_value.world.use_nodes=True;scene_render_value.world.node_tree.nodes['Background'].inputs[0].default_value=(.3,.3,.3,1)
bpy.ops.object.camera_add(location=(0,-5,.8));camera_object_value=bpy.context.object;camera_object_value.data.type='ORTHO';camera_object_value.data.ortho_scale=1.95;scene_render_value.camera=camera_object_value
for current_light_location,current_light_power,current_light_size in [((-3,-4,5),450,4),((3,-2,3),250,3),((0,3,4),350,3)]:
 bpy.ops.object.light_add(type='AREA',location=current_light_location);current_light_object=bpy.context.object;current_light_object.data.energy=current_light_power;current_light_object.data.shape='DISK';current_light_object.data.size=current_light_size;current_light_object.rotation_euler=(Vector((0,0,.8))-current_light_object.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005));floor_mesh_object=bpy.context.object
floor_material_value=bpy.data.materials.new('StudioGround');floor_material_value.diffuse_color=(.2,.22,.24,1);floor_mesh_object.data.materials.append(floor_material_value)
bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'anny-five-head-rig.blend'))
for current_view_name,current_camera_location,current_frame_value in [('front',(0,-5,.8),1),('side',(5,0,.8),1),('back',(0,5,.8),1),('three-quarter',(3,-5,1.6),1),('pose-front',(0,-5,.8),13),('pose-side',(5,0,.8),13)]:
 scene_render_value.frame_set(current_frame_value);camera_object_value.location=current_camera_location;camera_object_value.rotation_euler=(Vector((0,0,.8))-camera_object_value.location).to_track_quat('-Z','Y').to_euler();scene_render_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'{current_view_name}.png');bpy.ops.render.render(write_still=True)
print(validation_result_record,flush=True)
