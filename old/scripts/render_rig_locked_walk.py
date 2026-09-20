"""기본 리그의 포즈를 고정한 채 제작용 캐릭터 외형을 직접 렌더한다."""
from pathlib import Path
import hashlib
import json
import math
import threading
import time
import traceback
import numpy as np
from resolve_default_walk_rig import resolve_default_walk_rig

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[1]
RENDER_OUTPUT_PATH = WORKFLOW_ROOT_PATH / '.result/workflow/runs/rig-locked-walk-v1'
STYLE_ASSET_PATH = WORKFLOW_ROOT_PATH / '.result/workflow/reusable/rigs/default-styled-walk/v1'
DIRECTION_CAMERA_POINTS = {'down_left':(4,-6,4),'down_right':(-4,-6,4),'up_left':(4,6,4),'up_right':(-4,6,4)}
HEARTBEAT_STOP_EVENT = threading.Event()
CURRENT_STAGE_RECORD = {'stage':'prepare','frames':0}


def write_trace_message(stage_name_value,message_text_value):
    log_line_value=f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/rig-locked-walk/{stage_name_value} {message_text_value}'
    print(log_line_value,flush=True)
    with (RENDER_OUTPUT_PATH/'execution.log').open('a') as execution_log_handle:execution_log_handle.write(log_line_value+'\n')


def emit_progress_heartbeat():
    while not HEARTBEAT_STOP_EVENT.wait(5):write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))


