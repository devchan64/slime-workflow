"""3방향 레퍼런스에 맞춰 실루엣을 조정한다. 생성 원본은 보존한다."""
from pathlib import Path
import bpy, numpy as np, json, time
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
HEIGHT_PROFILE_VALUES=np.array([0,.15,.30,.40,.53,.70,.85,.985,1.1,1.2,1.3,1.435,1.5,1.565,1.70,1.85,2.0])
TORSO_WIDTH_SCALES=np.array([1,1,1,1,1,1,1,.97,.94,.92,.95,.96,.92,1,.96,.94,.95])

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/reference-sculpt/{stage_name_value} {message_text_value}',flush=True)

def smooth_interval_factor(coordinate_scalar_value,minimum_scalar_value,maximum_scalar_value):
 normalized_scalar_value=float(np.clip((coordinate_scalar_value-minimum_scalar_value)/(maximum_scalar_value-minimum_scalar_value),0,1))
 return normalized_scalar_value**2*(3-2*normalized_scalar_value)

write_trace_message('start','입력=inputs/accepted-mannequin.blend, 출력=sculpted-source.blend')
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'inputs/accepted-mannequin.blend'))
source_model_object=bpy.data.objects['reference-mannequin-multiview']
maximum_displacement_value=0.0
for vertex_record_value in source_model_object.data.vertices:
 original_point_value=vertex_record_value.co.copy()
 horizontal_scalar_value,depth_scalar_value,height_scalar_value=original_point_value
 side_sign_value=1 if horizontal_scalar_value>=0 else -1
 absolute_width_value=abs(horizontal_scalar_value)
 arm_boundary_value=.154+.21*max(1.32-height_scalar_value,0)
 if height_scalar_value>=1.565:
  vertex_record_value.co.x*=float(np.interp(height_scalar_value,HEIGHT_PROFILE_VALUES,TORSO_WIDTH_SCALES))
 elif absolute_width_value>arm_boundary_value and height_scalar_value>.72:
  arm_center_width=float(np.interp(height_scalar_value,[.72,.91,1.18,1.435,1.565],[.324,.310,.229,.187,.170]))
  arm_shift_value=float(np.interp(height_scalar_value,[.72,.91,1.18,1.435,1.565],[.016,.017,.015,.008,0]))
  vertex_record_value.co.x=side_sign_value*(arm_center_width-arm_shift_value+(absolute_width_value-arm_center_width)*.93)
  vertex_record_value.co.y=.020+(depth_scalar_value-.020)*.95
 elif height_scalar_value<.985:
  leg_blend_value=1-smooth_interval_factor(height_scalar_value,.84,.985)
  leg_center_width=float(np.interp(height_scalar_value,[0,.15,.53,.85,.985],[.110,.110,.105,.103,.103]))
  leg_scale_value=float(np.interp(height_scalar_value,[0,.15,.30,.40,.53,.70,.85,.985],[1,.96,.88,.87,.94,.94,.95,1]))
  vertex_record_value.co.x=side_sign_value*(leg_center_width+.006*leg_blend_value+(absolute_width_value-leg_center_width)*leg_scale_value)
  calf_depth_factor=1-.045*np.exp(-((height_scalar_value-.38)/.17)**2)
  vertex_record_value.co.y=.030+(depth_scalar_value-.030)*calf_depth_factor
 else:
  vertex_record_value.co.x*=float(np.interp(height_scalar_value,HEIGHT_PROFILE_VALUES,TORSO_WIDTH_SCALES))
  # 좌우 흉부의 과도한 돌출과 복부 깊은 굴곡을 완만하게 다듬는다.
  chest_front_weight=np.exp(-((height_scalar_value-1.355)/.105)**2)*np.exp(-((absolute_width_value-.067)/.055)**2)
  if depth_scalar_value<-.035:vertex_record_value.co.y+=.012*chest_front_weight
  if depth_scalar_value>0:
   vertex_record_value.co.y-=.007*np.exp(-((height_scalar_value-1.125)/.10)**2)
 maximum_displacement_value=max(maximum_displacement_value,(vertex_record_value.co-original_point_value).length)
source_model_object.data.update()
# 기존 생성 메시가 새 관절 아래에 남긴 중복 요철을 완만하게 정리한다.
smoothing_group_value=source_model_object.vertex_groups.new(name='joint-surface-cleanup')
for vertex_record_value in source_model_object.data.vertices:
 horizontal_scalar_value,depth_scalar_value,height_scalar_value=vertex_record_value.co
 absolute_width_value=abs(horizontal_scalar_value)
 smoothing_weight_value=0.0
 if absolute_width_value<.20 and .88<height_scalar_value<1.14:smoothing_weight_value=.9
 if absolute_width_value<.19 and .47<height_scalar_value<.66:smoothing_weight_value=1.0
 if absolute_width_value>.17 and 1.09<height_scalar_value<1.25:smoothing_weight_value=.7
 if absolute_width_value<.15 and 1.20<height_scalar_value<1.43:smoothing_weight_value=max(smoothing_weight_value,.4)
 if smoothing_weight_value:smoothing_group_value.add([vertex_record_value.index],smoothing_weight_value,'REPLACE')
bpy.context.view_layer.objects.active=source_model_object
smoothing_modifier_value=source_model_object.modifiers.new('remove-duplicated-joint-bulges','SMOOTH')
smoothing_modifier_value.vertex_group=smoothing_group_value.name;smoothing_modifier_value.factor=.6;smoothing_modifier_value.iterations=10
bpy.ops.object.modifier_apply(modifier=smoothing_modifier_value.name)
source_model_object.vertex_groups.clear()
source_model_object.data.update()
# 균일한 아이보리 소재와 넓은 광택으로 조형의 음영을 읽는다.
material_source_value=source_model_object.data.materials[0]
material_source_value.use_nodes=True
shader_source_value=material_source_value.node_tree.nodes.get('Principled BSDF')
shader_source_value.inputs['Base Color'].default_value=(.66,.605,.52,1)
shader_source_value.inputs['Roughness'].default_value=.36
bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'sculpted-source.blend'))
(EXPERIMENT_OUTPUT_ROOT/'sculpt-result.json').write_text(json.dumps({'status':'sculpted','vertices':len(source_model_object.data.vertices),'max_displacement':maximum_displacement_value,'method':'reference-guided local width/depth profiles; no inferred design-similarity claim'},indent=2))
write_trace_message('complete',f'최대 정점 이동={maximum_displacement_value:.6f}')
