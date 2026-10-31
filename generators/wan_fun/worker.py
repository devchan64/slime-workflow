"""Fun Control Q4 고·저노이즈 모델을 순차 로드하는 GPU 작업자."""
from pathlib import Path
import sys
import os
import gc
import hashlib
import importlib.util
FUN_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FUN_WORKSPACE_ROOT))
from generators.wan_fun.contracts import FUN_JOB_STORAGE, FUN_RUNTIME_DIRECTORY, FUN_MODEL_FILES, FUN_MODEL_REVISION, validate_fun_assets
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from tools.review.common.generation_records import write_record_atomically


def execute_fun_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    current_control_paths = [current_job_root/current_reference_name for current_reference_name in current_request_record['references']]
    if current_request_record.get('driving_video_file'):
        import subprocess
        import json
        current_metrics_recorder.update_generation_stage('pose-preprocess')
        subprocess.run([str(FUN_WORKSPACE_ROOT/'.venv/bin/python'), str(Path(__file__).with_name('pose_preprocess.py')), str(current_job_root), str(current_attempt_root)], env={**os.environ, 'PYTHONPATH': str(FUN_RUNTIME_DIRECTORY/'preprocess-deps')}, check=True)
        current_preprocess_record = json.loads((current_attempt_root/'pose-preprocess.json').read_text())
        current_control_paths.extend(Path(current_frame_path) for current_frame_path in current_preprocess_record['frames'])
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:True'
    sys.path.insert(0, str(FUN_RUNTIME_DIRECTORY / 'ComfyUI'))
    import torch
    import numpy as np
    from PIL import Image
    import comfy.cli_args
    comfy.cli_args.args.lowvram = True
    import nodes, folder_paths, comfy.model_management, comfy.sample
    from comfy_extras.nodes_wan import Wan22FunControlToVideo
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from generators.common.wan_video_memory import TiledWanVideoVae
    def resolve_encoder_cuda():
        return torch.device('cuda:0')
    comfy.model_management.text_encoder_device = resolve_encoder_cuda
    current_package_spec = importlib.util.spec_from_file_location('fun_gguf_runtime', FUN_RUNTIME_DIRECTORY / 'ComfyUI-GGUF/__init__.py', submodule_search_locations=[str(FUN_RUNTIME_DIRECTORY / 'ComfyUI-GGUF')])
    current_package_module = importlib.util.module_from_spec(current_package_spec)
    sys.modules[current_package_spec.name] = current_package_module
    current_package_spec.loader.exec_module(current_package_module)
    for current_folder_name, current_folder_path in [('unet_gguf', '.model/wan22-fun-control'), ('diffusion_models', '.model/wan22-fun-control'), ('clip', '.model/wan22-animate-components'), ('clip_gguf', '.model/wan22-animate-components'), ('vae', '.model/wan22-animate-components/split_files/vae')]:
        folder_paths.add_model_folder_path(current_folder_name, str(FUN_WORKSPACE_ROOT / current_folder_path))
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
    current_image_tensors = []
    for current_reference_name in current_control_paths:
        with Image.open(current_reference_name) as current_image_file:
            current_image_tensors.append(torch.from_numpy(np.asarray(current_image_file.convert('RGB'), dtype=np.float32) / 255.0))
    current_condition_output = Wan22FunControlToVideo.execute(positive_condition_data, negative_condition_data, current_vae_model, 832, 480, current_request_record['frames'], 1, ref_image=current_image_tensors[0].unsqueeze(0), control_video=torch.stack(current_image_tensors[1:]))
    positive_condition_data, negative_condition_data, current_latent_record = current_condition_output[:3]
    comfy.model_management.unload_all_models()
    comfy.model_management.soft_empty_cache()
    current_step_total = current_request_record['steps']
    current_switch_step = max(1, min(current_step_total - 1, round(current_step_total * current_request_record['switch_ratio'])))
    write_record_atomically(current_attempt_root / 'conditioning.json', {'control_type': current_request_record['control_type'], 'reference_mode': 'reference_latents', 'face_video': False, 'switch_step': current_switch_step, 'sampler': 'euler', 'scheduler': 'simple', 'model_revision': FUN_MODEL_REVISION, 'tiled_vae': True})
    current_latent_tensor = current_latent_record['samples']
    current_noise_tensor = comfy.sample.prepare_noise(current_latent_tensor, current_request_record['seed'])
    for current_model_stage, current_start_step, current_end_step in [('high', 0, current_switch_step), ('low', current_switch_step, current_step_total)]:
        current_metrics_recorder.update_generation_stage('load')
        current_model_relative = Path(FUN_MODEL_FILES[current_model_stage][0]).relative_to('.model/wan22-fun-control')
        current_diffusion_model = current_package_module.NODE_CLASS_MAPPINGS['UnetLoaderGGUF']().load_unet(str(current_model_relative))[0]
        current_diffusion_model = ModelSamplingSD3().patch(current_diffusion_model, current_request_record['flow_shift'])[0]
        current_metrics_recorder.update_generation_stage('inference')
        def record_fun_step(current_step_index, current_denoised_tensor, current_sample_tensor, current_stage_total):
            current_metrics_recorder.record_generation_step(current_start_step + current_step_index + 1)
        current_latent_tensor = comfy.sample.sample(current_diffusion_model, current_noise_tensor if current_start_step == 0 else torch.zeros_like(current_noise_tensor), current_step_total, current_request_record['guidance_scale'], 'euler', 'simple', positive_condition_data, negative_condition_data, current_latent_tensor, denoise=1.0, disable_noise=current_start_step != 0, start_step=current_start_step, last_step=current_end_step, force_full_denoise=current_end_step == current_step_total, callback=record_fun_step, seed=current_request_record['seed'])
        comfy.model_management.unload_all_models()
        del current_diffusion_model
        gc.collect()
        comfy.model_management.soft_empty_cache()
    current_metrics_recorder.update_generation_stage('saving')
    # 시간 경계 잔상을 피하고 재추론 없는 디코딩 검증을 위해 잠재값을 보존한다.
    from safetensors.torch import save_file
    current_latent_path = current_attempt_root / 'denoised-latents.safetensors'
    save_file({'samples': current_latent_tensor.detach().cpu().contiguous()}, str(current_latent_path))
    current_temporal_tile_count = max(2, current_latent_tensor.shape[2])
    from generators.common.wan_video_memory import WAN_VIDEO_DECODE_TEMPORAL_OVERLAP, WAN_VIDEO_DECODE_TILE_LATENTS, WAN_VIDEO_DECODE_OVERLAP_LATENTS
    write_record_atomically(current_attempt_root / 'decode-policy.json', {
        'temporal_tile': current_temporal_tile_count,
        'temporal_overlap': WAN_VIDEO_DECODE_TEMPORAL_OVERLAP,
        'spatial_tile': WAN_VIDEO_DECODE_TILE_LATENTS,
        'spatial_overlap': WAN_VIDEO_DECODE_OVERLAP_LATENTS,
        'latent_sha256': hashlib.sha256(current_latent_path.read_bytes()).hexdigest(),
        'policy': '시간축 전체 단일 타일 · 공간 타일 유지',
    })
    current_decoded_frames = current_vae_model.decode(current_latent_tensor, current_temporal_tile_count=current_temporal_tile_count)
    if current_decoded_frames.shape[0] != current_request_record['frames']:
        raise ValueError('출력 프레임 수 불일치')
    current_frame_arrays = (current_decoded_frames.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    current_output_hashes = save_video_outputs(current_attempt_root, current_frame_arrays, 16)
    if current_request_record.get('driving_video_file'):
        import zipfile
        with zipfile.ZipFile(current_attempt_root/'frames.zip', 'a') as current_output_archive:
            for current_artifact_name in ('pose.mp4', 'pose-preprocess.json'):
                current_output_archive.write(current_attempt_root/current_artifact_name, current_artifact_name)
    comfy.model_management.unload_all_models()
    del current_vae_model
    gc.collect()
    return {'attempt': current_attempt_root.name, 'frames': len(current_frame_arrays), 'fps': 16, 'output_sha256': current_output_hashes, 'model_id': 'QuantStack/Wan2.2-Fun-A14B-Control-GGUF', 'model_revision': FUN_MODEL_REVISION, 'prompt_words': len(current_request_record['prompt'].split()), 'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(), 'quality_status': '사용자 검수 대기'}


if __name__ == '__main__':
    run_reference_video_worker(FUN_JOB_STORAGE, Path(__file__), validate_fun_assets, execute_fun_inference)
