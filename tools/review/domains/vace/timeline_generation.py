"""VACE V2V 전용 서비스. 기존 R2V 중지 상태는 유지한다."""
from tools.review.domains.vace.generation import VaceGenerationManager
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT
from generators.vace.timeline import VACE_TIMELINE_STORAGE_ROOT, validate_timeline_request, verify_timeline_request


class VaceTimelineGenerationManager(VaceGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value='/wan21-vace-v2v'
        self.job_storage_root=VACE_TIMELINE_STORAGE_ROOT
        self.reference_request_limit=32_100_000

    def validate_generation_request(self,current_request_record):
        return validate_timeline_request(current_request_record)

    def validate_generation_resume(self,selected_job_directory):
        current_saved_record=verify_timeline_request(selected_job_directory)
        if (current_saved_record['width'],current_saved_record['height']) != (832,480):
            raise ValueError('이전 해상도 작업은 재개할 수 없습니다. 입력값을 불러와 832×480으로 새로 생성하세요.')

    def select_generation_runner(self,saved_request_record=None):
        return 'generators/vace/timeline_worker.py'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT/'wan21-vace-v2v'
