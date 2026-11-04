"""명시적으로 요청한 21→41프레임 초기 노이즈 통제 실험."""
import hashlib


def build_prefix_noise_latents(current_pipeline_object, current_request_record, current_attempt_root):
    import torch
    from diffusers.utils.torch_utils import randn_tensor
    from safetensors.torch import save_file
    from tools.review.common.generation_records import write_record_atomically
    if current_request_record['noise_prefix_frames'] != 21 or current_request_record['frames'] != 41 or current_request_record['mode'] != 'pose':
        raise ValueError('21→41 pose 노이즈 통제 실험 요청이 아닙니다.')
    current_vae_config = current_pipeline_object.vae.config
    current_latent_channels = current_vae_config.latent_channels
    current_noise_dtype = current_pipeline_object.text_encoder.dtype
    current_noise_device = torch.device('cuda')
    current_latent_height = current_request_record['height'] // current_pipeline_object.vae.spatial_compression_ratio
    current_latent_width = current_request_record['width'] // current_pipeline_object.vae.spatial_compression_ratio
    current_reference_count = len(current_request_record['references'])
    current_prefix_length = (21 - 1) // current_pipeline_object.vae.temporal_compression_ratio + 1 + current_reference_count
    current_output_length = (41 - 1) // current_pipeline_object.vae.temporal_compression_ratio + 1 + current_reference_count
    current_noise_values = []
    for current_temporal_length in (current_prefix_length, current_output_length):
        current_noise_generator = torch.Generator(device=current_noise_device).manual_seed(current_request_record['seed'])
        current_noise_values.append(randn_tensor((1, current_latent_channels, current_temporal_length, current_latent_height, current_latent_width), generator=current_noise_generator, device=current_noise_device, dtype=current_noise_dtype))
    current_prefix_noise, current_output_noise = current_noise_values
    current_original_tail = current_output_noise[:, :, current_prefix_length:].clone()
    current_output_noise[:, :, :current_prefix_length] = current_prefix_noise
    assert torch.equal(current_output_noise[:, :, :current_prefix_length], current_prefix_noise)
    assert torch.equal(current_output_noise[:, :, current_prefix_length:], current_original_tail)
    current_noise_path = current_attempt_root / 'initial-noise.safetensors'
    save_file({'latents': current_output_noise.cpu().contiguous(), 'prefix': current_prefix_noise.cpu().contiguous()}, str(current_noise_path))
    write_record_atomically(current_attempt_root / 'noise-experiment.json', {
        'experiment': '21-frame-prefix-in-41-frame-noise', 'seed': current_request_record['seed'],
        'prefix_latent_length': current_prefix_length, 'shape': list(current_output_noise.shape),
        'dtype': str(current_noise_dtype), 'prefix_equal': True, 'original_tail_equal': True,
        'sha256': hashlib.sha256(current_noise_path.read_bytes()).hexdigest(),
        'policy': '공식 latents 입력으로 초기 노이즈만 교체; 참조 슬롯 포함; 추론 연산 유지',
    })
    return current_output_noise
