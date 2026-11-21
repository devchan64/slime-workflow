"""8방향 참조에서 보이는 코를 3D 투영에 맞춰 검증한다.

진단 결과는 생성용 보정값을 자동으로 변경하지 않는다.
"""
import argparse
import json
from pathlib import Path

import numpy as np

HEAD_VISIBLE_ANGLE_LIMIT_DEGREES = 65.0
HEAD_MINIMUM_DETECTION_SCORE = 0.6
HEAD_MINIMUM_VISIBLE_VIEWS = 3


def calculate_multiview_head_diagnostics(current_reference_record, current_multiview_record):
    """전방 관측의 코를 추정하고 각 관측을 제외해 재투영 오차를 계산한다."""
    current_views = current_multiview_record['views']
    current_points = current_reference_record['keypoints']
    current_sources = current_reference_record['observation_sources']
    if len(current_views) != 8 or len(current_points) != 8 or len(current_sources) != 8:
        raise ValueError('8개 참조 관측과 8개 카메라가 필요합니다.')
    current_samples = []
    for current_index, (current_view, current_point, current_source) in enumerate(zip(current_views, current_points, current_sources)):
        current_body = np.asarray(current_point, dtype=float)
        current_box = np.asarray(current_source['bbox'], dtype=float)
        current_angle = float(current_view['fitted_yaw_degrees'])
        current_angle_offset = (current_angle + 180) % 360 - 180
        if current_body.shape != (18, 3) or current_box.shape != (4,) or not np.isfinite(current_body).all() or not np.isfinite(current_box).all():
            raise ValueError('참조 관절 또는 검출 상자 형식 오류')
        current_height = float(current_box[3] - current_box[1])
        current_scale = float(current_view['scale'])
        current_offset = np.asarray(current_view['offset'], dtype=float)
        if current_height <= 0 or current_scale <= 0 or current_offset.shape != (2,) or not np.isfinite(current_offset).all() or not np.isfinite(current_angle):
            raise ValueError('참조 카메라 또는 높이 형식 오류')
        if abs(current_angle_offset) > HEAD_VISIBLE_ANGLE_LIMIT_DEGREES or min(current_body[[0, 8, 11], 2]) < HEAD_MINIMUM_DETECTION_SCORE:
            continue
        current_center = current_body[[8, 11], :2].mean(axis=0)
        current_xy = ((current_body[0, :2] - current_center) / current_height - current_offset) / current_scale
        current_radians = np.deg2rad(current_angle)
        current_samples.append((current_index + 1, np.array([np.cos(current_radians), np.sin(current_radians)]), current_xy, current_height, current_scale))
    if len(current_samples) < HEAD_MINIMUM_VISIBLE_VIEWS:
        raise ValueError('코 3D 검증에 전방 유효 관측 3개 이상이 필요합니다.')

    def fit_head_sample_set(current_sample_set):
        current_matrix = np.asarray([current_sample[1] for current_sample in current_sample_set])
        current_horizontal = np.asarray([current_sample[2][0] for current_sample in current_sample_set])
        if np.linalg.matrix_rank(current_matrix) < 2:
            raise ValueError('코 깊이 추정에 서로 다른 전방 관측이 필요합니다.')
        current_xz = np.linalg.lstsq(current_matrix, current_horizontal, rcond=None)[0]
        current_y = -float(np.mean([current_sample[2][1] for current_sample in current_sample_set]))
        return np.array([current_xz[0], current_y, current_xz[1]])

    current_head_position = fit_head_sample_set(current_samples)
    current_joint_positions = np.asarray(current_multiview_record['joint_positions'], dtype=float)
    if current_joint_positions.shape != (12, 3) or not np.isfinite(current_joint_positions).all():
        raise ValueError('3D 관절 형식 오류')
    current_shoulder_height = float(current_joint_positions[[0, 3], 1].mean())
    current_hip_height = float(current_joint_positions[[6, 9], 1].mean())
    current_torso_height = current_shoulder_height - current_hip_height
    if current_torso_height <= 0 or current_head_position[1] <= current_shoulder_height:
        raise ValueError('코와 몸통의 3D 수직 순서가 유효하지 않습니다.')
    current_heldout_records = []
    for current_sample_index, current_sample in enumerate(current_samples):
        current_other_samples = current_samples[:current_sample_index] + current_samples[current_sample_index + 1:]
        current_heldout_head = fit_head_sample_set(current_other_samples)
        current_prediction = np.array([current_sample[1] @ current_heldout_head[[0, 2]], -current_heldout_head[1]])
        current_error = (current_prediction - current_sample[2]) * current_sample[3] * current_sample[4]
        current_heldout_records.append({'observation': current_sample[0], 'error_xy_px': current_error.tolist(), 'error_px': float(np.linalg.norm(current_error))})
    return {'schema': 'kimodo-multiview-head-diagnostics-v1', 'head_position': current_head_position.tolist(), 'vertical_nose_shoulder_to_torso': float((current_head_position[1] - current_shoulder_height) / current_torso_height), 'observations': [current_sample[0] for current_sample in current_samples], 'heldout': current_heldout_records, 'limitations': ['전방 각도는 추정 카메라 각도에 의존', '코 검출 점수는 가림 여부를 보장하지 않음', '동일 방향의 몸 관절은 카메라 추정에 사용', '생성용 보정값에 자동 적용하지 않음']}


if __name__ == '__main__':
    current_parser = argparse.ArgumentParser(description='8방향 참조의 코 3D 재투영 진단')
    current_parser.add_argument('reference_json', type=Path)
    current_parser.add_argument('multiview_json', type=Path)
    current_parser.add_argument('output_json', type=Path)
    current_arguments = current_parser.parse_args()
    current_reference = json.loads(current_arguments.reference_json.read_text())
    current_record = json.loads(current_arguments.multiview_json.read_text())
    current_result = calculate_multiview_head_diagnostics(current_reference, current_record.get('multiview_experiment', current_record))
    current_arguments.output_json.write_text(json.dumps(current_result, ensure_ascii=False, indent=2))
    print(f'코 재투영 진단 저장: {current_arguments.output_json}', flush=True)
