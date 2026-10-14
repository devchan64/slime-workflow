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
