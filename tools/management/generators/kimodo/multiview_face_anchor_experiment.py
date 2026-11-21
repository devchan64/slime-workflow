"""검수용 공통 3D 얼굴 관절을 SOMA 머리에 연결한다."""
import hashlib
import json
import re
from pathlib import Path

import numpy as np

FACE_ANCHOR_JOINT_INDICES = (0, 14, 15, 16, 17)
FACE_ANCHOR_MINIMUM_LENGTH = 1e-8


def calculate_body_alignment_basis(current_shoulder_pair, current_hip_center):
    """어깨와 골반으로 직교 좌표계 및 어깨·골반 거리를 만든다."""
    current_shoulder_pair = np.asarray(current_shoulder_pair, dtype=float)
    current_hip_center = np.asarray(current_hip_center, dtype=float)
    if current_shoulder_pair.shape != (2, 3) or current_hip_center.shape != (3,) or not np.isfinite(current_shoulder_pair).all() or not np.isfinite(current_hip_center).all():
        raise ValueError('어깨·골반 좌표 형식 오류')
    current_side_vector = current_shoulder_pair[1] - current_shoulder_pair[0]
    current_shoulder_center = current_shoulder_pair.mean(axis=0)
    current_torso_vector = current_shoulder_center - current_hip_center
    current_side_length = np.linalg.norm(current_side_vector)
    current_torso_length = np.linalg.norm(current_torso_vector)
    if min(current_side_length, current_torso_length) <= FACE_ANCHOR_MINIMUM_LENGTH:
        raise ValueError('어깨 너비 또는 몸통 길이가 0입니다.')
    current_side_vector /= current_side_length
    current_up_vector = current_torso_vector - current_side_vector * np.dot(current_torso_vector, current_side_vector)
    current_up_length = np.linalg.norm(current_up_vector)
    if current_up_length <= FACE_ANCHOR_MINIMUM_LENGTH:
        raise ValueError('어깨와 몸통의 기준축이 평행합니다.')
    current_up_vector /= current_up_length
    current_forward_vector = np.cross(current_side_vector, current_up_vector)
    return np.column_stack((current_side_vector, current_up_vector, current_forward_vector)), current_shoulder_center, float(current_torso_length)


def derive_multiview_face_anchors(current_skeleton_record, current_body_positions, current_head_position, current_head_rotation):
    """첫 프레임 몸 기준으로 3D 얼굴점을 정렬해 Head 로컬 좌표를 계산한다."""
    current_body_positions = np.asarray(current_body_positions, dtype=float)
    current_head_position = np.asarray(current_head_position, dtype=float)
    current_head_rotation = np.asarray(current_head_rotation, dtype=float)
    current_reference_body = np.asarray(current_skeleton_record['body_joint_positions'], dtype=float)
    current_reference_face = np.asarray(current_skeleton_record['face_joint_positions'], dtype=float)
    if current_skeleton_record.get('body18_joint_indices') != list(range(2,14)) or current_skeleton_record.get('face_joint_indices') != list(FACE_ANCHOR_JOINT_INDICES):
        raise ValueError('참조 3D 몸·얼굴 관절 순서 오류')
    if current_body_positions.shape != (18, 3) or current_head_position.shape != (3,) or current_head_rotation.shape != (3, 3) or current_reference_body.shape != (12, 3) or current_reference_face.shape != (5, 3) or not all(np.isfinite(current_array).all() for current_array in (current_body_positions, current_head_position, current_head_rotation, current_reference_body, current_reference_face)):
        raise ValueError('SOMA 또는 참조 얼굴 앵커 좌표 형식 오류')
    if not np.allclose(current_head_rotation.T @ current_head_rotation, np.eye(3), atol=1e-5) or not np.isclose(np.linalg.det(current_head_rotation), 1, atol=1e-5):
        raise ValueError('SOMA 머리 회전행렬 오류')
    current_reference_basis, current_reference_center, current_reference_length = calculate_body_alignment_basis(current_reference_body[[0,3]], current_reference_body[[6,9]].mean(axis=0))
    current_output_basis, current_output_center, current_output_length = calculate_body_alignment_basis(current_body_positions[[2,5]], current_body_positions[[8,11]].mean(axis=0))
    current_transform = current_output_basis @ current_reference_basis.T * (current_output_length / current_reference_length)
    current_face_targets = current_output_center + (current_reference_face - current_reference_center) @ current_transform.T
    return (current_face_targets - current_head_position) @ current_head_rotation


