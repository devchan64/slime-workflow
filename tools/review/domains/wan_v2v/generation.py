"""V2V를 공용 대기열·작업 이력에 연결한다."""
import base64
import hashlib
from generators.wan_v2v.contracts import V2V_JOB_STORAGE, inspect_v2v_assets, validate_v2v_assets, validate_v2v_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class WanVideoEditingManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-v2v',V2V_JOB_STORAGE,'generators/wan_v2v/worker.py',validate_v2v_request,validate_v2v_assets,inspect_v2v_assets)

    def save_generation_attachments(self,current_job_root,current_request_record):
        current_saved_request = dict(current_request_record)
        current_video_bytes = base64.b64decode(current_saved_request.pop('input_video'),validate=True)
        (current_job_root/'input.mp4').write_bytes(current_video_bytes)
        current_saved_request.update(input_video_file='input.mp4',input_video_sha256=hashlib.sha256(current_video_bytes).hexdigest())
        return current_saved_request
