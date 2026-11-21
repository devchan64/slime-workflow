"""공식 RoPE 계산 사이에서 완료된 Q 결과의 저장 위치만 변경한다."""


def install_query_result_offload(current_transformer_module):
    """Q→K 계산 순서·공식 RoPE·dtype을 유지하며 Q 결과를 CPU에 대기시킨다."""
    current_official_rope = current_transformer_module.rope_apply

    def apply_offloaded_query_key(current_query_tensor, current_key_tensor, current_grid_sizes, current_frequency_tensor):
        current_output_device = current_query_tensor.device
        current_query_result = current_official_rope(current_query_tensor, current_grid_sizes, current_frequency_tensor).to('cpu')
        current_key_result = current_official_rope(current_key_tensor, current_grid_sizes, current_frequency_tensor)
        return current_query_result.to(current_output_device), current_key_result

    current_transformer_module.rope_apply_qk = apply_offloaded_query_key
