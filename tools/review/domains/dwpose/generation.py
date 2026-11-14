"""단일 이미지 DWPose의 공용 GPU 대기열·이력 연결."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_fun.contracts import FUN_PYTHON_EXECUTABLE
from generators.dwpose.contracts import DWPOSE_JOB_STORAGE, validate_dwpose_request, validate_fun_pose_assets


def inspect_dwpose_runtime_status():
    try:
        if not FUN_PYTHON_EXECUTABLE.is_file():
            raise ValueError('ROCm 실행 환경이 없습니다. 모델 관리에서 Wan Fun Control을 준비하세요.')
        validate_fun_pose_assets()
        return {'ready': True, 'message': 'DWPose 모델 검증 완료 · ROCm 환경 실행 파일 확인됨. 의존성과 GPU 실행은 작업 시작 시 검증합니다.'}
    except (OSError, ValueError) as current_status_error:
        return {'ready': False, 'message': f'DWPose 준비 필요: {current_status_error}'}


class DwposeGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/dwpose', DWPOSE_JOB_STORAGE, 'generators/dwpose/rocm_worker.py', validate_dwpose_request, validate_fun_pose_assets, inspect_dwpose_runtime_status)

    def select_generation_python(self, saved_request_record=None):
        return FUN_PYTHON_EXECUTABLE

    def validate_generation_runtime(self, saved_request_record=None):
        if not FUN_PYTHON_EXECUTABLE.is_file():
            raise ValueError('DWPose ROCm 실행 환경이 없습니다. 모델 관리에서 Wan Fun Control을 준비하세요.')
        super().validate_generation_runtime(saved_request_record)
