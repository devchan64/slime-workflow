"""F2V의 대기 작업·입력·결과·이력을 V2V와 분리한다."""
from tools.review.domains.vace.timeline_generation import VaceTimelineGenerationManager
from tools.review.domains.image.image_generation import MANAGER_HISTORY_ROOT
from generators.vace.first_frame import VACE_FIRST_FRAME_ROOT, validate_first_frame_request, verify_first_frame_request


class VaceFirstFrameGenerationManager(VaceTimelineGenerationManager):
    def __init__(self):
        super().__init__()
        self.route_prefix_value = '/wan21-vace-f2v'
        self.job_storage_root = VACE_FIRST_FRAME_ROOT

    def validate_generation_request(self, current_request_record):
        raise ValueError('F2V 생성기는 폐기되었습니다. FL2V 또는 V2V를 사용하세요.')

    def validate_generation_resume(self, selected_job_directory):
        raise ValueError('F2V 생성기는 폐기되어 재개할 수 없습니다. FL2V 또는 V2V를 사용하세요.')

    def select_generation_runner(self, saved_request_record=None):
        raise ValueError('F2V 실행기는 폐기되었습니다.')

    def history_storage_path(self):
        return MANAGER_HISTORY_ROOT / 'wan21-vace-f2v'
