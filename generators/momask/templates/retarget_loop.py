"""저장된 위치 채널·골격 프로필을 공통 계산기로 ANNY 리그에 적용한다."""
from pathlib import Path
import hashlib
import json
import threading
import time

import bpy
import numpy as np
from mathutils import Matrix, Vector
from position_retarget import PositionRetargetSolver, RETARGET_ALGORITHM_VERSION, load_retarget_profile
from retarget_audit import write_coordinate_audit

EXPERIMENT_OUTPUT_ROOT = Path(__file__).resolve().parent
CURRENT_PROGRESS_STATE = {'stage': 'start', 'frame': 0}


def emit_progress_heartbeat():
    while True:
        print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/heartbeat {CURRENT_PROGRESS_STATE}', flush=True)
        time.sleep(5)


threading.Thread(target=emit_progress_heartbeat, daemon=True).start()
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/start output={EXPERIMENT_OUTPUT_ROOT}', flush=True)
source_motion_path = EXPERIMENT_OUTPUT_ROOT / 'inputs/mannequin-motion.npz'
source_manifest_record = json.loads((EXPERIMENT_OUTPUT_ROOT / 'inputs/artifact.json').read_text())
if hashlib.sha256(source_motion_path.read_bytes()).hexdigest() != source_manifest_record['files']['mannequin-motion.npz']:
    raise ValueError('위치 채널 입력 해시 불일치')
source_motion_bundle = np.load(source_motion_path, allow_pickle=False)
if set(source_motion_bundle.files) != {'joints', 'rest', 'contacts', 'sample_indices'}:
    raise ValueError('위치 채널 입력 필드 오류')
profile_source_path = EXPERIMENT_OUTPUT_ROOT / 'retarget-profile.yaml'
profile_record_values = load_retarget_profile(profile_source_path)
source_joint_frames = source_motion_bundle['joints']
if source_joint_frames.ndim != 3 or source_joint_frames.shape[1:] != (profile_record_values['joint_count'], 3) or not len(source_joint_frames) or not np.isfinite(source_joint_frames).all():
    raise ValueError('위치 채널 배열 형태·유한값 오류')
source_joint_frames = source_joint_frames @ np.asarray(profile_record_values['coordinate_matrix']).T
bpy.ops.wm.open_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT / 'inputs/anny-reference-fit-rig.blend'))
rig_object_value = bpy.data.objects['AnnyAttributesRig']
body_object_value = bpy.data.objects['AnnyAttributesBody']
rig_object_value.animation_data_clear()
rig_object_value.location = (0, 0, 0)
for current_skin_modifier in body_object_value.modifiers:
    if current_skin_modifier.type == 'ARMATURE':
        current_skin_modifier.use_deform_preserve_volume = True
for current_pose_bone in rig_object_value.pose.bones:
    current_pose_bone.matrix_basis = Matrix.Identity(4)
    current_pose_bone.rotation_mode = 'QUATERNION'
scene_render_value = bpy.context.scene
scene_render_value.frame_start = 1
scene_render_value.frame_end = len(source_joint_frames)
scene_render_value.render.fps = source_manifest_record['fps']
rest_bone_positions = {current_bone_value.name: current_bone_value.head_local.copy() for current_bone_value in rig_object_value.data.bones}
rest_bone_rotations = {current_bone_value.name: current_bone_value.matrix_local.to_quaternion() for current_bone_value in rig_object_value.data.bones}
position_retarget_solver = PositionRetargetSolver(profile_record_values, rest_bone_positions, rest_bone_rotations)
source_scale_start, source_scale_end = profile_record_values['scale_source']
target_scale_start, target_scale_end = profile_record_values['scale_target']
if target_scale_start not in rest_bone_positions or target_scale_end not in rest_bone_positions:
    raise ValueError('루트 이동 배율의 대상 본 누락')
source_scale_lengths = np.linalg.norm(source_joint_frames[:, source_scale_end] - source_joint_frames[:, source_scale_start], axis=1)
target_scale_length = (rest_bone_positions[target_scale_end] - rest_bone_positions[target_scale_start]).length
if np.min(source_scale_lengths) <= 1e-8 or target_scale_length <= 1e-8:
    raise ValueError('루트 이동 배율의 기준 구간 길이가 0입니다.')
motion_scale_value = target_scale_length / float(source_scale_lengths.mean())
CURRENT_PROGRESS_STATE['stage'] = 'coordinate-audit'
write_coordinate_audit(EXPERIMENT_OUTPUT_ROOT, source_motion_bundle['joints'],
                       profile_record_values, rest_bone_positions,
                       motion_scale_value, source_manifest_record)
