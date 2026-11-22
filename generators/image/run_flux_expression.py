"""기존 표정 작업 명령을 공용 FLUX 실행기에 연결한다."""
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.image.run_flux_image import execute_flux_image_worker


def execute_flux_expression_worker():
    execute_flux_image_worker(expression_mode=True)


if __name__ == '__main__':
    execute_flux_expression_worker()
