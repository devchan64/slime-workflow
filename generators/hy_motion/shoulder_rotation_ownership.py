"""쇄골·상완 로컬 회전 소유권. 운영 채택 전 단일 관절 검증용 구현."""
import numpy as np

SOURCE_TARGET_BASIS = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
SHOULDER_ROTATION_OWNERS = (
    ('L_Collar', 'L_Shoulder', 'clavicle.L', 'upperarm01.L'),
    ('R_Collar', 'R_Shoulder', 'clavicle.R', 'upperarm01.R'),
    ('L_Shoulder', 'L_Elbow', 'upperarm01.L', 'lowerarm01.L'),
    ('R_Shoulder', 'R_Elbow', 'upperarm01.R', 'lowerarm01.R'),
)
SHOULDER_REST_INTERMEDIATES = ('shoulder01.L', 'shoulder01.R', 'upperarm02.L', 'upperarm02.R')
ROTATION_MATRIX_TOLERANCE = 1e-5
ARM_ROTATION_EXTENSION = (
    ('L_Elbow', 'L_Wrist', 'lowerarm01.L', 'wrist.L'),
    ('R_Elbow', 'R_Wrist', 'lowerarm01.R', 'wrist.R'),
)


def validate_owned_rotation(current_rotation_matrix):
    current_rotation_matrix = np.asarray(current_rotation_matrix, dtype=float)
    if current_rotation_matrix.shape != (3, 3) or not np.isfinite(current_rotation_matrix).all() or not np.allclose(current_rotation_matrix.T @ current_rotation_matrix, np.eye(3), atol=ROTATION_MATRIX_TOLERANCE, rtol=0) or abs(np.linalg.det(current_rotation_matrix) - 1) > ROTATION_MATRIX_TOLERANCE:
        raise ValueError('회전 소유권 입력은 오른손 직교 회전이어야 합니다.')
    return current_rotation_matrix


def build_segment_reference(current_segment_vector, current_torso_vector):
    current_segment_vector = np.asarray(current_segment_vector, dtype=float)
    current_torso_vector = np.asarray(current_torso_vector, dtype=float)
    if current_segment_vector.shape != (3,) or current_torso_vector.shape != (3,) or not np.isfinite([current_segment_vector, current_torso_vector]).all():
        raise ValueError('기준 축은 유한한 XYZ 벡터여야 합니다.')
    current_segment_length = np.linalg.norm(current_segment_vector)
    if current_segment_length < ROTATION_MATRIX_TOLERANCE:
        raise ValueError('쇄골·상완 기준 길이가 퇴화했습니다.')
    current_primary_axis = current_segment_vector / current_segment_length
    current_secondary_axis = current_torso_vector - current_primary_axis * np.dot(current_primary_axis, current_torso_vector)
    if np.linalg.norm(current_secondary_axis) < ROTATION_MATRIX_TOLERANCE:
        raise ValueError('몸통 보조 축과 세그먼트가 평행합니다.')
    current_secondary_axis /= np.linalg.norm(current_secondary_axis)
    return np.column_stack((current_primary_axis, current_secondary_axis, np.cross(current_primary_axis, current_secondary_axis)))


