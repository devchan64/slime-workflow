"""검출된 첫 피부 충돌 앞에서 자세 진행을 멈추는 실험용 이산 경계 탐색."""
import math


def detect_surface_collision(current_body_object, current_partition_faces, minimum_surface_clearance):
    """비인접 교차 또는 팔 정점→몸통 삼각형의 수치 여유 부족을 검출한다.

    여유는 메시 로컬 단위다. 완전 내포·모든 변 간 거리·연속 충돌 검사는 아니다.
    """
    import bpy
    from mathutils.bvhtree import BVHTree

    if type(minimum_surface_clearance) not in (int, float) or not math.isfinite(minimum_surface_clearance) or minimum_surface_clearance < 0:
        raise ValueError('피부 수치 여유는 유한한 음이 아닌 값이어야 합니다.')
    if set(current_partition_faces) != {'L', 'R', 'body'} or any(not current_face_list for current_face_list in current_partition_faces.values()):
        raise ValueError('양팔·몸통 삼각형 분류가 필요합니다.')
    current_evaluated_object = current_body_object.evaluated_get(bpy.context.evaluated_depsgraph_get())
    current_evaluated_mesh = current_evaluated_object.to_mesh()
    try:
        if len(current_evaluated_mesh.vertices) != len(current_body_object.data.vertices):
            raise ValueError('피부 토폴로지가 변경되었습니다.')
        current_vertex_points = [current_vertex_record.co.copy() for current_vertex_record in current_evaluated_mesh.vertices]
        current_body_tree = BVHTree.FromPolygons(current_vertex_points, current_partition_faces['body'], all_triangles=True)
        for current_side_name in ('L', 'R'):
            current_arm_faces = current_partition_faces[current_side_name]
            current_arm_tree = BVHTree.FromPolygons(current_vertex_points, current_arm_faces, all_triangles=True)
            if any(not set(current_arm_faces[current_arm_index]).intersection(current_partition_faces['body'][current_body_index]) for current_arm_index, current_body_index in current_arm_tree.overlap(current_body_tree)):
                return True
            if minimum_surface_clearance > 0:
                for current_vertex_index in {current_vertex_index for current_face_record in current_arm_faces for current_vertex_index in current_face_record}:
                    current_nearest_result = current_body_tree.find_nearest(current_vertex_points[current_vertex_index], minimum_surface_clearance)
                    if current_nearest_result[0] is not None:
                        return True
        return False
    finally:
        current_evaluated_object.to_mesh_clear()


def advance_collision_free(apply_pose_fraction, probe_skin_collision, current_step_count, current_refinement_count):
    """안전한 0에서 1로 순서대로 검사한다. 연속 충돌 검출을 보장하지 않는다."""
    if type(current_step_count) is not int or current_step_count < 1 or type(current_refinement_count) is not int or not 0 <= current_refinement_count <= 24:
        raise ValueError('진행 단계는 양의 정수, 경계 세분화는 0~24 정수여야 합니다.')
    current_safe_fraction = 0.0
    current_probe_count = 0

    def evaluate_pose_fraction(current_pose_fraction):
        nonlocal current_probe_count
        apply_pose_fraction(current_pose_fraction)
        current_probe_result = probe_skin_collision()
        current_probe_count += 1
        if type(current_probe_result) is not bool:
            raise ValueError('피부 충돌 검사는 bool을 반환해야 합니다.')
        return current_probe_result

    if evaluate_pose_fraction(0.0):
        raise ValueError('시작 자세에 피부 충돌이 있어 경계 진행을 시작할 수 없습니다.')
    try:
        for current_step_index in range(1, current_step_count + 1):
            current_trial_fraction = current_step_index / current_step_count
            if not evaluate_pose_fraction(current_trial_fraction):
                current_safe_fraction = current_trial_fraction
                continue
            current_blocked_fraction = current_trial_fraction
            for current_refinement_index in range(current_refinement_count):
                current_midpoint_fraction = (current_safe_fraction + current_blocked_fraction) / 2
                if evaluate_pose_fraction(current_midpoint_fraction):
                    current_blocked_fraction = current_midpoint_fraction
                else:
                    current_safe_fraction = current_midpoint_fraction
            apply_pose_fraction(current_safe_fraction)
            return {'fraction': current_safe_fraction, 'blocked_fraction': current_blocked_fraction, 'probes': current_probe_count, 'blocked': True}
        return {'fraction': 1.0, 'blocked_fraction': None, 'probes': current_probe_count, 'blocked': False}
    except Exception:
        apply_pose_fraction(current_safe_fraction)
        raise
