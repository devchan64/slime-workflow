"""본 애니메이션을 보존하는 Blender 렌더 표면 보정과 리그 검사."""
import math

SURFACE_CORRECTION_SETTINGS = {
    'method': 'corrective-smooth', 'factor': 0.5, 'iterations': 10,
    'pin_boundary': True, 'scope': 'blender-render-only',
}


def apply_surface_correction(body_object_value):
    """ARMATURE 뒤에 한 번만 적용한다. GLB의 변형 방식은 변경하지 않는다."""
    if not any(item.type == 'ARMATURE' for item in body_object_value.modifiers):
        raise ValueError('표면 보정에 필요한 Armature modifier가 없습니다.')
    modifier_name_value = 'MoMaskSurfaceCorrection'
    surface_modifier_value = body_object_value.modifiers.get(modifier_name_value)
    if surface_modifier_value is None:
        surface_modifier_value = body_object_value.modifiers.new(modifier_name_value, 'CORRECTIVE_SMOOTH')
    if surface_modifier_value.type != 'CORRECTIVE_SMOOTH':
        raise ValueError('표면 보정 modifier 이름 충돌')
    surface_modifier_value.factor = SURFACE_CORRECTION_SETTINGS['factor']
    surface_modifier_value.iterations = SURFACE_CORRECTION_SETTINGS['iterations']
    surface_modifier_value.use_pin_boundary = SURFACE_CORRECTION_SETTINGS['pin_boundary']
    return dict(SURFACE_CORRECTION_SETTINGS)


def inspect_skin_rig(body_object_value, rig_object_value):
    """실제 변형 본 가중치만 검사한다. 보조 vertex group은 제외한다."""
    deform_bone_names = {bone.name for bone in rig_object_value.data.bones if bone.use_deform}
    deform_group_indices = {group.index for group in body_object_value.vertex_groups if group.name in deform_bone_names}
    vertex_weight_sums = [sum(group.weight for group in vertex.groups if group.group in deform_group_indices)
                          for vertex in body_object_value.data.vertices]
    if not vertex_weight_sums or not all(math.isfinite(weight) for weight in vertex_weight_sums):
        raise ValueError('스킨 정점 또는 가중치가 유효하지 않습니다.')
    unweighted_vertex_count = sum(weight <= 1e-8 for weight in vertex_weight_sums)
    normalization_error_count = sum(abs(weight - 1) > 1e-4 for weight in vertex_weight_sums)
    return {
        'vertices': len(vertex_weight_sums), 'unweighted_vertices': unweighted_vertex_count,
        'non_normalized_vertices': normalization_error_count,
        'weight_min': min(vertex_weight_sums), 'weight_max': max(vertex_weight_sums),
        'bone_hierarchy': {bone.name: bone.parent.name if bone.parent else None for bone in rig_object_value.data.bones},
        'quality_warnings': (['변형 본 가중치 누락 또는 정규화 오류가 있습니다.']
                             if unweighted_vertex_count or normalization_error_count else []),
        'inspection_limits': '가중치·계층 구조 검사이며 해부학적 회전, 관통, GLB 렌더 품질 승인을 의미하지 않습니다.',
    }
