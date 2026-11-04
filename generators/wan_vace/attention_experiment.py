"""진단 전용: 앞 21프레임의 self-attention에서 뒤쪽 시간 토큰을 제외한다."""

EXPERIMENT_PREFIX_TOKEN_COUNT = 7 * 30 * 52
EXPERIMENT_TOTAL_TOKEN_COUNT = 12 * 30 * 52


def install_prefix_attention_isolation(current_transformer_module, current_pipeline_object=None, current_branch_scope="all"):
    if current_branch_scope not in ("all", "base", "vace"):
        raise ValueError("attention 진단 분기는 all/base/vace만 지원합니다.")
    if current_branch_scope != "all" and current_pipeline_object is None:
        raise ValueError("분기 제한에는 파이프라인이 필요합니다.")
    """공식 기본값이 아닌 원인 분리용 계산. 텍스트 cross-attention은 유지한다."""
    import torch
    current_original_attention = current_transformer_module.attention

    def calculate_isolated_prefix_attention(current_query_tensor, current_key_tensor, v, **current_attention_options):
        if current_query_tensor.shape[1] != EXPERIMENT_TOTAL_TOKEN_COUNT or current_key_tensor.shape[1] != EXPERIMENT_TOTAL_TOKEN_COUNT:
            return current_original_attention(current_query_tensor, current_key_tensor, v=v, **current_attention_options)
        if current_attention_options.get('attn_mask') is not None or current_attention_options.get('causal', False):
            raise ValueError('진단 attention은 기존 마스크·causal 입력과 함께 사용할 수 없습니다.')
        current_prefix_options = dict(current_attention_options)
        if current_prefix_options.get('k_lens') is not None:
            current_prefix_options['k_lens'] = torch.full_like(current_prefix_options['k_lens'], EXPERIMENT_PREFIX_TOKEN_COUNT)
        current_prefix_output = current_original_attention(
            current_query_tensor[:, :EXPERIMENT_PREFIX_TOKEN_COUNT], current_key_tensor[:, :EXPERIMENT_PREFIX_TOKEN_COUNT],
            v=v[:, :EXPERIMENT_PREFIX_TOKEN_COUNT], **current_prefix_options)
        current_tail_output = current_original_attention(
            current_query_tensor[:, EXPERIMENT_PREFIX_TOKEN_COUNT:], current_key_tensor, v=v, **current_attention_options)
        return torch.cat((current_prefix_output, current_tail_output), dim=1)

    current_transformer_module.attention = calculate_isolated_prefix_attention

    if current_branch_scope != 'all':
        current_transformer_module.attention = current_original_attention

        def activate_branch_isolation(current_hook_module, current_hook_inputs):
            current_transformer_module.attention = calculate_isolated_prefix_attention

        def deactivate_branch_isolation(current_hook_module, current_hook_inputs, current_hook_output):
            current_transformer_module.attention = current_original_attention

        for current_branch_model in (current_pipeline_object.transformer, current_pipeline_object.transformer_2):
            current_selected_blocks = current_branch_model.blocks if current_branch_scope == 'base' else current_branch_model.vace_blocks
            for current_branch_block in current_selected_blocks:
                current_branch_block.self_attn.register_forward_pre_hook(activate_branch_isolation)
                current_branch_block.self_attn.register_forward_hook(deactivate_branch_isolation, always_call=True)
