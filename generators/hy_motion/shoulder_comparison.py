"""동일 Z-up 좌표계의 쇄골·어깨 비교. 위치 보정은 수행하지 않는다."""
import numpy as np


def measure_shoulder_difference(current_source_points, current_target_points):
    """양쪽 3점: 쇄골 시작, 어깨 보조 관절, 상완 시작. 단위 m."""
    current_source_points = np.asarray(current_source_points, dtype=float)
    current_target_points = np.asarray(current_target_points, dtype=float)
    if current_source_points.shape != (3, 3) or current_target_points.shape != (3, 3) or not np.isfinite(current_source_points).all() or not np.isfinite(current_target_points).all():
        raise ValueError('어깨 비교에는 유한한 [3,3] 좌표 두 개가 필요합니다.')
    current_segment_records = []
    for current_segment_index, current_segment_name in enumerate(('clavicle', 'shoulder')):
        current_source_vector = current_source_points[current_segment_index + 1] - current_source_points[current_segment_index]
        current_target_vector = current_target_points[current_segment_index + 1] - current_target_points[current_segment_index]
        current_source_length = float(np.linalg.norm(current_source_vector))
        current_target_length = float(np.linalg.norm(current_target_vector))
        if min(current_source_length, current_target_length) < 1e-8:
            raise ValueError('길이가 없는 쇄골·어깨 세그먼트')
        current_source_direction = current_source_vector / current_source_length
        current_target_direction = current_target_vector / current_target_length
        current_segment_records.append({'segment': current_segment_name, 'source_direction': current_source_direction.tolist(), 'target_direction': current_target_direction.tolist(), 'direction_error_degrees': float(np.degrees(np.arccos(np.clip(np.dot(current_source_direction, current_target_direction), -1, 1)))), 'source_elevation_degrees': float(np.degrees(np.arcsin(np.clip(current_source_direction[2], -1, 1)))), 'target_elevation_degrees': float(np.degrees(np.arcsin(np.clip(current_target_direction[2], -1, 1)))), 'source_length_m': current_source_length, 'target_length_m': current_target_length, 'height_error_target_length_m': float(current_target_vector[2] - current_source_direction[2] * current_target_length)})
    return {'segments': current_segment_records, 'shoulder_height_error_target_lengths_m': sum(current_segment_record['height_error_target_length_m'] for current_segment_record in current_segment_records), 'source_points_z_up': current_source_points.tolist(), 'target_points_z_up': current_target_points.tolist(), 'comparison_basis': '쇄골 시작점을 정렬하고 세그먼트별 ANNY 길이에 원본 방향을 적용한 상대 높이 차이. 양수는 ANNY가 높음. 체형 길이 차이와 루트 이동 제외.'}
