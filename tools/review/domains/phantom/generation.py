"""Wan2.1 PHANTOM R2V 작업 서비스. 수명 관리는 공용 GPU 대기열을 사용한다."""
import fcntl
from tools.review.common.video_result_files import enrich_video_result_status
import json
import re
from urllib.parse import urlsplit
from generators.phantom.contracts import PHANTOM_JOB_STORAGE_ROOT, validate_phantom_request, validate_phantom_assets, verify_phantom_request
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT, MANAGER_HISTORY_LOCK
from tools.review.common.generation_estimates import calculate_generation_estimate
from tools.review.common.queue_generation_telemetry import merge_generation_worker_metrics

PHANTOM_JOB_IDENTIFIER_PATTERN = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}'


class PhantomGenerationManager(ImageGenerationManager):
    def __init__(self):
        super().__init__(three_reference_mode=True)
        self.route_prefix_value = '/phantom'
        self.job_storage_root = PHANTOM_JOB_STORAGE_ROOT

    def validate_generation_request(self, current_request_record):
        raise ValueError('Phantom 생성기는 폐기되었습니다. V2V 또는 FL2V를 사용하세요.')

    def validate_generation_runtime(self, saved_request_record=None):
        raise ValueError('Phantom 모델은 폐기되어 사용할 수 없습니다.')

    def validate_generation_resume(self, selected_job_directory):
        raise ValueError('Phantom 생성기는 폐기되어 재개할 수 없습니다.')

    def select_generation_runner(self, saved_request_record=None):
        raise ValueError('Phantom 실행기는 폐기되었습니다.')

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'phantom'

    def read_generation_status_record(self, current_job_root, fallback_status_record=None, include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root, fallback_status_record, include_log_value)
        current_attempt_path = current_job_root/'current-attempt.json'
        if current_attempt_path.exists() and current_status_record['status'] != 'queued':
            current_attempt_record = json.loads(current_attempt_path.read_text())
            current_metrics_path = current_job_root/'attempts'/current_attempt_record['id']/'metrics.json'
            if current_metrics_path.exists():
                current_metrics_record = json.loads(current_metrics_path.read_text())
                if not merge_generation_worker_metrics(current_status_record, current_metrics_record):
                    return self.enrich_generation_status(current_job_root, current_status_record)
                current_status_record['progress'] = {'stage':current_metrics_record['stage'],'step':current_metrics_record['step'],'total':json.loads((current_job_root/'request.json').read_text())['steps'] if (current_job_root/'request.json').exists() else None,'percent':100 if current_status_record['status']=='completed' else None,'detail':'스텝은 추론 단계만; 전체 예상값은 ETA 참조'}
        if 'estimate' not in current_status_record:
            current_status_record['estimate'] = calculate_generation_estimate(current_status_record, [], '실행 관측 수집 중', 'GPU 대기 제외; 모델 준비·추론·저장')
        return self.enrich_generation_status(current_job_root,current_status_record)

    def enrich_generation_status(self, current_job_root, current_status_record):
        return enrich_video_result_status(current_job_root, current_status_record, self.route_prefix_value)

    def list_generation_history(self):
        current_history_records = super().list_generation_history()
        for current_history_record in current_history_records:
            current_history_record['image'] = current_history_record['status'].get('image')
        return current_history_records

    def handle_image_request(self, current_http_handler):
        current_url_path = urlsplit(current_http_handler.path).path
        current_file_match = re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/('+PHANTOM_JOB_IDENTIFIER_PATTERN+r')/attempts/([a-f0-9]{32})/(preview\.mp4|frames\.zip|output-\d{3}\.png)',current_url_path)
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
                    current_response_bytes = json.dumps({'ready':True,'message':'Wan2.1 PHANTOM 1.3B 로컬 모델 준비됨'}).encode()
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
