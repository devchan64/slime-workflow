"""바닥 타일의 고정 프롬프트와 공용 이미지 작업 서비스."""
import hashlib
import json
from urllib.parse import urlsplit
import yaml
from tools.review.domains.tile.tile_generation import TileGenerationManager
from tools.review.domains.image.image_generation import IMAGE_JOB_ROOT, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH, validate_image_request
from tools.review.domains.character_animation.character_animation_assets import UniqueMappingLoader

FLOOR_CONFIGURATION_PATH = WORKFLOW_ROOT_PATH/'generators/terrain/config/floor_tile.yaml'

def load_floor_configuration():
    configuration_record_value = yaml.load(FLOOR_CONFIGURATION_PATH.read_text(), Loader=UniqueMappingLoader)
    if not isinstance(configuration_record_value, dict) or set(configuration_record_value) != {'schema_version','base_prompt','style_prompt','default_user_prompt','source_generation_id','separation_size','separation_steps','separation_seed'} or configuration_record_value['schema_version'] != 3:
        raise ValueError('바닥 타일 설정 형식 오류')
    if any(not isinstance(configuration_record_value[current_field_name],str) or not configuration_record_value[current_field_name].strip() for current_field_name in ('base_prompt','style_prompt','default_user_prompt','source_generation_id')):
        raise ValueError('바닥 타일 설정 문자열 오류')
    for current_field_name, expected_field_value in (('separation_size',512),('separation_steps',4),('separation_seed',10107)):
        if type(configuration_record_value[current_field_name]) is not int or configuration_record_value[current_field_name] != expected_field_value:
            raise ValueError('분리 단계 고정 설정 오류: '+current_field_name)
    return configuration_record_value

def combine_floor_prompt(user_prompt_value, configuration_record_value):
    if not isinstance(user_prompt_value,str) or not user_prompt_value.strip():
        raise ValueError('바닥 표면 프롬프트를 입력하세요.')
    return ' '.join([user_prompt_value.strip().rstrip('.')+'.', configuration_record_value['base_prompt'], configuration_record_value['style_prompt']])

def prepare_floor_request(request_record_value):
    if request_record_value == {'action':'prepare'}: return request_record_value
    if not isinstance(request_record_value,dict) or set(request_record_value)-{'action','user_prompt','width','height','steps','seed','tag'} or not {'action','user_prompt','width','height','steps'} <= set(request_record_value):
        raise ValueError('바닥 타일 요청 필드 오류')
    configuration_record_value = load_floor_configuration()
    combined_prompt_value = combine_floor_prompt(request_record_value['user_prompt'], configuration_record_value)
    if len(combined_prompt_value.split()) >= 100: raise ValueError('최종 프롬프트는 100단어 미만이어야 합니다.')
    generation_tag_value = request_record_value.get('tag','')
    if not isinstance(generation_tag_value,str) or len(generation_tag_value)>80 or '\n' in generation_tag_value or '\r' in generation_tag_value: raise ValueError('생성 태그는 줄바꿈 없이 80자 이하여야 합니다.')
    validated_request_value = validate_image_request({current_field_name:request_record_value[current_field_name] for current_field_name in ('action','width','height','steps')} | {'seed':request_record_value.get('seed',251204),'prompt':combined_prompt_value})
    if validated_request_value['action'] != 'generate' or validated_request_value['width'] != validated_request_value['height'] or validated_request_value['width'] != 1024: raise ValueError('바닥 타일은 1024×1024 · 3행 3열 생성만 지원합니다.')
    return validated_request_value | {'user_prompt':request_record_value['user_prompt'].strip(),'tag':generation_tag_value,'base_prompt':configuration_record_value['base_prompt'],'style_prompt':configuration_record_value['style_prompt'],'prompt_words':len(combined_prompt_value.split()),'prompt_sha256':hashlib.sha256(combined_prompt_value.encode()).hexdigest(),'floor_separation':{'version':3,'prompt':request_record_value['user_prompt'].strip(),'width':configuration_record_value['separation_size'],'height':configuration_record_value['separation_size'],'steps':configuration_record_value['separation_steps'],'seed':configuration_record_value['separation_seed'],'prompt_words':len(request_record_value['user_prompt'].strip().split()),'prompt_sha256':hashlib.sha256(request_record_value['user_prompt'].strip().encode()).hexdigest()}}

class FloorGenerationManager(TileGenerationManager):
    def __init__(self):
        super().__init__()
        self.reference_upload_enabled = False
        self.route_prefix_value = '/floor-tile-generator'
        self.job_storage_root = IMAGE_JOB_ROOT/'floor-tile'
    def history_storage_path(self): return MANAGER_HISTORY_ROOT/'floor-tile'
    def validate_generation_request(self, request_record_value): return prepare_floor_request(request_record_value)
    def enrich_generation_status(self, current_job_root, current_status_record):
        current_status_record = super().enrich_generation_status(current_job_root,current_status_record)
        for current_field_name,current_file_name in (('separated_image','single-tile.png'),('extracted_image','center-tile.png'),('rectified_image','square-crop.png'),('detected_image','quadrilateral.png')):
            current_status_record[current_field_name] = f'{self.route_prefix_value}/jobs/{current_job_root.name}/{current_file_name}' if (current_job_root/current_file_name).is_file() else None
        return current_status_record
    def handle_image_request(self,current_http_handler):
        if current_http_handler.command=='GET' and urlsplit(current_http_handler.path).path==self.route_prefix_value+'/catalog':
            response_payload_value=json.dumps(load_floor_configuration(),ensure_ascii=False).encode()
            current_http_handler.send_response(200)
            current_http_handler.send_header('Content-Type','application/json; charset=utf-8')
            current_http_handler.send_header('Content-Length',str(len(response_payload_value)))
            current_http_handler.end_headers()
            current_http_handler.wfile.write(response_payload_value)
            return True
        return super().handle_image_request(current_http_handler)
