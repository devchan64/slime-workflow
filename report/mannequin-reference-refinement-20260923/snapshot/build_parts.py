"""채택한 외곽을 유지하고 좁은 곡선 경계와 내부 구체로 분할한다."""
import bpy,bmesh,numpy as np,math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from pathlib import Path
SOURCE_MODEL_FILE=str(Path(__file__).resolve().parent/'sculpted-source.blend')
SURFACE_SEAM_HALF_WIDTH=.0011
JOINT_SOCKET_CLEARANCE=.0007
JOINT_POSITION_VALUES={
 'shoulder':(.174,.024,1.435,.056),'elbow':(.213,.028,1.18,.045),
 'wrist':(.289,-.022,.91,.035),'hip':(.103,.012,.985,.103),
 'knee':(.111,.015,.56,.060),'ankle':(.116,.060,.15,.041)}

def arm_partition_value(point_vector_value):
 return abs(point_vector_value.x)-(.148+.19*max(1.32-point_vector_value.z,0))
def chest_partition_value(point_vector_value):
 horizontal_ratio_value=min(abs(point_vector_value.x)/.16,1)
 return point_vector_value.z-(1.255+.065*(1-horizontal_ratio_value**1.5))
def waist_partition_value(point_vector_value):
 return point_vector_value.z-(1.122+.023*min(abs(point_vector_value.x)/.15,1)**2)
def hip_partition_value(point_vector_value):
 front_blend_value=float(np.clip((.055-point_vector_value.y)/.11,0,1))
 hip_center_values=JOINT_POSITION_VALUES['hip']
 hip_scale_values=JOINT_AXIS_SCALES['hip']
 hip_width_radius=hip_center_values[3]*hip_scale_values[0]
 hip_height_radius=hip_center_values[3]*hip_scale_values[2]
 hip_arc_factor=math.sqrt(max(0,1-((abs(point_vector_value.x)-hip_center_values[0])/hip_width_radius)**2))
 front_height_value=hip_center_values[2]-1.18*hip_height_radius+1.50*hip_height_radius*hip_arc_factor
 back_height_value=hip_center_values[2]-.70*hip_height_radius+.98*hip_height_radius*hip_arc_factor
 return point_vector_value.z-(front_blend_value*front_height_value+(1-front_blend_value)*back_height_value)
def knee_partition_value(point_vector_value):
 front_blend_value=float(np.clip((.06-point_vector_value.y)/.08,0,1))
 return point_vector_value.z-(.53+.037*math.exp(-((abs(point_vector_value.x)-.105)/.046)**2)*front_blend_value)
def elbow_partition_value(point_vector_value):
 front_blend_value=float(np.clip((.06-point_vector_value.y)/.08,0,1))
 return point_vector_value.z-(1.18+.018*math.exp(-((abs(point_vector_value.x)-.228)/.042)**2)*front_blend_value)
def head_partition_value(point_vector_value):return point_vector_value.z-1.565
def neck_partition_value(point_vector_value):return point_vector_value.z-1.535
def wrist_partition_value(point_vector_value):return point_vector_value.z-.91
def ankle_partition_value(point_vector_value):return point_vector_value.z-(.15+.006*math.exp(-((point_vector_value.y+.005)/.06)**2))


JOINT_AXIS_SCALES={'shoulder':(1,1.06,1.12),'elbow':(1,1,1),'wrist':(.90,1.10,1),'hip':(.74,.90,.90),'knee':(.90,1.05,1),'ankle':(1,1,1)}

def create_limb_cup_boundary(joint_name_value,is_upper_shell):
 center_point_values=JOINT_POSITION_VALUES[joint_name_value]
 def evaluate_cup_surface(point_vector_value):
  horizontal_offset_value=(abs(point_vector_value.x)-center_point_values[0])/(center_point_values[3]*1.04)
  cap_profile_value=math.sqrt(max(0,1-horizontal_offset_value**2))
  front_weight_value=float(np.clip((center_point_values[1]+.03-point_vector_value.y)/.07,0,1))
  half_opening_value=(.007+.020*front_weight_value)*cap_profile_value if joint_name_value in ['knee','elbow'] else .008*cap_profile_value
  return point_vector_value.z-center_point_values[2]-(1 if is_upper_shell else -1)*half_opening_value
 return evaluate_cup_surface

