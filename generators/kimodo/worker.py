"""공용 대기열 진입점. 전용 환경에서 5초 측정과 함께 생성한다."""
import os
import sys
from pathlib import Path
KIMODO_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(KIMODO_WORKSPACE_ROOT))
from generators.kimodo.contracts import KIMODO_JOB_STORAGE,KIMODO_ENVIRONMENT_PYTHON,verify_kimodo_weights

if __name__ == '__main__':
    if Path(sys.prefix) != KIMODO_ENVIRONMENT_PYTHON.parent.parent:
        if not KIMODO_ENVIRONMENT_PYTHON.is_file():
            raise FileNotFoundError(f'전용 실행 환경 누락: {KIMODO_ENVIRONMENT_PYTHON}')
        os.execv(str(KIMODO_ENVIRONMENT_PYTHON),[str(KIMODO_ENVIRONMENT_PYTHON),str(Path(__file__).resolve()),*sys.argv[1:]])
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    from generators.common.reference_video_worker import run_reference_video_worker
    from generators.kimodo.runtime import execute_kimodo_inference
    run_reference_video_worker(KIMODO_JOB_STORAGE,Path(__file__),verify_kimodo_weights,execute_kimodo_inference)
