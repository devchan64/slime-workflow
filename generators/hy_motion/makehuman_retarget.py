"""VNCCS MakeHuman 고정 체형에 HY-Motion 관절 방향을 전달한다."""
import numpy as np

# HY-Motion body22 인덱스. 말단·손가락은 부모의 회전을 상속한다.
SOURCE_BONE_SEGMENTS = {
    'pelvis': (0, 3), 'spine_01': (3, 6), 'spine_02': (6, 9),
    'spine_03': (9, 12), 'neck_01': (12, 15),
    'thigh_l': (1, 4), 'thigh_r': (2, 5),
    'calf_l': (4, 7), 'calf_r': (5, 8),
    'foot_l': (7, 10), 'foot_r': (8, 11),
    'clavicle_l': (13, 16), 'clavicle_r': (14, 17),
    'upperarm_l': (16, 18), 'upperarm_r': (17, 19),
    'lowerarm_l': (18, 20), 'lowerarm_r': (19, 21),
}
SOURCE_TO_BLENDER = np.array(((1., 0., 0.), (0., 0., -1.), (0., 1., 0.)))


def calculate_direction_rotation(source_direction_vector, target_direction_vector):
    """반평행도 처리하는 최소 회전. 관절 축 회전은 별도 추정하지 않는다."""
    source_vector_length = np.linalg.norm(source_direction_vector)
    target_vector_length = np.linalg.norm(target_direction_vector)
    if min(source_vector_length, target_vector_length) < 1e-8:
        raise ValueError('길이가 0인 본 방향')
    source_unit_vector = source_direction_vector / source_vector_length
    target_unit_vector = target_direction_vector / target_vector_length
    rotation_cross_vector = np.cross(source_unit_vector, target_unit_vector)
    rotation_cosine_value = float(np.clip(source_unit_vector @ target_unit_vector, -1, 1))
    if rotation_cosine_value < -1 + 1e-8:
        rotation_axis_vector = np.cross(source_unit_vector, np.eye(3)[np.argmin(abs(source_unit_vector))])
        rotation_axis_vector /= np.linalg.norm(rotation_axis_vector)
        return 2 * np.outer(rotation_axis_vector, rotation_axis_vector) - np.eye(3)
    cross_product_matrix = np.array(((0, -rotation_cross_vector[2], rotation_cross_vector[1]), (rotation_cross_vector[2], 0, -rotation_cross_vector[0]), (-rotation_cross_vector[1], rotation_cross_vector[0], 0)))
    return np.eye(3) + cross_product_matrix + cross_product_matrix @ cross_product_matrix / (1 + rotation_cosine_value)


def retarget_makehuman_motion(source_joint_frames, source_root_rotations, target_bone_names, target_parent_indices, target_rest_heads, target_rest_tails):
    """본 길이·부모 오프셋을 보존하며 전역 회전과 위치를 산출한다."""
    if source_joint_frames.ndim != 3 or source_joint_frames.shape[1:] != (52, 3) or source_root_rotations.shape != (len(source_joint_frames), 3, 3):
        raise ValueError('HY-Motion 관절·루트 회전 크기 오류')
    if not np.isfinite(source_joint_frames).all() or not np.isfinite(source_root_rotations).all():
        raise ValueError('HY-Motion 비유한 값')
    if set(SOURCE_BONE_SEGMENTS) - set(target_bone_names):
        raise ValueError('MakeHuman 필수 본 누락')
    target_bone_count = len(target_bone_names)
    if target_rest_heads.shape != (target_bone_count, 3) or target_rest_tails.shape != (target_bone_count, 3) or len(target_parent_indices) != target_bone_count:
        raise ValueError('MakeHuman 본 배열 크기 오류')
    if not np.isfinite(target_rest_heads).all() or not np.isfinite(target_rest_tails).all() or len(set(target_bone_names)) != target_bone_count:
        raise ValueError('MakeHuman 비유한 좌표·중복 본 이름')
    if not np.allclose(source_root_rotations @ source_root_rotations.transpose(0, 2, 1), np.eye(3), atol=1e-4) or not np.allclose(np.linalg.det(source_root_rotations), 1, atol=1e-4):
        raise ValueError('HY-Motion 루트 회전 행렬 오류')
    target_frame_rotations = np.empty((len(source_joint_frames), target_bone_count, 3, 3))
    target_frame_positions = np.empty((len(source_joint_frames), target_bone_count, 3))
    source_world_points = source_joint_frames @ SOURCE_TO_BLENDER.T
    maximum_direction_error = 0.
    for current_frame_index, current_joint_points in enumerate(source_world_points):
        for current_bone_index, current_bone_name in enumerate(target_bone_names):
            current_parent_index = int(target_parent_indices[current_bone_index])
            if not -1 <= current_parent_index < current_bone_index:
                raise ValueError('MakeHuman 본은 부모 우선 순서여야 합니다')
            if current_parent_index == -1:
                current_parent_rotation = SOURCE_TO_BLENDER @ source_root_rotations[current_frame_index] @ SOURCE_TO_BLENDER.T
                target_frame_positions[current_frame_index, current_bone_index] = target_rest_heads[current_bone_index] + current_joint_points[0] - source_world_points[0, 0]
            else:
                current_parent_rotation = target_frame_rotations[current_frame_index, current_parent_index]
                target_frame_positions[current_frame_index, current_bone_index] = target_frame_positions[current_frame_index, current_parent_index] + current_parent_rotation @ (target_rest_heads[current_bone_index] - target_rest_heads[current_parent_index])
            current_world_rotation = current_parent_rotation
            if current_bone_name in SOURCE_BONE_SEGMENTS:
                current_start_index, current_end_index = SOURCE_BONE_SEGMENTS[current_bone_name]
                current_target_vector = current_joint_points[current_end_index] - current_joint_points[current_start_index]
                current_rest_vector = target_rest_tails[current_bone_index] - target_rest_heads[current_bone_index]
                current_world_rotation = calculate_direction_rotation(current_parent_rotation @ current_rest_vector, current_target_vector) @ current_parent_rotation
                current_actual_vector = current_world_rotation @ current_rest_vector
                current_cosine_value = np.clip(current_actual_vector @ current_target_vector / (np.linalg.norm(current_actual_vector) * np.linalg.norm(current_target_vector)), -1, 1)
                maximum_direction_error = max(maximum_direction_error, float(np.degrees(np.arccos(current_cosine_value))))
            target_frame_rotations[current_frame_index, current_bone_index] = current_world_rotation
    return target_frame_rotations, target_frame_positions, {'max_direction_error_degrees': maximum_direction_error, 'method': 'parent-inherited-minimum-direction-rotation', 'quality_warnings': ['손가락·머리·손목 말단은 부모 회전 상속', '축 회전·자체 충돌·VNCCS 생성 품질은 미검증']}
