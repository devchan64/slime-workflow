"""등록된 참조의 정면·측면에서 얼굴 다섯 점을 만들고 머리 운동에 연결한다."""
import hashlib
from pathlib import Path

import numpy as np
import yaml

from generators.kimodo.contracts import KIMODO_CONFIG_ROOT, UniqueConfigLoader
from generators.kimodo.multiview_face_anchor_experiment import (
    apply_multiview_face_anchors, derive_multiview_face_anchors,
)

REFERENCE_FACE_POINT_NAMES = ('nose', 'right_eye', 'left_eye', 'right_ear', 'left_ear')
REFERENCE_BODY_POINT_NAMES = ('right_shoulder', 'left_shoulder', 'right_hip', 'left_hip')
REFERENCE_FACE_CONFIG_PATH = KIMODO_CONFIG_ROOT / 'reference-face-anchors.yaml'


def load_reference_face_template():
    """참조 원본과 교정 좌표를 해시로 결합하고 잘못된 설정을 거절한다."""
    current_config_bytes = REFERENCE_FACE_CONFIG_PATH.read_bytes()
    current_config_record = yaml.load(current_config_bytes, Loader=UniqueConfigLoader)
    current_required_fields = {'schema_version', 'reference_image', 'reference_sha256', 'source_generation', 'front_points', 'profile_points', 'limitations'}
    if not isinstance(current_config_record, dict) or set(current_config_record) != current_required_fields or current_config_record['schema_version'] != 1:
        raise ValueError('참조 얼굴 설정 계약 오류')
    current_workspace_root = Path(__file__).resolve().parents[2]
    current_reference_path = (current_workspace_root / current_config_record['reference_image']).resolve()
    if not current_reference_path.is_relative_to(current_workspace_root) or hashlib.sha256(current_reference_path.read_bytes()).hexdigest() != current_config_record['reference_sha256']:
        raise ValueError('참조 얼굴 원본 경로 또는 해시 불일치: 좌표를 다시 검수하세요.')
    for current_field_name, current_point_names in (('front_points', REFERENCE_FACE_POINT_NAMES + REFERENCE_BODY_POINT_NAMES), ('profile_points', ('nose', 'right_eye', 'right_ear'))):
        current_point_record = current_config_record[current_field_name]
        if not isinstance(current_point_record, dict) or set(current_point_record) != set(current_point_names):
            raise ValueError('참조 얼굴 관측점 필드 오류')
        current_point_array = np.asarray(list(current_point_record.values()), dtype=float)
        if current_point_array.shape != (len(current_point_names), 2) or not np.isfinite(current_point_array).all():
            raise ValueError('참조 얼굴 관측점 좌표 오류')
    current_front_points = current_config_record['front_points']
    current_profile_points = current_config_record['profile_points']
    current_shoulder_center = np.mean([current_front_points[current_name] for current_name in REFERENCE_BODY_POINT_NAMES[:2]], axis=0)
    current_hip_center = np.mean([current_front_points[current_name] for current_name in REFERENCE_BODY_POINT_NAMES[2:]], axis=0)
    current_torso_length = float(current_hip_center[1] - current_shoulder_center[1])
    current_nose_depth = current_profile_points['nose'][0] - current_profile_points['right_ear'][0]
    current_eye_depth = current_profile_points['right_eye'][0] - current_profile_points['right_ear'][0]
    if current_torso_length <= 0 or not 0 < current_eye_depth < current_nose_depth:
        raise ValueError('참조 얼굴 높이 또는 측면 깊이 오류')
    current_body_template = np.zeros((12, 3))
    for current_joint_offset, current_point_name in zip((0, 3, 6, 9), REFERENCE_BODY_POINT_NAMES):
        current_point_value = current_front_points[current_point_name]
        current_body_template[current_joint_offset] = [(current_point_value[0] - current_shoulder_center[0]) / current_torso_length, (current_hip_center[1] - current_point_value[1]) / current_torso_length, 0]
    current_face_template = []
    for current_point_name, current_depth_value in zip(REFERENCE_FACE_POINT_NAMES, (current_nose_depth, current_eye_depth, current_eye_depth, 0, 0)):
        current_point_value = current_front_points[current_point_name]
        current_face_template.append([(current_point_value[0] - current_shoulder_center[0]) / current_torso_length, (current_hip_center[1] - current_point_value[1]) / current_torso_length, current_depth_value / current_torso_length])
    current_template_record = {'body18_joint_indices': list(range(2, 14)), 'face_joint_indices': [0, 14, 15, 16, 17], 'body_joint_positions': current_body_template.tolist(), 'face_joint_positions': current_face_template}
    current_source_record = {'reference_sha256': current_config_record['reference_sha256'], 'config_sha256': hashlib.sha256(current_config_bytes).hexdigest(), 'reference_image': current_config_record['reference_image'], 'source_generation': current_config_record['source_generation'], 'limitations': current_config_record['limitations'], 'alignment_frame': 0}
    return current_template_record, current_source_record


def apply_registered_reference_face(current_body_positions, current_head_positions, current_head_rotations, current_ratio_record):
    """같은 참조에만 얼굴 교정을 적용한다. SOMA 눈 좌표는 덮어쓴다."""
    current_template_record, current_source_record = load_reference_face_template()
    if current_ratio_record.get('reference_image_sha256') != [current_source_record['reference_sha256']]:
        return current_body_positions, None
    current_local_offsets = derive_multiview_face_anchors(current_template_record, current_body_positions[0], current_head_positions[0], current_head_rotations[0])
    current_adjusted_positions = apply_multiview_face_anchors(current_body_positions, current_head_positions, current_head_rotations, current_local_offsets)
    current_source_record['local_offsets'] = current_local_offsets.tolist()
    return current_adjusted_positions, current_source_record
