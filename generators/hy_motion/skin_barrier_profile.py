"""채택된 ANNY 피부 충돌 제약 설정의 엄격한 로딩."""
import math
from pathlib import Path
import yaml
from generators.hy_motion.contracts import UniqueConfigLoader

SKIN_BARRIER_PROFILE = Path(__file__).parent / 'config/anny-skin-barrier.yaml'
SKIN_BARRIER_FIELDS = {'schema_version', 'profile_id', 'target_rig', 'target_mesh', 'bone_prefixes', 'angle_step_degrees', 'boundary_refinements', 'minimum_surface_clearance_m', 'audit_substeps', 'adjacent_connections', 'collision_scope', 'approval_status'}


def load_skin_barrier(current_profile_path=SKIN_BARRIER_PROFILE):
    current_profile_record = yaml.load(Path(current_profile_path).read_text(), Loader=UniqueConfigLoader)
    current_adjacency_candidate = isinstance(current_profile_record, dict) and current_profile_record.get('profile_id') == 'anny-neutral-v4-adjacency-barrier-v4'
    current_temporal_candidate = isinstance(current_profile_record, dict) and current_profile_record.get('profile_id') in ('anny-neutral-v4-temporal-barrier-v3', 'anny-neutral-v4-adjacency-barrier-v4')
    current_proximal_candidate = current_temporal_candidate or (isinstance(current_profile_record, dict) and current_profile_record.get('profile_id') == 'anny-neutral-v4-proximal-barrier-v2')
    current_expected_fields = SKIN_BARRIER_FIELDS | ({'initialization'} if current_proximal_candidate else set())
    if not isinstance(current_profile_record, dict) or set(current_profile_record) != current_expected_fields:
        raise ValueError('ANNY 피부 충돌 제약 설정 필드 오류')
    current_fixed_fields = {'schema_version': 1, 'profile_id': 'anny-neutral-v4-skin-barrier-v1', 'target_rig': 'AnnyAttributesRig', 'target_mesh': 'AnnyAttributesBody', 'bone_prefixes': ['upperarm01', 'upperarm02', 'lowerarm01', 'lowerarm02', 'wrist'], 'adjacent_connections': 'excluded', 'collision_scope': 'arm_hand_vs_torso_pelvis_legs', 'approval_status': 'accepted_with_replay_warnings'}
    if current_proximal_candidate:
        current_fixed_fields.update(profile_id='anny-neutral-v4-proximal-barrier-v2', bone_prefixes=['clavicle', 'shoulder01', 'upperarm01', 'upperarm02', 'lowerarm01', 'lowerarm02', 'wrist'], approval_status='candidate', initialization='bilateral_rest_to_lateral_first_clear')
    if current_temporal_candidate:
        current_fixed_fields.update(profile_id='anny-neutral-v4-temporal-barrier-v3', initialization='previous_pose_with_lateral_collision_repair')
    if current_adjacency_candidate:
        current_fixed_fields.update(profile_id='anny-neutral-v4-adjacency-barrier-v4', adjacent_connections='upperarm_upper_spine_five_hops')
    if type(current_profile_record['schema_version']) is not int or any(current_profile_record[current_field_name] != current_field_value for current_field_name, current_field_value in current_fixed_fields.items()):
        raise ValueError('ANNY 피부 제약 대상·순서·승인 범위 계약 오류')
    for current_field_name in ('angle_step_degrees', 'minimum_surface_clearance_m'):
        current_field_value = current_profile_record[current_field_name]
        if type(current_field_value) not in (int, float) or not math.isfinite(current_field_value) or current_field_value <= 0:
            raise ValueError('피부 제약 수치 파라미터는 유한한 양수여야 합니다.')
    if current_profile_record['angle_step_degrees'] > 180:
        raise ValueError('회전 탐색 간격은 180도 이하여야 합니다.')
    for current_field_name, current_minimum_value, current_maximum_value in (('boundary_refinements', 0, 24), ('audit_substeps', 1, 16)):
        current_field_value = current_profile_record[current_field_name]
        if type(current_field_value) is not int or not current_minimum_value <= current_field_value <= current_maximum_value:
            raise ValueError('피부 제약 세분화 파라미터 범위 오류')
    return current_profile_record
