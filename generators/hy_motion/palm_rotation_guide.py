"""손 기준점과 손목 로컬 회전 제거 대조군. 모션은 수정하지 않는다."""
import numpy as np
from generators.hy_motion.hand_frame_transfer import build_hand_frame

PALM_GUIDE_LENGTH = 0.12


def build_palm_comparison(current_world_joints, current_global_rotations, current_rest_points, current_joint_names):
    current_point_groups = []
    current_angle_groups = []
    for current_side_name, current_wrist_index, current_parent_index in (('L', 20, 18), ('R', 21, 19)):
        current_joint_indices = [current_joint_names.index(current_side_name + '_' + current_joint_name) for current_joint_name in ('Wrist', 'Middle1', 'Index1', 'Pinky1')]
        current_rest_frame = build_hand_frame(current_rest_points[current_joint_indices])
        current_actual_frames = np.stack([build_hand_frame(current_frame_points[current_joint_indices]) for current_frame_points in current_world_joints])
        current_expected_frames = current_global_rotations[:, current_wrist_index] @ current_rest_frame
        if not np.allclose(current_actual_frames, current_expected_frames, atol=1e-5):
            raise ValueError('손 기준점과 원본 손목 회전이 일치하지 않습니다.')
        current_fixed_frames = current_global_rotations[:, current_parent_index] @ current_rest_frame
        current_wrist_points = current_world_joints[:, current_wrist_index, None, :]
        current_point_groups.extend([current_wrist_points + current_axis_frames.transpose(0, 2, 1) * PALM_GUIDE_LENGTH for current_axis_frames in (current_actual_frames, current_fixed_frames)])
        current_relative_frames = current_fixed_frames.transpose(0, 2, 1) @ current_actual_frames
        current_angle_groups.append(np.degrees(np.arccos(np.clip((np.trace(current_relative_frames, axis1=1, axis2=2) - 1) / 2, -1, 1))))
    return np.concatenate(current_point_groups, axis=1), np.stack(current_angle_groups, axis=1)
