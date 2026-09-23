"""고정 Qwen 2512 모델 준비 및 GPU 이미지 생성 작업자."""
from pathlib import Path
from worker_lock import acquire_worker_lock
import argparse
import json
import logging
import threading
import traceback
from qwen_2512 import *


def execute_image_worker():
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--job-dir', type=Path, required=True)
    parsed_argument_values = argument_parser_value.parse_args()
    current_job_root = parsed_argument_values.job_dir.resolve()
    if not current_job_root.is_relative_to(WORKFLOW_REPOSITORY_ROOT / '.tmp/test/qwen-image-2512'):
        raise ValueError('작업 경로 오류')
    current_request_record = json.loads((current_job_root / 'request.json').read_text())
    logging.basicConfig(level=logging.INFO, format='%(asctime)s/qwen-2512/%(message)s', handlers=[logging.FileHandler(current_job_root / 'execution.log'), logging.StreamHandler()])
    current_stop_event = threading.Event()
    current_stage_state = {'stage': 'cuda-check'}
    def emit_worker_heartbeat():
        while not current_stop_event.wait(5):
            logging.info('heartbeat %s log_bytes=%s', current_stage_state, (current_job_root / 'execution.log').stat().st_size)
    threading.Thread(target=emit_worker_heartbeat, daemon=True).start()
    current_lock_path = WORKFLOW_REPOSITORY_ROOT / ('.local/image-generation-worker.lock' if current_request_record['action']=='prepare' else '.local/image-generation-gpu.lock')
    current_lock_path.parent.mkdir(parents=True, exist_ok=True)
    current_lock_handle = current_lock_path.open('a')
    try:
        current_stage_state['stage']='waiting-download' if current_request_record['action']=='prepare' else 'waiting-gpu'
        acquire_worker_lock(current_lock_handle,current_stage_state['stage'])
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA 사용 불가: CPU 추론은 지원하지 않습니다.')
        if current_request_record['action'] == 'prepare':
            from huggingface_hub import snapshot_download, hf_hub_download
            current_stage_state['stage'] = 'download-model'
            snapshot_download(FIXED_MODEL_IDENTIFIER, revision=FIXED_MODEL_REVISION, local_dir=FIXED_MODEL_DIRECTORY)
            current_stage_state['stage'] = 'download-lightning'
            hf_hub_download(FIXED_LIGHTNING_REPOSITORY, FIXED_LIGHTNING_FILENAME, revision=FIXED_LIGHTNING_REVISION, local_dir=FIXED_LIGHTNING_DIRECTORY)
            validate_qwen_2512_assets()
        else:
            current_stage_state['stage'] = 'generate'
            generate_qwen_2512_lightning_image(selected_generator_seed=current_request_record.get('seed',251204),output_directory=current_job_root, prompt_text=current_request_record['prompt'], width=current_request_record['width'], height=current_request_record['height'], selected_inference_steps=current_request_record['steps'])
        (current_job_root / 'status.json').write_text(json.dumps({'status':'completed'}, ensure_ascii=False))
        logging.info('complete output=%s', current_job_root)
    except Exception as current_error_value:
        logging.exception('failed model_id=%s model_path=%s', FIXED_MODEL_IDENTIFIER, FIXED_MODEL_DIRECTORY)
        (current_job_root / 'status.json').write_text(json.dumps({'status':'failed','error':str(current_error_value)}, ensure_ascii=False))
        raise
    finally:
        current_stop_event.set()
        current_lock_handle.close()


if __name__ == '__main__':
    execute_image_worker()
