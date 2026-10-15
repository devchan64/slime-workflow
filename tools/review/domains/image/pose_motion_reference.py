"""등록된 걷기 모션의 ANNY 참조와 보조 문구를 읽는다."""
import hashlib
import math
import re
from pathlib import Path

import yaml
from tools.review.common.map_tile_assets import UniqueAssetYamlLoader
from PIL import Image

MOTION_REFERENCE_ROOT = Path(__file__).resolve().parents[4] / 'assets/motion-sheet/hy-motion-walking-v2'
MOTION_PROMPT_CONFIG = Path(__file__).resolve().parents[4] / 'generators/image/config/pose-motion-prompts.yaml'


MOTION_REFERENCE_FRAME_COUNT = 35
MOTION_REFERENCE_DIRECTIONS = ('down_left', 'down_right', 'up_left', 'up_right')
MOTION_MANIFEST_REQUIRED_FIELDS = frozenset((
    'schema_version', 'asset_id', 'version', 'status', 'replaces', 'source_generation_id',
    'frames', 'fps', 'cycle_seconds', 'directions', 'source_frames', 'preview_frames',
    'source_fps', 'projection', 'fov_degrees', 'camera_elevation_degrees',
    'constraint_state', 'camera', 'files',
))


MOTION_CAMERA_REQUIRED_FIELDS = frozenset((
    'projection', 'location', 'rotation_quaternion_wxyz', 'ortho_scale',
    'elevation_degrees', 'azimuth_degrees', 'target', 'distance', 'fov_degrees', 'framing',
))


def require_finite_motion_number(current_numeric_value, current_field_name):
    """YAML bool과 NaN/Infinity를 좌표·시간 값으로 사용하지 않는다."""
    if type(current_numeric_value) not in (int, float) or not math.isfinite(current_numeric_value):
        raise ValueError(f'걷기 참조 {current_field_name}은 유한한 숫자여야 합니다.')
    return current_numeric_value


def validate_motion_reference_metadata(current_manifest_record):
    """원본 설명과 카메라 값의 형식·범위를 검증한다."""
    for current_field_name in ('asset_id', 'status', 'replaces', 'source_generation_id', 'constraint_state'):
        if not isinstance(current_manifest_record[current_field_name], str) or not current_manifest_record[current_field_name].strip():
            raise ValueError(f'걷기 참조 {current_field_name}은 비어 있지 않은 문자열이어야 합니다.')
    if type(current_manifest_record['version']) is not int or current_manifest_record['version'] < 1:
        raise ValueError('걷기 참조 version은 양의 정수여야 합니다.')
    for current_field_name in ('fps', 'source_fps', 'cycle_seconds'):
        if require_finite_motion_number(current_manifest_record[current_field_name], current_field_name) <= 0:
            raise ValueError(f'걷기 참조 {current_field_name}은 양수여야 합니다.')
    current_preview_frames = current_manifest_record['preview_frames']
    if not isinstance(current_preview_frames, list) or len(current_preview_frames) != MOTION_REFERENCE_FRAME_COUNT or any(type(current_frame_number) is not int or current_frame_number < 1 for current_frame_number in current_preview_frames):
        raise ValueError('걷기 참조 preview_frames는 양의 정수 35개 목록이어야 합니다.')
    if current_manifest_record['projection'] not in ('perspective', 'orthographic'):
        raise ValueError('걷기 참조 projection은 perspective 또는 orthographic이어야 합니다.')
    for current_field_name, current_lower_limit, current_upper_limit in (('fov_degrees', 0, 180), ('camera_elevation_degrees', -90, 90)):
        current_angle_value = require_finite_motion_number(current_manifest_record[current_field_name], current_field_name)
        if (current_field_name == 'fov_degrees' and not current_lower_limit < current_angle_value < current_upper_limit) or (current_field_name == 'camera_elevation_degrees' and not current_lower_limit <= current_angle_value <= current_upper_limit):
            raise ValueError(f'걷기 참조 {current_field_name} 범위 오류')
    current_camera_records = current_manifest_record['camera']
    if not isinstance(current_camera_records, dict) or set(current_camera_records) != set(MOTION_REFERENCE_DIRECTIONS):
        raise ValueError('걷기 참조 camera에는 등록된 4방향이 모두 있어야 합니다.')
    for current_direction_name, current_camera_record in current_camera_records.items():
        current_camera_prefix = f'camera.{current_direction_name}'
        if not isinstance(current_camera_record, dict) or set(current_camera_record) != MOTION_CAMERA_REQUIRED_FIELDS:
            raise ValueError(f'걷기 참조 {current_camera_prefix} 필수·알 수 없는 필드 오류')
        if current_camera_record['projection'] != current_manifest_record['projection']:
            raise ValueError(f'걷기 참조 {current_camera_prefix}.projection 불일치')
        if not isinstance(current_camera_record['framing'], str) or not current_camera_record['framing'].strip():
            raise ValueError(f'걷기 참조 {current_camera_prefix}.framing 문자열 오류')
        for current_vector_name, current_vector_length in (('location', 3), ('target', 3), ('rotation_quaternion_wxyz', 4)):
            current_vector_values = current_camera_record[current_vector_name]
            if not isinstance(current_vector_values, list) or len(current_vector_values) != current_vector_length:
                raise ValueError(f'걷기 참조 {current_camera_prefix}.{current_vector_name} 길이 오류')
            for current_coordinate_value in current_vector_values:
                require_finite_motion_number(current_coordinate_value, f'{current_camera_prefix}.{current_vector_name}')
        if not any(current_camera_record['rotation_quaternion_wxyz']):
            raise ValueError(f'걷기 참조 {current_camera_prefix}.rotation_quaternion_wxyz는 영벡터일 수 없습니다.')
        for current_field_name in ('ortho_scale', 'distance', 'fov_degrees', 'elevation_degrees', 'azimuth_degrees'):
            current_numeric_value = require_finite_motion_number(current_camera_record[current_field_name], f'{current_camera_prefix}.{current_field_name}')
            if current_field_name in ('ortho_scale', 'distance') and current_numeric_value <= 0:
                raise ValueError(f'걷기 참조 {current_camera_prefix}.{current_field_name}은 양수여야 합니다.')
            if current_field_name == 'fov_degrees' and not 0 < current_numeric_value < 180:
                raise ValueError(f'걷기 참조 {current_camera_prefix}.fov_degrees 범위 오류')
            if current_field_name == 'elevation_degrees' and not -90 <= current_numeric_value <= 90:
                raise ValueError(f'걷기 참조 {current_camera_prefix}.elevation_degrees 범위 오류')