def build_shoulder_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents):
    """모션이 아닌 bind 기준점으로만 좌우 독립 축 대응을 계산한다."""
    current_source_points = np.asarray(current_source_points, dtype=float)
    if current_source_points.shape != (len(current_source_names), 3) or len(set(current_source_names)) != len(current_source_names):
        raise ValueError('원본 기준 관절 이름·위치 계약 오류')
    current_source_lookup = dict(zip(current_source_names, current_source_points @ SOURCE_TARGET_BASIS.T))
    current_target_lookup = {current_bone_name: np.asarray(current_bind_matrix, dtype=float) for current_bone_name, current_bind_matrix in current_target_matrices.items()}
    for current_bind_matrix in current_target_lookup.values():
        if current_bind_matrix.shape != (4, 4) or not np.isfinite(current_bind_matrix).all():
            raise ValueError('대상 bind 행렬 오류')
        validate_owned_rotation(current_bind_matrix[:3, :3])
    for current_side_suffix in ('L', 'R'):
        current_chain_names = [current_prefix_name + '.' + current_side_suffix for current_prefix_name in ('clavicle', 'shoulder01', 'upperarm01', 'upperarm02', 'lowerarm01')]
        for current_parent_name, current_child_name in zip(current_chain_names, current_chain_names[1:]):
            if current_target_parents[current_child_name] != current_parent_name:
                raise ValueError('쇄골·어깨 중간 본 부모 관계 불일치')
    current_source_torso = current_source_lookup['Spine3'] - current_source_lookup['Pelvis']
    current_target_torso = current_target_lookup['neck01'][:3, 3] - current_target_lookup['root'][:3, 3]
    current_calibration_records = []
    for current_source_name, current_source_end, current_owner_name, current_target_end in SHOULDER_ROTATION_OWNERS:
        current_source_frame = build_segment_reference(current_source_lookup[current_source_end] - current_source_lookup[current_source_name], current_source_torso)
        current_target_frame = build_segment_reference(current_target_lookup[current_target_end][:3, 3] - current_target_lookup[current_owner_name][:3, 3], current_target_torso)
        current_axis_transform = current_target_lookup[current_owner_name][:3, :3].T @ current_target_frame @ current_source_frame.T @ SOURCE_TARGET_BASIS
        validate_owned_rotation(current_axis_transform)
        current_calibration_records.append({'source_joint': current_source_name, 'source_index': current_source_names.index(current_source_name), 'owner_bone': current_owner_name, 'axis_transform': current_axis_transform.tolist()})
    return {'schema_version': 1, 'status': 'experimental', 'owners': current_calibration_records, 'rest_intermediates': list(SHOULDER_REST_INTERMEDIATES), 'compensation': False, 'axis_policy': 'bind 세그먼트와 몸통 축; 해부학적 축 검증 전'}


def calculate_shoulder_rotations(current_local_rotations, current_calibration_record):
    """대상 bind-local 증분만 반환한다. 자식 세계 방향 복원은 하지 않는다."""
    current_local_rotations = np.asarray(current_local_rotations, dtype=float)
    if current_local_rotations.shape != (22, 3, 3):
        raise ValueError('원본 로컬 회전은 [22,3,3]이어야 합니다.')
    for current_rotation_matrix in current_local_rotations:
        validate_owned_rotation(current_rotation_matrix)
    current_output_rotations = {current_bone_name: np.eye(3) for current_bone_name in current_calibration_record['rest_intermediates']}
    for current_owner_record in current_calibration_record['owners']:
        current_axis_transform = validate_owned_rotation(current_owner_record['axis_transform'])
        if current_calibration_record.get('profile_id') == 'hymotion-anny-arm-aligned-v2':
            current_parent_inverse = validate_owned_rotation(current_owner_record['parent_aligned_inverse'])
            current_rest_inverse = validate_owned_rotation(current_owner_record['effective_rest_inverse'])
            current_aligned_rotation = validate_owned_rotation(current_owner_record['aligned_bind_rotation'])
            current_source_rotation = SOURCE_TARGET_BASIS @ current_local_rotations[current_owner_record['source_index']] @ SOURCE_TARGET_BASIS.T
            current_output_rotations[current_owner_record['owner_bone']] = current_rest_inverse @ current_parent_inverse @ current_source_rotation @ current_aligned_rotation
        else:
            current_output_rotations[current_owner_record['owner_bone']] = current_axis_transform @ current_local_rotations[current_owner_record['source_index']] @ current_axis_transform.T
    return current_output_rotations


