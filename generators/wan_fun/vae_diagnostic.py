"""일반 VAE 진단에서 메모리 부족을 타일 처리로 숨기지 않는다."""


def disable_vae_tiled_fallback(current_vae_model):
    if current_vae_model.device.type != 'cuda':
        raise RuntimeError('일반 VAE 진단은 CUDA 연산이 필요합니다.')

    def reject_vae_tiled_fallback(*current_call_arguments, **current_call_options):
        raise RuntimeError('일반 VAE 처리 중 메모리 부족: 진단 조건 보존을 위해 자동 타일 대체를 차단했습니다.')

    current_vae_model.encode_tiled_3d = reject_vae_tiled_fallback
    current_vae_model.decode_tiled_3d = reject_vae_tiled_fallback
