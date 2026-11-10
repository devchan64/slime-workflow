"""8방향 2D 검출을 공통 3D 관절로 맞추는 비파괴 실험.

정사영과 약한 자세 차이를 가정한다. 추정값은 생산용 체형으로 확정하지 않는다.
"""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

MULTIVIEW_BODY_JOINTS = tuple(range(2, 14))
MULTIVIEW_LIMB_PAIRS = ((2, 3), (3, 4), (5, 6), (6, 7), (8, 9), (9, 10), (11, 12), (12, 13))
MULTIVIEW_SYMMETRIC_PAIRS = (((2, 3), (5, 6)), ((3, 4), (6, 7)), ((8, 9), (11, 12)), ((9, 10), (12, 13)))
MULTIVIEW_MINIMUM_SCORE = 0.6
MULTIVIEW_ANGLE_LIMIT_DEGREES = 15.0
MULTIVIEW_MAXIMUM_FIT_EVALUATIONS = 300
MULTIVIEW_OVERLAP_FRACTION = 0.25
MULTIVIEW_OCCLUDED_WEIGHT = 0.2
MULTIVIEW_POSE_PRIOR_WEIGHT = 0.06
MULTIVIEW_SYMMETRY_PRIOR_WEIGHT = 0.15
MULTIVIEW_CAMERA_PRIOR_WEIGHT = 0.15
MULTIVIEW_POSE_ANGLE_LIMIT_DEGREES = 15.0
MULTIVIEW_POSE_ANGLE_PRIOR_WEIGHT = 0.08
MULTIVIEW_HOLDOUT_JOINTS = (3, 6, 9, 12, 4, 7, 10, 13)


def project_multiview_joints(current_joint_positions, current_camera_angles, current_camera_scales, current_camera_offsets, current_limb_angles):
    """공통 자세를 정사영하고 방향별 투영 팔·다리 각도의 차이를 완화한다."""
    current_projected_points = np.stack((np.cos(current_camera_angles)[:, None] * current_joint_positions[None, :, 0] + np.sin(current_camera_angles)[:, None] * current_joint_positions[None, :, 2], np.broadcast_to(-current_joint_positions[None, :, 1], (8, 12))), axis=-1)
    for current_limb_index, current_limb_chain in enumerate(((0, 1, 2), (3, 4, 5), (6, 7, 8), (9, 10, 11))):
        current_limb_offsets = current_projected_points[:, current_limb_chain[1:], :] - current_projected_points[:, current_limb_chain[0], None, :]
        current_angle_cosines = np.cos(current_limb_angles[:, current_limb_index, None])
        current_angle_sines = np.sin(current_limb_angles[:, current_limb_index, None])
        current_rotated_offsets = np.stack((current_limb_offsets[:, :, 0] * current_angle_cosines - current_limb_offsets[:, :, 1] * current_angle_sines, current_limb_offsets[:, :, 0] * current_angle_sines + current_limb_offsets[:, :, 1] * current_angle_cosines), axis=-1)
        current_projected_points[:, current_limb_chain[1:], :] = current_projected_points[:, current_limb_chain[0], None, :] + current_rotated_offsets
    return current_projected_points * current_camera_scales[:, None, None] + current_camera_offsets[:, None, :]


