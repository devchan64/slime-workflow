"""Wan2.1 VACE 고정 R2V 작업자. 추론은 CUDA에서만 실행한다."""
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
from generators.vace.contracts import VACE_JOB_STORAGE_ROOT, verify_vace_request, validate_vace_assets
from tools.review.common.generation_records import write_record_atomically
from tools.review.common.generation_telemetry import GenerationTelemetryRecorder


def handle_worker_signal(current_signal_number, current_stack_frame):
    raise InterruptedError(f'종료 신호 {current_signal_number}')


def execute_vace_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    import torch
    import diffusers
    from PIL import Image, ImageOps
    from diffusers import WanVACEPipeline, AutoencoderKLWan, UniPCMultistepScheduler
    from diffusers.hooks import apply_group_offloading
    from diffusers.utils import export_to_video
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA를 사용할 수 없습니다. CPU 추론으로 대체하지 않습니다.')
    current_model_root = validate_vace_assets()
    current_model_config = current_request_record['vace']
    current_reference_image = Image.open(current_job_root/'reference-1.png').convert('RGB')
    current_reference_image = ImageOps.pad(current_reference_image,(current_model_config['width'],current_model_config['height']),method=Image.Resampling.BICUBIC,color='white')
    current_reference_image.save(current_attempt_root/'reference-input.png')
    (current_attempt_root/'prompt.txt').write_text(current_request_record['prompt'])
    (current_attempt_root/'negative-prompt.txt').write_text(current_model_config['negative_prompt'])
    write_record_atomically(current_attempt_root/'input-contract.json',{'task':'r2v','video':None,'mask':None,'reference_count':1,'first_frame_fixed':False})
    current_metrics_recorder.update_generation_stage('load')
    torch.cuda.reset_peak_memory_stats()
    current_vae_model = AutoencoderKLWan.from_pretrained(current_model_root,subfolder='vae',torch_dtype=torch.float32,local_files_only=True)
    current_pipeline_model = WanVACEPipeline.from_pretrained(current_model_root,vae=current_vae_model,torch_dtype=torch.bfloat16,local_files_only=True)
    apply_group_offloading(current_pipeline_model.text_encoder,onload_device=torch.device('cuda'),offload_type='leaf_level')
    current_pipeline_model.transformer.enable_group_offload(onload_device=torch.device('cuda'),offload_type='block_level',num_blocks_per_group=1)
    current_pipeline_model.vae.enable_tiling()
    current_pipeline_model.vae.to('cuda')
    current_pipeline_model.scheduler = UniPCMultistepScheduler.from_config(current_pipeline_model.scheduler.config,flow_shift=current_model_config['flow_shift'])
    def verify_cuda_output(current_module_value, current_input_values, current_output_value):
        if hasattr(current_output_value,'device') and current_output_value.device.type!='cuda':
            raise RuntimeError('모델 레이어 출력이 CUDA에 없습니다.')
    for current_component_model in (current_pipeline_model.text_encoder,current_pipeline_model.transformer,current_pipeline_model.vae):
        for current_module_value in current_component_model.modules():
            if isinstance(current_module_value,(torch.nn.Linear,torch.nn.Conv2d,torch.nn.Conv3d,torch.nn.Embedding)):
                current_module_value.register_forward_hook(verify_cuda_output)
    def record_inference_step(current_pipeline_value,current_step_index,current_timestep_value,current_callback_values):
        current_metrics_recorder.record_generation_step(current_step_index+1)
        return current_callback_values
    if len(current_pipeline_model.tokenizer(current_request_record['prompt']).input_ids)>512:
        raise ValueError('VACE 프롬프트가 512 토큰 한도를 초과합니다.')
    if len(current_pipeline_model.tokenizer(current_model_config['negative_prompt']).input_ids)>512:
        raise ValueError('VACE 부정 프롬프트가 512 토큰 한도를 초과합니다.')
    current_metrics_recorder.update_generation_stage('inference')
    current_output_frames = current_pipeline_model(prompt=current_request_record['prompt'],negative_prompt=current_model_config['negative_prompt'],video=None,mask=None,reference_images=[current_reference_image],height=current_model_config['height'],width=current_model_config['width'],num_frames=current_request_record['frames'],num_inference_steps=current_model_config['steps'],guidance_scale=current_model_config['guidance_scale'],conditioning_scale=current_model_config['conditioning_scale'],generator=torch.Generator(device='cpu').manual_seed(current_request_record['seed']),output_type='pil',callback_on_step_end=record_inference_step).frames[0]
    if len(current_output_frames)!=current_request_record['frames'] or any(current_frame_image.size!=(current_model_config['width'],current_model_config['height']) for current_frame_image in current_output_frames):
        raise ValueError('VACE 출력 프레임 수·크기 불일치')
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
    return {'attempt':current_attempt_root.name,'frames':len(current_output_frames),'fps':16,'duration_seconds':len(current_output_frames)/16,'output_sha256':current_output_hashes,'model_id':current_model_config['model_id'],'model_root':str(current_model_root),'model_revision_verified':False,'diffusers_version':diffusers.__version__,'torch_version':torch.__version__,'rng_device':'cpu','model_compute_device':'cuda','prompt_words':len(current_request_record['prompt'].split()),'prompt_sha256':current_model_config['prompt_sha256'],'torch_peak_allocated_mib':torch.cuda.max_memory_allocated()/2**20,'torch_peak_reserved_mib':torch.cuda.max_memory_reserved()/2**20,'negative_prompt_words':len(current_model_config['negative_prompt'].split()),'negative_prompt_sha256':hashlib.sha256(current_model_config['negative_prompt'].encode()).hexdigest(),'quality_status':'사용자 검수 대기'}


