"""생성기의 수치 경계에서 비유한 값을 실패로 처리한다."""
from functools import wraps


def require_finite_tensor(current_tensor_value, current_torch_module, current_stage_name):
    if not isinstance(current_tensor_value, current_torch_module.Tensor):
        raise RuntimeError(f'{current_stage_name}: 검사할 텐서가 없습니다.')
    if not bool(current_torch_module.isfinite(current_tensor_value).all().item()):
        raise RuntimeError(f'{current_stage_name}: NaN 또는 무한대가 발생했습니다.')


def check_denoise_latents(current_callback_values, current_torch_module, current_stage_name):
    require_finite_tensor(current_callback_values.get('latents'), current_torch_module, current_stage_name)
    return current_callback_values


def install_vae_decode_guard(current_vae_module, current_torch_module):
    current_original_decode = current_vae_module.decode

    @wraps(current_original_decode)
    def guarded_vae_decode(*current_decode_arguments, **current_decode_keywords):
        current_decode_result = current_original_decode(*current_decode_arguments, **current_decode_keywords)
        if isinstance(current_decode_result, (tuple, list)):
            current_output_tensor = current_decode_result[0] if current_decode_result else None
        else:
            current_output_tensor = getattr(current_decode_result, 'sample', None)
        require_finite_tensor(current_output_tensor, current_torch_module, 'VAE 디코딩 출력')
        return current_decode_result

    current_vae_module.decode = guarded_vae_decode
