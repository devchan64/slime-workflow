"""FL2V의 대기 작업·입력·결과·이력을 V2V와 분리한다."""
from tools.review.domains.vace.timeline_generation import VaceTimelineGenerationManager
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT
from generators.vace.first_last import VACE_FIRST_LAST_ROOT, validate_first_last_request, verify_first_last_request


class VaceFirstLastGenerationManager(VaceTimelineGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/wan21-vace-fl2v'
        self.job_storage_root = VACE_FIRST_LAST_ROOT

    def validate_generation_request(self, current_request_record):
        return validate_first_last_request(current_request_record)

    def validate_generation_resume(self, selected_job_directory):
        verify_first_last_request(selected_job_directory)
        super().validate_generation_resume(selected_job_directory)

    def select_generation_runner(self, saved_request_record=None):
        return 'generators/vace/first_last_worker.py'

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'wan21-vace-fl2v'
