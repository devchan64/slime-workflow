"""HumanML3D 관절을 자체 5등신 제작 리그로 옮겨 CUDA Depth를 렌더한다."""
from pathlib import Path
import hashlib
import json
import threading
import time
import traceback
import numpy as np

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
SOURCE_MOTION_PATH = WORKFLOW_ROOT_PATH / 'assets/motions/walk-travel/v1/motion.npz'
SOURCE_MANIFEST_PATH = SOURCE_MOTION_PATH.with_name('artifact.json')
OUTPUT_ASSET_PATH = WORKFLOW_ROOT_PATH / 'assets/rigs/five-head-walk/v9'
RENDER_OUTPUT_PATH = WORKFLOW_ROOT_PATH / '.result/workflow/runs/five-head-walk-v9'
SOURCE_START_FRAME = 41
SOURCE_END_FRAME = 65
OUTPUT_FRAME_COUNT = 8
RENDER_PIXEL_SIZE = 256
FOOT_PITCH_MINIMUM = np.deg2rad(-20)
FOOT_PITCH_MAXIMUM = np.deg2rad(25)
CAMERA_DEPTH_NEAR = 4.0
CAMERA_DEPTH_FAR = 8.0
JOINT_PARENT_INDICES = [-1,0,0,0,1,2,3,4,5,6,7,8,9,9,9,12,13,14,16,17,18,19]
# y-up, m. 머리 0.4m, 전체 중립 실루엣 2m. 외부 인체 모델 미사용.
REST_JOINT_POINTS = np.array([[0,1.0035,0],[.14,1.0035,0],[-.14,1.0035,0],[0,1.182,0],
 [.14,.5305,0],[-.14,.5305,0],[0,1.31,0],[.14,.085,0],[-.14,.085,0],[0,1.40,0],
 [.14,.065,.17],[-.14,.065,.17],[0,1.60,0],[.12,1.40,0],[-.12,1.40,0],[0,1.80,0],
 [.25,1.40,0],[-.25,1.40,0],[.28,1.09,0],[-.28,1.09,0],[.29,.83,0],[-.29,.83,0]],dtype=float)
HEAD_MESH_RADII = (.21,.19,.20)
SHOE_MESH_RADII = (.09,.18,.07)
THIGH_MESH_RADIUS = .115
CALF_MESH_RADIUS = .08
TORSO_MESH_RADIUS = .235
REFERENCE_ASSET_PATH = WORKFLOW_ROOT_PATH / 'assets/references/default-standing/v2'
DIRECTION_CAMERA_POINTS = {'down_left':(4,-6,4),'down_right':(-4,-6,4),'up_left':(4,6,4),'up_right':(-4,6,4)}
CURRENT_STAGE_RECORD = {'stage':'prepare','completed':0}
HEARTBEAT_STOP_EVENT = threading.Event()


def write_trace_message(stage_name_value, message_text_value):
    trace_line_value=f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/five-head-walk/{stage_name_value} {message_text_value}'
    print(trace_line_value,flush=True)
    with (RENDER_OUTPUT_PATH/'execution.log').open('a') as log_file_handle:
        log_file_handle.write(trace_line_value+'\n')


def emit_progress_heartbeat():
    while not HEARTBEAT_STOP_EVENT.wait(5):
        write_trace_message('heartbeat',str(CURRENT_STAGE_RECORD))


def solve_leg_contact(hip_joint_point,knee_joint_point,ankle_target_point,upper_leg_length,lower_leg_length):
    target_delta_vector=ankle_target_point-hip_joint_point
    target_distance_value=np.linalg.norm(target_delta_vector)
    if target_distance_value < 1e-8:
        raise ValueError('IK 대상과 고관절이 일치함')
    target_axis_vector=target_delta_vector/target_distance_value
    reachable_distance_value=np.clip(target_distance_value,abs(upper_leg_length-lower_leg_length)+1e-5,upper_leg_length+lower_leg_length-1e-5)
    bend_plane_vector=knee_joint_point-hip_joint_point
    bend_plane_vector-=np.dot(bend_plane_vector,target_axis_vector)*target_axis_vector
    if np.linalg.norm(bend_plane_vector)<1e-7:
        raise ValueError('무릎 굽힘 방향을 결정할 수 없음')
    bend_plane_vector/=np.linalg.norm(bend_plane_vector)
    projected_length_value=(upper_leg_length**2-lower_leg_length**2+reachable_distance_value**2)/(2*reachable_distance_value)
    bent_height_value=np.sqrt(max(0,upper_leg_length**2-projected_length_value**2))
    return hip_joint_point+target_axis_vector*projected_length_value+bend_plane_vector*bent_height_value,hip_joint_point+target_axis_vector*reachable_distance_value


