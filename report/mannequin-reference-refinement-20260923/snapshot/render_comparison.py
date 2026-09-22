"""세 모델을 동일 정사영 조건으로 렌더해 외곽 보존을 비교한다."""
from pathlib import Path
import bpy,time,threading,traceback
from mathutils import Vector
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
MODEL_COMPARISON_PATHS={'baseline':EXPERIMENT_OUTPUT_ROOT/'inputs/baseline-rigged.blend','refined':EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.blend'}
VIEW_CAMERA_POSITIONS={'front':(0,-6,1),'side':(6,0,1),'back':(0,6,1)}
HEARTBEAT_STOP_EVENT=threading.Event();CURRENT_STAGE_RECORD={'stage':'load'}
def write_trace_message(stage_name_value,message_text_value):print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/shape-comparison/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:
 for model_name_value,model_path_value in MODEL_COMPARISON_PATHS.items():
  bpy.ops.wm.open_mainfile(filepath=str(model_path_value));render_scene_value=bpy.context.scene
  for scene_object_value in bpy.data.objects:
   if scene_object_value.type=='ARMATURE':scene_object_value.animation_data_clear();scene_object_value.data.pose_position='REST';scene_object_value.location=(0,0,0)
  render_scene_value.render.film_transparent=True;render_scene_value.render.image_settings.color_mode='RGBA'
  render_scene_value.render.resolution_x=768;render_scene_value.render.resolution_y=768;render_scene_value.render.resolution_percentage=100
  render_scene_value.cycles.samples=32;render_scene_value.camera.data.ortho_scale=2.4
  device_preference_values=bpy.context.preferences.addons['cycles'].preferences;device_preference_values.compute_device_type='CUDA';device_preference_values.get_devices()
  if not any(device_record_value.type=='CUDA' for device_record_value in device_preference_values.devices):raise RuntimeError('CUDA 렌더 장치 없음')
  for device_record_value in device_preference_values.devices:device_record_value.use=device_record_value.type=='CUDA'
  render_scene_value.cycles.device='GPU'
  for view_name_value,camera_point_values in VIEW_CAMERA_POSITIONS.items():
   CURRENT_STAGE_RECORD['stage']=model_name_value+'-'+view_name_value
   camera_target_vector=Vector((0,0,1));camera_object_value=render_scene_value.camera
   camera_object_value.location=camera_point_values;camera_object_value.rotation_euler=(camera_target_vector-camera_object_value.location).to_track_quat('-Z','Y').to_euler()
   camera_right_vector=camera_object_value.rotation_euler.to_quaternion()@Vector((1,0,0));camera_front_vector=(camera_object_value.location-camera_target_vector).normalized()
   for light_name_value,light_side_value in [('key',-1),('fill',1)]:
    light_object_value=bpy.data.objects[light_name_value];light_object_value.location=camera_target_vector+camera_front_vector*3+camera_right_vector*light_side_value*3+Vector((0,0,3));light_object_value.rotation_euler=(camera_target_vector-light_object_value.location).to_track_quat('-Z','Y').to_euler()
   render_scene_value.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'compare-{model_name_value}-{view_name_value}.png');bpy.ops.render.render(write_still=True)
 write_trace_message('complete','동일 조건 정면·측면·후면 렌더 완료')
except Exception:write_trace_message('failure',traceback.format_exc());raise
finally:HEARTBEAT_STOP_EVENT.set()
