"""프롬프트 번역을 공용 GPU 대기열과 연결한다."""
from contextlib import contextmanager
import fcntl
import threading
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import uuid
from zoneinfo import ZoneInfo
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation, resume_gpu_generation
from tools.review.common.management_transport import validate_management_http_request, send_management_json_response
from tools.review.common.generation_cleanup import delete_generation_job_files, describe_generation_cleanup, read_cleanup_confirmation
from generators.prompt_translation.terms import validate_translation_glossary, load_approved_translation_terms

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
TRANSLATION_JOB_ROOT = WORKFLOW_ROOT_DIRECTORY / '.tmp/test/prompt-translation'
TRANSLATION_MODEL_ROOT = WORKFLOW_ROOT_DIRECTORY / '.model/prompt-translation'
TRANSLATION_PYTHON_PATH = WORKFLOW_ROOT_DIRECTORY / '.local/venvs/kimodo-rocm/bin/python'
TRANSLATION_JOB_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}')



def validate_translation_submission(translation_payload_record):
    """기존 번역 입력과 승인 용어 정책을 부작용 없이 검증한다."""
    if not {'text', 'target_language'} <= set(translation_payload_record) or set(translation_payload_record) - {'text', 'target_language', 'glossary'}:
        raise ValueError('원문·목표 언어와 선택 용어만 전달하세요.')
    translation_source_text = translation_payload_record['text']
    translation_target_language = translation_payload_record['target_language']
    if not isinstance(translation_source_text, str) or not translation_source_text.strip() or len(translation_source_text) > 6000:
        raise ValueError('원문은 1~6000자여야 합니다.')
    if translation_target_language not in ('en', 'zh-CN'):
        raise ValueError('목표 언어는 영어 또는 중국어 간체여야 합니다.')
    translation_glossary_values = validate_translation_glossary(translation_payload_record.get('glossary', []))
    if any(current_term_record['source'] not in translation_source_text for current_term_record in translation_glossary_values):
        raise ValueError('지정한 원문 용어가 입력에 없습니다.')
    translation_approved_records = load_approved_translation_terms(translation_target_language)
    translation_approved_lookup = {current_term['source']: current_term['target'] for current_term in translation_approved_records}
    if any(current_term['source'] in translation_approved_lookup and current_term['target'] != translation_approved_lookup[current_term['source']] for current_term in translation_glossary_values):
        raise ValueError('입력한 용어가 승인 용어집과 충돌합니다.')
    translation_check_records = [current_term for current_term in translation_approved_records if current_term['source'] in translation_source_text]
    translation_check_records.extend({**current_term, 'source_ref':'사용자가 요청에서 확인'} for current_term in translation_glossary_values if current_term['source'] not in translation_approved_lookup)
    return {'text':translation_source_text, 'target_language':translation_target_language, 'glossary':translation_glossary_values, 'check_terms':translation_check_records}


def validate_translation_resume_record(current_request_record):
    """저장된 번역 요청이 현재 입력·용어 계약과 일치하는지 확인한다."""
    if not isinstance(current_request_record,dict) or set(current_request_record)!={'text','target_language','glossary','check_terms','model_id'} or current_request_record.get('model_id')!='google/translategemma-4b-it':
        raise ValueError('저장된 번역 요청 형식 오류')
    current_validated_record=validate_translation_submission({current_field_name:current_request_record[current_field_name] for current_field_name in ('text','target_language','glossary')})
    if current_request_record!={**current_validated_record,'model_id':'google/translategemma-4b-it'}:
        raise ValueError('저장된 번역 요청이나 승인 용어가 현재 계약과 다릅니다.')


def build_translation_worker_command(current_job_directory):
    """번역 서비스의 고정 작업 실행 명령을 만든다."""
    return [str(TRANSLATION_PYTHON_PATH),str(WORKFLOW_ROOT_DIRECTORY/'generators/prompt_translation/worker.py'),'--job-dir',str(current_job_directory)]