def read_motion_reference_yaml(current_source_path):
    """구문 오류를 파일 이름이 포함된 설정 오류로 전달한다."""
    try:
        return yaml.load(current_source_path.read_text(), Loader=UniqueAssetYamlLoader)
    except yaml.YAMLError as current_yaml_error:
        raise ValueError(f'걷기 프리셋 YAML 구문 오류 ({current_source_path.name}): {current_yaml_error}') from current_yaml_error


def validate_motion_reference_manifest(current_manifest_record):
    """프리셋이 소비하는 방향·프레임·파일 계약을 검증한다."""
    if not isinstance(current_manifest_record, dict):
        raise ValueError('걷기 참조 매니페스트는 객체여야 합니다.')
    current_missing_fields = MOTION_MANIFEST_REQUIRED_FIELDS - current_manifest_record.keys()
    current_unknown_fields = current_manifest_record.keys() - MOTION_MANIFEST_REQUIRED_FIELDS
    if current_missing_fields or current_unknown_fields:
        raise ValueError(f'걷기 참조 매니페스트 필드 오류: 누락 {sorted(current_missing_fields)}, 알 수 없음 {sorted(map(str, current_unknown_fields))}')
    if type(current_manifest_record['schema_version']) is not int or current_manifest_record['schema_version'] != 1:
        raise ValueError('걷기 참조 schema_version은 지원하는 정수 1이어야 합니다.')
    if type(current_manifest_record.get('frames')) is not int or current_manifest_record['frames'] != MOTION_REFERENCE_FRAME_COUNT:
        raise ValueError('걷기 참조 frames는 정수 35여야 합니다.')
    current_source_frames = current_manifest_record.get('source_frames')
    if (not isinstance(current_source_frames, list)
            or len(current_source_frames) != MOTION_REFERENCE_FRAME_COUNT
            or any(type(current_frame_number) is not int or current_frame_number < 1
                   for current_frame_number in current_source_frames)):
        raise ValueError('걷기 참조 source_frames는 원본 프레임 번호를 담은 양의 정수 35개 목록이어야 합니다.')
    current_direction_values = current_manifest_record.get('directions')
    if not isinstance(current_direction_values, list) or any(not isinstance(current_direction_name, str) for current_direction_name in current_direction_values) or len(current_direction_values) != len(MOTION_REFERENCE_DIRECTIONS) or set(current_direction_values) != set(MOTION_REFERENCE_DIRECTIONS):
        raise ValueError('걷기 참조 directions는 중복 없는 등록 4방향이어야 합니다.')
    validate_motion_reference_metadata(current_manifest_record)
    current_file_records = current_manifest_record.get('files')
    if not isinstance(current_file_records, dict):
        raise ValueError('걷기 참조 files는 경로와 SHA-256 객체여야 합니다.')
    for current_relative_path, current_expected_hash in current_file_records.items():
        if not isinstance(current_relative_path, str) or not current_relative_path or current_relative_path.startswith('/') or any(current_path_part in ('', '.', '..') for current_path_part in current_relative_path.split('/')) or '\\' in current_relative_path:
            raise ValueError('걷기 참조 files 경로는 상위 이동 없는 상대 경로여야 합니다.')
        if not isinstance(current_expected_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', current_expected_hash):
            raise ValueError(f'걷기 참조 파일 해시 형식 오류: {current_relative_path}')
    for current_direction_name in MOTION_REFERENCE_DIRECTIONS:
        for current_frame_number in range(1, MOTION_REFERENCE_FRAME_COUNT + 1):
            current_relative_path = f'anny/{current_direction_name}/anny-{current_frame_number:04d}.png'
            current_expected_hash = current_file_records.get(current_relative_path)
            if not isinstance(current_expected_hash, str) or not re.fullmatch(r'[a-f0-9]{64}', current_expected_hash):
                raise ValueError(f'걷기 참조 파일 해시 누락 또는 형식 오류: {current_relative_path}')


def load_motion_reference(selected_direction_value, selected_frame_number):
    """1부터 시작하는 프레임 번호를 검증하고 해시가 일치하는 이미지를 반환한다."""
    current_manifest_record = read_motion_reference_yaml(MOTION_REFERENCE_ROOT / 'manifest.yaml')
    validate_motion_reference_manifest(current_manifest_record)
    if selected_direction_value not in current_manifest_record['directions']:
        raise ValueError('등록된 걷기 방향을 선택하세요.')
    if isinstance(selected_frame_number, bool) or not isinstance(selected_frame_number, (int, float)) or not float(selected_frame_number).is_integer() or not 1 <= selected_frame_number <= current_manifest_record['frames']:
        raise ValueError('걷기 프레임은 1~35 사이의 정수여야 합니다.')
    selected_frame_number = int(selected_frame_number)
    selected_relative_path = f'anny/{selected_direction_value}/anny-{selected_frame_number:04d}.png'
    selected_image_bytes = (MOTION_REFERENCE_ROOT / selected_relative_path).read_bytes()
    if hashlib.sha256(selected_image_bytes).hexdigest() != current_manifest_record['files'][selected_relative_path]:
        raise ValueError('걷기 ANNY 참조의 등록 해시가 일치하지 않습니다.')
    current_prompt_record = read_motion_reference_yaml(MOTION_PROMPT_CONFIG)
    if not isinstance(current_prompt_record, dict) or set(current_prompt_record) != {'template', 'directions', 'empty_prompt_frames', 'required_prompt_frames', 'empty_prompt_frames_by_direction', 'required_frame_prompts', 'frame_prompt_overrides', 'walking_prompt_excluded_frames'} or not isinstance(current_prompt_record['template'], str) or not isinstance(current_prompt_record['directions'], dict) or set(current_prompt_record['directions']) != set(current_manifest_record['directions']) or not all(isinstance(current_direction_text, str) for current_direction_text in current_prompt_record['directions'].values()):
        raise ValueError('걷기 프리셋 보조 프롬프트 설정이 올바르지 않습니다.')
    empty_prompt_frames = current_prompt_record['empty_prompt_frames']
    if not isinstance(empty_prompt_frames, list) or any(type(current_frame_number) is not int or not 1 <= current_frame_number <= current_manifest_record['frames'] for current_frame_number in empty_prompt_frames):
        raise ValueError('보조 프롬프트 제외 프레임은 1~35 정수 목록이어야 합니다.')
    direction_empty_frames = current_prompt_record['empty_prompt_frames_by_direction']
    if not isinstance(direction_empty_frames, dict) or any(
        current_direction_name not in current_manifest_record['directions']
        or not isinstance(current_frame_numbers, list)
        or any(type(current_frame_number) is not int or not 1 <= current_frame_number <= current_manifest_record['frames'] for current_frame_number in current_frame_numbers)
        for current_direction_name, current_frame_numbers in direction_empty_frames.items()
    ):
        raise ValueError('방향별 보조 프롬프트 제외 프레임은 유효한 방향과 1~35 정수 목록이어야 합니다.')
    required_prompt_frames = current_prompt_record['required_prompt_frames']
    if not isinstance(required_prompt_frames, dict) or any(
        current_direction_name not in current_manifest_record['directions']
        or not isinstance(current_frame_numbers, list)
        or any(type(current_frame_number) is not int or not 1 <= current_frame_number <= current_manifest_record['frames'] or current_frame_number in empty_prompt_frames or current_frame_number in direction_empty_frames.get(current_direction_name, []) for current_frame_number in current_frame_numbers)
        for current_direction_name, current_frame_numbers in required_prompt_frames.items()
    ):
        raise ValueError('보조 프롬프트 필요 프레임은 유효한 방향별 프레임 목록이며 제외 프레임과 겹치지 않아야 합니다.')
    required_frame_prompts = current_prompt_record['required_frame_prompts']
    if not isinstance(required_frame_prompts, dict) or set(required_frame_prompts) != set(required_prompt_frames) or any(not isinstance(current_prompt_text, str) or not current_prompt_text.strip() for current_prompt_text in required_frame_prompts.values()):
        raise ValueError('필수 프레임 보조 문구는 등록된 방향마다 비어 있지 않은 문자열이어야 합니다.')
    frame_prompt_overrides = current_prompt_record['frame_prompt_overrides']
    if not isinstance(frame_prompt_overrides, dict) or any(
        current_direction_name not in current_manifest_record['directions']
        or not isinstance(current_frame_prompts, dict)
        or any(type(current_frame_number) is not int
               or not 1 <= current_frame_number <= current_manifest_record['frames']
               or current_frame_number in empty_prompt_frames
               or current_frame_number in direction_empty_frames.get(current_direction_name, [])
               or not isinstance(current_prompt_text, str) or not current_prompt_text.strip()
               for current_frame_number, current_prompt_text in current_frame_prompts.items())
        for current_direction_name, current_frame_prompts in frame_prompt_overrides.items()
    ):
        raise ValueError('프레임별 보조 문구는 유효한 방향·프레임의 문자열이며 제외 프레임과 겹치지 않아야 합니다.')
    try:
        selected_prompt_text = current_prompt_record['template'].format(direction=current_prompt_record['directions'][selected_direction_value])
    except (KeyError, IndexError, ValueError, AttributeError) as current_template_error:
        raise ValueError(f'걷기 보조 프롬프트 template 치환 오류: {current_template_error}') from current_template_error
    if selected_frame_number in empty_prompt_frames or selected_frame_number in direction_empty_frames.get(selected_direction_value, []):
        selected_prompt_text = ''
    if selected_frame_number in required_prompt_frames.get(selected_direction_value, []):
        selected_prompt_text = required_frame_prompts[selected_direction_value]
    selected_override_prompt = frame_prompt_overrides.get(selected_direction_value, {}).get(selected_frame_number)
    if selected_override_prompt is not None:
        selected_prompt_text = selected_override_prompt
    from tools.review.domains.image.pose_description_prompt import load_pose_descriptions
    walking_excluded_frames = current_prompt_record['walking_prompt_excluded_frames']
    if not isinstance(walking_excluded_frames, dict) or any(
        current_direction_name not in current_manifest_record['directions']
        or not isinstance(current_frame_numbers, list)
        or any(type(current_frame_number) is not int or not 1 <= current_frame_number <= current_manifest_record['frames'] for current_frame_number in current_frame_numbers)
        for current_direction_name, current_frame_numbers in walking_excluded_frames.items()
    ):
        raise ValueError('걷기 문구 제외 프레임은 유효한 방향과 1~35 정수 목록이어야 합니다.')
    common_walking_prompt = '' if selected_frame_number in walking_excluded_frames.get(selected_direction_value, []) else load_pose_descriptions()['walking']['prompt']
    selected_prompt_text = ' '.join(filter(None, (selected_prompt_text, common_walking_prompt)))
    with Image.open(MOTION_REFERENCE_ROOT / selected_relative_path) as selected_image_value:
        loaded_image_value = selected_image_value.copy()
    source_frame_number = current_manifest_record['source_frames'][selected_frame_number-1]
    required_prompt_notice = ' · 등록 보조 문구 적용: 사용자 지정' if selected_override_prompt is not None or selected_frame_number in required_prompt_frames.get(selected_direction_value, []) else ''
    return loaded_image_value, selected_prompt_text, f'걷기 v2 · {selected_direction_value} · {selected_frame_number}/35 · 원본 {source_frame_number}번 · ANNY 참조 적용' + required_prompt_notice


def find_matching_auxiliary(current_history_records, selected_pose_digest, current_base_prompt):
    """같은 참조의 완료 이력에서 기본 문구 뒤에 붙였던 보조 문구를 찾는다."""
    retired_heel_instruction = 'Match heel elevation in <image 1>.'
    for current_history_record in sorted(current_history_records, key=lambda current_record_value: current_record_value['id'], reverse=True):
        current_request_record = current_history_record['request']
        current_snapshot_records = current_request_record.get('reference_snapshots', [])
        current_saved_prompt = current_request_record.get('prompt', '')
        if (current_history_record.get('status', {}).get('status') == 'completed'
                and len(current_snapshot_records) == 2
                and current_snapshot_records[1]['sha256'] == selected_pose_digest
                and retired_heel_instruction not in current_saved_prompt
                and current_saved_prompt.startswith(current_base_prompt + ' ')):
            return current_saved_prompt[len(current_base_prompt):].strip(), current_history_record['id']
    return None
