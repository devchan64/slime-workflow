from pathlib import Path
import bpy,numpy as np,json
from mathutils.kdtree import KDTree
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'anny-reference-fit-rig.blend'))
reference_frame_arrays={}
for current_frame_number in [1,7,13,19,25]:
 bpy.context.scene.frame_set(current_frame_number);bpy.context.view_layer.update()
 current_mesh_object=bpy.data.objects['AnnyAttributesBody'].evaluated_get(bpy.context.evaluated_depsgraph_get())
 reference_frame_arrays[current_frame_number]=np.array([(current_mesh_object.matrix_world@current_vertex_value.co)[:] for current_vertex_value in current_mesh_object.data.vertices])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps=24
bpy.ops.import_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'anny-reference-fit-rig.glb'))
roundtrip_frame_errors={}
for current_frame_number,reference_vertex_array in reference_frame_arrays.items():
 bpy.context.scene.frame_set(current_frame_number);bpy.context.view_layer.update()
 imported_vertex_values=[]
 for current_mesh_object in bpy.context.scene.objects:
  if current_mesh_object.type!='MESH' or not any(current_modifier_value.type=='ARMATURE' for current_modifier_value in current_mesh_object.modifiers): continue
  current_evaluated_object=current_mesh_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
  imported_vertex_values.extend([(current_evaluated_object.matrix_world@current_vertex_value.co)[:] for current_vertex_value in current_evaluated_object.data.vertices])
 reference_vertex_tree=KDTree(len(reference_vertex_array))
 for current_vertex_index,current_vertex_value in enumerate(reference_vertex_array):reference_vertex_tree.insert(current_vertex_value,current_vertex_index)
 reference_vertex_tree.balance()
 print('bounds',current_frame_number,reference_vertex_array.min(0),reference_vertex_array.max(0),np.min(imported_vertex_values,axis=0),np.max(imported_vertex_values,axis=0),flush=True)
 current_maximum_error=max(reference_vertex_tree.find(current_vertex_value)[2] for current_vertex_value in imported_vertex_values)
 roundtrip_frame_errors[current_frame_number]=current_maximum_error
 if current_maximum_error>1e-4:raise ValueError(f'GLB roundtrip mismatch frame={current_frame_number} error={current_maximum_error}')
validation_result_record={'status':'passed','frame_max_errors':roundtrip_frame_errors,'tolerance':1e-4,'method':'GLB 재수입 후 5개 자세의 모든 정점과 원본 Blender 표면 정점 사이 최근접 거리'}
(EXPERIMENT_OUTPUT_ROOT/'roundtrip-validation.json').write_text(json.dumps(validation_result_record,ensure_ascii=False,indent=2))
print(validation_result_record)