def prepare_multiview_observations(current_reference_record, current_view_angles, current_holdout_joints=None):
    """각도는 입력 순서에 대응하는 명시적 가정이며 검출 순서로 추론하지 않는다."""
    current_reference_points = current_reference_record['keypoints']
    current_source_records = current_reference_record['observation_sources']
    if len(current_reference_points) != 8 or len(current_source_records) != 8 or len(current_view_angles) != 8:
        raise ValueError('8개 관측과 명시적 카메라 각도 8개가 필요합니다.')
    current_observation_points = []
    current_observation_weights = []
    current_hip_centers = []
    current_box_heights = []
    for current_view_index, (current_point_record, current_source_record) in enumerate(zip(current_reference_points, current_source_records)):
        current_point_array = np.asarray(current_point_record, dtype=float)
        current_box_array = np.asarray(current_source_record['bbox'], dtype=float)
        if current_point_array.shape != (18, 3) or current_box_array.shape != (4,) or not np.isfinite(current_point_array).all() or not np.isfinite(current_box_array).all():
            raise ValueError('참조 관절 또는 검출 상자 형식 오류')
        current_box_height = float(current_box_array[3] - current_box_array[1])
        if current_box_height <= 0 or current_point_array[[8, 11], 2].min() < MULTIVIEW_MINIMUM_SCORE:
            raise ValueError('참조 인물 높이 또는 골반 관측이 유효하지 않습니다.')
        current_hip_center = current_point_array[[8, 11], :2].mean(axis=0)
        current_normalized_points = (current_point_array[list(MULTIVIEW_BODY_JOINTS), :2] - current_hip_center) / current_box_height
        current_joint_weights = np.where(current_point_array[list(MULTIVIEW_BODY_JOINTS), 2] >= MULTIVIEW_MINIMUM_SCORE, np.clip(current_point_array[list(MULTIVIEW_BODY_JOINTS), 2], 0, 1), 0.0)
        for current_left_pair, current_right_pair in MULTIVIEW_SYMMETRIC_PAIRS:
            if current_holdout_joints is not None and current_holdout_joints[current_view_index] in (*current_left_pair, *current_right_pair):
                continue
            current_lengths = [np.linalg.norm(current_point_array[current_pair[1], :2] - current_point_array[current_pair[0], :2]) for current_pair in (current_left_pair, current_right_pair)]
            current_average_length = float(np.mean(current_lengths))
            if current_average_length > 0 and all(np.linalg.norm(current_point_array[current_left_index, :2] - current_point_array[current_right_index, :2]) <= MULTIVIEW_OVERLAP_FRACTION * current_average_length for current_left_index, current_right_index in zip(current_left_pair, current_right_pair)):
                current_pair_scores = [float(current_point_array[list(current_pair), 2].min()) for current_pair in (current_left_pair, current_right_pair)]
                current_occluded_pair = (current_left_pair, current_right_pair)[int(np.argmin(current_pair_scores))]
                for current_joint_index in current_occluded_pair:
                    current_joint_weights[current_joint_index - 2] *= MULTIVIEW_OCCLUDED_WEIGHT
        current_observation_points.append(current_normalized_points)
        current_observation_weights.append(current_joint_weights)
        current_hip_centers.append(current_hip_center)
        current_box_heights.append(current_box_height)
    return np.asarray(current_observation_points), np.asarray(current_observation_weights), np.asarray(current_hip_centers), np.asarray(current_box_heights)


