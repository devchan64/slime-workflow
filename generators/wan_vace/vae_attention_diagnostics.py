"""VACE VAE SDPA의 실제 입력을 옵트인 방식으로 비교한다."""
import math
import os
import time
from contextlib import contextmanager


def describe_vace_tensor(current_tensor_value):
    return {'shape': list(current_tensor_value.shape), 'stride': list(current_tensor_value.stride()),
            'dtype': str(current_tensor_value.dtype), 'device': str(current_tensor_value.device)}


def measure_vace_difference(current_first_output, current_reference_output, current_torch_module):
    current_first_double = current_first_output.to(dtype=current_torch_module.float64)
    current_reference_double = current_reference_output.to(dtype=current_torch_module.float64)
    current_difference_value = (current_first_double - current_reference_double).abs()
    current_reference_mean = current_reference_double.abs().mean().item()
    current_error_mean = current_difference_value.mean().item()
    current_maximum_error = current_difference_value.max().item()
    current_relative_error = current_error_mean / current_reference_mean if current_reference_mean else None
    if not all(math.isfinite(current_value) for current_value in (current_error_mean, current_maximum_error, current_reference_mean)) or (current_relative_error is not None and not math.isfinite(current_relative_error)):
        raise ValueError('VACE 어텐션 오차 통계를 유한한 값으로 계산할 수 없습니다.')
    return {'mean_absolute_error': current_error_mean, 'max_absolute_error': current_maximum_error,
            'reference_mean_absolute': current_reference_mean, 'relative_mean_error': current_relative_error, 'statistics_dtype': 'float64'}


