"""공용 대기열·누적 이력·실제 파일 삭제 계약을 사용하는 Kimodo 서비스."""
from generators.kimodo.contracts import KIMODO_JOB_STORAGE,inspect_kimodo_assets,validate_kimodo_assets,validate_kimodo_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager

class KimodoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/kimodo',KIMODO_JOB_STORAGE,'generators/kimodo/worker.py',validate_kimodo_request,validate_kimodo_assets,inspect_kimodo_assets)
