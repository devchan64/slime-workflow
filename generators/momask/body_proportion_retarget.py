"""ANNY 실험용 체형 비율 손목 목표·팔 IK·표면 교차 검사. 기본 적용하지 않는다."""
import math

import bpy
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree

ARM_SURFACE_PREFIXES = ('upperarm', 'lowerarm', 'wrist', 'finger', 'metacarpal')
BODY_SURFACE_PREFIXES = ('spine', 'root', 'pelvis', 'upperleg', 'lowerleg')
MINIMUM_SEGMENT_LENGTH = 1e-8


def transport_elbow_reference(current_shoulder_point, desired_wrist_point, reference_upper_vector, reference_lower_vector, current_upper_length, current_lower_length):
    """원본 굽힘 평면을 새 어깨→손목 축에 최소 회전으로 운반한다."""
    if any(len(current_point_value)!=3 or not all(math.isfinite(current_axis_value) for current_axis_value in current_point_value) for current_point_value in (current_shoulder_point,desired_wrist_point,reference_upper_vector,reference_lower_vector)) or any(not math.isfinite(current_length_value) or current_length_value<=0 for current_length_value in (current_upper_length,current_lower_length)):
        raise ValueError('팔 평면 운반 입력이 유효하지 않습니다.')
    if min(reference_upper_vector.length,reference_lower_vector.length)<=MINIMUM_SEGMENT_LENGTH:
        raise ValueError('원본 팔 방향 길이가 0입니다.')
    reference_upper_vector=reference_upper_vector.normalized()
    reference_lower_vector=reference_lower_vector.normalized()
    reference_plane_normal = reference_upper_vector.cross(reference_lower_vector)
    reference_chain_vector = reference_upper_vector*current_upper_length+reference_lower_vector*current_lower_length
    current_target_vector = desired_wrist_point-current_shoulder_point
    if min(reference_plane_normal.length,reference_chain_vector.length,current_target_vector.length)<=MINIMUM_SEGMENT_LENGTH:
        raise ValueError('원본 굽힘 평면 또는 팔 방향이 퇴화했습니다.')
    current_transport_rotation = reference_chain_vector.rotation_difference(current_target_vector)
    current_plane_normal = current_transport_rotation @ reference_plane_normal.normalized()
    current_pole_direction = current_target_vector.normalized().cross(current_plane_normal).normalized()
    return current_shoulder_point+current_pole_direction*current_upper_length


def solve_shoulder_reach(current_pivot_point, current_shoulder_point, desired_wrist_point, desired_arm_reach, *, current_swing_limit_degrees):
    """쇄골 길이를 유지하는 구면에서 목표 도달 거리를 맞추되 어깨 회전을 제한한다."""
    if type(current_swing_limit_degrees) not in (int,float) or not math.isfinite(current_swing_limit_degrees) or not 0<=current_swing_limit_degrees<=180:
        raise ValueError('회전 제한은 명시적인 0~180도 값이어야 합니다. 해부학적 기본값은 없습니다.')
    if any(not all(math.isfinite(current_axis_value) for current_axis_value in current_point_value) for current_point_value in (current_pivot_point, current_shoulder_point, desired_wrist_point)) or not math.isfinite(desired_arm_reach) or desired_arm_reach <= 0:
        raise ValueError('어깨 도달 입력이 유효하지 않습니다.')
    current_shoulder_vector = current_shoulder_point-current_pivot_point
    current_target_vector = desired_wrist_point-current_pivot_point
    current_shoulder_radius = current_shoulder_vector.length
    current_target_distance = current_target_vector.length
    if min(current_shoulder_radius,current_target_distance)<MINIMUM_SEGMENT_LENGTH:
        raise ValueError('어깨 도달 기준 길이가 0입니다.')
    current_target_axis = current_target_vector.normalized()
    current_circle_offset = (current_shoulder_radius**2+current_target_distance**2-desired_arm_reach**2)/(2*current_target_distance)
    current_circle_offset = max(-current_shoulder_radius,min(current_shoulder_radius,current_circle_offset))
    current_circle_radius = math.sqrt(max(0,current_shoulder_radius**2-current_circle_offset**2))
    current_radial_vector = current_shoulder_vector-current_target_axis*current_shoulder_vector.dot(current_target_axis)
    if current_radial_vector.length<MINIMUM_SEGMENT_LENGTH:
        raise ValueError('어깨 도달 회전 평면이 퇴화했습니다.')
    desired_shoulder_vector = current_target_axis*current_circle_offset+current_radial_vector.normalized()*current_circle_radius
    current_delta_rotation = current_shoulder_vector.rotation_difference(desired_shoulder_vector)
    current_rotation_angle = current_delta_rotation.angle
    current_limited_angle = min(current_rotation_angle,math.radians(current_swing_limit_degrees))
    if current_rotation_angle > 1e-8:
        desired_shoulder_vector = Quaternion(current_delta_rotation.axis,current_limited_angle) @ current_shoulder_vector
    return current_pivot_point+desired_shoulder_vector, math.degrees(current_limited_angle)


