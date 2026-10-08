"""원본 Head의 기준 자세 대비 회전을 ANNY 머리에 전달한다."""
import numpy as np
import hashlib
import io
import json
from pathlib import Path
from generators.hy_motion.hand_frame_transfer import validate_rotation_frame
from generators.hy_motion.contracts import SOURCE_BUNDLE_DIRECTORY
from generators.hy_motion.arm_retarget_data import load_arm_contract
from generators.hy_motion.rotation_channels import reconstruct_rotation_channels
from generators.hy_motion.preview import validate_motion_output

HEAD_TRANSFER_TOLERANCE = 1e-5
HEAD_SOURCE_DIRECTORY = SOURCE_BUNDLE_DIRECTORY / 'scripts/gradio/static/assets/dump_wooden'


def load_head_motion_rotations(source_motion_path, expected_frame_count, *, source_reference_directory=HEAD_SOURCE_DIRECTORY):
    """공식 NPZ·Wooden 기준을 검증하고 ANNY 좌표계의 Head 전역 회전을 반환한다."""
    if type(expected_frame_count) is not int or expected_frame_count < 1:
        raise ValueError('머리 전달 프레임 수는 양의 정수여야 합니다.')
    current_motion_bytes = Path(source_motion_path).read_bytes()
    with np.load(io.BytesIO(current_motion_bytes), allow_pickle=False) as current_motion_archive:
        if len(current_motion_archive.files) != len(set(current_motion_archive.files)):
            raise ValueError('원본 NPZ에 중복 필드가 있습니다.')
        if 'fps' not in current_motion_archive.files:
            raise ValueError('원본 모션 FPS가 없습니다.')
        current_frame_rate = current_motion_archive['fps']
        if current_frame_rate.shape != () or current_frame_rate.dtype.kind not in 'if' or float(current_frame_rate) != 30:
            raise ValueError('원본 모션은 30 FPS여야 합니다.')
        current_motion_arrays = {current_field_name: current_motion_archive[current_field_name] for current_field_name in current_motion_archive.files if current_field_name != 'fps'}
    validate_motion_output(current_motion_arrays, expected_frame_count)
    current_reference_path = Path(source_reference_directory)
    current_reference_bytes = {current_file_name: (current_reference_path / current_file_name).read_bytes() for current_file_name in ('joint_names.json', 'j_template.bin', 'kintree.bin')}
    current_joint_names = json.loads(current_reference_bytes['joint_names.json'])
    current_rest_points = np.frombuffer(current_reference_bytes['j_template.bin'], dtype='<f4')
    current_parent_indices = np.frombuffer(current_reference_bytes['kintree.bin'], dtype='<i4')
    if not isinstance(current_joint_names, list) or len(current_joint_names) != 52 or any(not isinstance(current_joint_name, str) for current_joint_name in current_joint_names) or len(set(current_joint_names)) != 52 or current_joint_names[15] != 'Head' or current_rest_points.size != 156 or current_parent_indices.shape != (52,):
        raise ValueError('Wooden 머리 회전 기준 계약 오류')
    current_local_rotations, current_global_rotations, current_fk_error = reconstruct_rotation_channels(current_motion_arrays['rot6d'], current_rest_points.reshape(52, 3)[:22], current_parent_indices[:22], current_motion_arrays['transl'], current_motion_arrays['world_joints'][:, :22])
    current_coordinate_basis = np.asarray(load_arm_contract()['source_to_target_basis'], dtype=float)
    current_head_rotations = current_coordinate_basis @ current_global_rotations[:, 15] @ current_coordinate_basis.T
    current_source_record = {'motion_sha256': hashlib.sha256(current_motion_bytes).hexdigest(), 'reference_hashes': {current_file_name: hashlib.sha256(current_file_bytes).hexdigest() for current_file_name, current_file_bytes in current_reference_bytes.items()}, 'source_joint': 'Head', 'target_bone': 'head', 'source_to_target_basis': current_coordinate_basis.tolist(), 'frames': expected_frame_count, 'fps': 30, 'fk_error_m': current_fk_error}
    return current_head_rotations, current_source_record


def transfer_head_rotation(source_head_rotation, target_bind_rotation):
    """공통 월드 축의 원본 회전 델타를 대상 기준 본 회전에 적용한다.

    원본·대상의 중립 머리 기준 방향이 대응한다는 리그 규약이며 임상적 시선축 보정은 아니다.
    """
    return validate_rotation_frame(source_head_rotation) @ validate_rotation_frame(target_bind_rotation)


def apply_head_rotation(current_rig_object, source_head_rotation):
    """머리 중심·부모 자세는 유지하고 head의 회전만 변경한다."""
    import bpy
    from mathutils import Matrix

    current_head_bone = current_rig_object.pose.bones['head']
    current_saved_matrix = current_head_bone.matrix_basis.copy()
    current_saved_center = current_head_bone.head.copy()
    current_bind_rotation = np.asarray(current_rig_object.data.bones['head'].matrix_local.to_quaternion().to_matrix())
    current_target_rotation = transfer_head_rotation(source_head_rotation, current_bind_rotation)
    try:
        current_head_bone.matrix = Matrix.Translation(current_saved_center) @ Matrix(current_target_rotation).to_4x4()
        current_head_bone.location = (0, 0, 0)
        current_head_bone.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        current_center_error = (current_head_bone.head - current_saved_center).length
        current_rotation_error = float(np.max(np.abs(np.asarray(current_head_bone.matrix.to_quaternion().to_matrix()) - current_target_rotation)))
        if current_center_error > HEAD_TRANSFER_TOLERANCE or current_rotation_error > HEAD_TRANSFER_TOLERANCE:
            raise ValueError('머리 중심 또는 원본 회전 전달 검증 실패')
        return {'head_center_error_m': current_center_error, 'head_rotation_matrix_error': current_rotation_error}
    except Exception:
        current_head_bone.matrix_basis = current_saved_matrix
        bpy.context.view_layer.update()
        raise
