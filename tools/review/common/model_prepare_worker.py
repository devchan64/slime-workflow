"""공용 모델 준비 작업자: 게이트웨이와 별도 프로세스에서 고정된 준비 함수를 실행한다."""
import argparse
import importlib
import os
from pathlib import Path
import traceback

from tools.review.common.generation_records import write_record_atomically

MODEL_PREPARATION_PROFILES = {
    'qwen-21': (('generators.image.qwen_21_runtime', 'download_qwen_model_assets'),),
    'kimodo': (('generators.kimodo.prepare', 'prepare_kimodo_assets'),),
    'wan-animate2': (('generators.wan_animate2.prepare', 'prepare_animate_models'), ('generators.wan_animate2.contracts', 'validate_animate_assets')),
}


def run_registered_model_preparation():
    current_parser_value = argparse.ArgumentParser()
    current_parser_value.add_argument('--profile', required=True, choices=tuple(MODEL_PREPARATION_PROFILES))
    current_parser_value.add_argument('--status-path', type=Path, required=True)
    current_parser_value.add_argument('--lock-fd', type=int, required=True)
    current_argument_values = current_parser_value.parse_args()
    with os.fdopen(current_argument_values.lock_fd, 'a'):
        write_record_atomically(current_argument_values.status_path, {'status': 'running'})
        try:
            for current_module_name, current_function_name in MODEL_PREPARATION_PROFILES[current_argument_values.profile]:
                getattr(importlib.import_module(current_module_name), current_function_name)()
        except BaseException:
            traceback.print_exc()
            write_record_atomically(current_argument_values.status_path, {'status': 'failed'})
            raise
        else:
            write_record_atomically(current_argument_values.status_path, {'status': 'completed'})


if __name__ == '__main__':
    run_registered_model_preparation()
