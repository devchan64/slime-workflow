"""공용 GPU 대기열에서 Fun Control 모델을 준비한다."""
import argparse
import signal
import sys
import traceback
from pathlib import Path

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.wan_fun.contracts import FUN_JOB_STORAGE
from generators.wan_fun.setup_rocm import setup_fun_rocm_environment
from tools.review.common.generation_records import write_record_atomically


def handle_prepare_signal(current_signal_number, current_stack_frame):
    raise InterruptedError(f'준비 작업 종료 신호 {current_signal_number}')


def run_fun_prepare_worker():
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--job-dir', type=Path, required=True)
    current_job_directory = current_argument_parser.parse_args().job_dir.resolve()
    if current_job_directory.parent != FUN_JOB_STORAGE.resolve():
        raise ValueError('작업 경로가 관리 루트 밖입니다.')
    signal.signal(signal.SIGTERM, handle_prepare_signal)
    signal.signal(signal.SIGINT, handle_prepare_signal)
    try:
        setup_fun_rocm_environment()
        write_record_atomically(current_job_directory / 'result.json', {'prepared': True})
        write_record_atomically(current_job_directory / 'status.json', {'status': 'completed', 'message': '모델 준비 완료'})
    except BaseException as current_prepare_error:
        current_status_name = 'cancelled' if isinstance(current_prepare_error, (InterruptedError, KeyboardInterrupt)) else 'failed'
        write_record_atomically(current_job_directory / 'status.json', {'status': current_status_name, 'error': str(current_prepare_error)})
        traceback.print_exc()
        raise


if __name__ == '__main__':
    run_fun_prepare_worker()
