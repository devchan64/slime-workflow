"""ANNY 위치 리타기팅에 원본 팔 방향·손 기준계를 전달한다."""
from pathlib import Path
import sys
import json
import time
import hashlib
import threading
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CURRENT_OUTPUT_DIRECTORY = Path(globals()['stage_output_directory'])
CURRENT_BASELINE_PATH = CURRENT_OUTPUT_DIRECTORY.parent / 'mannequin.blend'
CURRENT_SOURCE_DIRECTORY = Path(globals()['source_job_directory'])
CURRENT_RUN_PROGRESS = {'stage': 'prepare'}
sys.path.insert(0, str(CURRENT_REPOSITORY_ROOT))
from generators.hy_motion.arm_retarget_data import collect_arm_evidence, load_arm_contract
from generators.hy_motion.arm_chain_transfer import apply_arm_directions
from generators.hy_motion.rotation_channels import reconstruct_rotation_channels
from generators.hy_motion.hand_frame_transfer import load_hand_calibration, build_hand_frame, transfer_hand_rotation
from generators.momask.body_proportion_retarget import build_surface_partitions, count_surface_intersections

def emit_experiment_heartbeat():
    while True:
        print(f'{time.strftime("%FT%T")}/chain-distribution/heartbeat {CURRENT_RUN_PROGRESS}', flush=True)
        time.sleep(5)