def apply_multiview_face_anchors(current_body_positions, current_head_positions, current_head_rotations, current_local_offsets):
    """Head 로컬 앵커를 모든 프레임에 적용하고 나머지 관절을 보존한다."""
    current_body_positions = np.asarray(current_body_positions, dtype=float)
    current_head_positions = np.asarray(current_head_positions, dtype=float)
    current_head_rotations = np.asarray(current_head_rotations, dtype=float)
    current_local_offsets = np.asarray(current_local_offsets, dtype=float)
    current_frames = len(current_body_positions)
    if current_body_positions.shape != (current_frames, 18, 3) or current_head_positions.shape != (current_frames, 3) or current_head_rotations.shape != (current_frames, 3, 3) or current_local_offsets.shape != (5, 3) or not current_frames or not all(np.isfinite(current_array).all() for current_array in (current_body_positions, current_head_positions, current_head_rotations, current_local_offsets)):
        raise ValueError('프레임별 얼굴 앵커 좌표 형식 오류')
    if not np.allclose(np.swapaxes(current_head_rotations,1,2) @ current_head_rotations, np.eye(3), atol=1e-5) or not np.allclose(np.linalg.det(current_head_rotations),1,atol=1e-5):
        raise ValueError('프레임별 SOMA 머리 회전행렬 오류')
    current_adjusted_positions = current_body_positions.copy()
    current_adjusted_positions[:, list(FACE_ANCHOR_JOINT_INDICES)] = current_head_positions[:, None, :] + np.einsum('fij,kj->fki',current_head_rotations,current_local_offsets)
    return current_adjusted_positions


