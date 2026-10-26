"""공용 대기열 영상 작업자의 기록·종료·출력 저장."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import signal
import traceback
import uuid
import zipfile
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder
from tools.review.domains.image.three_reference_generation import verify_reference_snapshots


def handle_video_signal(current_signal_number, current_stack_frame):
    raise InterruptedError(f'종료 신호 {current_signal_number}')


def save_video_outputs(current_attempt_root, current_frame_arrays, current_frame_rate):
    from PIL import Image
    import imageio.v2 as imageio
    output_frame_hashes = []
    with zipfile.ZipFile(current_attempt_root / 'frames.zip', 'w', compression=zipfile.ZIP_DEFLATED) as current_frame_archive:
        for current_frame_index, current_frame_array in enumerate(current_frame_arrays):
            current_frame_path = current_attempt_root / f'output-{current_frame_index:03d}.png'
            Image.fromarray(current_frame_array).save(current_frame_path)
            output_frame_hashes.append(hashlib.sha256(current_frame_path.read_bytes()).hexdigest())
            current_frame_archive.write(current_frame_path, current_frame_path.name)
    imageio.mimwrite(str(current_attempt_root / 'preview.mp4'), current_frame_arrays, fps=current_frame_rate, codec='libx264', quality=8, macro_block_size=1)
    return output_frame_hashes


def run_reference_video_worker(current_storage_root, current_worker_path, current_assets_validator, current_inference_callback):
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--job-dir', type=Path, required=True)
    current_job_root = current_argument_parser.parse_args().job_dir.resolve()
    if current_job_root.parent != current_storage_root.resolve():
        raise ValueError('작업 경로가 관리 루트 밖입니다.')
    current_request_record = json.loads((current_job_root / 'request.json').read_text())
    verify_reference_snapshots(current_job_root, current_request_record)
    current_attempt_root = current_job_root / 'attempts' / uuid.uuid4().hex
    current_attempt_root.mkdir(parents=True)
    write_record_atomically(current_job_root / 'current-attempt.json', {'id': current_attempt_root.name})
    write_record_atomically(current_attempt_root / 'request.json', current_request_record)
    (current_attempt_root / 'executor-source.py').write_bytes(current_worker_path.read_bytes())
    current_metrics_recorder = GenerationTelemetryRecorder(current_attempt_root, current_request_record['steps'], [])
    current_metrics_recorder.start_generation_telemetry()
    current_final_status = 'failed'
    signal.signal(signal.SIGTERM, handle_video_signal)
    signal.signal(signal.SIGINT, handle_video_signal)
    try:
        current_assets_validator()
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA 사용 불가: CPU 추론으로 대체하지 않습니다.')
        with torch.inference_mode():
            current_result_record = current_inference_callback(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder)
        write_record_atomically(current_attempt_root / 'result.json', current_result_record)
        write_record_atomically(current_job_root / 'result.json', current_result_record)
        current_final_status = 'completed'
    except BaseException as current_execution_error:
        current_final_status = 'cancelled' if isinstance(current_execution_error, (InterruptedError, KeyboardInterrupt)) else 'failed'
        write_record_atomically(current_attempt_root / 'error.json', {'error': str(current_execution_error), 'traceback': traceback.format_exc()})
        traceback.print_exc()
        raise
    finally:
        current_metrics_recorder.finish_generation_telemetry(current_final_status)
        write_record_atomically(current_job_root / 'status.json', {'status': current_final_status, 'attempt': current_attempt_root.name})
