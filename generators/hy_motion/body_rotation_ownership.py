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
)
BODY_SEGMENT_MAPPING = (
    ('L_Hip', 'L_Knee', 'upperleg01.L', 'lowerleg01.L'),
    ('R_Hip', 'R_Knee', 'upperleg01.R', 'lowerleg01.R'),
    ('L_Knee', 'L_Ankle', 'lowerleg01.L', 'foot.L'),
    ('R_Knee', 'R_Ankle', 'lowerleg01.R', 'foot.R'),
    ('L_Ankle', 'L_Foot', 'foot.L', 'toe3-1.L'),
    ('R_Ankle', 'R_Foot', 'foot.R', 'toe3-1.R'),
)


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
        current_toe_name = 'toe3-1.' + current_side_suffix
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
    return {'schema_version': 1, 'status': 'experimental', 'profile_id': 'hymotion-anny-arm-aligned-v2', 'body_profile_id': 'hymotion-anny-body-local-v1', 'owners': current_owner_records, 'rest_intermediates': [current_bone_name for current_bone_name in current_target_lookup if current_bone_name not in current_aligned_lookup], 'compensation': False, 'limitations': ['발가락 전체 분기 대신 세 번째 발가락 기저만 대응', '몸통 공통 축 및 목·머리 해부학적 기준 검증 전']}
