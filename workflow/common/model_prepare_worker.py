"""공용 모델 준비 작업자: 게이트웨이와 별도 프로세스에서 고정된 준비 함수를 실행한다."""
import argparse
import importlib
import os
from pathlib import Path
import traceback

from workflow.common.generation_records import write_record_atomically

MODEL_PREPARATION_PROFILES = {
    'animationgpt': (('workflow.common.animationgpt_model_download', 'prepare_animationgpt_model_files'),
                     ('workflow.common.animationgpt_model_download', 'prepare_author_t5_model_files'),
                     ('workflow.common.animationgpt_model_download', 'prepare_author_weight')),
    'hermes-model': (('workflow.common.hermes_model_download', 'prepare_hermes_model_files'),),
    'flux-image': (('generators.image.flux_model_prepare', 'prepare_flux_model_files'),),
    'expression-lora': (('workflow.domains.image.expression_generation', 'download_expression_adapter'),),
    'qwen-21': (('generators.image.qwen_21_runtime', 'download_qwen_model_assets'),),
    'kimodo': (('generators.kimodo.prepare', 'prepare_kimodo_assets'),),
    'dwpose-pose': (('generators.dwpose.prepare', 'prepare_dwpose_model_files'),),
    'wan-animate2': (('generators.wan_animate2.prepare', 'prepare_animate_models'), ('generators.wan_animate2.contracts', 'validate_animate_assets')),
    'wan22-animate2-lightx2v': (('generators.wan_animate2.lightx2v_assets', 'prepare_lightx2v'),),
    'wan-vace': (('generators.wan_vace.prepare', 'prepare_vace_models'),),
    'wan22-fighting-lora': (('generators.wan_vace.fighting_lora', 'prepare_fighting_lora'),),
    'wan22-vace-q8': (('generators.wan_vace.q8_assets', 'prepare_q8_assets'),),
    'wan22-vace-lightning': (('generators.wan_vace.lightning_lora', 'prepare_lightning_loras'),),
    'wan22-i2v-assets': (('generators.wan_i2v.assets', 'prepare_assets'),),
    'wan21-t2v-assets': (('generators.wan21_t2v.assets', 'prepare_assets'),),
    'wan21-i2v-assets': (('generators.wan21_i2v.assets', 'prepare_assets'),),
    'wan21-i2v-attack-lora': (('generators.wan21_i2v.attack_lora', 'prepare_assets'),),
    'writer-model': (('generators.writer_agent.prepare', 'prepare_writer_model_files'),),
    'heartmula-model': (('workflow.common.audio_model_download', 'download_heartmula_model_files'),),
    'dasheng-model': (('workflow.common.audio_model_download', 'download_dasheng_model_files'),),
    'prompt-translation-model': (('generators.prompt_translation.prepare', 'prepare_translation_model'),),
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
