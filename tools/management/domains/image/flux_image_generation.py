"""용도별 FLUX 이미지 생성의 공통 요청과 이력."""
import base64
import hashlib
import importlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from generators.image.common_art_style import compose_common_style_prompt
from tools.management.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, WORKFLOW_ROOT_PATH
from tools.management.domains.image.three_reference_generation import decode_reference_image, validate_three_reference_request, verify_reference_snapshots
from tools.management.domains.image.flux_expression_generation import FLUX_MODEL_ROOT_DIRECTORY, FLUX_MODEL_REVISION_VALUE
from tools.management.domains.image.flux_translation_queue import FluxTranslationQueueMixin, validate_flux_translation_runtime

from tools.management.domains.image.flux_profiles import FLUX_IMAGE_PROFILE_RECORDS
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
        from tools.management.common.model_prepare_process import inspect_registered_preparation
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
        from tools.management.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
        with self.current_request_lock:
            if inspect_registered_preparation(WORKFLOW_ROOT_PATH, 'flux-image') == 'running':
                return {'preparation_status': 'running'}
            return start_registered_preparation(WORKFLOW_ROOT_PATH, 'flux-image')

    def handle_image_request(self, current_http_handler):
        from tools.management.common.management_transport import send_management_json_response
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
            from tools.management.domains.image.building_prompt import load_building_base_prompt
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
        current_allowed_steps = range(1, 51) if self.current_profile_name == 'flux-character' else (16,)
        current_maximum_size = 2048 if self.current_profile_name == 'flux-character' else 1664
        current_request_record = validate_three_reference_request(request_record_value, allowed_inference_steps=current_allowed_steps, maximum_reference_count=2, minimum_output_size=256, maximum_output_size=current_maximum_size)
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

    def inspect_flux_resume_availability(self):
        """공유 FLUX 모델 준비 기록의 충돌 여부만 확인한다."""
        from tools.management.common.model_prepare_process import inspect_registered_preparation
        try:
            current_preparation_state=inspect_registered_preparation(WORKFLOW_ROOT_PATH,'flux-image')
        except (OSError,ValueError,TypeError):return 'unknown'
        if current_preparation_state=='running':return 'download_running'
        return 'available' if current_preparation_state in ('idle','completed','failed') else 'unknown'

    def fingerprint_generation_resume_inputs(self, current_job_directory):
        """재개 검토에 사용할 요청·상태·참조와 실행 기록의 지문을 반환한다."""
        from tools.management.domains.image.flux_resume_fingerprint import fingerprint_flux_resume_inputs
        return fingerprint_flux_resume_inputs(current_job_directory,self.current_profile_name)

    def preview_generation_resume(self, current_job_directory):
        """공용 잠금 아래 원 서비스 검증과 재개 입력 지문을 확인한다."""
        import fcntl
        import os
        import re
        import stat
        from contextlib import ExitStack
        from tools.management.common.gpu_job_queue import open_gpu_resume_lock
        current_job_directory=Path(current_job_directory)
        if (not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_directory.name)
                or current_job_directory.is_symlink() or current_job_directory.parent.resolve()!=Path(self.job_storage_root).resolve()):
            raise ValueError('FLUX 재개 작업 경로 오류')
        if not current_job_directory.is_dir():raise ValueError('FLUX 재개 작업이 없습니다.')
        with ExitStack() as current_lock_resources:
            current_resume_handle=current_lock_resources.enter_context(open_gpu_resume_lock(current_job_directory))
            fcntl.flock(current_resume_handle,fcntl.LOCK_EX)
            for current_lock_name in ('execution.lock','building-pipeline.lock'):
                try:
                    current_lock_descriptor=os.open(current_job_directory/current_lock_name,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
                    current_lock_handle=current_lock_resources.enter_context(os.fdopen(current_lock_descriptor,'a'))
                    if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):raise ValueError('FLUX 실행 잠금은 일반 파일이어야 합니다.')
                    fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError as current_lock_error:
                    raise ValueError('이전 FLUX 실행이 종료되지 않았습니다.') from current_lock_error
                except OSError as current_lock_error:
                    raise ValueError('FLUX 실행 잠금을 확인할 수 없습니다.') from current_lock_error
            current_initial_value=self.fingerprint_generation_resume_inputs(current_job_directory)
            current_request_value=json.loads((current_job_directory/'request.json').read_text())
            self.validate_generation_runtime(current_request_value)
            self.validate_generation_resume(current_job_directory)
            current_final_value=self.fingerprint_generation_resume_inputs(current_job_directory)
            if current_initial_value!=current_final_value:raise ValueError('FLUX 재개 검토 중 입력이 변경됐습니다.')
            return {'service':self.current_profile_name,'id':current_job_directory.name,'status':current_final_value['status'],'expected_resume_fingerprint':current_final_value['fingerprint'],'resume_availability':self.inspect_flux_resume_availability(),'note':'저장 요청·참조와 실행 기록 및 모델 준비 충돌을 검토한 시점의 결과입니다. 실제 접수·GPU 가용성은 별도입니다.'}

    def resume_reviewed_generation_job(self,current_job_directory,current_expected_fingerprint):
        """모델 준비 충돌을 막는 동안 검토 지문을 재확인하고 접수한다."""
        from tools.management.common.model_prepare_process import hold_registered_preparation_guard
        if self.inspect_flux_resume_availability()!='available':raise ValueError('FLUX 모델 준비 충돌 상태를 확인할 수 없거나 준비 중입니다.')
        with hold_registered_preparation_guard(WORKFLOW_ROOT_PATH,'flux-image'):
            return self.resume_reviewed_generation_guarded(current_job_directory,current_expected_fingerprint)

    def resume_reviewed_generation_guarded(self,current_job_directory,current_expected_fingerprint):
        """모델 준비 잠금을 잡은 상태에서 저장 요청과 참조를 재검증한다."""
        import fcntl
        import os
        import re
        import stat
        from tools.management.common.gpu_job_queue import resume_gpu_generation
        current_job_directory=Path(current_job_directory)
        if (not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',current_job_directory.name)
                or current_job_directory.is_symlink() or not current_job_directory.is_dir() or current_job_directory.parent.resolve()!=Path(self.job_storage_root).resolve()):
            raise ValueError('FLUX 재개 작업 경로 오류')
        if not isinstance(current_expected_fingerprint,str) or not re.fullmatch(r'[a-f0-9]{64}',current_expected_fingerprint):raise ValueError('FLUX 재개 확인값 오류')
        current_initial_fingerprint=self.fingerprint_generation_resume_inputs(current_job_directory)
        if current_initial_fingerprint['fingerprint']!=current_expected_fingerprint:raise ValueError('검토한 FLUX 재개 입력이 변경됐습니다.')
        current_request_value=json.loads((current_job_directory/'request.json').read_text())
        if (current_request_value.get('translation_source_ko') or current_request_value.get('building_design_ko')) and not current_request_value.get('translated_design'):
            return self.resume_reviewed_untranslated_generation(current_job_directory,current_request_value,current_expected_fingerprint)
        current_expected_command=[str(self.select_generation_python(current_request_value)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_value)),'--job-dir',str(current_job_directory)]
        current_expected_service=self.select_generation_service(current_request_value)
        def validate_locked_flux_resume(current_locked_directory):
            try:
                current_pipeline_descriptor=os.open(current_locked_directory/'building-pipeline.lock',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
                with os.fdopen(current_pipeline_descriptor,'a') as current_pipeline_handle:
                    if not stat.S_ISREG(os.fstat(current_pipeline_handle.fileno()).st_mode):raise ValueError('번역 잠금 파일 오류')
                    try:fcntl.flock(current_pipeline_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError as current_lock_error:raise ValueError('이전 번역 작업이 종료되지 않았습니다.') from current_lock_error
                    if self.fingerprint_generation_resume_inputs(current_locked_directory)['fingerprint']!=current_expected_fingerprint:raise ValueError('검토한 FLUX 재개 입력이 변경됐습니다.')
                    current_locked_request=json.loads((current_locked_directory/'request.json').read_text())
                    current_locked_command=[str(self.select_generation_python(current_locked_request)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_locked_request)),'--job-dir',str(current_locked_directory)]
                    if current_locked_command!=current_expected_command or self.select_generation_service(current_locked_request)!=current_expected_service:raise ValueError('검토한 FLUX 실행 명령이 변경됐습니다.')
                    self.validate_generation_runtime(current_locked_request)
                    self.validate_generation_resume(current_locked_directory)
                    if self.fingerprint_generation_resume_inputs(current_locked_directory)['fingerprint']!=current_expected_fingerprint:raise ValueError('FLUX 재개 검증 중 입력이 변경됐습니다.')
            except OSError as current_lock_error:
                raise ValueError('FLUX 번역 잠금을 확인할 수 없습니다.') from current_lock_error
        current_legacy_record={'command':current_expected_command,'service':current_expected_service}
        return resume_gpu_generation(current_job_directory,legacy_command_record=current_legacy_record,expected_resume_service=current_expected_service,expected_resume_command=current_expected_command,resume_locked_preflight_callback=validate_locked_flux_resume)

    def resume_reviewed_untranslated_generation(self,current_job_directory,current_request_value,current_expected_fingerprint):
        """번역 전 FLUX 작업의 입력을 잠금 안에서 재검증한 뒤 연결 작업자를 시작한다."""
        import fcntl
        import os
        import stat
        from contextlib import ExitStack
        from tools.management.common.generation_records import write_record_atomically
        from tools.management.common.gpu_job_queue import open_gpu_resume_lock,open_gpu_resume_log
        with open_gpu_resume_lock(current_job_directory) as current_resume_handle:
            fcntl.flock(current_resume_handle,fcntl.LOCK_EX)
            with ExitStack() as current_lock_resources:
                for current_lock_name in ('execution.lock','building-pipeline.lock'):
                    try:
                        current_lock_descriptor=os.open(current_job_directory/current_lock_name,os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
                        current_lock_handle=current_lock_resources.enter_context(os.fdopen(current_lock_descriptor,'a'))
                        if not stat.S_ISREG(os.fstat(current_lock_handle.fileno()).st_mode):raise ValueError('FLUX 실행 잠금 파일 오류')
                        fcntl.flock(current_lock_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError as current_lock_error:
                        raise ValueError('이전 FLUX 실행이 종료되지 않았습니다.') from current_lock_error
                    except OSError as current_lock_error:
                        raise ValueError('FLUX 실행 잠금을 확인할 수 없습니다.') from current_lock_error
                if self.fingerprint_generation_resume_inputs(current_job_directory)['fingerprint']!=current_expected_fingerprint:raise ValueError('검토한 FLUX 재개 입력이 변경됐습니다.')
                current_locked_request=json.loads((current_job_directory/'request.json').read_text())
                self.validate_generation_runtime(current_locked_request)
                self.validate_generation_resume(current_job_directory)
                if self.fingerprint_generation_resume_inputs(current_job_directory)['fingerprint']!=current_expected_fingerprint:raise ValueError('FLUX 재개 검증 중 입력이 변경됐습니다.')
                current_request_value=current_locked_request
            with open_gpu_resume_log(current_job_directory) as current_log_handle:
                (current_job_directory/'cancel.request').unlink(missing_ok=True)
                write_record_atomically(current_job_directory/'status.json',{'status':'queued','stage':'translation','message':'번역 대기열 재개 중'})
                try:self.launch_generation_worker(current_job_directory,current_request_value,current_log_handle)
                except (OSError,ValueError):
                    write_record_atomically(current_job_directory/'status.json',{'status':'failed','stage':'translation','error':'번역 연결 작업자를 시작하지 못했습니다. 실행 환경과 로그를 확인하세요.'})
                    raise
        return {'id':current_job_directory.name,'status':'queued'}

    def validate_generation_resume(self, selected_job_directory):
        current_request_record = json.loads((selected_job_directory/'request.json').read_text())
        if self.current_profile_name == 'flux-seamless' and current_request_record.get('seamless_method','edge-blend') not in FLUX_SEAMLESS_METHOD_VALUES:
            raise ValueError('저장된 심리스 처리 방식이 올바르지 않습니다.')
        verify_reference_snapshots(selected_job_directory,current_request_record)
        if 'translation_source_ko' in current_request_record:
            from tools.management.domains.image.flux_translation_queue import validate_flux_translation_record
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
        current_allowed_steps = range(1, 51) if self.current_profile_name == 'flux-character' else (16,)
        if type(current_request_record.get('steps')) is not int or current_request_record['steps'] not in current_allowed_steps or type(current_request_record.get('seed')) is not int or not 0 <= current_request_record['seed'] <= 4294967295:
            raise ValueError('저장된 스텝 또는 시드가 올바르지 않습니다.')
        current_maximum_size = 2048 if self.current_profile_name == 'flux-character' else 1664
        if any(type(current_request_record.get(name)) is not int or not 256 <= current_request_record[name] <= current_maximum_size or current_request_record[name] % 16 for name in ('width','height')):
            raise ValueError('저장된 출력 크기가 올바르지 않습니다.')
        if (current_request_record.get('building_design_ko') or current_request_record.get('translation_source_ko')) and not (selected_job_directory/'gpu-command.json').exists():
            return
        current_command_record=json.loads((selected_job_directory/'gpu-command.json').read_text())
        if Path(current_command_record['command'][1]).resolve() != (WORKFLOW_ROOT_PATH/self.select_generation_runner()).resolve():
            raise ValueError('저장된 실행기가 일치하지 않습니다.')
