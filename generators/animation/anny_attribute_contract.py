"""모델 로드 없이 검사하는 ANNY 기본 속성 구조."""
import math

ATTRIBUTE_REQUIRED_FIELD_NAMES = frozenset(('phenotype_kwargs', 'local_changes_kwargs', 'facial_actions', 'pose_parameterization', 'pose_parameters'))
ATTRIBUTE_GROUP_VALUE_RANGES = (('phenotype_kwargs', 0, 1), ('local_changes_kwargs', -1, 1), ('facial_actions', 0, 1))
ATTRIBUTE_HEAD_SCALE_NAMES = frozenset(('head-scale-horiz-incr', 'head-scale-vert-incr', 'head-scale-depth-incr'))


def validate_anny_attribute_structure(current_attribute_record):
    if not isinstance(current_attribute_record, dict) or set(current_attribute_record) != ATTRIBUTE_REQUIRED_FIELD_NAMES:
        raise ValueError('ANNY 입력 최상위 필드 불일치')
    if current_attribute_record['pose_parameterization'] != 'local-ref':
        raise ValueError('지원 pose_parameterization은 local-ref')
    for current_group_name, current_minimum_value, current_maximum_value in ATTRIBUTE_GROUP_VALUE_RANGES:
        current_group_values = current_attribute_record[current_group_name]
        if not isinstance(current_group_values, dict):
            raise ValueError(f'ANNY 속성 그룹 형식 오류: {current_group_name}')
        for current_attribute_name, current_numeric_value in current_group_values.items():
            current_allowed_maximum = 3 if current_group_name == 'local_changes_kwargs' and current_attribute_name in ATTRIBUTE_HEAD_SCALE_NAMES else current_maximum_value
            if not isinstance(current_attribute_name, str) or not current_attribute_name or type(current_numeric_value) not in (int, float) or not math.isfinite(current_numeric_value) or not current_minimum_value <= current_numeric_value <= current_allowed_maximum:
                raise ValueError(f'ANNY 속성 범위 오류: {current_group_name}.{current_attribute_name}')
    current_pose_values = current_attribute_record['pose_parameters']
    if not isinstance(current_pose_values, dict) or not current_pose_values:
        raise ValueError('ANNY 포즈 본 목록 형식 오류')
    for current_bone_name, current_matrix_values in current_pose_values.items():
        if not isinstance(current_bone_name, str) or not current_bone_name or not isinstance(current_matrix_values, list) or len(current_matrix_values) != 4:
            raise ValueError(f'ANNY 포즈 행렬 형식 오류: {current_bone_name}')
        for current_matrix_row in current_matrix_values:
            if not isinstance(current_matrix_row, list) or len(current_matrix_row) != 4 or any(type(current_numeric_value) not in (int, float) or not math.isfinite(current_numeric_value) for current_numeric_value in current_matrix_row):
                raise ValueError(f'ANNY 포즈 행렬 수치 오류: {current_bone_name}')
