"""MiniMax H3 영상 편집을 공용 관리·GPU 대기열 계약에 연결한다."""
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager
from workflow.common.video_attachment_verification import verify_saved_video_attachments
from workflow.generators.minimax_h3_ref2va.assets import inspect_runtime
from workflow.generators.minimax_h3_ref2va.contracts import JOB_STORAGE, PYTHON, save_video_input, validate_request


def validate_runtime():
    status = inspect_runtime()
    if not status['ready']:
        raise ValueError(status['message'])


class MiniMaxH3Ref2VAManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/minimax-h3-ref2va', JOB_STORAGE,
                         'workflow/generators/minimax_h3_ref2va/worker.py',
                         validate_request, validate_runtime, inspect_runtime)

    def select_generation_python(self, saved_request_record=None):
        return PYTHON

    def select_generation_service(self, saved_request_record=None):
        return 'minimax-h3-ref2va'

    def save_generation_attachments(self, current_job_root, current_request_record):
        return save_video_input(current_job_root, current_request_record)

    def validate_generation_resume(self, selected_job_directory, recover_interrupted_value=True):
        saved = super().validate_generation_resume(selected_job_directory, recover_interrupted_value)
        verify_saved_video_attachments(selected_job_directory, saved, ('edit_video',))
        return saved