class TranslationServiceManager:
    def __init__(self):
        self.job_storage_root = TRANSLATION_JOB_ROOT
        self.translation_thread_lock = threading.RLock()

    def resolve_translation_job(self, translation_job_identifier):
        if not isinstance(translation_job_identifier, str) or not TRANSLATION_JOB_PATTERN.fullmatch(translation_job_identifier):
            raise ValueError('번역 작업 ID 형식 오류')
        translation_job_path = self.job_storage_root / translation_job_identifier
        if translation_job_path.is_symlink() or not translation_job_path.is_dir():
            raise ValueError('번역 작업을 찾을 수 없습니다.')
        return translation_job_path

    @contextmanager
    def hold_translation_service_lock(self):
        self.job_storage_root.mkdir(parents=True, exist_ok=True)
        with self.translation_thread_lock, (self.job_storage_root / '.service.lock').open('a') as translation_lock_handle:
            fcntl.flock(translation_lock_handle, fcntl.LOCK_EX)
            yield

    def execute_translation_command(self, translation_command_name, translation_payload_record):
        with self.hold_translation_service_lock():
            return self.execute_locked_translation_command(translation_command_name, translation_payload_record)

    def execute_locked_translation_command(self, translation_command_name, translation_payload_record):
        if not isinstance(translation_payload_record, dict):
            raise ValueError('입력은 객체여야 합니다.')
        if translation_command_name == 'translation-submit':
            translation_validated_record = validate_translation_submission(translation_payload_record)
            if not TRANSLATION_PYTHON_PATH.is_file() or not (TRANSLATION_MODEL_ROOT / 'manifest.json').is_file():
                raise ValueError('TranslateGemma 모델과 ROCm 환경을 먼저 준비하세요.')
            translation_created_time = datetime.now(ZoneInfo('Asia/Seoul'))
            translation_job_identifier = translation_created_time.strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8]
            translation_job_path = self.job_storage_root / translation_job_identifier
            translation_job_path.mkdir(parents=True)
            write_record_atomically(translation_job_path / 'request.json', {**translation_validated_record, 'model_id': 'google/translategemma-4b-it'})
            with (translation_job_path / 'worker.log').open('a') as translation_log_handle:
                launch_gpu_process(build_translation_worker_command(translation_job_path), translation_job_path, 'prompt-translation', stdout=translation_log_handle, stderr=subprocess.STDOUT, start_new_session=True, cwd=WORKFLOW_ROOT_DIRECTORY)
            return {'id': translation_job_identifier, 'status': 'queued'}
        if translation_command_name == 'translation-rag':
            if set(translation_payload_record) != {'text'} or not isinstance(translation_payload_record['text'], str) or not translation_payload_record['text'].strip() or len(translation_payload_record['text']) > 6000:
                raise ValueError('검색할 원문은 1~6000자여야 합니다.')
            from generators.writer_agent.documents import load_workspace_config
            from generators.writer_agent.index import load_current_index, tokenize_search_terms
            _, translation_chunk_records = load_current_index(load_workspace_config())
            translation_query_terms = tokenize_search_terms(translation_payload_record['text'])
            translation_matches = []
            for translation_chunk_record in translation_chunk_records:
                translation_matching_terms = translation_query_terms & tokenize_search_terms(translation_chunk_record['heading'] + ' ' + translation_chunk_record['text'])
                if translation_matching_terms:
                    translation_matches.append({'path':translation_chunk_record['path'], 'heading':translation_chunk_record['heading'], 'text':translation_chunk_record['text'][:1200], 'matched_terms':sorted(translation_matching_terms)})
            translation_matches.sort(key=lambda current_match: (-len(current_match['matched_terms']), current_match['path'], current_match['heading']))
            return {'candidates':translation_matches[:5], 'method':'작가 AI 최신 RAG 색인의 단어 일치 · 승인된 번역어가 아닌 문서 근거'}
        if translation_command_name == 'history-observe':
            from tools.review.common.generation_records import observe_generation_history_records
            return observe_generation_history_records(None,self.job_storage_root,translation_payload_record)
        if translation_command_name == 'translation-history':
            if translation_payload_record:
                raise ValueError('이력은 입력을 받지 않습니다.')
            if not self.job_storage_root.exists():
                return {'records': []}
            return {'records': [self.read_translation_job(current_job_path) for current_job_path in sorted(self.job_storage_root.iterdir(), reverse=True) if current_job_path.is_dir() and not current_job_path.is_symlink() and TRANSLATION_JOB_PATTERN.fullmatch(current_job_path.name)][:100]}
        if translation_command_name in ('history', 'history-reset-preview', 'history-reset'):
            if translation_command_name != 'history-reset' and translation_payload_record:
                raise ValueError('이 명령은 입력을 받지 않습니다.')
            translation_job_targets = [current_job_path for current_job_path in self.job_storage_root.iterdir() if TRANSLATION_JOB_PATTERN.fullmatch(current_job_path.name)]
            if translation_command_name == 'history':
                translation_history_records = []
                for current_job_path in sorted(translation_job_targets, reverse=True):
                    if current_job_path.is_symlink() or not current_job_path.is_dir():
                        raise ValueError('번역 작업 경로 오류')
                    current_job_record = self.read_translation_job(current_job_path)
                    current_job_record['path'] = str(current_job_path)
                    current_job_record['request'] = {**current_job_record['request'], 'prompt': current_job_record['request']['text']}
                    translation_history_records.append(current_job_record)
                return {'records': translation_history_records}
            if translation_command_name == 'history-reset-preview':
                return describe_generation_cleanup(self.job_storage_root, translation_job_targets)
            translation_expected_jobs = read_cleanup_confirmation(translation_payload_record)
            return delete_generation_job_files(self.job_storage_root, translation_job_targets, current_expected_jobs=translation_expected_jobs)
        current_allowed_fields={'id','expected_resume_fingerprint'} if translation_command_name=='resume' else {'id'}
        if 'id' not in translation_payload_record or set(translation_payload_record)-current_allowed_fields:
            raise ValueError('작업 ID와 허용된 재개 확인값만 전달하세요.')
        translation_job_path = self.resolve_translation_job(translation_payload_record['id'])
        if translation_command_name == 'status':
            translation_job_record = self.read_translation_job(translation_job_path)
            translation_status_record = dict(translation_job_record['status'])
            translation_status_record['result'] = translation_job_record['result']
            translation_status_record['id'] = translation_job_path.name
            translation_log_path = translation_job_path / 'worker.log'
            if translation_log_path.is_file() and not translation_log_path.is_symlink():
                with translation_log_path.open('rb') as translation_log_handle:
                    translation_log_handle.seek(max(0, translation_log_path.stat().st_size - 16000))
                    translation_status_record['log'] = translation_log_handle.read().decode(errors='replace')
            if not (translation_job_path / 'gpu-command.json').is_file():
                translation_status_record.update(resume_allowed=False, resume_block_reason='생성 재개 불가 · 실행 기록 없음')
            return translation_status_record
        if translation_command_name == 'logs':
            return {'log': self.execute_locked_translation_command('status', translation_payload_record).get('log', '')}
        if translation_command_name == 'history-delete':
            return delete_generation_job_files(self.job_storage_root, [translation_job_path])
        if translation_command_name == 'resume-preview':
            from tools.review.common.gpu_job_queue import preview_gpu_resume_records
            current_preview_record=preview_gpu_resume_records(translation_job_path,'prompt-translation',build_translation_worker_command(translation_job_path),validate_translation_resume_record)
            return {'id':translation_job_path.name,'service':'prompt-translation',**current_preview_record,'note':'검토 시점 기록이며 실제 재개나 GPU 사용 가능 여부는 별도 확인합니다.'}
        if translation_command_name == 'resume':
            if 'expected_resume_fingerprint' in translation_payload_record:
                current_fingerprint_value=translation_payload_record['expected_resume_fingerprint']
                if not isinstance(current_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',current_fingerprint_value):raise ValueError('재개 확인값 형식 오류')
                validate_translation_resume_record(json.loads((translation_job_path/'request.json').read_text()))
                return resume_gpu_generation(translation_job_path,expected_resume_fingerprint=current_fingerprint_value,expected_resume_service='prompt-translation',expected_resume_command=build_translation_worker_command(translation_job_path))
            return resume_gpu_generation(translation_job_path)
        if translation_command_name == 'cancel':
            return cancel_gpu_generation(translation_job_path)
        if translation_command_name == 'translation-status':
            return self.read_translation_job(translation_job_path)
        if translation_command_name == 'translation-cancel':
            return cancel_gpu_generation(translation_job_path)
        raise ValueError('지원하지 않는 번역 명령입니다.')

    def read_translation_job(self, translation_job_path):
        def read_translation_record(translation_record_path):
            return json.loads(translation_record_path.read_text(encoding='utf-8'))
        translation_status_record = read_translation_record(translation_job_path / 'status.json')
        translation_result_path = translation_job_path / 'result.json'
        return {'id': translation_job_path.name, 'request': read_translation_record(translation_job_path / 'request.json'), 'status': translation_status_record, 'result': read_translation_record(translation_result_path) if translation_status_record.get('status') == 'completed' and translation_result_path.is_file() else None}

    def handle_translation_request(self, translation_http_handler):
        from tools.review.common.management_gateway import identify_management_command
        try:
            validate_management_http_request(translation_http_handler)
            translation_command_match = identify_management_command(translation_http_handler.path, translation_http_handler.command, getattr(translation_http_handler, 'management_command_payload', {}))
            if not translation_command_match or translation_command_match[0] != 'prompt-translation':
                raise ValueError('지원하지 않는 번역 요청입니다.')
            translation_response_record = self.execute_translation_command(translation_command_match[1], translation_command_match[2])
            if translation_command_match[1] == 'logs':
                translation_log_bytes = translation_response_record['log'].encode('utf-8')
                translation_http_handler.send_response(200)
                translation_http_handler.send_header('Content-Type', 'text/plain; charset=utf-8')
                translation_http_handler.send_header('Content-Length', str(len(translation_log_bytes)))
                translation_http_handler.end_headers()
                translation_http_handler.wfile.write(translation_log_bytes)
                return True
            send_management_json_response(translation_http_handler, 200, translation_response_record)
        except (OSError, ValueError, KeyError, TypeError) as translation_request_error:
            send_management_json_response(translation_http_handler, 400, {'error': str(translation_request_error)})
        return True
