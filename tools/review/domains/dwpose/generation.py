"""단일 이미지 DWPose의 공용 GPU 대기열·이력 연결."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.dwpose.contracts import DWPOSE_JOB_STORAGE, validate_dwpose_request, validate_fun_pose_assets


class DwposeGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/dwpose', DWPOSE_JOB_STORAGE, 'generators/dwpose/worker.py', validate_dwpose_request, validate_fun_pose_assets)
