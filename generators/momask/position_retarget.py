"""골격 이름·동작 이름에 의존하지 않는 위치 채널 리타깃."""
import math
from pathlib import Path

import yaml
from mathutils import Matrix, Quaternion, Vector

RETARGET_ALGORITHM_VERSION = 'position-reference-transport-v3'
MINIMUM_DIRECTION_LENGTH = 1e-8
MINIMUM_FRAME_SINE = 1e-6
PROFILE_REQUIRED_FIELDS = {'schema_version', 'profile_id', 'joint_count', 'coordinate_matrix', 'root_joint', 'scale_source', 'scale_target', 'segments', 'unmapped_policy', 'source_reference'}
SEGMENT_REQUIRED_FIELDS = {'segment_id', 'source_primary', 'target_primary', 'source_secondary', 'target_secondary', 'target_bones', 'transfer_mode'}


class UniqueProfileLoader(yaml.SafeLoader):
    """중복 키를 허용하지 않는 YAML 로더."""


def construct_unique_mapping(profile_yaml_loader, current_mapping_node, deep_mapping_flag=False):
    parsed_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_key_value = profile_yaml_loader.construct_object(current_key_node, deep=deep_mapping_flag)
        if current_key_value in parsed_mapping_values:
            raise ValueError(f'리타깃 프로필 중복 키: {current_key_value}')
        parsed_mapping_values[current_key_value] = profile_yaml_loader.construct_object(current_value_node, deep=deep_mapping_flag)
    return parsed_mapping_values


UniqueProfileLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def normalize_valid_direction(current_direction_value, direction_context_label):
    current_direction_value = Vector(current_direction_value)
    if not all(math.isfinite(current_axis_value) for current_axis_value in current_direction_value) or current_direction_value.length <= MINIMUM_DIRECTION_LENGTH:
        raise ValueError(f'유효하지 않은 관절 방향: {direction_context_label}')
    return current_direction_value.normalized()


def build_observed_frame(primary_direction_value, secondary_direction_value, frame_context_label):
    primary_axis_value = normalize_valid_direction(primary_direction_value, frame_context_label)
    secondary_axis_value = normalize_valid_direction(secondary_direction_value, frame_context_label)
    secondary_axis_value -= primary_axis_value * secondary_axis_value.dot(primary_axis_value)
    if secondary_axis_value.length <= MINIMUM_FRAME_SINE:
        raise ValueError(f'방향 프레임의 독립 축이 없습니다: {frame_context_label}')
    secondary_axis_value.normalize()
    depth_axis_value = primary_axis_value.cross(secondary_axis_value).normalized()
    return Matrix((secondary_axis_value, depth_axis_value, primary_axis_value)).transposed().to_quaternion()


def calculate_minimum_transport(previous_direction_value, current_direction_value, reference_axis_value):
    """반대 방향의 미정 회전축도 기준 프레임에서 일관되게 선택한다."""
    cross_direction_value = previous_direction_value.cross(current_direction_value)
    direction_dot_value = max(-1.0, min(1.0, previous_direction_value.dot(current_direction_value)))
    if cross_direction_value.length > MINIMUM_DIRECTION_LENGTH:
        return Quaternion(cross_direction_value.normalized(), math.atan2(cross_direction_value.length, direction_dot_value))
    if direction_dot_value >= 0:
        return Quaternion()
    rotation_axis_value = reference_axis_value - previous_direction_value * reference_axis_value.dot(previous_direction_value)
    rotation_axis_value = normalize_valid_direction(rotation_axis_value, '반대 방향 초기 기준 축')
    return Quaternion(rotation_axis_value, math.pi)


