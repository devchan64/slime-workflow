"""추론 스텝에서 비유한 값이 처음 나타난 위치를 보존한다."""
import hashlib
import json


def record_fun_tensor_failure(current_torch_module, current_attempt_root, current_stage_name, current_tensor_values, current_additional_record=None):
    """실패 경계의 메타데이터와 원본 텐서를 작업 시도에 보존한다."""
    from safetensors.torch import save_file
    from tools.review.common.generation_records import write_record_atomically
    current_tensor_records = {current_name: {'shape': list(current_tensor.shape), 'stride': list(current_tensor.stride()),
        'dtype': str(current_tensor.dtype), 'device': str(current_tensor.device)} for current_name, current_tensor in current_tensor_values.items()}
    current_failure_record = {'stage': current_stage_name, 'tensors': current_tensor_records, 'tensor_storage': 'cpu-contiguous', **(current_additional_record or {})}
    write_record_atomically(current_attempt_root / 'numerical-failure.json', current_failure_record)
    current_saved_values = {current_name: current_tensor.detach().to(device='cpu', copy=True).contiguous() for current_name, current_tensor in current_tensor_values.items()}
    save_file(current_saved_values, str(current_attempt_root / 'numerical-failure.safetensors'))


def fingerprint_fun_tensor(current_torch_module, current_tensor_value):
    current_detached_tensor = current_tensor_value.detach().to(dtype=current_torch_module.float32, device='cpu').contiguous()
    return {'shape': list(current_tensor_value.shape), 'stride': list(current_tensor_value.stride()), 'dtype': str(current_tensor_value.dtype), 'device': str(current_tensor_value.device), 'hash_representation': 'cpu-float32-contiguous', 'sha256': hashlib.sha256(current_detached_tensor.numpy().tobytes()).hexdigest(), 'finite': bool(current_torch_module.isfinite(current_detached_tensor).all().item())}


def record_fun_numerical_step(current_torch_module, current_attempt_root, current_model_stage, current_step_number, current_denoised_tensor, current_sample_tensor):
    current_step_record = {'stage': current_model_stage, 'step': current_step_number, 'callback_sample': '스텝 갱신 전'}
    for current_tensor_name, current_tensor_value in (('denoised', current_denoised_tensor), ('sample', current_sample_tensor)):
        current_tensor_finite = current_torch_module.isfinite(current_tensor_value)
        current_nonfinite_count = int((~current_tensor_finite).sum().item())
        current_step_record[current_tensor_name] = {'shape': list(current_tensor_value.shape), 'stride': list(current_tensor_value.stride()), 'dtype': str(current_tensor_value.dtype), 'device': str(current_tensor_value.device), 'nonfinite': current_nonfinite_count, 'max_abs': None if current_nonfinite_count else float(current_tensor_value.abs().max().item())}
    with (current_attempt_root / 'numerical-steps.jsonl').open('a', encoding='utf-8') as current_output_file:
        current_output_file.write(json.dumps(current_step_record, ensure_ascii=False, allow_nan=False) + '\n')
    if any(current_step_record[current_tensor_name]['nonfinite'] for current_tensor_name in ('denoised', 'sample')):
        record_fun_tensor_failure(current_torch_module, current_attempt_root, 'sampler-callback', {'denoised': current_denoised_tensor, 'sample': current_sample_tensor}, {'model_stage': current_model_stage, 'step': current_step_number})
        raise ValueError(f'{current_model_stage} 추론 {current_step_number}단계에서 NaN 또는 무한대가 발견되었습니다. numerical-steps.jsonl을 확인하세요.')