@contextmanager
def capture_vace_vae_attention(current_phase_name, current_attempt_root, current_torch_module, current_diagnostic_state):
    """VAE 호출 동안 첫 SDPA만 비교하며 호출 종료나 예외 때 원래 함수를 복원한다."""
    if current_phase_name in current_diagnostic_state:
        yield
        return
    from safetensors.torch import save_file
    from tools.review.common.generation_records import write_record_atomically
    current_ops_module = current_torch_module.nn.functional
    current_original_function = current_ops_module.scaled_dot_product_attention

    def compare_vace_vae_attention(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values):
        if current_phase_name in current_diagnostic_state:
            return current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
        current_diagnostic_state.add(current_phase_name)
        current_start_time = time.monotonic()
        current_record_value = {'phase': current_phase_name, 'status': 'started', 'synchronizes_gpu': True,
            'comparison_changes_execution_timing': True, 'selected_kernel': '미확인',
            'pytorch': str(current_torch_module.__version__), 'hip': current_torch_module.version.hip,
            'allocator_configuration': os.environ.get('PYTORCH_ALLOC_CONF'),
            'gpu_architecture': getattr(current_torch_module.cuda.get_device_properties(current_query_tensor.device), 'gcnArchName', None) if current_query_tensor.is_cuda else None,
            'gpu': current_torch_module.cuda.get_device_name(current_query_tensor.device) if current_query_tensor.is_cuda else 'CPU synthetic test',
            'inputs': {current_name: describe_vace_tensor(current_tensor) for current_name, current_tensor in
                       (('query', current_query_tensor), ('key', current_key_tensor), ('value', current_value_tensor))}}
        current_option_names = ('attn_mask', 'dropout_p', 'is_causal', 'scale', 'enable_gqa')
        current_option_values = {'attn_mask': None, 'dropout_p': 0.0, 'is_causal': False, 'scale': None, 'enable_gqa': False}
        current_option_values.update(zip(current_option_names, current_positional_values))
        current_option_values.update(current_keyword_values)
        current_mask_value = current_option_values.get('attn_mask')
        current_record_value['options'] = {current_name: current_value for current_name, current_value in current_option_values.items() if current_name != 'attn_mask'}
        current_record_value['mask'] = describe_vace_tensor(current_mask_value) if isinstance(current_mask_value, current_torch_module.Tensor) else None
        current_record_path = current_attempt_root / f'vae-sdpa-{current_phase_name}.json'
        try:
            current_saved_tensors = {'query': current_query_tensor.detach().to(device='cpu', copy=True).contiguous(),
                'key': current_key_tensor.detach().to(device='cpu', copy=True).contiguous(), 'value': current_value_tensor.detach().to(device='cpu', copy=True).contiguous()}
            if isinstance(current_mask_value, current_torch_module.Tensor):
                current_saved_tensors['attn_mask'] = current_mask_value.detach().to(device='cpu', copy=True).contiguous()
            save_file(current_saved_tensors, str(current_attempt_root / f'vae-sdpa-{current_phase_name}.safetensors'))
            current_record_value['saved_tensors_are_contiguous'] = True
            current_inputs_finite = all(current_torch_module.isfinite(current_tensor).all().item() for current_tensor in (current_query_tensor, current_key_tensor, current_value_tensor))
            current_record_value['inputs_finite'] = current_inputs_finite
            if not current_inputs_finite or current_option_values.get('dropout_p', 0) != 0:
                current_record_value['status'] = 'comparison-skipped'
                current_record_value['reason'] = 'nonfinite input' if not current_inputs_finite else 'dropout changes random state'
                if not current_inputs_finite:
                    write_record_atomically(current_attempt_root / 'numerical-failure.json', {'stage': f'vae-sdpa-{current_phase_name}-input', 'inputs': current_record_value['inputs']})
                    raise ValueError('VACE VAE SDPA 입력에 NaN 또는 무한대가 있습니다.')
                return current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
            current_default_output = current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
            if not current_torch_module.isfinite(current_default_output).all().item():
                from generators.wan_vace.vae_numerical_guard import record_vace_tensor_failure
                current_record_value['status'] = 'nonfinite-output'
                current_record_value['outputs_finite'] = {'default': False}
                record_vace_tensor_failure(current_attempt_root, f'vae-sdpa-{current_phase_name}-output', current_torch_module, {'default': current_default_output})
                raise ValueError('VACE VAE SDPA 기본 출력에 NaN 또는 무한대가 있습니다.')
            current_repeated_output = current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
            with current_torch_module.nn.attention.sdpa_kernel(current_torch_module.nn.attention.SDPBackend.MATH):
                current_math_output = current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
            current_outputs_finite = {current_name: bool(current_torch_module.isfinite(current_tensor).all().item()) for current_name, current_tensor in
                (('default', current_default_output), ('repeat', current_repeated_output), ('math', current_math_output))}
            current_record_value['outputs_finite'] = current_outputs_finite
            if all(current_outputs_finite.values()):
                current_record_value['default_vs_math'] = measure_vace_difference(current_default_output, current_math_output, current_torch_module)
                current_record_value['default_repeat'] = measure_vace_difference(current_repeated_output, current_default_output, current_torch_module)
                current_record_value['status'] = 'compared'
            else:
                current_record_value['status'] = 'nonfinite-output'
                from generators.wan_vace.vae_numerical_guard import record_vace_tensor_failure
                record_vace_tensor_failure(current_attempt_root, f'vae-sdpa-{current_phase_name}-output', current_torch_module, {'default': current_default_output, 'repeat': current_repeated_output, 'math': current_math_output}, {'outputs_finite': current_outputs_finite})
                raise ValueError('VACE VAE SDPA 비교 출력에 NaN 또는 무한대가 있습니다.')
            return current_default_output
        except Exception as current_diagnostic_error:
            if current_record_value['status'] == 'started':
                current_record_value['status'] = 'error'
            current_record_value['error'] = str(current_diagnostic_error)
            raise
        finally:
            current_record_value['duration_seconds'] = time.monotonic() - current_start_time
            write_record_atomically(current_record_path, current_record_value)

    current_ops_module.scaled_dot_product_attention = compare_vace_vae_attention
    try:
        yield
    finally:
        current_ops_module.scaled_dot_product_attention = current_original_function
