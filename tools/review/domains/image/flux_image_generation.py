"""용도별 FLUX 이미지 생성의 공통 요청과 이력."""
import base64
import hashlib
import importlib
import json
import re
import subprocess
from pathlib import Path
from generators.image.common_art_style import compose_common_style_prompt
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH
from tools.review.domains.image.three_reference_generation import decode_reference_image, validate_three_reference_request, verify_reference_snapshots
from tools.review.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY, FLUX_MODEL_REVISION_VALUE

FLUX_IMAGE_PROFILE_RECORDS = {
    'flux-image': ('일반 이미지', '입력한 내용과 참조 이미지로 이미지를 생성합니다.', 768, 768, 0),
    'flux-character': ('캐릭터', '캐릭터 외형과 자세를 설명하세요. 첫 참조로 신체 비율 기준을 선택할 수 있습니다.', 768, 1152, 0),
    'flux-mannequin': ('마네킨', '마네킨 제작 단계와 참조를 선택하고 필요한 변경을 입력하세요.', 768, 1152, 1),
    'flux-billboard': ('빌보드 가이드', '첫 참조에 점유 가이드를 선택하세요.', 768, 768, 1),
    'flux-prop': ('소품', '소품의 용도와 재질을 설명하세요.', 768, 768, 0),
    'flux-vegetation': ('식생', '식물의 종류와 형태를 설명하세요.', 768, 768, 0),
    'flux-building': ('건물', '첫 참조에 건물 배치 가이드를 선택하고 용도와 재질을 설명하세요.', 768, 768, 1),
    'flux-seamless': ('심리스 타일', '전역 주기 어텐션과 순환 VAE로 생성하고 3×3으로 확인합니다. 새 작업은 512×512 무참조만 지원합니다.', 512, 512, 0),
}
FLUX_SEAMLESS_METHOD_VALUES = ('global-periodic-v1', 'circular-vae-v2', 'circular-vae', 'edge-blend')


def require_flux_image_profile(current_profile_name):
    if current_profile_name not in FLUX_IMAGE_PROFILE_RECORDS:
        raise ValueError('등록되지 않은 FLUX 이미지 생성기입니다.')
    return FLUX_IMAGE_PROFILE_RECORDS[current_profile_name]


