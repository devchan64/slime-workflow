"""SOMA 목·머리의 전역 회전을 ANNY 기준 축으로 전달한다."""
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml
from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader


def prepare_neck_rotation_channels(current_attempt_root):
    current_config_path = KIMODO_CONFIG_ROOT / 'anny-rotation.yaml'
    current_config_record = yaml.load(current_config_path.read_text(), Loader=UniqueConfigLoader)
    if set(current_config_record) != {'schema_version', 'coordinate_matrix', 'bone_mapping', 'neck_chain_alignment'} or current_config_record['schema_version'] != 1:
        raise ValueError('목·머리 회전 설정 계약 오류')
    if current_config_record['bone_mapping'] != {'neck01': 'Neck1', 'neck02': 'Neck2', 'neck03': 'Neck2', 'head': 'Head'}:
        raise ValueError('목·머리 고정 대응 오류')
    if current_config_record['neck_chain_alignment'] != {'source_start':'Neck1','source_end':'Head','target_start':'neck01','target_end':'head','method':'rigid_chain_direction'}:
        raise ValueError('목 체인 정렬 계약 오류')
    current_coordinate_matrix = np.asarray(current_config_record['coordinate_matrix'], dtype=float)
    if not np.array_equal(current_coordinate_matrix, [[1,0,0],[0,0,-1],[0,1,0]]):
        raise ValueError('목·머리 좌표 변환 오류')
    current_skeleton_record = json.loads((current_attempt_root / 'skeleton.json').read_text())
    if current_skeleton_record['skeleton'] != 'somaskel77':
        raise ValueError('SOMA77 회전만 지원합니다.')
    with np.load(current_attempt_root / 'motion.npz', allow_pickle=False) as current_motion_archive:
        current_rotation_values = current_motion_archive['global_rot_mats']
        current_frame_count = len(current_motion_archive['posed_joints'])
    if current_rotation_values.shape != (current_frame_count,77,3,3) or not np.isfinite(current_rotation_values).all():
        raise ValueError('SOMA 전역 회전 크기·유한값 오류')
    if not np.allclose(current_rotation_values @ current_rotation_values.swapaxes(-1,-2), np.eye(3), atol=1e-4) or not np.allclose(np.linalg.det(current_rotation_values), 1, atol=1e-4):
        raise ValueError('SOMA 전역 회전은 정규 직교 회전이어야 합니다.')
    current_bone_channels = {
        current_target_name: current_coordinate_matrix @ current_rotation_values[:,current_skeleton_record['joint_names'].index(current_source_name)] @ current_coordinate_matrix.T
        for current_target_name,current_source_name in current_config_record['bone_mapping'].items()
    }
    return current_bone_channels, current_config_path