def calculate_face_anchor_binding(current_skeleton_record, current_joint_names):
    """참조 골격과 SOMA 리그가 교정 후 바뀌지 않았는지 확인할 식별자."""
    if not isinstance(current_skeleton_record, dict) or not isinstance(current_joint_names, list) or len(current_joint_names) != 77 or len(set(current_joint_names)) != 77 or any(not isinstance(current_name, str) for current_name in current_joint_names):
        raise ValueError('얼굴 앵커 참조 골격 또는 SOMA 리그 형식 오류')
    current_payload = {'reference_skeleton': current_skeleton_record, 'soma_joint_names': current_joint_names}
    return hashlib.sha256(json.dumps(current_payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def create_face_anchor_calibration(current_skeleton_record, current_joint_names, current_local_offsets, current_calibration_source=None):
    """명시적인 별도 검수용 얼굴 앵커와 골격의 대응을 만든다."""
    current_offsets = np.asarray(current_local_offsets, dtype=float)
    if current_offsets.shape != (5, 3) or not np.isfinite(current_offsets).all():
        raise ValueError('얼굴 앵커 로컬 좌표 형식 오류')
    current_record = {'schema': 'kimodo-face-anchor-calibration-v1', 'binding_sha256': calculate_face_anchor_binding(current_skeleton_record, current_joint_names), 'local_offsets': current_offsets.tolist()}
    if current_calibration_source is not None:
        validate_face_calibration_source(current_calibration_source)
        current_record['schema'] = 'kimodo-face-anchor-calibration-v2'
        current_record['source'] = current_calibration_source
    return current_record


def validate_face_calibration_format(current_calibration_record, current_require_source=False):
    """앵커 입력 형식과 선택적 출처를 검증한다."""
    if not isinstance(current_calibration_record, dict):
        raise ValueError('얼굴 앵커 교정 계약 오류')
    current_schema = current_calibration_record.get('schema')
    if current_schema == 'kimodo-face-anchor-calibration-v1' and set(current_calibration_record) == {'schema','binding_sha256','local_offsets'} and not current_require_source:
        pass
    elif current_schema == 'kimodo-face-anchor-calibration-v2' and set(current_calibration_record) == {'schema','binding_sha256','local_offsets','source'}:
        validate_face_calibration_source(current_calibration_record['source'])
    else:
        raise ValueError('얼굴 앵커 교정 계약 오류')
    if not isinstance(current_calibration_record['binding_sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',current_calibration_record['binding_sha256']):
        raise ValueError('얼굴 앵커 결합 해시 오류')
    try:
        current_offsets = np.asarray(current_calibration_record['local_offsets'], dtype=float)
    except (TypeError,ValueError) as current_error:
        raise ValueError('얼굴 앵커 로컬 좌표 형식 오류') from current_error
    if current_offsets.shape != (5, 3) or not np.isfinite(current_offsets).all():
        raise ValueError('얼굴 앵커 로컬 좌표 형식 오류')
    return current_offsets


def validate_face_anchor_calibration(current_calibration_record, current_skeleton_record, current_joint_names):
    """다른 참조 또는 리그에서 얼굴 앵커를 잘못 사용하는 것을 거부한다."""
    current_offsets = validate_face_calibration_format(current_calibration_record)
    if current_calibration_record['binding_sha256'] != calculate_face_anchor_binding(current_skeleton_record, current_joint_names):
        raise ValueError('얼굴 앵커의 참조 골격 또는 SOMA 리그가 일치하지 않습니다.')
    return current_offsets


def validate_face_calibration_source(current_source_record):
    """얼굴 교정에 사용한 원본 프레임과 파일의 해시를 확인한다."""
    if not isinstance(current_source_record,dict) or set(current_source_record)!={'frame','motion_sha256','skeleton_sha256','reference_sha256','render_sha256','head_anchors_sha256'} or type(current_source_record['frame']) is not int or current_source_record['frame']<0:
        raise ValueError('얼굴 앵커 교정 출처 형식 오류')
    if any(not isinstance(current_source_record[current_name],str) or not re.fullmatch(r'[0-9a-f]{64}',current_source_record[current_name]) for current_name in ('motion_sha256','skeleton_sha256','reference_sha256','render_sha256','head_anchors_sha256')):
        raise ValueError('얼굴 앵커 교정 출처 해시 오류')


def create_face_calibration_from_attempt(current_attempt_root, current_frame_index):
    """명시한 SOMA 프레임과 검수 참조로 얼굴 앵커 및 출처를 만든다."""
    from generators.kimodo.soma_pose import SOMA_BODY_JOINT_NAMES
    from generators.kimodo.reference_proportions import apply_reference_proportions
    from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader
    import yaml
    current_attempt_root=Path(current_attempt_root).resolve()
    if type(current_frame_index) is not int or current_frame_index<0:
        raise ValueError('얼굴 앵커 교정 프레임은 0 이상의 정수여야 합니다.')
    current_render_path=current_attempt_root/'soma-render.json'
    current_skeleton_path=current_attempt_root/'skeleton.json'
    current_reference_path=current_attempt_root/'reference-proportions.json'
    current_render=json.loads(current_render_path.read_text())
    current_skeleton=json.loads(current_skeleton_path.read_text())
    current_reference=json.loads(current_reference_path.read_text())
    if 'weighted_body_face_candidate' not in current_reference:
        raise ValueError('얼굴 앵커 교정에는 검수 3D 골격 비율이 필요합니다.')
    current_motion_path=(current_attempt_root/current_render['source']).resolve()
    if current_motion_path.parent!=current_attempt_root or not current_motion_path.is_file():
        raise ValueError('교정 모션 경로가 현재 시도 범위를 벗어났거나 존재하지 않습니다.')
    current_names=current_skeleton['joint_names']
    with np.load(current_motion_path,allow_pickle=False) as current_motion:
        current_joints=current_motion['posed_joints']
        current_rotations=current_motion['global_rot_mats']
    if current_frame_index>=len(current_joints):
        raise ValueError('얼굴 앵커 교정 프레임이 모션 범위를 벗어났습니다.')
    current_body=np.zeros((len(current_joints),18,3))
    for current_index,current_name in enumerate(SOMA_BODY_JOINT_NAMES):
        if current_name:
            current_body[:,current_index]=current_joints[:,current_names.index(current_name)]
    current_head=current_names.index('Head')
    current_anchor_path=KIMODO_CONFIG_ROOT/'head-anchors.yaml'
    current_anchors=yaml.load(current_anchor_path.read_text(),Loader=UniqueConfigLoader)
    for current_index,current_name in ((0,'nose'),(16,'right_ear'),(17,'left_ear')):
        current_offset=np.asarray(current_anchors['anchors'][current_name]['local_offset'],dtype=float)
        current_body[:,current_index]=current_joints[:,current_head]+np.einsum('nij,j->ni',current_rotations[:,current_head],current_offset)
    current_body[:,1]=current_body[:,[2,5]].mean(axis=1)
    current_body=apply_reference_proportions(current_body,current_reference)
    current_offsets=derive_multiview_face_anchors(current_reference['weighted_body_face_candidate'],current_body[current_frame_index],current_joints[current_frame_index,current_head],current_rotations[current_frame_index,current_head])
    current_source={'frame':current_frame_index,**{current_name:hashlib.sha256(current_path.read_bytes()).hexdigest() for current_name,current_path in (('motion_sha256',current_motion_path),('skeleton_sha256',current_skeleton_path),('reference_sha256',current_reference_path),('render_sha256',current_render_path),('head_anchors_sha256',current_anchor_path))}}
    return create_face_anchor_calibration(current_reference['weighted_body_face_candidate'],current_names,current_offsets,current_source)


if __name__=='__main__':
    import argparse
    current_parser=argparse.ArgumentParser(description='검수 3D 골격과 SOMA 프레임으로 얼굴 앵커 교정')
    current_parser.add_argument('attempt',type=Path)
    current_parser.add_argument('frame',type=int,help='0부터 시작하는 원본 프레임')
    current_parser.add_argument('output',type=Path)
    current_arguments=current_parser.parse_args()
    if current_arguments.output.exists():
        raise ValueError('기존 얼굴 앵커 교정 파일을 덮어쓰지 않습니다.')
    current_result=create_face_calibration_from_attempt(current_arguments.attempt,current_arguments.frame)
    current_arguments.output.write_text(json.dumps(current_result,ensure_ascii=False,indent=2))
    print(f'얼굴 앵커 교정 저장: {current_arguments.output}',flush=True)
