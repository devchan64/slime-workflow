"""상완–상부 척추의 제한된 본 계층 이웃만 제외하는 실험용 피부 검사."""
import math

# 2026-10-08 ANNY 스트레칭 검수: 상완–상부 척추 제약을 완화하자 팔 내리기가
# 개선됐다. 겹침 허용은 전신 공통값이 아니라 부위 관계에 따라 차등 적용해야 한다.
# 관절 접합부의 스키닝 겹침, 상완–겨드랑이·상부 몸통의 제한적 겹침,
# 전완·손–몸통·골반의 비인접 관통을 구분하는 방향으로 후속 검증한다.
# 아래 5단계 제외는 이 리그의 실험용 분류일 뿐 해부학적 허용 한도가 아니다.
# 현재는 제외 쌍의 깊거나 지속적인 관통도 막지 못한다. 최종 허용량은 침범 깊이·
# 지속 시간·원본 동작 보존 정도를 함께 측정해 정해야 하며, 수치는 아직 미검증이다.
UPPER_ARM_BONE_NAMES = ('upperarm01.L', 'upperarm02.L', 'upperarm01.R', 'upperarm02.R')
UPPER_SPINE_BONE_NAMES = ('spine01', 'spine02')
MAXIMUM_ADJACENCY_HOPS = 5


def calculate_bone_distance(current_parent_names, current_first_name, current_second_name):
    """무방향 부모 간선 수를 계산한다. 없는 본·순환·분리 골격은 거절한다."""
    def collect_parent_chain(current_start_name):
        current_parent_chain = []
        while current_start_name is not None:
            if current_start_name not in current_parent_names or current_start_name in current_parent_chain:
                raise ValueError('인접성 골격에 없는 본 또는 부모 순환 존재')
            current_parent_chain.append(current_start_name)
            current_start_name = current_parent_names[current_start_name]
        return current_parent_chain
    current_first_chain = collect_parent_chain(current_first_name)
    current_second_chain = collect_parent_chain(current_second_name)
    for current_second_distance, current_bone_name in enumerate(current_second_chain):
        if current_bone_name in current_first_chain:
            return current_second_distance + current_first_chain.index(current_bone_name)
    raise ValueError('공통 조상 없는 인접성 골격')


def select_excluded_pairs(current_parent_names):
    """상완 네 본과 상부 척추 두 본 사이에서만 5단계 이웃을 선택한다."""
    return frozenset((current_arm_name, current_spine_name) for current_arm_name in UPPER_ARM_BONE_NAMES for current_spine_name in UPPER_SPINE_BONE_NAMES if calculate_bone_distance(current_parent_names, current_arm_name, current_spine_name) <= MAXIMUM_ADJACENCY_HOPS)


def build_filtered_batches(current_partition_faces, current_vertex_labels, current_excluded_pairs):
    """삼각형 지배 본의 모든 조합이 제외 대상일 때만 그 삼각형 쌍을 뺀다."""
    current_body_labels = [frozenset(current_vertex_labels[current_vertex_index] for current_vertex_index in current_face_record) for current_face_record in current_partition_faces['body']]
    current_collision_batches = []
    for current_side_name in ('L', 'R'):
        current_grouped_faces = {}
        for current_arm_face in current_partition_faces[current_side_name]:
            current_arm_labels = frozenset(current_vertex_labels[current_vertex_index] for current_vertex_index in current_arm_face)
            current_excluded_labels = frozenset(current_body_name for _, current_body_name in current_excluded_pairs if all((current_arm_name, current_body_name) in current_excluded_pairs for current_arm_name in current_arm_labels))
            current_grouped_faces.setdefault(current_excluded_labels, []).append(current_arm_face)
        for current_excluded_labels, current_arm_faces in current_grouped_faces.items():
            current_body_faces = [current_body_face for current_body_face, current_face_labels in zip(current_partition_faces['body'], current_body_labels) if not current_face_labels <= current_excluded_labels]
            if not current_body_faces:
                raise ValueError('인접성 완화로 몸통 검사 전체가 제거됨')
            current_collision_batches.append((current_side_name, current_arm_faces, current_body_faces))
    return current_collision_batches


def prepare_shoulder_filter(current_body_object, current_rig_object, current_partition_faces):
    current_parent_names = {current_bone_record.name: current_bone_record.parent.name if current_bone_record.parent else None for current_bone_record in current_rig_object.data.bones}
    current_excluded_pairs = select_excluded_pairs(current_parent_names)
    current_group_names = {current_group_record.index: current_group_record.name for current_group_record in current_body_object.vertex_groups}
    current_vertex_labels = []
    for current_vertex_record in current_body_object.data.vertices:
        if not current_vertex_record.groups:
            raise ValueError('가중치 없는 정점')
        current_vertex_labels.append(current_group_names[max(current_vertex_record.groups, key=lambda current_group_record: current_group_record.weight).group])
    return build_filtered_batches(current_partition_faces, current_vertex_labels, current_excluded_pairs), sorted(current_excluded_pairs)


def evaluate_filtered_collisions(current_body_object, current_collision_batches, minimum_surface_clearance=0.0, *, stop_on_collision=False):
    """검사 대상 교차 수 또는 여유 포함 bool. 제외 대상 뒤의 근접면도 검사한다."""
    import bpy
    from mathutils.bvhtree import BVHTree
    if type(minimum_surface_clearance) not in (int, float) or not math.isfinite(minimum_surface_clearance) or minimum_surface_clearance < 0:
        raise ValueError('피부 여유는 유한한 음이 아닌 값이어야 합니다.')
    if minimum_surface_clearance and not stop_on_collision:
        raise ValueError('교차 집계와 수치 여유 검사는 구분해야 합니다.')
    current_evaluated_object = current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
    current_evaluated_mesh = current_evaluated_object.to_mesh()
    try:
        if len(current_evaluated_mesh.vertices) != len(current_body_object.data.vertices):
            raise ValueError('피부 토폴로지 변경')
        current_vertex_points = [current_vertex_record.co.copy() for current_vertex_record in current_evaluated_mesh.vertices]
        current_result_counts = {'L': 0, 'R': 0}
        for current_side_name, current_arm_faces, current_body_faces in current_collision_batches:
            current_body_tree = BVHTree.FromPolygons(current_vertex_points, current_body_faces, all_triangles=True)
            current_arm_tree = BVHTree.FromPolygons(current_vertex_points, current_arm_faces, all_triangles=True)
            for current_arm_index, current_body_index in current_arm_tree.overlap(current_body_tree):
                if not set(current_arm_faces[current_arm_index]).intersection(current_body_faces[current_body_index]):
                    if stop_on_collision:
                        return True
                    current_result_counts[current_side_name] += 1
            if minimum_surface_clearance:
                for current_vertex_index in {current_vertex_index for current_face_record in current_arm_faces for current_vertex_index in current_face_record}:
                    if current_body_tree.find_nearest(current_vertex_points[current_vertex_index], minimum_surface_clearance)[0] is not None:
                        return True
        return False if stop_on_collision else current_result_counts
    finally:
        current_evaluated_object.to_mesh_clear()
