"""공용 대기열에서 실행하는 Qwen Image 2.1 참조 생성 작업자."""
import argparse
import json
import os
from pathlib import Path
import sys
import traceback

WORKFLOW_ROOT_PATH = Path(__file__).resolve().parents[2]
QWEN_ENVIRONMENT_ROOT = WORKFLOW_ROOT_PATH / '.venv-qwen21'


def execute_qwen_reference_worker():
    # 대기열이 Python 심볼릭 링크를 해석해도 분리 환경을 보존한다.
    if Path(sys.prefix) != QWEN_ENVIRONMENT_ROOT:
        environment_python_path = QWEN_ENVIRONMENT_ROOT / 'bin/python'
        os.execv(str(environment_python_path), [str(environment_python_path), str(Path(__file__).resolve()), *sys.argv[1:]])
    sys.path.insert(0, str(WORKFLOW_ROOT_PATH))
    from generators.image.worker_lock import acquire_worker_lock
    from generators.image.qwen_21_runtime import execute_qwen_reference_generation
    from tools.review.domains.image.three_reference_generation import validate_three_reference_job_path, verify_reference_snapshots
    from tools.review.domains.image.seamless_generation import prepare_seamless_reference, finish_seamless_generation

    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--job-dir', type=Path, required=True)
    parsed_argument_values = argument_parser_value.parse_args()
    current_job_root = validate_three_reference_job_path(parsed_argument_values.job_dir)
    try:
        current_request_record = json.loads((current_job_root / 'request.json').read_text())
        verify_reference_snapshots(current_job_root, current_request_record)
        seamless_generation_enabled = 'seamless_tile' in current_request_record
        if seamless_generation_enabled:
            if current_request_record['seamless_tile'].get('schema_version') != 2:
                raise ValueError('Qwen 2.1 심리스 실행 기록 버전 오류')
        else:
            from tools.review.domains.image.qwen_21_generation import verify_qwen_saved_request
            verify_qwen_saved_request(current_job_root, current_request_record)
        current_lock_path = WORKFLOW_ROOT_PATH / '.local/image-generation-gpu.lock'
        current_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with current_lock_path.open('a') as current_lock_handle:
            acquire_worker_lock(current_lock_handle, 'waiting-gpu')
            current_reference_paths = [current_job_root / current_reference_name for current_reference_name in current_request_record['references']]
            if seamless_generation_enabled:
                current_reference_paths = [prepare_seamless_reference(current_job_root, current_request_record)]
            execute_qwen_reference_generation(current_job_root, current_request_record, current_reference_paths)
            if seamless_generation_enabled:
                finish_seamless_generation(current_job_root, current_request_record)
        (current_job_root / 'status.json').write_text('{"status":"completed"}')
    except Exception as current_error_value:
        traceback.print_exc()
        (current_job_root / 'status.json').write_text(json.dumps({'status': 'failed', 'error': str(current_error_value)}, ensure_ascii=False))
        raise


if __name__ == '__main__':
    execute_qwen_reference_worker()
