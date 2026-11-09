"""Animate-2를 기존 공용 GPU 대기열과 기록 저장소에 연결한다."""
import base64
import hashlib
from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE, inspect_animate_assets, validate_animate_assets, validate_animate_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class AnimateTwoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-animate2',ANIMATE_JOB_STORAGE,'generators/wan_animate2/worker.py',validate_animate_request,validate_animate_assets,inspect_animate_assets)

    def save_generation_attachments(self,current_job_root,current_request_record):
        current_saved_request=dict(current_request_record)
        current_video_bytes=base64.b64decode(current_saved_request.pop('driving_video'),validate=True)
        (current_job_root/'driving.mp4').write_bytes(current_video_bytes)
        current_saved_request.update(driving_video_file='driving.mp4',driving_video_sha256=hashlib.sha256(current_video_bytes).hexdigest())
        return current_saved_request
