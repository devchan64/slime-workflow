"""공식 참조 K/V의 값과 정밀도를 보존하고 보관 장치만 CPU로 변경한다."""
import torch


def enable_reference_cache_offload(current_cache_class):
    """프로세스 내 공식 캐시 클래스에 동기 복사 경계를 설치한다."""
    @torch.compiler.disable
    def store_reference_tensors(current_cache_object, current_key_tensor, current_value_tensor):
        if current_key_tensor.device.type != 'cuda' or current_value_tensor.device != current_key_tensor.device:
            raise ValueError('참조 K/V는 같은 CUDA 장치에서 생성되어야 합니다.')
        current_cache_object.reference_compute_device = current_key_tensor.device
        current_cache_object.key = current_key_tensor.detach().to('cpu', copy=True)
        current_cache_object.value = current_value_tensor.detach().to('cpu', copy=True)

    @torch.compiler.disable
    def load_reference_tensors(current_cache_object):
        if current_cache_object.key is None or current_cache_object.value is None:
            raise RuntimeError('참조 K/V 캐시가 비어 있습니다.')
        return (
            current_cache_object.key.to(current_cache_object.reference_compute_device),
            current_cache_object.value.to(current_cache_object.reference_compute_device),
        )

    current_cache_class.store = store_reference_tensors
    current_cache_class.get = load_reference_tensors
