"""DWPose 몸·얼굴 관측을 공통 3D 자세로 맞추는 비파괴 실험."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from generators.kimodo.multiview_reference_experiment import (
    MULTIVIEW_BODY_JOINTS, MULTIVIEW_MINIMUM_SCORE, MULTIVIEW_SYMMETRIC_PAIRS,
    prepare_multiview_observations, project_multiview_joints,
)

FACE_LANDMARK_INDICES = (0, 14, 15, 16, 17)
FACE_MINIMUM_OBSERVATIONS = 3
FACE_CAMERA_ANGLE_LIMIT_DEGREES = 15.0
FACE_FIT_MAXIMUM_EVALUATIONS = 350
FACE_BODY_PRIOR_WEIGHT = 0.06
FACE_SYMMETRY_WEIGHT = 0.15
FACE_CAMERA_PRIOR_WEIGHT = 0.15


def fit_multiview_body_face(current_reference_record, current_initial_record, current_face_visibility, current_excluded_face=None, current_joint_weight_table=None, current_excluded_body=None):
    """명시한 얼굴 가시성만 사용해 몸·얼굴의 공통 3D 좌표를 정사영에 맞춘다."""
    current_views = current_initial_record['views']
    if len(current_views) != 8 or len(current_face_visibility) != 8:
        raise ValueError('8개 카메라와 8개 얼굴 가시성 관측이 필요합니다.')
    if any(not isinstance(current_row, list) or len(current_row) != 5 or any(type(current_value) is not bool for current_value in current_row) for current_row in current_face_visibility):
        raise ValueError('얼굴 가시성은 8×5 불리언 배열이어야 합니다.')
    if current_excluded_body is not None:
        if not isinstance(current_excluded_body, (tuple, list)) or len(current_excluded_body) != 2 or type(current_excluded_body[0]) is not int or not 0 <= current_excluded_body[0] < 8 or type(current_excluded_body[1]) is not int or current_excluded_body[1] not in MULTIVIEW_BODY_JOINTS or current_excluded_body[1] in (8, 11):
            raise ValueError('검증에서 제외할 몸 관절이 유효하지 않습니다. 골반 중심점은 제외할 수 없습니다.')
    current_angles = np.deg2rad([current_view['fitted_yaw_degrees'] for current_view in current_views])
    current_body_observations, current_body_weights, current_centers, current_heights = prepare_multiview_observations(current_reference_record, np.rad2deg(current_angles), current_ignored_joint=current_excluded_body)
    if current_joint_weight_table is not None:
        from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
        current_direction_weights = np.asarray(validate_multiview_joint_weights(current_joint_weight_table), dtype=float)
        current_body_weights *= current_direction_weights[:, list(MULTIVIEW_BODY_JOINTS)]
    else:
        current_direction_weights = np.ones((8, 18), dtype=float)
    current_valid_body_weights = current_body_weights.copy()
    if current_excluded_body is not None:
        current_view_index, current_joint_index = current_excluded_body
        current_joint_offset = current_joint_index - 2
        if current_body_weights[current_view_index, current_joint_offset] <= 0:
            raise ValueError('검증에서 제외할 몸 관측이 유효하지 않습니다.')
        current_body_weights[current_view_index, current_joint_offset] = 0
    for current_joint_offset, current_joint_index in enumerate(MULTIVIEW_BODY_JOINTS):
        current_available_views = np.flatnonzero(current_body_weights[:, current_joint_offset] > 0)
        current_body_design = np.column_stack((np.cos(current_angles[current_available_views]), np.sin(current_angles[current_available_views])))
        if len(current_available_views) < 2 or np.linalg.matrix_rank(current_body_design) < 2:
            raise ValueError(f'몸 관절 {current_joint_index}의 서로 다른 유효 관측이 부족합니다.')
    current_face_observations = np.zeros((8, 5, 2))
    current_face_weights = np.zeros((8, 5))
    for current_view_index, current_body_record in enumerate(current_reference_record['keypoints']):
        current_points = np.asarray(current_body_record, dtype=float)
        for current_face_index, current_joint_index in enumerate(FACE_LANDMARK_INDICES):
            current_face_observations[current_view_index, current_face_index] = (current_points[current_joint_index, :2] - current_centers[current_view_index]) / current_heights[current_view_index]
            if current_face_visibility[current_view_index][current_face_index] and current_points[current_joint_index, 2] >= MULTIVIEW_MINIMUM_SCORE:
                current_face_weights[current_view_index, current_face_index] = min(float(current_points[current_joint_index, 2]), 1.0) * current_direction_weights[current_view_index, current_joint_index]
    current_valid_face_weights = current_face_weights.copy()
    if current_excluded_face is not None:
        current_view_index, current_joint_index = current_excluded_face
        if not 0 <= current_view_index < 8 or current_joint_index not in FACE_LANDMARK_INDICES or current_face_weights[current_view_index, FACE_LANDMARK_INDICES.index(current_joint_index)] <= 0:
            raise ValueError('검증에서 제외할 얼굴 관측이 유효하지 않습니다.')
        current_face_weights[current_view_index, FACE_LANDMARK_INDICES.index(current_joint_index)] = 0
    current_initial_scales = np.asarray([current_view['scale'] for current_view in current_views], dtype=float)
    current_initial_offsets = np.asarray([current_view['offset'] for current_view in current_views], dtype=float)
    current_initial_body = np.asarray(current_initial_record['joint_positions'], dtype=float)
    if current_initial_body.shape != (12, 3) or not np.isfinite(current_initial_body).all():
        raise ValueError('초기 3D 몸 관절 형식 오류')
    if current_excluded_body is not None:
        current_joint_offset = current_excluded_body[1] - 2
        current_available_views = np.flatnonzero(current_body_weights[:, current_joint_offset] > 0)
        current_body_design = np.column_stack((np.cos(current_angles[current_available_views]), np.sin(current_angles[current_available_views])))
        current_normalized_body = (current_body_observations[current_available_views, current_joint_offset] - current_initial_offsets[current_available_views]) / current_initial_scales[current_available_views, None]
        current_body_xz = np.linalg.lstsq(current_body_design, current_normalized_body[:, 0], rcond=None)[0]
        current_initial_body = current_initial_body.copy()
        current_initial_body[current_joint_offset] = [current_body_xz[0], -float(current_normalized_body[:, 1].mean()), current_body_xz[1]]
    current_initial_face = []
    for current_face_index in range(5):
        current_indices = np.flatnonzero(current_face_weights[:, current_face_index] > 0)
        if len(current_indices) < (FACE_MINIMUM_OBSERVATIONS - int(current_excluded_face is not None and current_excluded_face[1] == FACE_LANDMARK_INDICES[current_face_index])):
            raise ValueError('얼굴 관절별 유효 관측이 3개 이상 필요합니다.')
        current_design = np.column_stack((np.cos(current_angles[current_indices]), np.sin(current_angles[current_indices])))
        if np.linalg.matrix_rank(current_design) != 2:
            raise ValueError('얼굴 깊이를 추정할 서로 다른 시점이 필요합니다.')
        current_normalized = (current_face_observations[current_indices, current_face_index] - current_initial_offsets[current_indices]) / current_initial_scales[current_indices, None]
        current_xz = np.linalg.lstsq(current_design, current_normalized[:, 0], rcond=None)[0]
        current_initial_face.append([current_xz[0], -float(current_normalized[:, 1].mean()), current_xz[1]])
    current_initial_face = np.asarray(current_initial_face)
    current_initial_parameters = np.concatenate((current_initial_body.ravel(), current_initial_face.ravel(), current_angles, current_initial_scales, current_initial_offsets.ravel()))
    current_lower = np.r_[np.full(51, -2.), current_angles - np.deg2rad(FACE_CAMERA_ANGLE_LIMIT_DEGREES), np.full(8, .8), np.full(16, -.15)]
    current_upper = np.r_[np.full(51, 2.), current_angles + np.deg2rad(FACE_CAMERA_ANGLE_LIMIT_DEGREES), np.full(8, 1.2), np.full(16, .15)]

    def calculate_body_face_residuals(current_parameters):
        current_body = current_parameters[:36].reshape(12, 3)
        current_face = current_parameters[36:51].reshape(5, 3)
        current_camera_angles = current_parameters[51:59]
        current_scales = current_parameters[59:67]
        current_offsets = current_parameters[67:83].reshape(8, 2)
        current_projected_body = project_multiview_joints(current_body, current_camera_angles, current_scales, current_offsets, np.zeros((8, 4)))
        current_face_x = np.cos(current_camera_angles)[:, None] * current_face[None, :, 0] + np.sin(current_camera_angles)[:, None] * current_face[None, :, 2]
        current_face_y = np.broadcast_to(-current_face[None, :, 1], (8, 5))
        current_projected_face = np.stack((current_face_x, current_face_y), axis=-1) * current_scales[:, None, None] + current_offsets[:, None, :]
        current_body_errors = ((current_projected_body - current_body_observations) * np.sqrt(current_body_weights[:, :, None])).ravel()
        current_face_errors = ((current_projected_face - current_face_observations) * np.sqrt(current_face_weights[:, :, None])).ravel()
        current_symmetry_errors = [(np.linalg.norm(current_body[a-2]-current_body[b-2])-np.linalg.norm(current_body[c-2]-current_body[d-2])) * FACE_SYMMETRY_WEIGHT for (a,b),(c,d) in MULTIVIEW_SYMMETRIC_PAIRS]
        return np.r_[current_body_errors, current_face_errors, current_symmetry_errors, ((current_body-current_initial_body)*FACE_BODY_PRIOR_WEIGHT).ravel(), (current_camera_angles-current_angles)*FACE_CAMERA_PRIOR_WEIGHT, (current_scales-1)*FACE_CAMERA_PRIOR_WEIGHT, current_offsets.ravel()*FACE_CAMERA_PRIOR_WEIGHT]

    current_fit = least_squares(calculate_body_face_residuals, current_initial_parameters, bounds=(current_lower, current_upper), loss='soft_l1', f_scale=.02, max_nfev=FACE_FIT_MAXIMUM_EVALUATIONS)
    if not current_fit.success or not np.isfinite(current_fit.x).all():
        raise RuntimeError(f'몸·얼굴 공통 3D 추정 실패: {current_fit.message}')
    current_body = current_fit.x[:36].reshape(12, 3)
    current_face = current_fit.x[36:51].reshape(5, 3)
    current_angles_result = current_fit.x[51:59]
    current_scales_result = current_fit.x[59:67]
    current_offsets_result = current_fit.x[67:83].reshape(8, 2)
    current_body_projection = project_multiview_joints(current_body, current_angles_result, current_scales_result, current_offsets_result, np.zeros((8, 4)))
    current_face_x = np.cos(current_angles_result)[:, None] * current_face[None, :, 0] + np.sin(current_angles_result)[:, None] * current_face[None, :, 2]
    current_face_y = np.broadcast_to(-current_face[None, :, 1], (8, 5))
    current_face_projection = np.stack((current_face_x, current_face_y), axis=-1) * current_scales_result[:, None, None] + current_offsets_result[:, None, :]
    current_output_views = []
    for current_index in range(8):
        current_output_views.append({'observation': current_index+1, 'fitted_yaw_degrees': float(np.rad2deg(current_angles_result[current_index])), 'scale': float(current_scales_result[current_index]), 'offset': current_offsets_result[current_index].tolist(), 'body_xy': (current_body_projection[current_index]*current_heights[current_index]+current_centers[current_index]).tolist(), 'face_xy': (current_face_projection[current_index]*current_heights[current_index]+current_centers[current_index]).tolist(), 'body_weights': current_valid_body_weights[current_index].tolist(), 'body_fit_weights': current_body_weights[current_index].tolist(), 'face_weights': current_valid_face_weights[current_index].tolist(), 'face_fit_weights': current_face_weights[current_index].tolist()})
    from generators.kimodo.multiview_provenance import calculate_multiview_observation_hash,calculate_multiview_fit_context_hash
    current_observation_hash = calculate_multiview_observation_hash(current_reference_record)
    current_context_hash = calculate_multiview_fit_context_hash(current_observation_hash,current_initial_record,current_face_visibility,current_joint_weight_table)
    return {'observation_sha256':current_observation_hash, 'fit_context_sha256':current_context_hash, 'reference_image_sha256':current_reference_record.get('reference_image_sha256'), 'schema': 'kimodo-multiview-body-face-experiment-v1', 'body18_joint_indices': list(MULTIVIEW_BODY_JOINTS), 'face_joint_indices': list(FACE_LANDMARK_INDICES), 'body_joint_positions': current_body.tolist(), 'face_joint_positions': current_face.tolist(), 'views': current_output_views, 'excluded_face': current_excluded_face, 'excluded_body': current_excluded_body, 'joint_weight_table': current_joint_weight_table, 'fit_cost': float(current_fit.cost), 'limitations': ['공통 자세의 정사영 실험이며 2D 팔다리 회전 없음', '얼굴 가시성은 명시적 입력이며 검출 점수는 가림을 보장하지 않음', '카메라·인물 자세의 가정과 2D 검출 오차가 포함됨', '실제 3D 정답 및 생성기 적용 미검증', '초기 카메라와 다른 초기 3D 관절은 이전 적합에서 제공되므로 관측 제외 검증은 완전한 독립 검증이 아님']}


if __name__ == '__main__':
    import argparse
    current_parser = argparse.ArgumentParser(description='8방향 DWPose 공통 몸·얼굴 3D 스켈레톤 실험')
    current_parser.add_argument('reference_json', type=Path)
    current_parser.add_argument('initial_json', type=Path)
    current_parser.add_argument('visibility_json', type=Path)
    current_parser.add_argument('output_json', type=Path)
    current_parser.add_argument('--joint-weights', type=Path, help='8방향 BODY18 관절별 가중치 JSON')
    current_arguments = current_parser.parse_args()
    current_reference = json.loads(current_arguments.reference_json.read_text())
    current_initial = json.loads(current_arguments.initial_json.read_text())
    current_visibility = json.loads(current_arguments.visibility_json.read_text())
    current_weights = json.loads(current_arguments.joint_weights.read_text()) if current_arguments.joint_weights else None
    current_result = fit_multiview_body_face(current_reference, current_initial.get('multiview_experiment', current_initial), current_visibility, current_joint_weight_table=current_weights)
    current_arguments.output_json.write_text(json.dumps(current_result, ensure_ascii=False, indent=2))
    print(f'공통 몸·얼굴 스켈레톤 실험 저장: {current_arguments.output_json}', flush=True)