def build_arm_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents):
    """쇄골부터 손까지 동일한 로컬 증분 계약으로 확장한다."""
    from generators.hy_motion.hand_frame_transfer import build_hand_frame
    current_calibration_record = build_shoulder_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents)
    current_source_lookup = dict(zip(current_source_names, np.asarray(current_source_points) @ SOURCE_TARGET_BASIS.T))
    current_target_lookup = {current_bone_name: np.asarray(current_bind_matrix, dtype=float) for current_bone_name, current_bind_matrix in current_target_matrices.items()}
    current_source_torso = current_source_lookup['Spine3'] - current_source_lookup['Pelvis']
    current_target_torso = current_target_lookup['neck01'][:3, 3] - current_target_lookup['root'][:3, 3]
    for current_source_name, current_source_end, current_owner_name, current_target_end in ARM_ROTATION_EXTENSION:
        current_source_frame = build_segment_reference(current_source_lookup[current_source_end] - current_source_lookup[current_source_name], current_source_torso)
        current_target_frame = build_segment_reference(current_target_lookup[current_target_end][:3, 3] - current_target_lookup[current_owner_name][:3, 3], current_target_torso)
        current_axis_transform = current_target_lookup[current_owner_name][:3, :3].T @ current_target_frame @ current_source_frame.T @ SOURCE_TARGET_BASIS
        current_calibration_record['owners'].append({'source_joint': current_source_name, 'source_index': current_source_names.index(current_source_name), 'owner_bone': current_owner_name, 'axis_transform': validate_owned_rotation(current_axis_transform).tolist()})
    for current_side_suffix in ('L', 'R'):
        if current_target_parents['lowerarm02.' + current_side_suffix] != 'lowerarm01.' + current_side_suffix or current_target_parents['wrist.' + current_side_suffix] != 'lowerarm02.' + current_side_suffix:
            raise ValueError('전완·손 중간 본 부모 관계 불일치')
        current_calibration_record['rest_intermediates'].append('lowerarm02.' + current_side_suffix)
        current_source_name = current_side_suffix + '_Wrist'
        current_owner_name = 'wrist.' + current_side_suffix
        current_source_frame = build_hand_frame([current_source_lookup[current_side_suffix + '_' + current_joint_suffix] for current_joint_suffix in ('Wrist', 'Middle1', 'Index1', 'Pinky1')])
        current_target_frame = build_hand_frame([current_target_lookup[current_bone_prefix + '.' + current_side_suffix][:3, 3] for current_bone_prefix in ('wrist', 'finger3-1', 'finger2-1', 'finger5-1')])
        current_axis_transform = current_target_lookup[current_owner_name][:3, :3].T @ current_target_frame @ current_source_frame.T @ SOURCE_TARGET_BASIS
        current_calibration_record['owners'].append({'source_joint': current_source_name, 'source_index': current_source_names.index(current_source_name), 'owner_bone': current_owner_name, 'axis_transform': validate_owned_rotation(current_axis_transform).tolist()})
    current_calibration_record['profile_id'] = 'hymotion-anny-arm-local-v1'
    return current_calibration_record