def retarget_motion_sequence():
    source_manifest_record=json.loads(SOURCE_MANIFEST_PATH.read_text())
    if hashlib.sha256(SOURCE_MOTION_PATH.read_bytes()).hexdigest()!=source_manifest_record['sha256']:
        raise ValueError('원본 모션 해시 불일치')
    with np.load(SOURCE_MOTION_PATH,allow_pickle=False) as source_motion_bundle:
        if set(source_motion_bundle.files)!={'joints','features'}:
            raise ValueError('모션 필드 불일치')
        source_joint_frames=source_motion_bundle['joints'].copy()
    if source_joint_frames.shape!=(96,22,3) or not np.isfinite(source_joint_frames).all():
        raise ValueError('HumanML3D-22 출력 형식 불일치')
    source_joint_frames=source_joint_frames[SOURCE_START_FRAME:SOURCE_END_FRAME+1]
    retarget_joint_frames=np.zeros_like(source_joint_frames,dtype=float)
    source_relative_frames=source_joint_frames-source_joint_frames[:,0:1,:]
    retarget_joint_frames[:,0,1]=REST_JOINT_POINTS[0,1]+(source_joint_frames[:,0,1]-source_joint_frames[:,0,1].mean())*.8
    for joint_index_value in range(1,22):
        parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
        source_bone_vectors=source_relative_frames[:,joint_index_value]-source_relative_frames[:,parent_index_value]
        source_bone_lengths=np.linalg.norm(source_bone_vectors,axis=1)
        if (source_bone_lengths<1e-6).any():
            raise ValueError('길이가 0인 입력 관절')
        target_bone_length=np.linalg.norm(REST_JOINT_POINTS[joint_index_value]-REST_JOINT_POINTS[parent_index_value])
        retarget_joint_frames[:,joint_index_value]=retarget_joint_frames[:,parent_index_value]+source_bone_vectors/source_bone_lengths[:,None]*target_bone_length
    # 머리 중심은 목 위로 두어 머리 단위가 모션의 코/머리 관절 오프셋에 좌우되지 않게 한다.
    retarget_joint_frames[:,15]=retarget_joint_frames[:,12]+np.array([0,.20,0])
    seam_error_before=float(np.sqrt(np.mean((retarget_joint_frames[-1]-retarget_joint_frames[0])**2)))
    seam_delta_points=retarget_joint_frames[-1]-retarget_joint_frames[0]
    retarget_joint_frames-=np.linspace(0,1,len(retarget_joint_frames))[:,None,None]*seam_delta_points
    contact_frame_flags=[]
    for frame_index_value,joint_frame_points in enumerate(retarget_joint_frames):
        joint_frame_points[:,1]+=.085-min(joint_frame_points[7,1],joint_frame_points[8,1])
        current_contact_flags=[]
        for hip_index_value,knee_index_value,ankle_index_value,toe_index_value in [(1,4,7,10),(2,5,8,11)]:
            contact_active_value=bool(source_joint_frames[frame_index_value,toe_index_value,1]<.035)
            current_contact_flags.append(contact_active_value)
            if contact_active_value:
                ankle_target_point=joint_frame_points[ankle_index_value].copy();ankle_target_point[1]=.085
                knee_target_point,ankle_target_point=solve_leg_contact(joint_frame_points[hip_index_value],joint_frame_points[knee_index_value],ankle_target_point,
                    np.linalg.norm(REST_JOINT_POINTS[knee_index_value]-REST_JOINT_POINTS[hip_index_value]),
                    np.linalg.norm(REST_JOINT_POINTS[ankle_index_value]-REST_JOINT_POINTS[knee_index_value]))
                joint_frame_points[knee_index_value]=knee_target_point
                joint_frame_points[ankle_index_value]=ankle_target_point
                joint_frame_points[toe_index_value]=ankle_target_point+np.array([0,-.02,.17])
        contact_frame_flags.append(current_contact_flags)
    # 직선 걷기 전용: 발의 yaw/roll을 고정하고 원본 pitch만 제한·주기 평활한다.
    # 접지 판정의 경계에서 원본 발 방향으로 갑자기 복귀하지 않도록 한다.
    for ankle_index_value,toe_index_value in [(7,10),(8,11)]:
        foot_rest_vector=REST_JOINT_POINTS[toe_index_value]-REST_JOINT_POINTS[ankle_index_value]
        foot_rest_length=np.linalg.norm(foot_rest_vector)
        foot_rest_pitch=np.arctan2(foot_rest_vector[1],foot_rest_vector[2])
        foot_motion_vectors=retarget_joint_frames[:-1,toe_index_value]-retarget_joint_frames[:-1,ankle_index_value]
        foot_pitch_values=np.clip(np.arctan2(foot_motion_vectors[:,1],np.linalg.norm(foot_motion_vectors[:,[0,2]],axis=1))-foot_rest_pitch,FOOT_PITCH_MINIMUM,FOOT_PITCH_MAXIMUM)
        foot_pitch_values=(np.roll(foot_pitch_values,2)+4*np.roll(foot_pitch_values,1)+6*foot_pitch_values+4*np.roll(foot_pitch_values,-1)+np.roll(foot_pitch_values,-2))/16
        foot_target_angles=foot_rest_pitch+foot_pitch_values
        retarget_joint_frames[:-1,toe_index_value]=retarget_joint_frames[:-1,ankle_index_value]+np.column_stack((np.zeros_like(foot_target_angles),np.sin(foot_target_angles),np.cos(foot_target_angles)))*foot_rest_length
    # 원본 인체의 상승하는 쇄골 방향을 그대로 쓰면 짧은 체형에서 어깨가 목을 덮는다.
    # 걷기의 수평 회전은 보존하고 쇄골 수직 성분만 10%로 줄인 뒤 길이를 복원한다.
    for collar_index_value,shoulder_index_value,elbow_index_value,wrist_index_value in [(13,16,18,20),(14,17,19,21)]:
        previous_shoulder_points=retarget_joint_frames[:,shoulder_index_value].copy()
        previous_collar_points=retarget_joint_frames[:,collar_index_value].copy()
        for joint_index_value,parent_index_value,source_parent_points in [(collar_index_value,9,retarget_joint_frames[:,9].copy()),(shoulder_index_value,collar_index_value,previous_collar_points)]:
            shoulder_axis_vectors=retarget_joint_frames[:,joint_index_value]-source_parent_points
            shoulder_axis_vectors[:,1]*=.10
            shoulder_axis_lengths=np.linalg.norm(shoulder_axis_vectors,axis=1)
            if (shoulder_axis_lengths<1e-6).any():raise ValueError('쇄골 방향을 결정할 수 없음')
            shoulder_rest_length=np.linalg.norm(REST_JOINT_POINTS[joint_index_value]-REST_JOINT_POINTS[parent_index_value])
            retarget_joint_frames[:,joint_index_value]=retarget_joint_frames[:,parent_index_value]+shoulder_axis_vectors/shoulder_axis_lengths[:,None]*shoulder_rest_length
        shoulder_offset_points=retarget_joint_frames[:,shoulder_index_value]-previous_shoulder_points
        retarget_joint_frames[:,elbow_index_value]+=shoulder_offset_points
        retarget_joint_frames[:,wrist_index_value]+=shoulder_offset_points
    # 표현용 제자리 루프; 원본의 이동 경로는 원본 자산에 그대로 남는다.
    retarget_joint_frames[-1]=retarget_joint_frames[0]
    output_frame_indices=np.arange(OUTPUT_FRAME_COUNT)*3
    OUTPUT_ASSET_PATH.mkdir(parents=True)
    np.savez_compressed(OUTPUT_ASSET_PATH/'retargeted-motion.npz',joints=retarget_joint_frames,rest=REST_JOINT_POINTS,contacts=np.array(contact_frame_flags),sample_indices=output_frame_indices)
    return retarget_joint_frames[output_frame_indices],dict(source=source_manifest_record['asset_id'],source_version=source_manifest_record['version'],source_sha256=source_manifest_record['sha256'],source_interval=[SOURCE_START_FRAME,SOURCE_END_FRAME],fps=20,cycle_seconds=1.2,sample_indices=output_frame_indices.tolist(),seam_rms_before_m=seam_error_before,seam_position_after_m=0.0,contact_counts=np.array(contact_frame_flags).sum(axis=0).tolist(),quality_warnings=['관절 길이 재배치 후 접지 높이 IK만 적용; 수평 발 미끄러짐·경계 속도 불연속 검수 필요','5등신은 중립 제작 메시 기준; 참조 원화와 일치하는 최종 외형 메시가 아님','MoMask 가중치·학습자료의 상업 이용 조건 검토 미완료'])


