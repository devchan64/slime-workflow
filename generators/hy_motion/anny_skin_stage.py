"""HY-Motion→ANNY 피부 제약 후처리. 채택 기본값과 명시적 실험 프로필을 지원한다."""
from pathlib import Path
import json
import math
import time
import threading
import hashlib
import traceback

from generators.hy_motion.skin_barrier_profile import load_skin_barrier, SKIN_BARRIER_PROFILE

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
SAFE_POSE_REUSE_MARGIN = 0.00001


def apply_anny_skin_barrier(source_blend_path, output_directory_path, *, source_motion_path, skin_profile_path=SKIN_BARRIER_PROFILE):
    """원본 머리 회전과 피부 제약을 기본 적용하고 저장·보간 경고까지 반환한다."""
    import bpy
    import numpy as np
    from mathutils import Matrix
    from generators.hy_motion.skin_collision_barrier import advance_collision_free, detect_surface_collision as detect_unfiltered_collision
    from generators.hy_motion.head_rotation_transfer import apply_head_rotation, load_head_motion_rotations, transfer_head_rotation, HEAD_TRANSFER_TOLERANCE
    from generators.momask.body_proportion_retarget import build_surface_partitions, count_surface_intersections as count_unfiltered_intersections

    source_blend_path = Path(source_blend_path).resolve()
    source_motion_path = Path(source_motion_path).resolve()
    output_directory_path = Path(output_directory_path).resolve()
    skin_profile_path = Path(skin_profile_path).resolve()
    current_profile_record = load_skin_barrier(skin_profile_path)
    if not source_blend_path.is_file() or source_blend_path.suffix != '.blend':
        raise ValueError('존재하는 ANNY 리타기팅 Blender 입력이 필요합니다.')
    if not output_directory_path.is_relative_to(WORKFLOW_ROOT_DIRECTORY / '.tmp/test'):
        raise ValueError('후처리 결과는 새 .tmp/test 실험 실행 폴더 안에 저장해야 합니다.')
    output_directory_path.mkdir(parents=True, exist_ok=False)
    current_progress_state = {'stage': 'prepare'}
    current_shutdown_event = threading.Event()
    current_log_lock = threading.Lock()

    def emit_stage_progress(current_stage_name, current_stage_message):
        current_log_line = f'{time.strftime("%FT%T")}/skin-barrier/{current_stage_name} {current_stage_message}'
        with current_log_lock, (output_directory_path / 'worker.log').open('a') as current_log_stream:
            current_log_stream.write(current_log_line + '\n')
        print(current_log_line, flush=True)

    def emit_stage_heartbeat():
        while not current_shutdown_event.wait(5):
            emit_stage_progress('heartbeat', str(current_progress_state))

    current_heartbeat_thread = threading.Thread(target=emit_stage_heartbeat, daemon=True)
    current_heartbeat_thread.start()
    emit_stage_progress('start', f'입력={source_blend_path} 출력={output_directory_path} 프로필={current_profile_record["profile_id"]}')
    try:
        bpy.ops.wm.open_mainfile(filepath=str(source_blend_path))
        current_rig_object = bpy.data.objects[current_profile_record['target_rig']]
        current_preserve_local_head = current_rig_object.get('hy_motion_rotation_policy') == 'body_local_ownership_v1'
        current_body_object = bpy.data.objects[current_profile_record['target_mesh']]
        current_frame_count = bpy.context.scene.frame_end
        if bpy.context.scene.frame_start != 1 or current_frame_count < 1:
            raise ValueError('ANNY 입력은 1프레임부터 시작하는 비어 있지 않은 클립이어야 합니다.')
        if abs(bpy.context.scene.render.fps / bpy.context.scene.render.fps_base - 30) > 1e-8:
            raise ValueError('ANNY 클립과 원본 모션은 같은 30 FPS여야 합니다.')
        current_head_rotations, current_head_source_record = load_head_motion_rotations(source_motion_path, current_frame_count)
        current_head_bind_rotation = np.asarray(current_rig_object.data.bones['head'].matrix_local.to_quaternion().to_matrix())
        emit_stage_progress('head-source', f'입력={source_motion_path} FK 오차={current_head_source_record["fk_error_m"]}')
        if any(abs(current_scale_value - 1) > 1e-6 for current_scale_value in current_body_object.scale):
            raise ValueError('피부 여유를 적용할 메시의 스케일은 1이어야 합니다.')
        current_partition_faces = build_surface_partitions(current_body_object)
        current_collision_batches = None
        current_excluded_pairs = []
        current_relation_snapshot = None
        if current_profile_record['adjacent_connections'] == 'upperarm_upper_spine_five_hops':
            from generators.hy_motion.shoulder_adjacency_filter import prepare_shoulder_filter, evaluate_filtered_collisions
            from generators.hy_motion.collision_relations import load_collision_relations
            current_relation_record, current_relation_hash = load_collision_relations()
            current_parent_names = {current_bone_record.name: current_bone_record.parent.name if current_bone_record.parent else None for current_bone_record in current_rig_object.data.bones}
            current_relation_snapshot = {'profile': current_relation_record, 'sha256': current_relation_hash, 'rig_parents': current_parent_names, 'scope': '팔·손 대 몸통·골반·다리 검사. 전체 리그 관계를 보존하되 전신 충돌 검사는 아님'}
            (output_directory_path / 'collision-relations.json').write_text(json.dumps(current_relation_snapshot, ensure_ascii=False, indent=2))
            current_collision_batches, current_excluded_pairs = prepare_shoulder_filter(current_body_object, current_rig_object, current_partition_faces, current_relation_record)

        def count_surface_intersections(current_mesh_object, current_surface_faces):
            if current_collision_batches is not None:
                return evaluate_filtered_collisions(current_mesh_object, current_collision_batches)
            return count_unfiltered_intersections(current_mesh_object, current_surface_faces)

        current_latest_contacts = []

        def detect_surface_collision(current_mesh_object, current_surface_faces, current_clearance_value):
            current_probe_contacts = []
            if current_collision_batches is not None:
                current_collision_found = evaluate_filtered_collisions(current_mesh_object, current_collision_batches, current_clearance_value, stop_on_collision=True, current_contact_records=current_probe_contacts)
                if current_collision_found:
                    current_latest_contacts[:] = current_probe_contacts
                return current_collision_found
            return detect_unfiltered_collision(current_mesh_object, current_surface_faces, current_clearance_value)
        current_target_names = tuple(current_bone_prefix + '.' + current_side_name for current_side_name in ('L', 'R') for current_bone_prefix in current_profile_record['bone_prefixes'])
        for current_side_name in ('L', 'R'):
            current_chain_names = [current_bone_prefix + '.' + current_side_name for current_bone_prefix in current_profile_record['bone_prefixes']]
            for current_parent_name, current_child_name in zip(current_chain_names, current_chain_names[1:]):
                if current_rig_object.pose.bones[current_child_name].parent != current_rig_object.pose.bones[current_parent_name]:
                    raise ValueError('ANNY 근위→원위 부모 체인 불일치')
        current_saved_frames = []
        current_saved_wrist_targets = []
        for current_frame_number in range(1, current_frame_count + 1):
            bpy.context.scene.frame_set(current_frame_number)
            current_saved_wrist_targets.append({current_side_name: current_rig_object.pose.bones['wrist.' + current_side_name].matrix.copy() for current_side_name in ('L', 'R')})
            if any(current_pose_bone.location.length > 1e-6 or any(abs(current_scale_value - 1) > 1e-6 for current_scale_value in current_pose_bone.scale) for current_pose_bone in current_rig_object.pose.bones):
                raise ValueError('본 평행이동·스케일 애니메이션은 피부 제약 단계에서 지원하지 않습니다.')
            current_saved_frames.append(({current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}, current_rig_object.location.copy(), {current_bone_name: np.asarray(current_rig_object.pose.bones[current_bone_name].head).copy() for current_bone_name in current_target_names}, count_surface_intersections(current_body_object, current_partition_faces)))
        current_rig_object.animation_data_clear()
        current_frame_records = []
        current_previous_rotations = {}
        current_previous_target_poses = {}
        current_previous_full_poses = None
        current_previous_root_location = None
        current_temporal_enabled = current_profile_record.get('initialization') == 'previous_pose_with_lateral_collision_repair'
        current_stop_only_enabled = current_profile_record.get('initialization') == 'previous_safe_pose_stop_before_collision'
        for current_frame_number, (current_saved_poses, current_root_location, current_target_points, current_before_counts) in enumerate(current_saved_frames, 1):
            bpy.context.scene.frame_set(current_frame_number)
            current_rig_object.location = current_root_location
            # 첫 목표 자세가 안전하면 기본 자세로 되돌리는 우회를 하지 않는다.
            current_preserve_first_pose = False
            if current_frame_number == 1:
                for current_pose_bone in current_rig_object.pose.bones:
                    current_pose_bone.matrix_basis = current_saved_poses[current_pose_bone.name]
                bpy.context.view_layer.update()
                current_preserve_first_pose = not detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m'])
            for current_pose_bone in current_rig_object.pose.bones:
                current_pose_bone.matrix_basis = Matrix.Identity(4) if current_pose_bone.name in current_target_names and not current_preserve_first_pose else current_saved_poses[current_pose_bone.name]
                if (current_temporal_enabled or current_stop_only_enabled) and current_pose_bone.name in current_previous_target_poses:
                    current_pose_bone.matrix_basis = current_previous_target_poses[current_pose_bone.name]
            bpy.context.view_layer.update()
            current_initialization_record = {'strategy': 'preserved_collision_free_target' if current_preserve_first_pose else 'local_rest'}
            current_diagnostic_only = False
            current_whole_pose_applied = False
            if current_stop_only_enabled:
                from generators.hy_motion.priority_skin_barrier import apply_priority_arm_barrier
                current_latest_contacts.clear()
                current_initialization_record = apply_priority_arm_barrier(current_rig_object, current_saved_poses, current_previous_target_poses, current_target_names, lambda: detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m']), current_profile_record['angle_step_degrees'], current_profile_record['boundary_refinements'])
                current_initialization_record.update(contacts=list(current_latest_contacts), priority_policy='몸통·골반·다리·루트 보존 > 팔 > 손', compensation_applied=False)
                current_diagnostic_only = current_initialization_record['unresolved']
                # 별도 우선순위 해결기가 이미 처리했다. 기존 근위→원위 루프는 실행하지 않는다.
                current_preserve_first_pose = True
                if current_diagnostic_only:
                    emit_stage_progress('WARN', f'{current_frame_number}프레임: 팔 안전 시작점 없음 · 고우선권 동작 보존 · 진단 전용')
            if not current_preserve_first_pose and (current_profile_record.get('initialization') == 'bilateral_rest_to_lateral_first_clear' or current_temporal_enabled):
                from generators.hy_motion.proximal_collision_start import initialize_proximal_collision_start
                current_initialization_record = initialize_proximal_collision_start(current_rig_object, lambda: detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m']), current_profile_record['angle_step_degrees'], current_profile_record['boundary_refinements'])
                current_initialization_record['strategy'] = 'previous_pose_with_lateral_collision_repair' if current_temporal_enabled and current_previous_target_poses else 'local_rest_with_lateral_collision_repair'
            if not current_diagnostic_only and any(count_surface_intersections(current_body_object, current_partition_faces).values()):
                raise ValueError(f'{current_frame_number}프레임의 기준 팔 시작 자세에 비인접 충돌 존재')
            current_bone_records = {}
            if current_stop_only_enabled:
                for current_bone_name in current_initialization_record.get('limited_bones', []):
                    current_bone_records[current_bone_name] = {'blocked': current_initialization_record.get('blocked', False), 'fraction': current_initialization_record['fraction'], 'contacts': current_initialization_record['contacts'], 'target_space': 'local_rotation', 'policy': 'hand_first_arm_stop'}
            for current_bone_name in (() if current_preserve_first_pose or current_diagnostic_only or current_whole_pose_applied else current_target_names):
                current_progress_state.update(stage='proximal-to-distal', frame=current_frame_number, bone=current_bone_name)
                current_pose_bone = current_rig_object.pose.bones[current_bone_name]
                current_pose_bone.rotation_mode = 'QUATERNION'
                current_start_rotation = current_pose_bone.rotation_quaternion.copy()
                current_target_rotation = current_saved_poses[current_bone_name].to_quaternion()
                # 손목도 제약 전 로컬 회전을 유지한다. 제한된 부모 회전을
                # 손목에서 역보상하여 공간 방향만 맞추는 동작은 하지 않는다.
                if current_start_rotation.dot(current_target_rotation) < 0:
                    current_target_rotation.negate()
                current_requested_angle = math.degrees(2 * math.acos(min(1, abs(current_start_rotation.normalized().dot(current_target_rotation.normalized())))))

                def apply_current_fraction(current_pose_fraction):
                    current_pose_bone.rotation_quaternion = current_start_rotation.slerp(current_target_rotation, current_pose_fraction)
                    bpy.context.view_layer.update()

                def probe_current_collision():
                    return detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m'])

                current_latest_contacts.clear()
                current_bone_record = advance_collision_free(apply_current_fraction, probe_current_collision, max(1, math.ceil(current_requested_angle / current_profile_record['angle_step_degrees'])), current_profile_record['boundary_refinements'])
                current_bone_record['contacts'] = list(current_latest_contacts) if current_bone_record['blocked'] else []
                current_bone_record['contact_capture'] = 'blocked_fraction의 첫 검출 접촉' if current_collision_batches is not None else '미측정: 인접관절 필터 미사용 프로필'
                current_bone_record['requested_degrees'] = current_requested_angle
                current_bone_record['applied_degrees'] = current_requested_angle * current_bone_record['fraction']
                current_bone_record['target_space'] = 'pre_skin_parent_relative_rotation' if current_bone_name.startswith('wrist.') else 'local_rotation'
                current_bone_records[current_bone_name] = current_bone_record
            current_head_metrics = {'policy': '전신 로컬 전달·정지 결과 유지 · 머리 세계 방향 복원 없음'} if current_whole_pose_applied or current_preserve_local_head else apply_head_rotation(current_rig_object, current_head_rotations[current_frame_number - 1])
            if current_preserve_local_head:
                current_head_metrics['constrained_rotation_matrix'] = np.asarray(current_rig_object.pose.bones['head'].matrix.to_quaternion().to_matrix()).tolist()
            current_hand_diagnostics = {}
            for current_side_name in ('L', 'R'):
                current_target_matrix = current_saved_wrist_targets[current_frame_number - 1][current_side_name]
                current_actual_matrix = current_rig_object.pose.bones['wrist.' + current_side_name].matrix
                current_target_quaternion = current_target_matrix.to_quaternion().normalized()
                current_actual_quaternion = current_actual_matrix.to_quaternion().normalized()
                current_hand_diagnostics[current_side_name] = {'target_quaternion_wxyz': list(current_target_quaternion), 'actual_quaternion_wxyz': list(current_actual_quaternion), 'orientation_error_degrees': math.degrees(2 * math.acos(min(1, abs(current_target_quaternion.dot(current_actual_quaternion))))), 'space': 'armature', 'reference': '충돌 제약 이전 손목 공간 방향. 피부 표면 방향 오차와 구분', 'constraint_applied': not current_diagnostic_only, 'wrist_blocked': current_bone_records.get('wrist.' + current_side_name, {}).get('blocked', False)}
                current_wrist_name = 'wrist.' + current_side_name
                current_local_target = current_saved_poses[current_wrist_name].to_quaternion().normalized()
                current_local_actual = current_rig_object.pose.bones[current_wrist_name].matrix_basis.to_quaternion().normalized()
                current_hand_diagnostics[current_side_name].update(policy='preserve_pre_skin_parent_relative_rotation', parent_bone=current_rig_object.pose.bones[current_wrist_name].parent.name, target_local_quaternion_wxyz=list(current_local_target), actual_local_quaternion_wxyz=list(current_local_actual), parent_relative_error_degrees=math.degrees(2 * math.acos(min(1, abs(current_local_target.dot(current_local_actual))))), quality_note='공간 방향 오차와 부모 대비 상대 회전 오차를 구분. 해부학적 가동 범위·메시 비틀림은 별도 검수 필요')
            current_initialization_record['hand_orientation_diagnostics'] = current_hand_diagnostics
            if current_whole_pose_applied:
                current_head_metrics['constrained_rotation_matrix'] = [list(current_matrix_row) for current_matrix_row in current_rig_object.pose.bones['head'].matrix.to_quaternion().to_matrix()]
            if not current_diagnostic_only:
                current_previous_target_poses = {current_bone_name: current_rig_object.pose.bones[current_bone_name].matrix_basis.copy() for current_bone_name in current_target_names}
                # 경계의 행렬 복원 반올림으로 안전 판정이 뒤집히지 않도록
                # 재사용 시작 자세에만 0.01mm 수치 여유를 요구한다.
                if not detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m'] + SAFE_POSE_REUSE_MARGIN):
                    current_previous_full_poses = {current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}
                    current_previous_root_location = current_rig_object.location.copy()
            current_after_counts = count_surface_intersections(current_body_object, current_partition_faces)
            if not current_diagnostic_only and any(current_after_counts.values()):
                raise ValueError('제약 적용 후 피부 충돌 잔존')
            current_endpoint_errors = {current_bone_name: float(np.linalg.norm(np.asarray(current_rig_object.pose.bones[current_bone_name].head) - current_target_points[current_bone_name])) for current_bone_name in current_target_names}
            if current_stop_only_enabled and (current_rig_object.location - current_root_location).length > 1e-6:
                raise ValueError('충돌 제약이 고우선권 루트 이동을 변경했습니다.')
            for current_pose_bone in current_rig_object.pose.bones:
                if not current_whole_pose_applied and current_pose_bone.name not in (*current_target_names, 'head') and np.max(np.abs(np.asarray(current_pose_bone.matrix_basis) - np.asarray(current_saved_poses[current_pose_bone.name]))) > 1e-6:
                    raise ValueError('비대상 로컬 자세 변경')
                current_pose_bone.rotation_mode = 'QUATERNION'
                if current_pose_bone.name in current_previous_rotations and current_previous_rotations[current_pose_bone.name].dot(current_pose_bone.rotation_quaternion) < 0:
                    current_pose_bone.rotation_quaternion.negate()
                current_previous_rotations[current_pose_bone.name] = current_pose_bone.rotation_quaternion.copy()
                current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
            current_rig_object.keyframe_insert('location', frame=current_frame_number)
            current_frame_records.append({'frame': current_frame_number, 'before': current_before_counts, 'after': current_after_counts, 'endpoint_error_m': current_endpoint_errors, 'bones': current_bone_records, 'head_transfer': current_head_metrics, 'initialization': current_initialization_record})
        current_candidate_path = output_directory_path / 'barrier'
        current_candidate_path.mkdir()
        bpy.context.scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(current_candidate_path / 'mannequin.blend'))
        # 저장 후 실제 보간 자세를 재검사한다. 잔존 충돌은 숨기지 않고 품질 경고로 기록한다.
        bpy.ops.wm.open_mainfile(filepath=str(current_candidate_path / 'mannequin.blend'))
        current_body_object = bpy.data.objects[current_profile_record['target_mesh']]
        current_rig_object = bpy.data.objects[current_profile_record['target_rig']]
        current_audit_records = []
        current_previous_rotations = {}
        current_saved_head_error = 0.0
        for current_sample_index in range((current_frame_count - 1) * current_profile_record['audit_substeps'] + 1):
            current_sample_time = 1 + current_sample_index / current_profile_record['audit_substeps']
            current_progress_state.update(stage='saved-quarter-frame-audit', sample=current_sample_index)
            bpy.context.scene.frame_set(int(current_sample_time), subframe=current_sample_time % 1)
            current_rotation_steps = []
            for current_bone_name in (*current_target_names, 'head'):
                current_bone_rotation = current_rig_object.pose.bones[current_bone_name].matrix.to_quaternion().normalized()
                if current_bone_name in current_previous_rotations:
                    current_rotation_steps.append(math.degrees(2 * math.acos(min(1, abs(current_previous_rotations[current_bone_name].dot(current_bone_rotation))))))
                current_previous_rotations[current_bone_name] = current_bone_rotation.copy()
            if current_sample_time % 1 == 0:
                current_expected_rotation = transfer_head_rotation(current_head_rotations[int(current_sample_time) - 1], current_head_bind_rotation)
                if 'constrained_rotation_matrix' in current_frame_records[int(current_sample_time) - 1]['head_transfer']:
                    current_expected_rotation = np.asarray(current_frame_records[int(current_sample_time) - 1]['head_transfer']['constrained_rotation_matrix'])
                current_actual_rotation = np.asarray(current_rig_object.pose.bones['head'].matrix.to_quaternion().to_matrix())
                current_saved_head_error = max(current_saved_head_error, float(np.max(np.abs(current_actual_rotation - current_expected_rotation))))
            current_audit_records.append({'time': current_sample_time, 'intersections': count_surface_intersections(current_body_object, current_partition_faces), 'max_rotation_step_degrees': max(current_rotation_steps, default=0)})
            if current_collision_batches is not None:
                current_unfiltered_counts = count_unfiltered_intersections(current_body_object, current_partition_faces)
                current_audit_records[-1]['unfiltered_intersections'] = current_unfiltered_counts
                current_audit_records[-1]['excluded_intersections'] = {current_side_name: current_unfiltered_counts[current_side_name] - current_audit_records[-1]['intersections'][current_side_name] for current_side_name in ('L', 'R')}
        if current_saved_head_error > HEAD_TRANSFER_TOLERANCE:
            raise ValueError('저장 후 원본 머리 회전 전달 검증 실패')
        current_quality_warnings = ['혼합 경계·완전 내포·연속 시간 전체에 대한 충돌 보장은 없음', '원본 자세와 손목 방향은 충돌 제약으로 달라질 수 있음']
        if any(current_frame_record['initialization']['strategy'] == 'whole_pose_stop_before_collision' for current_frame_record in current_frame_records):
            current_quality_warnings.append('전신 동일 비율 정지 적용: 몸통·다리·루트도 제한되어 원본 동작 손실 가능. 보상 회전 없음')
        current_unresolved_frames = [current_frame_record['frame'] for current_frame_record in current_frame_records if current_frame_record['initialization'].get('unresolved')]
        if current_unresolved_frames:
            current_quality_warnings.append(f'안전 시작점 없는 진단 전용 프레임 {current_unresolved_frames}: 원본 충돌 자세 보존, 충돌 직전 정지 성공으로 간주하지 않음')
        if any(any(current_audit_record['intersections'].values()) for current_audit_record in current_audit_records):
            current_quality_warnings.append('저장 후 재생 표본에서 잔존 충돌 검출: 비관통은 보장하지 않음')
        current_summary_record = {'before_mean': {current_side_name: float(np.mean([current_frame_record['before'][current_side_name] for current_frame_record in current_frame_records])) for current_side_name in ('L', 'R')}, 'after_mean': {current_side_name: float(np.mean([current_frame_record['after'][current_side_name] for current_frame_record in current_frame_records])) for current_side_name in ('L', 'R')}, 'audit_colliding_samples': sum(any(current_audit_record['intersections'].values()) for current_audit_record in current_audit_records), 'max_quarter_frame_rotation_step_degrees': max(current_audit_record['max_rotation_step_degrees'] for current_audit_record in current_audit_records), 'max_wrist_target_error_m': max(current_frame_record['endpoint_error_m'][current_bone_name] for current_frame_record in current_frame_records for current_bone_name in ('wrist.L', 'wrist.R'))}
        current_result_record = {'status': 'completed', 'summary': current_summary_record, 'frames': current_frame_records, 'audit': current_audit_records, 'quality_warnings': current_quality_warnings, 'source_sha256': hashlib.sha256(source_blend_path.read_bytes()).hexdigest(), 'solver_sha256': hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/skin_collision_barrier.py').read_bytes()).hexdigest(), 'minimum_vertex_surface_clearance_m': current_profile_record['minimum_surface_clearance_m'], 'step_degrees': current_profile_record['angle_step_degrees'], 'refinements': current_profile_record['boundary_refinements'], 'order': current_target_names, 'collision_scope': '동일 부위 지배 가중치 삼각형의 팔/손 대 몸통/골반/다리. 팔 내부·어깨 접합 혼합 경계 제외', 'profile': current_profile_record, 'profile_sha256': hashlib.sha256(skin_profile_path.read_bytes()).hexdigest(), 'approved_profile_applied': current_profile_record['approval_status'] == 'accepted_with_replay_warnings', 'nonpenetration_guaranteed': False}
        current_result_record.update(blend_path='barrier/mannequin.blend', stage_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), surface_solver_sha256=hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/momask/body_proportion_retarget.py').read_bytes()).hexdigest())
        current_result_record['priority_solver_sha256'] = hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/priority_skin_barrier.py').read_bytes()).hexdigest()
        current_result_record['head_transfer'] = {'applied': not current_preserve_local_head, 'policy': 'pre_skin_local_rotation_preserved' if current_preserve_local_head else 'legacy_source_world_rotation', 'source': current_head_source_record, 'max_saved_rotation_matrix_error': current_saved_head_error, 'verification_scope': '저장 전후 적용 자세 보존; 원본 목표 일치나 품질 승인이 아님', 'solver_sha256': hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/head_rotation_transfer.py').read_bytes()).hexdigest()}
        if current_collision_batches is not None:
            current_result_record['adjacency_filter'] = {'excluded_bone_pairs': current_excluded_pairs, 'maximum_hops': 5, 'solver_sha256': hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/shoulder_adjacency_filter.py').read_bytes()).hexdigest()}
            current_result_record['collision_relations'] = current_relation_snapshot
            current_result_record['adjacency_filter'].pop('maximum_hops', None)
            current_quality_warnings.append('충돌 관계 설정의 허용 본 쌍은 제약에서 제외함. 제외 영역의 관통은 별도 검수 필요')
            current_summary_record['audit_unfiltered_colliding_samples'] = sum(any(current_audit_record['unfiltered_intersections'].values()) for current_audit_record in current_audit_records)
            current_summary_record['audit_excluded_colliding_samples'] = sum(any(current_audit_record['excluded_intersections'].values()) for current_audit_record in current_audit_records)
        (output_directory_path / 'comparison.json').write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
        (output_directory_path / 'outcome.json').write_text(json.dumps({'status': 'completed', 'quality_warnings': current_quality_warnings}, ensure_ascii=False))
        emit_stage_progress('completed', str(current_summary_record))
        return current_result_record
    except Exception as current_execution_error:
        current_failure_record = {'status': 'failed', 'error': str(current_execution_error)}
        (output_directory_path / 'outcome.json').write_text(json.dumps(current_failure_record, ensure_ascii=False))
        emit_stage_progress('failed', traceback.format_exc())
        raise
    finally:
        current_shutdown_event.set()
        current_heartbeat_thread.join(timeout=1)
