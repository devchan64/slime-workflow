"""Kimodo의 고정 모델·입력·준비 상태 계약."""
import hashlib
import json
import math
import re
from pathlib import Path
import yaml

KIMODO_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
KIMODO_MODEL_ROOT = KIMODO_WORKSPACE_ROOT / '.model/kimodo'
KIMODO_SOURCE_ROOT = KIMODO_WORKSPACE_ROOT / '.local/kimodo/upstream'
KIMODO_JOB_STORAGE = KIMODO_WORKSPACE_ROOT / '.tmp/test/kimodo'
KIMODO_ENVIRONMENT_PYTHON = KIMODO_WORKSPACE_ROOT / '.venv-kimodo/bin/python'
KIMODO_CONFIG_ROOT = Path(__file__).parent / 'config'

class UniqueConfigLoader(yaml.SafeLoader):
    """중복 설정 키를 거절한다."""

def construct_unique_mapping(current_yaml_loader, current_yaml_node, current_deep_value=False):
    current_mapping_result = {}
    for current_key_node, current_value_node in current_yaml_node.value:
        current_key_value = current_yaml_loader.construct_object(current_key_node, deep=current_deep_value)
        if current_key_value in current_mapping_result:
            raise ValueError(f'중복 설정 키: {current_key_value}')
        current_mapping_result[current_key_value] = current_yaml_loader.construct_object(current_value_node, deep=current_deep_value)
    return current_mapping_result

UniqueConfigLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)
KIMODO_ASSET_CONFIG = yaml.load((KIMODO_CONFIG_ROOT / 'assets.yaml').read_text(), Loader=UniqueConfigLoader)
KIMODO_DEFAULT_SETTINGS = yaml.load((KIMODO_CONFIG_ROOT / 'defaults.yaml').read_text(), Loader=UniqueConfigLoader)
if not isinstance(KIMODO_ASSET_CONFIG,dict) or set(KIMODO_ASSET_CONFIG) != {'source_revision','models'} or not re.fullmatch(r'[a-f0-9]{40}',KIMODO_ASSET_CONFIG['source_revision']):
    raise ValueError('Kimodo 자료 설정 계약 오류')
if not isinstance(KIMODO_ASSET_CONFIG['models'],list) or len(KIMODO_ASSET_CONFIG['models']) != 2:
    raise ValueError('Kimodo 모델 구성은 모션·인코더 2개여야 합니다.')
for current_asset_record in KIMODO_ASSET_CONFIG['models']:
    if not isinstance(current_asset_record,dict) or set(current_asset_record) != {'role','repository','revision','files'} or not re.fullmatch(r'[a-f0-9]{40}',current_asset_record['revision']):
        raise ValueError('Kimodo 모델 리비전 설정 오류')
    if not isinstance(current_asset_record['repository'],str) or not isinstance(current_asset_record['files'],list) or not current_asset_record['files']:
        raise ValueError('Kimodo 저장소·파일 목록 설정 오류')
    current_seen_paths = set()
    for current_file_record in current_asset_record['files']:
        if not isinstance(current_file_record,dict) or set(current_file_record) != {'path','size','sha256'}:
            raise ValueError('Kimodo 자료 파일 설정 오류')
        current_file_name = current_file_record['path']
        if not isinstance(current_file_name,str) or Path(current_file_name).is_absolute() or '..' in Path(current_file_name).parts or current_file_name in current_seen_paths:
            raise ValueError('Kimodo 자료 경로 오류')
        current_seen_paths.add(current_file_name)
        if type(current_file_record['size']) is not int or current_file_record['size'] <= 0 or (current_file_record['sha256'] is not None and not re.fullmatch(r'[a-f0-9]{64}',current_file_record['sha256'])):
            raise ValueError('Kimodo 자료 크기·해시 설정 오류')
if {current_asset_record['role'] for current_asset_record in KIMODO_ASSET_CONFIG['models']} != {'motion','encoder'}:
    raise ValueError('Kimodo 모델 역할 설정 오류')
if set(KIMODO_DEFAULT_SETTINGS) != {'schema_version','prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing','directions'} or KIMODO_DEFAULT_SETTINGS['schema_version'] != 1:
    raise ValueError('Kimodo 기본 설정 계약 오류')


KIMODO_DIRECTION_CONFIG = yaml.load((KIMODO_CONFIG_ROOT/'output-directions.yaml').read_text(),Loader=UniqueConfigLoader)
if not isinstance(KIMODO_DIRECTION_CONFIG,dict) or set(KIMODO_DIRECTION_CONFIG)!={'schema_version','directions'} or KIMODO_DIRECTION_CONFIG['schema_version']!=1:
    raise ValueError('출력 방향 설정 계약 오류')
KIMODO_DIRECTION_RECORDS = KIMODO_DIRECTION_CONFIG['directions']
if not isinstance(KIMODO_DIRECTION_RECORDS,dict) or set(KIMODO_DIRECTION_RECORDS)!={'front','front_left','left','back_left','back','back_right','right','front_right'}:
    raise ValueError('출력 방향 목록 오류')
for current_direction_record in KIMODO_DIRECTION_RECORDS.values():
    if not isinstance(current_direction_record,dict) or set(current_direction_record)!={'label','angle'} or not isinstance(current_direction_record['label'],str) or not current_direction_record['label'] or type(current_direction_record['angle']) is not int or not -180<=current_direction_record['angle']<=180:
        raise ValueError('출력 방향 라벨·각도 오류')