source_root_index = profile_record_values['root_joint']
# 부모를 먼저 적용해야 전역 회전의 로컬 변환이 다음 본에 정확히 반영된다.
ordered_pose_bones = sorted(rig_object_value.pose.bones, key=lambda current_pose_bone: len(current_pose_bone.parent_recursive))
previous_bone_quaternions = {}
frame_diagnostic_records = []
actual_direction_errors = []
CURRENT_PROGRESS_STATE['stage'] = 'retarget'
for current_frame_index, current_joint_points in enumerate(source_joint_frames):
    current_frame_number = current_frame_index + 1
    CURRENT_PROGRESS_STATE['frame'] = current_frame_number
    scene_render_value.frame_set(current_frame_number)
    for current_pose_bone in ordered_pose_bones:
        current_pose_bone.matrix_basis = Matrix.Identity(4)
    rig_object_value.location = Vector((current_joint_points[source_root_index] - source_joint_frames[0, source_root_index]) * motion_scale_value)
    bpy.context.view_layer.update()
    frame_rotation_values, frame_diagnostic_values = position_retarget_solver.calculate_frame_rotations(current_joint_points)
    for current_pose_bone in ordered_pose_bones:
        current_bone_name = current_pose_bone.name
        if current_bone_name in frame_rotation_values:
            current_pose_bone.matrix = Matrix.Translation(current_pose_bone.head) @ frame_rotation_values[current_bone_name].to_matrix().to_4x4()
            current_pose_bone.location = (0, 0, 0)
            current_pose_bone.scale = (1, 1, 1)
            bpy.context.view_layer.update()
        previous_bone_rotation = previous_bone_quaternions.get(current_bone_name)
        if previous_bone_rotation is not None and previous_bone_rotation.dot(current_pose_bone.rotation_quaternion) < 0:
            current_pose_bone.rotation_quaternion.negate()
        previous_bone_quaternions[current_bone_name] = current_pose_bone.rotation_quaternion.copy()
        current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
    rig_object_value.keyframe_insert('location', frame=current_frame_number)
    bpy.context.view_layer.update()
    current_direction_errors = []
    for current_segment_record in profile_record_values['segments']:
        target_start_name, target_end_name = current_segment_record['target_primary']
        source_start_index, source_end_index = current_segment_record['source_primary']
        target_direction_value = (rig_object_value.pose.bones[target_end_name].head - rig_object_value.pose.bones[target_start_name].head).normalized()
        source_direction_value = Vector(current_joint_points[source_end_index] - current_joint_points[source_start_index]).normalized()
        expected_direction_value = Vector(frame_diagnostic_values[current_segment_record['segment_id']]['expected_target_direction'])
        source_alignment_degrees = float(np.degrees(np.arctan2(target_direction_value.cross(source_direction_value).length, target_direction_value.dot(source_direction_value))))
        current_error_degrees = float(np.degrees(np.arctan2(target_direction_value.cross(expected_direction_value).length, target_direction_value.dot(expected_direction_value))))
        current_direction_errors.append(current_error_degrees)
        frame_diagnostic_values[current_segment_record['segment_id']]['evaluated_direction_error_degrees'] = current_error_degrees
        frame_diagnostic_values[current_segment_record['segment_id']]['source_alignment_degrees'] = source_alignment_degrees
    actual_direction_errors.append(current_direction_errors)
    frame_diagnostic_records.append(frame_diagnostic_values)
rig_object_value.animation_data.action.name = f'MoMask_{len(source_joint_frames)}frames_{scene_render_value.render.fps}fps'
scene_render_value.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
body_object_value.select_set(True)
rig_object_value.select_set(True)
bpy.context.view_layer.objects.active = rig_object_value
CURRENT_PROGRESS_STATE['stage'] = 'export'
bpy.ops.export_scene.gltf(filepath=str(EXPERIMENT_OUTPUT_ROOT / 'mannequin.glb'), use_selection=True, export_animations=True, export_all_influences=True)
np.savez_compressed(EXPERIMENT_OUTPUT_ROOT / 'retarget-diagnostics.npz', direction_errors=np.asarray(actual_direction_errors))
retarget_quality_warnings = ['단일 방향 구간의 축 비틀림은 관측값이 아닌 연속 운반 규약입니다.', '미대응 본은 기준 로컬 자세를 유지합니다.', '접지·루프 재정합은 적용하지 않습니다.']
review_result_record = {
    'status': 'generated_review_required', 'source_motion': source_manifest_record['source_motion'],
    'source_sha256': source_manifest_record['files']['mannequin-motion.npz'],
    'frames': len(source_joint_frames), 'fps': scene_render_value.render.fps,
    'bones': len(rig_object_value.data.bones), 'motion_scale': motion_scale_value,
    'retarget_method': RETARGET_ALGORITHM_VERSION,
    'profile_id': profile_record_values['profile_id'],
    'profile_sha256': hashlib.sha256(profile_source_path.read_bytes()).hexdigest(),
    'solver_sha256': hashlib.sha256((EXPERIMENT_OUTPUT_ROOT / 'position_retarget.py').read_bytes()).hexdigest(),
    'ground_method': 'none', 'hand_pose': 'inherit-rest-local',
    'evaluated_direction_error_max_degrees': float(np.max(actual_direction_errors)),
    'frame_diagnostics': frame_diagnostic_records, 'quality_warnings': retarget_quality_warnings,
}
(EXPERIMENT_OUTPUT_ROOT / 'review-metrics.json').write_text(json.dumps(review_result_record, ensure_ascii=False, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(EXPERIMENT_OUTPUT_ROOT / 'mannequin.blend'))
CURRENT_PROGRESS_STATE['stage'] = 'completed'
print(f'{time.strftime("%Y-%m-%dT%H:%M:%S")}/anny-momask/completed direction_error={np.max(actual_direction_errors):.6f}', flush=True)
