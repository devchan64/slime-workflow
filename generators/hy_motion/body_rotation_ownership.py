"""원본 22관절을 공통 기준 자세의 ANNY 로컬 체인으로 전달한다."""
import numpy as np
from generators.hy_motion.shoulder_rotation_ownership import (
    SOURCE_TARGET_BASIS, build_aligned_arm_calibration, build_segment_reference,
    validate_owned_rotation,
)

BODY_OWNER_MAPPING = (
    ('Pelvis', 'root'), ('L_Hip', 'upperleg01.L'), ('R_Hip', 'upperleg01.R'),
    ('Spine1', 'spine05'), ('L_Knee', 'lowerleg01.L'), ('R_Knee', 'lowerleg01.R'),
    ('Spine2', 'spine03'), ('L_Ankle', 'foot.L'), ('R_Ankle', 'foot.R'),
    ('Spine3', 'spine01'), ('L_Foot', 'toe3-1.L'), ('R_Foot', 'toe3-1.R'),
    ('Neck', 'neck01'), ('L_Collar', 'clavicle.L'), ('R_Collar', 'clavicle.R'),
    ('Head', 'head'), ('L_Shoulder', 'upperarm01.L'), ('R_Shoulder', 'upperarm01.R'),
    ('L_Elbow', 'lowerarm01.L'), ('R_Elbow', 'lowerarm01.R'),
    ('L_Wrist', 'wrist.L'), ('R_Wrist', 'wrist.R'),
    # 원본 Foot은 발가락 묶음이다. 형제 기저에 한 번씩 전달하고 말단은 고정한다.
    ('L_Foot', 'toe1-1.L'), ('L_Foot', 'toe2-1.L'),
    ('L_Foot', 'toe4-1.L'), ('L_Foot', 'toe5-1.L'),
    ('R_Foot', 'toe1-1.R'), ('R_Foot', 'toe2-1.R'),
    ('R_Foot', 'toe4-1.R'), ('R_Foot', 'toe5-1.R'),
)
BODY_SEGMENT_MAPPING = (
    ('L_Hip', 'L_Knee', 'upperleg01.L', 'lowerleg01.L'),
    ('R_Hip', 'R_Knee', 'upperleg01.R', 'lowerleg01.R'),
    ('L_Knee', 'L_Ankle', 'lowerleg01.L', 'foot.L'),
    ('R_Knee', 'R_Ankle', 'lowerleg01.R', 'foot.R'),
    ('L_Ankle', 'L_Foot', 'foot.L', 'toe3-1.L'),
    ('R_Ankle', 'R_Foot', 'foot.R', 'toe3-1.R'),
)
MAXIMUM_WORLD_MATRIX_ERROR = 1e-5


def measure_body_rotation_errors(current_global_rotations, current_calibration_record, current_audit_records):
    """부모 체인 적용 후 세계 회전을 독립적인 원본 FK 목표와 비교한다."""
    current_global_rotations = np.asarray(current_global_rotations, dtype=float)
    if current_global_rotations.shape != (22, 3, 3):
        raise ValueError('세계 회전 감사는 원본 22관절이 필요합니다.')
    current_actual_lookup = {current_audit_record['bone']: current_audit_record for current_audit_record in current_audit_records}
    current_error_records = []
    for current_owner_record in current_calibration_record['owners']:
        current_source_rotation = validate_owned_rotation(current_global_rotations[current_owner_record['source_index']])
        current_expected_rotation = SOURCE_TARGET_BASIS @ current_source_rotation @ SOURCE_TARGET_BASIS.T @ np.asarray(current_owner_record['aligned_bind_rotation'])
        current_actual_rotation = validate_owned_rotation(current_actual_lookup[current_owner_record['owner_bone']]['world_rotation'])
        current_matrix_error = float(np.max(np.abs(current_actual_rotation - current_expected_rotation)))
        if current_matrix_error > MAXIMUM_WORLD_MATRIX_ERROR:
            raise ValueError(f"전신 FK 목표 회전 불일치: {current_owner_record['owner_bone']} / {current_matrix_error}")
        current_error_records.append({'bone': current_owner_record['owner_bone'], 'source_joint': current_owner_record['source_joint'], 'world_matrix_error': current_matrix_error})
    return current_error_records


