"""몸통·다리 목표를 보존하고 손부터 팔의 원본 진행만 제한한다."""
import math
from generators.hy_motion.skin_collision_barrier import advance_collision_free


def resolve_priority_collision(current_priority_groups, apply_priority_fraction, probe_priority_collision, current_step_count, current_refinement_count):
    """낮은 우선권부터 누적한다. 안전 시작점이 없으면 목표를 진단용으로 보존한다."""
    apply_priority_fraction((), 1.0)
    if not probe_priority_collision():
        return {'strategy': 'preserved_collision_free_target', 'unresolved': False, 'limited_bones': [], 'fraction': 1.0}
    current_attempt_records = []
    for current_bone_group in current_priority_groups:
        apply_priority_fraction(current_bone_group, 0.0)
        current_start_collision = probe_priority_collision()
        current_attempt_records.append({'bones': list(current_bone_group), 'start_colliding': current_start_collision})
        if current_start_collision:
            continue
        current_transition_record = advance_collision_free(lambda current_pose_fraction: apply_priority_fraction(current_bone_group, current_pose_fraction), probe_priority_collision, current_step_count, current_refinement_count)
        return dict(current_transition_record, strategy='hand_first_arm_stop', unresolved=False, limited_bones=list(current_bone_group), attempts=current_attempt_records, compensation_applied=False)
    apply_priority_fraction((), 1.0)
    return {'strategy': 'unresolved_arm_priority_collision', 'unresolved': True, 'limited_bones': [], 'attempts': current_attempt_records, 'compensation_applied': False, 'reason': '현재 몸통·다리 목표에서 팔의 안전 시작점 없음. 원본 목표를 진단용으로 보존'}


def apply_priority_arm_barrier(current_rig_object, current_saved_poses, current_previous_poses, current_target_names, current_collision_probe, current_angle_step, current_refinement_count):
    import bpy
    from mathutils import Matrix
    current_rotation_pairs = {}
    current_maximum_angle = 0.0
    for current_bone_name in current_target_names:
        current_start_rotation = current_previous_poses.get(current_bone_name, Matrix.Identity(4)).to_quaternion().normalized()
        current_target_rotation = current_saved_poses[current_bone_name].to_quaternion().normalized()
        if current_start_rotation.dot(current_target_rotation) < 0:
            current_target_rotation.negate()
        current_maximum_angle = max(current_maximum_angle, math.degrees(2 * math.acos(min(1., abs(current_start_rotation.dot(current_target_rotation))))))
        current_rotation_pairs[current_bone_name] = (current_start_rotation, current_target_rotation)
    current_priority_groups = []
    current_accumulated_names = []
    # 체인 자체는 근위→원위로 검증된다. 제한은 양손부터 근위 방향으로 확대한다.
    current_left_chain = [current_bone_name for current_bone_name in current_target_names if current_bone_name.endswith('.L')]
    current_right_chain = [current_bone_name[:-1] + 'R' for current_bone_name in current_left_chain]
    for current_left_name in reversed(current_left_chain):
        current_accumulated_names.extend((current_left_name, current_left_name[:-1] + 'R'))
        current_priority_groups.append(tuple(current_bone_name for current_bone_name in current_accumulated_names if current_bone_name in current_left_chain))
        current_priority_groups.append(tuple(current_bone_name for current_bone_name in current_accumulated_names if current_bone_name in current_right_chain))
        current_priority_groups.append(tuple(current_accumulated_names))

    def apply_priority_fraction(current_bone_group, current_pose_fraction):
        for current_pose_bone in current_rig_object.pose.bones:
            current_pose_bone.matrix_basis = current_saved_poses[current_pose_bone.name]
        for current_bone_name in current_bone_group:
            current_pose_bone = current_rig_object.pose.bones[current_bone_name]
            current_pose_bone.rotation_mode = 'QUATERNION'
            current_start_rotation, current_target_rotation = current_rotation_pairs[current_bone_name]
            current_pose_bone.rotation_quaternion = current_start_rotation.slerp(current_target_rotation, current_pose_fraction)
        bpy.context.view_layer.update()

    return resolve_priority_collision(current_priority_groups, apply_priority_fraction, current_collision_probe, max(1, math.ceil(current_maximum_angle / current_angle_step)), current_refinement_count)