def build_render_scene(sample_joint_frames):
    import bpy
    from mathutils import Vector,Matrix
    bpy.ops.wm.read_factory_settings(use_empty=True)
    render_scene_value=bpy.context.scene
    render_scene_value.render.engine='CYCLES'
    device_preferences_value=bpy.context.preferences.addons['cycles'].preferences
    device_preferences_value.compute_device_type='CUDA';device_preferences_value.get_devices()
    gpu_device_values=[device for device in device_preferences_value.devices if device.type=='CUDA']
    if not gpu_device_values:
        raise RuntimeError('샌드박스 밖 Blender CUDA 장치 없음')
    for device_record_value in device_preferences_value.devices:
        device_record_value.use=device_record_value.type=='CUDA'
    render_scene_value.cycles.device='GPU';render_scene_value.cycles.samples=8
    render_scene_value.render.resolution_x=RENDER_PIXEL_SIZE;render_scene_value.render.resolution_y=RENDER_PIXEL_SIZE
    render_scene_value.render.resolution_percentage=100;render_scene_value.render.film_transparent=True
    render_scene_value.render.image_settings.file_format='PNG';render_scene_value.render.image_settings.color_mode='RGBA'
    render_scene_value.view_settings.view_transform='Standard'
    render_scene_value.world=bpy.data.worlds.new('neutral-world');render_scene_value.world.use_nodes=True
    render_scene_value.world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.6,.6,1)
    bpy.ops.object.armature_add()
    rig_object_value=bpy.context.object;rig_object_value.name='five-head-own-rig'
    bpy.ops.object.mode_set(mode='EDIT');rig_object_value.data.edit_bones.remove(rig_object_value.data.edit_bones[0])
    def convert_joint_vector(joint_point_value):
        return Vector((float(joint_point_value[0]),float(-joint_point_value[2]),float(joint_point_value[1])))
    bone_rest_records=[]
    for joint_index_value in range(1,22):
        parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
        bone_head_vector=convert_joint_vector(REST_JOINT_POINTS[parent_index_value]);bone_tail_vector=convert_joint_vector(REST_JOINT_POINTS[joint_index_value])
        bone_name_value=f'joint-{joint_index_value:02d}'
        edit_bone_value=rig_object_value.data.edit_bones.new(bone_name_value)
        edit_bone_value.head=bone_head_vector;edit_bone_value.tail=bone_tail_vector
        bone_rest_records.append((bone_name_value,bone_head_vector,bone_tail_vector,joint_index_value))
    bpy.ops.object.mode_set(mode='OBJECT')
    # 각 제작 파트를 명시한 본에 가중치 1로 연결한다. SMPL 토폴로지·파라미터 미사용.
    def bind_mesh_part(mesh_object_value,bone_name_value):
        deform_vertex_group=mesh_object_value.vertex_groups.new(name=bone_name_value)
        deform_vertex_group.add(list(range(len(mesh_object_value.data.vertices))),1,'REPLACE')
        armature_modifier_value=mesh_object_value.modifiers.new('own-rig-deform','ARMATURE');armature_modifier_value.object=rig_object_value
    for bone_name_value,bone_head_vector,bone_tail_vector,joint_index_value in bone_rest_records:
        if joint_index_value in [1,2,3,6,9,10,11,13,14,15]:continue
        bone_direction_vector=bone_tail_vector-bone_head_vector
        radius_size_value=THIGH_MESH_RADIUS if joint_index_value in [4,5] else CALF_MESH_RADIUS if joint_index_value in [7,8] else .067
        if joint_index_value in [3,6,9]:radius_size_value=TORSO_MESH_RADIUS
        if joint_index_value==12:radius_size_value=.075
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,location=(bone_head_vector+bone_tail_vector)/2)
        mesh_object_value=bpy.context.object;mesh_object_value.name='body-'+bone_name_value
        mesh_object_value.scale=(radius_size_value,radius_size_value,bone_direction_vector.length*(.82 if joint_index_value in [3,6,9] else .62))
        mesh_object_value.rotation_mode='QUATERNION';mesh_object_value.rotation_quaternion=bone_direction_vector.to_track_quat('Z','Y')
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bind_mesh_part(mesh_object_value,bone_name_value)
    # 원화의 셔츠~반바지 실루엣을 연속된 타원 단면으로 표현한다.
    # 분리된 몸통 구들의 구형 돌출과 생략된 골반을 제거한다.
    torso_ring_profiles=[(.86,.13,.115),(.94,.22,.14),(1.04,.225,.145),(1.17,.205,.135),(1.31,.235,.145),(1.40,.205,.13),(1.43,.08,.075)]
    torso_ring_segments=24
    torso_vertex_values=[]
    torso_face_values=[]
    for torso_height_value,torso_width_value,torso_depth_value in torso_ring_profiles:
        for ring_segment_index in range(torso_ring_segments):
            ring_angle_value=2*np.pi*ring_segment_index/torso_ring_segments
            torso_vertex_values.append((torso_width_value*np.cos(ring_angle_value),torso_depth_value*np.sin(ring_angle_value),torso_height_value))
    for ring_profile_index in range(len(torso_ring_profiles)-1):
        for ring_segment_index in range(torso_ring_segments):
            current_vertex_index=ring_profile_index*torso_ring_segments+ring_segment_index
            next_vertex_index=ring_profile_index*torso_ring_segments+(ring_segment_index+1)%torso_ring_segments
            torso_face_values.append((current_vertex_index,next_vertex_index,next_vertex_index+torso_ring_segments,current_vertex_index+torso_ring_segments))
    torso_face_values.append(tuple(reversed(range(torso_ring_segments))))
    torso_face_values.append(tuple(range((len(torso_ring_profiles)-1)*torso_ring_segments,len(torso_ring_profiles)*torso_ring_segments)))
    torso_mesh_data=bpy.data.meshes.new('continuous-torso-pelvis')
    torso_mesh_data.from_pydata(torso_vertex_values,[],torso_face_values);torso_mesh_data.update()
    torso_mesh_object=bpy.data.objects.new('continuous-torso-pelvis',torso_mesh_data)
    render_scene_value.collection.objects.link(torso_mesh_object)
    for torso_polygon_value in torso_mesh_data.polygons:torso_polygon_value.use_smooth=True
    # 하부·중부·상부 척추 사이에 높이별 가중치를 분배한다.
    torso_weight_centers=np.array([1.04,1.24,1.40])
    torso_deform_groups=[torso_mesh_object.vertex_groups.new(name=f'joint-{joint_index_value:02d}') for joint_index_value in [3,6,9]]
    for torso_vertex_index,torso_vertex_point in enumerate(torso_vertex_values):
        torso_height_value=torso_vertex_point[2]
        torso_weight_values=np.array([np.interp(torso_height_value,torso_weight_centers,[1,0,0]),np.interp(torso_height_value,torso_weight_centers,[0,1,0]),np.interp(torso_height_value,torso_weight_centers,[0,0,1])])
        for torso_group_value,torso_weight_value in zip(torso_deform_groups,torso_weight_values):
            if torso_weight_value>0:torso_group_value.add([torso_vertex_index],float(torso_weight_value),'REPLACE')
    torso_armature_modifier=torso_mesh_object.modifiers.new('spine-weighted-deform','ARMATURE');torso_armature_modifier.object=rig_object_value
    torso_armature_modifier.use_deform_preserve_volume=True
    # 굽힘 지점의 틈을 덮는 관절 볼륨. 기존 관절 위치·다리 모션은 변경하지 않는다.
    for joint_index_value,joint_radius_value in [(4,.093),(5,.093),(16,.075),(17,.075),(18,.064),(19,.064)]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=10,radius=joint_radius_value,location=convert_joint_vector(REST_JOINT_POINTS[joint_index_value]))
        joint_mesh_object=bpy.context.object;joint_mesh_object.name=f'joint-volume-{joint_index_value:02d}'
        bind_mesh_part(joint_mesh_object,f'joint-{joint_index_value:02d}')
    for joint_index_value,part_name_value,part_scale_values,part_offset_values in [(15,'head',HEAD_MESH_RADII,(0,0,0)),(7,'left-shoe',SHOE_MESH_RADII,(0,-.06,-.02)),(8,'right-shoe',SHOE_MESH_RADII,(0,-.06,-.02)),(20,'left-hand',(.055,.045,.08),(0,0,-.025)),(21,'right-hand',(.055,.045,.08),(0,0,-.025))]:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=convert_joint_vector(REST_JOINT_POINTS[joint_index_value])+Vector(part_offset_values))
        mesh_object_value=bpy.context.object;mesh_object_value.name=part_name_value;mesh_object_value.scale=part_scale_values
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        deform_joint_index={7:10,8:11}.get(joint_index_value,joint_index_value)
        bind_mesh_part(mesh_object_value,f'joint-{deform_joint_index:02d}')
    for frame_index_value,joint_frame_points in enumerate(sample_joint_frames):
        for bone_name_value,bone_head_vector,bone_tail_vector,joint_index_value in bone_rest_records:
            parent_index_value=JOINT_PARENT_INDICES[joint_index_value]
            current_head_vector=convert_joint_vector(joint_frame_points[parent_index_value]);current_tail_vector=convert_joint_vector(joint_frame_points[joint_index_value])
            pose_bone_value=rig_object_value.pose.bones[bone_name_value]
            # 기준 본의 roll을 보존하는 최소 회전. 전역 up 추적의 축 반전을 피한다.
            rest_bone_rotation=rig_object_value.data.bones[bone_name_value].matrix_local.to_quaternion()
            motion_swing_rotation=(bone_tail_vector-bone_head_vector).rotation_difference(current_tail_vector-current_head_vector)
            pose_bone_value.rotation_mode='QUATERNION'
            pose_bone_value.matrix=Matrix.Translation(current_head_vector)@(motion_swing_rotation@rest_bone_rotation).to_matrix().to_4x4()
            pose_bone_value.keyframe_insert('location',frame=frame_index_value+1)
            pose_bone_value.keyframe_insert('rotation_quaternion',frame=frame_index_value+1)
            pose_bone_value.keyframe_insert('scale',frame=frame_index_value+1)
    for mesh_object_value in render_scene_value.objects:
        if mesh_object_value.type=='MESH':
            for mesh_polygon_value in mesh_object_value.data.polygons:mesh_polygon_value.use_smooth=True
            for mesh_vertex_value in mesh_object_value.data.vertices:
                if not np.isclose(sum(group.weight for group in mesh_vertex_value.groups),1.0,atol=1e-6):
                    raise ValueError(f'정점 가중치 합 불일치: {mesh_object_value.name}/{mesh_vertex_value.index}')
    write_trace_message('validate','전체 메시 정점의 변형 가중치 합 1.0 검증 통과')
    validate_foot_transforms(bpy,rig_object_value,OUTPUT_FRAME_COUNT)
    render_scene_value.frame_start=1;render_scene_value.frame_end=OUTPUT_FRAME_COUNT
    render_scene_value.render.fps=20;render_scene_value.render.fps_base=3
    bpy.ops.object.camera_add();camera_object_value=bpy.context.object
    camera_object_value.data.type='ORTHO';camera_object_value.data.ortho_scale=2.65
    camera_object_value.data.clip_start=.1;camera_object_value.data.clip_end=20
    render_scene_value.camera=camera_object_value
    render_scene_value.use_nodes=True;render_scene_value.view_layers[0].use_pass_z=True
    compositor_nodes_value=render_scene_value.node_tree.nodes;compositor_nodes_value.clear()
    render_layer_node=compositor_nodes_value.new('CompositorNodeRLayers')
    depth_range_node=compositor_nodes_value.new('CompositorNodeMapRange')
    depth_range_node.inputs[1].default_value=CAMERA_DEPTH_NEAR;depth_range_node.inputs[2].default_value=CAMERA_DEPTH_FAR
    depth_range_node.inputs[3].default_value=1;depth_range_node.inputs[4].default_value=0;depth_range_node.use_clamp=True
    render_scene_value.node_tree.links.new(render_layer_node.outputs['Depth'],depth_range_node.inputs[0])
    file_output_node=compositor_nodes_value.new('CompositorNodeOutputFile');file_output_node.base_path=str(RENDER_OUTPUT_PATH)
    file_output_node.format.file_format='PNG';file_output_node.format.color_mode='BW';file_output_node.format.color_depth='16'
    file_output_node.file_slots[0].path='depth-';render_scene_value.node_tree.links.new(depth_range_node.outputs[0],file_output_node.inputs[0])
    file_output_node.file_slots.new('mask-');render_scene_value.node_tree.links.new(render_layer_node.outputs['Alpha'],file_output_node.inputs[1])
    composite_output_node=compositor_nodes_value.new('CompositorNodeComposite');render_scene_value.node_tree.links.new(render_layer_node.outputs['Image'],composite_output_node.inputs[0])
    for direction_name_value,camera_point_values in DIRECTION_CAMERA_POINTS.items():
        camera_target_vector=Vector((0,0,1))
        camera_offset_vector=Vector(camera_point_values)-camera_target_vector
        camera_object_value.location=camera_target_vector+camera_offset_vector.normalized()*6
        camera_object_value.rotation_euler=(camera_target_vector-camera_object_value.location).to_track_quat('-Z','Y').to_euler()
        if direction_name_value == 'down_left':
            render_scene_value.frame_set(1)
            file_output_node.file_slots[0].path='down_left/depth-'
            file_output_node.file_slots[1].path='down_left/mask-'
            render_scene_value.render.filepath=str(RENDER_OUTPUT_PATH/'down_left/preview-0001.png')
            bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_ASSET_PATH/'five-head-walk.blend'))
        for frame_index_value in range(OUTPUT_FRAME_COUNT):
            CURRENT_STAGE_RECORD.update(stage=direction_name_value,completed=frame_index_value)
            render_scene_value.frame_set(frame_index_value+1)
            file_output_node.file_slots[0].path=f'{direction_name_value}/depth-'
            file_output_node.file_slots[1].path=f'{direction_name_value}/mask-'
            render_scene_value.render.filepath=str(RENDER_OUTPUT_PATH/direction_name_value/f'preview-{frame_index_value+1:04d}.png')
            bpy.ops.render.render(write_still=True)
            write_trace_message('render',f'{direction_name_value} {frame_index_value+1}/{OUTPUT_FRAME_COUNT}')
    return dict(blender=bpy.app.version_string,gpu=[device.name for device in gpu_device_values],render_size=RENDER_PIXEL_SIZE,depth_near=CAMERA_DEPTH_NEAR,depth_far=CAMERA_DEPTH_FAR)