def execute_locked_render():
    import bpy
    from mathutils import Vector
    source_rig_directory=resolve_default_walk_rig()
    bpy.ops.wm.open_mainfile(filepath=str(source_rig_directory/'five-head-walk.blend'))
    render_scene_value=bpy.context.scene
    rig_object_value=bpy.data.objects['five-head-own-rig']
    source_pose_matrices=[]
    for frame_index_value in range(1,9):
        render_scene_value.frame_set(frame_index_value)
        source_pose_matrices.append({bone.name:np.array(bone.matrix).tolist() for bone in rig_object_value.pose.bones})
    render_scene_value.frame_set(1)
    device_preferences_value=bpy.context.preferences.addons['cycles'].preferences
    device_preferences_value.compute_device_type='CUDA';device_preferences_value.get_devices()
    if not any(device.type=='CUDA' for device in device_preferences_value.devices):raise RuntimeError('외부 실행 환경에 CUDA 장치 없음')
    for device_record_value in device_preferences_value.devices:device_record_value.use=device_record_value.type=='CUDA'
    render_scene_value.cycles.device='GPU';render_scene_value.cycles.samples=32
    render_scene_value.render.resolution_x=384;render_scene_value.render.resolution_y=384
    render_scene_value.render.film_transparent=True;render_scene_value.render.image_settings.color_mode='RGBA';render_scene_value.render.image_settings.color_depth='8'
    render_scene_value.use_nodes=False
    for node_record_value in render_scene_value.node_tree.nodes if render_scene_value.node_tree else []:
        if node_record_value.type=='OUTPUT_FILE':node_record_value.mute=True
    def create_surface_material(material_name_value,color_channel_values):
        material_record_value=bpy.data.materials.new(material_name_value);material_record_value.diffuse_color=(*color_channel_values,1)
        material_record_value.use_nodes=True
        surface_shader_node=material_record_value.node_tree.nodes.get('Principled BSDF')
        surface_shader_node.inputs['Base Color'].default_value=(*color_channel_values,1);surface_shader_node.inputs['Roughness'].default_value=.78
        return material_record_value
    skin_surface_material=create_surface_material('skin',(.63,.39,.23))
    shirt_surface_material=create_surface_material('white-shirt',(.88,.88,.85))
    shorts_surface_material=create_surface_material('gray-shorts',(.22,.23,.25))
    shoes_surface_material=create_surface_material('white-shoes',(.9,.9,.88))
    hair_surface_material=create_surface_material('dark-brown-hair',(.055,.027,.016))
    eyes_surface_material=create_surface_material('eye-white',(.9,.86,.77))
    pupils_surface_material=create_surface_material('dark-brown-eyes',(.022,.012,.009))
    for mesh_object_value in list(render_scene_value.objects):
        if mesh_object_value.type!='MESH':continue
        mesh_object_value.data.materials.clear()
        chosen_surface_material=skin_surface_material
        if mesh_object_value.name=='continuous-torso-pelvis':chosen_surface_material=shirt_surface_material
        if mesh_object_value.name in ['body-joint-16','body-joint-17','joint-volume-16','joint-volume-17']:chosen_surface_material=shirt_surface_material
        if 'shoe' in mesh_object_value.name:chosen_surface_material=shoes_surface_material
        mesh_object_value.data.materials.append(chosen_surface_material)
        if mesh_object_value.name=='continuous-torso-pelvis':
            mesh_object_value.data.materials.append(shorts_surface_material)
            for polygon_record_value in mesh_object_value.data.polygons:
                if polygon_record_value.center.z<1.025:polygon_record_value.material_index=1
    def bind_styled_object(mesh_object_value,bone_name_value,surface_material_value):
        mesh_object_value.data.materials.append(surface_material_value)
        for polygon_record_value in mesh_object_value.data.polygons:polygon_record_value.use_smooth=True
        vertex_group_value=mesh_object_value.vertex_groups.new(name=bone_name_value);vertex_group_value.add(list(range(len(mesh_object_value.data.vertices))),1,'REPLACE')
        armature_modifier_value=mesh_object_value.modifiers.new('approved-rig-deform','ARMATURE');armature_modifier_value.object=rig_object_value
    def add_styled_sphere(object_name_value,center_point_values,radius_axis_values,bone_name_value,surface_material_value):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=center_point_values)
        mesh_object_value=bpy.context.object;mesh_object_value.name=object_name_value;mesh_object_value.scale=radius_axis_values
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bind_styled_object(mesh_object_value,bone_name_value,surface_material_value)
        return mesh_object_value
    for joint_index_value in [18,19,4,5]:
        rest_bone_value=rig_object_value.data.bones[f'joint-{joint_index_value:02d}'];bone_direction_vector=rest_bone_value.tail_local-rest_bone_value.head_local
        sleeve_active_value=joint_index_value in [18,19]
        garment_radius_value=.09 if sleeve_active_value else .132
        garment_center_vector=rest_bone_value.head_local+bone_direction_vector*(.22 if sleeve_active_value else .23)
        garment_mesh_object=add_styled_sphere(f'garment-{joint_index_value}',garment_center_vector,(garment_radius_value,garment_radius_value,bone_direction_vector.length*.30),f'joint-{joint_index_value:02d}',shirt_surface_material if sleeve_active_value else shorts_surface_material)
        garment_mesh_object.rotation_mode='QUATERNION';garment_mesh_object.rotation_quaternion=bone_direction_vector.to_track_quat('Z','Y')
    hair_vertex_values=[];hair_face_values=[];hair_segment_count=32;hair_ring_count=12
    for ring_index_value in range(hair_ring_count+1):
        for segment_index_value in range(hair_segment_count):
            azimuth_angle_value=2*math.pi*segment_index_value/hair_segment_count
            hairline_angle_value=1.22 if math.sin(azimuth_angle_value)>0 else 1.80
            polar_angle_value=.025+(hairline_angle_value-.025)*ring_index_value/hair_ring_count
            hair_vertex_values.append((.218*math.sin(polar_angle_value)*math.cos(azimuth_angle_value),-.197*math.sin(polar_angle_value)*math.sin(azimuth_angle_value),1.8+.216*math.cos(polar_angle_value)))
    for ring_index_value in range(hair_ring_count):
        for segment_index_value in range(hair_segment_count):
            current_vertex_index=ring_index_value*hair_segment_count+segment_index_value;next_vertex_index=ring_index_value*hair_segment_count+(segment_index_value+1)%hair_segment_count
            hair_face_values.append((current_vertex_index,current_vertex_index+hair_segment_count,next_vertex_index+hair_segment_count,next_vertex_index))
    hair_face_values.append(tuple(reversed(range(hair_segment_count))))
    hair_mesh_data=bpy.data.meshes.new('hair-cap');hair_mesh_data.from_pydata(hair_vertex_values,[],hair_face_values);hair_mesh_data.update()
    hair_mesh_object=bpy.data.objects.new('hair-cap',hair_mesh_data);render_scene_value.collection.objects.link(hair_mesh_object);bind_styled_object(hair_mesh_object,'joint-15',hair_surface_material)
    for side_index_value in [-1,1]:
        add_styled_sphere(f'eye-white-{side_index_value}',(side_index_value*.074,-.169,1.835),(.045,.026,.034),'joint-15',eyes_surface_material)
        add_styled_sphere(f'pupil-{side_index_value}',(side_index_value*.074,-.193,1.835),(.019,.009,.026),'joint-15',pupils_surface_material)
        add_styled_sphere(f'ear-{side_index_value}',(side_index_value*.208,0,1.79),(.035,.035,.052),'joint-15',skin_surface_material)
    add_styled_sphere('nose',(0,-.19,1.79),(.025,.029,.03),'joint-15',skin_surface_material)
    bpy.ops.object.light_add(type='AREA',location=(-3,-4,7));key_light_object=bpy.context.object;key_light_object.data.energy=350;key_light_object.data.shape='DISK';key_light_object.data.size=5
    key_light_object.rotation_euler=(Vector((0,0,1))-key_light_object.location).to_track_quat('-Z','Y').to_euler()
    validation_frame_records=[]
    for frame_index_value in range(1,9):
        render_scene_value.frame_set(frame_index_value)
        for bone_record_value in rig_object_value.pose.bones:
            if not np.allclose(np.array(bone_record_value.matrix),source_pose_matrices[frame_index_value-1][bone_record_value.name],atol=1e-7):raise ValueError('외형 적용 중 승인 포즈가 변경됨')
        validation_frame_records.append(dict(frame=frame_index_value,pose_equal=True))
    (RENDER_OUTPUT_PATH/'pose-validation.json').write_text(json.dumps(validation_frame_records,indent=2)+'\n')
    write_trace_message('validate','8프레임 모든 본의 변환이 기본 리그와 동일함')
    camera_object_value=render_scene_value.camera
    for direction_name_value,camera_point_values in DIRECTION_CAMERA_POINTS.items():
        camera_target_vector=Vector((0,0,1));camera_offset_vector=Vector(camera_point_values)-camera_target_vector
        camera_object_value.location=camera_target_vector+camera_offset_vector.normalized()*6
        camera_object_value.rotation_euler=(camera_target_vector-camera_object_value.location).to_track_quat('-Z','Y').to_euler()
        (RENDER_OUTPUT_PATH/direction_name_value).mkdir()
        for frame_index_value in range(1,9):
            render_scene_value.frame_set(frame_index_value);render_scene_value.render.filepath=str(RENDER_OUTPUT_PATH/direction_name_value/f'frame-{frame_index_value:04d}.png')
            if direction_name_value=='down_left' and frame_index_value==1:bpy.ops.wm.save_as_mainfile(filepath=str(STYLE_ASSET_PATH/'styled-walk.blend'))
            bpy.ops.render.render(write_still=True);CURRENT_STAGE_RECORD.update(stage=direction_name_value,frames=CURRENT_STAGE_RECORD['frames']+1)
            write_trace_message('render',f'{direction_name_value}/{frame_index_value}')
    metadata_record_value=dict(asset_id='default-styled-walk',version=1,rig='five-head-walk/v9',source_sha256=hashlib.sha256((source_rig_directory/'five-head-walk.blend').read_bytes()).hexdigest(),method='deterministic-rig-render',status='motion-preserved-style-prototype',quality_warnings=['원화 외형의 정밀 복원이 아닌 제작용 3D 외형','발 접지·8프레임 샘플링의 자연스러움은 육안 검수 필요'],files={str(p.relative_to(RENDER_OUTPUT_PATH)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RENDER_OUTPUT_PATH.glob('*/*.png'))})
    (RENDER_OUTPUT_PATH/'manifest.json').write_text(json.dumps(metadata_record_value,ensure_ascii=False,indent=2)+'\n')
    (STYLE_ASSET_PATH/'artifact.json').write_text(json.dumps(dict(asset_id='default-styled-walk',version=1,source_rig='five-head-walk/v9',source_sha256=metadata_record_value['source_sha256'],blend_sha256=hashlib.sha256((STYLE_ASSET_PATH/'styled-walk.blend').read_bytes()).hexdigest()),indent=2)+'\n')


if __name__=='__main__':
    if RENDER_OUTPUT_PATH.exists() or STYLE_ASSET_PATH.exists():raise FileExistsError('불변 버전 덮어쓰기 금지')
    RENDER_OUTPUT_PATH.mkdir(parents=True);STYLE_ASSET_PATH.mkdir(parents=True)
    threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
    try:execute_locked_render();write_trace_message('complete','포즈 고정 외형 32프레임 생성')
    except Exception:write_trace_message('failure',traceback.format_exc());raise
    finally:HEARTBEAT_STOP_EVENT.set()
