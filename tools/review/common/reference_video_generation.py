"""참조 이미지 기반 영상 생성기의 공용 작업·이력·결과 파일 계약."""
import json
from tools.review.domains.image.image_generation import ImageGenerationManager, MANAGER_HISTORY_ROOT
from tools.review.domains.image.three_reference_generation import verify_reference_snapshots
from tools.review.common.video_result_files import enrich_video_result_status
from tools.review.common.queue_generation_telemetry import merge_generation_worker_metrics
from tools.review.common.video_job_recovery import normalize_recovered_video_metrics, recover_interrupted_video_job
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
 def validate_generation_resume(self,selected_job_directory,recover_interrupted_value=True):
  if recover_interrupted_value:
   recover_interrupted_video_job(selected_job_directory)
  current_request_path=selected_job_directory/'request.json'
  if current_request_path.is_symlink() or not current_request_path.is_file():
   raise ValueError('재개할 요청 기록의 일반 파일을 확인할 수 없습니다.')
  try:
   saved_request_record=json.loads(current_request_path.read_text())
   verify_reference_snapshots(selected_job_directory,saved_request_record)
  except (KeyError,TypeError,IndexError) as current_record_error:
   raise ValueError('재개할 참조 사본 기록이 올바르지 않습니다.') from current_record_error
  self.current_assets_validator()
  return saved_request_record
 def fingerprint_generation_resume_inputs(self,selected_job_directory):
  from tools.review.common.video_resume_fingerprint import fingerprint_video_resume_inputs
  return fingerprint_video_resume_inputs(selected_job_directory,self.route_prefix_value.lstrip('/'))
 def inspect_video_resume_availability(self):
  from tools.review.common.model_prepare_process import inspect_registered_preparation_strict
  from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH
  current_preparation_profiles={'/dwpose':'dwpose-pose','/wan22-animate2':'wan-animate2','/wan22-vace':'wan-vace'}
  if self.route_prefix_value not in current_preparation_profiles:return 'unknown'
  try:
   current_preparation_state=inspect_registered_preparation_strict(WORKFLOW_ROOT_PATH,current_preparation_profiles[self.route_prefix_value])
  except (OSError,ValueError,TypeError):return 'unknown'
  if current_preparation_state=='running':return 'download_running'
  return 'available' if current_preparation_state in ('idle','completed','failed') else 'unknown'
 def preview_generation_resume(self,selected_job_directory):
  """공용 잠금 아래 영상 요청과 모든 입력을 검사하고 지문을 반환한다."""
  import fcntl
  import os
  import re
  import stat
  from pathlib import Path
  from tools.review.common.gpu_job_queue import open_gpu_resume_lock
  selected_job_directory=Path(selected_job_directory)
  if self.route_prefix_value not in ('/dwpose','/wan22-animate2','/wan22-vace'):
   raise ValueError('이 영상 서비스는 재개 검토를 지원하지 않습니다.')
  if (not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',selected_job_directory.name)
      or selected_job_directory.is_symlink() or not selected_job_directory.is_dir()
      or selected_job_directory.parent.resolve()!=Path(self.job_storage_root).resolve()):
   raise ValueError('영상 재개 작업 경로 오류')
  recover_interrupted_video_job(selected_job_directory)
  with open_gpu_resume_lock(selected_job_directory) as current_resume_handle:
   fcntl.flock(current_resume_handle,fcntl.LOCK_EX)
   try:
    current_lock_descriptor=os.open(selected_job_directory/'execution.lock',os.O_WRONLY|os.O_CREAT|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
    with os.fdopen(current_lock_descriptor,'a') as current_execution_handle:
     if not stat.S_ISREG(os.fstat(current_execution_handle.fileno()).st_mode):
      raise ValueError('영상 실행 잠금은 일반 파일이어야 합니다.')
     try:
      fcntl.flock(current_execution_handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
     except BlockingIOError as current_lock_error:
      raise ValueError('이전 영상 실행이 종료되지 않았습니다.') from current_lock_error
     initial_fingerprint_value=self.fingerprint_generation_resume_inputs(selected_job_directory)
     saved_request_record=json.loads((selected_job_directory/'request.json').read_text())
     from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH
     current_command_path=selected_job_directory/'gpu-command.json'
     try:
      current_command_descriptor=os.open(current_command_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
     except FileNotFoundError:
      current_command_descriptor=None
     if current_command_descriptor is not None:
      with os.fdopen(current_command_descriptor,'rb') as current_command_stream:
       current_command_stat=os.fstat(current_command_stream.fileno())
       if not stat.S_ISREG(current_command_stat.st_mode) or current_command_stat.st_size>1048576:
        raise ValueError('영상 재개 실행 명령 기록 오류')
       current_command_record=json.loads(current_command_stream.read(1048577))
      current_expected_command=[str(self.select_generation_python(saved_request_record)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(saved_request_record)),'--job-dir',str(selected_job_directory)]
      if current_command_record!={'command':current_expected_command,'service':self.select_generation_service(saved_request_record)}:
       raise ValueError('영상 재개 실행 명령이 원 서비스와 일치하지 않습니다.')
     self.validate_generation_runtime(saved_request_record)
     self.validate_generation_resume(selected_job_directory,recover_interrupted_value=False)
     final_fingerprint_value=self.fingerprint_generation_resume_inputs(selected_job_directory)
     if initial_fingerprint_value!=final_fingerprint_value:
      raise ValueError('영상 재개 검토 중 입력이 변경됐습니다.')
     return {'service':self.route_prefix_value.lstrip('/'),'id':selected_job_directory.name,'status':final_fingerprint_value['status'],'expected_resume_fingerprint':final_fingerprint_value['fingerprint'],'resume_availability':self.inspect_video_resume_availability(),'note':'저장 입력을 검토한 시점의 결과이며 GPU 가용성과 접수는 별도입니다.'}
   except OSError as current_lock_error:
    raise ValueError('영상 실행 잠금을 확인할 수 없습니다.') from current_lock_error
 def resume_reviewed_generation_job(self,selected_job_directory,expected_fingerprint_value):
  """검토 입력을 공용 재개 잠금 안에서 재검증하고 기존 GPU 대기열로 접수한다."""
  import re
  from pathlib import Path
  from tools.review.domains.image.image_generation import WORKFLOW_ROOT_PATH
  from tools.review.common.gpu_job_queue import resume_gpu_generation
  from tools.review.common.model_prepare_process import hold_registered_preparation_guard
  selected_job_directory=Path(selected_job_directory)
  current_preparation_profiles={'/dwpose':'dwpose-pose','/wan22-animate2':'wan-animate2','/wan22-vace':'wan-vace'}
  if (self.route_prefix_value not in current_preparation_profiles
      or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8}',selected_job_directory.name)
      or selected_job_directory.is_symlink() or not selected_job_directory.is_dir()
      or selected_job_directory.parent.resolve()!=Path(self.job_storage_root).resolve()):
   raise ValueError('영상 재개 작업 경로 오류')
  if not isinstance(expected_fingerprint_value,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_fingerprint_value):
   raise ValueError('영상 재개 확인값 오류')
  if self.inspect_video_resume_availability()!='available':
   raise ValueError('영상 모델 준비가 진행 중이거나 준비 상태를 확인할 수 없습니다.')
  if self.fingerprint_generation_resume_inputs(selected_job_directory)['fingerprint']!=expected_fingerprint_value:
   raise ValueError('검토한 영상 재개 입력이 변경됐습니다.')
  saved_request_record=json.loads((selected_job_directory/'request.json').read_text())
  expected_command_values=[str(self.select_generation_python(saved_request_record)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(saved_request_record)),'--job-dir',str(selected_job_directory)]
  expected_service_value=self.select_generation_service(saved_request_record)
  def validate_locked_video_resume(current_locked_directory):
   if self.fingerprint_generation_resume_inputs(current_locked_directory)['fingerprint']!=expected_fingerprint_value:
    raise ValueError('검토한 영상 재개 입력이 변경됐습니다.')
   current_request_record=json.loads((current_locked_directory/'request.json').read_text())
   current_command_values=[str(self.select_generation_python(current_request_record)),str(WORKFLOW_ROOT_PATH/self.select_generation_runner(current_request_record)),'--job-dir',str(current_locked_directory)]
   if current_command_values!=expected_command_values or self.select_generation_service(current_request_record)!=expected_service_value:
    raise ValueError('검토한 영상 실행 명령이 변경됐습니다.')
   self.validate_generation_runtime(current_request_record)
   self.validate_generation_resume(current_locked_directory,recover_interrupted_value=False)
   if self.fingerprint_generation_resume_inputs(current_locked_directory)['fingerprint']!=expected_fingerprint_value:
    raise ValueError('영상 재개 검증 중 입력이 변경됐습니다.')
  current_legacy_record={'command':expected_command_values,'service':expected_service_value}
  with hold_registered_preparation_guard(WORKFLOW_ROOT_PATH,current_preparation_profiles[self.route_prefix_value]):
   return resume_gpu_generation(selected_job_directory,legacy_command_record=current_legacy_record,expected_resume_service=expected_service_value,expected_resume_command=expected_command_values,resume_locked_preflight_callback=validate_locked_video_resume)
 def select_generation_runner(self,saved_request_record=None):
  return self.current_runner_path
 def history_storage_path(self):
  return MANAGER_HISTORY_ROOT/self.route_prefix_value.lstrip('/')
 def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
  recover_interrupted_video_job(current_job_root)
  current_status_record=super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
  current_attempt_path=current_job_root/'current-attempt.json'
  if current_attempt_path.exists():
   current_metrics_path=current_job_root/'attempts'/json.loads(current_attempt_path.read_text())['id']/'metrics.json'
   if current_metrics_path.exists():
    merge_generation_worker_metrics(current_status_record,json.loads(current_metrics_path.read_text()))
  normalize_recovered_video_metrics(current_status_record)
  return enrich_video_result_status(current_job_root,current_status_record,self.route_prefix_value)
 def handle_image_request(self,current_http_handler):
  import re
  from urllib.parse import urlsplit
  current_url_path=urlsplit(current_http_handler.path).path
  current_file_match=re.fullmatch(re.escape(self.route_prefix_value)+r'/jobs/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-[a-f0-9]{8})/attempts/([a-f0-9]{32})/((?:soma-render|soma-direct|dwpose)-(?:front|front_left|front_left_30|left|back_left|back|back_right|right|front_right|front_right_75|front_right_60|front_right_30|front_right_15)\.mp4|preview\.mp4|comparison\.mp4|pose\.mp4|face\.mp4|frames\.zip|output-\d{3}\.png)',current_url_path)
  if current_http_handler.command=='GET' and (current_file_match or current_url_path==self.route_prefix_value+'/model-status'):
   current_content_type='application/json'
   try:
    from tools.review.common.management_environment import validate_loopback_request_host
    validate_loopback_request_host(current_http_handler)
    if current_file_match:
     current_file_path=self.job_storage_root/current_file_match[1]/'attempts'/current_file_match[2]/current_file_match[3]
     if not current_file_path.resolve().is_relative_to(self.job_storage_root.resolve()): raise ValueError('결과 경로 오류')
     if current_file_path.suffix == '.mp4':
      from tools.review.common.audio_file_response import send_media_file_response
      send_media_file_response(current_http_handler,current_file_path,'video/mp4')
      return True
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