def validate_foot_transforms(blender_module_value,rig_object_value,frame_count_value):
    """실제 평가된 신발 변환에서 옆 비틀림·뒤집힘·프레임 간 급회전을 검증한다."""
    from mathutils import Vector
    foot_frame_records={}
    for shoe_name_value,toe_index_value in [('left-shoe',10),('right-shoe',11)]:
        shoe_object_value=blender_module_value.data.objects[shoe_name_value]
        if [group.name for group in shoe_object_value.vertex_groups]!=[f'joint-{toe_index_value:02d}']:
            raise ValueError('신발이 발목–발끝 본에 연결되지 않음')
        foot_angle_values=[]
        for frame_index_value in range(frame_count_value):
            blender_module_value.context.scene.frame_set(frame_index_value+1)
            blender_module_value.context.view_layer.update()
            foot_bone_name=f'joint-{toe_index_value:02d}'
            foot_deform_matrix=rig_object_value.pose.bones[foot_bone_name].matrix@rig_object_value.data.bones[foot_bone_name].matrix_local.inverted()
            foot_forward_vector=(foot_deform_matrix.to_3x3()@Vector((0,-1,0))).normalized()
            foot_side_vector=(foot_deform_matrix.to_3x3()@Vector((1,0,0))).normalized()
            if abs(foot_forward_vector.x)>1e-5 or foot_side_vector.x<.99999 or foot_forward_vector.y>=0:
                raise ValueError(f'발 회전축 뒤집힘: {shoe_name_value}/{frame_index_value+1}')
            foot_angle_values.append(float(np.degrees(np.arctan2(foot_forward_vector.z,-foot_forward_vector.y))))
        foot_angle_deltas=np.abs(np.roll(foot_angle_values,-1)-foot_angle_values)
        if max(abs(value) for value in foot_angle_values)>25.01 or max(foot_angle_deltas)>30:
            raise ValueError(f'발 회전 범위/연속성 불일치: {shoe_name_value}')
        foot_frame_records[shoe_name_value]=dict(pitch_degrees=foot_angle_values,max_step_degrees=float(max(foot_angle_deltas)),yaw_roll_locked=True)
    (RENDER_OUTPUT_PATH/'foot-validation.json').write_text(json.dumps(foot_frame_records,indent=2)+'\n')
    write_trace_message('validate','신발 본 연결·평가 회전축·루프 포함 각도 변화 검증 통과')


