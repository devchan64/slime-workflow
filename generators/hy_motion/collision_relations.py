"""충돌 허용 관계의 수정 가능한 원본과 엄격한 검증."""
from pathlib import Path
import hashlib
import yaml
from generators.hy_motion.contracts import UniqueConfigLoader

COLLISION_RELATIONS_PATH = Path(__file__).parent / 'config/collision-relations.yaml'


def load_collision_relations(current_profile_path=COLLISION_RELATIONS_PATH):
    current_profile_bytes = Path(current_profile_path).read_bytes()
    current_profile_record = yaml.load(current_profile_bytes, Loader=UniqueConfigLoader)
    if not isinstance(current_profile_record, dict) or set(current_profile_record) != {'schema_version', 'profile_id', 'default_policy', 'rules', 'pair_overrides'}:
        raise ValueError('충돌 관계 설정 필드 오류')
    if type(current_profile_record['schema_version']) is not int or current_profile_record['schema_version'] != 1 or current_profile_record['default_policy'] != 'check' or not isinstance(current_profile_record['profile_id'], str) or not current_profile_record['profile_id'].strip():
        raise ValueError('충돌 관계 버전·기본 정책 오류')
    current_rule_identifiers = set()
    current_override_pairs = set()
    for current_section_name in ('rules', 'pair_overrides'):
        if not isinstance(current_profile_record[current_section_name], list):
            raise ValueError('충돌 관계 목록 형식 오류')
        for current_rule_record in current_profile_record[current_section_name]:
            current_expected_fields = {'id', 'arm_bones', 'body_bones', 'maximum_hops', 'policy', 'reason'} if current_section_name == 'rules' else {'arm_bone', 'body_bone', 'policy', 'reason'}
            if not isinstance(current_rule_record, dict) or set(current_rule_record) != current_expected_fields:
                raise ValueError('충돌 관계 규칙 필드 오류')
            if current_rule_record['policy'] not in ('allow', 'check') or not isinstance(current_rule_record['reason'], str) or not current_rule_record['reason'].strip():
                raise ValueError('충돌 관계 정책·사유 오류')
            if current_section_name == 'rules':
                current_rule_identifier = current_rule_record['id']
                if not isinstance(current_rule_identifier, str) or not current_rule_identifier or current_rule_identifier in current_rule_identifiers:
                    raise ValueError('충돌 관계 규칙 ID 중복·형식 오류')
                current_rule_identifiers.add(current_rule_identifier)
                if type(current_rule_record['maximum_hops']) is not int or current_rule_record['maximum_hops'] < 1:
                    raise ValueError('최대 인접 간선 수 오류')
                for current_field_name in ('arm_bones', 'body_bones'):
                    current_bone_names = current_rule_record[current_field_name]
                    if not isinstance(current_bone_names, list) or not current_bone_names or any(not isinstance(current_bone_name, str) or not current_bone_name for current_bone_name in current_bone_names) or len(set(current_bone_names)) != len(current_bone_names):
                        raise ValueError('본 목록 형식·중복 오류')
            else:
                current_pair_names = (current_rule_record['arm_bone'], current_rule_record['body_bone'])
                if any(not isinstance(current_bone_name, str) or not current_bone_name for current_bone_name in current_pair_names) or current_pair_names[0] == current_pair_names[1] or current_pair_names in current_override_pairs:
                    raise ValueError('개별 본 쌍 중복·형식 오류')
                current_override_pairs.add(current_pair_names)
    return current_profile_record, hashlib.sha256(current_profile_bytes).hexdigest()
