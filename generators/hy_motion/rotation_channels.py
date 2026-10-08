"""HY-Motion 공식 열 우선 6D 회전을 보존하고 위치 채널과 FK 일치를 검증한다."""
import numpy as np

MINIMUM_ROTATION_NORM = 1e-8
MAXIMUM_POSITION_ERROR = 1e-5


def decode_local_rotations(current_rotation_values):
    current_rotation_values = np.asarray(current_rotation_values, dtype=np.float64)
    if current_rotation_values.ndim != 3 or current_rotation_values.shape[1:] != (22,6) or not len(current_rotation_values) or not np.isfinite(current_rotation_values).all():
        raise ValueError('HY-Motion 회전은 유한한 [프레임,22,6] 배열이어야 합니다.')
    current_column_values = current_rotation_values.reshape(-1,22,3,2)
    current_first_column = current_column_values[...,0]
    current_first_norm = np.linalg.norm(current_first_column,axis=-1,keepdims=True)
    if np.any(current_first_norm<=MINIMUM_ROTATION_NORM):
        raise ValueError('6D 회전의 첫 축이 퇴화했습니다.')
    current_first_column = current_first_column/current_first_norm
    current_second_column = current_column_values[...,1]
    current_second_column = current_second_column-np.sum(current_first_column*current_second_column,axis=-1,keepdims=True)*current_first_column
    current_second_norm = np.linalg.norm(current_second_column,axis=-1,keepdims=True)
    if np.any(current_second_norm<=MINIMUM_ROTATION_NORM):
        raise ValueError('6D 회전의 두 축이 독립적이지 않습니다.')
    current_second_column = current_second_column/current_second_norm
    return np.stack((current_first_column,current_second_column,np.cross(current_first_column,current_second_column)),axis=-1)


def reconstruct_rotation_channels(current_rotation_values, current_rest_points, current_parent_indices, current_translation_values, expected_joint_positions):
    current_local_rotations = decode_local_rotations(current_rotation_values)
    current_frame_count = len(current_local_rotations)
    current_rest_points = np.asarray(current_rest_points,dtype=np.float64)
    current_parent_indices = np.asarray(current_parent_indices)
    current_translation_values = np.asarray(current_translation_values,dtype=np.float64)
    expected_joint_positions = np.asarray(expected_joint_positions,dtype=np.float64)
    if current_rest_points.shape!=(22,3) or current_parent_indices.shape!=(22,) or not np.issubdtype(current_parent_indices.dtype,np.integer) or current_translation_values.shape!=(current_frame_count,3) or expected_joint_positions.shape!=(current_frame_count,22,3):
        raise ValueError('회전 FK 검증 입력 형태가 계약과 다릅니다.')
    if not all(np.isfinite(current_array_values).all() for current_array_values in (current_rest_points,current_translation_values,expected_joint_positions)):
        raise ValueError('회전 FK 검증 입력에 비유한값이 있습니다.')
    if current_parent_indices[0] != -1 or any(not 0<=current_parent_indices[current_joint_index]<current_joint_index for current_joint_index in range(1,22)):
        raise ValueError('회전 FK 부모 순서가 유효하지 않습니다.')
    current_global_rotations = np.empty_like(current_local_rotations)
    current_joint_positions = np.empty((current_frame_count,22,3))
    current_global_rotations[:,0]=current_local_rotations[:,0]
    current_joint_positions[:,0]=current_rest_points[0]+current_translation_values
    for current_joint_index in range(1,22):
        current_parent_index = current_parent_indices[current_joint_index]
        current_global_rotations[:,current_joint_index]=current_global_rotations[:,current_parent_index] @ current_local_rotations[:,current_joint_index]
        current_joint_positions[:,current_joint_index]=current_joint_positions[:,current_parent_index]+np.einsum('fij,j->fi',current_global_rotations[:,current_parent_index],current_rest_points[current_joint_index]-current_rest_points[current_parent_index])
    current_maximum_error = float(np.linalg.norm(current_joint_positions-expected_joint_positions,axis=-1).max())
    if current_maximum_error>MAXIMUM_POSITION_ERROR:
        raise ValueError(f'원본 회전 FK와 저장 위치 불일치: {current_maximum_error}m')
    return current_local_rotations,current_global_rotations,current_maximum_error
