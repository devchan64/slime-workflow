"""팔꿈치 굽힘 평면을 이용해 위팔·아래팔의 축 비틀림을 함께 정한다."""
from mathutils import Vector, Quaternion
import math

MAX_ARM_TWIST_DEGREES = 25
MAX_TWIST_FRAME_DEGREES = 5


def calculate_arm_rotations(current_joint_points, rest_bone_positions, rest_bone_rotations, previous_arm_planes, arm_correction_values=None):
    arm_correction_values = arm_correction_values or {}
    arm_rotation_values = {}
    for current_side_label, current_joint_indices in [('L', (16, 18, 20)), ('R', (17, 19, 21))]:
        shoulder_joint_index, elbow_joint_index, wrist_joint_index = current_joint_indices
        rest_upper_direction = rest_bone_positions['lowerarm01.'+current_side_label]-rest_bone_positions['upperarm01.'+current_side_label]
        rest_lower_direction = rest_bone_positions['wrist.'+current_side_label]-rest_bone_positions['lowerarm01.'+current_side_label]
        target_upper_direction = Vector(current_joint_points[elbow_joint_index]-current_joint_points[shoulder_joint_index])
        target_lower_direction = Vector(current_joint_points[wrist_joint_index]-current_joint_points[elbow_joint_index])
        rest_elbow_normal = rest_upper_direction.cross(rest_lower_direction).normalized()
        target_elbow_normal = target_upper_direction.normalized().cross(target_lower_direction.normalized())
        # 팔이 거의 일직선이면 관절 위치의 작은 오차로 굽힘 평면이 뒤집히지 않게 한다.
        reference_elbow_normal = previous_arm_planes.get(current_side_label, rest_upper_direction.rotation_difference(target_upper_direction) @ rest_elbow_normal)
        if target_elbow_normal.length < .15:
            target_elbow_normal = reference_elbow_normal.copy()
        else:
            target_elbow_normal.normalize()
            if target_elbow_normal.dot(reference_elbow_normal) < 0:
                target_elbow_normal.negate()
        previous_arm_planes[current_side_label] = target_elbow_normal.copy()
        for bone_name_prefix, rest_segment_direction, target_segment_direction in [('upperarm', rest_upper_direction, target_upper_direction), ('lowerarm', rest_lower_direction, target_lower_direction)]:
            segment_swing_rotation = rest_segment_direction.rotation_difference(target_segment_direction)
            if arm_correction_values:
                # 매 프레임 기준 자세와 180° 근처를 비교하면 회전축이 급변한다.
                # 스트레칭은 직전 방향에서 현재 방향으로 최소 회전을 누적한다.
                previous_direction_key = bone_name_prefix+'.direction.'+current_side_label
                previous_swing_key = bone_name_prefix+'.swing.'+current_side_label
                if previous_direction_key in previous_arm_planes:
                    incremental_swing_rotation = previous_arm_planes[previous_direction_key].rotation_difference(target_segment_direction)
                    segment_swing_rotation = incremental_swing_rotation @ previous_arm_planes[previous_swing_key]
                    segment_swing_rotation.normalize()
                previous_arm_planes[previous_direction_key] = target_segment_direction.copy()
                previous_arm_planes[previous_swing_key] = segment_swing_rotation.copy()
            target_segment_axis = target_segment_direction.normalized()
            swung_plane_normal = segment_swing_rotation @ rest_elbow_normal
            desired_plane_normal = target_elbow_normal-target_segment_axis*target_elbow_normal.dot(target_segment_axis)
            desired_plane_normal.normalize()
            signed_twist_angle = math.atan2(target_segment_axis.dot(swung_plane_normal.cross(desired_plane_normal)), swung_plane_normal.dot(desired_plane_normal))
            signed_twist_angle *= arm_correction_values.get('twist_strength',1.0)
            maximum_segment_twist = math.radians(arm_correction_values.get('upper_arm_twist_degrees' if bone_name_prefix=='upperarm' else 'forearm_twist_degrees',MAX_ARM_TWIST_DEGREES))
            signed_twist_angle = max(-maximum_segment_twist, min(maximum_segment_twist, signed_twist_angle))
            previous_twist_key = bone_name_prefix+'.'+current_side_label
            previous_twist_angle = previous_arm_planes.get(previous_twist_key, signed_twist_angle)
            maximum_twist_step = math.radians(arm_correction_values.get('max_twist_step_degrees',MAX_TWIST_FRAME_DEGREES))
            signed_twist_angle = previous_twist_angle + max(-maximum_twist_step, min(maximum_twist_step, signed_twist_angle-previous_twist_angle))
            previous_arm_planes[previous_twist_key] = signed_twist_angle
            segment_world_rotation = Quaternion(target_segment_axis, signed_twist_angle) @ segment_swing_rotation
            if arm_correction_values:
                previous_rotation_key = bone_name_prefix+'.rotation.'+current_side_label
                previous_segment_rotation = previous_arm_planes.get(previous_rotation_key, segment_world_rotation)
                if previous_segment_rotation.dot(segment_world_rotation) < 0:
                    segment_world_rotation.negate()
                segment_rotation_delta = previous_segment_rotation.rotation_difference(segment_world_rotation).angle
                maximum_rotation_step = math.radians(arm_correction_values['max_upper_arm_step_degrees' if bone_name_prefix=='upperarm' else 'max_forearm_step_degrees'])
                if segment_rotation_delta > maximum_rotation_step:
                    segment_world_rotation = previous_segment_rotation.slerp(segment_world_rotation, maximum_rotation_step / segment_rotation_delta)
                previous_arm_planes[previous_rotation_key] = segment_world_rotation.copy()
            for current_bone_name in rest_bone_rotations:
                if current_bone_name.startswith(bone_name_prefix) and current_bone_name.endswith('.'+current_side_label):
                    arm_rotation_values[current_bone_name] = segment_world_rotation @ rest_bone_rotations[current_bone_name]
    return arm_rotation_values