def shoulder_arm_boundary(point_vector_value):return point_vector_value.z-1.421

def thigh_hip_boundary(point_vector_value):
 hip_center_values=JOINT_POSITION_VALUES['hip']
 hip_width_radius=hip_center_values[3]*JOINT_AXIS_SCALES['hip'][0]
 return point_vector_value.z-(hip_center_values[2]-.025+.015*min(abs(abs(point_vector_value.x)-hip_center_values[0])/hip_width_radius,1)**2)

def create_surface_partition(source_mesh_value,part_name_value,cut_surface_values):
 source_vertex_points=[vertex_record_value.co.copy() for vertex_record_value in source_mesh_value.vertices]
 partition_vertex_points=[];partition_face_indices=[];coordinate_index_records={}
 for source_polygon_value in source_mesh_value.polygons:
  clipped_polygon_points=[source_vertex_points[vertex_index_value].copy() for vertex_index_value in source_polygon_value.vertices]
  for scalar_axis_index,scalar_function_value,scalar_sign_value in cut_surface_values:
   if not clipped_polygon_points:break
   next_polygon_points=[]
   previous_point_value=clipped_polygon_points[-1]
   previous_scalar_value=scalar_sign_value*scalar_function_value(previous_point_value)-SURFACE_SEAM_HALF_WIDTH
   for current_point_value in clipped_polygon_points:
    current_scalar_value=scalar_sign_value*scalar_function_value(current_point_value)-SURFACE_SEAM_HALF_WIDTH
    if (current_scalar_value>=0)!=(previous_scalar_value>=0):
     edge_fraction_value=previous_scalar_value/(previous_scalar_value-current_scalar_value)
     next_polygon_points.append(previous_point_value.lerp(current_point_value,edge_fraction_value))
    if current_scalar_value>=0:next_polygon_points.append(current_point_value)
    previous_point_value=current_point_value;previous_scalar_value=current_scalar_value
   clipped_polygon_points=next_polygon_points
  if len(clipped_polygon_points)<3:continue
  polygon_index_values=[]
  for point_vector_value in clipped_polygon_points:
   coordinate_key_value=tuple(round(float(component_scalar_value),7) for component_scalar_value in point_vector_value)
   if coordinate_key_value not in coordinate_index_records:
    coordinate_index_records[coordinate_key_value]=len(partition_vertex_points);partition_vertex_points.append(tuple(point_vector_value))
   polygon_index_values.append(coordinate_index_records[coordinate_key_value])
  for corner_index_value in range(1,len(polygon_index_values)-1):
   face_index_values=(polygon_index_values[0],polygon_index_values[corner_index_value],polygon_index_values[corner_index_value+1])
   if len(set(face_index_values))==3:partition_face_indices.append(face_index_values)
 intermediate_mesh_value=bpy.data.meshes.new('surface-partition-intermediate');intermediate_mesh_value.from_pydata(partition_vertex_points,[],partition_face_indices);intermediate_mesh_value.update()
 part_bmesh_value=bmesh.new();part_bmesh_value.from_mesh(intermediate_mesh_value);bpy.data.meshes.remove(intermediate_mesh_value)
 if not part_bmesh_value.faces:raise ValueError(f'빈 부품: {part_name_value}')
 for face_record_value in part_bmesh_value.faces:face_record_value.smooth=True
 # 절단면을 큰 평면으로 막지 않고 얇은 셸의 림으로 연결한다.
 unchecked_vertex_values=set(part_bmesh_value.verts);connected_vertex_groups=[]
 while unchecked_vertex_values:
  connected_vertex_values=set();pending_vertex_values=[unchecked_vertex_values.pop()]
  while pending_vertex_values:
   current_vertex_value=pending_vertex_values.pop();connected_vertex_values.add(current_vertex_value)
   for edge_record_value in current_vertex_value.link_edges:
    neighbor_vertex_value=edge_record_value.other_vert(current_vertex_value)
    if neighbor_vertex_value in unchecked_vertex_values:
     unchecked_vertex_values.remove(neighbor_vertex_value);pending_vertex_values.append(neighbor_vertex_value)
  connected_vertex_groups.append(connected_vertex_values)
 retained_vertex_values=max(connected_vertex_groups,key=len)
 discarded_vertex_values=[vertex_record_value for vertex_record_value in part_bmesh_value.verts if vertex_record_value not in retained_vertex_values]
 if discarded_vertex_values:bmesh.ops.delete(part_bmesh_value,geom=discarded_vertex_values,context='VERTS')
 part_mesh_value=bpy.data.meshes.new(part_name_value+'-mesh');part_bmesh_value.to_mesh(part_mesh_value);part_bmesh_value.free()
 part_object_value=bpy.data.objects.new(part_name_value,part_mesh_value);bpy.context.scene.collection.objects.link(part_object_value)
 return part_object_value


