"""Wan I2V 작업을 공용 관리 서비스와 GPU 대기열에 연결한다."""
from generators.wan_i2v.contracts import JOB_STORAGE, PYTHON, ROOT, inspect_runtime, validate_request
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager


def validate_runtime():
    status = inspect_runtime()
    if not status['ready']:
        raise ValueError(status['message'])


class I2VGenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/wan22-i2v', JOB_STORAGE, 'generators/wan_i2v/worker.py', validate_request, validate_runtime, inspect_runtime)

    def select_generation_python(self, saved_request_record=None):
        return PYTHON

    def select_generation_service(self, saved_request_record=None):
        return 'wan22-i2v'

    def hold_generation_submission_guard(self):
        from workflow.common.model_prepare_process import hold_registered_preparation_guard
        return hold_registered_preparation_guard(ROOT, 'wan22-i2v-assets')
