"""Animate-2를 기존 공용 GPU 대기열과 기록 저장소에 연결한다."""
import base64
import hashlib
from pathlib import Path
from tools.review.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
from urllib.parse import urlsplit
from generators.wan_animate2.contracts import ANIMATE_JOB_STORAGE, inspect_animate_assets, validate_animate_assets, validate_animate_request
from tools.review.common.management_transport import send_management_json_response
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class AnimateTwoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-animate2',ANIMATE_JOB_STORAGE,'generators/wan_animate2/worker.py',validate_animate_request,validate_animate_assets,self.inspect_model_download)

    def inspect_model_download(self):
        with self.current_request_lock:
            current_download_status = inspect_registered_preparation(Path(__file__).resolve().parents[4], 'wan-animate2')
            if current_download_status == 'running':
                return {'ready': False, 'message': '모델 다운로드 및 파일 해시 기록 중입니다.', 'preparation_status': current_download_status}
            current_asset_status = inspect_animate_assets()
            if current_download_status == 'failed' and not current_asset_status['ready']:
                current_asset_status['message'] = '모델 다운로드 실패. .local/model-preparation/wan-animate2/worker.log에서 디스크 공간, 모델 접근 권한, Diffusers 리비전을 확인하세요.'
            return {**current_asset_status, 'preparation_status': current_download_status}

    def start_model_download(self):
        with self.current_request_lock:
            current_workflow_root = Path(__file__).resolve().parents[4]
            if inspect_registered_preparation(current_workflow_root, 'wan-animate2') == 'running':
                return {'preparation_status': 'running'}
            if inspect_animate_assets()['ready']:
                return {'preparation_status': 'completed'}
            try:
                return start_registered_preparation(current_workflow_root, 'wan-animate2')
            except OSError as current_start_error:
                raise ValueError('모델 다운로드를 시작할 수 없습니다.') from current_start_error

    def handle_image_request(self, current_http_handler):
        current_command_payload = getattr(current_http_handler, 'management_command_payload', None)
        if (current_http_handler.command == 'POST'
                and urlsplit(current_http_handler.path).path == '/wan22-animate2/jobs'
                and isinstance(current_command_payload, dict)
                and current_command_payload.get('action') == 'prepare'):
            if set(current_command_payload) != {'action'}:
                raise ValueError('Animate-2 모델 준비는 추가 입력을 받지 않습니다.')
            send_management_json_response(current_http_handler, 200, self.start_model_download())
            return True
        return super().handle_image_request(current_http_handler)

    def save_generation_attachments(self,current_job_root,current_request_record):
        current_saved_request=dict(current_request_record)
        current_video_bytes=base64.b64decode(current_saved_request.pop('driving_video'),validate=True)
        (current_job_root/'driving.mp4').write_bytes(current_video_bytes)
        current_saved_request.update(driving_video_file='driving.mp4',driving_video_sha256=hashlib.sha256(current_video_bytes).hexdigest())
        return current_saved_request
