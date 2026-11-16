"""한국어 FLUX 입력을 번역 대기열과 이미지 대기열에 순차 연결한다."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.image.common_art_style import compose_common_style_prompt
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_job_queue import launch_gpu_process
from tools.review.domains.translation.service import TranslationServiceManager


def execute_flux_translation_pipeline(building_job_path):
    building_job_path = Path(building_job_path)
    allowed_profile_names = ('flux-building','flux-image','flux-character','flux-mannequin','flux-billboard','flux-prop','flux-vegetation','flux-seamless','flux-expression')
    current_profile_name = building_job_path.parent.name.removesuffix('-generator')
    if current_profile_name not in allowed_profile_names or building_job_path.parent.name != current_profile_name+'-generator':
        raise ValueError('FLUX 번역 작업 종류 오류')
    expected_job_root = (WORKFLOW_ROOT_DIRECTORY/'.tmp/test'/(current_profile_name+'-generator')).resolve()
    if building_job_path.is_symlink() or building_job_path.resolve().parent != expected_job_root:
        raise ValueError('FLUX 번역 연결 작업 경로 오류')
    building_job_path = building_job_path.resolve()
    with (building_job_path/'building-pipeline.lock').open('a') as building_lock_handle:
        fcntl.flock(building_lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        building_request_path = building_job_path/'request.json'
        building_state_path = building_job_path/'translation-pipeline.json'
        try:
            building_request_record = json.loads(building_request_path.read_text())
            building_design_text = building_request_record.get('translation_source_ko') or building_request_record.get('building_design_ko')
            if not isinstance(building_design_text,str) or not building_design_text.strip():
                raise ValueError('번역할 한국어 입력이 없습니다.')
            building_translation_manager = TranslationServiceManager()
            building_state_record = json.loads(building_state_path.read_text()) if building_state_path.is_file() else {}
            building_translation_id = building_state_record.get('translation_id')
            building_translation_record = building_translation_manager.execute_translation_command('translation-status', {'id':building_translation_id}) if building_translation_id else None
            if building_translation_record and (building_translation_record['request']['text'] != building_design_text or building_translation_record['request']['target_language'] != 'en'):
                raise ValueError('저장된 번역 작업과 한국어 입력이 일치하지 않습니다.')
            if building_translation_record:
                building_translation_path = building_translation_manager.resolve_translation_job(building_translation_id)
                while building_translation_record['status']['status'] in ('queued','running') and (building_translation_path/'cancel.request').exists():
                    if (building_job_path/'cancel.request').exists():
                        write_record_atomically(building_job_path/'status.json', {'status':'cancelled','stage':'translation','translation_id':building_translation_id,'message':'번역 단계 중지 요청'})
                        return
                    write_record_atomically(building_job_path/'status.json', {'status':'queued','stage':'translation','translation_id':building_translation_id,'message':'이전 번역 작업 종료 대기'})
                    time.sleep(1)
                    building_translation_record = building_translation_manager.execute_translation_command('translation-status', {'id':building_translation_id})
            if not building_translation_record or building_translation_record['status']['status'] in ('failed','cancelled'):
                if (building_job_path/'cancel.request').exists():
                    write_record_atomically(building_job_path/'status.json', {'status':'cancelled','message':'번역 전에 중지되었습니다.'})
                    return
                building_translation_record = building_translation_manager.execute_translation_command('translation-submit', {'text':building_design_text,'target_language':'en'})
                building_translation_id = building_translation_record['id']
                write_record_atomically(building_state_path, {'translation_id':building_translation_id,'source_sha256':hashlib.sha256(building_design_text.encode()).hexdigest()})
            print(f'프롬프트 번역 작업: {building_translation_id}',flush=True)
            building_previous_stage = None
            while True:
                building_translation_record = building_translation_manager.execute_translation_command('translation-status', {'id':building_translation_id})
                building_translation_status = building_translation_record['status']['status']
                if (building_job_path/'cancel.request').exists():
                    if building_translation_status in ('queued','running','paused'):
                        building_translation_manager.execute_translation_command('translation-cancel', {'id':building_translation_id})
                    write_record_atomically(building_job_path/'status.json', {'status':'cancelled','stage':'translation','translation_id':building_translation_id,'message':'번역 단계 중지 요청'})
                    return
                if building_translation_status == 'completed':
                    break
                if building_translation_status not in ('queued','running'):
                    raise ValueError('번역 실패: '+str(building_translation_record['status'].get('error',building_translation_status)))
                if building_previous_stage != building_translation_status:
                    write_record_atomically(building_job_path/'status.json', {'status':building_translation_status,'stage':'translation','translation_id':building_translation_id,'message':'프롬프트 번역 대기' if building_translation_status=='queued' else '프롬프트 번역 중'})
                    building_previous_stage = building_translation_status
                time.sleep(1)
            building_translation_result = building_translation_record.get('result')
            if not isinstance(building_translation_result,dict) or not isinstance(building_translation_result.get('text'),str) or not building_translation_result['text'].strip():
                raise ValueError('완료된 번역 결과가 없거나 비었습니다.')
            building_translated_text = building_translation_result['text'].strip()
            building_base_prompt = building_request_record.get('translation_base_prompt',building_request_record.get('building_base_prompt',''))
            building_combined_prompt = ' '.join(filter(None,(building_base_prompt.strip(), building_translated_text)))
            if current_profile_name == 'flux-expression':
                building_final_prompt = building_combined_prompt
                building_style_record = None
            else:
                building_final_prompt, building_style_record = compose_common_style_prompt(building_combined_prompt)
            building_request_record.update(user_prompt=building_combined_prompt,prompt=building_final_prompt,
                prompt_sha256=hashlib.sha256(building_final_prompt.encode()).hexdigest(),translated_design=building_translated_text,
                translation={'id':building_translation_id,'model_id':building_translation_result.get('model_id'),'revision':building_translation_result.get('revision'),
                    'target_language':'en','term_checks':building_translation_result.get('term_checks',[]),'quality_checks':building_translation_result.get('quality_checks',[])})
            if building_style_record is not None:
                building_request_record['common_style'] = building_style_record
            write_record_atomically(building_request_path,building_request_record)
            with (building_job_path/'resume.lock').open('a') as building_resume_handle:
                fcntl.flock(building_resume_handle,fcntl.LOCK_EX)
                if (building_job_path/'cancel.request').exists():
                    write_record_atomically(building_job_path/'status.json', {'status':'cancelled','stage':'translation','translation_id':building_translation_id,'message':'번역 완료 후 생성 전에 중지되었습니다.'})
                    return
                print('번역 완료 · 이미지 GPU 대기열 등록',flush=True)
                current_runner_name='run_flux_expression.py' if current_profile_name == 'flux-expression' else 'run_flux_image.py'
                current_service_name='flux-expression' if current_profile_name == 'flux-expression' else 'flux-image'
                building_worker_process = launch_gpu_process([str(WORKFLOW_ROOT_DIRECTORY/'.venv/bin/python'),str(WORKFLOW_ROOT_DIRECTORY/'generators/image'/current_runner_name),'--job-dir',str(building_job_path)],building_job_path,current_service_name,start_new_session=True,cwd=WORKFLOW_ROOT_DIRECTORY)
            building_worker_process.wait()
        except Exception as building_pipeline_error:
            traceback.print_exc()
            if building_job_path.exists():
                building_status_value = 'cancelled' if (building_job_path/'cancel.request').exists() else 'failed'
                write_record_atomically(building_job_path/'status.json', {'status':building_status_value,'stage':'translation','error':str(building_pipeline_error)})
            raise


if __name__ == '__main__':
    building_argument_parser = argparse.ArgumentParser()
    building_argument_parser.add_argument('--job-dir', required=True)
    execute_flux_translation_pipeline(building_argument_parser.parse_args().job_dir)