def fit_multiview_reference(current_reference_record, current_view_angles, current_holdout_joints=MULTIVIEW_HOLDOUT_JOINTS):
    """8방향 공통 자세와 카메라를 최적화하고 제외한 관측을 별도로 평가한다."""
    current_view_angles = np.asarray(current_view_angles, dtype=float)
    if current_view_angles.shape != (8,) or not np.isfinite(current_view_angles).all():
        raise ValueError('카메라 각도 형식 오류')
    if len({round(float(current_angle_value)%360,6) for current_angle_value in current_view_angles})!=8:
        raise ValueError('다중 시점 카메라 각도 8개가 서로 달라야 합니다.')
    if len(current_holdout_joints) != 8 or any(type(current_joint_index) is not int or current_joint_index not in MULTIVIEW_BODY_JOINTS or current_joint_index in (8, 11) for current_joint_index in current_holdout_joints):
        raise ValueError('방향별 검증 관절 형식 오류')
    current_observations, current_weights, current_centers, current_heights = prepare_multiview_observations(current_reference_record, current_view_angles, current_holdout_joints)
    current_training_weights = current_weights.copy()
    for current_view_index, current_joint_index in enumerate(current_holdout_joints):
        if current_weights[current_view_index, current_joint_index - 2] <= 0:
            raise ValueError('검증 대상으로 선택한 관절이 유효하지 않습니다.')
        current_training_weights[current_view_index, current_joint_index - 2] = 0
    current_front_index = int(np.argmin(np.abs(current_view_angles)))
    current_initial_joints = np.column_stack((current_observations[current_front_index, :, 0], -current_observations[current_front_index, :, 1], np.zeros(12)))
    current_initial_angles = np.deg2rad(current_view_angles)
    # 검증용 점은 초기 위치와 자세 정규화에도 사용하지 않는다.
    for current_joint_offset in range(12):
        if current_training_weights[current_front_index, current_joint_offset] == 0:
            current_available_views = np.flatnonzero(current_training_weights[:, current_joint_offset] > 0)
            if not len(current_available_views):
                raise ValueError('초기 관절을 추정할 학습 관측이 없습니다.')
            current_start_index = int(current_available_views[np.argmax(np.abs(np.cos(current_initial_angles[current_available_views])))])
            current_cosine_value = float(np.cos(current_initial_angles[current_start_index]))
            if abs(current_cosine_value) < 0.2:
                raise ValueError('초기 관절을 추정할 정면·후면 관측이 부족합니다.')
            current_initial_joints[current_joint_offset, :2] = [current_observations[current_start_index, current_joint_offset, 0] / current_cosine_value, -current_observations[current_start_index, current_joint_offset, 1]]
    current_initial_parameters = np.concatenate((current_initial_joints.ravel(), current_initial_angles, np.ones(8), np.zeros(16), np.zeros(32)))
    current_lower_bounds = np.concatenate((np.full(36, -2.0), current_initial_angles - np.deg2rad(MULTIVIEW_ANGLE_LIMIT_DEGREES), np.full(8, 0.8), np.full(16, -0.15), np.full(32, -np.deg2rad(MULTIVIEW_POSE_ANGLE_LIMIT_DEGREES))))
    current_upper_bounds = np.concatenate((np.full(36, 2.0), current_initial_angles + np.deg2rad(MULTIVIEW_ANGLE_LIMIT_DEGREES), np.full(8, 1.2), np.full(16, 0.15), np.full(32, np.deg2rad(MULTIVIEW_POSE_ANGLE_LIMIT_DEGREES))))

    def calculate_multiview_residuals(current_fit_parameters):
        current_joint_positions = current_fit_parameters[:36].reshape(12, 3)
        current_camera_angles = current_fit_parameters[36:44]
        current_camera_scales = current_fit_parameters[44:52]
        current_camera_offsets = current_fit_parameters[52:68].reshape(8, 2)
        current_limb_angles = current_fit_parameters[68:100].reshape(8, 4)
        current_projected_points = project_multiview_joints(current_joint_positions, current_camera_angles, current_camera_scales, current_camera_offsets, current_limb_angles)
        current_reprojection_residuals = ((current_projected_points - current_observations) * np.sqrt(current_training_weights[:, :, None])).ravel()
        current_symmetry_residuals = []
        for current_left_pair, current_right_pair in MULTIVIEW_SYMMETRIC_PAIRS:
            current_left_length = np.linalg.norm(current_joint_positions[current_left_pair[0] - 2] - current_joint_positions[current_left_pair[1] - 2])
            current_right_length = np.linalg.norm(current_joint_positions[current_right_pair[0] - 2] - current_joint_positions[current_right_pair[1] - 2])
            current_symmetry_residuals.append((current_left_length - current_right_length) * MULTIVIEW_SYMMETRY_PRIOR_WEIGHT)
        return np.concatenate((current_reprojection_residuals, np.asarray(current_symmetry_residuals), ((current_joint_positions - current_initial_joints) * MULTIVIEW_POSE_PRIOR_WEIGHT).ravel(), (current_camera_angles - current_initial_angles) * MULTIVIEW_CAMERA_PRIOR_WEIGHT, (current_camera_scales - 1) * MULTIVIEW_CAMERA_PRIOR_WEIGHT, current_camera_offsets.ravel() * MULTIVIEW_CAMERA_PRIOR_WEIGHT, current_limb_angles.ravel() * MULTIVIEW_POSE_ANGLE_PRIOR_WEIGHT))

    current_fit_result = least_squares(calculate_multiview_residuals, current_initial_parameters, bounds=(current_lower_bounds, current_upper_bounds), loss='soft_l1', f_scale=0.02, max_nfev=MULTIVIEW_MAXIMUM_FIT_EVALUATIONS)
    if not current_fit_result.success or not np.isfinite(current_fit_result.x).all():
        raise RuntimeError(f'8방향 스켈레톤 최적화 실패: {current_fit_result.message}')
    current_joint_positions = current_fit_result.x[:36].reshape(12, 3)
    current_camera_angles = current_fit_result.x[36:44]
    current_camera_scales = current_fit_result.x[44:52]
    current_camera_offsets = current_fit_result.x[52:68].reshape(8, 2)
    current_limb_angles = current_fit_result.x[68:100].reshape(8, 4)
    current_projected_points = project_multiview_joints(current_joint_positions, current_camera_angles, current_camera_scales, current_camera_offsets, current_limb_angles)
    current_error_pixels = np.linalg.norm(current_projected_points - current_observations, axis=-1) * current_heights[:, None]
    current_view_records = []
    for current_view_index in range(8):
        current_training_mask = current_training_weights[current_view_index] > 0
        current_holdout_index = current_holdout_joints[current_view_index] - 2
        current_view_records.append({'observation': current_view_index + 1, 'assumed_yaw_degrees': float(current_view_angles[current_view_index]), 'fitted_yaw_degrees': float(np.rad2deg(current_camera_angles[current_view_index])), 'scale': float(current_camera_scales[current_view_index]), 'offset': current_camera_offsets[current_view_index].tolist(), 'limb_rotation_degrees': np.rad2deg(current_limb_angles[current_view_index]).tolist(), 'train_mean_px': float(current_error_pixels[current_view_index, current_training_mask].mean()), 'holdout_joint': current_holdout_joints[current_view_index], 'holdout_error_px': float(current_error_pixels[current_view_index, current_holdout_index]), 'weights': current_weights[current_view_index].tolist(), 'observed_xy': (current_observations[current_view_index] * current_heights[current_view_index] + current_centers[current_view_index]).tolist(), 'projected_xy': (current_projected_points[current_view_index] * current_heights[current_view_index] + current_centers[current_view_index]).tolist()})
    current_shoulder_center = current_joint_positions[[0, 3]].mean(axis=0)
    current_hip_center = current_joint_positions[[6, 9]].mean(axis=0)
    current_torso_length = float(np.linalg.norm(current_shoulder_center - current_hip_center))
    if current_torso_length <= 1e-8:
        raise ValueError('최적화된 몸통 길이가 0입니다.')
    from generators.kimodo.reference_proportions import REFERENCE_SEGMENT_GROUPS
    current_segment_ratios = {current_group_name: float(np.mean([np.linalg.norm(current_joint_positions[current_start_index - 2] - current_joint_positions[current_end_index - 2]) for current_start_index, current_end_index in current_joint_pairs]) / current_torso_length) for current_group_name, current_joint_pairs in REFERENCE_SEGMENT_GROUPS.items()}
    return {'schema': 'kimodo-multiview-experiment-v1', 'body18_joint_indices': list(MULTIVIEW_BODY_JOINTS), 'joint_positions': current_joint_positions.tolist(), 'ratios': current_segment_ratios, 'views': current_view_records, 'training_observations': int((current_training_weights > 0).sum()), 'held_out_observations': len(current_holdout_joints), 'fit_cost': float(current_fit_result.cost), 'limitations': ['정사영 및 근사적 공통 자세 가정', '방향별 팔다리 자세 차이는 투영된 2D 회전으로 근사하며 3D 관절 회전이 아님', '검출 점수는 확률이 아니며 좌우 가림 판정은 휴리스틱', '검증 관절을 제외한 같은 방향 관측은 카메라 추정에 사용', '8방향 각도 대응은 입력 가정이며 실제 각도 보장 없음', '절대 길이 및 실제 3D 정답 미검증']}


if __name__ == '__main__':
    import argparse
    current_argument_parser = argparse.ArgumentParser(description='8방향 참조 3D 재투영 실험')
    current_argument_parser.add_argument('reference_json', type=Path)
    current_argument_parser.add_argument('output_json', type=Path)
    current_argument_parser.add_argument('--angles', type=float, nargs=8, required=True, help='관측 순서의 카메라 각도 8개')
    current_arguments = current_argument_parser.parse_args()
    current_result_record = fit_multiview_reference(json.loads(current_arguments.reference_json.read_text()), current_arguments.angles)
    current_arguments.output_json.write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
    print(f"8방향 스켈레톤 실험 저장: {current_arguments.output_json}", flush=True)
