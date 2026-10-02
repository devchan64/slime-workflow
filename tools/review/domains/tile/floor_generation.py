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
    if not isinstance(configuration_record_value, dict) or set(configuration_record_value) != {'schema_version','base_prompt','margin_prompt','style_prompt','default_add_margins','default_user_prompt'} or configuration_record_value['schema_version'] != 5:
        raise ValueError('바닥 타일 설정 형식 오류')
    if any(not isinstance(configuration_record_value[current_field_name],str) or not configuration_record_value[current_field_name].strip() for current_field_name in ('base_prompt','margin_prompt','style_prompt','default_user_prompt')):
        raise ValueError('바닥 타일 설정 문자열 오류')
    if type(configuration_record_value['default_add_margins']) is not bool:
        raise ValueError('여백 기본 설정은 boolean이어야 합니다.')
    return configuration_record_value

def compose_floor_base_prompt(configuration_record_value, add_margins_value=None):
    if add_margins_value is None:
        add_margins_value = configuration_record_value['default_add_margins']
    if type(add_margins_value) is not bool:
        raise ValueError('여백 추가는 boolean이어야 합니다.')
    return ' '.join([configuration_record_value['base_prompt'], *([configuration_record_value['margin_prompt']] if add_margins_value else []), configuration_record_value['style_prompt']])

def combine_floor_prompt(user_prompt_value, configuration_record_value, add_margins_value=None):
    if not isinstance(user_prompt_value,str) or not user_prompt_value.strip():
        raise ValueError('바닥 표면 프롬프트를 입력하세요.')
    return ' '.join([user_prompt_value.strip().rstrip('.')+'.', compose_floor_base_prompt(configuration_record_value,add_margins_value)])

def prepare_floor_request(request_record_value):
    if not isinstance(request_record_value,dict) or set(request_record_value)-{'action','user_prompt','width','height','steps','seed','tag','add_margins'} or not {'action','user_prompt','width','height','steps'} <= set(request_record_value):
        raise ValueError('바닥 타일 요청 필드 오류')
    configuration_record_value = load_floor_configuration()
    add_margins_value = request_record_value.get('add_margins',configuration_record_value['default_add_margins'])
    if type(add_margins_value) is not bool:
        raise ValueError('여백 추가는 boolean이어야 합니다.')
    combined_prompt_value = combine_floor_prompt(request_record_value['user_prompt'], configuration_record_value,add_margins_value)
    if len(combined_prompt_value.split()) >= 100: raise ValueError('최종 프롬프트는 100단어 미만이어야 합니다.')
    generation_tag_value = request_record_value.get('tag','')
    if not isinstance(generation_tag_value,str) or len(generation_tag_value)>80 or '\n' in generation_tag_value or '\r' in generation_tag_value: raise ValueError('생성 태그는 줄바꿈 없이 80자 이하여야 합니다.')
    validated_request_value = validate_image_request({current_field_name:request_record_value[current_field_name] for current_field_name in ('action','width','height','steps')} | {'seed':request_record_value.get('seed',251204),'prompt':combined_prompt_value})
    if validated_request_value['action'] != 'generate' or validated_request_value['width'] != validated_request_value['height'] or validated_request_value['width'] != 512 or validated_request_value['steps'] != 4: raise ValueError('바닥 타일은 512×512 · 4스텝 단일 생성만 지원합니다.')
    return validated_request_value | {'generation_model':'Qwen/Qwen-Image-Edit-2511','references':[],'reference_snapshots':[],'user_prompt':request_record_value['user_prompt'].strip(),'tag':generation_tag_value,'add_margins':add_margins_value,'base_prompt':compose_floor_base_prompt(configuration_record_value,add_margins_value),'prompt_words':len(combined_prompt_value.split()),'prompt_sha256':hashlib.sha256(combined_prompt_value.encode()).hexdigest()}


class FloorGenerationManager(TileGenerationManager):
    def __init__(self):
        super().__init__()
        self.reference_upload_enabled = False
        self.route_prefix_value = '/floor-tile-generator'
        self.job_storage_root = IMAGE_JOB_ROOT/'floor-tile'
    def select_generation_runner(self, saved_request_record=None):
        if saved_request_record is None or saved_request_record.get('generation_model') == 'Qwen/Qwen-Image-Edit-2511':
            return 'generators/image/run_qwen_2511_three_reference.py'
        raise ValueError('이전 맵 타일 생성 이력은 재개할 수 없습니다. 현재 설정으로 새로 생성하세요.')
    def validate_generation_resume(self, selected_job_directory):
        saved_request_record = json.loads((selected_job_directory/'request.json').read_text())
        self.select_generation_runner(saved_request_record)
    def history_storage_path(self): return MANAGER_HISTORY_ROOT/'floor-tile'
    def validate_generation_request(self, request_record_value): return prepare_floor_request(request_record_value)
    def enrich_generation_status(self, current_job_root, current_status_record):
        current_status_record = super().enrich_generation_status(current_job_root,current_status_record)
        saved_request_record = json.loads((current_job_root/'request.json').read_text())
        current_status_record['resume_allowed'] = saved_request_record.get('generation_model') == 'Qwen/Qwen-Image-Edit-2511'
        current_status_record['resume_block_reason'] = '' if current_status_record['resume_allowed'] else '이전 이력 재개 불가 · 새로 생성하세요'
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
