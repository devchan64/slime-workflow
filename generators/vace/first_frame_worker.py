"""F2V 전용 작업 경로를 공용 VACE GPU 실행기에 연결한다."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from generators.vace import worker as current_worker_module
from generators.vace.first_frame import VACE_FIRST_FRAME_ROOT, verify_first_frame_request

if __name__ == '__main__':
    current_worker_module.VACE_JOB_STORAGE_ROOT = VACE_FIRST_FRAME_ROOT
    current_worker_module.verify_vace_request = verify_first_frame_request
    current_worker_module.execute_vace_worker()