def create_pelvis_surface(source_surface_tree):
 # 중앙의 생성 메시 잔여 면을 없애고 매끈한 골반 외피를 링 단면으로 만든다.
 height_profile_values=[.925,.935,.955,.98,1.02,1.06,1.10,1.145,1.17]
 width_profile_values=[0,.034,.085,.139,.173,.162,.147,.127,.120]
 front_profile_values=[0,.026,.050,.079,.111,.113,.109,.102,.098]
 back_profile_values=[0,.026,.050,.092,.118,.105,.089,.075,.072]
 ring_sample_count=64;ring_height_count=36
 surface_vertex_points=[];surface_polygon_indices=[]
 for height_index_value in range(ring_height_count):
  height_scalar_value=.925+(1.17-.925)*height_index_value/(ring_height_count-1)
  width_scalar_value=float(np.interp(height_scalar_value,height_profile_values,width_profile_values))
  front_scalar_value=float(np.interp(height_scalar_value,height_profile_values,front_profile_values))
  back_scalar_value=float(np.interp(height_scalar_value,height_profile_values,back_profile_values))
  for angle_index_value in range(ring_sample_count):
   angle_scalar_value=2*math.pi*angle_index_value/ring_sample_count
   depth_direction_value=math.sin(angle_scalar_value)
   surface_point_vector=Vector((width_scalar_value*math.cos(angle_scalar_value),(front_scalar_value if depth_direction_value<0 else back_scalar_value)*depth_direction_value,height_scalar_value))
   top_blend_weight=float(np.clip((height_scalar_value-1.025)/.075,0,1));top_blend_weight=top_blend_weight**2*(3-2*top_blend_weight)
   if top_blend_weight>0:
    ray_origin_vector=Vector((0,0,height_scalar_value));ray_direction_vector=Vector((math.cos(angle_scalar_value),depth_direction_value,0)).normalized()
    intersection_point_value,_,_,_=source_surface_tree.ray_cast(ray_origin_vector,ray_direction_vector)
    if intersection_point_value is None:raise ValueError('골반 상단의 원본 몸통 경계 교차 없음')
    surface_point_vector=surface_point_vector.lerp(intersection_point_value,top_blend_weight)
   surface_vertex_points.append(tuple(surface_point_vector))
  if height_index_value:
   for angle_index_value in range(ring_sample_count):
    next_angle_index=(angle_index_value+1)%ring_sample_count
    surface_polygon_indices.append(((height_index_value-1)*ring_sample_count+angle_index_value,(height_index_value-1)*ring_sample_count+next_angle_index,height_index_value*ring_sample_count+next_angle_index,height_index_value*ring_sample_count+angle_index_value))
 pelvis_source_mesh=bpy.data.meshes.new('reference-pelvis-source');pelvis_source_mesh.from_pydata(surface_vertex_points,[],surface_polygon_indices);pelvis_source_mesh.update()
 return pelvis_source_mesh


