"""음악생성의 고정 모델·요청·준비 산출물 계약."""
import hashlib
import json
import math
from pathlib import Path
import re
import yaml
from tools.review.common.generation_records import validate_history_tag

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
MUSIC_DEFAULTS_FILE = Path(__file__).with_name('defaults.yaml')
MUSIC_SERVICE_NAMES = ('music-ace-step', 'music-minimax')
MUSIC_IDENTIFIER_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'
MUSIC_PROFILE_FIELDS = {'label','model_id','runtime_directory','max_duration_seconds','sample_rate','steps','license_url','license_notice'}
MUSIC_REQUEST_FIELDS = {'action','prompt','duration_seconds','seed','loop_request','tag'}


def parse_unique_mapping(current_field_pairs):
    current_output_record = {}
    for current_field_name, current_field_value in current_field_pairs:
        if current_field_name in current_output_record:
            raise ValueError(f'중복 필드: {current_field_name}')
        current_output_record[current_field_name] = current_field_value
    return current_output_record


class MusicDefaultsLoader(yaml.SafeLoader):
    """중복 키를 거부하는 YAML 로더."""


def construct_unique_mapping(current_yaml_loader, current_yaml_node):
    return parse_unique_mapping([(current_yaml_loader.construct_object(current_key_node), current_yaml_loader.construct_object(current_value_node)) for current_key_node, current_value_node in current_yaml_node.value])


MusicDefaultsLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)


def read_music_record(current_record_path):
    return json.loads(current_record_path.read_text(), object_pairs_hook=parse_unique_mapping)


def load_music_defaults():
    current_default_record = yaml.load(MUSIC_DEFAULTS_FILE.read_text(), Loader=MusicDefaultsLoader)
    if not isinstance(current_default_record,dict) or set(current_default_record) != {'version','prompt','duration_seconds','seed','loop_request','instrumental_suffix','loop_suffix','profiles'} or type(current_default_record['version']) is not int or current_default_record['version'] != 1:
        raise ValueError('음악 기본 설정 스키마 오류')
    if set(current_default_record['profiles']) != set(MUSIC_SERVICE_NAMES):
        raise ValueError('음악 모델 설정 목록 오류')
    for current_service_name, current_profile_record in current_default_record['profiles'].items():
        if set(current_profile_record) != MUSIC_PROFILE_FIELDS:
            raise ValueError(f'모델 설정 필드 오류: {current_service_name}')
        for current_field_name in MUSIC_PROFILE_FIELDS - {'max_duration_seconds','sample_rate','steps'}:
            if not isinstance(current_profile_record[current_field_name], str) or not current_profile_record[current_field_name]:
                raise ValueError(f'모델 문자열 설정 오류: {current_field_name}')
        for current_field_name in ('max_duration_seconds','sample_rate','steps'):
            if type(current_profile_record[current_field_name]) is not int or current_profile_record[current_field_name] <= 0:
                raise ValueError(f'모델 수치 설정 오류: {current_field_name}')
        if not re.fullmatch(r'\.venv-music-[a-z]+',current_profile_record['runtime_directory']):
            raise ValueError('음악 실행 환경 경로 오류')
    for current_field_name in ('prompt','instrumental_suffix','loop_suffix'):
        if not isinstance(current_default_record[current_field_name],str):
            raise ValueError('기본 프롬프트는 문자열이어야 합니다.')
    if type(current_default_record['loop_request']) is not bool or type(current_default_record['seed']) is not int or not 0 <= current_default_record['seed'] <= 2**32-1 or type(current_default_record['duration_seconds']) is not int or not 5 <= current_default_record['duration_seconds'] <= 60:
        raise ValueError('기본 길이·시드·반복 요청 설정 오류')
    return current_default_record


def resolve_music_profile(current_service_name):
    if current_service_name not in MUSIC_SERVICE_NAMES:
        raise ValueError('지원하지 않는 음악 생성기')
    return load_music_defaults()['profiles'][current_service_name]


