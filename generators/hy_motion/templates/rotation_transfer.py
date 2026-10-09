"""원본 전체 클립의 회전 채널을 ANNY 상완·전완에 분리 전달한다."""
from pathlib import Path
import sys
import json
import math
import time
import threading
import hashlib
import bpy
import numpy as np

CURRENT_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CURRENT_OUTPUT_DIRECTORY = Path(globals()['stage_output_directory'])
CURRENT_BASELINE_PATH = CURRENT_OUTPUT_DIRECTORY.parent / 'arms/mannequin.blend'
CURRENT_SOURCE_DIRECTORY = Path(globals()['source_job_directory'])
CURRENT_CANDIDATE_RECORDS = {'full_rotation': (0, 1)}
CURRENT_RUN_PROGRESS = {'stage': 'prepare'}
sys.path.insert(0, str(CURRENT_REPOSITORY_ROOT))
from generators.hy_motion.arm_retarget_data import load_arm_contract
from generators.hy_motion.rotation_channels import reconstruct_rotation_channels
from generators.hy_motion.segment_rotation_transfer import transfer_segment_rotation, measure_segment_twist
from generators.hy_motion.arm_chain_transfer import redistribute_segment_twist
from generators.momask.body_proportion_retarget import build_surface_partitions, count_surface_intersections


def emit_experiment_heartbeat():
    while True:
        print(f'{time.strftime("%FT%T")}/source-rotation/heartbeat {CURRENT_RUN_PROGRESS}', flush=True)
        time.sleep(5)