def create_thigh_surface(side_sign_value):
 height_profile_values=[.51,.56,.62,.72,.82,.90,.96,1.03]
 width_profile_values=[.046,.050,.054,.067,.078,.079,.075,.074]
 depth_profile_values=[.055,.061,.076,.092,.102,.097,.090,.088]
 center_width_values=[.111,.111,.109,.106,.103,.103,.103,.103]
 ring_sample_count=64;ring_height_count=48
 surface_vertex_points=[];surface_polygon_indices=[]
 for height_index_value in range(ring_height_count):
  height_scalar_value=.51+(1.03-.51)*height_index_value/(ring_height_count-1)
  width_scalar_value=float(np.interp(height_scalar_value,height_profile_values,width_profile_values))
  depth_scalar_value=float(np.interp(height_scalar_value,height_profile_values,depth_profile_values))
  center_width_value=float(np.interp(height_scalar_value,height_profile_values,center_width_values))
  for angle_index_value in range(ring_sample_count):
   angle_scalar_value=2*math.pi*angle_index_value/ring_sample_count
   surface_vertex_points.append((side_sign_value*center_width_value+width_scalar_value*math.cos(angle_scalar_value),.012+depth_scalar_value*math.sin(angle_scalar_value),height_scalar_value))
  if height_index_value:
   for angle_index_value in range(ring_sample_count):
    next_angle_index=(angle_index_value+1)%ring_sample_count
    surface_polygon_indices.append(((height_index_value-1)*ring_sample_count+angle_index_value,(height_index_value-1)*ring_sample_count+next_angle_index,height_index_value*ring_sample_count+next_angle_index,height_index_value*ring_sample_count+angle_index_value))
 thigh_source_mesh=bpy.data.meshes.new('reference-thigh-source');thigh_source_mesh.from_pydata(surface_vertex_points,[],surface_polygon_indices);thigh_source_mesh.update()
 return thigh_source_mesh

