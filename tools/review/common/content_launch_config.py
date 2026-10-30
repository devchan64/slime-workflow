"""관리 실행기에서 DB 연결 경로를 읽는다. 인증값은 별도 비밀 파일에 둔다."""
import os
from pathlib import Path
from urllib.parse import urlsplit
import yaml
from tools.review.common.management_environment import validate_gateway_address, WORKFLOW_ROOT_DIRECTORY

DEFAULT_CONTENT_CONFIG_PATH = WORKFLOW_ROOT_DIRECTORY/'.local/content/connection.yaml'

CONTENT_CONFIG_ENVIRONMENT_FIELDS = {
    'serviceOrigin': 'SLIME_CONTENT_SERVICE_ORIGIN',
    'secretFile': 'SLIME_CONTENT_SERVICE_SECRET_FILE',
    'assetRoot': 'SLIME_ASSETS_ROOT',
    'snapshotRoot': 'SLIME_CONTENT_SNAPSHOT_ROOT',
    'gatewayOrigin': 'SLIME_MANAGEMENT_GATEWAY_URL',
}


class UniqueContentConfigLoader(yaml.SafeLoader):
    pass


def construct_unique_content_mapping(current_yaml_loader, current_mapping_node, deep=False):
    current_mapping_values = {}
    for current_key_node, current_value_node in current_mapping_node.value:
        current_key_value = current_yaml_loader.construct_object(current_key_node, deep=deep)
        if not isinstance(current_key_value, str) or current_key_value in current_mapping_values:
            raise ValueError('콘텐츠 연결 설정에 문자열이 아닌 키 또는 중복 키가 있습니다.')
        current_mapping_values[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=deep)
    return current_mapping_values


UniqueContentConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_content_mapping)


def read_content_launch_environment(current_config_path):
    current_config_record = yaml.load(Path(current_config_path).read_text(), Loader=UniqueContentConfigLoader)
    if not isinstance(current_config_record, dict) or set(current_config_record) not in (set(CONTENT_CONFIG_ENVIRONMENT_FIELDS), set(CONTENT_CONFIG_ENVIRONMENT_FIELDS)-{'secretFile'}):
        raise ValueError('콘텐츠 연결 설정 필드: ' + ', '.join(CONTENT_CONFIG_ENVIRONMENT_FIELDS))
    if any(not isinstance(current_field_value, str) or not current_field_value.strip() for current_field_value in current_config_record.values()):
        raise ValueError('콘텐츠 연결 설정 값은 비어 있지 않은 문자열이어야 합니다.')
    current_origin_parts = urlsplit(current_config_record['serviceOrigin'])
    if (current_origin_parts.scheme not in ('http', 'https') or not current_origin_parts.hostname
            or current_origin_parts.username or current_origin_parts.password
            or current_origin_parts.path not in ('', '/') or current_origin_parts.query or current_origin_parts.fragment
            or (current_origin_parts.scheme == 'http' and current_origin_parts.hostname not in ('localhost', '127.0.0.1', '::1'))):
        raise ValueError('콘텐츠 API 주소는 외부 HTTPS 또는 로컬 HTTP origin이어야 합니다.')
    validate_gateway_address(current_config_record['gatewayOrigin'])
    if 'secretFile' not in current_config_record and current_origin_parts.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('원격 콘텐츠 API에는 secretFile이 필요합니다.')
    for current_path_field in ('assetRoot', 'snapshotRoot', *(('secretFile',) if 'secretFile' in current_config_record else ())):
        if not Path(current_config_record[current_path_field]).is_absolute():
            raise ValueError('콘텐츠 연결 경로는 절대 경로여야 합니다: ' + current_path_field)
    if 'secretFile' in current_config_record and not Path(current_config_record['secretFile']).is_file():
        raise ValueError('콘텐츠 인증 파일이 없습니다.')
    if not Path(current_config_record['assetRoot']).is_dir():
        raise ValueError('에셋 원본 디렉터리가 없습니다.')
    return {'SLIME_CONTENT_STORAGE': 'database', **{
        current_environment_name: current_config_record.get(current_field_name, '')
        for current_field_name, current_environment_name in CONTENT_CONFIG_ENVIRONMENT_FIELDS.items()}}


def apply_content_launch_configuration():
    current_config_path = os.environ.get('SLIME_CONTENT_CONFIG_FILE')
    if current_config_path is None and DEFAULT_CONTENT_CONFIG_PATH.is_file():
        current_config_path = DEFAULT_CONTENT_CONFIG_PATH
    if current_config_path:
        current_environment_values = read_content_launch_environment(current_config_path)
        os.environ.update(current_environment_values)