def apply_neck_rotation_channels(current_retarget_root, current_stage_namespace):
    import bpy
    from mathutils import Matrix, Vector
    current_bone_channels,current_config_path = prepare_neck_rotation_channels(current_retarget_root.parent)
    current_rig_object = current_stage_namespace['rig_object_value']
    current_scene_object = bpy.context.scene
    current_rotation_errors = []
    current_direction_errors = []
    current_length_errors = []
    current_skeleton_record = json.loads((current_retarget_root.parent/'skeleton.json').read_text())
    with np.load(current_retarget_root.parent/'motion.npz', allow_pickle=False) as current_motion_archive:
        current_joint_positions = current_motion_archive['posed_joints']
    current_neck_index = current_skeleton_record['joint_names'].index('Neck1')
    current_head_index = current_skeleton_record['joint_names'].index('Head')
    current_source_vectors = current_joint_positions[:,current_head_index] - current_joint_positions[:,current_neck_index]
    current_coordinate_matrix = np.asarray([[1,0,0],[0,0,-1],[0,1,0]])
    current_source_vectors = current_source_vectors @ current_coordinate_matrix.T
    if not np.isfinite(current_source_vectors).all() or np.any(np.linalg.norm(current_source_vectors,axis=1)<1e-8):
        raise ValueError('목 체인 원본 방향이 유효하지 않습니다.')
    previous_bone_quaternions = {}
    for current_frame_index in range(len(current_bone_channels['head'])):
        current_scene_object.frame_set(current_frame_index + 1)
        for current_bone_name,current_rotation_values in current_bone_channels.items():
            current_pose_bone = current_rig_object.pose.bones[current_bone_name]
            current_target_matrix = Matrix(current_rotation_values[current_frame_index].tolist()) @ current_rig_object.data.bones[current_bone_name].matrix_local.to_3x3()
            current_pose_bone.matrix = Matrix.Translation(current_pose_bone.head) @ current_target_matrix.to_4x4()
            current_pose_bone.location = (0,0,0)
            current_pose_bone.scale = (1,1,1)
            bpy.context.view_layer.update()
        # 목 체인을 통째로 회전하여 길이·내부 관절 자세를 보존하고 머리 위치 방향을 맞춘다.
        current_neck_bone = current_rig_object.pose.bones['neck01']
        current_head_bone = current_rig_object.pose.bones['head']
        current_before_vector = current_head_bone.head - current_neck_bone.head
        current_source_vector = Vector(current_source_vectors[current_frame_index].tolist())
        current_alignment_rotation = current_before_vector.rotation_difference(current_source_vector)
        current_neck_bone.matrix = Matrix.Translation(current_neck_bone.head) @ (current_alignment_rotation.to_matrix() @ current_neck_bone.matrix.to_3x3()).to_4x4()
        current_neck_bone.location = (0,0,0)
        current_neck_bone.scale = (1,1,1)
        bpy.context.view_layer.update()
        current_after_vector = current_head_bone.head - current_neck_bone.head
        current_direction_errors.append(float(current_after_vector.angle(current_source_vector)))
        current_length_errors.append(abs(current_after_vector.length-current_before_vector.length))
        # 체인 정렬과 독립적으로 원본 머리 전역 회전은 유지한다.
        current_head_matrix = Matrix(current_bone_channels['head'][current_frame_index].tolist()) @ current_rig_object.data.bones['head'].matrix_local.to_3x3()
        current_head_bone.matrix = Matrix.Translation(current_head_bone.head) @ current_head_matrix.to_4x4()
        current_head_bone.location = (0,0,0)
        current_head_bone.scale = (1,1,1)
        bpy.context.view_layer.update()
        current_rotation_errors.append(float(current_head_bone.matrix.to_quaternion().rotation_difference(current_head_matrix.to_quaternion()).angle))
        for current_bone_name in current_bone_channels:
            current_pose_bone = current_rig_object.pose.bones[current_bone_name]
            if current_bone_name in previous_bone_quaternions and previous_bone_quaternions[current_bone_name].dot(current_pose_bone.rotation_quaternion) < 0:
                current_pose_bone.rotation_quaternion.negate()
            previous_bone_quaternions[current_bone_name] = current_pose_bone.rotation_quaternion.copy()
            current_pose_bone.keyframe_insert('rotation_quaternion', frame=current_frame_index + 1)
    current_scene_object.frame_set(1)
    bpy.ops.export_scene.gltf(filepath=str(current_retarget_root/'mannequin.glb'), use_selection=True, export_animations=True, export_all_influences=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(current_retarget_root/'mannequin.blend'))
    current_metrics_path = current_retarget_root/'review-metrics.json'
    current_metrics_record = json.loads(current_metrics_path.read_text())
    current_metrics_record['position_pass_diagnostics_scope'] = '위치 기반 1차 처리 측정. 최종 목·머리 회전 오차는 neck_rotation에서 별도 제공.'
    current_metrics_record['retarget_method'] += '+soma-neck-chain-v2'
    current_metrics_record['neck_rotation'] = {'bones':list(current_bone_channels), 'rotation_error_scope':'head only; neck aligned to source endpoint direction', 'chain_direction_max_error_degrees':float(np.degrees(max(current_direction_errors))), 'chain_length_max_change':max(current_length_errors), 'max_error_degrees':float(np.degrees(max(current_rotation_errors))), 'config_sha256':hashlib.sha256(current_config_path.read_bytes()).hexdigest()}
    current_metrics_path.write_text(json.dumps(current_metrics_record,ensure_ascii=False,indent=2))
    (current_retarget_root/'rotation-profile.yaml').write_bytes(current_config_path.read_bytes())