def build_body_calibration(current_source_names, current_source_points, current_source_parents, current_target_matrices, current_target_parents):
    current_arm_calibration = build_aligned_arm_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents)
    current_source_lookup = dict(zip(current_source_names, np.asarray(current_source_points) @ SOURCE_TARGET_BASIS.T))
    current_target_lookup = {current_bone_name: np.asarray(current_bind_matrix, dtype=float) for current_bone_name, current_bind_matrix in current_target_matrices.items()}
    current_aligned_lookup = {current_owner_record['owner_bone']: np.asarray(current_owner_record['aligned_bind_rotation']) for current_owner_record in current_arm_calibration['owners']}
    current_torso_transform = np.asarray(current_arm_calibration['torso_anchor']['aligned_bind_rotation']) @ current_target_lookup['spine01'][:3, :3].T
    for current_bone_name in ('root', 'spine05', 'spine03', 'spine01', 'neck01', 'head'):
        current_aligned_lookup[current_bone_name] = current_torso_transform @ current_target_lookup[current_bone_name][:3, :3]
    current_source_lateral = current_source_lookup['R_Hip'] - current_source_lookup['L_Hip']
    current_target_lateral = current_target_lookup['upperleg01.R'][:3, 3] - current_target_lookup['upperleg01.L'][:3, 3]
    for current_source_name, current_source_end, current_owner_name, current_target_end in BODY_SEGMENT_MAPPING:
        current_source_frame = build_segment_reference(current_source_lookup[current_source_end] - current_source_lookup[current_source_name], current_source_lateral)
        current_target_frame = build_segment_reference(current_target_lookup[current_target_end][:3, 3] - current_target_lookup[current_owner_name][:3, 3], current_target_lateral)
        current_aligned_lookup[current_owner_name] = current_source_frame @ current_target_frame.T @ current_target_lookup[current_owner_name][:3, :3]
    for current_side_suffix in ('L', 'R'):
        current_foot_name = 'foot.' + current_side_suffix
        for current_toe_number in range(1, 6):
            current_toe_name = f'toe{current_toe_number}-1.' + current_side_suffix
            if current_target_parents[current_toe_name] != current_foot_name:
                raise ValueError('발가락 기저는 발목 소유 본의 직접 자식이어야 합니다.')
            current_aligned_lookup[current_toe_name] = current_aligned_lookup[current_foot_name] @ current_target_lookup[current_foot_name][:3, :3].T @ current_target_lookup[current_toe_name][:3, :3]
    current_owner_records = []
    current_source_mapping = dict(BODY_OWNER_MAPPING)
    for current_source_name, current_owner_name in BODY_OWNER_MAPPING:
        current_source_index = current_source_names.index(current_source_name)
        current_parent_index = int(current_source_parents[current_source_index])
        current_parent_name = current_source_mapping[current_source_names[current_parent_index]] if current_parent_index >= 0 else None
        current_path_cursor = current_target_parents[current_owner_name]
        while current_path_cursor is not None and current_path_cursor not in current_aligned_lookup:
            current_path_cursor = current_target_parents[current_path_cursor]
        if current_path_cursor != current_parent_name:
            raise ValueError('원본 부모와 대상 유효 회전 소유 부모가 다릅니다: ' + current_owner_name)
        current_parent_bind = current_target_lookup[current_parent_name][:3, :3] if current_parent_name else np.eye(3)
        current_parent_aligned = current_aligned_lookup[current_parent_name] if current_parent_name else np.eye(3)
        current_owner_records.append({'source_joint': current_source_name, 'source_index': current_source_index, 'owner_bone': current_owner_name, 'axis_transform': np.eye(3).tolist(), 'parent_aligned_inverse': validate_owned_rotation(current_parent_aligned.T).tolist(), 'effective_rest_inverse': validate_owned_rotation(current_target_lookup[current_owner_name][:3, :3].T @ current_parent_bind).tolist(), 'aligned_bind_rotation': validate_owned_rotation(current_aligned_lookup[current_owner_name]).tolist(), 'effective_parent_bone': current_parent_name})
    return {'schema_version': 1, 'status': 'experimental', 'profile_id': 'hymotion-anny-arm-aligned-v2', 'body_profile_id': 'hymotion-anny-body-local-v2', 'owners': current_owner_records, 'rest_intermediates': [current_bone_name for current_bone_name in current_target_lookup if current_bone_name not in current_aligned_lookup], 'compensation': False, 'limitations': ['개별 손가락·발가락 말단 회전은 원본에 없어 rest-local 유지', '몸통 공통 축 및 목·머리 해부학적 기준 검증 전']}
