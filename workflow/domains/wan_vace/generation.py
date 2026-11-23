"""VACE 생성·대기열·이력은 공용 서비스 계약을 사용한다."""
from pathlib import Path
from urllib.parse import urlsplit
from generators.wan_vace.contracts import VACE_JOB_STORAGE, inspect_vace_assets, validate_vace_assets, validate_vace_request
from workflow.common.management_transport import send_management_json_response
from workflow.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager
from workflow.common.video_attachment_verification import verify_saved_video_attachments


class VaceVideoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-vace', VACE_JOB_STORAGE, 'generators/wan_vace/worker.py', validate_vace_request, validate_vace_assets, self.inspect_model_download)

    def validate_generation_resume(self, selected_job_directory, recover_interrupted_value=True):
        saved_request_record = super().validate_generation_resume(selected_job_directory, recover_interrupted_value=recover_interrupted_value)
        selected_input_fields = {'video_edit': ('edit_video', 'edit_mask'), 'video_condition': ('edit_video',), 'pose': ('pose_video',), 'text': (), 'reference': (), 'first_frame': ()}
        current_mode_value = saved_request_record.get('mode')
        if not isinstance(current_mode_value, str) or current_mode_value not in selected_input_fields:
            raise ValueError('재개할 영상 모드가 올바르지 않습니다.')
        expected_image_count = 0 if current_mode_value == 'text' else 1
        if len(saved_request_record['references']) != expected_image_count:
            raise ValueError('VACE 재개 참조 이미지 수가 입력 모드와 일치하지 않습니다.')
        verify_saved_video_attachments(selected_job_directory, saved_request_record, selected_input_fields[current_mode_value])

    def validate_generation_runtime(self, saved_request_record=None):
        if saved_request_record is not None and saved_request_record.get('model_profile') != 'official-bf16-resident-v1':
            raise ValueError('폐기된 Q4 작업은 재개할 수 없습니다. 입력을 불러와 새 작업을 생성하세요.')
        validate_vace_assets()
        if saved_request_record and saved_request_record.get('lora_mode', 'none') in ('lightning', 'fighting_lightning'):
            from generators.wan_vace.lightning_lora import inspect_lightning_loras
            if not inspect_lightning_loras():
                raise ValueError('Lightning LoRA를 모델 관리에서 준비하세요.')
        if saved_request_record and saved_request_record.get('lora_mode') in ('fighting', 'fighting_lightning'):
            from generators.wan_vace.fighting_lora import inspect_fighting_lora
            if not inspect_fighting_lora():
                raise ValueError('격투 LoRA를 모델 관리에서 준비하세요.')

    def inspect_model_download(self):
        current_root_path = Path(__file__).resolve().parents[3]
        current_preparation_status = inspect_registered_preparation(current_root_path, 'wan-vace')
        if current_preparation_status == 'running':
            return {'ready': False, 'message': 'Wan VACE 모델 다운로드 및 검증 중입니다.', 'preparation_status': current_preparation_status}
        current_asset_status = inspect_vace_assets()
        if current_preparation_status == 'failed' and not current_asset_status['ready']:
            current_asset_status['message'] = '모델 준비 실패. .local/model-preparation/wan-vace/worker.log를 확인하세요. ' + current_asset_status['message']
        return {**current_asset_status, 'preparation_status': current_preparation_status}

    def start_model_download(self):
        with self.current_request_lock:
            current_root_path = Path(__file__).resolve().parents[3]
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
