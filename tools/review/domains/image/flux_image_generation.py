"""용도별 FLUX 이미지 생성의 공통 요청과 이력."""
import base64
import hashlib
import importlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from generators.image.common_art_style import compose_common_style_prompt
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH
from tools.review.domains.image.three_reference_generation import decode_reference_image, validate_three_reference_request, verify_reference_snapshots
from tools.review.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY, FLUX_MODEL_REVISION_VALUE
from tools.review.domains.image.flux_translation_queue import FluxTranslationQueueMixin, validate_flux_translation_runtime

from tools.review.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
FLUX_SEAMLESS_METHOD_VALUES = ('global-periodic-v1', 'circular-vae-v2', 'circular-vae', 'edge-blend')


def require_flux_image_profile(current_profile_name):
    if current_profile_name not in FLUX_IMAGE_PROFILE_RECORDS:
        raise ValueError('등록되지 않은 FLUX 이미지 생성기입니다.')
    return FLUX_IMAGE_PROFILE_RECORDS[current_profile_name]


class FluxImageGenerationManager(FluxTranslationQueueMixin, ImageGenerationManager):
    def __init__(self, current_profile_name):
        require_flux_image_profile(current_profile_name)
        super().__init__(three_reference_mode=True)
        self.current_profile_name = current_profile_name
        self.route_prefix_value = '/' + current_profile_name + '-generator'
        self.job_storage_root = WORKFLOW_ROOT_PATH / '.tmp/test' / (current_profile_name + '-generator')
        self.reference_request_limit = 12_100_000

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / self.current_profile_name

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/image/run_flux_image.py'

    def select_generation_service(self, saved_request_record=None):
        return 'flux-image'

    def validate_generation_runtime(self, saved_request_record=None):
        if not all((FLUX_MODEL_ROOT_DIRECTORY / name).exists() for name in ('manifest.json','transformer','vae','text_encoder')):
            raise ValueError('FLUX 3 Image Klein 모델 구성 요소가 없습니다.')
        validate_flux_translation_runtime(saved_request_record)

    def inspect_flux_model_status(self):
        from generators.image.flux_model_prepare import FLUX_MODEL_DIRECTORY, read_flux_model_lock, inspect_flux_model_file_sizes
        from tools.review.common.model_prepare_process import inspect_registered_preparation
        current_preparation_status = inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'flux-image')
        current_model_exists = FLUX_MODEL_DIRECTORY.exists() or FLUX_MODEL_DIRECTORY.is_symlink()
        current_model_ready = False
        if current_model_exists:
            current_model_ready = inspect_flux_model_file_sizes(FLUX_MODEL_DIRECTORY, read_flux_model_lock())
        current_status_message = ('공식 모델 파일 크기 확인 · 전체 해시와 GPU 실행은 별도 확인' if current_model_ready else
            '기존 모델이 불완전합니다. 자동으로 덮어쓰지 않습니다.' if current_model_exists else '공식 모델 파일 준비가 필요합니다.')
        if current_preparation_status == 'failed':
            current_status_message += ' 준비 실패: .local/model-preparation/flux-image/worker.log를 확인하세요.'
        return {'ready': current_model_ready, 'generation_ready': current_model_ready,
                'can_prepare': not current_model_exists or current_model_ready, 'message': current_status_message,
                'prepare_blocked_reason': '기존 모델은 자동 변경하지 않습니다.', 'preparation_status': current_preparation_status}

    def start_flux_model_preparation(self):
        from tools.review.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
        with self.current_request_lock:
            if inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'flux-image') == 'running':
                return {'preparation_status': 'running'}
            return start_registered_preparation(WORKFLOW_ROOT_PATH, 'flux-image')

    def handle_image_request(self, current_http_handler):
        from tools.review.common.management_transport import send_management_json_response
        current_request_path = urlsplit(current_http_handler.path).path
        current_command_payload = getattr(current_http_handler, 'management_command_payload', None)
        if self.current_profile_name == 'flux-image' and current_command_payload is not None:
            if current_http_handler.command == 'GET' and current_request_path == self.route_prefix_value + '/model-status':
                send_management_json_response(current_http_handler, 200, self.inspect_flux_model_status())
                return True
            if current_http_handler.command == 'POST' and current_request_path == self.route_prefix_value + '/jobs' and isinstance(current_command_payload, dict) and current_command_payload.get('action') == 'prepare':
                if current_command_payload != {'action': 'prepare'}:
                    raise ValueError('FLUX 모델 준비는 추가 입력을 받지 않습니다.')
                send_management_json_response(current_http_handler, 200, self.start_flux_model_preparation())
                return True
        return super().handle_image_request(current_http_handler)

    def validate_generation_request(self, request_record_value):
        current_seamless_method = None
        current_building_design = None
        current_translation_source = None
        current_translation_base = None
        if isinstance(request_record_value,dict) and self.current_profile_name == 'flux-building' and 'building_design_ko' not in request_record_value and isinstance(request_record_value.get('prompt'),str) and re.search('[가-힣]',request_record_value['prompt']):
            request_record_value={**request_record_value,'building_design_ko':request_record_value['prompt']}
        if isinstance(request_record_value,dict) and 'building_design_ko' in request_record_value:
            if self.current_profile_name != 'flux-building':
                raise ValueError('한국어 건물 디자인은 건물 생성기에서만 지원합니다.')
            current_building_design=request_record_value['building_design_ko']
            if not isinstance(current_building_design,str) or not current_building_design.strip() or len(current_building_design)>6000 or not re.search('[가-힣]',current_building_design):
                raise ValueError('건물 디자인을 6000자 이하의 한국어로 입력하세요.')
            from tools.review.domains.image.building_prompt import load_building_base_prompt
            current_base_prompt=load_building_base_prompt().replace('transparent background','plain background')
            request_record_value={**{key:value for key,value in request_record_value.items() if key!='building_design_ko'},'prompt':current_base_prompt}
        if isinstance(request_record_value,dict) and self.current_profile_name != 'flux-building':
            current_translation_source=request_record_value.get('translation_source_ko')
            current_input_prompt=request_record_value.get('prompt')
            if not current_translation_source and isinstance(current_input_prompt,str) and re.search('[가-힣]',current_input_prompt):
                current_translation_source=current_input_prompt
                current_translation_base=''
            elif current_translation_source:
                current_translation_base=current_input_prompt
            if current_translation_source is not None:
                if not isinstance(current_translation_source,str) or not current_translation_source.strip() or len(current_translation_source)>6000 or not re.search('[가-힣]',current_translation_source):
                    raise ValueError('번역할 내용을 6000자 이하의 한국어로 입력하세요.')
                if not isinstance(current_translation_base,str) or re.search('[가-힣]',current_translation_base):
                    raise ValueError('준비 문구에는 영어를 입력하고 한국어는 번역 입력란에 입력하세요.')
                request_record_value={**{key:value for key,value in request_record_value.items() if key!='translation_source_ko'},'prompt':current_translation_base or 'Translation pending.'}
        if isinstance(request_record_value,dict) and self.current_profile_name == 'flux-seamless':
            current_requested_method = request_record_value.get('seamless_method','global-periodic-v1')
            if current_requested_method != 'global-periodic-v1':
                raise ValueError('새 작업은 전역 주기 어텐션과 순환 VAE 방식만 지원합니다.')
            current_seamless_method = 'global-periodic-v1'
            request_record_value = {key:value for key,value in request_record_value.items() if key != 'seamless_method'}
        if isinstance(request_record_value,dict) and isinstance(request_record_value.get('images'),list):
            request_record_value = {**request_record_value,'images':[base64.b64encode(decode_reference_image(current_image_text,composite_transparent_background=True)).decode() for current_image_text in request_record_value['images']]}
        current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=(16,), maximum_reference_count=2, minimum_output_size=256)
        if current_translation_source is not None:
            current_request_record['prompt']=current_translation_base.strip()
        if self.current_profile_name == 'flux-seamless' and (current_request_record['width'] != 512 or current_request_record['height'] != 512 or current_request_record['images']):
            raise ValueError('전역 주기 어텐션의 새 작업은 512×512와 참조 이미지 없음만 지원합니다.')
        if len(current_request_record['images']) < require_flux_image_profile(self.current_profile_name)[4]:
            raise ValueError('이 생성기는 첫 참조 이미지가 필요합니다.')
        current_final_prompt, current_style_record = compose_common_style_prompt(current_request_record['prompt'])
        current_body_sources = importlib.import_module('generators.character-generator.body_references').identify_body_reference_images(current_request_record['images']) if self.current_profile_name == 'flux-character' else []
        return {**current_request_record, 'user_prompt':current_request_record['prompt'], 'prompt':current_final_prompt, 'common_style':current_style_record, 'body_reference_sources':current_body_sources, 'profile':self.current_profile_name, 'flux_model_revision':FLUX_MODEL_REVISION_VALUE, 'prompt_sha256':hashlib.sha256(current_final_prompt.encode()).hexdigest(), **({'seamless_method':current_seamless_method} if current_seamless_method else {}), **({'building_design_ko':current_building_design.strip(),'building_base_prompt':current_request_record['prompt']} if current_building_design else {}), **({'translation_source_ko':current_translation_source.strip(),'translation_base_prompt':current_request_record['prompt']} if current_translation_source else {})}

    def enrich_generation_status(self, current_job_root, current_status_record):
        if self.current_profile_name == 'flux-seamless' and (current_job_root/'request.json').is_file():
            current_request_record=json.loads((current_job_root/'request.json').read_text())
            current_status_record['seamless_method']=current_request_record.get('seamless_method','edge-blend')
        return current_status_record

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        if self.current_profile_name == 'flux-seamless' and current_request_record.get('seamless_method','edge-blend') not in FLUX_SEAMLESS_METHOD_VALUES:
            raise ValueError('저장된 심리스 처리 방식이 올바르지 않습니다.')
        verify_reference_snapshots(selected_job_directory,current_request_record)
        if 'translation_source_ko' in current_request_record:
            from tools.review.domains.image.flux_translation_queue import validate_flux_translation_record
            validate_flux_translation_record(selected_job_directory,current_request_record)
        if self.current_profile_name == 'flux-building' and 'building_design_ko' in current_request_record:
            current_design_value=current_request_record['building_design_ko']
            current_base_value=current_request_record.get('building_base_prompt')
            current_translated_value=current_request_record.get('translated_design')
            if not isinstance(current_design_value,str) or not current_design_value.strip() or not isinstance(current_base_value,str) or not current_base_value.strip():
                raise ValueError('저장된 건물 디자인 또는 기본 문구가 올바르지 않습니다.')
            if current_translated_value is not None and (not isinstance(current_translated_value,str) or not current_translated_value.strip()):
                raise ValueError('저장된 건물 번역문이 올바르지 않습니다.')
            current_expected_user=' '.join((current_base_value.strip(),current_translated_value.strip())) if current_translated_value else current_base_value
            current_expected_final,_=compose_common_style_prompt(current_expected_user)
            if current_request_record.get('user_prompt') != current_expected_user or current_request_record.get('prompt') != current_expected_final:
                raise ValueError('저장된 건물 번역·기본 문구·화풍 조합이 일치하지 않습니다.')
            current_pipeline_path=selected_job_directory/'translation-pipeline.json'
            if current_pipeline_path.exists():
                current_pipeline_record=json.loads(current_pipeline_path.read_text())
                if current_pipeline_record.get('source_sha256') != hashlib.sha256(current_design_value.encode()).hexdigest():
                    raise ValueError('저장된 한국어 디자인과 번역 작업이 일치하지 않습니다.')
                if current_translated_value and (not isinstance(current_request_record.get('translation'),dict) or current_request_record['translation'].get('id') != current_pipeline_record.get('translation_id')):
                    raise ValueError('저장된 번역 작업 ID가 일치하지 않습니다.')
            elif current_translated_value:
                raise ValueError('완료된 번역 작업 정보가 없습니다.')
        if current_request_record.get('body_reference_sources'):
            importlib.import_module('generators.character-generator.body_references').verify_body_reference_history(selected_job_directory,current_request_record)
        current_references_value = current_request_record.get('references')
        if not isinstance(current_references_value,list) or not require_flux_image_profile(self.current_profile_name)[4] <= len(current_references_value) <= 2:
            raise ValueError('저장된 참조 이미지 수가 올바르지 않습니다.')
        if self.current_profile_name == 'flux-seamless' and current_request_record.get('seamless_method') == 'global-periodic-v1' and (current_request_record.get('width') != 512 or current_request_record.get('height') != 512 or current_references_value):
            raise ValueError('저장된 전역 주기 작업은 512×512 무참조여야 합니다.')
        if current_request_record.get('profile') != self.current_profile_name or current_request_record.get('flux_model_revision') != FLUX_MODEL_REVISION_VALUE or hashlib.sha256(current_request_record['prompt'].encode()).hexdigest() != current_request_record.get('prompt_sha256'):
            raise ValueError('저장된 생성기·모델 또는 프롬프트가 일치하지 않습니다.')
        if current_request_record.get('steps') != 16 or type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('저장된 스텝 또는 시드가 올바르지 않습니다.')
        if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= 1664 or current_request_record[name] % 16 for name in ('width','height')):
            raise ValueError('저장된 출력 크기가 올바르지 않습니다.')
        if (current_request_record.get('building_design_ko') or current_request_record.get('translation_source_ko')) and not (selected_job_directory/'gpu-command.json').exists():
            return
        current_command_record=json.loads((selected_job_directory/'gpu-command.json').read_text())
        if Path(current_command_record['command'][1]).resolve() != (WORKFLOW_ROOT_PATH/self.select_generation_runner()).resolve():
            raise ValueError('저장된 실행기가 일치하지 않습니다.')
