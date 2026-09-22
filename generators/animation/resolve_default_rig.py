"""기본 걷기 리그를 해시 검증 후 해석한다. 생성이나 GPU 추론은 수행하지 않는다."""
from pathlib import Path
import hashlib
import json
import time
import traceback
import yaml

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = WORKFLOW_ROOT_PATH / 'generators/animation/config/default_walk_rig.yaml'


class UniqueConfigLoader(yaml.SafeLoader):
    """중복 YAML 필드를 허용하지 않는다."""


def construct_unique_mapping(loader_instance_value, mapping_node_value, deep_load_enabled=False):
    parsed_mapping_values = {}
    for key_node_value, value_node_value in mapping_node_value.value:
        parsed_key_value = loader_instance_value.construct_object(key_node_value, deep=deep_load_enabled)
        if parsed_key_value in parsed_mapping_values:
            raise ValueError(f'중복 설정 필드: {parsed_key_value}')
        parsed_mapping_values[parsed_key_value] = loader_instance_value.construct_object(value_node_value, deep=deep_load_enabled)
    return parsed_mapping_values


UniqueConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def resolve_default_walk_rig():
    default_config_values = yaml.load(DEFAULT_CONFIG_PATH.read_text(), Loader=UniqueConfigLoader)
    if not isinstance(default_config_values, dict) or set(default_config_values) != {'asset_id', 'version', 'artifact_sha256'}:
        raise ValueError('기본 리그 설정 필드 불일치')
    if default_config_values['asset_id'] != 'mannequin-walk' or type(default_config_values['version']) is not int or default_config_values['version'] < 1:
        raise ValueError('기본 리그 식별자·버전 오류')
    expected_manifest_hash = default_config_values['artifact_sha256']
    if not isinstance(expected_manifest_hash, str) or len(expected_manifest_hash) != 64 or any(character not in '0123456789abcdef' for character in expected_manifest_hash):
        raise ValueError('기본 리그 SHA-256 형식 오류')
    resolved_asset_directory = WORKFLOW_ROOT_PATH / 'assets/rigs' / default_config_values['asset_id']
    if default_config_values['asset_id'] != 'mannequin-walk':
        resolved_asset_directory = resolved_asset_directory / f"v{default_config_values['version']}"
    resolved_manifest_path = resolved_asset_directory / 'artifact.json'
    if hashlib.sha256(resolved_manifest_path.read_bytes()).hexdigest() != expected_manifest_hash:
        raise ValueError('기본 리그 manifest 해시 불일치')
    resolved_manifest_values = json.loads(resolved_manifest_path.read_text())
    if resolved_manifest_values['asset_id'] != default_config_values['asset_id'] or resolved_manifest_values['version'] != default_config_values['version']:
        raise ValueError('기본 리그 manifest 식별자 불일치')
    for artifact_file_name in ['mannequin.blend', 'mannequin-motion.npz']:
        if hashlib.sha256((resolved_asset_directory / artifact_file_name).read_bytes()).hexdigest() != resolved_manifest_values['files'][artifact_file_name]:
            raise ValueError(f'기본 리그 파일 해시 불일치: {artifact_file_name}')
    return resolved_asset_directory


if __name__ == '__main__':
    execution_log_path = WORKFLOW_ROOT_PATH / '.result/workflow/logs/default-walk-rig.log'
    execution_log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resolved_rig_directory = resolve_default_walk_rig()
        execution_log_message = f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/default-walk-rig/resolve {resolved_rig_directory}\n'
    except Exception:
        execution_log_message = f'{time.strftime("%Y-%m-%dT%H:%M:%S%z")}/default-walk-rig/failure {traceback.format_exc()}\n'
        with execution_log_path.open('a') as execution_log_handle:
            execution_log_handle.write(execution_log_message)
        print(execution_log_message, end='')
        raise
    with execution_log_path.open('a') as execution_log_handle:
        execution_log_handle.write(execution_log_message)
    print(execution_log_message, end='')
