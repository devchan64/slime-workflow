"""기존 건물 번역 실행 경로를 공용 FLUX 번역 파이프라인에 연결한다."""
import argparse
from pathlib import Path
import sys

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.image.run_flux_translation_pipeline import execute_flux_translation_pipeline

execute_building_pipeline = execute_flux_translation_pipeline

if __name__ == '__main__':
    building_argument_parser = argparse.ArgumentParser()
    building_argument_parser.add_argument('--job-dir', required=True)
    execute_flux_translation_pipeline(building_argument_parser.parse_args().job_dir)
