"""관절 확대와 수동 굽힘 검수 이미지를 별도로 렌더한다."""
from pathlib import Path
import bpy,time,threading,traceback,math
from mathutils import Vector,Quaternion
EXPERIMENT_OUTPUT_ROOT=Path(__file__).resolve().parent
CURRENT_STAGE_RECORD={'stage':'load'}
HEARTBEAT_STOP_EVENT=threading.Event()

def write_trace_message(stage_name_value,message_text_value):
 print(f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/rig-details/{stage_name_value} {message_text_value}',flush=True)
def emit_progress_heartbeat():
 while not HEARTBEAT_STOP_EVENT.wait(5):write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))
def render_detail_view(view_name_value,target_point_values,camera_offset_values,ortho_scale_value):
 CURRENT_STAGE_RECORD['stage']=view_name_value
 camera_target_vector=Vector(target_point_values)
 camera_object_value=bpy.context.scene.camera;camera_object_value.location=camera_target_vector+Vector(camera_offset_values)
 camera_object_value.rotation_euler=(camera_target_vector-camera_object_value.location).to_track_quat('-Z','Y').to_euler();camera_object_value.data.ortho_scale=ortho_scale_value
 camera_right_vector=camera_object_value.rotation_euler.to_quaternion()@Vector((1,0,0));camera_front_vector=(camera_object_value.location-camera_target_vector).normalized()
 for light_name_value,light_side_value in [('key',-1),('fill',1)]:
  light_object_value=bpy.data.objects[light_name_value];light_object_value.location=camera_target_vector+camera_front_vector*3+camera_right_vector*light_side_value*3+Vector((0,0,3));light_object_value.rotation_euler=(camera_target_vector-light_object_value.location).to_track_quat('-Z','Y').to_euler()
 bpy.context.scene.render.filepath=str(EXPERIMENT_OUTPUT_ROOT/f'{view_name_value}.png');bpy.ops.render.render(write_still=True)
threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
try:
 bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT/'rigged-mannequin.blend'))
 rig_object_value=bpy.data.objects['multiview-ball-joint-rig'];rig_object_value.animation_data_clear();rig_object_value.location=(0,0,0);rig_object_value.data.pose_position='REST'
 bpy.context.scene.cycles.samples=32
 device_preference_values=bpy.context.preferences.addons['cycles'].preferences;device_preference_values.compute_device_type='CUDA';device_preference_values.get_devices()
 if not any(device_record_value.type=='CUDA' for device_record_value in device_preference_values.devices):raise RuntimeError('CUDA 렌더 장치 없음')
 for device_record_value in device_preference_values.devices:device_record_value.use=device_record_value.type=='CUDA'
 bpy.context.scene.cycles.device='GPU'
 render_detail_view('detail-shoulder',(0.17,0,1.40),(3,-6,1),.48)
 render_detail_view('detail-hip',(0,0,.985),(3,-6,1),.62)
 render_detail_view('detail-knee',(.105,.02,.53),(3,-6,1),.40)
 render_detail_view('detail-ankle',(.11,.02,.15),(3,-6,1),.37)
 rig_object_value.data.pose_position='POSE'
 for pose_bone_value in rig_object_value.pose.bones:
  pose_bone_value.location=(0,0,0);pose_bone_value.rotation_mode='QUATERNION';pose_bone_value.rotation_quaternion=(1,0,0,0);pose_bone_value.scale=(1,1,1)
 for bone_name_value,rotation_angle_value in [('joint-18',-.6),('joint-20',-1.05),('joint-04',-.6),('joint-07',1.05)]:
  rig_object_value.pose.bones[bone_name_value].rotation_quaternion=Quaternion(Vector((1,0,0)),rotation_angle_value)
 bpy.context.view_layer.update()
 render_detail_view('stress-bend-front',(0,0,1),(4,-6,1),2.4)
 render_detail_view('stress-bend-side',(0,0,1),(6,0,0),2.4)
 write_trace_message('complete','관절 확대 및 수동 굽힘 검수 렌더 완료')
except Exception:write_trace_message('failure',traceback.format_exc());raise
finally:HEARTBEAT_STOP_EVENT.set()
