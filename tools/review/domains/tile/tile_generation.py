"""고정 타일 프롬프트를 서버에서 결합하고 공용 Qwen 작업자로 실행한다."""
import hashlib
import html
import json
import time
from datetime import datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import yaml
from tools.review.domains.image.image_generation import ImageGenerationManager, IMAGE_JOB_ROOT, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH, validate_image_request
from tools.review.ui_assets import resolve_review_ui_asset

TILE_CONFIGURATION_PATH = WORKFLOW_ROOT_PATH/'generators/terrain/config/tile_map.yaml'

def load_tile_configuration():
    from tools.review.domains.character_animation.character_animation_assets import UniqueMappingLoader
    configuration_record_value = yaml.load(TILE_CONFIGURATION_PATH.read_text(),Loader=UniqueMappingLoader)
    if not isinstance(configuration_record_value,dict) or set(configuration_record_value)!={'schema_version','style_prompt','types'} or configuration_record_value['schema_version']!=1:
        raise ValueError('타일 설정 형식 오류')
    if set(configuration_record_value['types'])!={'rooftop','wall','ground'}:
        raise ValueError('타일 종류 설정 오류')
    for tile_type_record in configuration_record_value['types'].values():
        if set(tile_type_record)!={'label','base_prompt'} or not all(isinstance(prompt_text_value,str) and prompt_text_value.strip() for prompt_text_value in tile_type_record.values()):raise ValueError('타일 기본 프롬프트 설정 오류')
    if not isinstance(configuration_record_value['style_prompt'],str) or not configuration_record_value['style_prompt'].strip():raise ValueError('화풍 프롬프트 누락')
    return configuration_record_value

def prepare_tile_request(request_record_value):
    if request_record_value=={'action':'prepare'}:return request_record_value
    reference_image_values=request_record_value.get('images',[]) if isinstance(request_record_value,dict) else []
    if isinstance(request_record_value,dict):request_record_value={key:value for key,value in request_record_value.items() if key!='images'}
    if not isinstance(request_record_value,dict) or set(request_record_value)!={'action','tile_type','user_prompt','width','height','steps','seed'}:
        raise ValueError('타일 종류·사용자 프롬프트·생성 설정만 수정할 수 있습니다.')
    configuration_record_value=load_tile_configuration()
    selected_tile_kind=request_record_value['tile_type']
    if not isinstance(selected_tile_kind,str) or selected_tile_kind not in configuration_record_value['types']:raise ValueError('지원하지 않는 타일 종류')
    if not isinstance(request_record_value['user_prompt'],str):raise ValueError('사용자 프롬프트는 문자열이어야 합니다.')
    if type(request_record_value['seed']) is not int or not 0<=request_record_value['seed']<=4294967295:raise ValueError('Seed 범위 오류')
    base_prompt_value=configuration_record_value['types'][selected_tile_kind]['base_prompt']
    style_prompt_value=configuration_record_value['style_prompt']
    user_prompt_value=request_record_value['user_prompt'].strip()
    combined_prompt_value='\n\n'.join([base_prompt_value,user_prompt_value,style_prompt_value])
    if len(combined_prompt_value.split())>=100:raise ValueError('기본·사용자·화풍의 최종 프롬프트는 100단어 미만이어야 합니다.')
    validated_request_value=validate_image_request({key:request_record_value[key] for key in ('action','width','height','steps','seed')}|{'prompt':combined_prompt_value})
    if validated_request_value['width']!=validated_request_value['height']:raise ValueError('타일은 정사각형 해상도를 선택하세요.')
    from tools.review.domains.image.three_reference_generation import validate_three_reference_request
    validate_three_reference_request({**validated_request_value,'images':reference_image_values})
    return validated_request_value|{'images':reference_image_values}|{'tile_type':selected_tile_kind,'user_prompt':user_prompt_value,'base_prompt':base_prompt_value,'style_prompt':style_prompt_value,'prompt_words':len(combined_prompt_value.split()),'prompt_sha256':hashlib.sha256(combined_prompt_value.encode()).hexdigest()}

