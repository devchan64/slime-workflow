import math
import torch
from diffusers.models.transformers.transformer_flux3 import _get_qkv_projections
from diffusers.models.embeddings import apply_rotary_emb


def build_global_geometry(image_position_ids, position_embedding_module):
    image_grid_side_length = 32
    if image_position_ids.shape != (image_grid_side_length * image_grid_side_length, 4):
        raise ValueError('Only a single 32×32 image grid is supported')
    position_step_y = image_position_ids[image_grid_side_length, 1] - image_position_ids[0, 1]
    position_step_x = image_position_ids[1, 2] - image_position_ids[0, 2]
    image_grid_indices = torch.arange(image_grid_side_length * image_grid_side_length, device=image_position_ids.device)
    image_row_indices = image_grid_indices // image_grid_side_length
    image_column_indices = image_grid_indices % image_grid_side_length
    # Ties at half a period keep the original position.
    row_pair_distances = image_row_indices[:, None] - image_row_indices[None, :]
    column_pair_distances = image_column_indices[:, None] - image_column_indices[None, :]
    row_period_shifts = torch.where(row_pair_distances > image_grid_side_length//2, 1, torch.where(row_pair_distances < -image_grid_side_length//2, -1, 0))
    column_period_shifts = torch.where(column_pair_distances > image_grid_side_length//2, 1, torch.where(column_pair_distances < -image_grid_side_length//2, -1, 0))
    geometry_entry_values = []
    for current_row_shift in (-1, 0, 1):
        for current_column_shift in (-1, 0, 1):
            if current_row_shift == current_column_shift == 0:
                continue
            selected_pair_mask = (row_period_shifts == current_row_shift) & (column_period_shifts == current_column_shift)
            shifted_position_ids = image_position_ids.clone()
            shifted_position_ids[:, 1] += current_row_shift * image_grid_side_length * position_step_y
            shifted_position_ids[:, 2] += current_column_shift * image_grid_side_length * position_step_x
            geometry_entry_values.append(((current_row_shift, current_column_shift), selected_pair_mask, position_embedding_module(shifted_position_ids)))
    return geometry_entry_values


class PeriodicImageAttention:
    def __init__(self, current_experiment_context, has_text_prefix):
        self.experiment_context = current_experiment_context
        self.has_text_prefix = has_text_prefix

    def __call__(self, attn, hidden_states, attention_mask=None, image_rotary_emb=None):
        if attention_mask is not None or image_rotary_emb is None:
            raise ValueError('Unexpected attention inputs')
        current_prefix_count = hidden_states.shape[1] - 1024 if self.has_text_prefix else 0
        if current_prefix_count < 0 or (not self.has_text_prefix and hidden_states.shape[1] != 1024):
            raise ValueError('Unexpected sequence length')
        current_cache_key = str(hidden_states.device)
        if current_cache_key not in self.experiment_context['cache']:
            self.experiment_context['cache'][current_cache_key] = build_global_geometry(self.experiment_context['ids'].to(hidden_states.device), self.experiment_context['position_embedder'])
        current_geometry_entries = self.experiment_context['cache'][current_cache_key]
        current_query_value, current_key_value, current_value_tensor = _get_qkv_projections(attn, hidden_states)
        current_query_value, current_key_value, current_value_tensor = [current_tensor_value.unflatten(-1, (attn.heads, -1)) for current_tensor_value in (current_query_value, current_key_value, current_value_tensor)]
        current_query_value = attn.norm_q(current_query_value.float())
        current_key_value = attn.norm_k(current_key_value.float())
        rotated_query_value = apply_rotary_emb(current_query_value, image_rotary_emb, sequence_dim=1).to(current_value_tensor.dtype).transpose(1,2).float()
        rotated_key_value = apply_rotary_emb(current_key_value, image_rotary_emb, sequence_dim=1).to(current_value_tensor.dtype).transpose(1,2).float()
        current_attention_scale = 1.0 / math.sqrt(rotated_query_value.shape[-1])
        current_attention_logits = torch.matmul(rotated_query_value, rotated_key_value.transpose(-2,-1)) * current_attention_scale
        current_image_query = rotated_query_value[:,:,current_prefix_count:,:]
        for _, current_selected_pairs, current_shifted_rotary in current_geometry_entries:
            current_shifted_key = apply_rotary_emb(current_key_value[:,current_prefix_count:], current_shifted_rotary, sequence_dim=1).to(current_value_tensor.dtype).transpose(1,2).float()
            current_shifted_logits = torch.matmul(current_image_query, current_shifted_key.transpose(-2,-1)) * current_attention_scale
            current_image_logits = current_attention_logits[:,:,current_prefix_count:,current_prefix_count:]
            current_image_logits.copy_(torch.where(current_selected_pairs[None,None], current_shifted_logits, current_image_logits))
        current_attention_probabilities = torch.softmax(current_attention_logits, dim=-1)
        current_output_value = torch.matmul(current_attention_probabilities, current_value_tensor.transpose(1,2).float()).to(current_value_tensor.dtype)
        current_output_value = current_output_value.transpose(1,2).flatten(2,3)
        return attn.to_out[1](attn.to_out[0](current_output_value))


GLOBAL_PERIODIC_SHIFT_SEQUENCE = (
    (8, 24), (8, 16), (16, 24), (8, 0), (16, 16), (8, 8), (24, 24), (0, 0),
    (0, 8), (24, 8), (0, 24), (24, 16), (16, 8), (24, 0), (0, 16), (16, 0),
)


def install_global_periodic_attention(current_pipeline_value, finite_tensor_validator):
    """검증된 512×512 무참조 실험의 어텐션과 16단계 이동을 적용한다."""
    import functools

    current_transformer_value = current_pipeline_value.transformer
    current_context_value = {'cache': {}, 'ids': None, 'position_embedder': current_transformer_value.pos_embed}
    current_image_blocks = current_transformer_value.mode_blocks['image']
    current_joint_blocks = current_transformer_value.single_transformer_blocks
    if not current_image_blocks or not current_joint_blocks:
        raise ValueError('전역 주기 어텐션을 적용할 FLUX 블록이 없습니다.')
    for current_block_value in current_image_blocks:
        current_block_value.attn.set_processor(PeriodicImageAttention(current_context_value, False))
    for current_block_value in current_joint_blocks:
        current_block_value.attn.set_processor(PeriodicImageAttention(current_context_value, True))
    current_forward_value = current_transformer_value.forward
    current_call_counter = [0]

    @functools.wraps(current_forward_value)
    def execute_periodic_transformer(*current_arguments_value, **current_keywords_value):
        if current_arguments_value or current_keywords_value['hidden_states'].shape[1] != 1024:
            raise ValueError('전역 주기 어텐션은 512×512 잠재 격자만 지원합니다.')
        if current_keywords_value.get('image_cond_hidden_states') is not None:
            raise ValueError('전역 주기 어텐션은 참조 이미지를 지원하지 않습니다.')
        current_context_value['ids'] = current_keywords_value['img_ids']
        current_latent_value = current_keywords_value['hidden_states']
        current_batch_size, current_token_count, current_channel_count = current_latent_value.shape
        current_shift_value = GLOBAL_PERIODIC_SHIFT_SEQUENCE[current_call_counter[0] % len(GLOBAL_PERIODIC_SHIFT_SEQUENCE)]
        current_keywords_value['hidden_states'] = torch.roll(
            current_latent_value.reshape(current_batch_size, 32, 32, current_channel_count),
            shifts=current_shift_value, dims=(1, 2),
        ).reshape(current_batch_size, current_token_count, current_channel_count)
        current_result_value = current_forward_value(**current_keywords_value)
        if not isinstance(current_result_value, tuple) or len(current_result_value) != 1:
            raise ValueError('예상하지 못한 전역 주기 모델 출력입니다.')
        current_prediction_value = current_result_value[0]
        finite_tensor_validator(current_prediction_value, torch, '전역 주기 모델 예측')
        if current_prediction_value.shape != current_latent_value.shape:
            raise ValueError('전역 주기 모델 예측 격자가 다릅니다.')
        current_prediction_value = torch.roll(
            current_prediction_value.reshape(current_batch_size, 32, 32, current_channel_count),
            shifts=(-current_shift_value[0], -current_shift_value[1]), dims=(1, 2),
        ).reshape(current_batch_size, current_token_count, current_channel_count)
        current_call_counter[0] += 1
        return (current_prediction_value,)

    current_transformer_value.forward = execute_periodic_transformer
    return current_call_counter, len(current_image_blocks), len(current_joint_blocks)
