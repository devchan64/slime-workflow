"""Hunyuan 마네킨 자동 가중치·MoMask 보행 리타게팅 실험."""
from pathlib import Path
import bpy,numpy as np,time,threading,traceback,json,hashlib,math
from mathutils import Vector,Matrix
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
EXPERIMENT_OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
WORKFLOW_SOURCE_ROOT=Path(__file__).resolve().parents[2]
SOURCE_BLEND_PATH=Path('/home/cbsim/ws/slime-workflow/.tmp/2026-09-23_01-02-22/model-review/mannequin.blend')
SOURCE_MOTION_PATH=WORKFLOW_SOURCE_ROOT/'assets/motion-sheet/mannequin-walk-v1/mannequin-motion.npz'
SOURCE_MANIFEST_PATH=SOURCE_MOTION_PATH.with_name('artifact.json')
JOINT_PARENT_INDICES=[-1,0,0,0,1,2,3,4,5,6,7,8,9,9,9,12,13,14,16,17,18,19]
# HumanML3D y-up 정렬. 현재 메시의 관절 중심에 수동 정렬한 중립 본 위치.
TARGET_REST_POINTS=np.array([[0,1.03,0],[.103,.985,.005],[-.103,.985,.005],[0,1.125,.02],
 [.105,.53,-.027],[-.105,.53,-.027],[0,1.25,.025],[.110,.15,-.060],[-.110,.15,-.060],[0,1.54,0],
 [.110,.065,.095],[-.110,.065,.095],[0,1.555,0],[.080,1.455,-.018],[-.080,1.455,-.018],[0,1.80,0],
 [.182,1.435,-.024],[-.182,1.435,-.024],[.228,1.18,-.028],[-.228,1.18,-.028],[.306,.91,.022],[-.306,.91,.022]],dtype=float)
VIEW_CAMERA_POINTS={'down_left':(4,-6,2.8),'down_right':(-4,-6,2.8),'up_left':(4,6,2.8),'up_right':(-4,6,2.8)}
RENDER_SAMPLE_FRAMES=[1,4,7,10,13,16,19,22]
HEARTBEAT_STOP_EVENT=threading.Event()
CURRENT_STAGE_RECORD={'stage':'prepare','frame':0}

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/hunyuan-rig/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):write_trace_message('heartbeat',f'{CURRENT_STAGE_RECORD} images={len(list(EXPERIMENT_OUTPUT_ROOT.glob("*.png")))}')
def convert_joint_vector(joint_point_value):
 return Vector((float(joint_point_value[0]),float(-joint_point_value[2]),float(joint_point_value[1])))

def collect_deformed_vertices(rigid_part_records):
 deformed_part_points=[]
 for part_object_value,_,_ in rigid_part_records:
  evaluated_mesh_object=part_object_value.evaluated_get(bpy.context.evaluated_depsgraph_get())
  evaluated_vertex_values=np.empty(len(evaluated_mesh_object.data.vertices)*3,dtype=np.float64)
  evaluated_mesh_object.data.vertices.foreach_get('co',evaluated_vertex_values)
  object_world_matrix=np.array(evaluated_mesh_object.matrix_world)
  deformed_part_points.append(evaluated_vertex_values.reshape(-1,3)@object_world_matrix[:3,:3].T+object_world_matrix[:3,3])
 return np.concatenate(deformed_part_points)

