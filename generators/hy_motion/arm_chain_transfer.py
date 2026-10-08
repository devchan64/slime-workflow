"""ANNY 기준 체인의 길이를 보존하는 방향 전달. 임상 관절축 솔버는 아니다."""
import bpy
import math
from mathutils import Matrix, Quaternion, Vector

ARM_CHAIN_EPSILON = 1e-5


def redistribute_segment_twist(current_rig_object, current_segment_names, current_twist_radians, current_distal_share):
    """끝점 연결축으로 회전을 나누고 하위 본의 전역 방향을 복원하는 진단용 연산."""
    if len(current_segment_names) != 3 or len(set(current_segment_names)) != 3:
        raise ValueError('시작·중간·하위 본 세 개가 필요합니다.')
    if type(current_twist_radians) not in (float, int) or not math.isfinite(current_twist_radians) or type(current_distal_share) not in (float, int) or not math.isfinite(current_distal_share) or not 0 <= current_distal_share <= 1:
        raise ValueError('유한한 회전각과 0~1 분배 비율이 필요합니다.')
    current_segment_bones = [current_rig_object.pose.bones[current_bone_name] for current_bone_name in current_segment_names]
    if any(current_child_bone.parent != current_parent_bone for current_parent_bone, current_child_bone in zip(current_segment_bones, current_segment_bones[1:])):
        raise ValueError('중간 본을 포함한 직접 부모 체인이 필요합니다.')
    current_saved_poses = [current_pose_bone.matrix_basis.copy() for current_pose_bone in current_segment_bones]
    current_endpoint_position = current_segment_bones[-1].head.copy()
    current_endpoint_rotation = current_segment_bones[-1].matrix.to_quaternion()
    current_start_position = current_segment_bones[0].head.copy()
    try:
        # 로컬 Y 대신 실제 끝점 연결선을 사용한다. 해부학적 회전축으로 해석하지 않는다.
        for current_pose_bone, current_angle_share in zip(current_segment_bones[:2], (1 - current_distal_share, current_distal_share)):
            current_axis_vector = current_endpoint_position - current_pose_bone.head
            if current_axis_vector.length <= ARM_CHAIN_EPSILON:
                raise ValueError('분배 진단의 끝점 연결축 퇴화')
            current_delta_rotation = Quaternion(current_axis_vector.normalized(), current_twist_radians * current_angle_share)
            current_pose_bone.matrix = Matrix.Translation(current_pose_bone.head) @ (current_delta_rotation @ current_pose_bone.matrix.to_quaternion()).to_matrix().to_4x4()
            current_pose_bone.location = (0, 0, 0)
            current_pose_bone.scale = (1, 1, 1)
            bpy.context.view_layer.update()
        current_endpoint_bone = current_segment_bones[-1]
        current_endpoint_bone.matrix = Matrix.Translation(current_endpoint_bone.head) @ current_endpoint_rotation.to_matrix().to_4x4()
        current_endpoint_bone.location = (0, 0, 0)
        current_endpoint_bone.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        current_position_error = max((current_endpoint_bone.head - current_endpoint_position).length, (current_segment_bones[0].head - current_start_position).length)
        current_rotation_error = max(abs(current_endpoint_bone.matrix.to_quaternion().to_matrix()[current_row_index][current_column_index] - current_endpoint_rotation.to_matrix()[current_row_index][current_column_index]) for current_row_index in range(3) for current_column_index in range(3))
        if current_position_error > ARM_CHAIN_EPSILON or current_rotation_error > ARM_CHAIN_EPSILON:
            raise ValueError('분배 진단의 끝점 위치·하위 방향 보존 실패')
        return {'endpoint_error_m': current_position_error, 'downstream_rotation_matrix_error': current_rotation_error}
    except Exception:
        for current_pose_bone, current_saved_pose in zip(current_segment_bones, current_saved_poses):
            current_pose_bone.matrix_basis = current_saved_pose
        bpy.context.view_layer.update()
        raise


def align_arm_segment(current_rig_object, current_start_name, current_end_name, desired_segment_vector):
    current_start_bone = current_rig_object.pose.bones[current_start_name]
    current_end_bone = current_rig_object.pose.bones[current_end_name]
    current_segment_vector = current_end_bone.head - current_start_bone.head
    desired_segment_vector = Vector(desired_segment_vector)
    if len(desired_segment_vector) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in desired_segment_vector):
        raise ValueError('팔 방향은 유한한 XYZ 벡터여야 합니다.')
    if min(current_segment_vector.length, desired_segment_vector.length) <= ARM_CHAIN_EPSILON:
        raise ValueError('팔 방향 전달의 세그먼트 퇴화')
    current_delta_rotation = current_segment_vector.rotation_difference(desired_segment_vector)
    current_start_bone.matrix = Matrix.Translation(current_start_bone.head) @ (current_delta_rotation @ current_start_bone.matrix.to_quaternion()).to_matrix().to_4x4()
    current_start_bone.location = (0, 0, 0)
    current_start_bone.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    current_actual_vector = current_end_bone.head - current_start_bone.head
    if abs(current_actual_vector.length - current_segment_vector.length) > ARM_CHAIN_EPSILON or (current_actual_vector.normalized() - desired_segment_vector.normalized()).length > ARM_CHAIN_EPSILON:
        raise ValueError('팔 체인 방향 또는 길이 보존 실패')


def apply_arm_directions(current_rig_object, current_chain_names, current_endpoint_names, current_source_points):
    """중간 본의 기준 로컬 자세를 유지하고 상완·전완 방향을 각각 전달한다."""
    if len(current_chain_names) != 7 or len(current_endpoint_names) != 3 or list(current_endpoint_names) != [current_chain_names[2], current_chain_names[4], current_chain_names[6]]:
        raise ValueError('ANNY 7본 체인·세그먼트 끝점 계약 오류')
    if len(current_source_points) != 3 or any(len(current_point_values) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in current_point_values) for current_point_values in current_source_points):
        raise ValueError('원본 어깨·팔꿈치·손목 좌표 계약 오류')
    for current_parent_name, current_child_name in zip(current_chain_names, current_chain_names[1:]):
        if current_rig_object.data.bones[current_child_name].parent.name != current_parent_name:
            raise ValueError('ANNY 기준 부모 체인 불일치')
    # 쇄골·어깨 중심은 기존 모션을 유지한다. 팔 01/02 본만 기준 자세에서 재구성한다.
    for current_bone_name in current_chain_names[2:6]:
        current_rig_object.pose.bones[current_bone_name].matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for current_segment_index in range(2):
        align_arm_segment(current_rig_object, current_endpoint_names[current_segment_index], current_endpoint_names[current_segment_index + 1], Vector(current_source_points[current_segment_index + 1]) - Vector(current_source_points[current_segment_index]))
