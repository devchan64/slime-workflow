"""기준 중심선을 최소 회전 정렬하는 진단용 전달. 해부학적 축 보정은 아니다."""
import math
import numpy as np

from generators.hy_motion.hand_frame_transfer import validate_rotation_frame

MINIMUM_AXIS_LENGTH = 1e-8
MAXIMUM_AXIS_ERROR = 1e-5


def normalize_segment_axis(current_axis_vector):
    current_axis_vector = np.asarray(current_axis_vector, dtype=np.float64)
    if current_axis_vector.shape != (3,) or not np.isfinite(current_axis_vector).all():
        raise ValueError('세그먼트 축은 유한한 XYZ 벡터여야 합니다.')
    current_axis_length = np.linalg.norm(current_axis_vector)
    if current_axis_length <= MINIMUM_AXIS_LENGTH:
        raise ValueError('세그먼트 축이 퇴화했습니다.')
    return current_axis_vector / current_axis_length


def build_axis_cross_matrix(current_axis_vector):
    return np.array([[0, -current_axis_vector[2], current_axis_vector[1]],
                     [current_axis_vector[2], 0, -current_axis_vector[0]],
                     [-current_axis_vector[1], current_axis_vector[0], 0]])


def transfer_segment_rotation(source_global_rotation, source_rest_vector, target_rest_vector, target_bind_rotation):
    """대상→원본 기준축 최소 정렬 A를 구하고 S @ A @ B를 반환한다."""
    source_global_rotation = validate_rotation_frame(source_global_rotation)
    target_bind_rotation = validate_rotation_frame(target_bind_rotation)
    current_source_axis = normalize_segment_axis(source_rest_vector)
    current_target_axis = normalize_segment_axis(target_rest_vector)
    current_axis_cosine = float(np.clip(np.dot(current_target_axis, current_source_axis), -1, 1))
    if 1 + current_axis_cosine <= MINIMUM_AXIS_LENGTH:
        raise ValueError('반대 기준축의 최소 정렬은 회전축을 유일하게 정할 수 없습니다.')
    current_cross_matrix = build_axis_cross_matrix(np.cross(current_target_axis, current_source_axis))
    current_alignment_rotation = np.eye(3) + current_cross_matrix + current_cross_matrix @ current_cross_matrix / (1 + current_axis_cosine)
    return validate_rotation_frame(source_global_rotation @ current_alignment_rotation @ target_bind_rotation)


def measure_segment_twist(current_bone_rotation, desired_bone_rotation, current_segment_axis):
    """두 방향이 같은 중심선을 가질 때만 그 축 주위의 부호 있는 차이를 반환한다."""
    current_bone_rotation = validate_rotation_frame(current_bone_rotation)
    desired_bone_rotation = validate_rotation_frame(desired_bone_rotation)
    current_segment_axis = normalize_segment_axis(current_segment_axis)
    current_delta_rotation = desired_bone_rotation @ current_bone_rotation.T
    current_skew_vector = np.array([current_delta_rotation[2, 1] - current_delta_rotation[1, 2],
                                    current_delta_rotation[0, 2] - current_delta_rotation[2, 0],
                                    current_delta_rotation[1, 0] - current_delta_rotation[0, 1]]) / 2
    current_twist_angle = math.atan2(float(np.dot(current_skew_vector, current_segment_axis)), float(np.clip((np.trace(current_delta_rotation) - 1) / 2, -1, 1)))
    current_cross_matrix = build_axis_cross_matrix(current_segment_axis)
    current_expected_rotation = np.eye(3) + math.sin(current_twist_angle) * current_cross_matrix + (1 - math.cos(current_twist_angle)) * current_cross_matrix @ current_cross_matrix
    if np.max(np.abs(current_expected_rotation - current_delta_rotation)) > MAXIMUM_AXIS_ERROR:
        raise ValueError('회전 차이가 세그먼트 축 회전만으로 설명되지 않습니다.')
    return current_twist_angle
