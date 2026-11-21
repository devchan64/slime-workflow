"""공통 3D 추정에서 검수용 신체 비율 후보를 만든다."""
import copy
import json
from pathlib import Path

import numpy as np

from generators.kimodo.multiview_reference_experiment import MULTIVIEW_BODY_JOINTS
from generators.kimodo.reference_proportions import REFERENCE_RATIO_SCHEMA, REFERENCE_SEGMENT_GROUPS

CANDIDATE_FACE_JOINT_INDICES = (0, 14, 15, 16, 17)
CANDIDATE_MINIMUM_TORSO_LENGTH = 1e-8


def build_multiview_ratio_candidate(current_ratio_record, current_skeleton_record):
    """기존 참조 원본을 보존하고 실험용 3D 비율과 코 축만 교체한다."""
    if not isinstance(current_ratio_record, dict) or current_ratio_record.get('schema') != REFERENCE_RATIO_SCHEMA or not isinstance(current_ratio_record.get('body_axis'), dict):
        raise ValueError('기존 BODY18 참조 비율 계약 오류')
    if not isinstance(current_skeleton_record, dict) or current_skeleton_record.get('schema') != 'kimodo-multiview-body-face-experiment-v1':
        raise ValueError('몸·얼굴 3D 스켈레톤 계약 오류')
    if current_skeleton_record.get('body18_joint_indices') != list(MULTIVIEW_BODY_JOINTS) or current_skeleton_record.get('face_joint_indices') != list(CANDIDATE_FACE_JOINT_INDICES):
        raise ValueError('3D 스켈레톤 관절 순서 오류')
    if current_skeleton_record.get('excluded_body') is not None or current_skeleton_record.get('excluded_face') is not None:
        raise ValueError('제외 관측 검증 결과는 비율 후보로 사용할 수 없습니다.')
    if not isinstance(current_skeleton_record.get('joint_weight_table'), dict):
        raise ValueError('3D 비율 후보에 방향별 관절 가중치가 필요합니다.')
    from generators.kimodo.multiview_joint_weights import validate_multiview_joint_weights
    validate_multiview_joint_weights(current_skeleton_record['joint_weight_table'])
    current_body_positions = np.asarray(current_skeleton_record['body_joint_positions'], dtype=float)
    current_face_positions = np.asarray(current_skeleton_record['face_joint_positions'], dtype=float)
    if current_body_positions.shape != (12, 3) or current_face_positions.shape != (5, 3) or not np.isfinite(current_body_positions).all() or not np.isfinite(current_face_positions).all():
        raise ValueError('3D 관절 좌표 형식 오류')
    current_shoulder_center = current_body_positions[[0, 3]].mean(axis=0)
    current_hip_center = current_body_positions[[6, 9]].mean(axis=0)
    current_torso_length = float(np.linalg.norm(current_shoulder_center - current_hip_center))
    current_torso_height = float(current_shoulder_center[1] - current_hip_center[1])
    current_nose_height = float(current_face_positions[0, 1] - current_shoulder_center[1])
    if current_torso_length <= CANDIDATE_MINIMUM_TORSO_LENGTH or current_torso_height <= CANDIDATE_MINIMUM_TORSO_LENGTH or current_nose_height <= CANDIDATE_MINIMUM_TORSO_LENGTH:
        raise ValueError('3D 코·어깨·골반의 높이 또는 몸통 길이가 유효하지 않습니다.')
    current_candidate_ratios = {}
    for current_segment_name, current_joint_pairs in REFERENCE_SEGMENT_GROUPS.items():
        current_segment_lengths = [np.linalg.norm(current_body_positions[current_start_index-2] - current_body_positions[current_end_index-2]) for current_start_index, current_end_index in current_joint_pairs]
        current_candidate_ratios[current_segment_name] = float(np.mean(current_segment_lengths) / current_torso_length)
        if not np.isfinite(current_candidate_ratios[current_segment_name]) or current_candidate_ratios[current_segment_name] <= 0:
            raise ValueError(f'3D {current_segment_name} 비율 오류')
    current_candidate_record = copy.deepcopy(current_ratio_record)
    current_candidate_record['baseline_3d_candidate_ratios'] = copy.deepcopy(current_ratio_record['ratios'])
    current_candidate_record['baseline_3d_candidate_body_axis'] = copy.deepcopy(current_ratio_record['body_axis'])
    current_candidate_record['ratios'] = current_candidate_ratios
    current_candidate_record['body_axis']['nose_shoulder_to_torso'] = current_nose_height / current_torso_height
    current_candidate_record['body_axis']['vertical_nose_shoulder_to_torso'] = current_nose_height / current_torso_height
    current_candidate_record['body_axis']['anchor'] = '실험: 공통 3D 코·어깨 중심·골반 중심의 수직 높이 비율'
    current_candidate_record['weighted_body_face_candidate'] = copy.deepcopy(current_skeleton_record)
    current_candidate_record['method'] = '실험: 방향별 관절 가중치를 반영한 공통 3D 몸·얼굴 골격의 비율 후보'
    current_candidate_record['limitations'] = '검수용 후보; 이미지 검출점과 카메라·자세 가정에 의존. 얼굴 3D 좌표는 아직 SOMA 머리 앵커에 적용되지 않음.'
    return current_candidate_record


if __name__ == '__main__':
    import argparse
    current_parser = argparse.ArgumentParser(description='검수용 가중 3D 스켈레톤 비율 후보 생성')
    current_parser.add_argument('reference_json', type=Path)
    current_parser.add_argument('skeleton_json', type=Path)
    current_parser.add_argument('output_json', type=Path)
    current_arguments = current_parser.parse_args()
    if current_arguments.output_json.exists():
        raise ValueError('기존 비율 기록을 덮어쓰지 않습니다.')
    current_ratio_record = json.loads(current_arguments.reference_json.read_text())
    current_skeleton_record = json.loads(current_arguments.skeleton_json.read_text())
    current_result_record = build_multiview_ratio_candidate(current_ratio_record, current_skeleton_record)
    current_arguments.output_json.write_text(json.dumps(current_result_record, ensure_ascii=False, indent=2))
    print(f'검수용 3D 비율 후보 저장: {current_arguments.output_json}', flush=True)
