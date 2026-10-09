"""마지막 전신 안전 자세에서 목표까지 같은 비율로 진행한다. 관절 보상 없음."""
import math
from generators.hy_motion.skin_collision_barrier import advance_collision_free


def advance_whole_pose(current_rig_object, current_start_poses, current_start_location, current_target_poses, current_target_location, current_collision_probe, current_angle_step, current_refinement_count):
    import bpy
    current_rotation_pairs = {}
    current_maximum_angle = 0.0
    for current_bone_name, current_start_matrix in current_start_poses.items():
        current_start_rotation = current_start_matrix.to_quaternion().normalized()
        current_target_rotation = current_target_poses[current_bone_name].to_quaternion().normalized()
        if current_start_rotation.dot(current_target_rotation) < 0:
            current_target_rotation.negate()
        current_maximum_angle = max(current_maximum_angle, math.degrees(2 * math.acos(min(1, abs(current_start_rotation.dot(current_target_rotation))))))
        current_rotation_pairs[current_bone_name] = (current_start_rotation, current_target_rotation)

    def apply_whole_fraction(current_pose_fraction):
        for current_bone_name, (current_start_rotation, current_target_rotation) in current_rotation_pairs.items():
            current_pose_bone = current_rig_object.pose.bones[current_bone_name]
            current_pose_bone.matrix_basis = current_start_poses[current_bone_name].copy()
            current_pose_bone.rotation_mode = 'QUATERNION'
            if current_pose_fraction > 0:
                current_pose_bone.rotation_quaternion = current_start_rotation.slerp(current_target_rotation, current_pose_fraction)
        current_rig_object.location = current_start_location.lerp(current_target_location, current_pose_fraction)
        bpy.context.view_layer.update()

    current_step_count = max(1, math.ceil(current_maximum_angle / current_angle_step))
    current_result_record = advance_collision_free(apply_whole_fraction, current_collision_probe, current_step_count, current_refinement_count)
    current_result_record.update(strategy='whole_pose_stop_before_collision', affected_scope='전신 로컬 회전·루트 이동에 동일 진행률 적용. 다리·몸통도 정지할 수 있음', compensation_applied=False, maximum_requested_rotation_degrees=current_maximum_angle)
    return current_result_record