def build_surface_partitions(current_body_object):
    """지배 가중치가 같은 부위인 삼각형만 선택한다. 혼합 경계는 제외한다."""
    current_group_names = {current_group_item.index: current_group_item.name for current_group_item in current_body_object.vertex_groups}
    current_vertex_labels = []
    for current_vertex_item in current_body_object.data.vertices:
        if not current_vertex_item.groups:
            raise ValueError('가중치 없는 정점은 표면 분류할 수 없습니다.')
        current_vertex_labels.append(current_group_names[max(current_vertex_item.groups, key=lambda current_group_item: current_group_item.weight).group])
    current_body_object.data.calc_loop_triangles()
    current_surface_faces = [tuple(current_triangle_item.vertices) for current_triangle_item in current_body_object.data.loop_triangles]
    current_partition_faces = {}
    for current_side_name in ('L', 'R'):
        current_partition_faces[current_side_name] = [current_face_item for current_face_item in current_surface_faces if all(current_vertex_labels[current_vertex_index].startswith(ARM_SURFACE_PREFIXES) and current_vertex_labels[current_vertex_index].endswith('.' + current_side_name) for current_vertex_index in current_face_item)]
    current_partition_faces['body'] = [current_face_item for current_face_item in current_surface_faces if all(current_vertex_labels[current_vertex_index].startswith(BODY_SURFACE_PREFIXES) for current_vertex_index in current_face_item)]
    if any(not current_face_items for current_face_items in current_partition_faces.values()):
        raise ValueError('팔·몸통 표면 분류 결과가 비어 있습니다.')
    return current_partition_faces


def count_surface_intersections(current_body_object, current_partition_faces):
    """변형 후 메시를 사용한다. 교차쌍 수는 관통 깊이나 완전 내포를 나타내지 않는다."""
    current_evaluated_object = current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
    current_evaluated_mesh = current_evaluated_object.to_mesh()
    try:
        if len(current_evaluated_mesh.vertices) != len(current_body_object.data.vertices):
            raise ValueError('토폴로지가 바뀐 메시의 교차 검사는 지원하지 않습니다.')
        current_vertex_points = [current_vertex_item.co.copy() for current_vertex_item in current_evaluated_mesh.vertices]
        current_body_tree = BVHTree.FromPolygons(current_vertex_points, current_partition_faces['body'], all_triangles=True, epsilon=0)
        current_result_counts = {}
        for current_side_name in ('L', 'R'):
            current_arm_faces = current_partition_faces[current_side_name]
            current_arm_tree = BVHTree.FromPolygons(current_vertex_points, current_arm_faces, all_triangles=True, epsilon=0)
            current_result_counts[current_side_name] = sum(not set(current_arm_faces[current_arm_index]).intersection(current_partition_faces['body'][current_body_index]) for current_arm_index, current_body_index in current_arm_tree.overlap(current_body_tree))
        return current_result_counts
    finally:
        current_evaluated_object.to_mesh_clear()


def build_body_coordinate(current_left_hip, current_right_hip, current_shoulder_center):
    if any(len(current_point_value) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in current_point_value) for current_point_value in (current_left_hip, current_right_hip, current_shoulder_center)):
        raise ValueError('몸통 좌표 입력은 유한한 3차원 벡터여야 합니다.')
    current_lateral_axis = Vector(current_left_hip) - Vector(current_right_hip)
    current_vertical_axis = Vector(current_shoulder_center) - (Vector(current_left_hip) + Vector(current_right_hip)) / 2
    if current_lateral_axis.length < MINIMUM_SEGMENT_LENGTH:
        raise ValueError('골반 폭이 0입니다.')
    current_lateral_axis.normalize()
    current_vertical_axis -= current_lateral_axis * current_vertical_axis.dot(current_lateral_axis)
    if current_vertical_axis.length < MINIMUM_SEGMENT_LENGTH:
        raise ValueError('몸통 높이 축이 퇴화했습니다.')
    current_vertical_axis.normalize()
    return Matrix((current_lateral_axis, current_vertical_axis.cross(current_lateral_axis), current_vertical_axis)).transposed()


def calculate_body_ratios(source_reference_points, target_reference_points):
    """양쪽 골반·어깨 중심으로 폭·높이 비율을 구한다. 깊이는 추정하지 않는다.

    각 입력 순서는 왼쪽 골반, 오른쪽 골반, 양쪽 어깨의 중심이다.
    원본에는 기존 모션 스케일과 좌표 변환을 먼저 적용해야 한다.
    """
    current_body_dimensions = []
    for current_reference_points in (source_reference_points, target_reference_points):
        if len(current_reference_points) != 3:
            raise ValueError('체형 기준은 골반 두 점과 어깨 중심이어야 합니다.')
        build_body_coordinate(*current_reference_points)
        current_left_hip, current_right_hip, current_shoulder_center = map(Vector, current_reference_points)
        current_body_dimensions.append(((current_left_hip-current_right_hip).length, (current_shoulder_center-(current_left_hip+current_right_hip)/2).length))
    return Vector((current_body_dimensions[1][0]/current_body_dimensions[0][0], 1.0, current_body_dimensions[1][1]/current_body_dimensions[0][1]))