def execute_rig_experiment():
 write_trace_message('start',f'입력={SOURCE_BLEND_PATH}, {SOURCE_MOTION_PATH} 출력={EXPERIMENT_OUTPUT_ROOT}')
 source_manifest_record=json.loads(SOURCE_MANIFEST_PATH.read_text())
 if hashlib.sha256(SOURCE_MOTION_PATH.read_bytes()).hexdigest()!=source_manifest_record['files']['mannequin-motion.npz']:raise ValueError('기준 모션 해시 불일치')
 with np.load(SOURCE_MOTION_PATH,allow_pickle=False) as source_motion_bundle:
  if set(source_motion_bundle.files)!={'joints','rest','contacts','sample_indices'}:raise ValueError('모션 필드 불일치')
  source_joint_frames=source_motion_bundle['joints'].copy();source_rest_points=source_motion_bundle['rest'].copy()
 if source_joint_frames.shape!=(25,22,3) or not np.isfinite(source_joint_frames).all():raise ValueError('모션 관절 스키마 불일치')
 if not np.allclose(source_joint_frames[0],source_joint_frames[-1]):raise ValueError('원본 루프 끝점 불일치')
 from build_parts import create_rigid_parts
 rigid_part_records=create_rigid_parts(write_trace_message)
 render_scene_value=bpy.context.scene
 bpy.ops.object.select_all(action='DESELECT')
 bpy.ops.object.armature_add()
 rig_object_value=bpy.context.object;rig_object_value.name='multiview-ball-joint-rig'
 rig_object_value.show_in_front=True
 bpy.ops.object.mode_set(mode='EDIT');rig_object_value.data.edit_bones.remove(rig_object_value.data.edit_bones[0])
 root_edit_bone=rig_object_value.data.edit_bones.new('body-root-control')
 root_edit_bone.head=(0,0,.92);root_edit_bone.tail=convert_joint_vector(TARGET_REST_POINTS[0]);root_edit_bone.use_deform=True
 for joint_index_value in range(1,22):
  parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
  created_edit_bone=rig_object_value.data.edit_bones.new(f'joint-{joint_index_value:02d}')
  created_edit_bone.head=convert_joint_vector(TARGET_REST_POINTS[parent_index_value]);created_edit_bone.tail=convert_joint_vector(TARGET_REST_POINTS[joint_index_value])
  created_edit_bone.parent=rig_object_value.data.edit_bones[f'joint-{parent_index_value:02d}'] if parent_index_value>0 else root_edit_bone
  created_edit_bone.use_connect=parent_index_value>0
  created_edit_bone.use_deform=joint_index_value not in [1,2,13,14]
 for wrist_index_value,hand_sign_value in [(20,1),(21,-1)]:
  hand_edit_bone=rig_object_value.data.edit_bones.new(f'hand-{wrist_index_value:02d}-deform')
  hand_edit_bone.head=convert_joint_vector(TARGET_REST_POINTS[wrist_index_value]);hand_edit_bone.tail=convert_joint_vector(TARGET_REST_POINTS[wrist_index_value]+np.array([hand_sign_value*.005,-.14,.015]))
  hand_edit_bone.parent=rig_object_value.data.edit_bones[f'joint-{wrist_index_value:02d}'];hand_edit_bone.use_connect=True
 bpy.ops.object.mode_set(mode='OBJECT')
 CURRENT_STAGE_RECORD.update(stage='rigid-weights')
 from refine_weights import apply_surface_weights
 apply_surface_weights(rigid_part_records,rig_object_value)
 missing_vertex_count=sum(not vertex_record_value.groups or abs(sum(group_record_value.weight for group_record_value in vertex_record_value.groups)-1)>1e-5 for part_object_value,_,_ in rigid_part_records for vertex_record_value in part_object_value.data.vertices)
 if missing_vertex_count:raise ValueError(f'가중치 정규화 오류: {missing_vertex_count}')
 write_trace_message('weights','구체는 단일 본, 외곽 연결부는 최대 두 본 혼합')
 target_joint_frames=np.zeros_like(source_joint_frames)
 target_joint_frames[:,0]=TARGET_REST_POINTS[0]+source_joint_frames[:,0]-source_rest_points[0]
 for frame_index_value in range(25):
  for joint_index_value in range(1,22):
   parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
   original_rest_vector=convert_joint_vector(source_rest_points[joint_index_value]-source_rest_points[parent_index_value])
   source_motion_vector=convert_joint_vector(source_joint_frames[frame_index_value,joint_index_value]-source_joint_frames[frame_index_value,parent_index_value])
   target_rest_vector=convert_joint_vector(TARGET_REST_POINTS[joint_index_value]-TARGET_REST_POINTS[parent_index_value])
   current_bone_vector=original_rest_vector.rotation_difference(source_motion_vector)@target_rest_vector
   target_joint_frames[frame_index_value,joint_index_value]=target_joint_frames[frame_index_value,parent_index_value]+np.array([current_bone_vector.x,current_bone_vector.z,-current_bone_vector.y])
 ground_offset_values=[]
 CURRENT_STAGE_RECORD.update(stage='animate')
 for frame_index_value,joint_frame_points in enumerate(target_joint_frames):
  render_scene_value.frame_set(frame_index_value+1)
  rig_object_value.location=(0,0,0)
  root_pose_bone=rig_object_value.pose.bones['body-root-control']
  root_pose_bone.location=convert_joint_vector(joint_frame_points[0]-TARGET_REST_POINTS[0])
  root_pose_bone.keyframe_insert('location',frame=frame_index_value+1)
  bpy.context.view_layer.update()
  for joint_index_value in range(1,22):
   parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
   current_head_vector=convert_joint_vector(joint_frame_points[parent_index_value]);current_tail_vector=convert_joint_vector(joint_frame_points[joint_index_value])
   rest_head_vector=convert_joint_vector(TARGET_REST_POINTS[parent_index_value]);rest_tail_vector=convert_joint_vector(TARGET_REST_POINTS[joint_index_value])
   bone_name_value=f'joint-{joint_index_value:02d}'
   rest_rotation_value=rig_object_value.data.bones[bone_name_value].matrix_local.to_quaternion()
   motion_rotation_value=(rest_tail_vector-rest_head_vector).rotation_difference(current_tail_vector-current_head_vector)
   pose_bone_value=rig_object_value.pose.bones[bone_name_value]
   pose_bone_value.rotation_mode='QUATERNION';pose_bone_value.matrix=Matrix.Translation(current_head_vector)@(motion_rotation_value@rest_rotation_value).to_matrix().to_4x4()
   pose_bone_value.keyframe_insert('location',frame=frame_index_value+1);pose_bone_value.keyframe_insert('rotation_quaternion',frame=frame_index_value+1);pose_bone_value.keyframe_insert('scale',frame=frame_index_value+1)
   bpy.context.view_layer.update()
  evaluated_vertex_points=collect_deformed_vertices(rigid_part_records)
  if not np.isfinite(evaluated_vertex_points).all():raise ValueError('비정상 변형 좌표')
  foot_ground_offset=-float(evaluated_vertex_points[:,2].min())
  ground_offset_values.append(foot_ground_offset)
  rig_object_value.location.z=foot_ground_offset;rig_object_value.keyframe_insert('location',frame=frame_index_value+1)
  CURRENT_STAGE_RECORD.update(frame=frame_index_value+1)
 # 원본 보행의 고정 굽힘 편향을 중립 마네킨에 맞춰 보정한다. 프레임별 흔들림은 보존한다.
 spine_neutral_pitch={'joint-03':1.0,'joint-06':1.0,'joint-09':2.0,'joint-12':-3.0,'joint-15':-1.0}
 original_spine_angles={bone_name_value:[] for bone_name_value in spine_neutral_pitch}
 original_collar_rotations={bone_name_value:[] for bone_name_value in ['joint-13','joint-14']}
 for frame_number_value in range(1,26):
  render_scene_value.frame_set(frame_number_value)
  for bone_name_value in spine_neutral_pitch:original_spine_angles[bone_name_value].append(rig_object_value.pose.bones[bone_name_value].rotation_quaternion.to_euler('XYZ').copy())
  for bone_name_value in original_collar_rotations:original_collar_rotations[bone_name_value].append(rig_object_value.pose.bones[bone_name_value].matrix.to_quaternion().copy())
 spine_pitch_offsets={bone_name_value:float(np.mean([angle_vector_value.x for angle_vector_value in angle_frame_values[:24]]))-math.radians(spine_neutral_pitch[bone_name_value]) for bone_name_value,angle_frame_values in original_spine_angles.items()}
 for frame_number_value in range(1,26):
  render_scene_value.frame_set(frame_number_value)
  for bone_name_value,angle_frame_values in original_spine_angles.items():
   adjusted_angle_vector=angle_frame_values[frame_number_value-1].copy();adjusted_angle_vector.x-=spine_pitch_offsets[bone_name_value]
   pose_bone_value=rig_object_value.pose.bones[bone_name_value];pose_bone_value.rotation_quaternion=adjusted_angle_vector.to_quaternion();pose_bone_value.keyframe_insert('rotation_quaternion',frame=frame_number_value)
  bpy.context.view_layer.update()
  # 흉곽 자세 보정이 기존 팔 스윙의 월드 방향을 바꾸지 않도록 쇄골에서 상쇄한다.
  for bone_name_value,rotation_frame_values in original_collar_rotations.items():
   pose_bone_value=rig_object_value.pose.bones[bone_name_value]
   pose_bone_value.matrix=Matrix.Translation(pose_bone_value.head)@rotation_frame_values[frame_number_value-1].to_matrix().to_4x4()
   pose_bone_value.keyframe_insert('rotation_quaternion',frame=frame_number_value)
  bpy.context.view_layer.update()
 write_trace_message('retarget-calibration',str({bone_name_value:math.degrees(offset_scalar_value) for bone_name_value,offset_scalar_value in spine_pitch_offsets.items()}))
 # 강체 몸통의 소켓과 구체가 어긋나지 않도록 보조 본을 몸통에 고정한다.
 rigid_helper_names={'joint-01','joint-02','joint-13','joint-14','joint-16','joint-17'}
 ground_offset_values=[]
 original_rigid_frames=[]
 for frame_number_value in range(1,26):
  render_scene_value.frame_set(frame_number_value);bpy.context.view_layer.update()
  original_rigid_frames.append({'rotations':{pose_bone_value.name:pose_bone_value.matrix.to_quaternion().copy() for pose_bone_value in rig_object_value.pose.bones},'hip_axis':(rig_object_value.pose.bones['joint-04'].head-rig_object_value.pose.bones['joint-05'].head).normalized(),'root_head':rig_object_value.pose.bones['body-root-control'].head.copy()})
 for frame_number_value in range(1,26):
  render_scene_value.frame_set(frame_number_value);bpy.context.view_layer.update()
  saved_world_rotations=original_rigid_frames[frame_number_value-1]['rotations']
  hip_direction_vector=original_rigid_frames[frame_number_value-1]['hip_axis']
  pelvis_rotation_value=Vector((1,0,0)).rotation_difference(hip_direction_vector)
  root_pose_bone=rig_object_value.pose.bones['body-root-control']
  root_pose_bone.rotation_mode='QUATERNION'
  root_pose_bone.matrix=Matrix.Translation(original_rigid_frames[frame_number_value-1]['root_head'])@(pelvis_rotation_value@rig_object_value.data.bones['body-root-control'].matrix_local.to_quaternion()).to_matrix().to_4x4()
  root_pose_bone.keyframe_insert('location',frame=frame_number_value);root_pose_bone.keyframe_insert('rotation_quaternion',frame=frame_number_value)
  bpy.context.view_layer.update()
  for pose_bone_value in rig_object_value.pose.bones:
   if pose_bone_value.name=='body-root-control':continue
   pose_bone_value.rotation_mode='QUATERNION'
   pose_bone_value.location=(0,0,0);pose_bone_value.scale=(1,1,1)
   if pose_bone_value.name in rigid_helper_names:pose_bone_value.rotation_quaternion=(1,0,0,0)
   else:pose_bone_value.matrix=Matrix.Translation(pose_bone_value.head)@saved_world_rotations[pose_bone_value.name].to_matrix().to_4x4()
   pose_bone_value.keyframe_insert('location',frame=frame_number_value);pose_bone_value.keyframe_insert('rotation_quaternion',frame=frame_number_value);pose_bone_value.keyframe_insert('scale',frame=frame_number_value)
   bpy.context.view_layer.update()
  rig_object_value.location=(0,0,0);bpy.context.view_layer.update()
  foot_ground_offset=-float(collect_deformed_vertices(rigid_part_records)[:,2].min())
  rig_object_value.location.z=foot_ground_offset;rig_object_value.keyframe_insert('location',frame=frame_number_value)
  ground_offset_values.append(foot_ground_offset)
 write_trace_message('rigid-socket-lock','고관절·쇄골 보조 본 고정 및 보행 골반 회전 적용')
 # 20fps · 24프레임 루프, 마지막 25번은 시작점과 같은 보간용 키프레임.
 render_scene_value.frame_start=1;render_scene_value.frame_end=25;render_scene_value.render.fps=20;render_scene_value.render.fps_base=1
 render_scene_value.frame_set(1)
 render_scene_value.render.resolution_x=768;render_scene_value.render.resolution_y=768;render_scene_value.cycles.samples=24
 render_scene_value.camera.data.ortho_scale=2.40
 render_scene_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/'preview.png')
 np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'retargeted-motion.npz',joints=target_joint_frames,rest=TARGET_REST_POINTS,ground_offsets=np.array(ground_offset_values))
 bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.blend'))
 bpy.ops.object.select_all(action='DESELECT')
 for part_object_value,_,_ in rigid_part_records:part_object_value.select_set(True)
 rig_object_value.select_set(True);bpy.context.view_layer.objects.active=rig_object_value
 bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.glb'),use_selection=True,export_format='GLB',export_animations=True)
 device_preferences_value=bpy.context.preferences.addons['cycles'].preferences;device_preferences_value.compute_device_type='CUDA';device_preferences_value.get_devices()
 gpu_device_values=[device_record_value for device_record_value in device_preferences_value.devices if device_record_value.type=='CUDA']
 if not gpu_device_values:raise RuntimeError('샌드박스 밖 CUDA 렌더 장치 없음')
 for device_record_value in device_preferences_value.devices:device_record_value.use=device_record_value.type=='CUDA'
 render_scene_value.cycles.device='GPU'
 saved_motion_action=rig_object_value.animation_data.action
 rig_object_value.animation_data.action=None
 rig_object_value.data.pose_position='REST';rig_object_value.location=(0,0,0)
 for view_name_value,camera_point_values in {'front':(0,-6,1),'side':(6,0,1),'back':(0,6,1),'three-quarter':(4,-6,2.3)}.items():
  camera_target_vector=Vector((0,0,1));render_scene_value.camera.location=camera_point_values;render_scene_value.camera.rotation_euler=(camera_target_vector-render_scene_value.camera.location).to_track_quat('-Z','Y').to_euler()
  camera_right_vector=render_scene_value.camera.rotation_euler.to_quaternion()@Vector((1,0,0));camera_front_vector=(render_scene_value.camera.location-camera_target_vector).normalized()
  for light_name_value,light_side_value in [('key',-1),('fill',1)]:
   light_object_value=bpy.data.objects[light_name_value];light_object_value.location=camera_target_vector+camera_front_vector*3+camera_right_vector*light_side_value*3+Vector((0,0,3));light_object_value.rotation_euler=(camera_target_vector-light_object_value.location).to_track_quat('-Z','Y').to_euler()
  CURRENT_STAGE_RECORD.update(stage='rest-'+view_name_value)
  render_scene_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'rest-{view_name_value}.png');bpy.ops.render.render(write_still=True)
 rig_object_value.animation_data.action=saved_motion_action
 rig_object_value.data.pose_position='POSE'
 for view_name_value,camera_point_values in VIEW_CAMERA_POINTS.items():
  camera_target_vector=Vector((0,0,1))
  render_scene_value.camera.location=camera_point_values
  render_scene_value.camera.rotation_euler=(camera_target_vector-render_scene_value.camera.location).to_track_quat('-Z','Y').to_euler()
  camera_right_vector=render_scene_value.camera.rotation_euler.to_quaternion()@Vector((1,0,0))
  camera_front_vector=(render_scene_value.camera.location-camera_target_vector).normalized()
  for light_name_value,light_side_value in [('key',-1),('fill',1)]:
   light_object_value=bpy.data.objects[light_name_value]
   light_object_value.location=camera_target_vector+camera_front_vector*3+camera_right_vector*light_side_value*3+Vector((0,0,3))
   light_object_value.rotation_euler=(camera_target_vector-light_object_value.location).to_track_quat('-Z','Y').to_euler()
  for sample_frame_index,frame_number_value in enumerate(RENDER_SAMPLE_FRAMES):
   CURRENT_STAGE_RECORD.update(stage=view_name_value,frame=frame_number_value)
   render_scene_value.frame_set(frame_number_value)
   render_scene_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}-{sample_frame_index+1:02d}.png')
   bpy.ops.render.render(write_still=True)
 result_record_value={'status':'rigged_ball_joint_candidate','source_mesh_sha256':hashlib.sha256(SOURCE_BLEND_PATH.read_bytes()).hexdigest(),'source_motion_id':'mannequin-walk/v1','source_motion_sha256':hashlib.sha256(SOURCE_MOTION_PATH.read_bytes()).hexdigest(),'bones':len(rig_object_value.data.bones),'parts':[{'name':part_object_value.name,'bone':bone_name_value,'kind':part_kind_value,'triangles':sum(len(polygon_record_value.vertices)-2 for polygon_record_value in part_object_value.data.polygons)} for part_object_value,bone_name_value,part_kind_value in rigid_part_records],'weight_method':'내부 구체 강체 고정 + 외곽 연결부 최대 두 본 혼합','unweighted_vertices':missing_vertex_count,'fps':20,'cycle_seconds':1.2,'ground_offsets':ground_offset_values,'render_sample_frames':RENDER_SAMPLE_FRAMES,'quality_warnings':['디지털 모션 검수용이며 실물 조립용 공차·내부 고정 구조 미설계','손가락 개별 리그 없음','극단 각도에서 셸 간 충돌은 추가 검수 필요']}
 (EXPERIMENT_OUTPUT_ROOT/'result.json').write_text(json.dumps(result_record_value,ensure_ascii=False,indent=2))
 write_trace_message('complete',str(result_record_value))
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:execute_rig_experiment()
except Exception:
 write_trace_message('failure',traceback.format_exc())
 (EXPERIMENT_OUTPUT_ROOT/'result.json').write_text(json.dumps({'status':'failed','error':traceback.format_exc()},ensure_ascii=False));raise
finally:HEARTBEAT_STOP_EVENT.set()
