"""Fun Control을 공용 대기열·이력에 연결한다."""
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager
from generators.wan_fun.contracts import FUN_JOB_STORAGE, validate_fun_request, validate_fun_assets, inspect_fun_assets

class FunControlGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-fun-control', FUN_JOB_STORAGE, 'generators/wan_fun/worker.py', validate_fun_request, validate_fun_assets, inspect_fun_assets)
