"""Qwen 2.1 생성 토큰에만 반대편 경계 K/V와 상대 위치를 추가하는 실험."""
TOROIDAL_LEGACY_CONFIGURATION = {'schema_version': 3, 'axes': 'xy', 'scope': 'target_attention', 'vae': 'standard', 'references': False}

TOROIDAL_ATTENTION_CONFIGURATION = {'schema_version': 4, 'axes': 'xy', 'scope': 'target_attention', 'vae': 'standard', 'references': False, 'boundary_radius': 2}


def build_toroidal_boundary(current_grid_height, current_grid_width):
    source_token_indices, height_offset_values, width_offset_values = [], [], []
    for current_column_index in range(current_grid_width):
        source_token_indices.extend([(current_grid_height - 1) * current_grid_width + current_column_index, current_column_index])
        height_offset_values.extend([-current_grid_height, current_grid_height])
        width_offset_values.extend([0, 0])
    for current_row_index in range(current_grid_height):
        source_token_indices.extend([current_row_index * current_grid_width + current_grid_width - 1, current_row_index * current_grid_width])
        height_offset_values.extend([0, 0])
        width_offset_values.extend([-current_grid_width, current_grid_width])
    return source_token_indices, height_offset_values, width_offset_values


class ToroidalTargetAttention:
    def __init__(self, current_position_embedder, current_grid_height, current_grid_width, boundary_radius_value=None, vertical_boundary_radius=None):
        self.grid_height_value = current_grid_height
        self.grid_width_value = current_grid_width
        self.boundary_radius_value = boundary_radius_value
        self.vertical_boundary_radius = vertical_boundary_radius
        self.position_embedder_value = current_position_embedder
        self.target_token_count = current_grid_height * current_grid_width
        self.boundary_mapping_values = build_toroidal_boundary(current_grid_height, current_grid_width)
        self.completed_call_count = 0

    def __call__(self, attn, hidden_states, attention_mask=None, rotary_emb=None, layer_cache=None,
                 kv_cache_mode=None, cache_write_slice=None, segments=None, key_valid=None):
        import torch
        from diffusers.models.transformers.transformer_qwenimage21 import (
            QwenImage21AttnProcessor, _qwenimage21_prepare_qkv, apply_rotary_emb_qwen, dispatch_attention_fn,
        )
        # 첫 스텝의 텍스트 출력·캐시는 기존 블록 인과성 구현으로 보존한다.
        original_prefix_output = None
        if segments is not None:
            original_prefix_output = QwenImage21AttnProcessor()(attn, hidden_states,
                attention_mask=attention_mask, rotary_emb=rotary_emb, layer_cache=layer_cache,
                kv_cache_mode=kv_cache_mode, cache_write_slice=cache_write_slice,
                segments=segments, key_valid=key_valid)
        query_tensor_value, key_tensor_value, value_tensor_value, query_sequence_length = _qwenimage21_prepare_qkv(
            attn, hidden_states, rotary_emb, layer_cache, kv_cache_mode, cache_write_slice)
        if query_sequence_length < self.target_token_count:
            raise ValueError('순환 Attention의 생성 토큰 수가 맞지 않습니다.')
        source_token_indices, height_offset_values, width_offset_values = self.boundary_mapping_values
        source_index_tensor = torch.tensor(source_token_indices, device=key_tensor_value.device) + key_tensor_value.shape[1] - self.target_token_count
        offset_tensor_values = [
            torch.zeros(len(source_token_indices), device=key_tensor_value.device),
            torch.tensor(height_offset_values, device=key_tensor_value.device),
            torch.tensor(width_offset_values, device=key_tensor_value.device),
        ]
        relative_rotary_tensor = torch.cat([
            self.position_embedder_value.rope_params(current_offset_tensor.cpu(), current_axis_dimension, self.position_embedder_value.theta).to(key_tensor_value.device)
            for current_offset_tensor, current_axis_dimension in zip(offset_tensor_values, self.position_embedder_value.axes_dim)
        ], dim=-1)
        extra_key_tensor = apply_rotary_emb_qwen(key_tensor_value[:, source_index_tensor], relative_rotary_tensor, use_real=False)
        extended_key_tensor = torch.cat([key_tensor_value, extra_key_tensor], dim=1)
        extended_value_tensor = torch.cat([value_tensor_value, value_tensor_value[:, source_index_tensor]], dim=1)
        target_attention_mask = attention_mask if segments is None else (None if key_valid is None else key_valid[:, None, None, :])
        if target_attention_mask is not None and target_attention_mask.dtype != torch.bool:
            raise ValueError('순환 Attention은 불리언 패딩 마스크만 지원합니다.')
        if self.boundary_radius_value is not None:
            query_index_tensor = torch.arange(self.target_token_count, device=key_tensor_value.device)
            local_source_tensor = torch.tensor(source_token_indices, device=key_tensor_value.device)
            synthetic_height_tensor = local_source_tensor // self.grid_width_value + offset_tensor_values[1]
            synthetic_width_tensor = local_source_tensor % self.grid_width_value + offset_tensor_values[2]
            boundary_distance_tensor = (
                (query_index_tensor[:, None] // self.grid_width_value - synthetic_height_tensor[None, :]).abs()
                + (query_index_tensor[:, None] % self.grid_width_value - synthetic_width_tensor[None, :]).abs()
            )
            # 좌우 연결 범위는 유지하고 상하 경계 복제 토큰에만 별도 반경을 적용한다.
            boundary_radius_tensor = torch.full_like(offset_tensor_values[1], self.boundary_radius_value)
            if self.vertical_boundary_radius is not None:
                boundary_radius_tensor[offset_tensor_values[1] != 0] = self.vertical_boundary_radius
            extra_allowed_tensor = (boundary_distance_tensor <= boundary_radius_tensor[None, :])[None, None]
            original_allowed_tensor = torch.ones(
                (query_tensor_value.shape[0], 1, self.target_token_count, key_tensor_value.shape[1]),
                dtype=torch.bool, device=key_tensor_value.device)
            if target_attention_mask is not None:
                original_allowed_tensor = original_allowed_tensor & target_attention_mask
                extra_allowed_tensor = extra_allowed_tensor & target_attention_mask[..., source_index_tensor]
            else:
                extra_allowed_tensor = extra_allowed_tensor.expand(query_tensor_value.shape[0], -1, -1, -1)
            target_attention_mask = torch.cat([original_allowed_tensor, extra_allowed_tensor], dim=-1)
        elif target_attention_mask is not None:
            target_attention_mask = torch.cat([target_attention_mask, target_attention_mask[..., source_index_tensor]], dim=-1)
        target_output_tensor = dispatch_attention_fn(query_tensor_value[:, -self.target_token_count:],
            extended_key_tensor, extended_value_tensor, attn_mask=target_attention_mask, dropout_p=0.0, backend=None)
        target_output_tensor = target_output_tensor.flatten(2, 3).type_as(query_tensor_value)
        target_output_tensor = attn.to_out[1](attn.to_out[0](target_output_tensor))
        self.completed_call_count += 1
        if original_prefix_output is not None:
            return torch.cat([original_prefix_output[:, :-self.target_token_count], target_output_tensor], dim=1)
        return target_output_tensor


def install_toroidal_attention(current_pipeline_model, current_request_record):
    if current_request_record.get('references'):
        raise ValueError('순환 Attention 첫 실험은 참조 없는 텍스트 생성만 지원합니다.')
    current_grid_height = current_request_record['height'] // current_pipeline_model.vae_scale_factor
    current_grid_width = current_request_record['width'] // current_pipeline_model.vae_scale_factor
    for current_transformer_block in current_pipeline_model.transformer.transformer_blocks:
        current_transformer_block.attn.set_processor(ToroidalTargetAttention(
            current_pipeline_model.transformer.pos_embed, current_grid_height, current_grid_width,
            current_request_record['circular_vae'].get('boundary_radius'),
            current_request_record['circular_vae'].get('vertical_boundary_radius')))
    return len(current_pipeline_model.transformer.transformer_blocks)
