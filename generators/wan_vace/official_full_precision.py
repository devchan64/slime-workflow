"""고정된 공식 VACE 비양자화 전문가의 준비·GPU 로딩 도구.
"""
from pathlib import Path
import hashlib

from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_ENCODER_IDENTIFIER, VACE_ENCODER_REVISION

VACE_FULL_PRECISION_FILES = {
    'high': ('high_noise_model/diffusion_pytorch_model.safetensors', 34675325000,
             '66c61b736c5674deeeef17861e494d3652cc9b1463a9656bf18c2c72d2c5f007'),
    'low': ('low_noise_model/diffusion_pytorch_model.safetensors', 34675325000,
            '0bf791adfb8330d451d2f5c03577b2a8fb780453f8ef05e23a8fa91f27a2134d'),
}
VACE_FULL_PRECISION_ROOT = VACE_WORKSPACE_ROOT / '.model/wan22-vace-official'


def get_full_precision_path(current_expert_name):
    if current_expert_name not in VACE_FULL_PRECISION_FILES:
        raise ValueError('전문가는 high 또는 low여야 합니다.')
    return VACE_FULL_PRECISION_ROOT / VACE_FULL_PRECISION_FILES[current_expert_name][0]


def verify_full_precision_file(current_expert_name):
    current_expert_path = get_full_precision_path(current_expert_name)
    _, expected_file_size, expected_file_hash = VACE_FULL_PRECISION_FILES[current_expert_name]
    if not current_expert_path.is_file() or current_expert_path.stat().st_size != expected_file_size:
        raise ValueError(f'공식 전문가 파일 누락 또는 크기 불일치: {current_expert_name}')
    with current_expert_path.open('rb') as current_file_stream:
        if hashlib.file_digest(current_file_stream, 'sha256').hexdigest() != expected_file_hash:
            raise ValueError(f'공식 전문가 SHA-256 불일치: {current_expert_name}')
    return current_expert_path


def download_full_precision_file(current_expert_name):
    from tools.management.common.model_http_download import download_verified_http
    current_expert_path = get_full_precision_path(current_expert_name)
    current_remote_name, expected_file_size, expected_file_hash = VACE_FULL_PRECISION_FILES[current_expert_name]
    current_expert_path.parent.mkdir(parents=True, exist_ok=True)
    current_remote_url = f'https://huggingface.co/{VACE_ENCODER_IDENTIFIER}/resolve/{VACE_ENCODER_REVISION}/{current_remote_name}'
    download_verified_http(current_remote_url, current_expert_path, expected_file_hash,
                           'wan-vace/full-precision-' + current_expert_name,
                           current_partial_path=current_expert_path.with_suffix('.partial'),
                           expected_total_bytes=expected_file_size)
    return verify_full_precision_file(current_expert_name)


def assign_vace_bf16_weight(current_setter_function, current_model_object, current_tensor_name, current_file_tensor, current_torch_module):
    """메타 모델 기본 dtype이 FP32여도 파일의 BF16 정밀도를 유지한다."""
    current_setter_function(current_model_object, current_tensor_name, 'cuda', value=current_file_tensor, dtype=current_torch_module.bfloat16)


def load_full_precision_expert(current_expert_name, current_model_class):
    """검증된 전문가를 GPU에 직접 적재한다. CPU 추론이나 오프로드는 사용하지 않는다."""
    import torch
    import yaml
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open
    from videox_fun.models.wan_transformer3d import rope_params

    if not getattr(torch.version, 'hip', None) or not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('비양자화 VACE는 BF16을 지원하는 GPU가 필요합니다.')
    current_weight_path = verify_full_precision_file(current_expert_name)
    current_config_path = Path(__file__).parent / 'config/official-model.yaml'
    current_config_record = yaml.safe_load(current_config_path.read_text())
    with torch.device('meta'):
        current_model_object = current_model_class(**current_config_record)
    current_expected_state = current_model_object.state_dict()
    with safe_open(str(current_weight_path), framework='pt', device='cpu') as current_safe_file:
        if set(current_safe_file.keys()) != set(current_expected_state):
            raise ValueError('공식 전문가 텐서 이름이 모델과 일치하지 않습니다.')
    # 대형 체크포인트의 mmap 전체를 열린 채 읽으면 이미 GPU로 복사한
    # 페이지도 작업자 RSS에 남아 한정된 호스트 RAM을 고갈시킬 수 있다.
    # 각 텐서 복사 후 참조와 매핑을 해제한다. 가중치는 GPU에 상주한다.
    for current_tensor_name, current_model_tensor in current_expected_state.items():
        with safe_open(str(current_weight_path), framework='pt', device='cpu') as current_safe_file:
            current_file_tensor = current_safe_file.get_tensor(current_tensor_name)
            if current_file_tensor.shape != current_model_tensor.shape:
                raise ValueError(f'공식 전문가 텐서 형상 불일치: {current_tensor_name}')
            if current_file_tensor.dtype != torch.bfloat16:
                raise ValueError(f'공식 전문가 텐서가 BF16이 아닙니다: {current_tensor_name}')
            assign_vace_bf16_weight(set_module_tensor_to_device, current_model_object, current_tensor_name, current_file_tensor, torch)
            del current_file_tensor
    for current_tensor_name, current_loaded_tensor in current_model_object.state_dict().items():
        if current_loaded_tensor.dtype != torch.bfloat16 or current_loaded_tensor.device.type != 'cuda':
            raise RuntimeError(f'공식 전문가 텐서는 GPU BF16이어야 합니다: {current_tensor_name}')
    current_head_dimension = current_model_object.dim // current_model_object.num_heads
    current_model_object.freqs = torch.cat([
        rope_params(1024, current_head_dimension - 4 * (current_head_dimension // 6)),
        rope_params(1024, 2 * (current_head_dimension // 6)),
        rope_params(1024, 2 * (current_head_dimension // 6)),
    ], dim=1).to('cuda')
    return current_model_object.eval().requires_grad_(False)