threading.Thread(target=emit_experiment_heartbeat, daemon=True).start()
print(f'{time.strftime("%FT%T")}/source-rotation/start baseline={CURRENT_BASELINE_PATH} source={CURRENT_SOURCE_DIRECTORY} output={CURRENT_OUTPUT_DIRECTORY}', flush=True)
current_contract_record = load_arm_contract()
current_job_record = json.loads((CURRENT_SOURCE_DIRECTORY / 'result.json').read_text())
current_motion_path = CURRENT_SOURCE_DIRECTORY / current_job_record['relative_path'] / 'motion.npz'
current_motion_archive = np.load(current_motion_path)
current_wooden_directory = CURRENT_REPOSITORY_ROOT / '.model/hy-motion/upstream/scripts/gradio/static/assets/dump_wooden'
current_rest_points = np.fromfile(current_wooden_directory / 'j_template.bin', dtype=np.float32).reshape(52, 3)
current_joint_names = json.loads((current_wooden_directory / 'joint_names.json').read_text())
current_parent_values = np.fromfile(current_wooden_directory / 'kintree.bin', dtype=np.int32)[:22]
current_local_rotations, current_global_rotations, current_fk_error = reconstruct_rotation_channels(current_motion_archive['rot6d'], current_rest_points[:22], current_parent_values, current_motion_archive['transl'], current_motion_archive['world_joints'][:, :22])
current_coordinate_matrix = np.asarray(current_contract_record['source_to_target_basis'])
current_frame_count = len(current_global_rotations)
current_candidate_results = {}
for current_candidate_name, current_active_segments in CURRENT_CANDIDATE_RECORDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(CURRENT_BASELINE_PATH))
    current_rig_object = bpy.data.objects['AnnyAttributesRig']
    current_body_object = bpy.data.objects['AnnyAttributesBody']
    current_surface_faces = build_surface_partitions(current_body_object)
    current_center_names = [current_bone_name for current_side_name in ('left', 'right') for current_bone_name in current_contract_record['target_segment_endpoints'][current_side_name]]
    current_target_names = {current_bone_name for current_side_name in ('left', 'right') for current_bone_name in current_contract_record['target_bone_chains'][current_side_name][2:]}
    current_saved_frames = []
    for current_frame_number in range(1, current_frame_count + 1):
        bpy.context.scene.frame_set(current_frame_number)
        current_saved_frames.append(({current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}, current_rig_object.location.copy(), {current_bone_name: current_rig_object.pose.bones[current_bone_name].head.copy() for current_bone_name in current_center_names}, {current_bone_name: np.asarray(current_rig_object.pose.bones[current_bone_name].matrix.to_quaternion().to_matrix()).copy() for current_bone_name in ('wrist.L', 'wrist.R')}))
    current_rig_object.animation_data_clear()
    current_frame_records = []
    current_previous_rotations = {}
    current_previous_local_rotations = {}
    for current_frame_number, (current_saved_poses, current_root_location, current_center_points, current_wrist_rotations) in enumerate(current_saved_frames, 1):
        CURRENT_RUN_PROGRESS.update(candidate=current_candidate_name, frame=current_frame_number)
        bpy.context.scene.frame_set(current_frame_number)
        current_rig_object.location = current_root_location
        for current_pose_bone in current_rig_object.pose.bones:
            current_pose_bone.matrix_basis = current_saved_poses[current_pose_bone.name]
        bpy.context.view_layer.update()
        current_segment_records = {}
        for current_side_name in ('left', 'right'):
            current_endpoint_names = current_contract_record['target_segment_endpoints'][current_side_name]
            current_chain_names = current_contract_record['target_bone_chains'][current_side_name]
            current_source_indices = [current_joint_names.index(current_joint_name) for current_joint_name in current_contract_record['source_joint_chains'][current_side_name][1:]]
            for current_segment_index in (0, 1):
                current_start_name, current_end_name = current_endpoint_names[current_segment_index:current_segment_index + 2]
                current_start_bone = current_rig_object.pose.bones[current_start_name]
                current_start_index, current_end_index = current_source_indices[current_segment_index:current_segment_index + 2]
                current_source_rotation = current_coordinate_matrix @ current_global_rotations[current_frame_number - 1, current_start_index] @ current_coordinate_matrix.T
                current_source_vector = current_coordinate_matrix @ (current_rest_points[current_end_index] - current_rest_points[current_start_index])
                current_target_vector = np.asarray(current_rig_object.data.bones[current_end_name].head_local) - np.asarray(current_rig_object.data.bones[current_start_name].head_local)
                current_bind_rotation = np.asarray(current_rig_object.data.bones[current_start_name].matrix_local.to_quaternion().to_matrix())
                current_desired_rotation = transfer_segment_rotation(current_source_rotation, current_source_vector, current_target_vector, current_bind_rotation)
                current_actual_rotation = np.asarray(current_start_bone.matrix.to_quaternion().to_matrix())
                current_axis_vector = np.asarray(current_rig_object.pose.bones[current_end_name].head - current_start_bone.head)
                current_twist_angle = measure_segment_twist(current_actual_rotation, current_desired_rotation, current_axis_vector)
                if current_segment_index in current_active_segments:
                    current_segment_names = current_chain_names[2 + 2 * current_segment_index:5 + 2 * current_segment_index]
                    redistribute_segment_twist(current_rig_object, current_segment_names, current_twist_angle, 0)
                current_orientation_error = float(np.max(np.abs(np.asarray(current_start_bone.matrix.to_quaternion().to_matrix()) - current_desired_rotation)))
                if current_segment_index in current_active_segments and current_orientation_error > 1e-5:
                    raise ValueError('원본 기반 세그먼트 회전 전달 실패')
                current_segment_records[current_start_name] = {'source_twist_degrees': math.degrees(current_twist_angle), 'orientation_matrix_error': current_orientation_error, 'applied': current_segment_index in current_active_segments}
        current_center_error = max((current_rig_object.pose.bones[current_bone_name].head - current_center_points[current_bone_name]).length for current_bone_name in current_center_names)
        current_wrist_error = max(float(np.max(np.abs(np.asarray(current_rig_object.pose.bones[current_bone_name].matrix.to_quaternion().to_matrix()) - current_wrist_rotations[current_bone_name]))) for current_bone_name in ('wrist.L', 'wrist.R'))
        if current_center_error > 1e-5 or current_wrist_error > 1e-5:
            raise ValueError('주요 관절 중심 또는 손목 방향 보존 실패')
        from generators.hy_motion.shoulder_comparison import measure_shoulder_difference
        current_shoulder_comparison = {}
        for current_side_name, current_source_indices in (('L', [9, 13, 16]), ('R', [9, 14, 17])):
            current_source_points = current_motion_archive['world_joints'][current_frame_number - 1, current_source_indices] @ current_coordinate_matrix.T
            current_target_points = np.asarray([current_rig_object.pose.bones[current_bone_prefix + '.' + current_side_name].head[:] for current_bone_prefix in ('clavicle', 'shoulder01', 'upperarm01')])
            current_shoulder_comparison[current_side_name] = measure_shoulder_difference(current_source_points, current_target_points)
        current_intersection_counts = count_surface_intersections(current_body_object, current_surface_faces)
        current_rotation_steps = []
        for current_pose_bone in current_rig_object.pose.bones:
            if current_pose_bone.name not in current_target_names and np.max(np.abs(np.asarray(current_pose_bone.matrix_basis) - np.asarray(current_saved_poses[current_pose_bone.name]))) > 1e-6:
                raise ValueError('비대상 로컬 자세 변경')
            current_global_quaternion = current_pose_bone.matrix.to_quaternion()
            if current_pose_bone.name in current_previous_rotations:
                current_rotation_steps.append(math.degrees(2 * math.acos(min(1, abs(current_previous_rotations[current_pose_bone.name].normalized().dot(current_global_quaternion.normalized()))))))
            current_previous_rotations[current_pose_bone.name] = current_global_quaternion.copy()
            current_pose_bone.rotation_mode = 'QUATERNION'
            if current_pose_bone.name in current_previous_local_rotations and current_previous_local_rotations[current_pose_bone.name].dot(current_pose_bone.rotation_quaternion) < 0:
                current_pose_bone.rotation_quaternion.negate()
            current_previous_local_rotations[current_pose_bone.name] = current_pose_bone.rotation_quaternion.copy()
            current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
        if (current_rig_object.location - current_root_location).length > 1e-8:
            raise ValueError('루트 이동 변경')
        current_rig_object.keyframe_insert('location', frame=current_frame_number)
        current_frame_records.append({'frame': current_frame_number, 'shoulder_comparison_before_skin': current_shoulder_comparison, 'intersections': current_intersection_counts, 'center_error_m': current_center_error, 'wrist_matrix_error': current_wrist_error, 'max_global_rotation_step_degrees': max(current_rotation_steps, default=0), 'segments': current_segment_records})
    current_candidate_path = CURRENT_OUTPUT_DIRECTORY / current_candidate_name
    current_candidate_path.mkdir()
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(current_candidate_path / 'mannequin.blend'))
    current_summary_record = {'intersections_mean': {current_side_name: float(np.mean([current_frame_record['intersections'][current_side_name] for current_frame_record in current_frame_records])) for current_side_name in ('L', 'R')}, 'max_center_error_m': max(current_frame_record['center_error_m'] for current_frame_record in current_frame_records), 'max_wrist_matrix_error': max(current_frame_record['wrist_matrix_error'] for current_frame_record in current_frame_records), 'max_global_rotation_step_degrees': max(current_frame_record['max_global_rotation_step_degrees'] for current_frame_record in current_frame_records)}
    current_candidate_results[current_candidate_name] = {'summary': current_summary_record, 'frames': current_frame_records}
    print(f'{time.strftime("%FT%T")}/source-rotation/candidate {current_candidate_name} {current_summary_record}', flush=True)
current_hash_paths = [CURRENT_BASELINE_PATH, current_motion_path, Path(__file__), CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/segment_rotation_transfer.py', CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/arm_chain_transfer.py', CURRENT_REPOSITORY_ROOT / 'generators/hy_motion/config/arm-retarget-contract.yaml']
current_result_record = {'status': 'completed', 'hashes': {str(current_file_path): hashlib.sha256(current_file_path.read_bytes()).hexdigest() for current_file_path in current_hash_paths}, 'fk_error_m': current_fk_error, 'candidates': current_candidate_results, 'clinical_limits_applied': False, 'automatic_adoption': False, 'reference_policy': '대상→원본 기준 중심선 최소 회전 정렬. 축 회전 영점의 해부학적 동일성은 미검증. 시작 본에 원본 회전을 적용하고 하위 방향을 복원하여 분리 비교한다.'}
(CURRENT_OUTPUT_DIRECTORY / 'comparison.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
print(f'{time.strftime("%FT%T")}/source-rotation/completed 1후보 × {current_frame_count}프레임', flush=True)
