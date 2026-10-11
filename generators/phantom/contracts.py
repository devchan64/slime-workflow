"""PHANTOM R2V의 고정 모델·입력 계약."""
import base64
import hashlib
import json
import math
from pathlib import Path
import yaml
from tools.review.domains.image.three_reference_generation import decode_reference_image, verify_reference_snapshots
from tools.review.common.generation_records import validate_history_tag

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
PHANTOM_CONFIGURATION_PATH = Path(__file__).parent / 'config/defaults.yaml'
PHANTOM_JOB_STORAGE_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/phantom'
PHANTOM_ALLOWED_FRAME_COUNTS = tuple(range(1, 162, 4))
PHANTOM_ALLOWED_IMAGE_SIZES = ((832, 480),)
PHANTOM_CONFIGURATION_KEYS = {'model_id','model_directory','width','height','frames','fps','steps','seed','flow_shift','guidance_scale','conditioning_scale','negative_prompt'}


def load_phantom_defaults():
    from tools.review.domains.image.image_generation import parse_unique_request
    class UniqueConfigurationLoader(yaml.SafeLoader):
        pass
    def construct_unique_mapping(current_yaml_loader, current_yaml_node):
        return parse_unique_request(current_yaml_loader.construct_pairs(current_yaml_node, deep=True))
    UniqueConfigurationLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_unique_mapping)
    current_default_values = yaml.load(PHANTOM_CONFIGURATION_PATH.read_text(), Loader=UniqueConfigurationLoader)
    if not isinstance(current_default_values, dict) or set(current_default_values) != PHANTOM_CONFIGURATION_KEYS:
        raise ValueError('PHANTOM 기본 설정 필드 오류')
    if current_default_values['model_id'] != 'bytedance-research/Phantom' or current_default_values['model_directory'] != '.model/phantom-1.3b':
        raise ValueError('PHANTOM 모델은 파이프라인에서 고정합니다.')
    for current_field_name, expected_field_value in {'width':832,'height':480,'frames':81,'fps':16,'steps':50,'seed':42,'flow_shift':5.0,'guidance_scale':7.5,'conditioning_scale':5.0}.items():
        if type(current_default_values[current_field_name]) is not type(expected_field_value) or current_default_values[current_field_name] != expected_field_value:
            raise ValueError(f'PHANTOM 기본 설정 오류: {current_field_name}')
    if not isinstance(current_default_values['negative_prompt'], str):
        raise ValueError('부정 프롬프트는 문자열이어야 합니다.')
    return current_default_values


