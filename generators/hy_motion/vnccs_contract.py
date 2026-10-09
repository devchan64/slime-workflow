"""VNCCS용 ANNY 포즈 이미지 출력 계약. 이미지 생성 모델은 실행하지 않는다."""
import hashlib
import math
from pathlib import Path
import yaml
from generators.hy_motion.contracts import UniqueConfigLoader, SUPPORTED_DIRECTION_NAMES
from tools.review.common.generation_records import validate_history_tag

VNCCS_EXPORT_CONFIG = Path(__file__).parent / 'config/vnccs-export.yaml'
VNCCS_EXPORT_FIELDS = {'source_id', 'start_frame', 'end_frame', 'frame_step', 'directions', 'tag'}


def load_vnccs_config():
    current_config_record = yaml.load(VNCCS_EXPORT_CONFIG.read_text(), Loader=UniqueConfigLoader)
    current_expected_fields = {'schema_version', 'rig_backend', 'resolution', 'samples', 'frame_step', 'camera_elevation', 'camera_angles', 'framing_margin', 'skin_profile', 'target_profile', 'projections', 'perspective_fov_degrees'}
    if not isinstance(current_config_record, dict) or set(current_config_record) != current_expected_fields:
        raise ValueError('VNCCS 출력 설정 필드 오류')
    if current_config_record['rig_backend'] != 'anny':
        raise ValueError('지원하지 않는 VNCCS 리그 백엔드')
    if current_config_record['projections'] != ['orthographic', 'perspective']:
        raise ValueError('VNCCS 출력은 정사영·원근투영 순서로 고정합니다.')
    if type(current_config_record['perspective_fov_degrees']) not in (int, float) or current_config_record['perspective_fov_degrees'] != 30:
        raise ValueError('VNCCS 원근투영 FOV는 30도로 고정합니다.')
    for current_field_name, current_minimum_value, current_maximum_value in (('schema_version', 1, 1), ('resolution', 512, 512), ('samples', 1, 128), ('frame_step', 1, 360)):
        if type(current_config_record[current_field_name]) is not int or not current_minimum_value <= current_config_record[current_field_name] <= current_maximum_value:
            raise ValueError('VNCCS 출력 정수 설정 오류: ' + current_field_name)
    if current_config_record['skin_profile'] != 'generators/hy_motion/config/anny-adjacency-barrier.yaml' or current_config_record['target_profile'] != 'generators/animation/config/anny_profiles/neutral.yaml':
        raise ValueError('지원하지 않는 고정 ANNY 출력 프로필')
    if not isinstance(current_config_record['camera_angles'], dict) or set(current_config_record['camera_angles']) != set(SUPPORTED_DIRECTION_NAMES):
        raise ValueError('VNCCS 카메라 방향 설정 오류')
    for current_numeric_value in [current_config_record['camera_elevation'], current_config_record['framing_margin'], *current_config_record['camera_angles'].values()]:
        if type(current_numeric_value) not in (int, float) or not math.isfinite(current_numeric_value):
            raise ValueError('VNCCS 카메라 설정은 유한한 수여야 합니다.')
    if not 1 < current_config_record['framing_margin'] <= 2 or not -80 <= current_config_record['camera_elevation'] <= 80:
        raise ValueError('VNCCS 카메라 여백·고도 범위 오류')
    return current_config_record


def validate_vnccs_request(current_request_values, current_source_frames):
    if type(current_source_frames) is not int or not 1 <= current_source_frames <= 360:
        raise ValueError('원본 프레임 수는 1~360 정수여야 합니다.')
    if not isinstance(current_request_values, dict) or not {'source_id'} <= set(current_request_values) <= VNCCS_EXPORT_FIELDS:
        raise ValueError('VNCCS 출력 입력 필드 오류')
    if not isinstance(current_request_values['source_id'], str) or not current_request_values['source_id'].strip():
        raise ValueError('원본 생성 ID가 필요합니다.')
    current_request_record = {'start_frame': 1, 'end_frame': current_source_frames, 'frame_step': load_vnccs_config()['frame_step'], 'directions': list(SUPPORTED_DIRECTION_NAMES), 'tag': '', **current_request_values}
    for current_field_name in ('start_frame', 'end_frame', 'frame_step'):
        if type(current_request_record[current_field_name]) is not int or not 1 <= current_request_record[current_field_name] <= current_source_frames:
            raise ValueError('원본 범위의 정수 프레임이 필요합니다: ' + current_field_name)
    if current_request_record['start_frame'] > current_request_record['end_frame']:
        raise ValueError('시작 프레임이 종료 프레임보다 큽니다.')
    current_direction_names = current_request_record['directions']
    if not isinstance(current_direction_names, list) or not current_direction_names or any(type(current_direction_name) is not str or current_direction_name not in SUPPORTED_DIRECTION_NAMES for current_direction_name in current_direction_names) or len(set(current_direction_names)) != len(current_direction_names):
        raise ValueError('VNCCS 출력 방향 오류')
    current_request_record['tag'] = validate_history_tag(current_request_record['tag'])
    return current_request_record


def calculate_file_digest(current_source_path):
    return hashlib.sha256(Path(current_source_path).read_bytes()).hexdigest()
