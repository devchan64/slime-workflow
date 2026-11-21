"""VACE VAE와 조건 구성 경계의 비유한 값을 감지한다."""
from contextlib import contextmanager, nullcontext
from functools import wraps


def record_vace_tensor_failure(current_attempt_root, current_stage_name, current_torch_module, current_tensor_values, current_extra_record=None):
    """최초 감지 경계의 텐서와 원래 배치를 작업 시도에 보존한다."""
    from safetensors.torch import save_file
    from tools.management.common.generation_records import write_record_atomically
    current_tensor_records = {current_name: {'shape': list(current_tensor.shape), 'stride': list(current_tensor.stride()), 'dtype': str(current_tensor.dtype), 'device': str(current_tensor.device)} for current_name, current_tensor in current_tensor_values.items()}
    current_failure_record = {'stage': current_stage_name, 'tensors': current_tensor_records, 'tensor_storage': 'cpu-contiguous', **(current_extra_record or {})}
    write_record_atomically(current_attempt_root / 'numerical-failure.json', current_failure_record)
    if current_tensor_values:
        current_saved_tensors = {current_name: current_tensor.detach().to(device='cpu', copy=True).contiguous() for current_name, current_tensor in current_tensor_values.items()}
        save_file(current_saved_tensors, str(current_attempt_root / 'numerical-failure.safetensors'))


def check_vace_boundary_values(current_value_object, current_stage_name, current_attempt_root, current_torch_module, current_input_tensor=None, current_value_path='output'):
    """중첩된 텐서를 검사하고 최초 실패의 메타데이터를 남긴다."""
    from tools.management.common.generation_records import write_record_atomically
    if isinstance(current_value_object, current_torch_module.Tensor):
        if not current_torch_module.isfinite(current_value_object).all().item():
            current_tensor_values = {'output': current_value_object}
            if isinstance(current_input_tensor, current_torch_module.Tensor):
                current_tensor_values['input'] = current_input_tensor
            record_vace_tensor_failure(current_attempt_root, current_stage_name, current_torch_module, current_tensor_values, {
                'shape': list(current_value_object.shape), 'stride': list(current_value_object.stride()),
                'dtype': str(current_value_object.dtype), 'device': str(current_value_object.device), 'value_path': current_value_path,
            })
            raise ValueError(f'VACE {current_stage_name}에 NaN 또는 무한대가 있습니다.')
    elif isinstance(current_value_object, (tuple, list)):
        for current_item_index, current_item_value in enumerate(current_value_object):
            check_vace_boundary_values(current_item_value, current_stage_name, current_attempt_root, current_torch_module, current_input_tensor, f'{current_value_path}[{current_item_index}]')
    elif isinstance(current_value_object, dict):
        for current_item_name, current_item_value in current_value_object.items():
            check_vace_boundary_values(current_item_value, current_stage_name, current_attempt_root, current_torch_module, current_input_tensor, f'{current_value_path}.{current_item_name}')


@contextmanager
def guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, current_torch_module, current_diagnostic_enabled=False):
    """공식 메서드의 결과를 검사하고 종료 시 원래 메서드를 복원한다."""
    current_replaced_methods = []
    current_check_counts = {}
    current_diagnostic_state = set()

    def wrap_vace_boundary_method(current_owner_object, current_method_name, current_stage_name):
        current_original_method = getattr(current_owner_object, current_method_name)
        current_had_instance_method = current_method_name in vars(current_owner_object)
        current_instance_method = vars(current_owner_object).get(current_method_name)

        @wraps(current_original_method)
        def check_vace_method_result(*current_argument_values, **current_keyword_values):
            current_phase_name = {'vae-encode-output': 'encode', 'vae-decode-before-clamp': 'decode'}.get(current_stage_name)
            current_diagnostic_context = nullcontext()
            if current_diagnostic_enabled and current_phase_name:
                from generators.wan_vace.vae_attention_diagnostics import capture_vace_vae_attention
                current_diagnostic_context = capture_vace_vae_attention(current_phase_name, current_attempt_root, current_torch_module, current_diagnostic_state)
            with current_diagnostic_context:
                current_output_value = current_original_method(*current_argument_values, **current_keyword_values)
            current_input_tensor = current_argument_values[0] if current_argument_values else None
            check_vace_boundary_values(current_output_value, current_stage_name, current_attempt_root, current_torch_module, current_input_tensor)
            current_check_counts[current_stage_name] = current_check_counts.get(current_stage_name, 0) + 1
            return current_output_value

        setattr(current_owner_object, current_method_name, check_vace_method_result)
        current_replaced_methods.append((current_owner_object, current_method_name, current_had_instance_method, current_instance_method))

    try:
        current_vae_model = current_pipeline_object.vae.model
        wrap_vace_boundary_method(current_vae_model, 'encode', 'vae-encode-output')
        # 외부 VAE는 이 반환값을 clamp하므로 무한대가 가려지기 전에 검사한다.
        wrap_vace_boundary_method(current_vae_model, 'decode', 'vae-decode-before-clamp')
        wrap_vace_boundary_method(current_pipeline_object, 'vace_encode_frames', 'condition-encoded-frames')
        wrap_vace_boundary_method(current_pipeline_object, 'vace_encode_masks', 'condition-encoded-masks')
        wrap_vace_boundary_method(current_pipeline_object, 'vace_latent', 'condition-context')
        yield current_check_counts
    finally:
        for current_owner_object, current_method_name, current_had_instance_method, current_instance_method in reversed(current_replaced_methods):
            if current_had_instance_method:
                setattr(current_owner_object, current_method_name, current_instance_method)
            else:
                delattr(current_owner_object, current_method_name)
