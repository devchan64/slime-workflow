"""FLUX 구성요소를 CPU 오프로드 없이 ROCm GPU에 순차 적재한다."""


def load_flux_resident_components(current_pipeline_value, current_torch_module, current_model_directory):
    """호스트 동시 점유를 줄이되 모든 모델을 GPU에 유지하고 누락 시 실패한다."""
    if not current_torch_module.cuda.is_available() or not getattr(current_torch_module.version, 'hip', None):
        raise ValueError('FLUX는 사용 가능한 ROCm GPU가 필요합니다.')
    current_component_names = ('text_encoder', 'tokenizer', 'transformer', 'vae')
    current_component_paths = {current_component_name:str(current_model_directory) for current_component_name in current_component_names}
    for current_component_name in current_component_names:
        current_pipeline_value.load_components(names=[current_component_name], dtype={'vae':current_torch_module.float32,'default':current_torch_module.bfloat16}, pretrained_model_name_or_path=current_component_paths, local_files_only=True)
        current_component_value = getattr(current_pipeline_value, current_component_name, None)
        if current_component_value is None:
            raise ValueError('FLUX 구성요소 적재 실패: ' + current_component_name)
        if current_component_name != 'tokenizer':
            if not isinstance(current_component_value, current_torch_module.nn.Module):
                raise ValueError('FLUX 모델 구성요소 형식 오류: ' + current_component_name)
            current_component_value.to('cuda')
            for current_tensor_value in list(current_component_value.parameters()) + list(current_component_value.buffers()):
                if current_tensor_value.device.type != 'cuda':
                    raise ValueError('FLUX 구성요소의 GPU 적재를 확인할 수 없습니다: ' + current_component_name)
            print('FLUX GPU 상주 구성요소: ' + current_component_name, flush=True)
    return current_pipeline_value
