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
MUSIC_SERVICE_NAMES = ('music-minimax', 'music-magenta', 'music-heartmula')
MAGENTA_DEFAULTS_FILE = Path(__file__).with_name('magenta_defaults.yaml')
SOUND_EFFECT_SERVICE = 'sfx-dasheng-audiogen'
AUDIO_SERVICE_NAMES = (*MUSIC_SERVICE_NAMES, SOUND_EFFECT_SERVICE)
SOUND_EFFECT_DEFAULTS = WORKFLOW_ROOT_DIRECTORY/'generators/sound_effects/defaults.yaml'
MUSIC_IDENTIFIER_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'
MUSIC_PROFILE_FIELDS = {'label','model_id','runtime_directory','max_duration_seconds','sample_rate','steps','license_url','license_notice'}
MUSIC_REQUEST_FIELDS = {'action','prompt','lyrics','duration_seconds','max_new_tokens','min_duration_seconds','seed','loop_request','tag'}
MINIMAX_AUDIO_FRAME_RATE = 25
MINIMAX_MAXIMUM_AUDIO_FRAMES = 3000


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


def resolve_audio_defaults(current_service_name=None):
    if current_service_name is not None and current_service_name not in AUDIO_SERVICE_NAMES:
        raise ValueError('지원하지 않는 오디오 생성기')
    if current_service_name == 'music-heartmula':
        return Path(__file__).with_name('heartmula_defaults.yaml')
    if current_service_name == 'music-magenta':
        return MAGENTA_DEFAULTS_FILE
    return SOUND_EFFECT_DEFAULTS if current_service_name == SOUND_EFFECT_SERVICE else MUSIC_DEFAULTS_FILE


def resolve_audio_minimum(current_service_name):
    return 0.5 if current_service_name == SOUND_EFFECT_SERVICE else 5


def load_music_defaults(current_service_name=None):
    current_default_record = yaml.load(resolve_audio_defaults(current_service_name).read_text(), Loader=MusicDefaultsLoader)
    if not isinstance(current_default_record,dict) or set(current_default_record) != {'version','prompt','duration_seconds','seed','loop_request','instrumental_suffix','loop_suffix','profiles'} or type(current_default_record['version']) is not int or current_default_record['version'] != 1:
        raise ValueError('음악 기본 설정 스키마 오류')
    if not isinstance(current_default_record['profiles'],dict) or set(current_default_record['profiles']) != ({SOUND_EFFECT_SERVICE} if current_service_name == SOUND_EFFECT_SERVICE else {current_service_name} if current_service_name in ('music-magenta','music-heartmula') else {'music-minimax','music-ace-step'}):
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
        if not re.fullmatch(r'\.venv-(?:music|sfx)-[a-z]+',current_profile_record['runtime_directory']):
            raise ValueError('음악 실행 환경 경로 오류')
    for current_field_name in ('prompt','instrumental_suffix','loop_suffix'):
        if not isinstance(current_default_record[current_field_name],str):
            raise ValueError('기본 프롬프트는 문자열이어야 합니다.')
    if type(current_default_record['loop_request']) is not bool or type(current_default_record['seed']) is not int or not 0 <= current_default_record['seed'] <= 2**32-1:
        raise ValueError('기본 길이·시드·반복 요청 설정 오류')
    if current_service_name == SOUND_EFFECT_SERVICE:
        if current_default_record['duration_seconds'] is not None:
            raise ValueError('Dasheng 길이는 모델 자동 예측입니다.')
    elif type(current_default_record['duration_seconds']) is not int or not resolve_audio_minimum(current_service_name) <= current_default_record['duration_seconds'] <= 60:
        raise ValueError('기본 길이 설정 오류')
    # 기존 MiniMax 대기 요청의 설정 해시를 보존하되 폐기 모델은 노출하지 않는다.
    current_default_record['profiles'].pop('music-ace-step',None)
    return current_default_record


