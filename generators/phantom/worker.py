"""Wan2.1 PHANTOM 고정 R2V 작업자. 추론은 CUDA에서만 실행한다."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import traceback
import uuid
import zipfile

WORKFLOW_ROOT_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(WORKFLOW_ROOT_DIRECTORY))
from generators.phantom.contracts import PHANTOM_JOB_STORAGE_ROOT, verify_phantom_request, validate_phantom_assets
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


def handle_worker_signal(current_signal_number, current_stack_frame):
    raise InterruptedError(f'종료 신호 {current_signal_number}')


def execute_phantom_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    import torch
    import diffusers
    from PIL import Image, ImageOps
    from diffusers.utils import export_to_video
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA를 사용할 수 없습니다. CPU 추론으로 대체하지 않습니다.')
    current_model_root = validate_phantom_assets()
    current_model_config = current_request_record['phantom']
    for current_reference_index,current_reference_name in enumerate(current_request_record['references']):
        current_reference_image = Image.open(current_job_root/current_reference_name).convert('RGB')
        current_target_width,current_target_height=832,480
        current_image_ratio=current_reference_image.width/current_reference_image.height
        if current_image_ratio>current_target_width/current_target_height:
            current_resize_width=current_target_width
            current_resize_height=int(current_resize_width/current_image_ratio)
        else:
            current_resize_height=current_target_height
            current_resize_width=int(current_resize_height*current_image_ratio)
        current_reference_image=current_reference_image.resize((current_resize_width,current_resize_height),Image.Resampling.LANCZOS)
        current_delta_width=current_target_width-current_resize_width
        current_delta_height=current_target_height-current_resize_height
        current_reference_image=ImageOps.expand(current_reference_image,(current_delta_width//2,current_delta_height//2,current_delta_width-current_delta_width//2,current_delta_height-current_delta_height//2),fill=(255,255,255))
        current_reference_image.save(current_attempt_root/f'reference-{current_reference_index+1}.png')
    (current_attempt_root/'prompt.txt').write_text(current_request_record['prompt'])
    (current_attempt_root/'negative-prompt.txt').write_text(current_model_config['negative_prompt'])
    write_record_atomically(current_attempt_root/'input-contract.json',{'task':'s2v','video':None,'mask':None,'reference_count':len(current_request_record['references']),'first_frame_fixed':False})
    from generators.phantom.runtime import generate_phantom_frames
    current_metrics_recorder.update_generation_stage('load')
    current_output_frames,current_runtime_record=generate_phantom_frames(current_request_record,current_attempt_root,current_metrics_recorder)
    if len(current_output_frames)!=current_request_record['frames'] or any(current_frame_image.size!=(832,480) for current_frame_image in current_output_frames):
        raise ValueError('Phantom 출력 계약 불일치')
    current_metrics_recorder.update_generation_stage('saving')
    current_output_hashes = []
    with zipfile.ZipFile(current_attempt_root/'frames.zip','w',zipfile.ZIP_DEFLATED) as current_archive_file:
        for current_frame_index,current_frame_image in enumerate(current_output_frames):
            current_frame_path = current_attempt_root/f'output-{current_frame_index:03d}.png'
            current_frame_image.save(current_frame_path)
            current_output_hashes.append(hashlib.sha256(current_frame_path.read_bytes()).hexdigest())
            current_archive_file.write(current_frame_path,current_frame_path.name)
    export_to_video(current_output_frames,str(current_attempt_root/'preview.mp4'),fps=16)
    current_output_frames[0].save(current_attempt_root/'preview.gif',save_all=True,append_images=current_output_frames[1:],duration=[round((current_frame_index+1)*100/16)*10-round(current_frame_index*100/16)*10 for current_frame_index in range(len(current_output_frames))],loop=0)
    return {**current_runtime_record,'attempt':current_attempt_root.name,'frames':len(current_output_frames),'fps':16,'duration_seconds':len(current_output_frames)/16,'output_sha256':current_output_hashes,'model_id':current_model_config['model_id'],'model_root':str(current_model_root),'model_revision_verified':False,'diffusers_version':diffusers.__version__,'torch_version':torch.__version__,'rng_device':'cuda','model_compute_device':'cuda','prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':current_model_config['prompt_sha256'],'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,'torch_peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20,'negative_prompt_words':len(current_model_config['negative_prompt'].split()),'negative_prompt_sha256':hashlib.sha256(current_model_config['negative_prompt'].encode()).hexdigest(),'quality_status':'사용자 검수 대기'}


def execute_phantom_worker():
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--job-dir',type=Path,required=True)
    current_job_root = current_argument_parser.parse_args().job_dir.resolve()
    if current_job_root.parent != PHANTOM_JOB_STORAGE_ROOT.resolve():
        raise ValueError('PHANTOM 작업 경로 오류')
    current_attempt_root = current_job_root/'attempts'/uuid.uuid4().hex
    current_attempt_root.mkdir(parents=True)
    write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_root.name})
    current_request_record = verify_phantom_request(current_job_root)
    current_duration_samples = []
    current_metrics_recorder = GenerationTelemetryRecorder(current_attempt_root,current_request_record['steps'],current_duration_samples)
    current_metrics_recorder.start_generation_telemetry()
    current_final_status = 'failed'
    signal.signal(signal.SIGTERM,handle_worker_signal)
    signal.signal(signal.SIGINT,handle_worker_signal)
    try:
        current_request_record = verify_phantom_request(current_job_root)
        (current_attempt_root/'request.json').write_text(json.dumps(current_request_record,ensure_ascii=False))
        (current_attempt_root/'executor-source.py').write_bytes(Path(__file__).read_bytes())
        for current_previous_path in PHANTOM_JOB_STORAGE_ROOT.glob('*/attempts/*/result.json'):
            current_previous_result = json.loads(current_previous_path.read_text())
            current_previous_request = json.loads((current_previous_path.parent/'request.json').read_text())
            if all(current_previous_request['phantom'].get(current_setting_name)==current_request_record['phantom'].get(current_setting_name) for current_setting_name in ('model_id','width','height','frames','steps','flow_shift','guidance_scale','conditioning_scale')):
                current_previous_metrics = json.loads((current_previous_path.parent/'metrics.json').read_text())
                if current_previous_metrics['status']=='completed':
                    current_duration_samples.append(current_previous_metrics['elapsed_seconds'])
        print(f"{current_metrics_recorder.current_run_state['started_at']}/phantom/start R2V 입력={current_job_root/'reference-1.png'} 출력={current_attempt_root}",flush=True)
        current_result_record = execute_phantom_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder)
        write_record_atomically(current_attempt_root/'result.json',current_result_record)
        write_record_atomically(current_job_root/'result.json',current_result_record)
        current_final_status = 'completed'
    except BaseException as current_execution_error:
        current_final_status = 'cancelled' if isinstance(current_execution_error,(InterruptedError,KeyboardInterrupt)) else 'failed'
        write_record_atomically(current_attempt_root/'error.json',{'error':str(current_execution_error),'traceback':traceback.format_exc()})
        traceback.print_exc()
        raise
    finally:
        current_metrics_recorder.finish_generation_telemetry(current_final_status)
        write_record_atomically(current_job_root/'status.json',{'status':current_final_status,'attempt':current_attempt_root.name})


if __name__ == '__main__':
    execute_phantom_worker()
