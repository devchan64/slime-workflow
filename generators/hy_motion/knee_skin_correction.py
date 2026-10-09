"""관절 회전을 바꾸지 않는 무릎 국소 변형 평활화 실험."""
import math

KNEE_CORRECTION_GROUP = 'HyMotionKneeCorrection'
KNEE_CORRECTION_MODIFIER = 'HyMotionKneeCorrectiveSmooth'
KNEE_RADIUS_LENGTH_RATIO = 0.32
KNEE_SMOOTHING_FACTOR = 0.5
KNEE_SMOOTHING_ITERATIONS = 5
KNEE_WEIGHT_HALF_WIDTH = 0.09
KNEE_POSTERIOR_HALF_WIDTH = 0.14
KNEE_POSTERIOR_BLEND_DEPTH = 0.06


def redistribute_knee_skin_weights(current_body_object, current_rig_object, *, use_posterior_weight_profile=False):
    """승인된 허벅지 말단·종아리 기저 가중치 재분배. 관절은 변경하지 않는다."""
    if current_body_object.get('hy_motion_knee_weight_profile'):
        raise ValueError('무릎 가중치 재분배가 이미 적용되어 있습니다.')
    current_mesh_transform = current_body_object.matrix_world.inverted() @ current_rig_object.matrix_world
    current_changed_records = []
    for current_side_name in ('L', 'R'):
        current_upper_group = current_body_object.vertex_groups['upperleg02.' + current_side_name]
        current_lower_group = current_body_object.vertex_groups['lowerleg01.' + current_side_name]
        current_knee_center = current_mesh_transform @ current_rig_object.data.bones['lowerleg01.' + current_side_name].head_local
        current_ankle_center = current_mesh_transform @ current_rig_object.data.bones['foot.' + current_side_name].head_local
        current_down_axis = (current_ankle_center - current_knee_center).normalized()
        current_toe_center = current_mesh_transform @ current_rig_object.data.bones['toe3-1.' + current_side_name].head_local
        current_forward_axis = current_toe_center - current_ankle_center
        current_forward_axis -= current_down_axis * current_forward_axis.dot(current_down_axis)
        if current_forward_axis.length < 1e-6:
            raise ValueError('무릎 앞뒤 판별 축이 퇴화했습니다.')
        current_forward_axis.normalize()
        for current_mesh_vertex in current_body_object.data.vertices:
            current_existing_weights = {current_assignment.group: current_assignment.weight for current_assignment in current_mesh_vertex.groups}
            current_upper_weight = current_existing_weights.get(current_upper_group.index, 0.)
            current_lower_weight = current_existing_weights.get(current_lower_group.index, 0.)
            current_pair_weight = current_upper_weight + current_lower_weight
            current_offset_vector = current_mesh_vertex.co - current_knee_center
            current_axis_distance = current_offset_vector.dot(current_down_axis)
            current_posterior_factor = min(1., max(0., -current_offset_vector.dot(current_forward_axis) / KNEE_POSTERIOR_BLEND_DEPTH)) if use_posterior_weight_profile else 0.
            current_half_width = KNEE_WEIGHT_HALF_WIDTH + current_posterior_factor * (KNEE_POSTERIOR_HALF_WIDTH - KNEE_WEIGHT_HALF_WIDTH)
            if current_pair_weight < .5 or abs(current_axis_distance) >= 2 * current_half_width:
                continue
            current_transition_value = min(1., max(0., (current_axis_distance + current_half_width) / (2 * current_half_width)))
            current_transition_value = current_transition_value ** 2 * (3 - 2 * current_transition_value)
            current_blend_factor = min(1., max(0., 2 - abs(current_axis_distance) / current_half_width))
            current_lower_target = current_lower_weight + current_blend_factor * (current_pair_weight * current_transition_value - current_lower_weight)
            current_upper_group.add([current_mesh_vertex.index], current_pair_weight - current_lower_target, 'REPLACE')
            current_lower_group.add([current_mesh_vertex.index], current_lower_target, 'REPLACE')
            current_changed_records.append({'vertex': current_mesh_vertex.index, 'side': current_side_name, 'before_lower': current_lower_weight, 'after_lower': current_lower_target, 'pair_total': current_pair_weight})
    if not current_changed_records:
        raise ValueError('무릎 가중치 변경 대상이 없습니다.')
    current_profile_name = 'knee-posterior-v2-experimental' if use_posterior_weight_profile else 'knee-transition-v1'
    current_body_object['hy_motion_knee_weight_profile'] = current_profile_name
    return {'status': 'experimental' if use_posterior_weight_profile else 'user_selected', 'profile': current_profile_name, 'half_width_m': KNEE_WEIGHT_HALF_WIDTH, 'posterior_half_width_m': KNEE_POSTERIOR_HALF_WIDTH if use_posterior_weight_profile else KNEE_WEIGHT_HALF_WIDTH, 'changed_vertices': len(current_changed_records), 'changes': current_changed_records, 'joint_rotations_modified': False}


