"""VACE 인코딩과 복원 사이의 VAE 가중치만 CPU 메모리에 보관한다."""
from datetime import datetime

import torch
from diffusers import AutoencoderKLWan, WanVACEPipeline


def record_memory_transition(current_stage_name):
    print(f'{datetime.now().astimezone().isoformat()}/vace/memory {current_stage_name} '
          f'allocated_mib={torch.cuda.memory_allocated()/2**20:.1f} '
          f'reserved_mib={torch.cuda.memory_reserved()/2**20:.1f}', flush=True)


class StageOffloadedWanAutoencoder(AutoencoderKLWan):
    def decode(self, *current_decode_args, **current_decode_kwargs):
        """복원 연산 전에 가중치를 CUDA로 돌려놓는다."""
        self.to('cuda')
        record_memory_transition('vae_decode_cuda')
        return super().decode(*current_decode_args, **current_decode_kwargs)


class StageOffloadedVacePipeline(WanVACEPipeline):
    def prepare_video_latents(self, *current_encode_args, **current_encode_kwargs):
        """비디오·참조 전체 인코딩 완료 후, 첫 추론 스텝 전에 해제한다."""
        self.vae.to('cuda')
        current_condition_latents = super().prepare_video_latents(
            *current_encode_args, **current_encode_kwargs)
        self.vae.to('cpu')
        torch.cuda.empty_cache()
        record_memory_transition('vae_wait_cpu')
        return current_condition_latents


VACE_FEED_FORWARD_CHUNK = 1024


def enable_chunked_feed_forward(current_transformer_model):
    """토큰별 독립 FFN을 나누어 GELU 중간 텐서 피크를 줄인다. 추론 전용."""
    from types import MethodType
    from diffusers.models.attention import FeedForward
    current_installed_count = 0
    for current_feed_forward in current_transformer_model.modules():
        if not isinstance(current_feed_forward, FeedForward):
            continue
        if getattr(current_feed_forward, '_vace_chunked_forward', False):
            raise ValueError('FFN 분할이 이미 적용되었습니다.')
        current_original_forward = current_feed_forward.forward
        def execute_chunked_forward(current_module_value, current_hidden_states, *current_argument_values,
                current_original_forward=current_original_forward, **current_keyword_values):
            if torch.is_grad_enabled():
                raise RuntimeError('VACE FFN 분할은 gradient 없는 추론 전용입니다.')
            if current_hidden_states.ndim != 3:
                raise ValueError('VACE FFN 입력은 batch × tokens × channels여야 합니다.')
            current_output_buffer = None
            for current_token_start in range(0, current_hidden_states.shape[1], VACE_FEED_FORWARD_CHUNK):
                current_token_end = min(current_token_start + VACE_FEED_FORWARD_CHUNK, current_hidden_states.shape[1])
                current_chunk_output = current_original_forward(current_hidden_states[:, current_token_start:current_token_end], *current_argument_values, **current_keyword_values)
                if current_output_buffer is None:
                    current_output_buffer = current_chunk_output.new_empty((current_hidden_states.shape[0], current_hidden_states.shape[1], current_chunk_output.shape[-1]))
                current_output_buffer[:, current_token_start:current_token_end].copy_(current_chunk_output)
                del current_chunk_output
            if current_output_buffer is None:
                raise ValueError('VACE FFN 토큰이 비어 있습니다.')
            return current_output_buffer
        current_feed_forward.forward = MethodType(execute_chunked_forward, current_feed_forward)
        current_feed_forward._vace_chunked_forward = True
        current_installed_count += 1
    if not current_installed_count:
        raise ValueError('분할할 VACE FeedForward 모듈을 찾지 못했습니다.')
    return current_installed_count
