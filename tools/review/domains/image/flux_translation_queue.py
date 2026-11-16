"""FLUX 생성기의 번역 대기·취소·재개 공용 처리."""
import json
import hashlib
import subprocess
from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH


def validate_flux_translation_runtime(current_request_record):
    if current_request_record and (current_request_record.get('translation_source_ko') or current_request_record.get('building_design_ko')) and not current_request_record.get('translated_design'):
        from tools.review.domains.translation.service import TRANSLATION_MODEL_ROOT, TRANSLATION_PYTHON_PATH
        if not TRANSLATION_PYTHON_PATH.is_file() or not (TRANSLATION_MODEL_ROOT / 'manifest.json').is_file():
            raise ValueError('한국어 프롬프트 번역을 위해 TranslateGemma 모델과 ROCm 환경을 먼저 준비하세요.')


def validate_flux_translation_record(current_job_path, current_request_record, expression_mode_enabled=False):
    current_source_text=current_request_record.get('translation_source_ko')
    current_base_text=current_request_record.get('translation_base_prompt')
    current_translated_text=current_request_record.get('translated_design')
    if not isinstance(current_source_text,str) or not current_source_text.strip() or not isinstance(current_base_text,str):
        raise ValueError('저장된 한국어 원문 또는 준비 문구가 올바르지 않습니다.')
    if current_translated_text is not None and (not isinstance(current_translated_text,str) or not current_translated_text.strip()):
        raise ValueError('저장된 번역문이 올바르지 않습니다.')
    current_combined_text=' '.join(filter(None,(current_base_text.strip(),current_translated_text.strip() if current_translated_text else '')))
    if expression_mode_enabled:
        current_expected_text=current_combined_text
    else:
        from generators.image.common_art_style import compose_common_style_prompt
        current_expected_text,_=compose_common_style_prompt(current_combined_text)
    if current_request_record.get('user_prompt') != current_combined_text or current_request_record.get('prompt') != current_expected_text:
        raise ValueError('저장된 번역·준비 문구·최종 프롬프트가 일치하지 않습니다.')
    current_pipeline_path=current_job_path/'translation-pipeline.json'
    if current_pipeline_path.exists():
        current_pipeline_record=json.loads(current_pipeline_path.read_text())
        if current_pipeline_record.get('source_sha256') != hashlib.sha256(current_source_text.encode()).hexdigest():
            raise ValueError('저장된 한국어 원문과 번역 작업이 일치하지 않습니다.')
        if current_translated_text and (not isinstance(current_request_record.get('translation'),dict) or current_request_record['translation'].get('id') != current_pipeline_record.get('translation_id')):
            raise ValueError('저장된 번역 작업 ID가 일치하지 않습니다.')
    elif current_translated_text:
        raise ValueError('완료된 번역 작업 정보가 없습니다.')


class FluxTranslationQueueMixin:
    def launch_generation_worker(self, current_job_root, current_request_record, current_log_handle):
        if (current_request_record.get('translation_source_ko') or current_request_record.get('building_design_ko')) and not current_request_record.get('translated_design'):
            from tools.review.common.generation_records import write_record_atomically
            write_record_atomically(current_job_root/'status.json', {'status':'queued','stage':'translation','message':'번역 대기열 등록 중'})
            return subprocess.Popen([str(self.select_generation_python(current_request_record)),str(WORKFLOW_ROOT_PATH/'generators/image/run_flux_translation_pipeline.py'),'--job-dir',str(current_job_root)],stdout=current_log_handle,stderr=subprocess.STDOUT,start_new_session=True,cwd=WORKFLOW_ROOT_PATH)
        return super().launch_generation_worker(current_job_root,current_request_record,current_log_handle)

    def resume_generation_job(self, selected_job_directory, saved_request_record, legacy_command_record):
        if (saved_request_record.get('translation_source_ko') or saved_request_record.get('building_design_ko')) and not saved_request_record.get('translated_design'):
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
        for current_history_record in current_history_records:
            current_request_path=self.job_storage_root/current_history_record['id']/'request.json'
            if current_request_path.is_file():
                current_history_record['request']=json.loads(current_request_path.read_text())
        return current_history_records

