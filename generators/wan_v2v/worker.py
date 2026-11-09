"""공식 DiffSynth Wan2.2 input_video 재노이즈 경로를 실행한다."""
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from generators.wan_v2v.contracts import V2V_JOB_STORAGE, V2V_MODEL_DIRECTORY, V2V_RUNTIME_DIRECTORY, V2V_MODEL_IDENTIFIER, V2V_MODEL_REVISION, V2V_RUNTIME_REVISION, V2V_FIXED_SETTINGS, validate_v2v_assets, read_v2v_frames
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs


def execute_v2v_inference(current_job_root,current_attempt_root,current_request_record,current_metrics_recorder):
    import torch
    import numpy as np
    sys.path.insert(0,str(V2V_RUNTIME_DIRECTORY))
    from diffsynth.pipelines.wan_video import WanVideoPipeline, ModelConfig
    current_video_path = current_job_root/'input.mp4'
    if current_request_record['input_video_file']!='input.mp4' or hashlib.sha256(current_video_path.read_bytes()).hexdigest()!=current_request_record['input_video_sha256']:
        raise ValueError('입력 영상 사본 해시 불일치')
    current_source_frames,current_source_rate = read_v2v_frames(current_video_path,current_request_record['frames'])
    current_metrics_recorder.update_generation_stage('model-load')
    current_offload_settings = dict(offload_device='disk',offload_dtype='disk',onload_device='cpu',onload_dtype=torch.bfloat16,preparing_device='cuda',preparing_dtype=torch.bfloat16,computation_device='cuda',computation_dtype=torch.bfloat16)
    current_model_configs = [ModelConfig(path=[str(current_model_path) for current_model_path in sorted((V2V_MODEL_DIRECTORY/current_expert_name).glob('diffusion_pytorch_model-*.safetensors'))],**current_offload_settings) for current_expert_name in ('high_noise_model','low_noise_model')]
    current_model_configs.extend(ModelConfig(path=str(V2V_MODEL_DIRECTORY/current_file_name),**current_offload_settings) for current_file_name in ('models_t5_umt5-xxl-enc-bf16.pth','Wan2.1_VAE.pth'))
    current_pipeline_model = WanVideoPipeline.from_pretrained(torch_dtype=torch.bfloat16,device='cuda',model_configs=current_model_configs,tokenizer_config=ModelConfig(path=str(V2V_MODEL_DIRECTORY/'google/umt5-xxl')),redirect_common_files=False,vram_limit=torch.cuda.mem_get_info()[1]/1024**3-2)
    if current_pipeline_model.dit is None or current_pipeline_model.dit2 is None:
        raise RuntimeError('Wan2.2 고·저노이즈 전문가 로드 누락')
    current_metrics_recorder.update_generation_stage('inference')
    def report_v2v_progress(current_timestep_values):
        for current_step_index,current_timestep_value in enumerate(current_timestep_values):
            yield current_timestep_value
            current_metrics_recorder.record_generation_step(current_step_index+1)
    current_output_frames = current_pipeline_model(input_video=current_source_frames,denoising_strength=current_request_record['denoising_strength'],prompt=current_request_record['prompt'],negative_prompt=current_request_record['negative_prompt'],height=480,width=832,num_frames=current_request_record['frames'],num_inference_steps=current_request_record['steps'],seed=current_request_record['seed'],progress_bar_cmd=report_v2v_progress,**V2V_FIXED_SETTINGS)
    current_output_arrays = np.stack([np.asarray(current_frame_image) for current_frame_image in current_output_frames])
    if current_output_arrays.shape != (current_request_record['frames'],480,832,3) or current_output_arrays.dtype != np.uint8:
        raise ValueError('공식 V2V 출력 형식 불일치')
    current_metrics_recorder.update_generation_stage('postprocess')
    current_output_hashes = save_video_outputs(current_attempt_root,current_output_arrays,current_source_rate)
    return dict(attempt=current_attempt_root.name,frames=len(current_output_frames),fps=current_source_rate,output_sha256=current_output_hashes,model_id=V2V_MODEL_IDENTIFIER,model_revision=V2V_MODEL_REVISION,runtime_revision=V2V_RUNTIME_REVISION,denoising_strength=current_request_record['denoising_strength'],fixed_settings=V2V_FIXED_SETTINGS,prompt_words=len(current_request_record['prompt'].split()),prompt_sha256=hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(),negative_prompt_words=len(current_request_record['negative_prompt'].split()),negative_prompt_sha256=hashlib.sha256(current_request_record['negative_prompt'].encode()).hexdigest(),quality_status='사용자 검수 대기')

if __name__=='__main__':
    run_reference_video_worker(V2V_JOB_STORAGE,Path(__file__),validate_v2v_assets,execute_v2v_inference)
