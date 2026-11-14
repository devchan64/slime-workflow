"""VACE 생성·대기열·이력은 공용 서비스 계약을 사용한다."""
from pathlib import Path
from urllib.parse import urlsplit
from generators.wan_vace.contracts import VACE_JOB_STORAGE, inspect_vace_assets, validate_vace_assets, validate_vace_request
from tools.review.common.management_transport import send_management_json_response
from tools.review.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class VaceVideoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-vace', VACE_JOB_STORAGE, 'generators/wan_vace/worker.py', validate_vace_request, validate_vace_assets, self.inspect_model_download)

    def inspect_model_download(self):
        current_root_path = Path(__file__).resolve().parents[4]
        current_preparation_status = inspect_registered_preparation(current_root_path, 'wan-vace')
        if current_preparation_status == 'running':
            return {'ready': False, 'message': 'Wan VACE 모델 다운로드 및 검증 중입니다.', 'preparation_status': current_preparation_status}
        current_asset_status = inspect_vace_assets()
        if current_preparation_status == 'failed' and not current_asset_status['ready']:
            current_asset_status['message'] = '모델 준비 실패. .local/model-preparation/wan-vace/worker.log를 확인하세요. ' + current_asset_status['message']
        return {**current_asset_status, 'preparation_status': current_preparation_status}

    def start_model_download(self):
        with self.current_request_lock:
            current_root_path = Path(__file__).resolve().parents[4]
            if inspect_registered_preparation(current_root_path, 'wan-vace') == 'running':
                return {'preparation_status': 'running'}
            if inspect_vace_assets()['ready']:
                return {'preparation_status': 'completed'}
            return start_registered_preparation(current_root_path, 'wan-vace')

    def handle_image_request(self, current_http_handler):
        current_command_payload = getattr(current_http_handler, 'management_command_payload', None)
        if (current_http_handler.command == 'POST' and urlsplit(current_http_handler.path).path == '/wan22-vace/jobs'
                and isinstance(current_command_payload, dict) and current_command_payload.get('action') == 'prepare'):
            if current_command_payload != {'action': 'prepare'}:
                raise ValueError('Wan VACE 모델 준비는 추가 입력을 받지 않습니다.')
            send_management_json_response(current_http_handler, 200, self.start_model_download())
            return True
        return super().handle_image_request(current_http_handler)

    def save_generation_attachments(self, current_job_root, current_request_record):
        if current_request_record['mode'] == 'video_edit':
            from generators.wan_vace.video_edit import save_edit_inputs
            return save_edit_inputs(current_job_root, current_request_record)
        if current_request_record['mode'] == 'video_condition':
            from generators.wan_vace.video_edit import save_edit_inputs
            return save_edit_inputs(current_job_root, current_request_record, ('edit_video',))
        if current_request_record['mode'] == 'pose':
            from generators.wan_vace.video_edit import save_edit_inputs
            return save_edit_inputs(current_job_root, current_request_record, ('pose_video',))
        return current_request_record
