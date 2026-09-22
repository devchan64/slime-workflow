"""원본 안와 표면을 따르는 얕은 눈 렌즈와 눈썹을 머리 메시로 합친다."""
import bpy,math
from mathutils import Vector
EYE_CENTER_WIDTH=.070
EYE_CENTER_HEIGHT=1.735
EYE_OUTLINE_WIDTH=.037
EYE_OUTLINE_HEIGHT=.020
EYE_RING_SEGMENTS=48
EYE_RADIAL_RINGS=6

def create_face_material(material_name_value,color_channel_values,roughness_scalar_value):
 material_record_value=bpy.data.materials.new(material_name_value);material_record_value.diffuse_color=(*color_channel_values,1);material_record_value.use_nodes=True
 shader_record_value=material_record_value.node_tree.nodes.get('Principled BSDF')
 shader_record_value.inputs['Base Color'].default_value=(*color_channel_values,1);shader_record_value.inputs['Roughness'].default_value=roughness_scalar_value
 return material_record_value

def append_eye_details(head_shell_object):
 white_material_value=create_face_material('warm-eye-sclera',(.76,.74,.67),.25)
 iris_material_value=create_face_material('charcoal-olive-iris',(.055,.060,.043),.24)
 pupil_material_value=create_face_material('deep-pupil',(.008,.009,.007),.20)
 brow_material_value=create_face_material('soft-taupe-eyebrow',(.17,.14,.105),.62)
 attached_face_objects=[head_shell_object]
 for side_sign_value in [-1,1]:
  def read_face_depth(horizontal_scalar_value,height_scalar_value):
   hit_result_value,hit_point_value,_,_=head_shell_object.ray_cast(Vector((horizontal_scalar_value,-1,height_scalar_value)),Vector((0,1,0)))
   if not hit_result_value:raise ValueError('눈 표면의 원본 안와 교차 없음')
   return hit_point_value.y
  def eye_surface_depth(horizontal_scalar_value,height_scalar_value):
   radial_scalar_value=min(1,((horizontal_scalar_value-side_sign_value*EYE_CENTER_WIDTH)/EYE_OUTLINE_WIDTH)**2+((height_scalar_value-EYE_CENTER_HEIGHT)/EYE_OUTLINE_HEIGHT)**2)
   return -.151-.70*(height_scalar_value-EYE_CENTER_HEIGHT)+.35*(abs(horizontal_scalar_value)-EYE_CENTER_WIDTH)-.013*(1-radial_scalar_value)
  for detail_name_value,detail_width_value,detail_height_value,depth_offset_value,detail_material_value in [('sclera',EYE_OUTLINE_WIDTH,EYE_OUTLINE_HEIGHT,0,white_material_value),('iris',.014,.018,.0009,iris_material_value),('pupil',.008,.0115,.0015,pupil_material_value)]:
   vertex_point_values=[(side_sign_value*EYE_CENTER_WIDTH,eye_surface_depth(side_sign_value*EYE_CENTER_WIDTH,EYE_CENTER_HEIGHT)-depth_offset_value,EYE_CENTER_HEIGHT)];polygon_index_values=[]
   for ring_index_value in range(1,EYE_RADIAL_RINGS+1):
    radius_ratio_value=ring_index_value/EYE_RADIAL_RINGS
    for angle_index_value in range(EYE_RING_SEGMENTS):
     angle_scalar_value=2*math.pi*angle_index_value/EYE_RING_SEGMENTS
     horizontal_scalar_value=side_sign_value*EYE_CENTER_WIDTH+detail_width_value*radius_ratio_value*math.cos(angle_scalar_value)
     height_scalar_value=EYE_CENTER_HEIGHT+detail_height_value*radius_ratio_value*math.sin(angle_scalar_value)*(1 if detail_name_value!='sclera' else .70+.30*abs(math.sin(angle_scalar_value)))
     vertex_point_values.append((horizontal_scalar_value,eye_surface_depth(horizontal_scalar_value,height_scalar_value)-depth_offset_value,height_scalar_value))
   for angle_index_value in range(EYE_RING_SEGMENTS):
    polygon_index_values.append((0,1+angle_index_value,1+(angle_index_value+1)%EYE_RING_SEGMENTS))
   for ring_index_value in range(EYE_RADIAL_RINGS-1):
    for angle_index_value in range(EYE_RING_SEGMENTS):
     next_angle_index=(angle_index_value+1)%EYE_RING_SEGMENTS
     polygon_index_values.append((1+ring_index_value*EYE_RING_SEGMENTS+angle_index_value,1+ring_index_value*EYE_RING_SEGMENTS+next_angle_index,1+(ring_index_value+1)*EYE_RING_SEGMENTS+next_angle_index,1+(ring_index_value+1)*EYE_RING_SEGMENTS+angle_index_value))
   detail_mesh_value=bpy.data.meshes.new(detail_name_value);detail_mesh_value.from_pydata(vertex_point_values,[],polygon_index_values);detail_mesh_value.materials.append(detail_material_value)
   detail_object_value=bpy.data.objects.new(f'{detail_name_value}-{side_sign_value}',detail_mesh_value);bpy.context.scene.collection.objects.link(detail_object_value)
   for polygon_record_value in detail_mesh_value.polygons:polygon_record_value.use_smooth=True
   attached_face_objects.append(detail_object_value)
  brow_vertex_points=[];brow_polygon_indices=[]
  for sample_index_value in range(25):
   horizontal_ratio_value=sample_index_value/24
   horizontal_scalar_value=side_sign_value*(.033+.075*horizontal_ratio_value)
   height_scalar_value=1.786+.009*math.sin(math.pi*horizontal_ratio_value)-.003*horizontal_ratio_value
   ribbon_half_width=.001+.002*math.sin(math.pi*horizontal_ratio_value)
   for ribbon_side_value in [-1,1]:
    ribbon_height_value=height_scalar_value+ribbon_side_value*ribbon_half_width
    brow_vertex_points.append((horizontal_scalar_value,read_face_depth(horizontal_scalar_value,ribbon_height_value)-.0015,ribbon_height_value))
   if sample_index_value:brow_polygon_indices.append((2*sample_index_value-2,2*sample_index_value-1,2*sample_index_value+1,2*sample_index_value))
  brow_mesh_value=bpy.data.meshes.new('eyebrow-ribbon');brow_mesh_value.from_pydata(brow_vertex_points,[],brow_polygon_indices);brow_mesh_value.materials.append(brow_material_value)
  brow_object_value=bpy.data.objects.new(f'eyebrow-{side_sign_value}',brow_mesh_value);bpy.context.scene.collection.objects.link(brow_object_value);attached_face_objects.append(brow_object_value)
 bpy.ops.object.select_all(action='DESELECT')
 for detail_object_value in attached_face_objects:detail_object_value.select_set(True)
 bpy.context.view_layer.objects.active=head_shell_object;bpy.ops.object.join()