def guard_fun_vae_method(current_vae_model, current_attempt_root, current_torch_module, current_method_name):
    """VAE의 정규화 이전 결과를 검사하는 컨텍스트를 반환한다."""
    from contextlib import contextmanager
    from functools import wraps
    from tools.review.common.generation_records import write_record_atomically

    @contextmanager
    def apply_fun_vae_guard():
        current_inner_model = current_vae_model.first_stage_model
        current_original_method = getattr(current_inner_model, current_method_name)
        current_had_instance_method = current_method_name in vars(current_inner_model)
        current_instance_method = vars(current_inner_model).get(current_method_name)

        @wraps(current_original_method)
        def check_fun_vae_result(*current_arguments, **current_options):
            current_result_tensor = current_original_method(*current_arguments, **current_options)
            if not isinstance(current_result_tensor, current_torch_module.Tensor):
                raise TypeError(f'Fun VAE {current_method_name} 출력이 텐서가 아닙니다.')
            if not current_torch_module.isfinite(current_result_tensor).all().item():
                current_tensor_values = {'output': current_result_tensor}
                if current_arguments and isinstance(current_arguments[0], current_torch_module.Tensor):
                    current_tensor_values['input'] = current_arguments[0]
                record_fun_tensor_failure(current_torch_module, current_attempt_root, f'vae-{current_method_name}-before-postprocessing', current_tensor_values)
                raise ValueError(f'Fun VAE {current_method_name} 출력에 NaN 또는 무한대가 있습니다.')
            return current_result_tensor

        setattr(current_inner_model, current_method_name, check_fun_vae_result)
        try:
            yield
        finally:
            if current_had_instance_method:
                setattr(current_inner_model, current_method_name, current_instance_method)
            else:
                delattr(current_inner_model, current_method_name)
    return apply_fun_vae_guard()


def describe_fun_vae_attention(current_vae_model):
    """VAE 모듈에 지정된 어텐션 함수를 기록하며 실제 GPU 커널로 추정하지 않는다."""
    current_attention_paths = set()
    for current_model_module in current_vae_model.first_stage_model.modules():
        current_attention_function = getattr(current_model_module, 'optimized_attention', None)
        if callable(current_attention_function):
            current_attention_paths.add(f'{getattr(current_attention_function, "__module__", "미확인")}.{getattr(current_attention_function, "__name__", "미확인")}')
    return sorted(current_attention_paths)


