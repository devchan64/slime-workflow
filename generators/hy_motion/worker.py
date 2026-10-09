"""공용 GPU 대기열에서 실행하는 HY-Motion 작업자."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import uuid
from zoneinfo import ZoneInfo

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW_ROOT_DIRECTORY))
from generators.hy_motion.contracts import MODEL_CACHE_DIRECTORY, validate_generation_request
from tools.review.common.generation_records import write_record_atomically


def execute_generation_worker(generation_job_path):
    from generators.hy_motion.runtime import prepare_model_bundle, run_motion_inference
    generation_job_path = generation_job_path.resolve()
    current_request_record = json.loads((generation_job_path / 'request.json').read_text())
    current_config_record = json.loads((generation_job_path / 'config.json').read_text())
    current_started_time = time.monotonic()
    current_started_timestamp = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
    current_progress_state = {'stage': 'starting', 'message': '작업 준비'}
    current_shutdown_event = threading.Event()
    current_attempt_path = generation_job_path / 'attempts' / (datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d_%H-%M-%S') + '-' + uuid.uuid4().hex[:8])
    current_attempt_path.mkdir(parents=True)

    def record_worker_progress(current_stage_name, current_message_text):
        current_progress_state.update(stage=current_stage_name, message=current_message_text)
        current_timestamp_text = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
        print(f'{current_timestamp_text}/hy-motion/{current_stage_name} {current_message_text}', flush=True)
        write_record_atomically(generation_job_path / 'status.json', {'status': 'running', 'message': current_message_text, 'started_at': current_started_timestamp, 'attempt_path': current_attempt_path.relative_to(generation_job_path).as_posix(), 'progress': {'stage': current_stage_name}})

    def emit_worker_heartbeat():
        while not current_shutdown_event.wait(5):
            from tools.review.domains.hy_motion.jobs import estimate_generation_completion
            current_live_status = json.loads((generation_job_path / 'status.json').read_text())
            if current_live_status['status'] == 'running':
                write_record_atomically(generation_job_path / 'eta.json', estimate_generation_completion(generation_job_path, current_request_record, current_live_status))
            current_output_count = sum(1 for current_artifact_path in current_attempt_path.rglob('*') if current_artifact_path.is_file())
            print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/hy-motion/heartbeat stage={current_progress_state["stage"]} elapsed={time.monotonic()-current_started_time:.1f}s artifacts={current_output_count} recent={current_progress_state["message"]}', flush=True)

    current_heartbeat_thread = threading.Thread(target=emit_worker_heartbeat, daemon=True)
    current_heartbeat_thread.start()
    try:
        record_worker_progress('starting', f'실행기=HY-Motion 출력={current_attempt_path} 입력={json.dumps(current_request_record, ensure_ascii=False)}')
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA GPU를 사용할 수 없습니다. 샌드박스 밖 GPU 환경에서 게이트웨이를 실행하세요.')
        MODEL_CACHE_DIRECTORY.mkdir(parents=True, exist_ok=True)
        with (MODEL_CACHE_DIRECTORY / 'bundle.lock').open('a') as current_bundle_lock:
            fcntl.flock(current_bundle_lock, fcntl.LOCK_EX if current_request_record.get('action') == 'prepare' else fcntl.LOCK_SH)
            if current_request_record.get('action') == 'prepare':
                prepare_model_bundle(record_worker_progress)
                current_result_record = {'kind': 'prepared', 'model_root': str(MODEL_CACHE_DIRECTORY)}
            elif current_request_record.get('action') == 'export-vnccs':
                from generators.hy_motion.vnccs_export import export_vnccs_package
                current_result_record = export_vnccs_package(generation_job_path, current_attempt_path, current_request_record, current_config_record, record_worker_progress)
                current_result_record['relative_path'] = current_attempt_path.relative_to(generation_job_path).as_posix()
            else:
                import numpy as np
                from generators.hy_motion.preview import validate_motion_output, render_motion_previews
                from generators.hy_motion.gif_export import export_motion_gifs
                validate_generation_request(current_request_record)
                current_output_arrays, current_provenance_record = run_motion_inference(current_request_record, current_config_record, current_attempt_path, record_worker_progress)
                import gc
                gc.collect()
                torch.cuda.empty_cache()
                validate_motion_output(current_output_arrays, round(current_request_record['duration_seconds'] * 30))
                current_provenance_record.update(request=current_request_record, config=current_config_record, encoder_prompt=json.loads((current_attempt_path / 'encoder-prompt.json').read_text()))
                np.savez_compressed(current_attempt_path / 'motion.npz', **current_output_arrays, fps=np.array(30))
                write_record_atomically(current_attempt_path / 'provenance.json', current_provenance_record)
                from generators.hy_motion.head_rotation_transfer import load_head_motion_rotations
                current_head_rotations, current_head_source = load_head_motion_rotations(current_attempt_path / 'motion.npz', len(current_output_arrays['world_joints']))
                current_coordinate_basis = np.asarray(current_head_source['source_to_target_basis'])
                current_source_rotations = current_coordinate_basis.T @ current_head_rotations @ current_coordinate_basis
                from generators.hy_motion.head_rotation_transfer import HEAD_SOURCE_DIRECTORY
                from generators.hy_motion.rotation_channels import reconstruct_rotation_channels
                current_rest_points = np.fromfile(HEAD_SOURCE_DIRECTORY / 'j_template.bin', dtype='<f4').reshape(52, 3)
                current_parent_indices = np.fromfile(HEAD_SOURCE_DIRECTORY / 'kintree.bin', dtype='<i4')[:22]
                _, current_global_rotations, _ = reconstruct_rotation_channels(current_output_arrays['rot6d'], current_rest_points[:22], current_parent_indices, current_output_arrays['transl'], current_output_arrays['world_joints'][:, :22])
                current_result_record = render_motion_previews(current_output_arrays['world_joints'][:, :22], current_request_record, current_config_record, current_attempt_path, record_worker_progress, current_source_rotations, current_global_rotations[:, 20:22])
                current_result_record['head_rotation_guide'] = True
                current_result_record['gifs'] = export_motion_gifs(current_result_record, current_attempt_path, record_worker_progress)
                current_result_record.update(kind='motion', relative_path=current_attempt_path.relative_to(generation_job_path).as_posix(), provenance=current_provenance_record)
                from generators.hy_motion.automatic_render import generate_automatic_renders
                from generators.hy_motion.vnccs_contract import load_vnccs_config
                current_render_config_path = generation_job_path / 'render-config.json'
                # 과거 모션 작업의 재개도 새 기본 출력을 적용하고 해당 시도에 설정을 보존한다.
                current_render_config = json.loads(current_render_config_path.read_text()) if current_render_config_path.exists() else load_vnccs_config()
                write_record_atomically(current_attempt_path / 'render-config.json', current_render_config)
                current_result_record['rendering'] = generate_automatic_renders(generation_job_path, current_attempt_path, current_request_record, current_render_config, record_worker_progress)
                current_result_record['quality_warnings'] = current_result_record['rendering']['quality_warnings']
        current_result_record['elapsed_seconds'] = round(time.monotonic() - current_started_time, 2)
        write_record_atomically(generation_job_path / 'result.json', current_result_record)
        write_record_atomically(current_attempt_path / 'outcome.json', {'status': 'completed', 'result': current_result_record})
        write_record_atomically(generation_job_path / 'status.json', {'status': 'completed', 'message': '모델 준비 완료' if current_result_record['kind'] == 'prepared' else 'VNCCS용 포즈 PNG·출처 패키지 완료 · 품질 경고 확인 필요' if current_result_record['kind'] == 'vnccs' else '원본 모션·ANNY 리그·정사영·원근투영·OpenPose 저장 완료'})
        print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/hy-motion/completed 출력={current_attempt_path}', flush=True)
        return 0
    except Exception as current_execution_error:
        traceback.print_exc()
        current_failure_record = {'status': 'failed', 'error': str(current_execution_error), 'model_id': 'tencent/HY-Motion-1.0', 'model_root': str(MODEL_CACHE_DIRECTORY), 'binary_path': sys.executable}
        write_record_atomically(current_attempt_path / 'outcome.json', current_failure_record)
        write_record_atomically(generation_job_path / 'status.json', current_failure_record)
        print(f'{datetime.now(ZoneInfo("Asia/Seoul")).isoformat()}/hy-motion/failed {json.dumps(current_failure_record, ensure_ascii=False)}', flush=True)
        current_log_path = generation_job_path / 'worker.log'
        if current_log_path.exists():
            with current_log_path.open('rb') as current_log_stream:
                current_log_stream.seek(max(0, current_log_path.stat().st_size - 4000))
                print(current_log_stream.read().decode(errors='replace'), flush=True)
        return 1
    finally:
        current_shutdown_event.set()
        current_heartbeat_thread.join(timeout=1)


if __name__ == '__main__':
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--job-dir', type=Path, required=True)
    sys.exit(execute_generation_worker(current_argument_parser.parse_args().job_dir))
