"""Wan VAE의 명시적 공간·시간 타일링 정책."""
WAN_VIDEO_ENCODE_TILE_PIXELS = 256
WAN_VIDEO_ENCODE_OVERLAP_PIXELS = 64
WAN_VIDEO_ENCODE_TILE_FRAMES = 9
WAN_VIDEO_ENCODE_OVERLAP_FRAMES = 5
WAN_VIDEO_DECODE_TILE_LATENTS = 32
WAN_VIDEO_DECODE_OVERLAP_LATENTS = 8
WAN_VIDEO_DECODE_TEMPORAL_LATENTS = 3
WAN_VIDEO_DECODE_TEMPORAL_OVERLAP = 1


class TiledWanVideoVae:
    """공식 VAE 타일 API를 사용하고 CUDA 추론 모드를 보장한다."""

    def __init__(self, current_vae_model):
        if current_vae_model.device.type != 'cuda':
            raise ValueError('Wan VAE 연산은 CUDA에서만 실행합니다.')
        self.current_vae_model = current_vae_model

    def __getattr__(self, current_attribute_name):
        return getattr(self.current_vae_model, current_attribute_name)

    def encode(self, current_pixel_tensor):
        import torch
        with torch.inference_mode():
            current_latent_tensor = self.current_vae_model.encode_tiled(
                current_pixel_tensor,
                tile_x=WAN_VIDEO_ENCODE_TILE_PIXELS,
                tile_y=WAN_VIDEO_ENCODE_TILE_PIXELS,
                overlap=WAN_VIDEO_ENCODE_OVERLAP_PIXELS,
                tile_t=WAN_VIDEO_ENCODE_TILE_FRAMES,
                overlap_t=WAN_VIDEO_ENCODE_OVERLAP_FRAMES,
            )
        expected_temporal_count = (current_pixel_tensor.shape[0] - 1) // 4 + 1
        if current_latent_tensor.shape[2] != expected_temporal_count:
            raise ValueError('VAE 인코딩 후 시간축 길이가 입력과 맞지 않습니다.')
        return current_latent_tensor

    def decode(self, current_latent_tensor, current_temporal_tile_count=None):
        import torch
        if current_temporal_tile_count is None:
            current_temporal_tile_count = WAN_VIDEO_DECODE_TEMPORAL_LATENTS
        if type(current_temporal_tile_count) is not int or current_temporal_tile_count < 2:
            raise ValueError('시간 디코딩 타일은 2 이상의 정수여야 합니다.')
        with torch.inference_mode():
            current_pixel_tensor = self.current_vae_model.decode_tiled(
                current_latent_tensor,
                tile_x=WAN_VIDEO_DECODE_TILE_LATENTS,
                tile_y=WAN_VIDEO_DECODE_TILE_LATENTS,
                overlap=WAN_VIDEO_DECODE_OVERLAP_LATENTS,
                tile_t=current_temporal_tile_count,
                overlap_t=WAN_VIDEO_DECODE_TEMPORAL_OVERLAP,
            )
        if current_pixel_tensor.ndim == 5:
            current_pixel_tensor = current_pixel_tensor.flatten(0, 1)
        return current_pixel_tensor
