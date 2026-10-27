"""VACE-Fun Q4 고·저노이즈 전문가를 CUDA에서 순차 실행한다."""
from pathlib import Path
import sys
import os
import gc
import hashlib
import importlib.util
VACE_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VACE_WORKSPACE_ROOT))
from generators.wan_vace.contracts import VACE_JOB_STORAGE, VACE_RUNTIME_DIRECTORY, VACE_MODEL_FILES, VACE_MODEL_REVISION, VACE_MODEL_IDENTIFIER, VACE_SOURCE_REVISION, VACE_EXPERT_BOUNDARY, verify_vace_weights, locate_expert_switch
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from tools.review.common.generation_records import write_record_atomically


def build_vace_conditions(current_request_record, current_reference_tensor):
    """외형 참조는 별도 잠재 슬롯, 첫 프레임은 비편집 마스크로 전달한다."""
    import torch
    current_frame_count = current_request_record['frames']
    if current_request_record['mode'] == 'reference':
        return {'reference_image': current_reference_tensor}
    if current_request_record['mode'] == 'first_frame':
        current_video_tensor = torch.full((current_frame_count, 480, 832, 3), 0.5)
        current_video_tensor[:1] = current_reference_tensor
        current_mask_tensor = torch.ones((current_frame_count, 480, 832))
        current_mask_tensor[:1] = 0
        return {'control_video': current_video_tensor, 'control_masks': current_mask_tensor}
    return {}


