"""Wan2.2 TI2V 관리 서비스."""
from generators.wan_ti2v.contracts import TI2V_JOB_STORAGE, inspect_ti2v_assets, validate_ti2v_assets, validate_ti2v_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager


class Ti2vGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-ti2v', TI2V_JOB_STORAGE, 'generators/wan_ti2v/worker.py', validate_ti2v_request, validate_ti2v_assets, inspect_ti2v_assets)