def guard_fun_vae_attention(current_vae_model, current_attempt_root, current_torch_module, current_phase_name):
    """진단 선택 시 VAE 첫 어텐션의 입력·출력과 SDPA 비교를 기록한다."""
    from contextlib import contextmanager
    from functools import wraps
    from tools.review.common.generation_records import write_record_atomically
    from safetensors.torch import save_file
    import time

    @contextmanager
    def apply_fun_attention_guard():
        current_restoration_values = []
        current_diagnostic_state = {'captured': False}
        try:
            for current_model_module in current_vae_model.first_stage_model.modules():
                current_original_function = getattr(current_model_module, 'optimized_attention', None)
                if not callable(current_original_function):
                    continue
                current_had_instance_value = 'optimized_attention' in vars(current_model_module)
                current_instance_value = vars(current_model_module).get('optimized_attention')

                def make_fun_attention_wrapper(current_attention_function):
                    @wraps(current_attention_function)
                    def inspect_fun_attention(current_query_tensor, current_key_tensor, current_value_tensor):
                        if current_diagnostic_state['captured']:
                            return current_attention_function(current_query_tensor, current_key_tensor, current_value_tensor)
                        current_diagnostic_state['captured'] = True
                        current_start_time = time.monotonic()
                        current_tensor_values = {'query': current_query_tensor, 'key': current_key_tensor, 'value': current_value_tensor}
                        current_record_value = {
                            'phase': current_phase_name,
                            'attention_function': f'{current_attention_function.__module__}.{current_attention_function.__name__}',
                            'selected_gpu_kernel': '미확인', 'mask': None, 'dropout_p': 0.0, 'is_causal': False,
                            'inputs': {current_name: {'shape': list(current_tensor.shape), 'stride': list(current_tensor.stride()), 'dtype': str(current_tensor.dtype), 'device': str(current_tensor.device)} for current_name, current_tensor in current_tensor_values.items()},
                            'saved_tensors_are_contiguous': True, 'synchronizes_gpu': True, 'changes_execution_timing': True,
                            'status': 'started',
                        }
                        try:
                            save_file({current_name: current_tensor.detach().to(device='cpu', copy=True).contiguous() for current_name, current_tensor in current_tensor_values.items()}, str(current_attempt_root / f'vae-attention-{current_phase_name}.safetensors'))
                            current_record_value['inputs_finite'] = all(current_torch_module.isfinite(current_tensor).all().item() for current_tensor in current_tensor_values.values())
                            if not current_record_value['inputs_finite']:
                                write_record_atomically(current_attempt_root / 'numerical-failure.json', {'stage': f'vae-attention-{current_phase_name}-input', 'inputs': current_record_value['inputs']})
                                raise ValueError('Fun VAE 어텐션 입력에 NaN 또는 무한대가 있습니다.')
                            current_default_output = current_attention_function(current_query_tensor, current_key_tensor, current_value_tensor)
                            if not current_torch_module.isfinite(current_default_output).all().item():
                                write_record_atomically(current_attempt_root / 'numerical-failure.json', {'stage': f'vae-attention-{current_phase_name}-output'})
                                raise ValueError('Fun VAE 어텐션 출력에 NaN 또는 무한대가 있습니다.')
                            if (current_attention_function.__module__, current_attention_function.__name__) != ('comfy.ldm.modules.diffusionmodules.model', 'pytorch_attention'):
                                current_record_value.update(status='comparison-skipped', reason='선택된 VAE 함수가 PyTorch SDPA 경로가 아님')
                                return current_default_output
                            current_repeat_output = current_attention_function(current_query_tensor, current_key_tensor, current_value_tensor)
                            current_batch_count, current_channel_count = current_query_tensor.shape[:2]
                            current_attention_inputs = [current_tensor.reshape(current_batch_count, 1, current_channel_count, -1).transpose(2, 3).contiguous() for current_tensor in current_tensor_values.values()]
                            current_record_value['sdpa_inputs'] = {current_name: {'shape': list(current_tensor.shape), 'stride': list(current_tensor.stride()), 'dtype': str(current_tensor.dtype), 'device': str(current_tensor.device)} for current_name, current_tensor in zip(('query', 'key', 'value'), current_attention_inputs)}
                            current_record_value['sdpa_scale'] = 'default: 1/sqrt(head_dim)'
                            with current_torch_module.nn.attention.sdpa_kernel(current_torch_module.nn.attention.SDPBackend.MATH):
                                current_math_output = current_torch_module.nn.functional.scaled_dot_product_attention(*current_attention_inputs, attn_mask=None, dropout_p=0.0, is_causal=False)
                            current_math_output = current_math_output.transpose(2, 3).reshape(current_query_tensor.shape)
                            if not all(current_torch_module.isfinite(current_tensor).all().item() for current_tensor in (current_repeat_output, current_math_output)):
                                write_record_atomically(current_attempt_root / 'numerical-failure.json', {'stage': f'vae-attention-{current_phase_name}-comparison'})
                                raise ValueError('Fun VAE 어텐션 비교 출력에 NaN 또는 무한대가 있습니다.')
                            for current_name, current_compared_tensor in (('default_repeat', current_repeat_output), ('default_vs_math', current_math_output)):
                                current_difference_tensor = (current_default_output.float() - current_compared_tensor.float()).abs()
                                current_reference_mean = current_compared_tensor.float().abs().mean().item()
                                current_error_mean = current_difference_tensor.mean().item()
                                current_record_value[current_name] = {'mean_absolute_error': current_error_mean, 'max_absolute_error': current_difference_tensor.max().item(), 'reference_mean_absolute': current_reference_mean, 'relative_mean_error': current_error_mean / current_reference_mean if current_reference_mean else None}
                            current_record_value['status'] = 'compared'
                            return current_default_output
                        except Exception as current_diagnostic_error:
                            if current_record_value['status'] == 'started':
                                current_record_value['status'] = 'error'
                            current_record_value['error'] = str(current_diagnostic_error)
                            raise
                        finally:
                            current_record_value['duration_seconds'] = time.monotonic() - current_start_time
                            write_record_atomically(current_attempt_root / f'vae-attention-{current_phase_name}.json', current_record_value)
                    return inspect_fun_attention

                setattr(current_model_module, 'optimized_attention', make_fun_attention_wrapper(current_original_function))
                current_restoration_values.append((current_model_module, current_had_instance_value, current_instance_value))
            yield
        finally:
            for current_model_module, current_had_instance_value, current_instance_value in reversed(current_restoration_values):
                if current_had_instance_value:
                    setattr(current_model_module, 'optimized_attention', current_instance_value)
                else:
                    delattr(current_model_module, 'optimized_attention')
    return apply_fun_attention_guard()