def validate_profile_pair(current_pair_values, pair_value_type, profile_context_label, source_joint_count):
    if not isinstance(current_pair_values, list) or len(current_pair_values) != 2 or any(type(current_pair_value) is not pair_value_type for current_pair_value in current_pair_values):
        raise ValueError(f'관절 대응 쌍 형식 오류: {profile_context_label}')
    if current_pair_values[0] == current_pair_values[1]:
        raise ValueError(f'동일 관절 대응 쌍: {profile_context_label}')
    if pair_value_type is int and any(current_joint_index < 0 or current_joint_index >= source_joint_count for current_joint_index in current_pair_values):
        raise ValueError(f'원본 관절 인덱스 범위 오류: {profile_context_label}')


def load_retarget_profile(profile_source_path):
    profile_record_values = yaml.load(Path(profile_source_path).read_text(), Loader=UniqueProfileLoader)
    if not isinstance(profile_record_values, dict) or set(profile_record_values) != PROFILE_REQUIRED_FIELDS:
        raise ValueError('리타깃 프로필 필드가 계약과 다릅니다.')
    if type(profile_record_values['schema_version']) is not int or profile_record_values['schema_version'] != 2 or not isinstance(profile_record_values['profile_id'], str) or not profile_record_values['profile_id']:
        raise ValueError('리타깃 프로필 버전·식별자 오류')
    source_joint_count = profile_record_values['joint_count']
    if type(source_joint_count) is not int or source_joint_count < 2:
        raise ValueError('리타깃 관절 수 오류')
    source_reference_record = profile_record_values['source_reference']
    if not isinstance(source_reference_record, dict) or set(source_reference_record) != {'id', 'source_url', 'source_sha256', 'joint_positions'}:
        raise ValueError('원본 기준 골격 필드 오류')
    if any(not isinstance(source_reference_record[current_field_name], str) or not source_reference_record[current_field_name] for current_field_name in ('id', 'source_url', 'source_sha256')):
        raise ValueError('원본 기준 골격 출처 누락')
    source_reference_points = source_reference_record['joint_positions']
    if not isinstance(source_reference_points, list) or len(source_reference_points) != source_joint_count or any(not isinstance(current_point_values, list) or len(current_point_values) != 3 or any(type(current_axis_value) not in (int, float) or not math.isfinite(current_axis_value) for current_axis_value in current_point_values) for current_point_values in source_reference_points):
        raise ValueError('원본 기준 골격 관절 오류')
    if type(profile_record_values['root_joint']) is not int or not 0 <= profile_record_values['root_joint'] < source_joint_count:
        raise ValueError('루트 관절 인덱스 오류')
    if profile_record_values['unmapped_policy'] != 'inherit_rest_local':
        raise ValueError('지원하지 않는 미대응 본 정책')
    coordinate_matrix_values = profile_record_values['coordinate_matrix']
    if not isinstance(coordinate_matrix_values, list) or len(coordinate_matrix_values) != 3 or any(not isinstance(current_row_values, list) or len(current_row_values) != 3 or any(type(current_axis_value) not in (float, int) or not math.isfinite(current_axis_value) for current_axis_value in current_row_values) for current_row_values in coordinate_matrix_values):
        raise ValueError('좌표 변환 행렬 형식 오류')
    coordinate_matrix_value = Matrix(coordinate_matrix_values)
    identity_matrix_value = coordinate_matrix_value.transposed() @ coordinate_matrix_value
    if abs(coordinate_matrix_value.determinant()-1) > MINIMUM_FRAME_SINE or any(abs(identity_matrix_value[row_axis_index][column_axis_index] - int(row_axis_index == column_axis_index)) > MINIMUM_FRAME_SINE for row_axis_index in range(3) for column_axis_index in range(3)):
        raise ValueError('좌표 변환은 오른손 직교 회전이어야 합니다.')
    validate_profile_pair(profile_record_values['scale_source'], int, 'scale_source', source_joint_count)
    validate_profile_pair(profile_record_values['scale_target'], str, 'scale_target', source_joint_count)
    if not isinstance(profile_record_values['segments'], list) or not profile_record_values['segments']:
        raise ValueError('리타깃 구간 목록이 비어 있습니다.')
    assigned_bone_names = set()
    assigned_segment_names = set()
    for current_segment_record in profile_record_values['segments']:
        if not isinstance(current_segment_record, dict) or set(current_segment_record) != SEGMENT_REQUIRED_FIELDS:
            raise ValueError('리타깃 구간 필드 오류')
        if current_segment_record['transfer_mode'] not in ('absolute_direction', 'reference_delta'):
            raise ValueError('지원하지 않는 방향 전달 방식')
        current_segment_label = current_segment_record['segment_id']
        if not isinstance(current_segment_label, str) or not current_segment_label or current_segment_label in assigned_segment_names:
            raise ValueError('리타깃 구간 식별자 오류·중복')
        assigned_segment_names.add(current_segment_label)
        for current_pair_field, current_pair_type in [('source_primary', int), ('target_primary', str)]:
            validate_profile_pair(current_segment_record[current_pair_field], current_pair_type, current_segment_label, source_joint_count)
        if (current_segment_record['source_secondary'] is None) != (current_segment_record['target_secondary'] is None):
            raise ValueError(f'부 방향 대응 불일치: {current_segment_label}')
        if current_segment_record['source_secondary'] is not None:
            validate_profile_pair(current_segment_record['source_secondary'], int, current_segment_label, source_joint_count)
            validate_profile_pair(current_segment_record['target_secondary'], str, current_segment_label, source_joint_count)
        if not isinstance(current_segment_record['target_bones'], list) or not current_segment_record['target_bones']:
            raise ValueError(f'대상 본 목록 오류: {current_segment_label}')
        for current_bone_name in current_segment_record['target_bones']:
            if not isinstance(current_bone_name, str) or not current_bone_name or current_bone_name in assigned_bone_names:
                raise ValueError(f'대상 본 이름 오류·중복: {current_bone_name}')
            assigned_bone_names.add(current_bone_name)
    return profile_record_values