def validate_kimodo_directions(current_direction_names):
    if not isinstance(current_direction_names,list) or not current_direction_names or any(not isinstance(current_direction_name,str) or current_direction_name not in KIMODO_DIRECTION_RECORDS for current_direction_name in current_direction_names) or len(set(current_direction_names))!=len(current_direction_names):
        raise ValueError('출력 방향을 중복 없이 한 개 이상 선택하세요.')
    return list(current_direction_names)

validate_kimodo_directions(KIMODO_DEFAULT_SETTINGS['directions'])


def validate_kimodo_request(current_request_record):
    current_required_fields = {'action','prompt','frames','steps','seed','guidance_scale','heading_degrees','post_processing'}
    if not isinstance(current_request_record, dict) or set(current_request_record) not in (current_required_fields,current_required_fields|{'directions'}):
        raise ValueError('Kimodo 요청 필드 오류')
    if current_request_record['action'] != 'generate':
        raise ValueError('generate 명령만 지원합니다.')
    current_prompt_text = current_request_record['prompt']
    if not isinstance(current_prompt_text, str) or not current_prompt_text.strip() or len(current_prompt_text) > 2000 or len(current_prompt_text.split()) > 100:
        raise ValueError('프롬프트는 1~100단어, 2000자 이내로 입력하세요.')
    if not any(current_character_value.isalnum() for current_character_value in current_prompt_text):
        raise ValueError('프롬프트에 문자 또는 숫자가 필요합니다.')
    for current_field_name, current_minimum_value, current_maximum_value in [('frames',30,300),('steps',2,100),('seed',0,2147483647)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) is not int or not current_minimum_value <= current_field_value <= current_maximum_value:
            raise ValueError(f'{current_field_name}: {current_minimum_value}~{current_maximum_value} 정수 필요')
    for current_field_name, current_minimum_value, current_maximum_value in [('guidance_scale',0,10),('heading_degrees',-180,180)]:
        current_field_value = current_request_record[current_field_name]
        if type(current_field_value) not in (float,int) or not math.isfinite(current_field_value) or not current_minimum_value <= current_field_value <= current_maximum_value:
            raise ValueError(f'{current_field_name}: 범위 오류')
    if type(current_request_record['post_processing']) is not bool:
        raise ValueError('후처리 여부는 참/거짓이어야 합니다.')
    return {**current_request_record, 'directions':validate_kimodo_directions(current_request_record.get('directions',['front_left'])), 'prompt':current_prompt_text.strip(), 'images':[], 'width':512, 'height':512, 'tag':'kimodo'}


def inspect_kimodo_assets():
    current_missing_paths = []
    for current_asset_record in KIMODO_ASSET_CONFIG['models']:
        for current_file_record in current_asset_record['files']:
            current_file_path = KIMODO_MODEL_ROOT / current_asset_record['role'] / current_file_record['path']
            if not current_file_path.is_file() or current_file_path.stat().st_size != current_file_record['size']:
                current_missing_paths.append(str(current_file_path))
    current_revision_path = KIMODO_SOURCE_ROOT.parent / 'PINNED_REVISION'
    if not current_revision_path.is_file() or current_revision_path.read_text().strip() != KIMODO_ASSET_CONFIG['source_revision']:
        current_missing_paths.append(str(current_revision_path))
    for current_required_path in (KIMODO_ENVIRONMENT_PYTHON, KIMODO_MODEL_ROOT/'prepared.json'):
        if not current_required_path.is_file():
            current_missing_paths.append(str(current_required_path))
    current_prepared_path = KIMODO_MODEL_ROOT/'prepared.json'
    if current_prepared_path.is_file():
        try:
            current_prepared_record = json.loads(current_prepared_path.read_text())
            if current_prepared_record.get('source_revision') != KIMODO_ASSET_CONFIG['source_revision'] or current_prepared_record.get('models') != KIMODO_ASSET_CONFIG['models']:
                current_missing_paths.append('준비 기록의 모델 리비전 불일치')
        except (ValueError,AttributeError):
            current_missing_paths.append('준비 기록 형식 오류')
    return {'ready':not current_missing_paths,'missing':current_missing_paths,'message':'Kimodo SOMA v1.2 · NF4 파일 준비 완료 · 실행·품질은 별도 검수' if not current_missing_paths else '준비 필요: '+', '.join(current_missing_paths[:3])}


def validate_kimodo_assets():
    current_asset_status = inspect_kimodo_assets()
    if not current_asset_status['ready']:
        raise ValueError(current_asset_status['message'])


def verify_kimodo_weights():
    validate_kimodo_assets()
    for current_asset_record in KIMODO_ASSET_CONFIG['models']:
        for current_file_record in current_asset_record['files']:
            if current_file_record['sha256']:
                current_file_path = KIMODO_MODEL_ROOT/current_asset_record['role']/current_file_record['path']
                with current_file_path.open('rb') as current_file_stream:
                    if hashlib.file_digest(current_file_stream,'sha256').hexdigest() != current_file_record['sha256']:
                        raise ValueError(f'모델 해시 불일치: {current_file_path}')


def normalize_kimodo_prompt(current_prompt_text):
    """고정 공식 소스의 문장 정규화를 UI와 실행기가 공유한다."""
    import importlib.util
    current_source_path = KIMODO_SOURCE_ROOT/'kimodo/sanitize.py'
    current_module_spec = importlib.util.spec_from_file_location('kimodo_prompt_sanitizer',current_source_path)
    current_module_value = importlib.util.module_from_spec(current_module_spec)
    current_module_spec.loader.exec_module(current_module_value)
    if not any(current_character_value.isalnum() for current_character_value in current_prompt_text):
        raise ValueError('프롬프트에 문자 또는 숫자가 필요합니다.')
    return current_module_value.sanitize_text(current_prompt_text)
