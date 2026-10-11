"""Wan2.1 VACE R2V 작업 서비스. 수명 관리는 공용 GPU 대기열을 사용한다."""
import fcntl
import json
import re
from urllib.parse import urlsplit
from generators.vace.contracts import VACE_JOB_STORAGE_ROOT, validate_vace_request, validate_vace_assets, verify_vace_request
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, MANAGER_HISTORY_LOCK
from tools.review.common.generation_estimates import calculate_generation_estimate

VACE_JOB_IDENTIFIER_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'


class VaceGenerationManager(ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/wan21-vace'
        self.job_storage_root = VACE_JOB_STORAGE_ROOT

    def validate_generation_request(self, current_request_record):
        return validate_vace_request(current_request_record)

    def validate_generation_runtime(self, saved_request_record=None):
        validate_vace_assets()

    def validate_generation_resume(self, selected_job_directory):
        verify_vace_request(selected_job_directory)

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/vace/worker.py'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'wan21-vace'

    def delete_generation_history(self, generation_job_identifier):
        if not isinstance(generation_job_identifier, str) or not re.fullmatch(VACE_JOB_IDENTIFIER_PATTERN, generation_job_identifier):
            raise ValueError('생성 ID 형식 오류')
        current_job_root = self.job_storage_root/generation_job_identifier
        if current_job_root.is_symlink() or not current_job_root.is_dir() or self.job_storage_root.is_symlink():
            raise ValueError('작업 경로 오류')
        with self.current_request_lock, MANAGER_HISTORY_LOCK, (current_job_root/'resume.lock').open('a') as current_resume_lock:
            fcntl.flock(current_resume_lock, fcntl.LOCK_EX)
            if json.loads((current_job_root/'status.json').read_text())['status'] not in ('completed','failed','cancelled'):
                raise ValueError('실행·대기 중에는 이력을 삭제할 수 없습니다.')
            (current_job_root/'.history-deleted').touch()
            (self.history_storage_path()/(generation_job_identifier+'.json')).unlink(missing_ok=True)
        return {'deleted':generation_job_identifier,'files_preserved':True}

    def reset_generation_history(self):
        # 원본은 보존하고 개별 삭제와 같은 작업 잠금·상태 검증을 적용한다.
        current_history_records = self.list_generation_history()
        if any(current_record_value['status']['status'] in ('running','queued') for current_record_value in current_history_records):
            raise ValueError('실행·대기 작업이 있으면 이력을 초기화할 수 없습니다.')
        for current_record_value in current_history_records:
            self.delete_generation_history(current_record_value['id'])

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root, fallback_status_record, include_log_value)
        current_attempt_path = current_job_root/'current-attempt.json'
        if current_attempt_path.exists() and current_status_record['status'] != 'queued':
            current_attempt_record = json.loads(current_attempt_path.read_text())
            current_metrics_path = current_job_root/'attempts'/current_attempt_record['id']/'metrics.json'
            if current_metrics_path.exists():
                current_metrics_record = json.loads(current_metrics_path.read_text())
                current_status_record.update(metrics=current_metrics_record, estimate=current_metrics_record['estimate'])
                current_status_record['progress'] = {'stage':current_metrics_record['stage'],'step':current_metrics_record['step'],'total':json.loads((current_job_root/'request.json').read_text())['steps'] if (current_job_root/'request.json').exists() else None,'percent':100 if current_status_record['status']=='completed' else None,'detail':'스텝은 추론 단계만; 전체 예상값은 ETA 참조'}
        if 'estimate' not in current_status_record:
            current_status_record['estimate'] = calculate_generation_estimate(current_status_record, [], '실행 관측 수집 중', 'GPU 대기 제외; 모델 준비·추론·저장')
        return self.enrich_generation_status(current_job_root,current_status_record)

    def enrich_generation_status(self, current_job_root, current_status_record):
        current_result_path = current_job_root/'result.json'
        if current_result_path.exists() and current_status_record['status']=='completed':
            current_result_record = json.loads(current_result_path.read_text())
            current_result_base = f'{self.route_prefix_value}/jobs/{current_job_root.name}/attempts/{current_result_record["attempt"]}/'
            current_status_record.update(video=current_result_base+'preview.mp4',download=current_result_base+'frames.zip',image=current_result_base+'output-000.png')
        return current_status_record

    def list_generation_history(self):
        current_history_records = super().list_generation_history()
        for current_history_record in current_history_records:
            current_history_record['image'] = current_history_record['status'].get('image')
        return current_history_records

    def handle_image_request(self, current_http_handler):
        current_url_path = urlsplit(current_http_handler.path).path
        current_file_match = re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/('+VACE_JOB_IDENTIFIER_PATTERN+r')/attempts/([a-f0-9]{32})/(preview\.mp4|frames\.zip|output-\d{3}\.png)',current_url_path)
        if current_http_handler.command == 'GET' and (current_file_match or current_url_path==self.route_prefix_value+'/model-status'):
            try:
                if current_http_handler.headers.get('Host') != f'127.0.0.1:{current_http_handler.server.server_port}':
                    raise ValueError('허용하지 않는 Host')
                if current_file_match:
                    current_file_path = self.job_storage_root/current_file_match[1]/'attempts'/current_file_match[2]/current_file_match[3]
                    if not current_file_path.resolve().is_relative_to(self.job_storage_root.resolve()):
                        raise ValueError('결과 경로 오류')
                    current_response_bytes = current_file_path.read_bytes()
                    current_content_type = 'video/mp4' if current_file_path.suffix=='.mp4' else 'application/zip' if current_file_path.suffix=='.zip' else 'image/png'
                else:
                    self.validate_generation_runtime()
                    current_response_bytes = json.dumps({'ready':True,'message':'Wan2.1 VACE 1.3B 로컬 모델 준비됨'}).encode()
                    current_content_type = 'application/json'
                current_status_code = 200
            except (ValueError,OSError) as current_error_value:
                current_status_code = 400
                current_response_bytes = json.dumps({'error':str(current_error_value)},ensure_ascii=False).encode()
                current_content_type = 'application/json'
            current_http_handler.send_response(current_status_code)
            current_http_handler.send_header('Content-Type',current_content_type)
            current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
            current_http_handler.send_header('Cache-Control','no-store')
            current_http_handler.end_headers()
            current_http_handler.wfile.write(current_response_bytes)
            return True
        return super().handle_image_request(current_http_handler)
