"""고정 Qwen 2512 모델 준비 및 GPU 이미지 생성 작업자."""
from pathlib import Path
from worker_lock import acquire_worker_lock
import argparse
import json
import logging
import threading
import sys
import traceback
from qwen_2512 import *
sys.path.insert(0,str(WORKFLOW_REPOSITORY_ROOT))
from tools.review.domains.tile.tile_results import save_tile_border_result
from tools.review.common.worker_generation_progress import WorkerGenerationProgress


def execute_image_worker():
    argument_parser_value = argparse.ArgumentParser(description=__doc__)
    argument_parser_value.add_argument('--job-dir', type=Path, required=True)
    parsed_argument_values = argument_parser_value.parse_args()
    current_job_root = parsed_argument_values.job_dir.resolve()
    if not current_job_root.is_relative_to(WORKFLOW_REPOSITORY_ROOT / '.tmp/test/qwen-image-2512'):
        raise ValueError('작업 경로 오류')
    current_request_record = json.loads((current_job_root / 'request.json').read_text())
    logging.basicConfig(level=logging.INFO, format='%(asctime)s/qwen-2512/%(message)s', handlers=[logging.FileHandler(current_job_root / 'execution.log'), logging.StreamHandler()])
    if 'floor_separation' in current_request_record:
        from tools.review.domains.tile.floor_pipeline import execute_floor_pipeline
        execute_floor_pipeline(current_job_root,current_request_record)
        return
    current_stop_event = threading.Event()
    current_stage_state = {'stage': 'cuda-check', 'step': 0, 'total': current_request_record.get('steps', FIXED_INFERENCE_STEPS)}
    current_progress_writer = WorkerGenerationProgress(current_job_root)
    def publish_worker_progress(current_progress_record):
        current_stage_state.update(current_progress_record)
        current_progress_writer.record_worker_progress(current_stage_state)
    publish_worker_progress(current_stage_state)
    def emit_worker_heartbeat():
        while not current_stop_event.wait(5):
            current_progress_writer.record_worker_progress(current_stage_state)
            logging.info('heartbeat %s log_bytes=%s', current_stage_state, (current_job_root / 'execution.log').stat().st_size)
    current_heartbeat_thread = None
    current_lock_handle = None
    current_lock_path = WORKFLOW_REPOSITORY_ROOT / ('.local/image-generation-worker.lock' if current_request_record['action']=='prepare' else '.local/image-generation-gpu.lock')
    try:
        current_lock_path.parent.mkdir(parents=True, exist_ok=True)
        current_lock_handle = current_lock_path.open('a')
        current_heartbeat_thread = threading.Thread(target=emit_worker_heartbeat, daemon=True)
        current_heartbeat_thread.start()
        current_stage_state['stage']='waiting-download' if current_request_record['action']=='prepare' else 'waiting-gpu'
        publish_worker_progress(current_stage_state)
        acquire_worker_lock(current_lock_handle,current_stage_state['stage'])
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA 사용 불가: CPU 추론은 지원하지 않습니다.')
        if current_request_record['action'] == 'prepare':
            from huggingface_hub import snapshot_download, hf_hub_download
            publish_worker_progress({'stage':'download-model'})
            snapshot_download(FIXED_MODEL_IDENTIFIER, revision=FIXED_MODEL_REVISION, local_dir=FIXED_MODEL_DIRECTORY)
            publish_worker_progress({'stage':'download-lightning'})
            hf_hub_download(FIXED_LIGHTNING_REPOSITORY, FIXED_LIGHTNING_FILENAME, revision=FIXED_LIGHTNING_REVISION, local_dir=FIXED_LIGHTNING_DIRECTORY)
            validate_qwen_2512_assets()
        else:
            publish_worker_progress({'stage':'generate'})
            generate_qwen_2512_lightning_image(selected_generator_seed=current_request_record.get('seed',251204),output_directory=current_job_root, prompt_text=current_request_record['prompt'], width=current_request_record['width'], height=current_request_record['height'], selected_inference_steps=current_request_record['steps'],worker_progress_callback=publish_worker_progress)
        if current_request_record['action'] != 'prepare':
            publish_worker_progress({'stage':'border-crop'})
            save_tile_border_result(current_job_root,current_request_record)
            if 'floor_rectify' in current_request_record:
                publish_worker_progress({'stage':'floor-rectify'})
                from tools.review.domains.tile.floor_results import save_floor_rectification
                save_floor_rectification(current_job_root,current_request_record)
        (current_job_root / 'status.json').write_text(json.dumps({'status':'completed'}, ensure_ascii=False))
        publish_worker_progress({'stage':'complete'})
        logging.info('complete output=%s', current_job_root)
    except Exception as current_error_value:
        logging.exception('failed model_id=%s model_path=%s', FIXED_MODEL_IDENTIFIER, FIXED_MODEL_DIRECTORY)
        (current_job_root / 'status.json').write_text(json.dumps({'status':'failed','error':str(current_error_value)}, ensure_ascii=False))
        raise
    finally:
        current_stop_event.set()
        if current_heartbeat_thread is not None and current_heartbeat_thread.ident is not None:
            current_heartbeat_thread.join()
        if current_lock_handle is not None:
            current_lock_handle.close()


if __name__ == '__main__':
    execute_image_worker()
