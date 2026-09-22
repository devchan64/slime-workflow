"""외곽 연결부만 두 본으로 혼합하고 내부 구체는 강체로 유지한다."""
import numpy as np,bpy
from mathutils import Vector
from build_parts import JOINT_POSITION_VALUES,chest_partition_value,waist_partition_value
JOINT_BLEND_WIDTHS={'shoulder':.020,'elbow':.018,'wrist':.010,'hip':.025,'knee':.018,'ankle':.014}

def smooth_joint_factor(signed_distance_value,blend_width_value):
 normalized_factor_value=float(np.clip(.5+signed_distance_value/(2*blend_width_value),0,1))
 return normalized_factor_value**2*(3-2*normalized_factor_value)
def apply_surface_weights(rigid_part_records,rig_object_value):
 for part_object_value,default_bone_name,part_kind_value in rigid_part_records:
  part_object_value.vertex_groups.clear()
  weight_group_records={bone_record_value.name:part_object_value.vertex_groups.new(name=bone_record_value.name) for bone_record_value in rig_object_value.data.bones}
  for vertex_record_value in part_object_value.data.vertices:
   vertex_point_value=vertex_record_value.co
   selected_weight_values={default_bone_name:1.0}
   if part_kind_value=='shell':
    side_sign_value=1 if vertex_point_value.x>=0 else -1
    side_name_value='left' if side_sign_value>0 else 'right'
    thigh_bone_name='joint-04' if side_sign_value>0 else 'joint-05';shin_bone_name='joint-07' if side_sign_value>0 else 'joint-08';foot_bone_name='joint-10' if side_sign_value>0 else 'joint-11'
    arm_bone_name='joint-18' if side_sign_value>0 else 'joint-19';forearm_bone_name='joint-20' if side_sign_value>0 else 'joint-21';hand_bone_name='hand-20-deform' if side_sign_value>0 else 'hand-21-deform'
    joint_binding_records=[
     ('shoulder','chest-shell-part',side_name_value+'-upper-arm-shell','joint-09',arm_bone_name,Vector((side_sign_value*.046,.004,-.255)),.091),
     ('elbow',side_name_value+'-upper-arm-shell',side_name_value+'-forearm-shell',arm_bone_name,forearm_bone_name,Vector((side_sign_value*.078,-.05,-.27)),.075),
     ('wrist',side_name_value+'-forearm-shell',side_name_value+'-hand-shell',forearm_bone_name,hand_bone_name,Vector((side_sign_value*.01,-.01,-.12)),.065),
     ('hip','pelvis-shell-part',side_name_value+'-thigh-shell','body-root-control',thigh_bone_name,Vector((side_sign_value*.002,.032,-.455)),.155),
     ('knee',side_name_value+'-thigh-shell',side_name_value+'-shin-shell',thigh_bone_name,shin_bone_name,Vector((side_sign_value*.005,.033,-.38)),.10),
     ('ankle',side_name_value+'-shin-shell',side_name_value+'-foot-shell',shin_bone_name,foot_bone_name,Vector((0,0,-1)),.13)]
    for joint_name_value,parent_part_name,child_part_name,parent_bone_name,child_bone_name,joint_axis_vector,radial_limit_value in joint_binding_records:
     if part_object_value.name not in [parent_part_name,child_part_name]:continue
     if joint_name_value=='hip':continue
     center_record_values=JOINT_POSITION_VALUES[joint_name_value]
     center_point_vector=Vector((side_sign_value*center_record_values[0],center_record_values[1],center_record_values[2]))
     joint_axis_vector.normalize();joint_offset_vector=vertex_point_value-center_point_vector
     axis_distance_value=joint_offset_vector.dot(joint_axis_vector)
     radial_distance_value=(joint_offset_vector-joint_axis_vector*axis_distance_value).length
     if radial_distance_value>radial_limit_value:continue
     if abs(axis_distance_value)>.16:continue
     distal_weight_value=smooth_joint_factor(axis_distance_value,JOINT_BLEND_WIDTHS[joint_name_value])
     selected_weight_values={parent_bone_name:1-distal_weight_value,child_bone_name:distal_weight_value}
    for parent_part_name,child_part_name,parent_bone_name,child_bone_name,boundary_function_value,blend_width_value in [
     ('pelvis-shell-part','abdomen-shell-part','body-root-control','joint-06',waist_partition_value,.026),
     ('abdomen-shell-part','chest-shell-part','joint-06','joint-09',chest_partition_value,.035)]:
     if part_object_value.name in [parent_part_name,child_part_name]:
      boundary_distance_value=boundary_function_value(vertex_point_value)
      if abs(boundary_distance_value)<blend_width_value:
       distal_weight_value=smooth_joint_factor(boundary_distance_value,blend_width_value)
       selected_weight_values={parent_bone_name:1-distal_weight_value,child_bone_name:distal_weight_value}
   for bone_name_value,weight_scalar_value in selected_weight_values.items():
    if weight_scalar_value>1e-7:weight_group_records[bone_name_value].add([vertex_record_value.index],weight_scalar_value,'REPLACE')
  part_object_value.parent=rig_object_value
  armature_modifier_value=part_object_value.modifiers.new('localized-surface-skin','ARMATURE');armature_modifier_value.object=rig_object_value
  part_object_value['rigid_bone_name']=default_bone_name;part_object_value['part_kind']=part_kind_value
