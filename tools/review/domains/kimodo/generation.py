"""공용 대기열·누적 이력·실제 파일 삭제 계약을 사용하는 Kimodo 서비스."""
from generators.kimodo.contracts import KIMODO_JOB_STORAGE,inspect_kimodo_assets,validate_kimodo_assets,validate_kimodo_request
from tools.review.common.reference_video_generation import ReferenceVideoGenerationManager

class KimodoGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/kimodo',KIMODO_JOB_STORAGE,'generators/kimodo/worker.py',validate_kimodo_request,validate_kimodo_assets,inspect_kimodo_assets)

    def read_generation_status_record(self,current_job_root,fallback_status_record=None,include_log_value=False):
        current_status_record = super().read_generation_status_record(current_job_root,fallback_status_record,include_log_value)
        if current_status_record.get('video'):
            import json
            current_result_record = json.loads((current_job_root/'result.json').read_text())
            current_comparison_path = current_job_root/'attempts'/current_result_record['attempt']/'comparison.mp4'
            if current_comparison_path.is_file() and current_comparison_path.resolve().is_relative_to(current_job_root.resolve()):
                current_status_record['comparison_video'] = current_status_record['video'].removesuffix('preview.mp4')+'comparison.mp4'
        return current_status_record
