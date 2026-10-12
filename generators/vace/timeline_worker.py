"""V2V 작업도 공용 VACE 실행기·ETA·VRAM 기록을 사용한다."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.vace import worker as current_worker_module
from generators.vace.timeline import VACE_TIMELINE_STORAGE_ROOT, verify_timeline_request

if __name__ == '__main__':
    current_worker_module.VACE_JOB_STORAGE_ROOT = VACE_TIMELINE_STORAGE_ROOT
    current_worker_module.verify_vace_request = verify_timeline_request
    current_worker_module.execute_vace_worker()
