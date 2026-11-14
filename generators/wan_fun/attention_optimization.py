"""gfx1151의 긴 Wan self-attention에 연속 메모리 배치를 사용한다."""


def install_fun_attention_optimization(current_torch_module, current_ops_module):
    if not current_torch_module.version.hip or not current_torch_module.cuda.is_available():
        return False
    current_device_record = current_torch_module.cuda.get_device_properties(0)
    if not current_device_record.gcnArchName.startswith('gfx1151'):
        return False
    current_original_attention = current_ops_module.scaled_dot_product_attention

    def execute_contiguous_attention(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values):
        current_tensors = (current_query_tensor, current_key_tensor, current_value_tensor)
        current_is_long_self_attention = (all(current_tensor.ndim == 4 and current_tensor.device.type == 'cuda' for current_tensor in current_tensors)
            and current_query_tensor.shape[-2] >= 8192
            and current_query_tensor.shape == current_key_tensor.shape == current_value_tensor.shape
            and current_query_tensor.dtype in (current_torch_module.float16, current_torch_module.bfloat16))
        if current_is_long_self_attention:
            current_copy_bytes = sum(current_tensor.numel() * current_tensor.element_size() for current_tensor in current_tensors if not current_tensor.is_contiguous())
            current_free_bytes, _ = current_torch_module.cuda.mem_get_info(current_query_tensor.device)
            if current_copy_bytes and current_free_bytes >= current_copy_bytes + 512 * 1024 * 1024:
                try:
                    current_tensors = tuple(current_tensor.contiguous() for current_tensor in current_tensors)
                except current_torch_module.cuda.OutOfMemoryError:
                    current_torch_module.cuda.empty_cache()
        return current_original_attention(*current_tensors, *current_positional_values, **current_keyword_values)

    current_ops_module.scaled_dot_product_attention = execute_contiguous_attention
    return True
