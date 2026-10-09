"""위치 단계의 루트 이동을 보존하고 회전은 공식 로컬 채널로 한 번만 전달한다."""
import hashlib
import json
from pathlib import Path
import threading
import time
import bpy
import numpy as np
from generators.hy_motion.body_rotation_ownership import build_body_calibration, measure_body_rotation_errors, MAXIMUM_WORLD_MATRIX_ERROR
from generators.hy_motion.shoulder_rotation_ownership import apply_shoulder_rotations
from generators.hy_motion.rotation_channels import reconstruct_rotation_channels
from generators.hy_motion.knee_skin_correction import redistribute_knee_skin_weights

CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CURRENT_OUTPUT_DIRECTORY = Path(globals()['stage_output_directory'])
CURRENT_SOURCE_DIRECTORY = Path(globals()['source_job_directory'])
CURRENT_PROGRESS_RECORD = {'stage': 'prepare'}
CURRENT_FINISHED_EVENT = threading.Event()


def emit_transfer_heartbeat():
    while not CURRENT_FINISHED_EVENT.wait(5):
        print(f'{time.strftime("%FT%T")}/local-retarget/heartbeat {CURRENT_PROGRESS_RECORD}', flush=True)


threading.Thread(target=emit_transfer_heartbeat, daemon=True).start()
print(f'{time.strftime("%FT%T")}/local-retarget/start 입력={CURRENT_SOURCE_DIRECTORY} 출력={CURRENT_OUTPUT_DIRECTORY}', flush=True)
current_motion_path = CURRENT_SOURCE_DIRECTORY / 'motion.npz'
current_wooden_directory = CURRENT_REPOSITORY_ROOT / '.model/hy-motion/upstream/scripts/gradio/static/assets/dump_wooden'
current_source_names = json.loads((current_wooden_directory / 'joint_names.json').read_text())
current_rest_points = np.fromfile(current_wooden_directory / 'j_template.bin', dtype=np.float32).reshape(52, 3)
current_parent_indices = np.fromfile(current_wooden_directory / 'kintree.bin', dtype=np.int32)[:22]
with np.load(current_motion_path, allow_pickle=False) as current_motion_archive:
    current_local_rotations, current_global_rotations, current_fk_error = reconstruct_rotation_channels(current_motion_archive['rot6d'], current_rest_points[:22], current_parent_indices, current_motion_archive['transl'], current_motion_archive['world_joints'][:, :22])
current_baseline_path = CURRENT_OUTPUT_DIRECTORY.parent / 'mannequin.blend'
bpy.ops.wm.open_mainfile(filepath=str(current_baseline_path))
current_rig_object = bpy.data.objects['AnnyAttributesRig']
current_knee_correction = redistribute_knee_skin_weights(bpy.data.objects['AnnyAttributesBody'], current_rig_object)
current_rig_object['hy_motion_rotation_policy'] = 'body_local_ownership_v1'
current_calibration_record = build_body_calibration(current_source_names, current_rest_points, current_parent_indices, {current_bone_record.name: np.asarray(current_bone_record.matrix_local) for current_bone_record in current_rig_object.data.bones}, {current_bone_record.name: current_bone_record.parent.name if current_bone_record.parent else None for current_bone_record in current_rig_object.data.bones})
current_root_positions = []
for current_frame_number in range(1, len(current_local_rotations) + 1):
    bpy.context.scene.frame_set(current_frame_number)
    current_root_positions.append(current_rig_object.location.copy())
current_rig_object.animation_data_clear()
current_frame_records = []
current_previous_quaternions = {}
for current_frame_number, current_frame_rotations in enumerate(current_local_rotations, 1):
    CURRENT_PROGRESS_RECORD.update(stage='local-transfer', frame=current_frame_number, frames=len(current_local_rotations))
    bpy.context.scene.frame_set(current_frame_number)
    current_rig_object.location = current_root_positions[current_frame_number - 1]
    current_audit_records = apply_shoulder_rotations(current_rig_object, current_frame_rotations, current_calibration_record)
    current_world_errors = measure_body_rotation_errors(current_global_rotations[current_frame_number - 1], current_calibration_record, current_audit_records)
    for current_pose_bone in current_rig_object.pose.bones:
        current_pose_bone.rotation_mode = 'QUATERNION'
        if current_pose_bone.name in current_previous_quaternions and current_previous_quaternions[current_pose_bone.name].dot(current_pose_bone.rotation_quaternion) < 0:
            current_pose_bone.rotation_quaternion.negate()
        current_previous_quaternions[current_pose_bone.name] = current_pose_bone.rotation_quaternion.copy()
        current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
    current_rig_object.keyframe_insert('location', frame=current_frame_number)
    current_frame_records.append({'frame': current_frame_number, 'bones': current_audit_records, 'world_rotation_errors': current_world_errors})