def create_rigid_parts(write_trace_message):
 bpy.ops.wm.open_mainfile(filepath=SOURCE_MODEL_FILE)
 source_model_object=bpy.data.objects['reference-mannequin-multiview'];source_mesh_value=source_model_object.data.copy()
 surface_material_value=source_model_object.data.materials[0]
 bpy.data.objects.remove(source_model_object,do_unlink=True)
 source_vertex_points=[vertex_record_value.co.copy() for vertex_record_value in source_mesh_value.vertices]
 source_vertex_normals=[vertex_record_value.normal.copy() for vertex_record_value in source_mesh_value.vertices]
 source_polygon_indices=[tuple(polygon_record_value.vertices) for polygon_record_value in source_mesh_value.polygons]
 source_surface_tree=BVHTree.FromPolygons(source_vertex_points,source_polygon_indices,all_triangles=True)
 rigid_part_records=[]
 def append_shell_record(part_name_value,bone_name_value,cut_surface_values,socket_record_values):
  write_trace_message('surface-partition',part_name_value)
  socket_cut_surfaces=list(cut_surface_values)
  if part_name_value in ['chest-shell-part']:
   joint_name_value='shoulder' if part_name_value=='chest-shell-part' else 'hip'
   joint_center_values=JOINT_POSITION_VALUES[joint_name_value]
   joint_scale_values=(1,1,1)
   for side_sign_value in [-1,1]:
    center_point_vector=Vector((side_sign_value*joint_center_values[0],joint_center_values[1],joint_center_values[2]))
    def socket_distance_value(point_vector_value,center_point_vector=center_point_vector,joint_center_values=joint_center_values,joint_scale_values=joint_scale_values):
     return (sum(((point_vector_value[axis_index_value]-center_point_vector[axis_index_value])/joint_scale_values[axis_index_value])**2 for axis_index_value in range(3))**.5)-joint_center_values[3]-.0005
    socket_cut_surfaces.append((0,socket_distance_value,1))
  partition_source_mesh=source_mesh_value
  if part_name_value=='pelvis-shell-part':partition_source_mesh=create_pelvis_surface(source_surface_tree)
  elif part_name_value.endswith('-thigh-shell'):partition_source_mesh=create_thigh_surface(1 if part_name_value.startswith('left') else -1)
  part_object_value=create_surface_partition(partition_source_mesh,part_name_value,socket_cut_surfaces)
  if partition_source_mesh!=source_mesh_value:bpy.data.meshes.remove(partition_source_mesh)
  if part_name_value=='pelvis-shell-part' or part_name_value.endswith('-thigh-shell'):
   for vertex_record_value in part_object_value.data.vertices:
    current_point_value=vertex_record_value.co.copy()
    side_sign_value=1 if current_point_value.x>=0 else -1
    hip_center_values=JOINT_POSITION_VALUES['hip']
    center_point_vector=Vector((side_sign_value*hip_center_values[0],hip_center_values[1],hip_center_values[2]))
    radius_vector_values=Vector(tuple(hip_center_values[3]*axis_scale_value for axis_scale_value in JOINT_AXIS_SCALES['hip']))
    offset_vector_value=current_point_value-center_point_vector
    if part_name_value=='pelvis-shell-part':
     boundary_distance_value=abs(hip_partition_value(current_point_value))
     center_protection_value=float(np.clip((abs(current_point_value.x)-.035)/.035,0,1))
     blend_weight_value=math.exp(-(boundary_distance_value/.025)**2)*center_protection_value
    else:
     boundary_distance_value=abs(thigh_hip_boundary(current_point_value))
     transition_ratio_value=float(np.clip(1-boundary_distance_value/.055,0,1))
     blend_weight_value=transition_ratio_value**2*(3-2*transition_ratio_value)
    radial_length_value=math.sqrt(sum((offset_vector_value[axis_index_value]/radius_vector_values[axis_index_value])**2 for axis_index_value in range(3)))
    if blend_weight_value>.001 and radial_length_value>1e-6:
     vertical_radius_factor=offset_vector_value.z/radius_vector_values.z
     planar_radius_value=math.sqrt((offset_vector_value.x/radius_vector_values.x)**2+(offset_vector_value.y/radius_vector_values.y)**2)
     if abs(vertical_radius_factor)<.98 and planar_radius_value>1e-6:
      planar_scale_value=math.sqrt(max(0,1.014**2-vertical_radius_factor**2))/planar_radius_value
      target_point_value=center_point_vector+Vector((offset_vector_value.x*planar_scale_value,offset_vector_value.y*planar_scale_value,offset_vector_value.z))
      vertex_record_value.co=current_point_value.lerp(target_point_value,blend_weight_value)
   part_object_value.data.update()
  part_object_value.data.materials.append(surface_material_value)
  write_trace_message('preserved-surface',f'{part_name_value}: {len(part_object_value.data.polygons)}')
  bpy.context.view_layer.objects.active=part_object_value
  exterior_normal_records={tuple(round(float(coordinate_value),7) for coordinate_value in vertex_record_value.co):vertex_record_value.normal.copy() for vertex_record_value in part_object_value.data.vertices}
  wall_modifier_value=part_object_value.modifiers.new('inward-shell-wall','SOLIDIFY');wall_modifier_value.thickness=.0015;wall_modifier_value.offset=-1;wall_modifier_value.use_rim=True
  bpy.ops.object.modifier_apply(modifier=wall_modifier_value.name)
  # 내벽 생성 후 외부 노멀을 원본 표면에서 보간해 복원한다.
  part_object_value.data.update()
  recovered_vertex_normals=[]
  for vertex_record_value in part_object_value.data.vertices:
   nearest_point_value,nearest_normal_value,polygon_index_value,surface_distance_value=source_surface_tree.find_nearest(vertex_record_value.co)
   coordinate_key_value=tuple(round(float(coordinate_value),7) for coordinate_value in vertex_record_value.co)
   if (part_name_value=='pelvis-shell-part' or part_name_value.endswith('-thigh-shell')) and coordinate_key_value in exterior_normal_records:
    normal_vector_value=exterior_normal_records[coordinate_key_value]
   elif surface_distance_value<2e-5 and part_name_value!='pelvis-shell-part':
    triangle_index_values=source_polygon_indices[polygon_index_value]
    first_point_value,second_point_value,third_point_value=[source_vertex_points[index_scalar_value] for index_scalar_value in triangle_index_values]
    first_edge_vector=second_point_value-first_point_value;second_edge_vector=third_point_value-first_point_value;target_edge_vector=nearest_point_value-first_point_value
    first_dot_value=first_edge_vector.dot(first_edge_vector);cross_dot_value=first_edge_vector.dot(second_edge_vector);second_dot_value=second_edge_vector.dot(second_edge_vector)
    target_first_value=target_edge_vector.dot(first_edge_vector);target_second_value=target_edge_vector.dot(second_edge_vector)
    determinant_scalar_value=first_dot_value*second_dot_value-cross_dot_value*cross_dot_value
    if abs(determinant_scalar_value)>1e-18:
     second_weight_value=(second_dot_value*target_first_value-cross_dot_value*target_second_value)/determinant_scalar_value
     third_weight_value=(first_dot_value*target_second_value-cross_dot_value*target_first_value)/determinant_scalar_value
     normal_vector_value=(source_vertex_normals[triangle_index_values[0]]*(1-second_weight_value-third_weight_value)+source_vertex_normals[triangle_index_values[1]]*second_weight_value+source_vertex_normals[triangle_index_values[2]]*third_weight_value).normalized()
    else:normal_vector_value=nearest_normal_value
   else:normal_vector_value=vertex_record_value.normal.copy()
   recovered_vertex_normals.append(normal_vector_value)
  loop_normal_values=[Vector((0,0,1)) for loop_record_value in part_object_value.data.loops]
  for polygon_record_value in part_object_value.data.polygons:
   for loop_index_value in polygon_record_value.loop_indices:
    loop_normal_values[loop_index_value]=recovered_vertex_normals[part_object_value.data.loops[loop_index_value].vertex_index] if polygon_record_value.use_smooth else polygon_record_value.normal
  part_object_value.data.normals_split_custom_set(loop_normal_values)
  rigid_part_records.append((part_object_value,bone_name_value,'shell'))
 def append_internal_ball(part_name_value,bone_name_value,center_point_values,radius_scalar_value,axis_scale_values=(1,1,1)):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=radius_scalar_value,location=center_point_values)
  part_object_value=bpy.context.object;part_object_value.name=part_name_value;part_object_value.scale=axis_scale_values
  bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  part_object_value.data.materials.append(surface_material_value)
  for polygon_record_value in part_object_value.data.polygons:polygon_record_value.use_smooth=True
  rigid_part_records.append((part_object_value,bone_name_value,'ball'))
 torso_cut_values=[(0,arm_partition_value,-1)]
 shoulder_socket_values=[((side_sign_value*.182,.024,1.435),.051) for side_sign_value in [-1,1]]
 hip_socket_values=[((side_sign_value*.103,-.005,.985),.073) for side_sign_value in [-1,1]]
 append_shell_record('head-shell-part','joint-15',[(2,head_partition_value,1)],[((0,0,1.555),.035)])
 append_shell_record('neck-shell-part','joint-12',[(2,head_partition_value,-1),(2,neck_partition_value,1)],[])
 append_shell_record('chest-shell-part','joint-09',torso_cut_values+[(2,neck_partition_value,-1),(2,chest_partition_value,1)],shoulder_socket_values)
 append_shell_record('abdomen-shell-part','joint-06',torso_cut_values+[(2,chest_partition_value,-1),(2,waist_partition_value,1)],[])
 append_shell_record('pelvis-shell-part','body-root-control',torso_cut_values+[(2,waist_partition_value,-1),(2,hip_partition_value,1)],hip_socket_values)
 append_internal_ball('head-pivot-ball','joint-15',(0,0,1.555),.034)
 for side_sign_value,side_name_value,bone_index_values in [(1,'left',[4,7,10,18,20]),(-1,'right',[5,8,11,19,21])]:
  hip_bone_index,knee_bone_index,foot_bone_index,arm_bone_index,wrist_bone_index=bone_index_values
  def side_partition_value(point_vector_value):return point_vector_value.x*side_sign_value
  arm_cut_values=[(2,neck_partition_value,-1),(0,arm_partition_value,1),(0,side_partition_value,1)]
  leg_cut_values=[(0,arm_partition_value,-1),(0,side_partition_value,1)]
  joint_socket_values={joint_name_value:((side_sign_value*joint_value_values[0],joint_value_values[1],joint_value_values[2]),joint_value_values[3]) for joint_name_value,joint_value_values in JOINT_POSITION_VALUES.items()}
  append_shell_record(side_name_value+'-upper-arm-shell',f'joint-{arm_bone_index:02d}',arm_cut_values+[(2,shoulder_arm_boundary,-1),(2,create_limb_cup_boundary('elbow',True),1)],[joint_socket_values['shoulder'],joint_socket_values['elbow']])
  append_shell_record(side_name_value+'-forearm-shell',f'joint-{wrist_bone_index:02d}',arm_cut_values+[(2,create_limb_cup_boundary('elbow',False),-1),(2,create_limb_cup_boundary('wrist',True),1)],[joint_socket_values['elbow'],joint_socket_values['wrist']])
  append_shell_record(side_name_value+'-hand-shell',f'hand-{wrist_bone_index:02d}-deform',arm_cut_values+[(2,create_limb_cup_boundary('wrist',False),-1)],[joint_socket_values['wrist']])
  append_shell_record(side_name_value+'-thigh-shell',f'joint-{hip_bone_index:02d}',leg_cut_values+[(2,thigh_hip_boundary,-1),(2,create_limb_cup_boundary('knee',True),1)],[joint_socket_values['hip'],joint_socket_values['knee']])
  append_shell_record(side_name_value+'-shin-shell',f'joint-{knee_bone_index:02d}',leg_cut_values+[(2,create_limb_cup_boundary('knee',False),-1),(2,create_limb_cup_boundary('ankle',True),1)],[joint_socket_values['knee'],joint_socket_values['ankle']])
  append_shell_record(side_name_value+'-foot-shell',f'joint-{foot_bone_index:02d}',leg_cut_values+[(2,create_limb_cup_boundary('ankle',False),-1)],[joint_socket_values['ankle']])
  for joint_name_value,bone_name_value in [('shoulder',f'joint-{arm_bone_index:02d}'),('elbow',f'joint-{wrist_bone_index:02d}'),('wrist',f'hand-{wrist_bone_index:02d}-deform'),('hip',f'joint-{hip_bone_index:02d}'),('knee',f'joint-{knee_bone_index:02d}'),('ankle',f'joint-{foot_bone_index:02d}')]:
   center_point_values,radius_scalar_value=joint_socket_values[joint_name_value]
   append_internal_ball(side_name_value+'-'+joint_name_value+'-ball',bone_name_value,center_point_values,radius_scalar_value,JOINT_AXIS_SCALES[joint_name_value])
 from face_details import append_eye_details
 append_eye_details(bpy.data.objects['head-shell-part'])
 bpy.data.meshes.remove(source_mesh_value)
 return rigid_part_records