def validate_phantom_request(current_request_record):
    current_default_values = load_phantom_defaults()
    if not isinstance(current_request_record, dict) or set(current_request_record) - {'action','prompt','negative_prompt','images','frames','seed','tag','width','height','steps','flow_shift','guidance_scale','conditioning_scale'}:
        raise ValueError('PHANTOM 요청 필드 오류; 비디오·마스크·모델 지정은 지원하지 않습니다.')
    if current_request_record.get('action') != 'generate':
        raise ValueError('generate 요청이 필요합니다.')
    current_prompt_text = current_request_record.get('prompt')
    if not isinstance(current_prompt_text, str) or not 1 <= len(current_prompt_text.strip()) <= 8000:
        raise ValueError('프롬프트는 1~8000자여야 합니다.')
    current_negative_text = current_request_record.get('negative_prompt', current_default_values['negative_prompt'])
    if not isinstance(current_negative_text, str) or len(current_negative_text) > 8000:
        raise ValueError('부정 프롬프트는 8000자 이하 문자열이어야 합니다.')
    current_optional_fields = {}
    if 'negative_prompt' in current_request_record:
        current_optional_fields['negative_prompt'] = current_negative_text.strip()
    current_default_values['negative_prompt'] = current_negative_text.strip()
    current_reference_values = current_request_record.get('images')
    if not isinstance(current_reference_values, list) or not 1 <= len(current_reference_values) <= 4:
        raise ValueError('Phantom 참조 이미지 1~4장이 필요합니다.')
    current_frame_count = current_request_record.get('frames', current_default_values['frames'])
    current_seed_value = current_request_record.get('seed', current_default_values['seed'])
    if type(current_frame_count) is not int or current_frame_count not in PHANTOM_ALLOWED_FRAME_COUNTS:
        raise ValueError('프레임 수는 1~161 범위의 4n+1 정수여야 합니다.')
    if type(current_seed_value) is not int or not 0 <= current_seed_value <= 4294967295:
        raise ValueError('시드는 0~4294967295 정수여야 합니다.')
    for current_field_name in ('width','height','steps'):
        current_field_value = current_request_record.get(current_field_name,current_default_values[current_field_name])
        if type(current_field_value) is not int:
            raise ValueError(f'{current_field_name}는 정수여야 합니다.')
        current_default_values[current_field_name] = current_field_value
    if (current_default_values['width'],current_default_values['height']) not in PHANTOM_ALLOWED_IMAGE_SIZES:
        raise ValueError('해상도는 832×480 중 선택하세요.')
    if not 1 <= current_default_values['steps'] <= 100:
        raise ValueError('스텝은 1~100 정수여야 합니다.')
    for current_field_name,current_lower_bound,current_upper_bound in (('flow_shift',0.1,30),('guidance_scale',1,20),('conditioning_scale',0,20)):
        current_field_value = current_request_record.get(current_field_name,current_default_values[current_field_name])
        if type(current_field_value) not in (int,float) or not math.isfinite(current_field_value) or not current_lower_bound <= current_field_value <= current_upper_bound:
            raise ValueError(f'{current_field_name}는 {current_lower_bound}~{current_upper_bound} 유한 숫자여야 합니다.')
        current_default_values[current_field_name] = float(current_field_value)
        if current_field_name in current_request_record:
            current_optional_fields[current_field_name] = float(current_field_value)
    current_encoded_images = [base64.b64encode(decode_reference_image(current_reference_value, composite_transparent_background=True)).decode() for current_reference_value in current_reference_values]
    return {**current_optional_fields,'action':'generate','prompt':current_prompt_text.strip(),'images':current_encoded_images, 'frames':current_frame_count,'seed':current_seed_value,'tag':validate_history_tag(current_request_record.get('tag','')), 'width':current_default_values['width'],'height':current_default_values['height'],'steps':current_default_values['steps'],'phantom':{**current_default_values,'frames':current_frame_count,'seed':current_seed_value,'task':'s2v','video':None,'mask':None,'prompt_words':len(current_prompt_text.strip().split()),'prompt_sha256':hashlib.sha256(current_prompt_text.strip().encode()).hexdigest()}}


def validate_phantom_assets():
    current_model_root = WORKFLOW_ROOT_DIRECTORY / load_phantom_defaults()['model_directory']
    current_required_paths = [current_model_root/'Phantom-Wan-1.3B.pth',WORKFLOW_ROOT_DIRECTORY/'.model/wan21-phantom-components/Wan2.1_VAE.pth',WORKFLOW_ROOT_DIRECTORY/'.model/wan21-phantom-components/models_t5_umt5-xxl-enc-bf16.pth',WORKFLOW_ROOT_DIRECTORY/'.model/wan21-phantom-components/google/umt5-xxl/tokenizer_config.json']
    for current_required_path in current_required_paths:
        if not current_required_path.is_file():
            raise ValueError(f'Phantom 모델 파일 누락: {current_required_path}')
    return current_model_root


def verify_phantom_request(current_job_root):
    current_request_record = json.loads((current_job_root/'request.json').read_text())
    current_reference_names=current_request_record.get('references',[])
    if not 1 <= len(current_reference_names) <= 4 or current_reference_names != [f'reference-{current_reference_index+1}.png' for current_reference_index in range(len(current_reference_names))] or not current_request_record.get('reference_snapshots'):
        raise ValueError('R2V 저장 참조 계약 오류')
    verify_reference_snapshots(current_job_root, current_request_record)
    restored_request_record = {current_field_name:current_request_record[current_field_name] for current_field_name in ('action','prompt','frames','seed','tag','width','height','steps')}
    for current_field_name in ('negative_prompt','flow_shift','guidance_scale','conditioning_scale'):
        if current_field_name in current_request_record:
            restored_request_record[current_field_name] = current_request_record[current_field_name]
    restored_request_record['images'] = [base64.b64encode((current_job_root/current_reference_name).read_bytes()).decode() for current_reference_name in current_reference_names]
    if set(current_request_record) != set(restored_request_record)-{'images'} | {'phantom','references','reference_snapshots'}:
        raise ValueError('저장 요청 필드 오류')
    if validate_phantom_request(restored_request_record)['phantom'] != current_request_record['phantom']:
        raise ValueError('저장된 PHANTOM 설정·프롬프트 해시 불일치')
    return current_request_record
