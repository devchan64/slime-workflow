"""Hunyuan3D 메시를 Blender에 가져와 형태 검수용 뷰를 렌더한다."""
from pathlib import Path
import bpy,numpy as np,json,threading,time,traceback
from mathutils import Vector
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent/'model-review'
INPUT_MODEL_PATH=EXPERIMENT_OUTPUT_ROOT.parent/'hunyuan-mannequin-raw.glb'
VIEW_CAMERA_POINTS={'front':(0,-6,1),'side':(6,0,1),'back':(0,6,1),'three-quarter':(4,-6,2.3),'face-front':(0,-6,1.78),'face-side':(6,0,1.78)}
CURRENT_STAGE_RECORD={'stage':'load'}
HEARTBEAT_STOP_EVENT=threading.Event()
BODY_TARGET_HEIGHT=2.0
HEAD_TARGET_HEIGHT=.4
CHIN_HEIGHT_FRACTION=.8096

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/hunyuan-render/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))

def execute_model_render():
 EXPERIMENT_OUTPUT_ROOT.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(INPUT_MODEL_PATH))
 selected_mesh_objects=[scene_mesh_object for scene_mesh_object in bpy.context.scene.objects if scene_mesh_object.type=='MESH']
 if not selected_mesh_objects:raise ValueError('가져온 메시 없음')
 bpy.ops.object.select_all(action='DESELECT')
 for scene_mesh_object in selected_mesh_objects:scene_mesh_object.select_set(True)
 bpy.context.view_layer.objects.active=selected_mesh_objects[0]
 bpy.ops.object.join()
 model_mesh_object=bpy.context.object
 model_mesh_object.name='reference-mannequin-multiview'
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 model_vertex_points=np.array([model_vertex_value.co[:] for model_vertex_value in model_mesh_object.data.vertices])
 model_minimum_point=model_vertex_points.min(axis=0)
 model_maximum_point=model_vertex_points.max(axis=0)
 model_height_value=model_maximum_point[2]-model_minimum_point[2]
 if model_height_value<max(model_maximum_point[:2]-model_minimum_point[:2]):raise ValueError('입력 메시 세로축 불일치')
 # 원본 다중 시점 비율을 유지하며 전체 높이만 정규화한다.
 uniform_scale_value=BODY_TARGET_HEIGHT/model_height_value
 model_vertex_points[:,0]-=(model_minimum_point[0]+model_maximum_point[0])/2
 model_vertex_points[:,1]-=(model_minimum_point[1]+model_maximum_point[1])/2
 model_vertex_points[:,2]-=model_minimum_point[2]
 model_vertex_points*=uniform_scale_value
 for model_vertex_value,model_vertex_point in zip(model_mesh_object.data.vertices,model_vertex_points):model_vertex_value.co=model_vertex_point
 for mesh_polygon_value in model_mesh_object.data.polygons:mesh_polygon_value.use_smooth=True
 # 새 생성 고해상도 형상은 따로 보관하고 전달 후보는 3만 삼각형으로 정리한다.
 source_triangle_count=sum(len(polygon_record_value.vertices)-2 for polygon_record_value in model_mesh_object.data.polygons)
 bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'normalized-high.glb'),use_selection=True,export_format='GLB')
 triangle_decimate_modifier=model_mesh_object.modifiers.new('thirty-thousand-triangles','DECIMATE');triangle_decimate_modifier.ratio=30000/source_triangle_count;triangle_decimate_modifier.use_collapse_triangulate=True
 bpy.ops.object.modifier_apply(modifier=triangle_decimate_modifier.name)
 model_surface_material=bpy.data.materials.new('warm-ivory-mannequin')
 model_surface_material.diffuse_color=(.64,.57,.47,1)
 model_surface_material.use_nodes=True
 model_shader_node=model_surface_material.node_tree.nodes.get('Principled BSDF')
 model_shader_node.inputs['Base Color'].default_value=(.64,.57,.47,1)
 model_shader_node.inputs['Roughness'].default_value=.47
 model_mesh_object.data.materials.clear();model_mesh_object.data.materials.append(model_surface_material)
 render_scene_value=bpy.context.scene
 render_scene_value.render.engine='CYCLES'
 device_preferences_value=bpy.context.preferences.addons['cycles'].preferences
 device_preferences_value.compute_device_type='CUDA';device_preferences_value.get_devices()
 gpu_device_values=[device_record_value for device_record_value in device_preferences_value.devices if device_record_value.type=='CUDA']
 if not gpu_device_values:raise RuntimeError('샌드박스 밖 CUDA 렌더 장치 없음')
 for device_record_value in device_preferences_value.devices:device_record_value.use=device_record_value.type=='CUDA'
 render_scene_value.cycles.device='GPU';render_scene_value.cycles.samples=48
 render_scene_value.render.resolution_x=768;render_scene_value.render.resolution_y=768
 render_scene_value.render.resolution_percentage=100
 render_scene_value.render.film_transparent=False
 render_scene_value.world=bpy.data.worlds.new('review-world');render_scene_value.world.use_nodes=True
 render_scene_value.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.18,1)
 render_scene_value.world.node_tree.nodes['Background'].inputs[1].default_value=.5
 render_scene_value.view_settings.view_transform='AgX'
 bpy.ops.object.camera_add(location=(0,-6,1))
 camera_object_value=bpy.context.object;camera_object_value.data.type='ORTHO';camera_object_value.data.ortho_scale=2.30
 render_scene_value.camera=camera_object_value
 scene_light_objects=[]
 for light_name_value,light_power_value in [('key',550),('fill',250)]:
  light_data_value=bpy.data.lights.new(light_name_value,'AREA');light_data_value.energy=light_power_value;light_data_value.shape='DISK';light_data_value.size=3
  light_object_value=bpy.data.objects.new(light_name_value,light_data_value);render_scene_value.collection.objects.link(light_object_value);scene_light_objects.append(light_object_value)
 for view_name_value,camera_point_values in VIEW_CAMERA_POINTS.items():
  CURRENT_STAGE_RECORD.update(stage=view_name_value)
  camera_target_vector=Vector((0,0,1.78 if view_name_value.startswith('face-') else 1))
  camera_object_value.data.ortho_scale=.6 if view_name_value.startswith('face-') else 2.30
  camera_object_value.location=camera_point_values
  camera_object_value.rotation_euler=(camera_target_vector-camera_object_value.location).to_track_quat('-Z','Y').to_euler()
  camera_right_vector=camera_object_value.rotation_euler.to_quaternion()@Vector((1,0,0))
  camera_front_vector=(camera_object_value.location-camera_target_vector).normalized()
  for light_object_value,light_side_value in zip(scene_light_objects,[-1,1]):
   light_object_value.location=camera_target_vector+camera_front_vector*3+camera_right_vector*light_side_value*3+Vector((0,0,3))
   light_object_value.rotation_euler=(camera_target_vector-light_object_value.location).to_track_quat('-Z','Y').to_euler()
  render_scene_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}.png')
  if view_name_value=='front':
   bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.blend'))
   bpy.ops.object.select_all(action='DESELECT');model_mesh_object.select_set(True);bpy.context.view_layer.objects.active=model_mesh_object
   bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT/'mannequin.glb'),use_selection=True,export_format='GLB')
  bpy.ops.render.render(write_still=True)
 result_record_value={'status':'candidate_review','rigged':False,'input':str(INPUT_MODEL_PATH),'target_height':BODY_TARGET_HEIGHT,'proportion_method':'생성 결과의 원래 비율 유지, 전체 균일 스케일만 적용','uniform_scale':uniform_scale_value,'source_triangles':source_triangle_count,'vertices':len(model_mesh_object.data.vertices),'faces':len(model_mesh_object.data.polygons)}
 (EXPERIMENT_OUTPUT_ROOT/'render-result.json').write_text(json.dumps(result_record_value,ensure_ascii=False,indent=2))
 write_trace_message('complete',str(result_record_value))
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:execute_model_render()
except Exception:write_trace_message('failure',traceback.format_exc());raise
finally:HEARTBEAT_STOP_EVENT.set()