def apply_knee_skin_correction(current_body_object, current_rig_object):
    """기준 자세의 무릎 거리로 마스크를 만들고 Armature 뒤에 보정한다."""
    if current_body_object.vertex_groups.get(KNEE_CORRECTION_GROUP) or current_body_object.modifiers.get(KNEE_CORRECTION_MODIFIER):
        raise ValueError('무릎 스키닝 보정이 이미 적용되어 있습니다.')
    current_skin_modifiers = [current_modifier for current_modifier in current_body_object.modifiers if current_modifier.type == 'ARMATURE']
    if len(current_skin_modifiers) != 1 or current_skin_modifiers[0].object != current_rig_object:
        raise ValueError('무릎 보정에는 대상 리그의 단일 Armature가 필요합니다.')
    current_mesh_transform = current_body_object.matrix_world.inverted() @ current_rig_object.matrix_world
    current_knee_regions = []
    for current_side_name in ('L', 'R'):
        current_knee_bone = current_rig_object.data.bones['lowerleg01.' + current_side_name]
        current_hip_bone = current_rig_object.data.bones['upperleg01.' + current_side_name]
        current_knee_center = current_mesh_transform @ current_knee_bone.head_local
        current_region_radius = (current_mesh_transform @ current_hip_bone.head_local - current_knee_center).length * KNEE_RADIUS_LENGTH_RATIO
        if not math.isfinite(current_region_radius) or current_region_radius <= 0:
            raise ValueError('무릎 보정 반경이 유효하지 않습니다.')
        current_knee_regions.append((current_knee_center, current_region_radius))
    current_vertex_group = current_body_object.vertex_groups.new(name=KNEE_CORRECTION_GROUP)
    current_affected_vertices = 0
    for current_mesh_vertex in current_body_object.data.vertices:
        current_weight_value = max(max(0., 1. - (current_mesh_vertex.co - current_center_point).length / current_radius_value) for current_center_point, current_radius_value in current_knee_regions)
        current_weight_value = current_weight_value ** 2 * (3. - 2. * current_weight_value)
        if current_weight_value > 0:
            current_vertex_group.add([current_mesh_vertex.index], current_weight_value, 'REPLACE')
            current_affected_vertices += 1
    if not current_affected_vertices:
        raise ValueError('무릎 보정 마스크에 정점이 없습니다.')
    current_smooth_modifier = current_body_object.modifiers.new(KNEE_CORRECTION_MODIFIER, 'CORRECTIVE_SMOOTH')
    current_smooth_modifier.vertex_group = current_vertex_group.name
    current_smooth_modifier.factor = KNEE_SMOOTHING_FACTOR
    current_smooth_modifier.iterations = KNEE_SMOOTHING_ITERATIONS
    current_smooth_modifier.smooth_type = 'LENGTH_WEIGHTED'
    current_smooth_modifier.rest_source = 'ORCO'
    return {'status': 'experimental', 'affected_vertices': current_affected_vertices, 'radius_length_ratio': KNEE_RADIUS_LENGTH_RATIO, 'factor': KNEE_SMOOTHING_FACTOR, 'iterations': KNEE_SMOOTHING_ITERATIONS, 'joint_rotations_modified': False, 'skinning_weights_modified': False}