current_candidate_directory = CURRENT_OUTPUT_DIRECTORY / 'full_rotation'
current_candidate_directory.mkdir(exist_ok=False)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(current_candidate_directory / 'mannequin.blend'))
# 기록 직전의 메모리 상태가 아니라 실제 저장된 키프레임을 다시 평가한다.
bpy.ops.wm.open_mainfile(filepath=str(current_candidate_directory / 'mannequin.blend'))
current_saved_rig = bpy.data.objects['AnnyAttributesRig']
current_saved_checks = []
for current_frame_record in current_frame_records:
    current_frame_number = current_frame_record['frame']
    CURRENT_PROGRESS_RECORD.update(stage='saved-animation-audit', frame=current_frame_number)
    bpy.context.scene.frame_set(current_frame_number)
    current_saved_bones = []
    current_local_errors = []
    for current_bone_record in current_frame_record['bones']:
        current_pose_bone = current_saved_rig.pose.bones[current_bone_record['bone']]
        current_expected_basis = np.eye(4)
        current_expected_basis[:3, :3] = current_bone_record['local_rotation']
        current_basis_error = float(np.max(np.abs(np.asarray(current_pose_bone.matrix_basis) - current_expected_basis)))
        if current_basis_error > MAXIMUM_WORLD_MATRIX_ERROR:
            raise ValueError(f'저장 후 로컬 회전·이동·크기 불일치: {current_frame_number}/{current_pose_bone.name}/{current_basis_error}')
        current_local_errors.append(current_basis_error)
        current_saved_bones.append({'bone': current_pose_bone.name, 'world_rotation': np.asarray(current_pose_bone.matrix.to_quaternion().to_matrix()).tolist()})
    current_world_errors = measure_body_rotation_errors(current_global_rotations[current_frame_number - 1], current_calibration_record, current_saved_bones)
    current_root_error = float(np.max(np.abs(np.asarray(current_saved_rig.location) - current_root_positions[current_frame_number - 1])))
    if current_root_error > MAXIMUM_WORLD_MATRIX_ERROR:
        raise ValueError(f'저장 후 루트 이동 불일치: {current_frame_number}/{current_root_error}')
    current_saved_checks.append({'frame': current_frame_number, 'local_bones_checked': len(current_local_errors), 'maximum_local_matrix_error': max(current_local_errors), 'world_rotation_errors': current_world_errors, 'root_translation_error_m': current_root_error})
current_hash_paths = [current_motion_path, current_baseline_path, Path(__file__), CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/body_rotation_ownership.py', CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/shoulder_rotation_ownership.py']
current_result_record = {'status': 'completed', 'profile': current_calibration_record, 'fk_error_m': current_fk_error, 'frames': current_frame_records, 'hashes': {str(current_file_path): hashlib.sha256(current_file_path.read_bytes()).hexdigest() for current_file_path in current_hash_paths}, 'quality_approved': False, 'skin_constraints_applied': False, 'compensation': False}
current_result_record['saved_animation_audit'] = {'status': 'passed', 'frames': current_saved_checks, 'scope': '정수 프레임의 전체 로컬 본·소유 본 세계 회전·루트 이동. 피부 품질 및 프레임 사이 보간은 미검증'}
current_result_record['knee_skin_weights'] = current_knee_correction
current_result_record['hashes'][str(CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/knee_skin_correction.py')] = hashlib.sha256((CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/knee_skin_correction.py').read_bytes()).hexdigest()
(CURRENT_OUTPUT_DIRECTORY / 'comparison.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
CURRENT_FINISHED_EVENT.set()
print(f'{time.strftime("%FT%T")}/local-retarget/completed 프레임={len(current_frame_records)} FK오차={current_fk_error}', flush=True)