class FluxImageGenerationManager(ImageGenerationManager):
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
        if saved_request_record and saved_request_record.get('building_design_ko') and not saved_request_record.get('translated_design'):
            from tools.review.domains.translation.service import TRANSLATION_MODEL_ROOT, TRANSLATION_PYTHON_PATH
            if not TRANSLATION_PYTHON_PATH.is_file() or not (TRANSLATION_MODEL_ROOT / 'manifest.json').is_file():
                raise ValueError('한국어 건물 디자인 번역을 위해 TranslateGemma 모델과 ROCm 환경을 먼저 준비하세요.')

    def launch_generation_worker(self, current_job_root, current_request_record, current_log_handle):
        if self.current_profile_name == 'flux-building' and current_request_record.get('building_design_ko') and not current_request_record.get('translated_design'):
            from tools.review.common.generation_records import write_record_atomically
            write_record_atomically(current_job_root/'status.json', {'status':'queued','stage':'translation','message':'번역 대기열 등록 중'})
            return subprocess.Popen([str(self.select_generation_python(current_request_record)),str(WORKFLOW_ROOT_PATH/'generators/image/run_flux_building_pipeline.py'),'--job-dir',str(current_job_root)],stdout=current_log_handle,stderr=subprocess.STDOUT,start_new_session=True,cwd=WORKFLOW_ROOT_PATH)
        return super().launch_generation_worker(current_job_root,current_request_record,current_log_handle)

    def resume_generation_job(self, selected_job_directory, saved_request_record, legacy_command_record):
        if self.current_profile_name == 'flux-building' and saved_request_record.get('building_design_ko') and not saved_request_record.get('translated_design'):
            import fcntl
            from tools.review.common.generation_records import write_record_atomically
            with (selected_job_directory/'resume.lock').open('a') as current_resume_handle:
                current_status_record=json.loads((selected_job_directory/'status.json').read_text())
                if current_status_record.get('status') not in ('failed','cancelled','paused'):
                    raise ValueError('실패·취소·일시정지된 작업만 재개할 수 있습니다.')
                with (selected_job_directory/'building-pipeline.lock').open('a') as current_pipeline_handle:
                    try:
                        fcntl.flock(current_pipeline_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError as current_lock_error:
                        raise ValueError('이전 번역 연결 작업이 종료되는 중입니다.') from current_lock_error
                (selected_job_directory/'cancel.request').unlink(missing_ok=True)
                write_record_atomically(selected_job_directory/'status.json', {'status':'queued','stage':'translation','message':'번역 대기열 재개 중'})
                with (selected_job_directory/'worker.log').open('a') as current_log_handle:
                    self.launch_generation_worker(selected_job_directory,saved_request_record,current_log_handle)
            return {'id':selected_job_directory.name,'status':'queued'}
        return super().resume_generation_job(selected_job_directory,saved_request_record,legacy_command_record)

    def list_generation_history(self):
        current_history_records=super().list_generation_history()
        if self.current_profile_name == 'flux-building':
            for current_history_record in current_history_records:
                current_request_path=self.job_storage_root/current_history_record['id']/'request.json'
                if current_request_path.is_file():
                    current_history_record['request']=json.loads(current_request_path.read_text())
        return current_history_records

    def validate_generation_request(self, request_record_value):
        current_seamless_method = None
        current_building_design = None
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
        if isinstance(request_record_value,dict) and self.current_profile_name == 'flux-seamless':
            current_requested_method = request_record_value.get('seamless_method','global-periodic-v1')
            if current_requested_method != 'global-periodic-v1':
                raise ValueError('새 작업은 전역 주기 어텐션과 순환 VAE 방식만 지원합니다.')
            current_seamless_method = 'global-periodic-v1'
            request_record_value = {key:value for key,value in request_record_value.items() if key != 'seamless_method'}
        if isinstance(request_record_value,dict) and isinstance(request_record_value.get('images'),list):
            request_record_value = {**request_record_value,'images':[base64.b64encode(decode_reference_image(current_image_text,composite_transparent_background=True)).decode() for current_image_text in request_record_value['images']]}
        current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=(16,), maximum_reference_count=2, minimum_output_size=256)
        if self.current_profile_name == 'flux-seamless' and (current_request_record['width'] != 512 or current_request_record['height'] != 512 or current_request_record['images']):
            raise ValueError('전역 주기 어텐션의 새 작업은 512×512와 참조 이미지 없음만 지원합니다.')
        if len(current_request_record['images']) < require_flux_image_profile(self.current_profile_name)[4]:
            raise ValueError('이 생성기는 첫 참조 이미지가 필요합니다.')
        current_final_prompt, current_style_record = compose_common_style_prompt(current_request_record['prompt'])
        current_body_sources = importlib.import_module('generators.character-generator.body_references').identify_body_reference_images(current_request_record['images']) if self.current_profile_name == 'flux-character' else []
        return {**current_request_record, 'user_prompt':current_request_record['prompt'], 'prompt':current_final_prompt, 'common_style':current_style_record, 'body_reference_sources':current_body_sources, 'profile':self.current_profile_name, 'flux_model_revision':FLUX_MODEL_REVISION_VALUE, 'prompt_sha256':hashlib.sha256(current_final_prompt.encode()).hexdigest(), **({'seamless_method':current_seamless_method} if current_seamless_method else {}), **({'building_design_ko':current_building_design.strip(),'building_base_prompt':current_request_record['prompt']} if current_building_design else {})}

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
        if current_request_record.get('building_design_ko') and not (selected_job_directory/'gpu-command.json').exists():
            return
        current_command_record=json.loads((selected_job_directory/'gpu-command.json').read_text())
        if Path(current_command_record['command'][1]).resolve() != (WORKFLOW_ROOT_PATH/self.select_generation_runner()).resolve():
            raise ValueError('저장된 실행기가 일치하지 않습니다.')
