"""MiniMax H3 I2V를 공용 관리 서비스와 GPU 대기열에 연결한다."""
from generators.minimax_h3.contracts import JOB_STORAGE, PYTHON, inspect_runtime, validate_request
from workflow.common.reference_video_generation import ReferenceVideoGenerationManager


def validate_runtime():
    status=inspect_runtime()
    if not status['ready']:
        raise ValueError(status['message'])


class MiniMaxH3GenerationManager(ReferenceVideoGenerationManager):
    def __init__(self):
        super().__init__('/minimax-h3-i2v',JOB_STORAGE,'generators/minimax_h3/worker.py',validate_request,validate_runtime,inspect_runtime)

    def select_generation_python(self,saved_request_record=None):
        return PYTHON

    def select_generation_service(self,saved_request_record=None):
        return 'minimax-h3-i2v'
