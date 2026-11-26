"""Wan I2V 실험 작업자. 공용 GPU 작업 서비스에서만 실행한다."""
import gc
import hashlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
TEMP_ROOT = ROOT / '.tmp' / 'wan22-i2v-runtime'
if __name__ == '__main__':
    # torch 및 GPU 초기화 전에 적용한다.
    os.environ['PYTORCH_ALLOC_CONF'] = 'expandable_segments:False'
    os.environ.pop('PYTORCH_CUDA_ALLOC_CONF', None)
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(TEMP_ROOT)
sys.path.insert(0, str(ROOT))

from generators.wan_i2v.assets import DIRECTORY, FILES
from generators.wan_i2v.contracts import JOB_STORAGE, RUNTIME, inspect_runtime
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from workflow.common.generation_records import write_record_atomically


def load_i2v_model(torch, comfy_sd, comfy_utils, supported_models, model_path):
    """체크포인트를 GPU에 직접 적재하고 CPU 추론·오프로드를 거절한다."""
    device = torch.device('cuda:0')
    free, _ = torch.cuda.mem_get_info(device)
    required = 2 * model_path.stat().st_size + 4 * 1024**3
    if free < required:
        raise RuntimeError(f'I2V 모델 적재 GPU 여유 메모리 부족: {free} < {required}')
    config = supported_models.WAN21_I2V
    original = config.get_model
    def build_meta(instance, state_dict, prefix='', device=None):
        return original(instance, state_dict, prefix, device=torch.device('meta')).to_empty(device=torch.device('cuda:0'))
    try:
        config.get_model = build_meta
        weights = comfy_utils.load_torch_file(str(model_path), device=device)
        model = comfy_sd.load_diffusion_model_state_dict(weights, model_options={'dtype': torch.bfloat16})
        if model is None or model.load_device.type != 'cuda' or model.offload_device.type != 'cuda':
            raise RuntimeError('I2V GPU 전용 모델 로드 실패')
        return model
    finally:
        config.get_model = original


def apply_adapter(model, path, strength, comfy_sd, comfy_utils):
    """실제 적용된 키가 없는 LoRA를 성공으로 취급하지 않는다."""
    old_patches = {key: len(value) for key, value in model.patches.items()}
    adapter = comfy_utils.load_torch_file(str(path), safe_load=True)
    expected = sum(key.endswith(('.lora_down.weight', '.lora_A.weight')) for key in adapter)
    if not expected:
        raise ValueError(f'LoRA 가중치를 확인할 수 없습니다: {path.name}')
    result, _ = comfy_sd.load_lora_for_models(model, None, adapter, strength, 0)
    added = sum(len(value) - old_patches.get(key, 0) for key, value in result.patches.items())
    if added != expected:
        raise ValueError(f'LoRA 적용 수 불일치: {path.name}, 예상 {expected}, 적용 {added}')
    return result, added