def execute_vace_worker():
    current_argument_parser = argparse.ArgumentParser(description=__doc__)
    current_argument_parser.add_argument('--job-dir',type=Path,required=True)
    current_job_root = current_argument_parser.parse_args().job_dir.resolve()
    if current_job_root.parent != VACE_JOB_STORAGE_ROOT.resolve():
        raise ValueError('VACE 작업 경로 오류')
    current_attempt_root = current_job_root/'attempts'/uuid.uuid4().hex
    current_attempt_root.mkdir(parents=True)
    write_record_atomically(current_job_root/'current-attempt.json',{'id':current_attempt_root.name})
    current_request_record = verify_vace_request(current_job_root)
    current_duration_samples = []
    current_metrics_recorder = GenerationTelemetryRecorder(current_attempt_root,current_request_record['steps'],current_duration_samples)
    current_metrics_recorder.start_generation_telemetry()
    current_final_status = 'failed'
    signal.signal(signal.SIGTERM,handle_worker_signal)
    signal.signal(signal.SIGINT,handle_worker_signal)
    try:
        current_request_record = verify_vace_request(current_job_root)
        (current_attempt_root/'request.json').write_text(json.dumps(current_request_record,ensure_ascii=False))
        (current_attempt_root/'executor-source.py').write_bytes(Path(__file__).read_bytes())
        for current_previous_path in VACE_JOB_STORAGE_ROOT.glob('*/attempts/*/result.json'):
            current_previous_result = json.loads(current_previous_path.read_text())
            current_previous_request = json.loads((current_previous_path.parent/'request.json').read_text())
            if all(current_previous_request['vace'].get(current_setting_name)==current_request_record['vace'].get(current_setting_name) for current_setting_name in ('model_id','width','height','frames','steps','flow_shift','guidance_scale','conditioning_scale')):
                current_previous_metrics = json.loads((current_previous_path.parent/'metrics.json').read_text())
                if current_previous_metrics['status']=='completed':
                    current_duration_samples.append(current_previous_metrics['elapsed_seconds'])
        print(f"{current_metrics_recorder.current_run_state['started_at']}/vace/start R2V 입력={current_job_root/'reference-1.png'} 출력={current_attempt_root}",flush=True)
        current_result_record = execute_vace_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder)
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
    execute_vace_worker()
