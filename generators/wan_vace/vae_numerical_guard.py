"""VACE VAE와 조건 구성 경계의 비유한 값을 감지한다."""
from contextlib import contextmanager
from functools import wraps


def check_vace_boundary_values(current_value_object, current_stage_name, current_attempt_root, current_torch_module):
    """중첩된 텐서를 검사하고 최초 실패의 메타데이터를 남긴다."""
    from tools.review.common.generation_records import write_record_atomically
    if isinstance(current_value_object, current_torch_module.Tensor):
        if not current_torch_module.isfinite(current_value_object).all().item():
            write_record_atomically(current_attempt_root / 'numerical-failure.json', {
                'stage': current_stage_name, 'shape': list(current_value_object.shape),
                'stride': list(current_value_object.stride()), 'dtype': str(current_value_object.dtype),
                'device': str(current_value_object.device),
            })
            raise ValueError(f'VACE {current_stage_name}에 NaN 또는 무한대가 있습니다.')
    elif isinstance(current_value_object, (tuple, list)):
        for current_item_value in current_value_object:
            check_vace_boundary_values(current_item_value, current_stage_name, current_attempt_root, current_torch_module)
    elif isinstance(current_value_object, dict):
        for current_item_value in current_value_object.values():
            check_vace_boundary_values(current_item_value, current_stage_name, current_attempt_root, current_torch_module)


@contextmanager
def guard_vace_vae_boundaries(current_pipeline_object, current_attempt_root, current_torch_module):
    """공식 메서드의 결과를 검사하고 종료 시 원래 메서드를 복원한다."""
    current_replaced_methods = []
    current_check_counts = {}

    def wrap_vace_boundary_method(current_owner_object, current_method_name, current_stage_name):
        current_original_method = getattr(current_owner_object, current_method_name)
        current_had_instance_method = current_method_name in vars(current_owner_object)
        current_instance_method = vars(current_owner_object).get(current_method_name)

        @wraps(current_original_method)
        def check_vace_method_result(*current_argument_values, **current_keyword_values):
            current_output_value = current_original_method(*current_argument_values, **current_keyword_values)
            check_vace_boundary_values(current_output_value, current_stage_name, current_attempt_root, current_torch_module)
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