def write_preview_gallery():
    """같은 화면 높이·발밑 기준선에서 참조 원화와 제작 리그를 비교한다."""
    from PIL import Image
    from scipy.ndimage import label
    def measure_subject_bounds(image_pixel_values):
        component_label_values,component_count_value=label(image_pixel_values[:,:,3]>127)
        if component_count_value==0:
            raise ValueError('미리보기의 불투명 캐릭터 영역 없음')
        component_size_values=np.bincount(component_label_values.ravel());component_size_values[0]=0
        subject_row_values,subject_column_values=np.where(component_label_values==component_size_values.argmax())
        return [int(subject_column_values.min()),int(subject_row_values.min()),int(subject_column_values.max()+1),int(subject_row_values.max()+1)]
    reference_pixel_values=np.asarray(Image.open(REFERENCE_ASSET_PATH/'reference.png').convert('RGBA'))
    preview_comparison_records=[]
    for direction_index_value,direction_name_value in enumerate(DIRECTION_CAMERA_POINTS):
        reference_top_value=int(direction_index_value*reference_pixel_values.shape[0]/4)
        reference_bottom_value=int((direction_index_value+1)*reference_pixel_values.shape[0]/4)
        reference_width_value=int(reference_pixel_values.shape[1]/4)
        reference_crop_values=reference_pixel_values[reference_top_value:reference_bottom_value,:reference_width_value]
        reference_bounds_values=measure_subject_bounds(reference_crop_values)
        reference_bounds_values[1]+=reference_top_value;reference_bounds_values[3]+=reference_top_value
        render_bounds_values=[]
        for frame_index_value in range(OUTPUT_FRAME_COUNT):
            render_pixel_values=np.asarray(Image.open(RENDER_OUTPUT_PATH/direction_name_value/f'preview-{frame_index_value+1:04d}.png').convert('RGBA'))
            render_bounds_values.append(measure_subject_bounds(render_pixel_values))
        # 걷기 한 주기의 합집합 높이를 사용해 프레임마다 확대율이 바뀌지 않게 한다.
        render_union_bounds=[min(value[0] for value in render_bounds_values),min(value[1] for value in render_bounds_values),max(value[2] for value in render_bounds_values),max(value[3] for value in render_bounds_values)]
        preview_comparison_records.append(dict(direction=direction_name_value,reference=reference_bounds_values,walking=render_union_bounds))
    preview_html_text="""<!doctype html><meta charset="utf-8"><title>걷기 v9 · 스탠딩 비율 비교</title>
<style>body{background:#242938;color:#eee;font:16px sans-serif;margin:24px}section{display:inline-block;margin:8px;background:#30384a;padding:12px;border-radius:8px}canvas{width:360px;max-width:100%;display:block}button,input{margin:12px}h2{font-size:17px}.labels{display:flex;justify-content:space-around;font-size:14px;color:#ccd5e6}</style>
<h1>쇄골 방향·목 노출 개선 · 기본 스탠딩 비교</h1><p>스탠딩과 걷기 한 주기의 화면 높이를 220px로 맞췄습니다. 걷기 배율은 프레임 전체에서 고정합니다.</p><p>하단 선은 발밑 정렬 기준이며 가로선 간격은 표시 높이의 1/5입니다. 2D 투영 비교이며 정확한 3D 신체 치수 측정은 아닙니다.</p>
<button id="toggle">일시정지</button><input id="frame" type="range" min="0" max="7" value="0"><output id="number">1 / 8</output><div id="comparisons"></div><p id="status">이미지 로딩 중</p><script>
const comparisonFrameRecords=__RECORDS__;
const referenceImageSource='../../reusable/references/default-standing/v2/reference.png';
const previewCanvasWidth=360,previewCanvasHeight=270,subjectDisplayHeight=220,subjectBaselinePosition=240;
let currentFrameIndex=0,isPlaybackActive=true;
const frameSliderElement=document.getElementById('frame'),playbackToggleButton=document.getElementById('toggle');
function loadPreviewImage(imageSourceValue){return new Promise((resolveImageLoad,rejectImageLoad)=>{const loadedImageElement=new Image();loadedImageElement.onload=()=>resolveImageLoad(loadedImageElement);loadedImageElement.onerror=()=>rejectImageLoad(new Error(imageSourceValue));loadedImageElement.src=imageSourceValue})}
function drawComparisonSubject(canvasContextValue,subjectImageElement,subjectBoundsValues,subjectCenterPosition){const subjectWidthValue=subjectBoundsValues[2]-subjectBoundsValues[0],subjectHeightValue=subjectBoundsValues[3]-subjectBoundsValues[1],subjectScaleValue=subjectDisplayHeight/subjectHeightValue;canvasContextValue.drawImage(subjectImageElement,subjectBoundsValues[0],subjectBoundsValues[1],subjectWidthValue,subjectHeightValue,subjectCenterPosition-subjectWidthValue*subjectScaleValue/2,subjectBaselinePosition-subjectDisplayHeight,subjectWidthValue*subjectScaleValue,subjectDisplayHeight)}
async function initializeComparisonPreview(){
 const referenceImageElement=await loadPreviewImage(referenceImageSource);
 for(const comparisonFrameRecord of comparisonFrameRecords){
  const comparisonSectionElement=document.createElement('section');comparisonSectionElement.innerHTML='<h2>'+comparisonFrameRecord.direction+'</h2><div class="labels"><span>기본 스탠딩</span><span>걷기 v9</span></div><canvas width="360" height="270"></canvas>';document.getElementById('comparisons').append(comparisonSectionElement);
  comparisonFrameRecord.context=comparisonSectionElement.querySelector('canvas').getContext('2d');
  comparisonFrameRecord.images=await Promise.all(Array.from({length:8},(unusedArrayValue,frameIndexValue)=>loadPreviewImage(comparisonFrameRecord.direction+'/preview-'+String(frameIndexValue+1).padStart(4,'0')+'.png')));
 }
 function updatePreviewFrame(){for(const comparisonFrameRecord of comparisonFrameRecords){const canvasContextValue=comparisonFrameRecord.context;canvasContextValue.clearRect(0,0,previewCanvasWidth,previewCanvasHeight);for(let guideLineIndex=0;guideLineIndex<=5;guideLineIndex++){const guideLinePosition=subjectBaselinePosition-guideLineIndex*subjectDisplayHeight/5;canvasContextValue.strokeStyle=guideLineIndex===0?'#e7bb67':'#566177';canvasContextValue.beginPath();canvasContextValue.moveTo(0,guideLinePosition);canvasContextValue.lineTo(previewCanvasWidth,guideLinePosition);canvasContextValue.stroke()}drawComparisonSubject(canvasContextValue,referenceImageElement,comparisonFrameRecord.reference,90);drawComparisonSubject(canvasContextValue,comparisonFrameRecord.images[currentFrameIndex],comparisonFrameRecord.walking,270)}frameSliderElement.value=currentFrameIndex;document.getElementById('number').textContent=(currentFrameIndex+1)+' / 8'}
 playbackToggleButton.onclick=()=>{isPlaybackActive=!isPlaybackActive;playbackToggleButton.textContent=isPlaybackActive?'일시정지':'재생'};
 frameSliderElement.oninput=()=>{isPlaybackActive=false;playbackToggleButton.textContent='재생';currentFrameIndex=Number(frameSliderElement.value);updatePreviewFrame()};
 updatePreviewFrame();document.getElementById('status').textContent='4방향 로딩 완료 · 원본 스탠딩 에셋은 변경하지 않았습니다';setInterval(()=>{if(isPlaybackActive){currentFrameIndex=(currentFrameIndex+1)%8;updatePreviewFrame()}},150);
}
initializeComparisonPreview().catch(previewLoadError=>{document.getElementById('status').textContent='이미지 로드 실패: '+previewLoadError.message});
</script>""".replace('__RECORDS__',json.dumps(preview_comparison_records))
    (RENDER_OUTPUT_PATH/'preview.html').write_text(preview_html_text)
    (RENDER_OUTPUT_PATH/'comparison.json').write_text(json.dumps(preview_comparison_records,indent=2)+'\n')


