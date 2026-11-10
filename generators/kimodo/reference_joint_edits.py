"""참조 포즈 검출점의 수동 수정과 원본 일치 여부를 검증한다."""
import math
import numpy as np

REFERENCE_JOINT_MATCH_TOLERANCE = 0.01


def apply_reference_joint_edits(current_reference_points, current_edit_records, current_image_size):
    """원본 픽셀 좌표를 확인한 뒤 수정 좌표와 변경 근거를 반환한다."""
    current_source_points = np.asarray(current_reference_points, dtype=float)
    if current_source_points.shape != (18, 3) or not np.isfinite(current_source_points).all():
        raise ValueError('참조 BODY18 관절 좌표 형식 오류')
    if not isinstance(current_edit_records, list):
        raise ValueError('참조 관절 수정 목록 형식 오류')
    if not isinstance(current_image_size, (tuple, list)) or len(current_image_size) != 2 or any(type(current_dimension_value) is not int or current_dimension_value <= 0 for current_dimension_value in current_image_size):
        raise ValueError('참조 이미지 크기 형식 오류')
    current_edited_points = current_source_points.copy()
    current_edit_evidence = []
    current_seen_indices = set()
    for current_edit_record in current_edit_records:
        if not isinstance(current_edit_record, dict) or set(current_edit_record) != {'joint', 'original', 'edited'}:
            raise ValueError('참조 관절 수정 필드 오류')
        current_joint_index = current_edit_record['joint']
        if type(current_joint_index) is not int or not 0 <= current_joint_index < 18 or current_joint_index in current_seen_indices:
            raise ValueError('참조 관절 번호가 중복되었거나 범위를 벗어났습니다.')
        current_seen_indices.add(current_joint_index)
        for current_coordinate_name in ('original', 'edited'):
            current_coordinates = current_edit_record[current_coordinate_name]
            if not isinstance(current_coordinates, list) or len(current_coordinates) != 2 or any(type(current_coordinate_value) not in (int, float) or not math.isfinite(current_coordinate_value) for current_coordinate_value in current_coordinates):
                raise ValueError('참조 관절 수정 좌표 형식 오류')
        current_original_coordinates = current_edit_record['original']
        current_edited_coordinates = current_edit_record['edited']
        if any(not 0 <= current_edited_coordinates[current_axis_index] < current_image_size[current_axis_index] for current_axis_index in (0, 1)):
            raise ValueError('수정한 관절 좌표가 참조 이미지 범위를 벗어났습니다.')
        if not np.allclose(current_source_points[current_joint_index, :2], current_original_coordinates, rtol=0, atol=REFERENCE_JOINT_MATCH_TOLERANCE):
            raise ValueError('관절 검출 원본이 변경되어 수동 수정을 적용할 수 없습니다.')
        current_edited_points[current_joint_index, :2] = current_edit_record['edited']
        current_edit_evidence.append({'joint': current_joint_index, 'original': list(current_original_coordinates), 'edited': list(current_edit_record['edited']), 'source_confidence': float(current_source_points[current_joint_index, 2])})
    return current_edited_points, current_edit_evidence
