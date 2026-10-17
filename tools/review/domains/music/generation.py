"""음악생성 공용 작업 서비스: GUI·CLI는 같은 이력과 GPU 대기열을 사용한다."""
from contextlib import contextmanager
from tools.review.common.generation_cleanup import delete_generation_job_files, describe_generation_cleanup, read_cleanup_confirmation
from datetime import datetime
import fcntl
import json
from pathlib import Path
import re
import subprocess
import threading
from urllib.parse import urlsplit
import uuid
from zoneinfo import ZoneInfo
from generators.music.contracts import WORKFLOW_ROOT_DIRECTORY, MUSIC_IDENTIFIER_PATTERN, build_music_request, read_music_record, resolve_music_paths, resolve_music_profile, validate_music_identifier, verify_music_request
from tools.review.common.generation_records import write_record_atomically, load_generation_history_records
from tools.review.common.generation_estimates import calculate_generation_estimate
from tools.review.common.gpu_job_queue import launch_gpu_process, cancel_gpu_generation, resume_gpu_generation
from tools.review.common.management_transport import validate_management_http_request, send_management_json_response


class MusicGenerationManager:
    def __init__(self,current_service_name):
        self.current_service_name = current_service_name
        self.current_profile_record = resolve_music_profile(current_service_name)
        self.job_storage_root,self.model_storage_root,self.runtime_python_path = resolve_music_paths(current_service_name)
        self.route_prefix_value = '/'+current_service_name
        self.audio_output_filename = 'sound.wav' if current_service_name=='sfx-stable-audio' else 'music.wav'
        self.history_storage_root = WORKFLOW_ROOT_DIRECTORY/'.tmp/manager-current'/current_service_name
        self.current_request_lock = threading.RLock()

    @contextmanager
    def hold_music_lock(self):
        self.history_storage_root.mkdir(parents=True,exist_ok=True)
        with self.current_request_lock,(self.history_storage_root/'service.lock').open('a') as current_service_lock:
            fcntl.flock(current_service_lock,fcntl.LOCK_EX)
            yield

    def resolve_music_job(self,current_identifier_value):
        validate_music_identifier(current_identifier_value)
        current_job_root = self.job_storage_root/current_identifier_value
        if current_job_root.is_symlink() or not current_job_root.is_dir() or current_job_root.resolve().parent != self.job_storage_root.resolve():
            raise ValueError('음악 작업 경로가 없거나 허용되지 않습니다.')
        return current_job_root

    def create_music_job(self,current_payload_record):
        current_request_record = build_music_request(self.current_service_name,current_payload_record)
        if not self.runtime_python_path.is_file():
            raise FileNotFoundError(f"음악 실행 환경이 없습니다: {self.runtime_python_path}. 해당 생성기 README.md의 설치 절차를 먼저 실행하세요. model_id={self.current_profile_record['model_id']} model_root={self.model_storage_root} model_path={self.model_storage_root}")
        with self.hold_music_lock():
            current_created_time = datetime.now(ZoneInfo('Asia/Seoul'))
            current_job_identifier = current_created_time.strftime('%Y-%m-%d_%H-%M-%S')+'-'+uuid.uuid4().hex[:8]
            current_job_root = self.job_storage_root/current_job_identifier
            current_job_root.mkdir(parents=True)
            write_record_atomically(current_job_root/'request.json',current_request_record)
            write_record_atomically(current_job_root/'status.json',{'status':'queued'})
            write_record_atomically(self.history_storage_root/(current_job_identifier+'.json'),{'id':current_job_identifier,'created_at':current_created_time.isoformat(),'request':current_request_record,'path':str(current_job_root)})
            with (current_job_root/'worker.log').open('a') as current_log_handle:
                launch_gpu_process([str(self.runtime_python_path),'-u',str(WORKFLOW_ROOT_DIRECTORY/'generators/music/worker.py'),'--service',self.current_service_name,'--job-dir',str(current_job_root)],current_job_root,self.current_service_name,
                    stdout=current_log_handle,stderr=subprocess.STDOUT,start_new_session=True,cwd=WORKFLOW_ROOT_DIRECTORY)
        return {'id':current_job_identifier,'status':'queued'}

    def read_music_status(self,current_job_root,current_include_logs=True):
        current_status_record = read_music_record(current_job_root/'status.json')
        current_status_record['id'] = current_job_root.name
        current_attempt_path = current_job_root/'current-attempt.json'
        if current_attempt_path.is_file() and current_status_record['status']!='queued':
            current_attempt_name = read_music_record(current_attempt_path)['id']
            if not re.fullmatch('[a-f0-9]{32}',current_attempt_name):
                raise ValueError('음악 실행 시도 ID 오류')
            current_attempt_root = current_job_root/'attempts'/current_attempt_name
            if not current_attempt_root.resolve().is_relative_to(current_job_root.resolve()):
                raise ValueError('음악 실행 시도 경로 오류')
            current_metrics_path = current_attempt_root/'metrics.json'
            if current_metrics_path.is_file():
                current_metrics_record = read_music_record(current_metrics_path)
                current_status_record.update(metrics=current_metrics_record,estimate=current_metrics_record['estimate'])
            current_error_path = current_attempt_root/'error.json'
            if current_error_path.is_file():
                current_status_record['error'] = read_music_record(current_error_path)['error']
        if 'estimate' not in current_status_record or current_status_record['status'] not in ('running','queued'):
            current_status_record['estimate'] = calculate_generation_estimate(current_status_record,[],'동일 모델·길이·GPU의 성공 실행 표본 수집 중','GPU 대기 제외; 모델 준비·추론·저장')
        current_result_path = current_job_root/'result.json'
        if current_status_record['status']=='completed' and current_result_path.is_file():
            current_result_record = read_music_record(current_result_path)
            current_status_record['result'] = current_result_record
            if current_result_record.get('format')=='wav':
                current_status_record['audio'] = f"{self.route_prefix_value}/jobs/{current_job_root.name}/attempts/{current_result_record['attempt']}/{self.audio_output_filename}"
        if current_include_logs:
            current_log_path = current_job_root/'worker.log'
            if current_log_path.is_file():
                with current_log_path.open('rb') as current_log_handle:
                    current_log_handle.seek(max(0,current_log_path.stat().st_size-16000))
                    current_status_record['log'] = current_log_handle.read().decode(errors='replace')
        return current_status_record

    def list_music_history(self):
        current_history_records = load_generation_history_records(self.history_storage_root,self.job_storage_root)
        for current_history_record in current_history_records:
            current_job_root = self.resolve_music_job(current_history_record['id'])
            current_history_record.update(status=self.read_music_status(current_job_root),path=str(current_job_root))
        return current_history_records

    def delete_music_history(self,current_identifier_value):
        current_job_root = self.resolve_music_job(current_identifier_value)
        with self.hold_music_lock():
            current_cleanup_result = delete_generation_job_files(self.job_storage_root,[current_job_root],[self.history_storage_root/(current_identifier_value+'.json')])
        return {**current_cleanup_result,'deleted':current_identifier_value}

    def execute_music_command(self,current_command_name,current_payload_record):
        current_allowed_fields = {'generate':{'action','prompt','duration_seconds','seed','loop_request','tag'},'prepare':{'action'},'status':{'id'},'logs':{'id'},'history':{'page'},'active':set(),'model-status':set(),'cancel':{'id'},'resume':{'id'},'history-delete':{'id'},'history-reset':{'action','expected_jobs'},'history-reset-preview':set()}
        if current_command_name not in current_allowed_fields or not isinstance(current_payload_record,dict) or set(current_payload_record)-current_allowed_fields[current_command_name]:
            raise ValueError('음악 명령·필드 오류')
        if current_command_name in ('generate','prepare'):
            return self.create_music_job(current_payload_record)
        if current_command_name=='model-status':
            from generators.music.runtime import validate_prepared_music
            if self.current_service_name == 'sfx-stable-audio':
                from generators.sound_effects.runtime import validate_effects_model as validate_prepared_music
            try:
                validate_prepared_music(self.current_service_name)
                return {'ready':True,'message':'모델 준비됨 · VRAM 관측 피크는 실행 이력에서 확인','model_id':self.current_profile_record['model_id']}
            except (OSError,ValueError,KeyError) as current_prepare_error:
                return {'ready':False,'message':str(current_prepare_error),'model_id':self.current_profile_record['model_id']}
        if current_command_name in ('history','active'):
            current_history_records = self.list_music_history()
            if current_command_name=='history':
                return {'records':current_history_records}
            current_active_record = next((current_history_record for current_history_record in current_history_records if current_history_record['status']['status'] in ('running','queued')),None)
            return {'id':current_active_record['id'] if current_active_record else None}
        if current_command_name in ('history-reset','history-reset-preview'):
            current_expected_jobs=read_cleanup_confirmation(current_payload_record) if current_command_name=='history-reset' else None
            with self.hold_music_lock():
                current_job_targets = [current_job_path for current_job_path in self.job_storage_root.iterdir() if re.fullmatch(MUSIC_IDENTIFIER_PATTERN,current_job_path.name)] if self.job_storage_root.exists() else []
                if current_command_name=='history-reset-preview':
                    current_preview_record = describe_generation_cleanup(self.job_storage_root,current_job_targets)
                    current_preview_record['scope'] = self.current_profile_record['label']+' · '+current_preview_record['scope']
                    return current_preview_record
                return delete_generation_job_files(self.job_storage_root,current_job_targets,self.history_storage_root.glob('*.json'),current_expected_jobs)
        current_job_root = self.resolve_music_job(current_payload_record['id'])
        if current_command_name=='status':
            return self.read_music_status(current_job_root)
        if current_command_name=='logs':
            return {'log':self.read_music_status(current_job_root).get('log','')}
        if current_command_name=='history-delete':
            return self.delete_music_history(current_job_root.name)
        with self.hold_music_lock():
            if (current_job_root/'.history-deleted').exists():
                raise ValueError('삭제한 이력은 재개·중지할 수 없습니다. 새 작업으로 등록하세요.')
            if current_command_name=='resume':
                verify_music_request(self.current_service_name,read_music_record(current_job_root/'request.json'))
                return resume_gpu_generation(current_job_root)
            return cancel_gpu_generation(current_job_root)

    def handle_music_request(self,current_http_handler):
        from tools.review.common.management_gateway import identify_management_command
        try:
            validate_management_http_request(current_http_handler)
            current_url_path = urlsplit(current_http_handler.path).path
            current_file_match = re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/('+MUSIC_IDENTIFIER_PATTERN+r')/attempts/([a-f0-9]{32})/'+re.escape(self.audio_output_filename),current_url_path)
            if current_http_handler.command=='GET' and current_file_match:
                current_job_root = self.resolve_music_job(current_file_match[1])
                current_audio_path = current_job_root/'attempts'/current_file_match[2]/self.audio_output_filename
                if not current_audio_path.resolve().is_relative_to(current_job_root.resolve()):
                    raise ValueError('음악 결과 경로 오류')
                current_response_bytes = current_audio_path.read_bytes()
                current_http_handler.send_response(200)
                current_http_handler.send_header('Content-Type','audio/wav')
                current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
                current_http_handler.send_header('Cache-Control','no-store')
                current_http_handler.end_headers()
                current_http_handler.wfile.write(current_response_bytes)
                return True
            current_payload_record = getattr(current_http_handler,'management_command_payload',{})
            current_command_match = identify_management_command(current_http_handler.path,current_http_handler.command,current_payload_record)
            if current_command_match is None or current_command_match[0] != self.current_service_name:
                raise ValueError('지원하지 않는 음악 요청 경로')
            current_response_record = self.execute_music_command(current_command_match[1],current_command_match[2])
            # 공용 CLI logs는 text/plain 응답 계약을 사용한다.
            if current_command_match[1]=='logs':
                current_response_bytes = current_response_record['log'].encode()
                current_http_handler.send_response(200)
                current_http_handler.send_header('Content-Type','text/plain; charset=utf-8')
                current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
                current_http_handler.end_headers()
                current_http_handler.wfile.write(current_response_bytes)
            else:
                send_management_json_response(current_http_handler,200,current_response_record)
        except (OSError,ValueError,KeyError,TypeError) as current_request_error:
            send_management_json_response(current_http_handler,400,{'error':str(current_request_error)})
        return True
