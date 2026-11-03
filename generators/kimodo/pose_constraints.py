"""단일 모션 생성용 SOMA 전신 키프레임 입력 검증."""
import math


def validate_pose_constraints(current_constraint_records, current_frame_count):
    if not isinstance(current_constraint_records, list) or len(current_constraint_records) > 1:
        raise ValueError('포즈 제약은 전신 제약 목록 하나까지 지원합니다.')
    if not current_constraint_records:
        return []
    if type(current_frame_count) is not int or not 30 <= current_frame_count <= 300:
        raise ValueError('포즈 제약의 모션 길이는 30~300 정수 프레임이어야 합니다.')
    current_constraint_record = current_constraint_records[0]
    if not isinstance(current_constraint_record, dict) or set(current_constraint_record) != {'type', 'frame_indices', 'local_joints_rot', 'root_positions'} or current_constraint_record['type'] != 'fullbody':
        raise ValueError('전신 포즈 제약 필드 오류')
    current_frame_indices = current_constraint_record['frame_indices']
    if not isinstance(current_frame_indices, list) or not current_frame_indices or any(type(current_frame_index) is not int or not 0 <= current_frame_index < current_frame_count for current_frame_index in current_frame_indices) or current_frame_indices != sorted(set(current_frame_indices)):
        raise ValueError('제약 프레임은 범위 내의 중복 없는 오름차순 정수여야 합니다.')
    def validate_numeric_shape(current_input_value, current_expected_shape):
        if not current_expected_shape:
            if type(current_input_value) not in (int, float) or not math.isfinite(current_input_value):
                raise ValueError('포즈 제약은 유한한 숫자여야 합니다.')
            return
        if not isinstance(current_input_value, list) or len(current_input_value) != current_expected_shape[0]:
            raise ValueError('포즈 제약 배열 크기 오류: SOMA 77관절 축각 회전이 필요합니다.')
        for current_child_value in current_input_value:
            validate_numeric_shape(current_child_value, current_expected_shape[1:])
    validate_numeric_shape(current_constraint_record['local_joints_rot'], (len(current_frame_indices), 77, 3))
    validate_numeric_shape(current_constraint_record['root_positions'], (len(current_frame_indices), 3))
    return current_constraint_records
