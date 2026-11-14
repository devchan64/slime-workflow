"""Wan BF16 가중치를 GPU로 직접 읽고 메타 모델에 적재한다."""
from pathlib import Path


def load_fun_gpu_unet(current_torch_module, current_folder_paths, current_sd_module, current_utils_module, current_models_module, current_model_name):
    current_model_path = Path(current_folder_paths.get_full_path_or_raise('diffusion_models', current_model_name))
    current_gpu_device = current_torch_module.device('cuda:0')
    current_free_bytes, _ = current_torch_module.cuda.mem_get_info(current_gpu_device)
    current_required_bytes = 2 * current_model_path.stat().st_size + 4 * 1024**3
    if current_free_bytes < current_required_bytes:
        raise RuntimeError(f'BF16 모델 GPU 직접 로드에 필요한 메모리가 부족합니다: 여유 {current_free_bytes // 1024**2} MiB, 필요 {current_required_bytes // 1024**2} MiB')

    current_config_class = current_models_module.WAN21_FunControl2V
    current_original_builder = current_config_class.get_model

    def build_meta_fun_model(current_config_record, current_state_dict, current_prefix='', device=None):
        current_meta_model = current_original_builder(current_config_record, current_state_dict, current_prefix, device=current_torch_module.device('meta'))
        return current_meta_model.to_empty(device=current_gpu_device)

    try:
        current_config_class.get_model = build_meta_fun_model
        current_model_weights = current_utils_module.load_torch_file(str(current_model_path), device=current_gpu_device)
        current_model_value = current_sd_module.load_diffusion_model_state_dict(current_model_weights, model_options={'dtype':current_torch_module.bfloat16})
        if current_model_value is None:
            raise ValueError(f'Wan Fun Control 모델 형식을 확인할 수 없습니다: {current_model_path.name}')
        return current_model_value
    finally:
        current_config_class.get_model = current_original_builder
