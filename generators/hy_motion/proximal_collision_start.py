"""실제 리그 어깨 축을 따라 양팔의 첫 비충돌 시작 자세를 찾는 실험용 초기화."""
import math


def initialize_proximal_collision_start(current_rig_object, current_collision_probe, current_angle_step, current_refinement_count):
    """몸통은 유지하고 상완을 기준 방향→동측 어깨 바깥 방향으로 최소 회전한다."""
    import bpy
    from mathutils import Matrix, Quaternion

    if type(current_angle_step) not in (int, float) or not math.isfinite(current_angle_step) or not 0 < current_angle_step <= 180 or type(current_refinement_count) is not int or not 0 <= current_refinement_count <= 24:
        raise ValueError('시작 자세 탐색 간격·세분화 계약 오류')
    current_shoulder_axis = current_rig_object.pose.bones['upperarm01.L'].head - current_rig_object.pose.bones['upperarm01.R'].head
    if current_shoulder_axis.length < 1e-8:
        raise ValueError('양쪽 어깨 중심이 겹쳐 몸 바깥 방향을 정할 수 없습니다.')
    current_shoulder_axis.normalize()
    current_segment_records = []
    for current_side_name, current_side_sign in (('L', 1), ('R', -1)):
        current_start_bone = current_rig_object.pose.bones['upperarm01.' + current_side_name]
        current_arm_direction = current_rig_object.pose.bones['lowerarm01.' + current_side_name].head - current_start_bone.head
        if current_arm_direction.length < 1e-8:
            raise ValueError('상완 길이가 0입니다.')
        current_outward_rotation = current_arm_direction.rotation_difference(current_shoulder_axis * current_side_sign)
        current_segment_records.append((current_start_bone, current_start_bone.matrix_basis.copy(), current_start_bone.head.copy(), current_start_bone.matrix.to_quaternion(), current_outward_rotation))
    current_maximum_angle = max(math.degrees(current_segment_record[-1].angle) for current_segment_record in current_segment_records)
    current_step_count = max(1, math.ceil(current_maximum_angle / current_angle_step))
    current_probe_count = 0

    def evaluate_start_fraction(current_pose_fraction):
        nonlocal current_probe_count
        for current_pose_bone, current_saved_matrix, current_head_point, current_bind_rotation, current_outward_rotation in current_segment_records:
            current_pose_rotation = Quaternion().slerp(current_outward_rotation, current_pose_fraction) @ current_bind_rotation
            current_pose_bone.matrix = Matrix.Translation(current_head_point) @ current_pose_rotation.to_matrix().to_4x4()
            current_pose_bone.location = (0, 0, 0)
            current_pose_bone.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        current_collision_value = current_collision_probe()
        if type(current_collision_value) is not bool:
            raise ValueError('시작 자세 충돌 검사는 bool이어야 합니다.')
        current_probe_count += 1
        return current_collision_value

    try:
        current_clear_fraction = None
        current_blocked_fraction = 0.0
        for current_step_index in range(current_step_count + 1):
            current_trial_fraction = current_step_index / current_step_count
            if not evaluate_start_fraction(current_trial_fraction):
                current_clear_fraction = current_trial_fraction
                break
            current_blocked_fraction = current_trial_fraction
        if current_clear_fraction is None:
            raise ValueError('어깨 바깥 방향까지 탐색해도 비충돌 시작 자세를 찾지 못했습니다.')
        if current_clear_fraction:
            for current_refinement_index in range(current_refinement_count):
                current_midpoint_fraction = (current_blocked_fraction + current_clear_fraction) / 2
                if evaluate_start_fraction(current_midpoint_fraction):
                    current_blocked_fraction = current_midpoint_fraction
                else:
                    current_clear_fraction = current_midpoint_fraction
        if evaluate_start_fraction(current_clear_fraction):
            raise ValueError('찾은 시작 자세의 재검증에 실패했습니다.')
        return {'fraction': current_clear_fraction, 'probes': current_probe_count, 'outward_axis': list(current_shoulder_axis), 'upperarm_rotation_degrees': {current_segment_record[0].name: math.degrees(current_segment_record[-1].angle) * current_clear_fraction for current_segment_record in current_segment_records}}
    except Exception:
        for current_pose_bone, current_saved_matrix, *_ in current_segment_records:
            current_pose_bone.matrix_basis = current_saved_matrix
        bpy.context.view_layer.update()
        raise
