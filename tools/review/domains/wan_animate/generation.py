"""Animate 공용 영상 작업 서비스 연결."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_animate.contracts import ANIMATE_JOB_STORAGE, validate_animate_request, validate_animate_assets

class AnimateGenerationManager(ReferenceVideoGenerationManager):
 def __init__(self):
  super().__init__('/wan22-animate',ANIMATE_JOB_STORAGE,'generators/wan_animate/worker.py',validate_animate_request,validate_animate_assets)

 def save_generation_attachments(self,current_job_root,current_request_record):
  if 'driving_video' not in current_request_record:
   return current_request_record
  import base64,hashlib
  current_video_bytes=base64.b64decode(current_request_record['driving_video'],validate=True)
  (current_job_root/'driving.mp4').write_bytes(current_video_bytes)
  return {**{current_field_name:current_field_value for current_field_name,current_field_value in current_request_record.items() if current_field_name!='driving_video'},'driving_video_file':'driving.mp4','driving_video_sha256':hashlib.sha256(current_video_bytes).hexdigest()}

 def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
  current_status_record=super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
  if current_status_record.get('video'):
   current_video_prefix=current_status_record['video'].rsplit('/',1)[0]
   import json
   current_result_record=json.loads((current_job_root/'result.json').read_text())
   current_attempt_root=current_job_root/'attempts'/current_result_record['attempt']
   if all((current_attempt_root/current_file_name).is_file() for current_file_name in ('pose.mp4','face.mp4')):
    current_status_record['preprocess_videos']={'몸 포즈':current_video_prefix+'/pose.mp4','얼굴 크롭':current_video_prefix+'/face.mp4'}
  return current_status_record