def resolve_music_profile(current_service_name):
    if current_service_name not in AUDIO_SERVICE_NAMES:
        raise ValueError('지원하지 않는 음악 생성기')
    current_profile_record = load_music_defaults(current_service_name)['profiles'][current_service_name]
    if current_service_name == 'music-minimax':
        # 기존 요청의 defaults_sha256 보존: 운영 상한은 기본 입력 파일과 분리한다.
        current_profile_record['max_duration_seconds'] = MINIMAX_MAXIMUM_AUDIO_FRAMES // MINIMAX_AUDIO_FRAME_RATE
    return current_profile_record


def resolve_music_paths(current_service_name):
    current_profile_record = resolve_music_profile(current_service_name)
    return (WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/current_service_name,
            WORKFLOW_ROOT_DIRECTORY/'.model/music'/current_service_name,
            WORKFLOW_ROOT_DIRECTORY/current_profile_record['runtime_directory']/'bin/python')


def convert_minimax_token_duration(current_token_limit):
    """토큰 상한을 기존 Diffusers 요청 단위로 변환한다. 반올림에 따른 프레임 손실을 방지한다."""
    current_minimum_tokens = int(resolve_audio_minimum('music-minimax') * MINIMAX_AUDIO_FRAME_RATE)
    current_maximum_tokens = resolve_music_profile('music-minimax')['max_duration_seconds'] * MINIMAX_AUDIO_FRAME_RATE
    if type(current_token_limit) is not int or not current_minimum_tokens <= current_token_limit <= current_maximum_tokens:
        raise ValueError(f'max_new_tokens는 {current_minimum_tokens}~{current_maximum_tokens} 정수여야 합니다.')
    current_duration_seconds = current_token_limit / MINIMAX_AUDIO_FRAME_RATE
    if int(current_duration_seconds * MINIMAX_AUDIO_FRAME_RATE) < current_token_limit:
        current_duration_seconds = math.nextafter(current_duration_seconds, math.inf)
    return current_duration_seconds


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
    current_default_record = load_music_defaults(current_service_name)
    current_profile_record = resolve_music_profile(current_service_name)
    current_prompt_text = current_request_record.get('prompt')
    if not isinstance(current_prompt_text,str) or not current_prompt_text.strip() or len(current_prompt_text) > 4000 or '\x00' in current_prompt_text:
        raise ValueError('음악 프롬프트는 비어 있지 않은 4000자 이하 문자열이어야 합니다.')
    if current_service_name == 'music-heartmula' and 'lyrics' not in current_request_record:
        raise ValueError('HeartMuLa lyrics를 직접 입력하세요. 공식적으로 보장된 무보컬 기본값은 없습니다.')
    current_lyrics_fields = {}
    if 'lyrics' in current_request_record:
        current_lyrics_text = current_request_record['lyrics']
        if current_service_name not in ('music-minimax','music-heartmula') or not isinstance(current_lyrics_text,str) or (current_service_name != 'music-heartmula' and not current_lyrics_text.strip()) or len(current_lyrics_text) > 20000 or '\x00' in current_lyrics_text:
            raise ValueError('lyrics는 20000자 이하 문자열이어야 합니다. 빈 문자열은 HeartMuLa 비교 실험에서만 허용합니다.')
        current_lyrics_fields['lyrics'] = current_lyrics_text
    current_seed_value = current_request_record.get('seed',current_default_record['seed'])
    current_duration_value = current_request_record.get('duration_seconds',current_default_record['duration_seconds'])
    if 'max_new_tokens' in current_request_record:
        if current_service_name != 'music-minimax':
            raise ValueError('max_new_tokens는 MiniMax 전용 입력입니다.')
        if 'duration_seconds' in current_request_record:
            raise ValueError('max_new_tokens와 duration_seconds는 하나만 지정하세요.')
        current_duration_value = convert_minimax_token_duration(current_request_record['max_new_tokens'])
    current_loop_value = current_request_record.get('loop_request',current_default_record['loop_request'])
    if type(current_seed_value) is not int or not 0 <= current_seed_value <= 2**32-1:
        raise ValueError('시드는 0~4294967295 정수여야 합니다.')
    if current_service_name == SOUND_EFFECT_SERVICE and current_duration_value is not None:
        raise ValueError('Dasheng-AudioGen은 요청 길이를 지원하지 않습니다. duration_seconds를 생략하세요.')
    if current_service_name != SOUND_EFFECT_SERVICE and (type(current_duration_value) not in (int,float) or not math.isfinite(current_duration_value) or not resolve_audio_minimum(current_service_name) <= current_duration_value <= current_profile_record['max_duration_seconds']):
        raise ValueError(f"길이는 {resolve_audio_minimum(current_service_name)}~{current_profile_record['max_duration_seconds']}초여야 합니다.")
    if current_service_name in ('music-magenta','music-heartmula') and current_loop_value:
        raise ValueError('Magenta 실험은 반복 요청을 지원하지 않습니다.')
    if type(current_loop_value) is not bool:
        raise ValueError('반복 구조 요청은 bool이어야 합니다.')
    current_minimum_seconds = current_request_record.get('min_duration_seconds',0)
    if type(current_minimum_seconds) not in (int,float) or not math.isfinite(current_minimum_seconds) or current_minimum_seconds < 0:
        raise ValueError('최소 길이는 0 이상의 유한한 초 값이어야 합니다.')
    if current_minimum_seconds and (current_service_name != 'music-minimax' or current_minimum_seconds > current_duration_value):
        raise ValueError('최소 길이는 MiniMax에서만 지원하며 최대 길이 이하여야 합니다.')
    return {**current_lyrics_fields,**({'min_duration_seconds':float(current_minimum_seconds)} if current_minimum_seconds else {}),'action':'generate','prompt':current_prompt_text.strip(),'duration_seconds':None if current_service_name == SOUND_EFFECT_SERVICE else float(current_duration_value),'seed':current_seed_value,'loop_request':current_loop_value,'tag':validate_history_tag(current_request_record.get('tag',''))}


