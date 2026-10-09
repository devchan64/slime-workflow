"""ANNY 모션을 프레임 공통 카메라로 CUDA 렌더하여 VNCCS PNG를 출력한다."""
from pathlib import Path
import json
import math
import threading
import time
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

CURRENT_STAGE_RECORD = globals()['export_stage_request']
CURRENT_OUTPUT_DIRECTORY = Path(CURRENT_STAGE_RECORD['export_directory'])
CURRENT_CONFIG_RECORD = CURRENT_STAGE_RECORD['config']
CURRENT_REQUEST_RECORD = CURRENT_STAGE_RECORD['request']
CURRENT_RENDER_PROGRESS = {'stage': 'prepare'}
CURRENT_LIGHT_POSITIONS = ((-3, -4, 4), (3, 4, 4))
CURRENT_SAMPLE_FRAMES = tuple(range(CURRENT_REQUEST_RECORD['start_frame'], CURRENT_REQUEST_RECORD['end_frame'] + 1, CURRENT_REQUEST_RECORD['frame_step']))
CURRENT_COCO_BONES = ('neck01', 'upperarm01.R', 'lowerarm01.R', 'wrist.R', 'upperarm01.L', 'lowerarm01.L', 'wrist.L', 'upperleg01.R', 'lowerleg01.R', 'foot.R', 'upperleg01.L', 'lowerleg01.L', 'foot.L')


def emit_render_heartbeat():
    while True:
        print(f'{time.strftime("%FT%T")}/vnccs-render/heartbeat {CURRENT_RENDER_PROGRESS}', flush=True)
        time.sleep(5)


threading.Thread(target=emit_render_heartbeat, daemon=True).start()
if 'prepared_body_object' not in globals():
    bpy.ops.wm.open_mainfile(filepath=str(Path(CURRENT_STAGE_RECORD['output_directory']) / ('rotation/full_rotation/mannequin.blend' if CURRENT_STAGE_RECORD.get('constraint_comparison_disabled') else 'final/barrier/mannequin.blend')))
current_render_scene = bpy.context.scene
current_body_object = globals()['prepared_body_object'] if 'prepared_body_object' in globals() else bpy.data.objects['AnnyAttributesBody']
current_rig_object = bpy.data.objects['AnnyAttributesRig']
current_render_scene.render.engine = 'CYCLES'
current_device_preferences = bpy.context.preferences.addons['cycles'].preferences
current_device_preferences.compute_device_type = 'CUDA'
current_device_preferences.get_devices()
if not any(current_device_record.type == 'CUDA' for current_device_record in current_device_preferences.devices):
    raise RuntimeError('VNCCS 렌더에 CUDA GPU가 필요합니다. CPU 대체 없음')
for current_device_record in current_device_preferences.devices:
    current_device_record.use = current_device_record.type == 'CUDA'
current_render_scene.cycles.device = 'GPU'
current_render_scene.cycles.samples = CURRENT_CONFIG_RECORD['samples']
current_render_scene.cycles.use_denoising = True
current_render_scene.render.resolution_x = CURRENT_CONFIG_RECORD['resolution']
current_render_scene.render.resolution_y = CURRENT_CONFIG_RECORD['resolution']
current_render_scene.render.resolution_percentage = 100
current_render_scene.render.image_settings.file_format = 'PNG'
current_render_scene.render.image_settings.color_mode = 'RGBA'
current_render_scene.render.film_transparent = True
current_render_scene.world.use_nodes = True
current_render_scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.8, .8, .8, 1)
current_render_scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .4
current_render_scene.view_settings.view_transform = 'AgX'
for current_scene_object in list(bpy.data.objects):
    if current_scene_object.type == 'MESH' and current_scene_object != current_body_object:
        current_scene_object.hide_render = True
    if current_scene_object.type == 'LIGHT':
        bpy.data.objects.remove(current_scene_object, do_unlink=True)
for current_light_position in CURRENT_LIGHT_POSITIONS:
    bpy.ops.object.light_add(type='AREA', location=current_light_position)
    bpy.context.object.data.energy = 400
    bpy.context.object.data.size = 3
    bpy.context.object.rotation_euler = (Vector((0, 0, 1)) - bpy.context.object.location).to_track_quat('-Z', 'Y').to_euler()
