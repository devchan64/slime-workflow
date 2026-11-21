"""공식 VACE 어텐션과 전문가 출력의 비유한 값을 즉시 발견한다."""
import inspect
import json
from pathlib import Path


def install_vace_attention_guard(current_transformer_module, current_attempt_root, current_torch_module):
    current_original_attention = current_transformer_module.attention
    current_signature_value = inspect.signature(current_original_attention)
    current_guard_state = {'attention_calls': 0, 'step': 0}

    def check_vace_attention_values(*current_arguments, **current_keyword_values):
        current_bound_values = current_signature_value.bind(*current_arguments, **current_keyword_values)
        current_bound_values.apply_defaults()
        current_argument_values = current_bound_values.arguments
        current_inputs = {current_name: current_argument_values[current_name] for current_name in ('q', 'k', 'v')}
        current_input_finite = {current_name: bool(current_torch_module.isfinite(current_tensor).all().item()) for current_name, current_tensor in current_inputs.items()}
        current_guard_state['attention_calls'] += 1
        if not all(current_input_finite.values()):
            save_vace_attention_failure(current_attempt_root, current_torch_module, current_guard_state, current_argument_values, current_input_finite, None)
            raise ValueError('VACE 어텐션 입력에 NaN 또는 무한대가 있습니다.')
        current_output_tensor = current_original_attention(*current_arguments, **current_keyword_values)
        if not bool(current_torch_module.isfinite(current_output_tensor).all().item()):
            save_vace_attention_failure(current_attempt_root, current_torch_module, current_guard_state, current_argument_values, current_input_finite, current_output_tensor)
            raise ValueError('VACE 어텐션 출력에 NaN 또는 무한대가 있습니다.')
        return current_output_tensor

    current_transformer_module.attention = check_vace_attention_values
    return current_guard_state


def save_vace_attention_failure(current_attempt_root, current_torch_module, current_guard_state, current_argument_values, current_input_finite, current_output_tensor):
    from safetensors.torch import save_file
    current_attempt_root = Path(current_attempt_root)
    current_tensor_values = {current_name: current_argument_values[current_name].detach().to(device='cpu', copy=True).contiguous() for current_name in ('q', 'k', 'v')}
    for current_name in ('attn_mask', 'q_lens', 'k_lens'):
        current_optional_tensor = current_argument_values.get(current_name)
        if isinstance(current_optional_tensor, current_torch_module.Tensor):
            current_tensor_values[current_name] = current_optional_tensor.detach().to(device='cpu', copy=True).contiguous()
    if current_output_tensor is not None:
        current_tensor_values['output'] = current_output_tensor.detach().to(device='cpu', copy=True).contiguous()
    save_file(current_tensor_values, str(current_attempt_root / 'attention-failure-inputs.safetensors'))
    current_record_value = {'step': current_guard_state['step'], 'attention_call': current_guard_state['attention_calls'], 'input_finite': current_input_finite, 'output_finite': False if current_output_tensor is not None else None, 'input_shapes': {current_name: list(current_argument_values[current_name].shape) for current_name in ('q', 'k', 'v')}, 'input_dtypes': {current_name: str(current_argument_values[current_name].dtype) for current_name in ('q', 'k', 'v')}, 'input_strides': {current_name: list(current_argument_values[current_name].stride()) for current_name in ('q', 'k', 'v')}, 'saved_tensors_are_contiguous': True, 'options': {current_name: str(current_value) for current_name, current_value in current_argument_values.items() if current_name not in ('q', 'k', 'v', 'attn_mask', 'q_lens', 'k_lens')}, 'mask_present': current_argument_values.get('attn_mask') is not None, 'pytorch': current_torch_module.__version__, 'rocm': current_torch_module.version.hip, 'gpu': current_torch_module.cuda.get_device_name(0), 'math_comparison': '미실행'}
    current_comparison_supported = (
        current_output_tensor is not None and all(current_input_finite.values())
        and all(current_argument_values.get(current_option_name) is None for current_option_name in ('attn_mask', 'q_lens', 'k_lens', 'softmax_scale', 'q_scale'))
        and not current_argument_values.get('causal', False) and not current_argument_values.get('dropout_p', 0)
        and current_argument_values.get('window_size', (-1, -1)) == (-1, -1)
        and current_argument_values.get('attention_type') == 'SDPA'
    )
    if current_comparison_supported:
        try:
            current_bad_index = (~current_torch_module.isfinite(current_output_tensor)).nonzero()[0].tolist()
            current_batch_index, current_sequence_index, current_head_index = current_bad_index[:3]
            current_query_tensor = current_argument_values['q'][current_batch_index:current_batch_index+1, current_sequence_index:current_sequence_index+1, current_head_index:current_head_index+1, :].transpose(1, 2)
            current_key_tensor = current_argument_values['k'][current_batch_index:current_batch_index+1, :, current_head_index:current_head_index+1, :].transpose(1, 2)
            current_value_tensor = current_argument_values['v'][current_batch_index:current_batch_index+1, :, current_head_index:current_head_index+1, :].transpose(1, 2)
            with current_torch_module.nn.attention.sdpa_kernel(current_torch_module.nn.attention.SDPBackend.MATH):
                current_math_output = current_torch_module.nn.functional.scaled_dot_product_attention(current_query_tensor, current_key_tensor, current_value_tensor)
            current_record_value['math_comparison'] = {'query_index': current_bad_index, 'finite': bool(current_torch_module.isfinite(current_math_output).all().item()), 'scope': '동일 Q·K·V의 비유한 출력 위치 한 행'}
        except Exception as current_comparison_error:
            current_record_value['math_comparison'] = {'error': str(current_comparison_error)}
    (current_attempt_root / 'attention-failure.json').write_text(json.dumps(current_record_value, ensure_ascii=False, indent=2) + '\n')
