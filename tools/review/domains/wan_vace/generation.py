"""VACE 생성·대기열·이력은 공용 서비스 계약을 사용한다."""
from generators.wan_vace.contracts import VACE_JOB_STORAGE, inspect_vace_assets, validate_vace_assets, validate_vace_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class VaceVideoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-vace', VACE_JOB_STORAGE, 'generators/wan_vace/worker.py', validate_vace_request, validate_vace_assets, inspect_vace_assets)