def execute_vace_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'
    sys.path.insert(0, str(VACE_RUNTIME_DIRECTORY / 'ComfyUI'))
    import torch
    import numpy as np
    from PIL import Image
    from diffusers import FlowMatchEulerDiscreteScheduler
    import comfy.cli_args
    comfy.cli_args.args.lowvram = True
    import nodes, folder_paths, comfy.model_management, comfy.sample
    from comfy_extras.nodes_wan import WanVaceToVideo
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from generators.common.wan_video_memory import TiledWanVideoVae
    def resolve_encoder_cuda():
        return torch.device('cuda:0')
    comfy.model_management.text_encoder_device = resolve_encoder_cuda
    current_package_spec = importlib.util.spec_from_file_location('vace_gguf_runtime', VACE_RUNTIME_DIRECTORY / 'ComfyUI-GGUF/__init__.py', submodule_search_locations=[str(VACE_RUNTIME_DIRECTORY / 'ComfyUI-GGUF')])
    current_package_module = importlib.util.module_from_spec(current_package_spec)
    sys.modules[current_package_spec.name] = current_package_module
    current_package_spec.loader.exec_module(current_package_module)
    for current_folder_name, current_folder_path in [('unet_gguf', '.model/wan22-vace'), ('diffusion_models', '.model/wan22-vace'), ('clip', '.model/wan22-animate-components'), ('clip_gguf', '.model/wan22-animate-components'), ('vae', '.model/wan22-animate-components/split_files/vae')]:
        folder_paths.add_model_folder_path(current_folder_name, str(VACE_WORKSPACE_ROOT / current_folder_path))
    current_metrics_recorder.update_generation_stage('load')
    current_text_encoder = current_package_module.NODE_CLASS_MAPPINGS['CLIPLoaderGGUF']().load_clip('umt5-xxl-encoder-Q4_K_M.gguf', type='wan')[0]
    if current_text_encoder.patcher.load_device.type != 'cuda':
        raise RuntimeError('텍스트 인코더 CUDA 설정 오류')
    positive_condition_data = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['prompt'])[0]
    negative_condition_data = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['negative_prompt'])[0]
    comfy.model_management.unload_all_models()
    del current_text_encoder
    gc.collect()
    comfy.model_management.soft_empty_cache()
    current_metrics_recorder.update_generation_stage('encoding')
    current_vae_model = TiledWanVideoVae(nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0])
    current_reference_tensor = None
    if current_request_record['references']:
        with Image.open(current_job_root / current_request_record['references'][0]) as current_image_file:
            current_reference_tensor = torch.from_numpy(np.asarray(current_image_file.convert('RGB'), dtype=np.float32) / 255.0).unsqueeze(0)
    current_condition_output = WanVaceToVideo.execute(positive_condition_data, negative_condition_data, current_vae_model, 832, 480, current_request_record['frames'], 1, current_request_record['reference_strength'], **build_vace_conditions(current_request_record, current_reference_tensor))
    positive_condition_data, negative_condition_data, current_latent_record, reference_trim_count = current_condition_output[:4]
    expected_reference_trim = 1 if current_request_record['mode'] == 'reference' else 0
    if reference_trim_count != expected_reference_trim:
        raise ValueError('VACE 참조 잠재 슬롯 수 불일치')
    comfy.model_management.unload_all_models()
    comfy.model_management.soft_empty_cache()
    current_step_total = current_request_record['steps']
    # 제작자 Flow 경로와 같은 Diffusers sigma 배열을 그대로 사용한다.
    current_flow_scheduler = FlowMatchEulerDiscreteScheduler(num_train_timesteps=1000, shift=current_request_record['flow_shift'], use_dynamic_shifting=False)
    current_flow_scheduler.set_timesteps(current_step_total)
    current_sigma_values = current_flow_scheduler.sigmas.cpu()
    current_switch_step = locate_expert_switch(current_sigma_values)
    write_record_atomically(current_attempt_root / 'conditioning.json', {
        'mode': current_request_record['mode'], 'trim_latent': reference_trim_count,
        'reference_strength': current_request_record['reference_strength'],
        'switch_step': current_switch_step, 'boundary': VACE_EXPERT_BOUNDARY,
        'sampler': 'euler', 'scheduler': 'Diffusers FlowMatchEulerDiscreteScheduler',
        'sigmas': current_sigma_values.tolist(), 'source_revision': VACE_SOURCE_REVISION,
        'implementation': 'ComfyUI WanVaceToVideo + GGUF; 제작자 BF16 파이프라인과 동일 구현은 아님',
    })
    write_record_atomically(current_attempt_root / 'model-selection.json', {'model_id': VACE_MODEL_IDENTIFIER, 'revision': VACE_MODEL_REVISION, 'files': VACE_MODEL_FILES, 'quantization': 'Q4_K_M', 'compute_device': 'cuda', 'offload_device': 'cpu'})
    current_latent_tensor = current_latent_record['samples']
    current_noise_tensor = comfy.sample.prepare_noise(current_latent_tensor, current_request_record['seed'])
    for current_model_stage, current_start_step, current_end_step in [('high', 0, current_switch_step), ('low', current_switch_step, current_step_total)]:
        current_metrics_recorder.update_generation_stage('load')
        current_model_relative = Path(VACE_MODEL_FILES[current_model_stage][0]).relative_to('.model/wan22-vace')
        current_diffusion_model = current_package_module.NODE_CLASS_MAPPINGS['UnetLoaderGGUF']().load_unet(str(current_model_relative))[0]
        current_diffusion_model = ModelSamplingSD3().patch(current_diffusion_model, current_request_record['flow_shift'])[0]
        if current_diffusion_model.model.model_config.unet_config.get('model_type') != 'vace':
            raise RuntimeError('로드한 가중치가 VACE 모델로 인식되지 않았습니다.')
        current_metrics_recorder.update_generation_stage('inference')
        def record_vace_step(current_step_index, current_denoised_tensor, current_sample_tensor, current_stage_total):
            current_metrics_recorder.record_generation_step(current_start_step + current_step_index + 1)
        current_latent_tensor = comfy.sample.sample(current_diffusion_model, current_noise_tensor if current_start_step == 0 else torch.zeros_like(current_noise_tensor), current_step_total, current_request_record['guidance_scale'], 'euler', 'simple', positive_condition_data, negative_condition_data, current_latent_tensor, denoise=1.0, disable_noise=current_start_step != 0, start_step=current_start_step, last_step=current_end_step, force_full_denoise=current_end_step == current_step_total, sigmas=current_sigma_values, callback=record_vace_step, seed=current_request_record['seed'])
        comfy.model_management.unload_all_models()
        del current_diffusion_model
        gc.collect()
        comfy.model_management.soft_empty_cache()
    current_metrics_recorder.update_generation_stage('saving')
    current_latent_tensor = current_latent_tensor[:, :, reference_trim_count:]
    if current_latent_tensor.shape[2] != (current_request_record['frames'] - 1) // 4 + 1:
        raise ValueError('참조 슬롯 제거 후 출력 시간축 불일치')
    current_temporal_tile_count = max(2, current_latent_tensor.shape[2])
    write_record_atomically(current_attempt_root / 'decode-policy.json', {'trim_latent': reference_trim_count, 'temporal_tile': current_temporal_tile_count, 'spatial_tile': 32, 'spatial_overlap': 8, 'fps': 16})
    current_decoded_frames = current_vae_model.decode(current_latent_tensor, current_temporal_tile_count=current_temporal_tile_count)
    if current_decoded_frames.shape[0] != current_request_record['frames'] or not torch.isfinite(current_decoded_frames).all():
        raise ValueError('출력 프레임 수 또는 유한값 검증 실패')
    current_frame_arrays = (current_decoded_frames.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    current_output_hashes = save_video_outputs(current_attempt_root, current_frame_arrays, 16)
    comfy.model_management.unload_all_models()
    return {'attempt': current_attempt_root.name, 'mode': current_request_record['mode'], 'frames': len(current_frame_arrays), 'fps': 16, 'output_sha256': current_output_hashes, 'model_id': VACE_MODEL_IDENTIFIER, 'model_revision': VACE_MODEL_REVISION, 'prompt': current_request_record['prompt'], 'prompt_words': len(current_request_record['prompt'].split()), 'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(), 'negative_prompt_words': len(current_request_record['negative_prompt'].split()), 'quality_status': '사용자 검수 대기'}


if __name__ == '__main__':
    run_reference_video_worker(VACE_JOB_STORAGE, Path(__file__), verify_vace_weights, execute_vace_inference)