current_camera_axes = {}
for current_direction_name in CURRENT_REQUEST_RECORD['directions']:
    current_angle_radians = math.radians(CURRENT_CONFIG_RECORD['camera_angles'][current_direction_name])
    current_elevation_radians = math.radians(CURRENT_CONFIG_RECORD['camera_elevation'])
    current_camera_normal = Vector((math.sin(current_angle_radians) * math.cos(current_elevation_radians), -math.cos(current_angle_radians) * math.cos(current_elevation_radians), math.sin(current_elevation_radians)))
    current_camera_rotation = (-current_camera_normal).to_track_quat('-Z', 'Y')
    current_camera_axes[current_direction_name] = (current_camera_normal, current_camera_rotation, current_camera_rotation @ Vector((1, 0, 0)), current_camera_rotation @ Vector((0, 1, 0)))
current_world_bounds = []
for current_frame_number in CURRENT_SAMPLE_FRAMES:
    CURRENT_RENDER_PROGRESS.update(stage='framing', frame=current_frame_number)
    current_render_scene.frame_set(current_frame_number)
    current_evaluated_object = current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
    current_world_bounds.extend(current_evaluated_object.matrix_world @ Vector(current_corner_point) for current_corner_point in current_evaluated_object.bound_box)
current_camera_center = Vector(tuple((min(current_point[current_axis_index] for current_point in current_world_bounds) + max(current_point[current_axis_index] for current_point in current_world_bounds)) / 2 for current_axis_index in range(3)))
current_projection_extent = max(abs((current_point - current_camera_center).dot(current_projection_axis)) for current_point in current_world_bounds for current_camera_record in current_camera_axes.values() for current_projection_axis in current_camera_record[2:])
current_camera_scale = 2 * current_projection_extent * CURRENT_CONFIG_RECORD['framing_margin']
if CURRENT_STAGE_RECORD.get('constraint_comparison_disabled'):
    current_reference_cameras = json.loads((CURRENT_OUTPUT_DIRECTORY.parent / 'render-manifest.json').read_text())['camera']
    current_reference_camera = current_reference_cameras[CURRENT_REQUEST_RECORD['directions'][0]]
    current_camera_center = Vector(current_reference_camera['target'])
    current_camera_scale = current_reference_camera['ortho_scale']
if not math.isfinite(current_camera_scale) or current_camera_scale <= 0:
    raise ValueError('VNCCS 카메라 프레이밍 크기 오류')
