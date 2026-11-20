"""단일 이미지 DWPose의 공용 GPU 대기열·이력 연결."""
from urllib.parse import urlsplit
from tools.review.common.management_transport import send_management_json_response
from tools.review.common.model_prepare_process import inspect_registered_preparation, start_registered_preparation
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_fun.contracts import FUN_PYTHON_EXECUTABLE
from generators.dwpose.contracts import DWPOSE_WORKSPACE_ROOT, DWPOSE_JOB_STORAGE, validate_dwpose_request, validate_fun_pose_assets


def inspect_dwpose_runtime_status():
    current_preparation_status = inspect_registered_preparation(DWPOSE_WORKSPACE_ROOT, 'dwpose-pose')
    if current_preparation_status == 'running':
        return {'ready': False, 'message': 'DWPose 모델 준비 중입니다.', 'preparation_status': current_preparation_status}
    try:
        if not FUN_PYTHON_EXECUTABLE.is_file():
            raise ValueError('ROCm 실행 환경이 없습니다. 모델 관리에서 Wan Fun Control을 준비하세요.')
        validate_fun_pose_assets()
        return {'ready': True, 'message': 'DWPose 모델 검증 완료 · ROCm 환경 실행 파일 확인됨. 의존성과 GPU 실행은 작업 시작 시 검증합니다.', 'preparation_status': current_preparation_status}
    except (OSError, ValueError) as current_status_error:
        return {'ready': False, 'message': f'DWPose 준비 필요: {current_status_error}', 'preparation_status': current_preparation_status}


class DwposeGenerationManager(ReferenceVideoGenerationManager):
    def validate_generation_resume(self, selected_job_directory, recover_interrupted_value=True):
        saved_request_record = super().validate_generation_resume(selected_job_directory, recover_interrupted_value=recover_interrupted_value)
        if len(saved_request_record['references']) != 1:
            raise ValueError('DWPose 재개에는 참조 이미지 1장이 필요합니다.')

    def __init__(self):
        super().__init__('/dwpose', DWPOSE_JOB_STORAGE, 'generators/dwpose/rocm_worker.py', validate_dwpose_request, validate_fun_pose_assets, inspect_dwpose_runtime_status)

    def start_model_preparation(self):
        if not FUN_PYTHON_EXECUTABLE.is_file():
            raise ValueError('DWPose ROCm 환경이 없습니다. workflow.sh setup --scope wan-fun-runtime을 먼저 실행하세요.')
        current_status_record = inspect_dwpose_runtime_status()
        if current_status_record['preparation_status'] == 'running':
            return {'preparation_status': 'running'}
        if current_status_record['ready']:
            return {'preparation_status': 'completed'}
        return start_registered_preparation(DWPOSE_WORKSPACE_ROOT, 'dwpose-pose')

    def handle_image_request(self, current_http_handler):
        current_payload_record = getattr(current_http_handler, 'management_command_payload', None)
        if (current_http_handler.command == 'POST' and urlsplit(current_http_handler.path).path == '/dwpose/jobs'
                and isinstance(current_payload_record, dict) and current_payload_record.get('action') == 'prepare'):
            if current_payload_record != {'action': 'prepare'}:
                raise ValueError('DWPose 모델 준비는 추가 입력을 받지 않습니다.')
            send_management_json_response(current_http_handler, 200, self.start_model_preparation())
            return True
        return super().handle_image_request(current_http_handler)

    def select_generation_python(self, saved_request_record=None):
        return FUN_PYTHON_EXECUTABLE

    def validate_generation_runtime(self, saved_request_record=None):
        if not FUN_PYTHON_EXECUTABLE.is_file():
            raise ValueError('DWPose ROCm 실행 환경이 없습니다. 모델 관리에서 Wan Fun Control을 준비하세요.')
        super().validate_generation_runtime(saved_request_record)