def resolve_music_paths(current_service_name):
    current_profile_record = resolve_music_profile(current_service_name)
    return (WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/current_service_name,
            WORKFLOW_ROOT_DIRECTORY/'.model/music'/current_service_name,
            WORKFLOW_ROOT_DIRECTORY/current_profile_record['runtime_directory']/'bin/python')


def validate_music_request(current_service_name, current_request_record):
    if not isinstance(current_request_record,dict) or set(current_request_record) - MUSIC_REQUEST_FIELDS:
        raise ValueError('음악 요청의 알 수 없는 필드 또는 객체 형식 오류')
    current_action_name = current_request_record.get('action','generate')
    if current_action_name == 'prepare':
        if set(current_request_record) != {'action'}:
            raise ValueError('모델 준비에는 다른 입력을 지정할 수 없습니다.')
        return {'action':'prepare'}
    if current_action_name != 'generate':
        raise ValueError('지원하지 않는 음악 작업')
    current_default_record = load_music_defaults()
    current_profile_record = resolve_music_profile(current_service_name)
    current_prompt_text = current_request_record.get('prompt')
    if not isinstance(current_prompt_text,str) or not current_prompt_text.strip() or len(current_prompt_text) > 4000 or '\x00' in current_prompt_text:
        raise ValueError('음악 프롬프트는 비어 있지 않은 4000자 이하 문자열이어야 합니다.')
    current_seed_value = current_request_record.get('seed',current_default_record['seed'])
    current_duration_value = current_request_record.get('duration_seconds',current_default_record['duration_seconds'])
    current_loop_value = current_request_record.get('loop_request',current_default_record['loop_request'])
    if type(current_seed_value) is not int or not 0 <= current_seed_value <= 2**32-1:
        raise ValueError('시드는 0~4294967295 정수여야 합니다.')
    if type(current_duration_value) not in (int,float) or not math.isfinite(current_duration_value) or not 5 <= current_duration_value <= current_profile_record['max_duration_seconds']:
        raise ValueError(f"길이는 5~{current_profile_record['max_duration_seconds']}초여야 합니다.")
    if type(current_loop_value) is not bool:
        raise ValueError('반복 구조 요청은 bool이어야 합니다.')
    return {'action':'generate','prompt':current_prompt_text.strip(),'duration_seconds':float(current_duration_value),'seed':current_seed_value,'loop_request':current_loop_value,'tag':validate_history_tag(current_request_record.get('tag',''))}


def build_music_request(current_service_name, current_payload_record):
    current_input_record = validate_music_request(current_service_name,current_payload_record)
    current_default_record = load_music_defaults()
    current_final_prompt = ''
    if current_input_record['action'] == 'generate':
        current_final_prompt = current_input_record['prompt']+' '+current_default_record['instrumental_suffix']
        if current_input_record['loop_request']:
            current_final_prompt += ' '+current_default_record['loop_suffix']
    return {**current_input_record,'service':current_service_name,'model_id':resolve_music_profile(current_service_name)['model_id'],
            'final_prompt':current_final_prompt,'prompt_words':len(current_input_record.get('prompt','').split()),
            'final_prompt_words':len(current_final_prompt.split()),'prompt_sha256':hashlib.sha256(current_final_prompt.encode()).hexdigest(),
            'defaults_sha256':hashlib.sha256(MUSIC_DEFAULTS_FILE.read_bytes()).hexdigest()}


def verify_music_request(current_service_name, current_saved_record):
    current_rebuilt_record = build_music_request(current_service_name,{current_field_name:current_field_value for current_field_name,current_field_value in current_saved_record.items() if current_field_name in MUSIC_REQUEST_FIELDS})
    if current_rebuilt_record != current_saved_record:
        raise ValueError('저장된 음악 요청·고정 설정·프롬프트 해시 불일치; 새 작업으로 등록하세요.')
    return current_saved_record


def validate_music_identifier(current_identifier_value):
    if not isinstance(current_identifier_value,str) or not re.fullmatch(MUSIC_IDENTIFIER_PATTERN,current_identifier_value):
        raise ValueError('음악 생성 ID 형식 오류')
    return current_identifier_value
