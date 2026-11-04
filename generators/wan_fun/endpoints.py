"""공식 VideoX-Fun 양끝 마스크 조건을 ComfyUI Fun 채널 계약에 연결한다."""
import hashlib
from pathlib import Path


def load_fun_endpoint(current_job_root, current_request_record, current_endpoint_name):
    """저장된 입력 사본의 경로와 해시를 검사한다."""
    current_file_name = current_request_record.get(current_endpoint_name + '_file')
    if current_file_name is None:
        return None
    current_expected_name = current_endpoint_name.replace('_', '-') + '.png'
    current_image_path = Path(current_job_root)/current_file_name
    if current_file_name != current_expected_name or current_image_path.is_symlink():
        raise ValueError('시작·종료 이미지 사본 경로 오류')
    if hashlib.sha256(current_image_path.read_bytes()).hexdigest() != current_request_record[current_endpoint_name + '_sha256']:
        raise ValueError('시작·종료 이미지 사본 해시 불일치')
    import numpy as np
    import torch
    from PIL import Image
    with Image.open(current_image_path) as current_image_object:
        if current_image_object.size != (832, 480) or current_image_object.format != 'PNG':
            raise ValueError('시작·종료 이미지 사본 형식 오류')
        return torch.from_numpy(np.asarray(current_image_object.convert('RGB'), dtype=np.float32)/255).unsqueeze(0)


def build_fun_endpoint_tensors(current_frame_count, current_start_tensor, current_end_tensor):
    """미지 구간은 정규화 후 0인 회색, 마스크는 Comfy의 1=미지 계약이다."""
    import torch
    current_reference_tensor = current_start_tensor if current_start_tensor is not None else current_end_tensor
    if current_reference_tensor is None or (current_frame_count-1) % 4:
        raise ValueError('양끝 이미지와 4n+1 프레임 수가 필요합니다.')
    current_height_value, current_width_value = current_reference_tensor.shape[1:3]
    current_video_tensor = torch.full((current_frame_count, current_height_value, current_width_value, 3), 0.5, dtype=current_reference_tensor.dtype, device=current_reference_tensor.device)
    current_mask_tensor = torch.ones((1, 1, current_frame_count+3, 1, 1), dtype=current_reference_tensor.dtype, device=current_reference_tensor.device)
    if current_start_tensor is not None:
        current_video_tensor[:1] = current_start_tensor
        current_mask_tensor[:, :, :4] = 0
    if current_end_tensor is not None:
        current_video_tensor[-1:] = current_end_tensor
        current_mask_tensor[:, :, -1:] = 0
    current_mask_tensor = current_mask_tensor.view(1, (current_frame_count+3)//4, 4, 1, 1).transpose(1, 2)
    return current_video_tensor, current_mask_tensor


def apply_fun_endpoint_conditions(current_condition_output, current_vae_model, current_frame_count, current_start_tensor, current_end_tensor):
    """포즈 절반·외형 참조는 보존하고 이미지 조건 절반과 마스크만 교체한다."""
    import torch
    current_video_tensor, current_mask_tensor = build_fun_endpoint_tensors(current_frame_count, current_start_tensor, current_end_tensor)
    current_endpoint_latent = current_vae_model.encode(current_video_tensor)
    current_channel_count = current_vae_model.latent_channels
    current_condition_groups = []
    for current_condition_group in current_condition_output[:2]:
        current_updated_group = []
        for current_embedding_tensor, current_metadata_record in current_condition_group:
            current_metadata_record = dict(current_metadata_record)
            current_combined_latent = current_metadata_record['concat_latent_image']
            if current_combined_latent.shape[1] != 2*current_channel_count or current_endpoint_latent.shape != current_combined_latent[:, current_channel_count:].shape:
                raise ValueError('Fun Control 양끝 이미지 잠재값 형상 불일치')
            current_metadata_record['concat_latent_image'] = torch.cat((current_combined_latent[:, :current_channel_count], current_endpoint_latent.to(current_combined_latent)), dim=1)
            current_metadata_record['concat_mask'] = current_mask_tensor.to(current_combined_latent).expand(1, 4, -1, current_combined_latent.shape[-2], current_combined_latent.shape[-1])
            current_updated_group.append([current_embedding_tensor, current_metadata_record])
        current_condition_groups.append(current_updated_group)
    return (*current_condition_groups, current_condition_output[2])
