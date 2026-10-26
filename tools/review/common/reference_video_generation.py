"""참조 이미지 기반 영상 생성기의 공용 작업·이력·결과 파일 계약."""
import json
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT
from tools.review.common.video_result_files import enrich_video_result_status
from tools.review.common.queue_generation_telemetry import merge_generation_worker_metrics
class ReferenceVideoGenerationManager(ImageGenerationManager):
 def __init__(self,current_route_prefix,current_job_storage,current_runner_path,current_request_validator,current_assets_validator,current_assets_inspector=None):
  super().__init__(three_reference_mode=True)
  self.route_prefix_value=current_route_prefix
  self.job_storage_root=current_job_storage
  self.current_runner_path=current_runner_path
  self.current_request_validator=current_request_validator
  self.current_assets_validator=current_assets_validator
  self.current_assets_inspector=current_assets_inspector
 def validate_generation_request(self,current_request_record):
  return self.current_request_validator(current_request_record)
 def validate_generation_runtime(self,saved_request_record=None):
  self.current_assets_validator()
 def validate_generation_resume(self,selected_job_directory):
  self.current_assets_validator()
 def select_generation_runner(self,saved_request_record=None):
  return self.current_runner_path
 def history_storage_path(self):
  return MANAGER_HISTORY_ROOT/self.route_prefix_value.lstrip('/')
 def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
  current_status_record=super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
  current_attempt_path=current_job_root/'current-attempt.json'
  if current_attempt_path.exists():
   current_metrics_path=current_job_root/'attempts'/json.loads(current_attempt_path.read_text())['id']/'metrics.json'
   if current_metrics_path.exists():
    merge_generation_worker_metrics(current_status_record,json.loads(current_metrics_path.read_text()))
  return enrich_video_result_status(current_job_root,current_status_record,self.route_prefix_value)
 def handle_image_request(self,current_http_handler):
  import re
  from urllib.parse import urlsplit
  current_url_path=urlsplit(current_http_handler.path).path
  current_file_match=re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8})/attempts/([a-f0-9]{32})/(preview\.mp4|frames\.zip|output-\d{3}\.png)',current_url_path)
  if current_http_handler.command=='GET' and (current_file_match or current_url_path==self.route_prefix_value+'/model-status'):
   current_content_type='application/json'
   try:
    if current_http_handler.headers.get('Host')!=f'127.0.0.1:{current_http_handler.server.server_port}': raise ValueError('허용하지 않는 Host')
    if current_file_match:
     current_file_path=self.job_storage_root/current_file_match[1]/'attempts'/current_file_match[2]/current_file_match[3]
     if not current_file_path.resolve().is_relative_to(self.job_storage_root.resolve()): raise ValueError('결과 경로 오류')
     current_response_bytes=current_file_path.read_bytes()
     current_content_type={'.mp4':'video/mp4','.zip':'application/zip','.png':'image/png'}[current_file_path.suffix]
    else:
     if self.current_assets_inspector is not None:
      current_response_record=self.current_assets_inspector()
     else:
      self.current_assets_validator()
      current_response_record={'ready':True,'message':'모델 준비 완료'}
     current_response_bytes=json.dumps(current_response_record).encode()
    current_status_code=200
   except (ValueError,OSError) as current_request_error:
    current_status_code=400
    current_response_bytes=json.dumps({'error':str(current_request_error)},ensure_ascii=False).encode()
   current_http_handler.send_response(current_status_code)
   current_http_handler.send_header('Content-Type',current_content_type)
   current_http_handler.send_header('Content-Length',str(len(current_response_bytes)))
   current_http_handler.end_headers()
   current_http_handler.wfile.write(current_response_bytes)
   return True
  return super().handle_image_request(current_http_handler)
