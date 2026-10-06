"""Qwen 2.1 디코더의 공간 경계를 순환 패딩으로 연결한다."""
from types import MethodType

CIRCULAR_SOFT_SHADING_PROMPT = 'Illustration with soft shading.'
CIRCULAR_PATTERN_VIEW_PROMPT = 'Top view. Repeat pattern. Close-up'
CIRCULAR_DEFAULT_PROMPT = '잔디와 꽃을 그린다.'
CIRCULAR_LEGACY_CONFIGURATION = {'schema_version': 1, 'axes': 'xy', 'scope': 'decoder', 'tiled_decode': False}

CIRCULAR_HALO_CONFIGURATION = {'schema_version': 2, 'axes': 'xy', 'scope': 'latent_halo', 'halo_latents': 8, 'tiled_decode': False, 'baseline_decode': True}

from generators.image.qwen_21_toroidal import TOROIDAL_ATTENTION_CONFIGURATION
CIRCULAR_COMPARISON_CONFIGURATION = {**TOROIDAL_ATTENTION_CONFIGURATION, 'schema_version': 5, 'vae': 'circular_decoder_comparison', 'baseline_decode': True}
CIRCULAR_VERTICAL_CONFIGURATION = {**CIRCULAR_COMPARISON_CONFIGURATION, 'schema_version': 6, 'vertical_boundary_radius': 4}
CIRCULAR_SINGLE_STRIP_CONFIGURATION = {**CIRCULAR_COMPARISON_CONFIGURATION, 'schema_version': 7, 'boundary_radius': 8, 'vertical_boundary_radius': 8}
CIRCULAR_DOUBLE_STRIP_CONFIGURATION = {**CIRCULAR_SINGLE_STRIP_CONFIGURATION, 'schema_version': 8, 'boundary_strip_depth': 2}
CIRCULAR_CORNER_CONFIGURATION = {**CIRCULAR_SINGLE_STRIP_CONFIGURATION, 'schema_version': 9, 'boundary_strip_depth': 1, 'corner_reference_enabled': True}
CIRCULAR_VAE_CONFIGURATION = {**CIRCULAR_SINGLE_STRIP_CONFIGURATION, 'schema_version': 10, 'boundary_radius': 12, 'vertical_boundary_radius': 12, 'boundary_strip_depth': 1, 'corner_reference_enabled': False}

CIRCULAR_RADIUS_CHOICES = (8, 12, 16, 24)


def build_circular_configuration(selected_radius_value=12, baseline_decode_enabled=True, reference_input_enabled=False):
    if type(selected_radius_value) is not int or selected_radius_value not in CIRCULAR_RADIUS_CHOICES:
        raise ValueError('순환 참조 반경은 8·12·16토큰 중 선택하세요.')
    if type(baseline_decode_enabled) is not bool:
        raise ValueError('일반 VAE 비교 옵션은 ON/OFF 값이어야 합니다.')
    return {**CIRCULAR_VAE_CONFIGURATION, **({'schema_version': 11, 'references': True} if reference_input_enabled else {}), 'baseline_decode': baseline_decode_enabled, 'boundary_radius': selected_radius_value,
            'vertical_boundary_radius': selected_radius_value}


CIRCULAR_SELECTABLE_CONFIGURATIONS = tuple(build_circular_configuration(current_radius_value, baseline_decode_enabled, reference_input_enabled) for current_radius_value in CIRCULAR_RADIUS_CHOICES for baseline_decode_enabled in (False, True) for reference_input_enabled in (False, True))


def forward_circular_convolution(current_conv_module, current_input_tensor, cache_x=None):
    import torch.nn.functional as functional_operations
    if not getattr(current_conv_module, '_circular_decode_enabled', True):
        return current_conv_module._original_decode_forward(current_input_tensor, cache_x=cache_x)
    if cache_x is not None:
        raise ValueError('Qwen 2.1 순환 디코더는 시간 캐시를 지원하지 않습니다.')
    padded_input_tensor = functional_operations.pad(current_input_tensor.squeeze(2), current_conv_module._padding, mode='circular')
    return functional_operations.conv2d(padded_input_tensor, current_conv_module.weight, current_conv_module.bias,
        current_conv_module.stride, 0, current_conv_module.dilation, current_conv_module.groups).unsqueeze(2)


def apply_circular_decoder(current_vae_module):
    import torch.nn as neural_network_modules
    from diffusers.models.autoencoders.autoencoder_kl_qwenimage21 import AutoencoderKLQwenImage21, QwenImage21CausalConv3d
    if not isinstance(current_vae_module, AutoencoderKLQwenImage21):
        raise TypeError('순환 디코더는 AutoencoderKLQwenImage21 전용입니다.')
    patched_module_count = 0
    for current_layer_module in current_vae_module.decoder.modules():
        if isinstance(current_layer_module, QwenImage21CausalConv3d):
            current_layer_module.forward = MethodType(forward_circular_convolution, current_layer_module)
            patched_module_count += 1
        elif isinstance(current_layer_module, neural_network_modules.Conv2d):
            current_layer_module.padding_mode = 'circular'
            patched_module_count += 1
        elif isinstance(current_layer_module, neural_network_modules.ZeroPad2d):
            raise TypeError('디코더에 예상하지 않은 ZeroPad2d가 있습니다.')
    if not patched_module_count:
        raise ValueError('순환 패딩을 적용할 디코더 합성곱이 없습니다.')
    # 각 조각의 경계를 감는 분할 디코딩은 전체 이미지의 주기 경계와 다르다.
    current_vae_module.disable_tiling()
    return patched_module_count



