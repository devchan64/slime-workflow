"""Fun Control 비양자화 고·저노이즈 모델을 순차 로드하는 GPU 작업자."""
from pathlib import Path
import sys
import os
import gc
import hashlib
from contextlib import nullcontext
def configure_fun_memory_allocator(current_environment_values):
    """gfx1151의 확장형 세그먼트 사용을 차단한다."""
    current_environment_values['PYTORCH_ALLOC_CONF'] = 'expandable_segments:False'
    current_environment_values.pop('PYTORCH_CUDA_ALLOC_CONF', None)


# 공용 작업자가 torch를 가져오기 전에 설정해야 한다.
if __name__ == '__main__':
    configure_fun_memory_allocator(os.environ)
FUN_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FUN_WORKSPACE_ROOT))
from generators.wan_fun.contracts import reject_retired_rgb_input, FUN_JOB_STORAGE, FUN_RUNTIME_DIRECTORY, FUN_MODEL_FILES, FUN_MODEL_IDENTIFIER, FUN_MODEL_REVISION, FUN_PYTHON_EXECUTABLE, validate_fun_assets
from generators.common.reference_video_worker import run_reference_video_worker, save_video_outputs
from workflow.common.generation_records import write_record_atomically


def execute_fun_inference(current_job_root, current_attempt_root, current_request_record, current_metrics_recorder):
    reject_retired_rgb_input(current_request_record)
    current_model_profile = current_request_record.get('model_profile', 'wan22-14b')
    if current_model_profile not in ('wan22-14b', 'wan21-1.3b'):
        raise ValueError('지원하지 않는 Fun Control 모델입니다.')
    current_is_wan13 = current_model_profile == 'wan21-1.3b'
    current_control_paths = [current_job_root/current_reference_name for current_reference_name in current_request_record['references']]
    if current_request_record.get('pose_video_file'):
        from generators.wan_fun.video_input import decode_processed_pose_video
        current_control_paths.extend(decode_processed_pose_video(current_job_root,current_attempt_root,current_request_record))
    if current_request_record.get('driving_video_file'):
        import subprocess
        import json
        import sysconfig
        current_metrics_recorder.update_generation_stage('pose-preprocess')
        current_site_directory = Path(sysconfig.get_paths()['purelib'])
        current_process_environment = os.environ.copy()
        current_library_paths = [str(current_site_directory/'onnxruntime/capi'), str(current_site_directory/'migraphx_libs')]
        if current_process_environment.get('LD_LIBRARY_PATH'):
            current_library_paths.append(current_process_environment['LD_LIBRARY_PATH'])
        current_process_environment['LD_LIBRARY_PATH'] = os.pathsep.join(current_library_paths)
        subprocess.run([str(FUN_PYTHON_EXECUTABLE), str(Path(__file__).with_name('pose_preprocess.py')), str(current_job_root), str(current_attempt_root)], env=current_process_environment, check=True)
        current_preprocess_record = json.loads((current_attempt_root/'pose-preprocess.json').read_text())
        current_control_paths.extend(Path(current_frame_path) for current_frame_path in current_preprocess_record['frames'])
    sys.path.insert(0, str(FUN_RUNTIME_DIRECTORY / 'ComfyUI'))
    import torch
    import numpy as np
    from PIL import Image
    import comfy.cli_args
    # 두 노이즈 모델은 순차 실행하며 사용 가능한 GPU 메모리에 우선 적재한다.
    comfy.cli_args.args.lowvram = False
    comfy.cli_args.args.highvram = True
    comfy.cli_args.args.gpu_only = True
    comfy.cli_args.args.cpu_vae = False
    comfy.cli_args.args.fp16_vae = False
    comfy.cli_args.args.bf16_vae = False
    comfy.cli_args.args.fp32_vae = True
    comfy.cli_args.args.bf16_unet = True
    import nodes, folder_paths, comfy.model_management, comfy.sample, comfy.sd, comfy.utils, comfy.supported_models
    import comfy.ops
    if os.environ.get('SLIME_WAN_CONTIGUOUS_ATTENTION', '1') == '1':
        from generators.wan_fun.attention_optimization import install_fun_attention_optimization
        install_fun_attention_optimization(torch, comfy.ops)
    if os.environ.get('SLIME_WAN_ATTENTION_PROFILE') == '1':
        from generators.wan_fun.attention_profile import install_fun_attention_profile
        install_fun_attention_profile(current_attempt_root, comfy.ops)
    from comfy_extras.nodes_wan import Wan22FunControlToVideo
    from comfy_extras.nodes_model_advanced import ModelSamplingSD3
    if current_is_wan13:
        from generators.wan_fun.wan13_model_assets import WAN13_MODEL_DIRECTORY, WAN13_REVISION_HASH, WAN13_REPOSITORY_NAME, WAN13_CLIP_REPOSITORY_NAME, WAN13_CLIP_REVISION_HASH, WAN13_MODEL_FILES
        folder_paths.add_model_folder_path('diffusion_models', str(WAN13_MODEL_DIRECTORY))
        folder_paths.add_model_folder_path('clip_vision', str(WAN13_MODEL_DIRECTORY / 'split_files/clip_vision'))
    def resolve_encoder_cuda():
        return torch.device('cuda:0')
    comfy.model_management.text_encoder_device = resolve_encoder_cuda
    if not torch.version.hip:
        raise RuntimeError('AMD ROCm PyTorch가 필요합니다.')
    for current_folder_name, current_folder_path in [('diffusion_models', '.model/wan22-fun-control/split_files/diffusion_models'), ('text_encoders', '.model/wan22-animate-components/split_files/text_encoders'), ('vae', '.model/wan22-animate-components/split_files/vae')]:
        folder_paths.add_model_folder_path(current_folder_name, str(FUN_WORKSPACE_ROOT / current_folder_path))
    current_metrics_recorder.update_generation_stage('load')
    current_text_encoder = nodes.CLIPLoader().load_clip('umt5_xxl_fp16.safetensors', type='wan')[0]
    if current_text_encoder.patcher.load_device.type != 'cuda' or current_text_encoder.patcher.offload_device.type != 'cuda':
        raise RuntimeError('텍스트 인코더는 GPU 전용이어야 합니다.')
    positive_condition_data = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['prompt'])[0]
    negative_condition_data = nodes.CLIPTextEncode().encode(current_text_encoder, current_request_record['negative_prompt'])[0]
    comfy.model_management.unload_all_models()
    del current_text_encoder
    gc.collect()
    comfy.model_management.soft_empty_cache()
    current_metrics_recorder.update_generation_stage('encoding')
    from generators.wan_fun.vae_diagnostic import disable_vae_tiled_fallback
    def load_fun_gpu_vae():
        current_loaded_vae = nodes.VAELoader().load_vae('wan_2.1_vae.safetensors')[0]
        if current_loaded_vae.device.type != 'cuda' or current_loaded_vae.patcher.offload_device.type != 'cuda' or current_loaded_vae.vae_dtype != torch.float32:
            raise RuntimeError('VAE는 FP32 GPU 전용이어야 합니다.')
        disable_vae_tiled_fallback(current_loaded_vae)
        return current_loaded_vae
    current_vae_model = load_fun_gpu_vae()
    from generators.wan_fun.numerical_diagnostics import describe_fun_vae_attention, guard_fun_vae_method, guard_fun_vae_attention
    current_gpu_properties = torch.cuda.get_device_properties(0)
    write_record_atomically(current_attempt_root / 'runtime-environment.json', {
        'pytorch_version': str(torch.__version__), 'hip_version': torch.version.hip,
        'gpu_name': torch.cuda.get_device_name(0),
        'gpu_architecture': getattr(current_gpu_properties, 'gcnArchName', None),
        'allocator_configuration_environment': os.environ.get('PYTORCH_ALLOC_CONF'),
        'allocator_backend': torch.cuda.memory.get_allocator_backend(),
        'model_revision': WAN13_REVISION_HASH if current_is_wan13 else FUN_MODEL_REVISION, 'requested_model_dtype': 'bfloat16',
        'reference_encoder': {'repository': WAN13_CLIP_REPOSITORY_NAME, 'revision': WAN13_CLIP_REVISION_HASH, 'sha256': WAN13_MODEL_FILES['split_files/clip_vision/clip_vision_h.safetensors'][1]} if current_is_wan13 else None,
        'text_encoder_checkpoint': 'umt5_xxl_fp16.safetensors', 'vae_dtype': str(current_vae_model.vae_dtype),
        'vae_attention_functions': describe_fun_vae_attention(current_vae_model),
        'selected_gpu_kernel': '미확인',
        'attention_profile_enabled': os.environ.get('SLIME_WAN_ATTENTION_PROFILE') == '1',
        'boundary_checks_synchronize_gpu': True,
        'vae_attention_diagnostic_enabled': os.environ.get('SLIME_FUN_VAE_ATTENTION_DIAGNOSTIC') == '1',
    })
    write_record_atomically(current_attempt_root / 'encode-policy.json', {
        'use_regular_vae': True, 'vae_dtype': 'float32', 'temporal_tile_frames': None,
        'spatial_tile_pixels': None, 'policy': '일반 VAE 고정 · OOM 타일 대체 차단',
    })
    current_image_tensors = []
    for current_reference_name in current_control_paths:
        with Image.open(current_reference_name) as current_image_file:
            current_image_tensors.append(torch.from_numpy(np.asarray(current_image_file.convert('RGB'), dtype=np.float32) / 255.0))
    if current_is_wan13:
        import node_helpers
        current_clip_model = nodes.CLIPVisionLoader().load_clip('clip_vision_h.safetensors')[0]
        if current_clip_model.patcher.load_device.type != 'cuda' or current_clip_model.patcher.offload_device.type != 'cuda':
            raise RuntimeError('참조 이미지 인코더는 GPU 전용이어야 합니다.')
        current_clip_output = nodes.CLIPVisionEncode().encode(current_clip_model, current_image_tensors[0].unsqueeze(0), 'center')[0]
        positive_condition_data = node_helpers.conditioning_set_values(positive_condition_data, {'clip_vision_output': current_clip_output})
        negative_condition_data = node_helpers.conditioning_set_values(negative_condition_data, {'clip_vision_output': current_clip_output})
        comfy.model_management.unload_all_models()
        del current_clip_model
        gc.collect()
        comfy.model_management.soft_empty_cache()
    current_encode_diagnostic = guard_fun_vae_attention(current_vae_model, current_attempt_root, torch, 'encode') if os.environ.get('SLIME_FUN_VAE_ATTENTION_DIAGNOSTIC') == '1' else nullcontext()
    with torch.inference_mode(), guard_fun_vae_method(current_vae_model, current_attempt_root, torch, 'encode'), current_encode_diagnostic:
        current_condition_output = Wan22FunControlToVideo.execute(positive_condition_data, negative_condition_data, current_vae_model, 832, 480, current_request_record['frames'], 1, ref_image=current_image_tensors[0].unsqueeze(0), control_video=torch.stack(current_image_tensors[1:]))
    positive_condition_data, negative_condition_data, current_latent_record = current_condition_output[:3]
    from generators.wan_fun.numerical_diagnostics import fingerprint_fun_tensor, record_fun_tensor_failure
    current_condition_metadata = positive_condition_data[0][1]
    current_initial_condition_fingerprints = {
        current_tensor_name: fingerprint_fun_tensor(torch, current_tensor_value)
        for current_tensor_name, current_tensor_value in (
            ('reference_latent', current_condition_metadata['reference_latents'][0]),
            ('control_latent', current_condition_metadata['concat_latent_image']),
        )
    }
    write_record_atomically(current_attempt_root / 'conditioning-before-release.json', current_initial_condition_fingerprints)
    current_invalid_initial = [current_tensor_name for current_tensor_name, current_fingerprint_record in current_initial_condition_fingerprints.items() if not current_fingerprint_record['finite']]
    if current_invalid_initial:
        record_fun_tensor_failure(torch, current_attempt_root, 'conditioning-before-release', {current_name: current_condition_metadata['reference_latents'][0] if current_name == 'reference_latent' else current_condition_metadata['concat_latent_image'] for current_name in current_invalid_initial})
        raise ValueError('VAE 인코딩 결과에 NaN 또는 무한대가 있습니다: ' + ', '.join(current_invalid_initial))
    comfy.model_management.unload_all_models()
    del current_vae_model
    gc.collect()
    comfy.model_management.soft_empty_cache()
    current_step_total = current_request_record['steps']
    current_switch_step = max(1, min(current_step_total - 1, round(current_step_total * current_request_record['switch_ratio'])))
    write_record_atomically(current_attempt_root / 'conditioning.json', {'input_mode': current_request_record.get('input_mode', 'controlled'), 'control_video_present': True, 'control_type': current_request_record['control_type'], 'reference_mode': 'reference_latents+clip_vision' if current_is_wan13 else 'reference_latents', 'face_video': False, 'switch_step': None if current_is_wan13 else current_switch_step, 'sampler': 'euler', 'scheduler': 'simple', 'model_revision': WAN13_REVISION_HASH if current_is_wan13 else FUN_MODEL_REVISION, 'tiled_vae': False})
    current_latent_tensor = current_latent_record['samples']
    current_noise_tensor = comfy.sample.prepare_noise(current_latent_tensor, current_request_record['seed'])
    current_condition_tensors = dict((
            ('positive_text', positive_condition_data[0][0]),
            ('negative_text', negative_condition_data[0][0]),
            ('reference_latent', current_condition_metadata['reference_latents'][0]),
            ('control_latent', current_condition_metadata['concat_latent_image']),
            ('initial_noise', current_noise_tensor),
        ))
    if current_is_wan13:
        current_condition_tensors['clip_vision'] = current_clip_output.penultimate_hidden_states
    current_condition_fingerprints = {current_tensor_name: fingerprint_fun_tensor(torch, current_tensor_value) for current_tensor_name, current_tensor_value in current_condition_tensors.items()}
    write_record_atomically(current_attempt_root / 'conditioning-fingerprints.json', current_condition_fingerprints)
    current_invalid_conditions = [current_tensor_name for current_tensor_name, current_fingerprint_record in current_condition_fingerprints.items() if not current_fingerprint_record['finite']]
    if current_invalid_conditions:
        record_fun_tensor_failure(torch, current_attempt_root, 'conditioning-before-sampling', {current_name: current_condition_tensors[current_name] for current_name in current_invalid_conditions})
        raise ValueError('추론 입력 조건에 NaN 또는 무한대가 있습니다: ' + ', '.join(current_invalid_conditions))
    current_sampling_stages = [('wan13', 0, current_step_total)] if current_is_wan13 else [('high', 0, current_switch_step), ('low', current_switch_step, current_step_total)]
    for current_model_stage, current_start_step, current_end_step in current_sampling_stages:
        current_metrics_recorder.update_generation_stage('load')
        current_model_relative = 'diffusion_pytorch_model.safetensors' if current_is_wan13 else Path(FUN_MODEL_FILES[current_model_stage][0]).name
        from generators.wan_fun.gpu_direct_loader import load_fun_gpu_unet
        current_diffusion_model = load_fun_gpu_unet(torch, folder_paths, comfy.sd, comfy.utils, comfy.supported_models, current_model_relative)
        if current_diffusion_model.load_device.type != 'cuda' or current_diffusion_model.offload_device.type != 'cuda':
            raise RuntimeError('확산 모델은 GPU 전용이어야 합니다.')
        current_diffusion_model = ModelSamplingSD3().patch(current_diffusion_model, current_request_record['flow_shift'])[0]
        current_metrics_recorder.update_generation_stage('inference')
        def record_fun_step(current_step_index, current_denoised_tensor, current_sample_tensor, current_stage_total):
            # ROCm 커널 제출만 끝난 상태를 완료된 스텝으로 기록하지 않는다.
            torch.cuda.synchronize()
            from generators.wan_fun.numerical_diagnostics import record_fun_numerical_step
            record_fun_numerical_step(torch, current_attempt_root, current_model_stage, current_start_step + current_step_index + 1, current_denoised_tensor, current_sample_tensor)
            current_metrics_recorder.record_generation_step(current_start_step + current_step_index + 1)
        current_latent_tensor = comfy.sample.sample(current_diffusion_model, current_noise_tensor if current_start_step == 0 else torch.zeros_like(current_noise_tensor), current_step_total, current_request_record['guidance_scale'], 'euler', 'simple', positive_condition_data, negative_condition_data, current_latent_tensor, denoise=1.0, disable_noise=current_start_step != 0, start_step=current_start_step, last_step=current_end_step, force_full_denoise=current_end_step == current_step_total, callback=record_fun_step, seed=current_request_record['seed'])
        if not torch.isfinite(current_latent_tensor).all().item():
            record_fun_tensor_failure(torch, current_attempt_root, 'sampler-final-latents', {'latents': current_latent_tensor}, {'model_stage': current_model_stage, 'step': current_end_step})
            raise ValueError(f'{current_model_stage} 추론의 잠재값에 NaN 또는 무한대가 있어 출력을 중단합니다.')
        comfy.model_management.unload_all_models()
        del current_diffusion_model
        gc.collect()
        comfy.model_management.soft_empty_cache()
    current_metrics_recorder.update_generation_stage('saving')
    # 시간 경계 잔상을 피하고 재추론 없는 디코딩 검증을 위해 잠재값을 보존한다.
    from safetensors.torch import save_file
    current_latent_path = current_attempt_root / 'denoised-latents.safetensors'
    save_file({'samples': current_latent_tensor.detach().cpu().contiguous()}, str(current_latent_path))
    write_record_atomically(current_attempt_root / 'decode-policy.json', {
        'use_regular_vae': True, 'vae_dtype': 'float32', 'temporal_tile': None, 'spatial_tile': None,
        'latent_sha256': hashlib.sha256(current_latent_path.read_bytes()).hexdigest(),
        'policy': '일반 VAE 고정 · OOM 타일 대체 차단',
    })
    current_vae_model = load_fun_gpu_vae()
    current_decode_diagnostic = guard_fun_vae_attention(current_vae_model, current_attempt_root, torch, 'decode') if os.environ.get('SLIME_FUN_VAE_ATTENTION_DIAGNOSTIC') == '1' else nullcontext()
    with torch.inference_mode(), guard_fun_vae_method(current_vae_model, current_attempt_root, torch, 'decode'), current_decode_diagnostic:
        current_decoded_frames = current_vae_model.decode(current_latent_tensor)
    if current_decoded_frames.ndim == 5:
        current_decoded_frames = current_decoded_frames.flatten(0, 1)
    if current_decoded_frames.shape[0] != current_request_record['frames']:
        raise ValueError('출력 프레임 수 불일치')
    if not torch.isfinite(current_decoded_frames).all().item():
        record_fun_tensor_failure(torch, current_attempt_root, 'decoded-frames', {'frames': current_decoded_frames})
        raise ValueError('디코딩된 영상에 NaN 또는 무한대가 있어 저장을 중단합니다.')
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
    return {'attempt': current_attempt_root.name, 'frames': len(current_frame_arrays), 'fps': 16, 'output_sha256': current_output_hashes, 'model_id': WAN13_REPOSITORY_NAME if current_is_wan13 else FUN_MODEL_IDENTIFIER, 'model_revision': WAN13_REVISION_HASH if current_is_wan13 else FUN_MODEL_REVISION, 'prompt_words': len(current_request_record['prompt'].split()), 'prompt_sha256': hashlib.sha256(current_request_record['prompt'].encode()).hexdigest(), 'quality_status': '사용자 검수 대기'}


def validate_current_fun_job_assets():
    import json
    current_job_directory = Path(sys.argv[sys.argv.index('--job-dir') + 1])
    current_job_request = json.loads((current_job_directory / 'request.json').read_text())
    if current_job_request.get('model_profile') == 'wan21-1.3b':
        from generators.wan_fun.wan13_model_assets import validate_wan13_generation_assets
        validate_wan13_generation_assets()
    else:
        validate_fun_assets()


if __name__ == '__main__':
    from generators.wan_fun.progress_otel import FunProgressRecorder
    run_reference_video_worker(FUN_JOB_STORAGE, Path(__file__), validate_current_fun_job_assets, execute_fun_inference, recorder_class=FunProgressRecorder)