def execute_render_pipeline():
    if OUTPUT_ASSET_PATH.exists() or RENDER_OUTPUT_PATH.exists():raise FileExistsError('불변 버전 덮어쓰기 금지')
    RENDER_OUTPUT_PATH.mkdir(parents=True)
    threading.Thread(target=emit_progress_heartbeat,daemon=True).start()
    try:
        write_trace_message('retarget','MoMask 원본 검증 및 5등신 길이 재배치')
        reference_asset_record=json.loads((REFERENCE_ASSET_PATH/'artifact.json').read_text())
        if hashlib.sha256((REFERENCE_ASSET_PATH/'reference.png').read_bytes()).hexdigest()!=reference_asset_record['sha256']:
            raise ValueError('기본 캐릭터 참조 해시 불일치')
        sample_joint_frames,motion_metadata_record=retarget_motion_sequence()
        motion_metadata_record['proportion_reference']=reference_asset_record
        motion_metadata_record['proportion_method']='standing-v2 시각적 비율 수동 추정; 자동 3D 피팅 아님'
        motion_metadata_record['motion_review']=dict(source_rig_version=4,status='user_accepted',scope='리그 동작 사용 가능; v6는 다리 확대 유지·목 메시 추가·어깨 0.08m 하향')
        motion_metadata_record['comparison_baseline']='five-head-walk/v8'
        motion_metadata_record['clavicle_vertical_scale']=.10
        motion_metadata_record['leg_length_scale']=1.10
        motion_metadata_record['silhouette_adjustment']='첨부 비교 이미지: 머리 크기·다리 관절 유지, 목 노출 및 연속 몸통·골반 메시 추가; 2D 시각적 추정'
        motion_metadata_record['rest_proportions']=dict(height_m=2.0,head_height_m=.4,head_width_m=.42,shoulder_width_m=.50,hip_height_m=1.0035,wrist_height_m=.83,shoulder_height_m=1.40,neck_top_height_m=1.60)
        render_metadata_record=build_render_scene(sample_joint_frames)
        artifact_metadata_record=dict(asset_id='five-head-walk',version=9,status='generated_review_required',motion=motion_metadata_record,render=render_metadata_record,files={str(file_path_value.relative_to(OUTPUT_ASSET_PATH)):hashlib.sha256(file_path_value.read_bytes()).hexdigest() for file_path_value in OUTPUT_ASSET_PATH.iterdir() if file_path_value.is_file()})
        (OUTPUT_ASSET_PATH/'artifact.json').write_text(json.dumps(artifact_metadata_record,ensure_ascii=False,indent=2)+'\n')
        render_file_records={str(file_path_value.relative_to(RENDER_OUTPUT_PATH)):hashlib.sha256(file_path_value.read_bytes()).hexdigest() for file_path_value in sorted(RENDER_OUTPUT_PATH.glob('*/*.png'))}
        if len(render_file_records)!=96:
            raise ValueError('렌더 산출물 96장 계약 불일치')
        (RENDER_OUTPUT_PATH/'manifest.json').write_text(json.dumps(dict(asset_id='five-head-walk',version=9,artifact_sha256=hashlib.sha256((OUTPUT_ASSET_PATH/'artifact.json').read_bytes()).hexdigest(),files=render_file_records),ensure_ascii=False,indent=2)+'\n')
        write_preview_gallery()
        write_trace_message('complete','4방향 Depth 32장·마스크 32장 저장')
    except Exception:
        write_trace_message('failure',traceback.format_exc())
        raise
    finally:
        HEARTBEAT_STOP_EVENT.set()

if __name__=='__main__':
    raise SystemExit('직접 실행하지 마세요. generators/animation/render_pose_frames.py를 사용하세요.')