def map_proportional_wrist(source_body_points, target_body_points, source_wrist_point, current_side_index, current_ratio_vector):
    """몸통 좌표에서 같은 쪽 골반 대비 손목 위치를 체형 비율로 옮긴다."""
    if type(current_side_index) is not int or current_side_index not in (0, 1):
        raise ValueError('골반 인덱스는 왼쪽 0 또는 오른쪽 1이어야 합니다.')
    if len(current_ratio_vector) != 3 or any(not math.isfinite(current_ratio_value) or current_ratio_value <= 0 for current_ratio_value in current_ratio_vector):
        raise ValueError('체형 비율은 양의 유한한 3차원 벡터여야 합니다.')
    if len(source_wrist_point) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in source_wrist_point):
        raise ValueError('손목 입력은 유한한 3차원 벡터여야 합니다.')
    if len(source_body_points) != 3 or len(target_body_points) != 3:
        raise ValueError('몸통 기준은 골반 두 점과 어깨 중심이어야 합니다.')
    source_body_basis = build_body_coordinate(*source_body_points)
    target_body_basis = build_body_coordinate(*target_body_points)
    current_local_offset = source_body_basis.transposed() @ (Vector(source_wrist_point)-Vector(source_body_points[current_side_index]))
    current_scaled_offset = Vector(tuple(current_local_offset[current_axis_index]*current_ratio_vector[current_axis_index] for current_axis_index in range(3)))
    return Vector(target_body_points[current_side_index])+target_body_basis @ current_scaled_offset


def solve_two_segment(current_shoulder_point, current_elbow_point, current_wrist_point, desired_wrist_point, reference_elbow_point=None):
    """원래 팔꿈치 굽힘 평면을 유지하고 도달 불가 목표는 도달 범위에 투영한다."""
    if any(len(current_point_value) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in current_point_value) for current_point_value in (current_shoulder_point, current_elbow_point, current_wrist_point, desired_wrist_point)):
        raise ValueError('팔 IK 입력은 유한한 3차원 벡터여야 합니다.')
    current_upper_length = (current_elbow_point - current_shoulder_point).length
    current_lower_length = (current_wrist_point - current_elbow_point).length
    current_target_vector = desired_wrist_point - current_shoulder_point
    if min(current_upper_length, current_lower_length, current_target_vector.length) < MINIMUM_SEGMENT_LENGTH:
        raise ValueError('팔 IK 길이 또는 목표 거리가 0입니다.')
    current_target_axis = current_target_vector.normalized()
    current_target_distance = min(current_upper_length + current_lower_length - 1e-6, max(abs(current_upper_length - current_lower_length) + 1e-6, current_target_vector.length))
    if reference_elbow_point is not None and (len(reference_elbow_point) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in reference_elbow_point)):
        raise ValueError('팔꿈치 기준 입력은 유한한 3차원 벡터여야 합니다.')
    current_pole_vector = (current_elbow_point if reference_elbow_point is None else reference_elbow_point) - current_shoulder_point
    current_pole_vector -= current_target_axis * current_pole_vector.dot(current_target_axis)
    if current_pole_vector.length < MINIMUM_SEGMENT_LENGTH:
        raise ValueError('팔꿈치 굽힘 평면이 퇴화했습니다.')
    current_pole_vector.normalize()
    current_axis_distance = (current_upper_length ** 2 - current_lower_length ** 2 + current_target_distance ** 2) / (2 * current_target_distance)
    current_pole_distance = math.sqrt(max(0, current_upper_length ** 2 - current_axis_distance ** 2))
    desired_elbow_point = current_shoulder_point + current_target_axis * current_axis_distance + current_pole_vector * current_pole_distance
    reachable_wrist_point = current_shoulder_point + current_target_axis * current_target_distance
    return desired_elbow_point, reachable_wrist_point, (reachable_wrist_point - desired_wrist_point).length


def rotate_segment_toward(current_rig_object, current_start_name, current_end_name, desired_end_point):
    current_pose_bone = current_rig_object.pose.bones[current_start_name]
    current_source_vector = current_rig_object.pose.bones[current_end_name].head - current_pose_bone.head
    current_target_vector = desired_end_point - current_pose_bone.head
    if min(current_source_vector.length, current_target_vector.length) < MINIMUM_SEGMENT_LENGTH:
        raise ValueError('팔 회전 방향이 퇴화했습니다.')
    current_delta_rotation = current_source_vector.rotation_difference(current_target_vector)
    current_pose_bone.matrix = Matrix.Translation(current_pose_bone.head) @ (current_delta_rotation @ current_pose_bone.matrix.to_quaternion()).to_matrix().to_4x4()
    current_pose_bone.location = (0, 0, 0)
    current_pose_bone.scale = (1, 1, 1)
    bpy.context.view_layer.update()