def pad_circular_latents(current_latent_tensor, halo_latent_width):
    import torch.nn.functional as functional_operations
    if current_latent_tensor.ndim != 5 or halo_latent_width <= 0:
        raise ValueError('순환 잠재값은 5차원이며 여백은 양수여야 합니다.')
    if halo_latent_width > min(current_latent_tensor.shape[-2:]):
        raise ValueError('순환 여백이 잠재 이미지보다 큽니다.')
    flattened_latent_tensor = current_latent_tensor.flatten(0, 2).unsqueeze(1)
    extended_latent_tensor = functional_operations.pad(flattened_latent_tensor, (halo_latent_width,) * 4, mode='circular')
    return extended_latent_tensor.reshape(*current_latent_tensor.shape[:3], *extended_latent_tensor.shape[-2:])


def install_circular_halo_decode(current_pipeline_model, current_job_root):
    """같은 잠재값의 일반 복원과 순환 여백 복원을 보존한다."""
    import torch
    from diffusers.models.autoencoders.vae import DecoderOutput
    current_vae_module = current_pipeline_model.vae
    original_decode_method = current_vae_module.decode
    halo_latent_width = CIRCULAR_HALO_CONFIGURATION['halo_latents']
    current_vae_module.disable_tiling()

    def decode_with_circular_halo(current_latent_tensor, return_dict=True):
        torch.save(current_latent_tensor.detach().cpu(), current_job_root / 'decode-latents.pt')
        baseline_output_tensor = original_decode_method(current_latent_tensor, return_dict=False)[0]
        baseline_output_image = current_pipeline_model.image_processor.postprocess(baseline_output_tensor[:, :, 0], output_type='pil')[0]
        baseline_output_image.save(current_job_root / 'baseline.png')
        del baseline_output_tensor
        extended_latent_tensor = pad_circular_latents(current_latent_tensor, halo_latent_width)
        extended_output_tensor = original_decode_method(extended_latent_tensor, return_dict=False)[0]
        output_scale_ratio = current_vae_module.spatial_compression_ratio
        halo_pixel_width = halo_latent_width * output_scale_ratio
        expected_output_height = current_latent_tensor.shape[-2] * output_scale_ratio
        expected_output_width = current_latent_tensor.shape[-1] * output_scale_ratio
        cropped_output_tensor = extended_output_tensor[..., halo_pixel_width:halo_pixel_width + expected_output_height, halo_pixel_width:halo_pixel_width + expected_output_width].contiguous()
        if cropped_output_tensor.shape[-2:] != (expected_output_height, expected_output_width):
            raise ValueError('순환 여백 복원 출력 크기가 맞지 않습니다.')
        return DecoderOutput(sample=cropped_output_tensor) if return_dict else (cropped_output_tensor,)

    current_vae_module.decode = decode_with_circular_halo


def install_circular_comparison(current_pipeline_model, current_job_root):
    """오프로딩 훅 등록 전에 전환 가능한 디코더를 준비해 같은 잠재값을 비교한다."""
    import torch
    from diffusers.models.autoencoders.autoencoder_kl_qwenimage21 import QwenImage21CausalConv3d
    current_vae_module = current_pipeline_model.vae
    original_decode_method = current_vae_module.decode
    custom_conv_layers = []
    ordinary_conv_layers = []
    for current_layer_module in current_vae_module.decoder.modules():
        if isinstance(current_layer_module, QwenImage21CausalConv3d):
            current_layer_module._original_decode_forward = current_layer_module.forward
            custom_conv_layers.append(current_layer_module)
        elif isinstance(current_layer_module, torch.nn.Conv2d):
            ordinary_conv_layers.append((current_layer_module, current_layer_module.padding_mode))
    apply_circular_decoder(current_vae_module)

    def decode_with_comparison(current_latent_tensor, return_dict=True):
        torch.save(current_latent_tensor.detach().cpu(), current_job_root / 'decode-latents.pt')
        for current_layer_module in custom_conv_layers:
            current_layer_module._circular_decode_enabled = False
        for current_layer_module, original_padding_mode in ordinary_conv_layers:
            current_layer_module.padding_mode = original_padding_mode
        baseline_output_tensor = original_decode_method(current_latent_tensor, return_dict=False)[0]
        current_pipeline_model.image_processor.postprocess(baseline_output_tensor[:, :, 0], output_type='pil')[0].save(current_job_root / 'baseline.png')
        del baseline_output_tensor
        for current_layer_module in custom_conv_layers:
            current_layer_module._circular_decode_enabled = True
        for current_layer_module, original_padding_mode in ordinary_conv_layers:
            current_layer_module.padding_mode = 'circular'
        return original_decode_method(current_latent_tensor, return_dict=return_dict)

    current_vae_module.decode = decode_with_comparison
