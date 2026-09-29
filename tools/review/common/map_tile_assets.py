"""에셋 저장소에서 등록된 맵 타일 원본과 출처를 검증한다."""
import hashlib
import os
from pathlib import Path

import yaml

DEFAULT_ASSET_REPOSITORY = Path(__file__).resolve().parents[4] / 'slime-assets'


class UniqueAssetYamlLoader(yaml.SafeLoader):
    """등록부의 중복 키를 거절한다."""


def construct_unique_mapping(current_yaml_loader, current_mapping_node, deep=False):
    current_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_key_value = current_yaml_loader.construct_object(current_key_node, deep=deep)
        if current_key_value in current_mapping_values:
            raise ValueError(f'에셋 등록부 중복 키: {current_key_value}')
        current_mapping_values[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=deep)
    return current_mapping_values


UniqueAssetYamlLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def load_registered_tiles():
    asset_repository_path = Path(os.environ.get('SLIME_ASSETS_ROOT', DEFAULT_ASSET_REPOSITORY)).resolve()
    asset_registry_record = yaml.load((asset_repository_path / 'asset-registry.yaml').read_text(), Loader=UniqueAssetYamlLoader)
    if not isinstance(asset_registry_record, dict) or set(asset_registry_record) != {'schema_version', 'assets'} or asset_registry_record['schema_version'] != 1 or not isinstance(asset_registry_record['assets'], list):
        raise ValueError('에셋 등록부 형식 오류')
    registered_tile_records = {}
    registered_version_pairs = set()
    required_asset_fields = {'managementId', 'version', 'path', 'sha256', 'source'}
    optional_asset_fields = {'frontend_path', 'name', 'width', 'height', 'license'}
    for current_asset_record in asset_registry_record['assets']:
        if not isinstance(current_asset_record, dict) or not required_asset_fields <= current_asset_record.keys() or current_asset_record.keys() - required_asset_fields - optional_asset_fields:
            raise ValueError('에셋 등록 항목 필드 오류')
        if any(not isinstance(current_asset_record[current_field_name], str) or not current_asset_record[current_field_name] for current_field_name in ('managementId', 'version', 'path', 'sha256')) or not isinstance(current_asset_record['source'], dict):
            raise ValueError('에셋 등록 항목 자료형 오류')
        current_version_pair = (current_asset_record['managementId'], current_asset_record['version'])
        if current_version_pair in registered_version_pairs or current_asset_record['path'] in registered_tile_records:
            raise ValueError('에셋 ID·버전 또는 경로 중복')
        registered_version_pairs.add(current_version_pair)
        registered_tile_records[current_asset_record['path']] = current_asset_record
    return asset_repository_path, registered_tile_records


def resolve_registered_asset(asset_relative_path, asset_repository_path, registered_tile_records, asset_directory_prefix):
    if not isinstance(asset_relative_path, str) or not asset_relative_path.startswith(asset_directory_prefix+'/') or '..' in Path(asset_relative_path).parts:
        raise ValueError(f'맵 타일 원본 경로 오류: {asset_relative_path}')
    if asset_relative_path not in registered_tile_records:
        raise ValueError(f'미등록 맵 타일: {asset_relative_path}')
    current_asset_record = registered_tile_records[asset_relative_path]
    source_texture_path = (asset_repository_path / asset_relative_path).resolve()
    if not source_texture_path.is_relative_to(asset_repository_path / asset_directory_prefix):
        raise ValueError('맵 타일 원본이 에셋 경로 밖에 있습니다.')
    current_asset_digest = hashlib.sha256(source_texture_path.read_bytes()).hexdigest()
    if current_asset_digest != current_asset_record['sha256']:
        raise ValueError(f'맵 타일 원본 해시 불일치: {asset_relative_path}')
    return source_texture_path, {'repository': 'slime-assets', 'source': asset_relative_path, 'managementId': current_asset_record['managementId'], 'version': current_asset_record['version'], 'sha256': current_asset_digest}


def resolve_registered_tile(asset_relative_path, asset_repository_path, registered_tile_records):
    return resolve_registered_asset(asset_relative_path, asset_repository_path, registered_tile_records, 'assets/tiles')


def resolve_registered_sprite(asset_relative_path):
    asset_repository_path, registered_asset_records = load_registered_tiles()
    return resolve_registered_asset(asset_relative_path, asset_repository_path, registered_asset_records, 'assets/sprites')