def build_music_request(current_service_name, current_payload_record):
    current_input_record = validate_music_request(current_service_name,current_payload_record)
    current_default_record = load_music_defaults(current_service_name)
    current_final_prompt = ''
    if current_input_record['action'] == 'generate':
        current_final_prompt = current_input_record['prompt'] if 'lyrics' in current_input_record else current_input_record['prompt']+' '+current_default_record['instrumental_suffix']
        if current_service_name in (SOUND_EFFECT_SERVICE, 'music-magenta','music-heartmula'):
            current_final_prompt = current_final_prompt.strip()
        if current_input_record['loop_request']:
            current_final_prompt += ' '+current_default_record['loop_suffix']
        if current_service_name == SOUND_EFFECT_SERVICE:
            current_final_prompt = '<|caption|> '+current_final_prompt.strip()
    return {**current_input_record,'service':current_service_name,'model_id':resolve_music_profile(current_service_name)['model_id'],
            'final_prompt':current_final_prompt,'prompt_words':len(current_input_record.get('prompt','').split()),
            'final_prompt_words':len(current_final_prompt.split()),'prompt_sha256':hashlib.sha256(current_final_prompt.encode()).hexdigest(),
            'defaults_sha256':hashlib.sha256(resolve_audio_defaults(current_service_name).read_bytes()).hexdigest()}


def verify_music_request(current_service_name, current_saved_record):
    current_rebuilt_record = build_music_request(current_service_name,{current_field_name:current_field_value for current_field_name,current_field_value in current_saved_record.items() if current_field_name in MUSIC_REQUEST_FIELDS})
    if current_rebuilt_record != current_saved_record:
        raise ValueError('저장된 음악 요청·고정 설정·프롬프트 해시 불일치; 새 작업으로 등록하세요.')
    return current_saved_record


def validate_music_identifier(current_identifier_value):
    if not isinstance(current_identifier_value,str) or not re.fullmatch(MUSIC_IDENTIFIER_PATTERN,current_identifier_value):
        raise ValueError('음악 생성 ID 형식 오류')
    return current_identifier_value
