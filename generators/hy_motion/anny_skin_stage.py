"""채택된 HY-Motion→ANNY 피부 제약 후처리. 원본 모션 생성·GPU 렌더는 수행하지 않는다."""
from pathlib import Path
import json
import math
import time
import threading
import hashlib
import traceback

from generators.hy_motion.skin_barrier_profile import load_skin_barrier, SKIN_BARRIER_PROFILE

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]


def apply_anny_skin_barrier(source_blend_path, output_directory_path):
    """ANNY 리타기팅 결과를 새 폴더에 보존하고 저장·보간 충돌 경고까지 반환한다."""
    import bpy
    import numpy as np
    from mathutils import Matrix
    from generators.hy_motion.skin_collision_barrier import advance_collision_free, detect_surface_collision
    from generators.momask.body_proportion_retarget import build_surface_partitions, count_surface_intersections

    source_blend_path = Path(source_blend_path).resolve()
    output_directory_path = Path(output_directory_path).resolve()
    current_profile_record = load_skin_barrier()
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
        current_body_object = bpy.data.objects[current_profile_record['target_mesh']]
        current_frame_count = bpy.context.scene.frame_end
        if bpy.context.scene.frame_start != 1 or current_frame_count < 1:
            raise ValueError('ANNY 입력은 1프레임부터 시작하는 비어 있지 않은 클립이어야 합니다.')
        if any(abs(current_scale_value - 1) > 1e-6 for current_scale_value in current_body_object.scale):
            raise ValueError('피부 여유를 적용할 메시의 스케일은 1이어야 합니다.')
        current_partition_faces = build_surface_partitions(current_body_object)
        current_target_names = tuple(current_bone_prefix + '.' + current_side_name for current_side_name in ('L', 'R') for current_bone_prefix in current_profile_record['bone_prefixes'])
        for current_side_name in ('L', 'R'):
            current_chain_names = [current_bone_prefix + '.' + current_side_name for current_bone_prefix in current_profile_record['bone_prefixes']]
            for current_parent_name, current_child_name in zip(current_chain_names, current_chain_names[1:]):
                if current_rig_object.pose.bones[current_child_name].parent != current_rig_object.pose.bones[current_parent_name]:
                    raise ValueError('ANNY 근위→원위 부모 체인 불일치')
        current_saved_frames = []
        for current_frame_number in range(1, current_frame_count + 1):
            bpy.context.scene.frame_set(current_frame_number)
            if any(current_pose_bone.location.length > 1e-6 or any(abs(current_scale_value - 1) > 1e-6 for current_scale_value in current_pose_bone.scale) for current_pose_bone in current_rig_object.pose.bones):
                raise ValueError('본 평행이동·스케일 애니메이션은 피부 제약 단계에서 지원하지 않습니다.')
            current_saved_frames.append(({current_pose_bone.name: current_pose_bone.matrix_basis.copy() for current_pose_bone in current_rig_object.pose.bones}, current_rig_object.location.copy(), {current_bone_name: np.asarray(current_rig_object.pose.bones[current_bone_name].head).copy() for current_bone_name in current_target_names}, count_surface_intersections(current_body_object, current_partition_faces)))
        current_rig_object.animation_data_clear()
        current_frame_records = []
        current_previous_rotations = {}
        for current_frame_number, (current_saved_poses, current_root_location, current_target_points, current_before_counts) in enumerate(current_saved_frames, 1):
            bpy.context.scene.frame_set(current_frame_number)
            current_rig_object.location = current_root_location
            for current_pose_bone in current_rig_object.pose.bones:
                current_pose_bone.matrix_basis = Matrix.Identity(4) if current_pose_bone.name in current_target_names else current_saved_poses[current_pose_bone.name]
            bpy.context.view_layer.update()
            if any(count_surface_intersections(current_body_object, current_partition_faces).values()):
                raise ValueError(f'{current_frame_number}프레임의 기준 팔 시작 자세에 비인접 충돌 존재')
            current_bone_records = {}
            for current_bone_name in current_target_names:
                current_progress_state.update(stage='proximal-to-distal', frame=current_frame_number, bone=current_bone_name)
                current_pose_bone = current_rig_object.pose.bones[current_bone_name]
                current_pose_bone.rotation_mode = 'QUATERNION'
                current_start_rotation = current_pose_bone.rotation_quaternion.copy()
                current_target_rotation = current_saved_poses[current_bone_name].to_quaternion()
                if current_start_rotation.dot(current_target_rotation) < 0:
                    current_target_rotation.negate()
                current_requested_angle = math.degrees(2 * math.acos(min(1, abs(current_start_rotation.normalized().dot(current_target_rotation.normalized())))))

                def apply_current_fraction(current_pose_fraction):
                    current_pose_bone.rotation_quaternion = current_start_rotation.slerp(current_target_rotation, current_pose_fraction)
                    bpy.context.view_layer.update()

                def probe_current_collision():
                    return detect_surface_collision(current_body_object, current_partition_faces, current_profile_record['minimum_surface_clearance_m'])

                current_bone_record = advance_collision_free(apply_current_fraction, probe_current_collision, max(1, math.ceil(current_requested_angle / current_profile_record['angle_step_degrees'])), current_profile_record['boundary_refinements'])
                current_bone_record['requested_degrees'] = current_requested_angle
                current_bone_records[current_bone_name] = current_bone_record
            current_after_counts = count_surface_intersections(current_body_object, current_partition_faces)
            if any(current_after_counts.values()):
                raise ValueError('제약 적용 후 피부 충돌 잔존')
            current_endpoint_errors = {current_bone_name: float(np.linalg.norm(np.asarray(current_rig_object.pose.bones[current_bone_name].head) - current_target_points[current_bone_name])) for current_bone_name in current_target_names}
            for current_pose_bone in current_rig_object.pose.bones:
                if current_pose_bone.name not in current_target_names and np.max(np.abs(np.asarray(current_pose_bone.matrix_basis) - np.asarray(current_saved_poses[current_pose_bone.name]))) > 1e-6:
                    raise ValueError('비대상 로컬 자세 변경')
                current_pose_bone.rotation_mode = 'QUATERNION'
                if current_pose_bone.name in current_previous_rotations and current_previous_rotations[current_pose_bone.name].dot(current_pose_bone.rotation_quaternion) < 0:
                    current_pose_bone.rotation_quaternion.negate()
                current_previous_rotations[current_pose_bone.name] = current_pose_bone.rotation_quaternion.copy()
                current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_number)
            current_rig_object.keyframe_insert('location', frame=current_frame_number)
            current_frame_records.append({'frame': current_frame_number, 'before': current_before_counts, 'after': current_after_counts, 'endpoint_error_m': current_endpoint_errors, 'bones': current_bone_records})
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
        for current_sample_index in range((current_frame_count - 1) * current_profile_record['audit_substeps'] + 1):
            current_sample_time = 1 + current_sample_index / current_profile_record['audit_substeps']
            current_progress_state.update(stage='saved-quarter-frame-audit', sample=current_sample_index)
            bpy.context.scene.frame_set(int(current_sample_time), subframe=current_sample_time % 1)
            current_rotation_steps = []
            for current_bone_name in current_target_names:
                current_bone_rotation = current_rig_object.pose.bones[current_bone_name].matrix.to_quaternion().normalized()
                if current_bone_name in current_previous_rotations:
                    current_rotation_steps.append(math.degrees(2 * math.acos(min(1, abs(current_previous_rotations[current_bone_name].dot(current_bone_rotation))))))
                current_previous_rotations[current_bone_name] = current_bone_rotation.copy()
            current_audit_records.append({'time': current_sample_time, 'intersections': count_surface_intersections(current_body_object, current_partition_faces), 'max_rotation_step_degrees': max(current_rotation_steps, default=0)})
        current_quality_warnings = ['혼합 경계·완전 내포·연속 시간 전체에 대한 충돌 보장은 없음', '원본 자세와 손목 방향은 충돌 제약으로 달라질 수 있음']
        if any(any(current_audit_record['intersections'].values()) for current_audit_record in current_audit_records):
            current_quality_warnings.append('저장 후 재생 표본에서 잔존 충돌 검출: 개선 방식은 채택됐으나 비관통은 보장하지 않음')
        current_summary_record = {'before_mean': {current_side_name: float(np.mean([current_frame_record['before'][current_side_name] for current_frame_record in current_frame_records])) for current_side_name in ('L', 'R')}, 'after_mean': {current_side_name: float(np.mean([current_frame_record['after'][current_side_name] for current_frame_record in current_frame_records])) for current_side_name in ('L', 'R')}, 'audit_colliding_samples': sum(any(current_audit_record['intersections'].values()) for current_audit_record in current_audit_records), 'max_quarter_frame_rotation_step_degrees': max(current_audit_record['max_rotation_step_degrees'] for current_audit_record in current_audit_records), 'max_wrist_target_error_m': max(current_frame_record['endpoint_error_m'][current_bone_name] for current_frame_record in current_frame_records for current_bone_name in ('wrist.L', 'wrist.R'))}
        current_result_record = {'status': 'completed', 'summary': current_summary_record, 'frames': current_frame_records, 'audit': current_audit_records, 'quality_warnings': current_quality_warnings, 'source_sha256': hashlib.sha256(source_blend_path.read_bytes()).hexdigest(), 'solver_sha256': hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/hy_motion/skin_collision_barrier.py').read_bytes()).hexdigest(), 'minimum_vertex_surface_clearance_m': current_profile_record['minimum_surface_clearance_m'], 'step_degrees': current_profile_record['angle_step_degrees'], 'refinements': current_profile_record['boundary_refinements'], 'order': current_target_names, 'collision_scope': '동일 부위 지배 가중치 삼각형의 팔/손 대 몸통/골반/다리. 팔 내부·어깨 접합 혼합 경계 제외', 'profile': current_profile_record, 'profile_sha256': hashlib.sha256(SKIN_BARRIER_PROFILE.read_bytes()).hexdigest(), 'approved_profile_applied': True, 'nonpenetration_guaranteed': False}
        current_result_record.update(blend_path='barrier/mannequin.blend', stage_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), surface_solver_sha256=hashlib.sha256((WORKFLOW_ROOT_DIRECTORY / 'generators/momask/body_proportion_retarget.py').read_bytes()).hexdigest())
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