def execute_i2v(job, attempt, request, metrics):
    sys.path.insert(0, str(RUNTIME))
    import torch
    import numpy as np
    from PIL import Image
    import comfy.cli_args
    comfy.cli_args.args.lowvram = False
    comfy.cli_args.args.highvram = True
    comfy.cli_args.args.gpu_only = True
    comfy.cli_args.args.cpu_vae = False
    comfy.cli_args.args.fp32_vae = True
    comfy.cli_args.args.bf16_unet = True
    import nodes, folder_paths, comfy.model_management, comfy.sample, comfy.sd, comfy.utils, comfy.supported_models
    from comfy_extras.nodes_wan import WanImageToVideo
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    from generators.wan_fun.vae_diagnostic import disable_vae_tiled_fallback
    from generators.wan_fun.numerical_diagnostics import guard_fun_vae_method, record_fun_numerical_step, record_fun_tensor_failure
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('ROCm GPU가 필요합니다.')
    comfy.model_management.text_encoder_device = lambda: torch.device('cuda:0')
    from workflow.common.model_storage_layout import resolve_wan_shared_model_directory
    folder_paths.add_model_folder_path('text_encoders', str(resolve_wan_shared_model_directory(ROOT/'.model', 'umt5')))
    folder_paths.add_model_folder_path('vae', str(resolve_wan_shared_model_directory(ROOT/'.model', 'vae')))
    metrics.update_generation_stage('load')
    clip = nodes.CLIPLoader().load_clip('umt5_xxl_fp16.safetensors', type='wan')[0]
    if clip.patcher.load_device.type != 'cuda' or clip.patcher.offload_device.type != 'cuda':
        raise RuntimeError('텍스트 인코더는 GPU 전용이어야 합니다.')
    positive = nodes.CLIPTextEncode().encode(clip, request['prompt'])[0]
    negative = nodes.CLIPTextEncode().encode(clip, request['negative_prompt'])[0]
    for label, condition in [('positive', positive), ('negative', negative)]:
        if not torch.isfinite(condition[0][0]).all().item():
            record_fun_tensor_failure(torch, attempt, 'text-conditioning', {label: condition[0][0]})
            raise ValueError(f'{label} 텍스트 조건에 비유한 값이 있습니다.')
    comfy.model_management.unload_all_models(); del clip; gc.collect(); comfy.model_management.soft_empty_cache()
    def load_vae():
        vae = nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0]
        if vae.device.type != 'cuda' or vae.patcher.offload_device.type != 'cuda' or vae.vae_dtype != torch.float32:
            raise RuntimeError('VAE는 FP32 GPU 전용이어야 합니다.')
        disable_vae_tiled_fallback(vae)
        return vae
    vae = load_vae()
    reference = job / request['references'][0]
    with Image.open(reference) as image:
        pixels = torch.from_numpy(np.asarray(image.convert('RGB'), dtype=np.float32) / 255).unsqueeze(0)
    metrics.update_generation_stage('encoding')
    with guard_fun_vae_method(vae, attempt, torch, 'encode'):
        positive, negative, latent = WanImageToVideo.execute(positive, negative, vae, request['width'], request['height'], request['frames'], 1, start_image=pixels)
    for label, tensor in [('reference_latent', positive[0][1]['concat_latent_image']), ('latent', latent['samples'])]:
        if not torch.isfinite(tensor).all().item():
            record_fun_tensor_failure(torch, attempt, 'conditioning', {label: tensor})
            raise ValueError(f'{label}에 비유한 값이 있습니다.')
    write_record_atomically(attempt / 'runtime-environment.json', {'torch': str(torch.__version__), 'hip': torch.version.hip, 'gpu': torch.cuda.get_device_name(0), 'allocator': os.environ['PYTORCH_ALLOC_CONF'], 'tmpdir': os.environ['TMPDIR'], 'vae_dtype': str(vae.vae_dtype), 'vae_sdpa': '기본 경로; 실제 커널 및 정확도 미검증', 'model_dtype': 'bfloat16', 'model_checkpoint_dtype': 'float16'})
    comfy.model_management.unload_all_models(); del vae; gc.collect(); comfy.model_management.soft_empty_cache()
    sample = latent['samples']
    noise = comfy.sample.prepare_noise(sample, request['seed'])
    split = request['steps'] // 2
    counts = {}
    for stage, start, end in [('high', 0, split), ('low', split, request['steps'])]:
        metrics.update_generation_stage('load')
        model = load_i2v_model(torch, comfy.sd, comfy.utils, comfy.supported_models, DIRECTORY / f'base/{stage}.safetensors')
        if 'lightning' in request['lora_mode']:
            model, counts[f'lightning_{stage}'] = apply_adapter(model, DIRECTORY / f'lightning/{stage}.safetensors', 1.0, comfy.sd, comfy.utils)
        if 'kungfu' in request['lora_mode']:
            model, counts[f'kungfu_{stage}'] = apply_adapter(model, DIRECTORY / f'kungfu/{stage}.safetensors', request['kungfu_strength'], comfy.sd, comfy.utils)
        model = ModelSamplingSD3().patch(model, request['flow_shift'])[0]
        metrics.update_generation_stage('inference')
        def callback(index, denoised, sample_value, total):
            torch.cuda.synchronize()
            record_fun_numerical_step(torch, attempt, stage, start + index + 1, denoised, sample_value)
            metrics.record_generation_step(start + index + 1)
        sample = comfy.sample.sample(model, noise if start == 0 else torch.zeros_like(noise), request['steps'], request['guidance_scale'], 'euler', 'simple', positive, negative, sample, denoise=1.0, disable_noise=start != 0, start_step=start, last_step=end, force_full_denoise=end == request['steps'], callback=callback, seed=request['seed'])
        if not torch.isfinite(sample).all().item():
            record_fun_tensor_failure(torch, attempt, 'sampler-final', {'latent': sample}, {'stage': stage})
            raise ValueError('샘플러 출력에 비유한 값이 있습니다.')
        comfy.model_management.unload_all_models(); del model; gc.collect(); comfy.model_management.soft_empty_cache()
    write_record_atomically(attempt / 'lora-application.json', counts)
    write_record_atomically(attempt / 'model-assets.json', {'files': [{'path': relative, 'repository': repo, 'revision': revision, 'source': remote, 'size': size, 'sha256': digest} for relative, repo, revision, remote, size, digest in FILES if relative.startswith('base/') or (relative.startswith('lightning/') and 'lightning' in request['lora_mode'])], 'sampler': 'euler', 'scheduler': 'simple', 'switch_step': split, 'lora_patch_counts': counts})
    from safetensors.torch import save_file
    save_file({'samples': sample.detach().cpu().contiguous()}, str(attempt / 'denoised-latents.safetensors'))
    metrics.update_generation_stage('decoding')
    vae = load_vae()
    with guard_fun_vae_method(vae, attempt, torch, 'decode'):
        frames = vae.decode(sample)
    if frames.ndim == 5:
        frames = frames.flatten(0, 1)
    if frames.shape[0] != request['frames'] or not torch.isfinite(frames).all().item():
        raise ValueError('출력 프레임 수가 다르거나 비유한 값이 있습니다.')
    arrays = (frames.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    hashes = save_video_outputs(attempt, arrays, 16)
    return {'attempt': attempt.name, 'frames': len(arrays), 'fps': 16, 'output_sha256': hashes, 'model_id': 'Comfy-Org/Wan-2.2 I2V A14B', 'prompt_sha256': hashlib.sha256(request['prompt'].encode()).hexdigest(), 'prompt_words': len(request['prompt'].split()), 'quality_status': '사용자 검수 대기'}


def validate_assets(request):
    if request.get('lora_mode') not in ('none', 'lightning'):
        raise ValueError('폐기된 LoRA 설정은 실행할 수 없습니다.')
    status = inspect_runtime(verify_hash=True)
    if not status['ready']:
        raise ValueError(status['message'])


if __name__ == '__main__':
    run_reference_video_worker(JOB_STORAGE, Path(__file__), validate_assets, execute_i2v, assets_validator_takes_request=True)