def calculate_pair_direction(current_point_values, current_pair_values):
    return Vector(current_point_values[current_pair_values[1]]) - Vector(current_point_values[current_pair_values[0]])


class PositionRetargetSolver:
    """독립적인 두 방향은 직접 복원하고, 단일 방향의 비틀림은 운반한다."""

    def __init__(self, profile_record_values, rest_bone_positions, rest_bone_rotations):
        self.profile_record_values = profile_record_values
        self.rest_bone_rotations = rest_bone_rotations
        self.segment_binding_values = {}
        self.previous_segment_states = {}
        source_reference_points = [Matrix(profile_record_values['coordinate_matrix']) @ Vector(current_point_values) for current_point_values in profile_record_values['source_reference']['joint_positions']]
        for current_segment_record in profile_record_values['segments']:
            for current_pair_field in ('target_primary', 'target_secondary'):
                for current_bone_name in current_segment_record[current_pair_field] or []:
                    if current_bone_name not in rest_bone_positions:
                        raise ValueError(f'대상 기준 관절 누락: {current_bone_name}')
            for current_bone_name in current_segment_record['target_bones']:
                if current_bone_name not in rest_bone_rotations:
                    raise ValueError(f'대상 본 누락: {current_bone_name}')
            rest_primary_value = normalize_valid_direction(calculate_pair_direction(rest_bone_positions, current_segment_record['target_primary']), current_segment_record['segment_id'])
            reference_point_values = source_reference_points if current_segment_record['transfer_mode'] == 'reference_delta' else rest_bone_positions
            reference_primary_pair = current_segment_record['source_primary'] if current_segment_record['transfer_mode'] == 'reference_delta' else current_segment_record['target_primary']
            reference_secondary_pair = current_segment_record['source_secondary'] if current_segment_record['transfer_mode'] == 'reference_delta' else current_segment_record['target_secondary']
            reference_primary_value = normalize_valid_direction(calculate_pair_direction(reference_point_values, reference_primary_pair), current_segment_record['segment_id'])
            rest_frame_rotation = None
            if current_segment_record['target_secondary'] is not None:
                rest_frame_rotation = build_observed_frame(reference_primary_value, calculate_pair_direction(reference_point_values, reference_secondary_pair), current_segment_record['segment_id'])
            # 기준 본의 축 중 주 방향과 가장 독립적인 축으로 초기 미관측 회전을 정의한다.
            first_bone_rotation = rest_bone_rotations[current_segment_record['target_bones'][0]]
            reference_axis_values = [first_bone_rotation @ Vector(current_axis_values) for current_axis_values in ((1, 0, 0), (0, 1, 0), (0, 0, 1))]
            rest_reference_axis = min(reference_axis_values, key=lambda current_axis_value: abs(current_axis_value.dot(reference_primary_value)))
            self.segment_binding_values[current_segment_record['segment_id']] = (reference_primary_value, rest_frame_rotation, rest_reference_axis, rest_primary_value)

    def calculate_frame_rotations(self, current_joint_points):
        if len(current_joint_points) != self.profile_record_values['joint_count'] or any(len(current_joint_point) != 3 or not all(math.isfinite(current_axis_value) for current_axis_value in current_joint_point) for current_joint_point in current_joint_points):
            raise ValueError('위치 채널 형태·유한값 오류')
        frame_rotation_values = {}
        frame_diagnostic_values = {}
        next_segment_states = {}
        for current_segment_record in self.profile_record_values['segments']:
            current_segment_label = current_segment_record['segment_id']
            rest_primary_value, rest_frame_rotation, rest_reference_axis, target_rest_primary = self.segment_binding_values[current_segment_label]
            target_primary_value = normalize_valid_direction(calculate_pair_direction(current_joint_points, current_segment_record['source_primary']), current_segment_label)
            previous_segment_state = self.previous_segment_states.get(current_segment_label)
            if rest_frame_rotation is not None:
                current_frame_rotation = build_observed_frame(target_primary_value, calculate_pair_direction(current_joint_points, current_segment_record['source_secondary']), current_segment_label)
                segment_delta_rotation = current_frame_rotation @ rest_frame_rotation.inverted()
                segment_observation_mode = 'two_directions'
            else:
                previous_direction_value, previous_delta_rotation = previous_segment_state if previous_segment_state is not None else (rest_primary_value, Quaternion())
                incremental_rotation_value = calculate_minimum_transport(previous_direction_value, target_primary_value, previous_delta_rotation @ rest_reference_axis)
                segment_delta_rotation = incremental_rotation_value @ previous_delta_rotation
                segment_observation_mode = 'direction_only_transport'
            segment_delta_rotation.normalize()
            if previous_segment_state is not None and previous_segment_state[1].dot(segment_delta_rotation) < 0:
                segment_delta_rotation.negate()
            next_segment_states[current_segment_label] = (target_primary_value.copy(), segment_delta_rotation.copy())
            actual_primary_value = segment_delta_rotation @ rest_primary_value
            direction_error_degrees = math.degrees(math.atan2(actual_primary_value.cross(target_primary_value).length, actual_primary_value.dot(target_primary_value)))
            rotation_step_degrees = 0.0 if previous_segment_state is None else math.degrees(2 * math.acos(min(1.0, abs(previous_segment_state[1].dot(segment_delta_rotation)))))
            expected_target_direction = segment_delta_rotation @ target_rest_primary
            frame_diagnostic_values[current_segment_label] = {'observation': segment_observation_mode, 'transfer_mode': current_segment_record['transfer_mode'], 'direction_error_degrees': direction_error_degrees, 'rotation_step_degrees': rotation_step_degrees, 'expected_target_direction': list(expected_target_direction)}
            for current_bone_name in current_segment_record['target_bones']:
                frame_rotation_values[current_bone_name] = segment_delta_rotation @ self.rest_bone_rotations[current_bone_name]
        self.previous_segment_states = next_segment_states
        return frame_rotation_values, frame_diagnostic_values
