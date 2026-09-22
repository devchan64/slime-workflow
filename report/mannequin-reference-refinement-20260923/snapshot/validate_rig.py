"""보행 전 프레임의 강체 길이·관절 중심·루프·지면을 검사한다."""
from pathlib import Path
import bpy,numpy as np,json,time,hashlib
from mathutils import Vector
from build_parts import JOINT_POSITION_VALUES
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
VALIDATION_ERROR_LIMIT=1e-5

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/rig-validation/{stage_name_value} {message_text_value}',flush=True)
def collect_world_vertices(part_object_value):
 evaluated_object_value=part_object_value.evaluated_get(bpy.context.evaluated_depsgraph_get())
 coordinate_array_values=np.empty(len(evaluated_object_value.data.vertices)*3)
 evaluated_object_value.data.vertices.foreach_get('co',coordinate_array_values)
 world_matrix_values=np.array(evaluated_object_value.matrix_world)
 return coordinate_array_values.reshape(-1,3)@world_matrix_values[:3,:3].T+world_matrix_values[:3,3]

bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.blend'))
rig_object_value=bpy.data.objects['multiview-ball-joint-rig']
rig_part_objects=[object_record_value for object_record_value in bpy.data.objects if object_record_value.type=='MESH']
rest_edge_lengths={};part_edge_indices={};total_triangle_count=0
for part_object_value in rig_part_objects:
 if 'rigid_bone_name' not in part_object_value:raise ValueError(f'부품 본 정보 누락: {part_object_value.name}')
 for vertex_record_value in part_object_value.data.vertices:
  if not vertex_record_value.groups or len(vertex_record_value.groups)>2 or abs(sum(group_record_value.weight for group_record_value in vertex_record_value.groups)-1)>1e-5:raise ValueError('연결부 가중치 불일치')
 vertex_point_values=np.array([vertex_record_value.co[:] for vertex_record_value in part_object_value.data.vertices])
 edge_index_values=np.array([edge_record_value.vertices[:] for edge_record_value in part_object_value.data.edges])
 rest_edge_lengths[part_object_value.name]=np.linalg.norm(vertex_point_values[edge_index_values[:,0]]-vertex_point_values[edge_index_values[:,1]],axis=1)
 part_edge_indices[part_object_value.name]=edge_index_values
 total_triangle_count+=sum(len(polygon_record_value.vertices)-2 for polygon_record_value in part_object_value.data.polygons)
maximum_edge_error=0.0;maximum_joint_error=0.0;maximum_floor_error=0.0
first_frame_points={};last_frame_points={};baked_joint_frames=[];joint_error_records={}
for frame_number_value in range(1,26):
 bpy.context.scene.frame_set(frame_number_value)
 frame_floor_height=float('inf')
 for part_object_value in rig_part_objects:
  vertex_point_values=collect_world_vertices(part_object_value)
  if not np.isfinite(vertex_point_values).all():raise ValueError('비정상 변형 좌표')
  edge_index_values=part_edge_indices[part_object_value.name]
  deformed_edge_lengths=np.linalg.norm(vertex_point_values[edge_index_values[:,0]]-vertex_point_values[edge_index_values[:,1]],axis=1)
  if part_object_value['part_kind']!='shell':maximum_edge_error=max(maximum_edge_error,float(np.abs(deformed_edge_lengths-rest_edge_lengths[part_object_value.name]).max()))
  frame_floor_height=min(frame_floor_height,float(vertex_point_values[:,2].min()))
  if frame_number_value==1:first_frame_points[part_object_value.name]=vertex_point_values.copy()
  if frame_number_value==25:last_frame_points[part_object_value.name]=vertex_point_values.copy()
 maximum_floor_error=max(maximum_floor_error,abs(frame_floor_height))
 for side_name_value,side_sign_value in [('left',1),('right',-1)]:
  for joint_name_value,proximal_part_name in [('shoulder','chest-shell-part'),('elbow',side_name_value+'-upper-arm-shell'),('wrist',side_name_value+'-forearm-shell'),('hip','pelvis-shell-part'),('knee',side_name_value+'-thigh-shell'),('ankle',side_name_value+'-shin-shell')]:
   source_center_values=JOINT_POSITION_VALUES[joint_name_value]
   source_center_vector=Vector((side_sign_value*source_center_values[0],source_center_values[1],source_center_values[2]))
   proximal_bone_name=bpy.data.objects[proximal_part_name]['rigid_bone_name'];distal_bone_name=bpy.data.objects[side_name_value+'-'+joint_name_value+'-ball']['rigid_bone_name']
   proximal_center_vector=rig_object_value.pose.bones[proximal_bone_name].matrix@rig_object_value.data.bones[proximal_bone_name].matrix_local.inverted()@source_center_vector
   distal_center_vector=rig_object_value.pose.bones[distal_bone_name].matrix@rig_object_value.data.bones[distal_bone_name].matrix_local.inverted()@source_center_vector
   error_scalar_value=(proximal_center_vector-distal_center_vector).length
   maximum_joint_error=max(maximum_joint_error,error_scalar_value)
   joint_error_records[side_name_value+'-'+joint_name_value]=max(joint_error_records.get(side_name_value+'-'+joint_name_value,0),error_scalar_value)
 joint_frame_points=[rig_object_value.matrix_world@rig_object_value.pose.bones['joint-03'].head]
 joint_frame_points += [rig_object_value.matrix_world@rig_object_value.pose.bones[f'joint-{joint_index_value:02d}'].tail for joint_index_value in range(1,22)]
 baked_joint_frames.append([[joint_point_value.x,joint_point_value.z,-joint_point_value.y] for joint_point_value in joint_frame_points])
 if frame_number_value%5==0:write_trace_message('frame',str(frame_number_value))
loop_position_error=max(float(np.abs(first_frame_points[part_name_value]-last_frame_points[part_name_value]).max()) for part_name_value in first_frame_points)
if max(maximum_edge_error,maximum_joint_error,maximum_floor_error,loop_position_error)>VALIDATION_ERROR_LIMIT:raise ValueError(f'검증 오차 초과 edge={maximum_edge_error} joint={maximum_joint_error} floor={maximum_floor_error} loop={loop_position_error}')
np.savez_compressed(EXPERIMENT_OUTPUT_ROOT/'verified-baked-motion.npz',joints=np.array(baked_joint_frames),fps=np.array(20),frame_numbers=np.arange(1,26))
validation_result_record={'status':'passed','frames':25,'bones':len(rig_object_value.data.bones),'parts':len(rig_part_objects),'surface_weight_policy':'외곽 연결부 최대 두 본 혼합, 내부 구체만 강체','triangles':total_triangle_count,'max_internal_ball_edge_length_error':maximum_edge_error,'max_socket_center_error':maximum_joint_error,'max_ground_height_error':maximum_floor_error,'loop_max_vertex_error':loop_position_error,'joint_center_errors':joint_error_records,'source_motion_id':'mannequin-walk/v1','coordinate_units':'정규화 모델 높이 2.0, Blender 미터 단위','quality_warnings':['검증은 제공된 보행 루프 범위이며 극단 각도 충돌을 보증하지 않음','손가락 개별 리그 미적용','내부 연결면은 디지털용으로 실물 조립 구조가 아님']}
(EXPERIMENT_OUTPUT_ROOT/'validation.json').write_text(json.dumps(validation_result_record,ensure_ascii=False,indent=2))
write_trace_message('complete',str(validation_result_record))
