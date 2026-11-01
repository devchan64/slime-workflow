"""공식 RoPE의 위치·연산 정밀도를 보존하고 임시 텐서만 토큰 단위로 나눈다."""
import torch

ROTARY_TOKEN_CHUNK_SIZE = 1024


def apply_chunked_rotary(current_input_tensor, current_grid_sizes, current_frequency_tensor):
    current_output_tensor = torch.empty_like(current_input_tensor)
    current_head_count = current_input_tensor.shape[2]
    current_complex_width = current_input_tensor.shape[3] // 2
    current_frequency_parts = current_frequency_tensor.split([current_complex_width-2*(current_complex_width//3),current_complex_width//3,current_complex_width//3],dim=1)
    with torch.autocast(device_type=current_input_tensor.device.type, enabled=False):
        for current_batch_index, (current_time_count,current_height_count,current_width_count) in enumerate(current_grid_sizes.tolist()):
            current_token_count = current_time_count*current_height_count*current_width_count
            for current_chunk_start in range(0,current_token_count,ROTARY_TOKEN_CHUNK_SIZE):
                current_chunk_end = min(current_chunk_start+ROTARY_TOKEN_CHUNK_SIZE,current_token_count)
                current_token_indices = torch.arange(current_chunk_start,current_chunk_end,device=current_input_tensor.device)
                current_time_indices = current_token_indices//(current_height_count*current_width_count)
                current_height_indices = current_token_indices//current_width_count%current_height_count
                current_width_indices = current_token_indices%current_width_count
                current_chunk_frequencies = torch.cat([current_frequency_parts[0][current_time_indices],current_frequency_parts[1][current_height_indices],current_frequency_parts[2][current_width_indices]],dim=-1).unsqueeze(1)
                current_complex_tensor = torch.view_as_complex(current_input_tensor[current_batch_index,current_chunk_start:current_chunk_end].float().reshape(current_chunk_end-current_chunk_start,current_head_count,-1,2))
                current_output_tensor[current_batch_index,current_chunk_start:current_chunk_end] = torch.view_as_real(current_complex_tensor*current_chunk_frequencies).flatten(2).to(current_input_tensor.dtype)
            current_output_tensor[current_batch_index,current_token_count:] = current_input_tensor[current_batch_index,current_token_count:]
    return current_output_tensor


class ChunkedFeedForward(torch.nn.Module):
    """토큰 사이 상호작용이 없는 FFN만 묶음별로 계산한다."""
    def __init__(self, current_original_module):
        super().__init__()
        self.current_original_module = current_original_module

    def forward(self, current_input_tensor):
        current_output_tensor = None
        for current_chunk_start in range(0,current_input_tensor.shape[-2],ROTARY_TOKEN_CHUNK_SIZE):
            current_chunk_end = min(current_chunk_start+ROTARY_TOKEN_CHUNK_SIZE,current_input_tensor.shape[-2])
            current_chunk_output = self.current_original_module(current_input_tensor[...,current_chunk_start:current_chunk_end,:])
            if current_output_tensor is None:
                current_output_tensor = torch.empty(current_input_tensor.shape,device=current_chunk_output.device,dtype=current_chunk_output.dtype)
            current_output_tensor[...,current_chunk_start:current_chunk_end,:] = current_chunk_output
        return current_output_tensor


def install_chunked_feedforward(current_model_object):
    for current_module_name,current_module_object in list(current_model_object.named_modules()):
        if current_module_name.endswith('.ffn') and isinstance(current_module_object,torch.nn.Sequential):
            current_parent_name,current_child_name = current_module_name.rsplit('.',1)
            setattr(current_model_object.get_submodule(current_parent_name),current_child_name,ChunkedFeedForward(current_module_object))