class TileGenerationManager(ImageGenerationManager):
    def __init__(self):
        super().__init__()
        self.reference_upload_enabled=True
        self.route_prefix_value='/tile-map-generator'
        self.job_storage_root=IMAGE_JOB_ROOT/'tile-map'
    def history_storage_path(self):return MANAGER_HISTORY_ROOT/'tile-map'
    def history_reset_marker_path(self):return self.history_storage_path()/'.reset-marker'
    def list_generation_history(self):
        history_records_by_identifier={record_value['id']:record_value for record_value in super().list_generation_history()}
        reset_marker_timestamp=self.history_reset_marker_path().stat().st_mtime if self.history_reset_marker_path().is_file() else 0
        for current_job_root in sorted(self.job_storage_root.iterdir(),key=lambda path_value:path_value.stat().st_mtime,reverse=True) if self.job_storage_root.is_dir() else []:
            request_file_path=current_job_root/'request.json'
            status_file_path=current_job_root/'status.json'
            if not current_job_root.is_dir() or not request_file_path.is_file() or not status_file_path.is_file():continue
            if request_file_path.stat().st_mtime<=reset_marker_timestamp:continue
            job_identifier_value=current_job_root.name
            if job_identifier_value in history_records_by_identifier:continue
            history_records_by_identifier[job_identifier_value]={'id':job_identifier_value,'created_at':datetime.fromtimestamp(current_job_root.stat().st_mtime,ZoneInfo('Asia/Seoul')).isoformat(),'request':json.loads(request_file_path.read_text()),'status':json.loads(status_file_path.read_text()),'job_path':str(current_job_root)}
        history_records=sorted(history_records_by_identifier.values(),key=lambda record_value:record_value.get('created_at',''),reverse=True)
        for current_history_record in history_records:
            current_job_root=self.job_storage_root/current_history_record['id']
            current_history_record['path']=str(current_job_root.resolve())
            current_history_record['image']=f'{self.route_prefix_value}/jobs/{current_history_record["id"]}/result.png' if (current_job_root/'result.png').is_file() else None
        return history_records
    def reset_generation_history(self):
        self.history_storage_path().mkdir(parents=True,exist_ok=True)
        self.history_reset_marker_path().touch()
        super().reset_generation_history()
    def validate_generation_request(self, request_record_value):return prepare_tile_request(request_record_value)
    def enrich_generation_status(self, current_job_root, current_status_record):
        if current_status_record['status']!='running':return current_status_record
        current_request_value=json.loads((current_job_root/'request.json').read_text())
        completed_duration_values=[]
        for history_record_value in self.list_generation_history():
            previous_request_value=history_record_value['request']
            if history_record_value['status']['status']!='completed' or any(previous_request_value.get(key)!=current_request_value.get(key) for key in ('steps','width','height','action')):continue
            result_record_path=self.job_storage_root/history_record_value['id']/'result.json'
            if result_record_path.is_file():
                elapsed_seconds_value=json.loads(result_record_path.read_text()).get('elapsed_seconds')
                if isinstance(elapsed_seconds_value,(int,float)) and elapsed_seconds_value>0:completed_duration_values.append(elapsed_seconds_value)
            if len(completed_duration_values)==5:break
        remaining_seconds_value=None
        if completed_duration_values:
            remaining_seconds_value=max(0,sum(completed_duration_values)/len(completed_duration_values)-(time.time()-(current_job_root/'request.json').stat().st_mtime))
        return current_status_record|{'estimate':{'remaining_seconds':remaining_seconds_value,'samples':len(completed_duration_values)}}
    def render_generation_page(self):
        # 모델 준비·생성·취소·진행·이력은 기존 이미지 생성 화면을 공유한다.
        page_source_value=super().render_generation_page().decode().replace('/image-generation','/tile-map-generator').replace('qwen2512Job','tileMapJob')
        page_source_value=page_source_value.replace('Qwen 2512 · 이미지 생성','타일 에셋 생성기').replace('Qwen 2512 이미지 생성','타일 에셋 생성기').replace('텍스트 설명으로 이미지를 생성합니다. 4스텝 Lightning / 30스텝 표준을 선택하세요.','지붕·벽·맵 타일을 생성합니다. 문은 벽 타일 프롬프트로 함께 처리합니다.')
        start_style_position=page_source_value.index('<div class="style-prompt-setting">')
        end_style_position=page_source_value.index('<label for="prompt">',start_style_position)
        tile_configuration_value=load_tile_configuration()
        tile_option_values=''.join(f'<option value="{kind_name_value}">{html.escape(kind_record_value["label"])}</option>' for kind_name_value,kind_record_value in tile_configuration_value['types'].items())
        fixed_prompt_section='<label for="tile-type">타일 종류</label><select id="tile-type">'+tile_option_values+'</select><h3>기본 프롬프트 · 고정 <small id="base-word-count"></small></h3><pre id="tile-base-prompt"></pre><h3>화풍 프롬프트 · 항상 적용 <small id="style-word-count"></small></h3><pre id="tile-style-prompt"></pre><p id="tile-word-count" role="status"></p>'
        page_source_value=page_source_value[:start_style_position]+fixed_prompt_section+page_source_value[end_style_position:]
        reference_input_section='<fieldset><legend>참조 이미지 · 선택 사항, 최대 3장</legend><p>512×512 불투명 PNG. 이미지 1·2·3 순서로 전달합니다. 사용자 프롬프트에 각 참조의 역할을 적으세요. 참조가 있으면 Qwen 2511, 없으면 기존 Qwen 2512로 생성합니다.</p>'+''.join(f'<label>이미지 {reference_slot_index}<input id="tile-reference-{reference_slot_index}" type="file" accept="image/png"><img id="tile-reference-preview-{reference_slot_index}" alt="참조 {reference_slot_index}" hidden style="max-width:128px"><button type="button" data-clear-reference="{reference_slot_index}">제거</button></label>' for reference_slot_index in range(1,4))+'</fieldset>'
        page_source_value=page_source_value.replace('<label for="prompt">',reference_input_section+'<label for="prompt">')
        page_source_value=page_source_value.replace('만들 이미지 설명','사용자 프롬프트').replace('원하는 대상, 배경, 구도, 스타일을 설명하세요.','재질, 색상, 건물의 용도 등 추가 요구를 입력하세요.')
        page_source_value=page_source_value.replace('<script src="/tile-map-generator/history-ui.js">','<script src="/tile-map-generator/tile-ui.js"></script><script src="/tile-map-generator/history-ui.js">')
        return page_source_value.encode()
    def handle_image_request(self,current_http_handler):
        route_path_value=urlsplit(current_http_handler.path).path
        if current_http_handler.command=='GET' and route_path_value in ('/tile-map-generator/catalog','/tile-map-generator/tile-ui.js'):
            response_payload_value=json.dumps(load_tile_configuration(),ensure_ascii=False).encode() if route_path_value.endswith('/catalog') else resolve_review_ui_asset('tile-generation.js').read_bytes()
            current_http_handler.send_response(200);current_http_handler.send_header('Content-Type','application/json; charset=utf-8' if route_path_value.endswith('/catalog') else 'text/javascript; charset=utf-8');current_http_handler.send_header('Content-Length',str(len(response_payload_value)));current_http_handler.end_headers();current_http_handler.wfile.write(response_payload_value);return True
        return super().handle_image_request(current_http_handler)