threading.Thread(target=emit_experiment_heartbeat, daemon=True).start()
print(f'{time.strftime("%FT%T")}/chain-distribution/start 입력={CURRENT_BASELINE_PATH} 출력={CURRENT_OUTPUT_DIRECTORY}', flush=True)
current_evidence_record = collect_arm_evidence()
current_contract_record = load_arm_contract()
current_hand_profile = load_hand_calibration(CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/config/anny-hand-landmarks.yaml')
current_job_record = json.loads((CURRENT_SOURCE_DIRECTORY / 'result.json').read_text())
current_motion_path = CURRENT_SOURCE_DIRECTORY / current_job_record['relative_path'] / 'motion.npz'
current_motion_archive = np.load(current_motion_path)
current_wooden_directory = CURRENT_REPOSITORY_ROOT / '.model/hy-motion/upstream/scripts/gradio/static/assets/dump_wooden'
current_rest_points = np.fromfile(current_wooden_directory / 'j_template.bin', dtype=np.float32).reshape(52, 3)
current_joint_names = json.loads((current_wooden_directory / 'joint_names.json').read_text())
current_parent_values = np.fromfile(current_wooden_directory / 'kintree.bin', dtype=np.int32)[:22]
current_local_rotations, current_global_rotations, current_fk_error = reconstruct_rotation_channels(current_motion_archive['rot6d'], current_rest_points[:22], current_parent_values, current_motion_archive['transl'], current_motion_archive['world_joints'][:, :22])
current_coordinate_matrix = np.asarray(current_contract_record['source_to_target_basis'])
current_source_positions = current_motion_archive['world_joints'] @ current_coordinate_matrix.T
bpy.ops.wm.open_mainfile(filepath=str(CURRENT_BASELINE_PATH))
current_rig_object = bpy.data.objects['AnnyAttributesRig']
current_body_object = bpy.data.objects['AnnyAttributesBody']
current_surface_faces = build_surface_partitions(current_body_object)
current_frame_count = len(current_source_positions)
current_saved_poses = []
current_hand_frames = {}
current_weight_records = {}
for current_side_name in ('left', 'right'):
    current_source_indices = [current_joint_names.index(current_joint_name) for current_joint_name in current_hand_profile['source_joint_names'][current_side_name]]
    current_target_names = current_hand_profile['target_bone_names'][current_side_name]
    current_hand_frames[current_side_name] = (build_hand_frame(current_rest_points[current_source_indices] @ current_coordinate_matrix.T), build_hand_frame([current_rig_object.data.bones[current_bone_name].head_local[:] for current_bone_name in current_target_names]), np.array(current_rig_object.data.bones[current_target_names[0]].matrix_local.to_quaternion().to_matrix()))
    for current_bone_name in current_contract_record['target_bone_chains'][current_side_name]:
        current_group_index = current_body_object.vertex_groups[current_bone_name].index
        current_weights_list = [current_group_record.weight for current_vertex_record in current_body_object.data.vertices for current_group_record in current_vertex_record.groups if current_group_record.group == current_group_index]
        current_weight_records[current_bone_name] = {'influenced_vertices': len(current_weights_list), 'weight_sum': sum(current_weights_list)}
    for current_endpoint_name, current_reference_name in zip(current_contract_record['target_segment_endpoints'][current_side_name], ('shoulder', 'elbow', 'wrist')):
        current_contract_matrix = next(current_bone_record['bind_matrix'] for current_bone_record in current_evidence_record['sides'][current_side_name]['target_chain'] if current_bone_record['name'] == current_endpoint_name)
        if np.linalg.norm(np.asarray(current_rig_object.data.bones[current_endpoint_name].head_local) - np.asarray(current_contract_matrix)[:3, 3]) > 1e-5:
            raise ValueError('실험 장면과 수집한 ANNY 기준 자세가 다릅니다.')
for current_frame_number in range(1, current_frame_count + 1):
    bpy.context.scene.frame_set(current_frame_number)
    current_saved_poses.append(({current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}, current_rig_object.location.copy()))
current_rig_object.animation_data_clear()
current_frame_records, current_probe_records = [], []
current_previous_rotations = {}
current_arm_names = {current_bone_name for current_side_name in ('left', 'right') for current_bone_name in current_contract_record['target_bone_chains'][current_side_name][2:]}
for current_frame_number in range(1, current_frame_count + 1):
    CURRENT_RUN_PROGRESS.update(stage='apply-and-probe', frame=current_frame_number, frames=current_frame_count)
    bpy.context.scene.frame_set(current_frame_number)
    current_saved_bones, current_root_location = current_saved_poses[current_frame_number - 1]
    current_rig_object.location = current_root_location
    for current_pose_bone in current_rig_object.pose.bones:
        current_pose_bone.matrix_basis = current_saved_bones[current_pose_bone.name]
    bpy.context.view_layer.update()
    current_before_counts = count_surface_intersections(current_body_object, current_surface_faces)
    current_side_metrics = {}
    for current_side_name in ('left', 'right'):
        current_endpoint_names = current_contract_record['target_segment_endpoints'][current_side_name]
        current_indices_values = [current_joint_names.index(current_joint_name) for current_joint_name in current_contract_record['source_joint_chains'][current_side_name][1:]]
        current_shoulder_before = current_rig_object.pose.bones[current_endpoint_names[0]].head.copy()
        apply_arm_directions(current_rig_object, current_contract_record['target_bone_chains'][current_side_name], current_endpoint_names, current_source_positions[current_frame_number - 1, current_indices_values])
        current_hand_source, current_hand_target, current_hand_bind = current_hand_frames[current_side_name]
        current_source_rotation = current_coordinate_matrix @ current_global_rotations[current_frame_number - 1, current_indices_values[-1]] @ current_coordinate_matrix.T
        current_wrist_bone = current_rig_object.pose.bones[current_endpoint_names[-1]]
        current_wrist_rotation = transfer_hand_rotation(current_source_rotation, current_hand_source, current_hand_target, current_hand_bind)
        current_wrist_bone.matrix = Matrix.Translation(current_wrist_bone.head) @ Matrix(current_wrist_rotation).to_4x4()
        current_wrist_bone.location = (0, 0, 0)
        current_wrist_bone.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        current_points_values = np.asarray([current_rig_object.pose.bones[current_bone_name].head[:] for current_bone_name in current_endpoint_names])
        current_length_errors = np.linalg.norm(np.diff(current_points_values, axis=0), axis=1) - current_evidence_record['sides'][current_side_name]['target_metrics']['lengths_m']
        current_hand_actual = build_hand_frame([current_rig_object.pose.bones[current_bone_name].head[:] for current_bone_name in current_hand_profile['target_bone_names'][current_side_name]])
        current_hand_error = float(np.max(np.abs(current_hand_actual - current_source_rotation @ current_hand_source)))
        current_shoulder_error = (current_rig_object.pose.bones[current_endpoint_names[0]].head - current_shoulder_before).length
        if np.max(np.abs(current_length_errors)) > 1e-5 or current_shoulder_error > 1e-6 or current_hand_error > 1e-5:
            raise ValueError('길이·어깨 위치·손목 기준계 검증 실패')
        current_side_metrics[current_side_name] = {'length_error_m': current_length_errors.tolist(), 'shoulder_shift_m': current_shoulder_error, 'hand_frame_error': current_hand_error, 'centers': current_points_values.tolist()}
    current_after_counts = count_surface_intersections(current_body_object, current_surface_faces)
    current_applied_poses = {current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}
    for current_pose_bone in current_rig_object.pose.bones:
        current_pose_bone.matrix_basis = current_applied_poses[current_pose_bone.name]
        if current_pose_bone.name not in current_arm_names and np.max(np.abs(np.asarray(current_pose_bone.matrix_basis) - np.asarray(current_saved_bones[current_pose_bone.name]))) > 1e-6:
            raise ValueError('비대상 본 변경')
        current_pose_bone.rotation_mode = 'QUATERNION'
        if current_pose_bone.name in current_previous_rotations and current_previous_rotations[current_pose_bone.name].dot(current_pose_bone.rotation_quaternion) < 0:
            current_pose_bone.rotation_quaternion.negate()
        current_previous_rotations[current_pose_bone.name] = current_pose_bone.rotation_quaternion.copy()
        current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
    if (current_rig_object.location - current_root_location).length > 1e-8:
        raise ValueError('루트 이동 변경')
    current_rig_object.keyframe_insert('location', frame=current_frame_number)
    current_frame_records.append({'frame': current_frame_number, 'before': current_before_counts, 'after': current_after_counts, 'sides': current_side_metrics})
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(CURRENT_OUTPUT_DIRECTORY / 'mannequin.blend'))
current_result_record = {'status': 'completed', 'source_sha256': hashlib.sha256(current_motion_path.read_bytes()).hexdigest(), 'baseline_sha256': hashlib.sha256(CURRENT_BASELINE_PATH.read_bytes()).hexdigest(), 'evidence': current_evidence_record, 'fk_error_m': current_fk_error, 'weights': current_weight_records, 'frames': current_frame_records, 'probes': current_probe_records, 'clinical_limits_applied': False, 'probe_note': '출력 파이프라인에서는 별도 회전 자극 진단을 실행하지 않음'}
(CURRENT_OUTPUT_DIRECTORY / 'comparison.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
print(f'{time.strftime("%FT%T")}/chain-distribution/completed 프레임={current_frame_count} 진단={len(current_probe_records)}', flush=True)