def build_aligned_arm_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents):
    """공통 기준 자세의 고정 오프셋을 로컬 전달에 포함한다. 현재 pose는 읽지 않는다."""
    current_calibration_record = build_arm_calibration(current_source_names, current_source_points, current_target_matrices, current_target_parents)
    current_source_lookup = dict(zip(current_source_names, np.asarray(current_source_points) @ SOURCE_TARGET_BASIS.T))
    current_target_lookup = {current_bone_name: np.asarray(current_bind_matrix, dtype=float) for current_bone_name, current_bind_matrix in current_target_matrices.items()}
    current_source_frame = build_segment_reference(current_source_lookup['Spine3'] - current_source_lookup['Pelvis'], current_source_lookup['R_Shoulder'] - current_source_lookup['L_Shoulder'])
    current_target_frame = build_segment_reference(current_target_lookup['neck01'][:3, 3] - current_target_lookup['root'][:3, 3], current_target_lookup['upperarm01.R'][:3, 3] - current_target_lookup['upperarm01.L'][:3, 3])
    current_torso_alignment = current_source_frame @ current_target_frame.T @ current_target_lookup['spine01'][:3, :3]
    current_owner_lookup = {current_owner_record['owner_bone']: current_owner_record for current_owner_record in current_calibration_record['owners']}
    for current_side_suffix in ('L', 'R'):
        if current_target_parents['clavicle.' + current_side_suffix] != 'spine01':
            raise ValueError('쇄골 부모는 검증된 spine01이어야 합니다.')
        current_previous_name = 'spine01'
        current_previous_alignment = current_torso_alignment
        for current_bone_prefix in ('clavicle', 'upperarm01', 'lowerarm01', 'wrist'):
            current_owner_name = current_bone_prefix + '.' + current_side_suffix
            current_owner_record = current_owner_lookup[current_owner_name]
            current_aligned_rotation = SOURCE_TARGET_BASIS @ np.asarray(current_owner_record['axis_transform']).T
            current_rest_inverse = current_target_lookup[current_owner_name][:3, :3].T @ current_target_lookup[current_previous_name][:3, :3]
            current_owner_record.update(parent_aligned_inverse=validate_owned_rotation(current_previous_alignment.T).tolist(), effective_rest_inverse=validate_owned_rotation(current_rest_inverse).tolist(), aligned_bind_rotation=validate_owned_rotation(current_aligned_rotation).tolist(), effective_parent_bone=current_previous_name)
            current_previous_alignment = current_aligned_rotation
            current_previous_name = current_owner_name
    current_calibration_record['profile_id'] = 'hymotion-anny-arm-aligned-v2'
    current_calibration_record['torso_anchor'] = {'source_joint': 'Spine3', 'source_index': current_source_names.index('Spine3'), 'target_bone': 'spine01', 'aligned_bind_rotation': current_torso_alignment.tolist()}
    current_calibration_record['reference_policy'] = '원본 항등 회전은 ANNY bind가 아니라 고정 공통 기준 자세로 대응한다. 중간 본은 bind-local 유지. 충돌 후 재계산 없음.'
    return current_calibration_record


def apply_shoulder_rotations(current_rig_object, current_local_rotations, current_calibration_record):
    """Blender 로컬 회전만 설정한다. 하위 관절의 기존 로컬 값은 보존한다."""
    import bpy
    from mathutils import Matrix
    current_output_rotations = calculate_shoulder_rotations(current_local_rotations, current_calibration_record)
    current_previous_poses = {current_pose_bone.name: np.asarray(current_pose_bone.matrix_basis).copy() for current_pose_bone in current_rig_object.pose.bones}
    for current_bone_name, current_rotation_matrix in current_output_rotations.items():
        current_pose_bone = current_rig_object.pose.bones[current_bone_name]
        current_pose_bone.matrix_basis = Matrix(current_rotation_matrix).to_4x4()
        # float32 bind 행렬의 미세 비직교성이 본 스케일로 저장되지 않도록 분리한다.
        current_pose_bone.location = (0, 0, 0)
        current_pose_bone.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    current_audit_records = []
    for current_pose_bone in current_rig_object.pose.bones:
        current_actual_matrix = np.asarray(current_pose_bone.matrix_basis)
        if current_pose_bone.name not in current_output_rotations:
            if not np.allclose(current_actual_matrix, current_previous_poses[current_pose_bone.name], atol=ROTATION_MATRIX_TOLERANCE, rtol=0):
                raise ValueError('쇄골·어깨 전달 중 비대상 본 로컬 회전 변경')
            continue
        current_error_value = float(np.max(np.abs(current_actual_matrix[:3, :3] - current_output_rotations[current_pose_bone.name])))
        if current_error_value > ROTATION_MATRIX_TOLERANCE:
            raise ValueError('쇄골·어깨 로컬 회전 적용 불일치')
        current_audit_records.append({'bone': current_pose_bone.name, 'local_rotation': current_actual_matrix[:3, :3].tolist(), 'matrix_error': current_error_value, 'world_head': list(current_pose_bone.head), 'world_rotation': np.asarray(current_pose_bone.matrix.to_quaternion().to_matrix()).tolist()})
    return current_audit_records
