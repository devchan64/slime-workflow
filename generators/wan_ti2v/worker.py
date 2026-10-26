"""Wan2.2 TI2V 5B Q4를 단계별 CUDA 로드·해제로 실행한다."""
from pathlib import Path
import gc
import hashlib
import os
import sys
import importlib.util

TI2V_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TI2V_WORKSPACE_ROOT))

from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from generators.wan_ti2v.contracts import TI2V_JOB_STORAGE, TI2V_MODEL_FILES, TI2V_MODEL_IDENTIFIER, TI2V_MODEL_REVISION, TI2V_RUNTIME_DIRECTORY, validate_ti2v_assets
from tools.review.common.generation_records import write_record_atomically
from generators.wan_ti2v.diagnostics import summarize_temporal_tensor

TI2V_DECODE_TILE_LATENTS = 16
TI2V_DECODE_OVERLAP_LATENTS = 4
TI2V_DECODE_TEMPORAL_OVERLAP = 1


def execute_ti2v_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'
    sys.path.insert(0, str(TI2V_RUNTIME_DIRECTORY / 'ComfyUI'))
    import numpy as np
    import torch
    from PIL import Image
    import comfy.cli_args
    comfy.cli_args.args.lowvram = True
    import comfy.model_management
    import comfy.sample
    import folder_paths
    import nodes
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from comfy_extras.nodes_wan import Wan22ImageToVideoLatent
    from generators.common.wan_video_memory import TiledWanVideoVae

    if not torch.cuda.is_available():
        raise RuntimeError('Wan2.2 TI2V는 CUDA GPU가 필요합니다.')
    def resolve_encoder_cuda():
        return torch.device('cuda:0')
    comfy.model_management.text_encoder_device = resolve_encoder_cuda
    current_package_spec = importlib.util.spec_from_file_location('ti2v_gguf_runtime', TI2V_RUNTIME_DIRECTORY / 'ComfyUI-GGUF/__init__.py', submodule_search_locations=[str(TI2V_RUNTIME_DIRECTORY / 'ComfyUI-GGUF')])
    current_package_module = importlib.util.module_from_spec(current_package_spec)
    sys.modules[current_package_spec.name] = current_package_module
    current_package_spec.loader.exec_module(current_package_module)
    for current_folder_name, current_relative_path in (('unet_gguf', '.model/wan22-ti2v/diffusion_models'), ('diffusion_models', '.model/wan22-ti2v/diffusion_models'), ('clip', '.model/wan22-animate-components'), ('clip_gguf', '.model/wan22-animate-components'), ('vae', '.model/wan22-ti2v/vae')):
        folder_paths.add_model_folder_path(current_folder_name, str(TI2V_WORKSPACE_ROOT / current_relative_path))
    current_metrics_recorder.update_generation_stage('load')
    current_text_encoder = current_package_module.NODE_CLASS_MAPPINGS['CLIPLoaderGGUF']().load_clip(Path(TI2V_MODEL_FILES['encoder']).name, type='wan')[0]
    if current_text_encoder.patcher.load_device.type != 'cuda':
        raise RuntimeError('텍스트 인코더 CUDA 설정 오류')
    current_positive_conditioning = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['prompt'])[0]
    current_negative_conditioning = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['negative_prompt'])[0]
    comfy.model_management.unload_all_models()
    del current_text_encoder
    gc.collect()
    comfy.model_management.soft_empty_cache()
    current_vae_model = TiledWanVideoVae(nodes.VAELoader().load_vae('wan2.2_vae.safetensors')[0])
    current_start_image = None
    if current_request_record['references']:
        with Image.open(current_job_root / current_request_record['references'][0]) as current_image_file:
            current_image_array = np.asarray(current_image_file.convert('RGB'), dtype=np.float32) / 255.0
        current_start_image = torch.from_numpy(current_image_array).unsqueeze(0)
    current_metrics_recorder.update_generation_stage('encoding')
    current_latent_record = Wan22ImageToVideoLatent().execute(current_vae_model, current_request_record['width'], current_request_record['height'], current_request_record['frames'], 1, current_start_image)[0]
    comfy.model_management.unload_all_models()
    comfy.model_management.soft_empty_cache()
    current_diffusion_name = Path(TI2V_MODEL_FILES['diffusion']).name
    current_diffusion_model = current_package_module.NODE_CLASS_MAPPINGS['UnetLoaderGGUF']().load_unet(current_diffusion_name)[0]
    current_diffusion_model = ModelSamplingSD3().patch(current_diffusion_model, current_request_record['flow_shift'])[0]
    current_noise_tensor = comfy.sample.prepare_noise(current_latent_record['samples'], current_request_record['seed'])
    current_diagnostic_record = {
        'schema_version': 1, 'attempt': current_attempt_root.name,
        'seed': current_request_record['seed'], 'requested_frames': current_request_record['frames'],
        'interpretation': '인접 시간 구간 MAE는 변화량이며 보행 점수가 아닙니다. 잠재값과 픽셀의 수치는 직접 비교하지 않습니다.',
        'initial_latent': summarize_temporal_tensor(current_latent_record['samples'], 2),
        'initial_noise': summarize_temporal_tensor(current_noise_tensor, 2),
        'noise_mask': summarize_temporal_tensor(current_latent_record['noise_mask'], 2) if 'noise_mask' in current_latent_record else None,
    }
    write_record_atomically(current_attempt_root / 'temporal-diagnostics.json', current_diagnostic_record)
    current_metrics_recorder.update_generation_stage('inference')

    def record_ti2v_step(current_step_index, current_denoised_tensor, current_sample_tensor, current_step_total):
        current_metrics_recorder.record_generation_step(current_step_index + 1)

    current_sample_tensor = comfy.sample.sample(current_diffusion_model, current_noise_tensor, current_request_record['steps'], current_request_record['guidance_scale'], 'uni_pc', 'simple', current_positive_conditioning, current_negative_conditioning, current_latent_record['samples'], noise_mask=current_latent_record.get('noise_mask'), callback=record_ti2v_step, seed=current_request_record['seed'])
    comfy.model_management.unload_all_models()
    del current_diffusion_model
    gc.collect()
    comfy.model_management.soft_empty_cache()
    current_diagnostic_record['sampled_latent'] = summarize_temporal_tensor(current_sample_tensor, 2)
    write_record_atomically(current_attempt_root / 'temporal-diagnostics.json', current_diagnostic_record)
    current_metrics_recorder.update_generation_stage('saving')
    current_temporal_tile_count = max(2, current_sample_tensor.shape[2])
    write_record_atomically(current_attempt_root / 'memory-policy.json', {'diffusion': 'Q4_K_M', 'encoder': 'Q4_K_M', 'compute_device': 'cuda', 'offload_device': 'cpu', 'sequential_stages': True, 'decode_spatial_tile': TI2V_DECODE_TILE_LATENTS, 'decode_spatial_overlap': TI2V_DECODE_OVERLAP_LATENTS, 'decode_temporal_tile': current_temporal_tile_count, 'decode_temporal_overlap': TI2V_DECODE_TEMPORAL_OVERLAP, 'model_revision': TI2V_MODEL_REVISION})
    current_decoded_frames = current_vae_model.decode_tiled(current_sample_tensor, tile_x=TI2V_DECODE_TILE_LATENTS, tile_y=TI2V_DECODE_TILE_LATENTS, overlap=TI2V_DECODE_OVERLAP_LATENTS, tile_t=current_temporal_tile_count, overlap_t=TI2V_DECODE_TEMPORAL_OVERLAP)
    if current_decoded_frames.ndim == 5:
        current_decoded_frames = current_decoded_frames.flatten(0, 1)
    if current_decoded_frames.shape[0] != current_request_record['frames']:
        raise ValueError('출력 프레임 수 불일치')
    current_frame_arrays = (current_decoded_frames.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    current_diagnostic_record['decoded_pixels'] = summarize_temporal_tensor(current_decoded_frames, 0)
    write_record_atomically(current_attempt_root / 'temporal-diagnostics.json', current_diagnostic_record)
    current_output_hashes = save_video_outputs(current_attempt_root, current_frame_arrays, 24)
    write_record_atomically(current_attempt_root / 'conditioning.json', {'mode': 'i2v' if current_start_image is not None else 't2v', 'sampler': 'uni_pc', 'scheduler': 'simple', 'flow_shift': current_request_record['flow_shift'], 'reference_count': len(current_request_record['references'])})
    comfy.model_management.unload_all_models()
    del current_vae_model
    gc.collect()
    return {'attempt': current_attempt_root.name, 'frames': len(current_frame_arrays), 'fps': 24, 'output_sha256': current_output_hashes, 'model_id': TI2V_MODEL_IDENTIFIER, 'model_revision': TI2V_MODEL_REVISION, 'prompt_words': len(current_request_record['prompt'].split()), 'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(), 'temporal_diagnostics': 'temporal-diagnostics.json', 'quality_status': '사용자 검수 대기'}


if __name__ == '__main__':
    run_reference_video_worker(TI2V_JOB_STORAGE, Path(__file__), validate_ti2v_assets, execute_ti2v_inference)