current_image_records = []
current_camera_records = {}
current_projection_cameras = {}
# 투영 지정이 없는 과거 저장 설정은 기존 정사영 출력만 재현한다.
current_projection_names = CURRENT_CONFIG_RECORD.get('projections', ['orthographic'])
for current_projection_name in current_projection_names:
    current_projection_cameras[current_projection_name] = {}
    current_camera_distance = 8
    current_render_scene.camera.data.type = 'ORTHO'
    current_render_scene.camera.data.ortho_scale = current_camera_scale
    if current_projection_name == 'perspective':
        current_field_radians = math.radians(CURRENT_CONFIG_RECORD['perspective_fov_degrees'])
        current_camera_distance = current_camera_scale / (2 * math.tan(current_field_radians / 2))
        current_render_scene.camera.data.type = 'PERSP'
        current_render_scene.camera.data.sensor_fit = 'HORIZONTAL'
        current_render_scene.camera.data.angle = current_field_radians
    elif current_projection_name != 'orthographic':
        raise ValueError('지원하지 않는 카메라 투영: ' + current_projection_name)
    for current_direction_name, (current_camera_normal, current_camera_rotation, _, _) in current_camera_axes.items():
        current_relative_directory = current_direction_name if current_projection_name == 'orthographic' else 'perspective/' + current_direction_name
        current_direction_directory = CURRENT_OUTPUT_DIRECTORY / current_relative_directory
        current_direction_directory.mkdir(parents=True, exist_ok=False)
        current_render_scene.camera.location = current_camera_center + current_camera_normal * current_camera_distance
        current_render_scene.camera.rotation_mode = 'QUATERNION'
        current_render_scene.camera.rotation_quaternion = current_camera_rotation
        current_camera_record = {'projection': current_projection_name, 'location': list(current_render_scene.camera.location), 'rotation_quaternion_wxyz': list(current_camera_rotation), 'ortho_scale': current_camera_scale, 'elevation_degrees': CURRENT_CONFIG_RECORD['camera_elevation'], 'azimuth_degrees': CURRENT_CONFIG_RECORD['camera_angles'][current_direction_name], 'target': list(current_camera_center), 'distance': current_camera_distance}
        if current_projection_name == 'perspective':
            current_camera_record['fov_degrees'] = CURRENT_CONFIG_RECORD['perspective_fov_degrees']
            current_camera_record['framing'] = 'orthographic-center-plane-equivalent'
        else:
            current_camera_records[current_direction_name] = current_camera_record
        current_projection_cameras[current_projection_name][current_direction_name] = current_camera_record
        for current_image_index, current_frame_number in enumerate(CURRENT_SAMPLE_FRAMES, 1):
            CURRENT_RENDER_PROGRESS.update(stage='render', projection=current_projection_name, direction=current_direction_name, frame=current_frame_number)
            current_render_scene.frame_set(current_frame_number)
            current_relative_path = current_relative_directory + f'/frame-{current_image_index:04d}.png'
            current_render_scene.render.filepath = str(CURRENT_OUTPUT_DIRECTORY / current_relative_path)
            bpy.ops.render.render(write_still=True)
            current_pose_keypoints = [[0., 0., 0.] for current_joint_index in range(18)]
            for current_joint_index, current_bone_name in enumerate(CURRENT_COCO_BONES, 1):
                current_world_point = current_rig_object.matrix_world @ current_rig_object.pose.bones[current_bone_name].head
                current_projected_point = world_to_camera_view(current_render_scene, current_render_scene.camera, current_world_point)
                if current_projected_point.z > 0 and 0 <= current_projected_point.x <= 1 and 0 <= current_projected_point.y <= 1:
                    current_pose_keypoints[current_joint_index] = [float(current_projected_point.x * CURRENT_CONFIG_RECORD['resolution']), float((1 - current_projected_point.y) * CURRENT_CONFIG_RECORD['resolution']), 1.]
            current_next_frame = CURRENT_SAMPLE_FRAMES[current_image_index] if current_image_index < len(CURRENT_SAMPLE_FRAMES) else CURRENT_REQUEST_RECORD['end_frame'] + 1
            current_head_keypoints = []
            for current_head_position in (current_rig_object.pose.bones['head'].head, current_rig_object.pose.bones['head'].tail):
                current_head_projection = world_to_camera_view(current_render_scene, current_render_scene.camera, current_rig_object.matrix_world @ current_head_position)
                current_head_keypoints.append([float(current_head_projection.x * CURRENT_CONFIG_RECORD['resolution']), float((1 - current_head_projection.y) * CURRENT_CONFIG_RECORD['resolution']), 1.] if current_head_projection.z > 0 and 0 <= current_head_projection.x <= 1 and 0 <= current_head_projection.y <= 1 else [0., 0., 0.])
            current_image_records.append({'path': current_relative_path, 'projection': current_projection_name, 'direction': current_direction_name, 'source_frame': current_frame_number, 'source_time_seconds': (current_frame_number - 1) / 30, 'duration_seconds': (current_next_frame - current_frame_number) / 30, 'pose_keypoints_2d': [current_axis_value for current_joint_point in current_pose_keypoints for current_axis_value in current_joint_point], 'head_bone_keypoints_2d': current_head_keypoints})
(CURRENT_OUTPUT_DIRECTORY / 'render-manifest.json').write_text(json.dumps({'images': current_image_records, 'camera': current_camera_records, 'projection_cameras': current_projection_cameras, 'projections': current_projection_names}, ensure_ascii=False, indent=2))
print(f'{time.strftime("%FT%T")}/vnccs-render/completed images={len(current_image_records)}', flush=True)
