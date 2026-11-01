"""공식 VideoX-Fun 모델에 고정 GGUF 혼합 정밀도를 연결한다."""
from pathlib import Path
import sys
import numpy as np
import torch
import gguf
import yaml
from diffusers.quantizers.gguf.utils import dequantize_functions
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES, VACE_SOURCE_REVISION

VACE_OFFICIAL_SOURCE_ROOT = VACE_WORKSPACE_ROOT/'.local/videox-fun-vace-pinned'
VACE_OFFICIAL_CONFIG_PATH = Path(__file__).parent/'config/official-model.yaml'


class OfficialGgufLinear(torch.nn.Module):
    """양자화 바이트는 CPU에 두고 CUDA에서만 역양자화·행렬 연산한다."""
    def __init__(self, current_weight_record, current_bias_tensor):
        super().__init__()
        self.current_weight_record = current_weight_record
        self.register_buffer('current_bias_tensor', current_bias_tensor)

    def forward(self, current_input_tensor):
        if current_input_tensor.device.type != 'cuda':
            raise RuntimeError('GGUF Linear는 CUDA 연산만 지원합니다.')
        current_packed_tensor = torch.from_numpy(np.array(self.current_weight_record.data, copy=True)).to(current_input_tensor.device)
        current_quant_type = self.current_weight_record.tensor_type
        current_block_size, current_type_size = gguf.GGML_QUANT_SIZES[current_quant_type]
        current_weight_tensor = dequantize_functions[current_quant_type](current_packed_tensor.reshape(-1,current_type_size),current_block_size,current_type_size,dtype=torch.float32).reshape(tuple(self.current_weight_record.shape[::-1])).to(current_input_tensor.dtype)
        current_bias_tensor = self.current_bias_tensor.to(current_input_tensor) if self.current_bias_tensor is not None else None
        return torch.nn.functional.linear(current_input_tensor, current_weight_tensor, current_bias_tensor)


def inspect_official_gguf(current_model_stage):
    if current_model_stage not in ('high','low'):
        raise ValueError('고정 전문가 high/low만 허용합니다.')
    sys.path.insert(0,str(VACE_OFFICIAL_SOURCE_ROOT))
    from videox_fun.models import VaceWanTransformer3DModel
    current_model_config = yaml.safe_load(VACE_OFFICIAL_CONFIG_PATH.read_text())
    with torch.device('meta'):
        current_official_model = VaceWanTransformer3DModel(**current_model_config)
    current_gguf_reader = gguf.GGUFReader(str(VACE_WORKSPACE_ROOT/VACE_MODEL_FILES[current_model_stage][0]))
    current_tensor_mapping = {current_tensor_record.name: current_tensor_record for current_tensor_record in current_gguf_reader.tensors}
    current_model_state = current_official_model.state_dict()
    if set(current_tensor_mapping) != set(current_model_state):
        raise ValueError('공식 VACE와 GGUF 텐서 이름 불일치')
    for current_tensor_name,current_model_tensor in current_model_state.items():
        if tuple(current_model_tensor.shape) != tuple(current_tensor_mapping[current_tensor_name].shape[::-1]):
            raise ValueError(f'공식 VACE와 GGUF 형상 불일치: {current_tensor_name}')
    return current_official_model,current_gguf_reader,current_tensor_mapping


def load_official_gguf(current_model_stage):
    from accelerate.utils import set_module_tensor_to_device
    current_official_model,current_gguf_reader,current_tensor_mapping = inspect_official_gguf(current_model_stage)
    current_replaced_names = set()
    for current_module_name,current_module_object in list(current_official_model.named_modules()):
        current_weight_name = current_module_name+'.weight'
        if not isinstance(current_module_object,torch.nn.Linear):
            continue
        current_weight_record = current_tensor_mapping[current_weight_name]
        if current_weight_record.tensor_type not in (gguf.GGMLQuantizationType.Q4_K,gguf.GGMLQuantizationType.Q6_K):
            continue
        current_bias_name = current_module_name+'.bias'
        current_bias_tensor = torch.from_numpy(np.array(current_tensor_mapping[current_bias_name].data,copy=True)).to(torch.bfloat16) if current_bias_name in current_tensor_mapping else None
        current_parent_name,current_child_name = current_module_name.rsplit('.',1)
        setattr(current_official_model.get_submodule(current_parent_name),current_child_name,OfficialGgufLinear(current_weight_record,current_bias_tensor))
        current_replaced_names.update((current_weight_name,current_bias_name))
    for current_tensor_name,current_tensor_record in current_tensor_mapping.items():
        if current_tensor_name in current_replaced_names:
            continue
        if current_tensor_record.tensor_type not in (gguf.GGMLQuantizationType.F32,gguf.GGMLQuantizationType.F16,gguf.GGMLQuantizationType.BF16):
            raise ValueError(f'비선형 계층 양자화는 지원하지 않습니다: {current_tensor_name}')
        current_value_tensor = torch.from_numpy(gguf.dequantize(current_tensor_record.data,current_tensor_record.tensor_type).copy()).to(torch.bfloat16)
        set_module_tensor_to_device(current_official_model,current_tensor_name,'cpu',value=current_value_tensor)
    from videox_fun.models.wan_transformer3d import rope_params
    current_head_dimension = current_official_model.dim // current_official_model.num_heads
    current_official_model.freqs = torch.cat([rope_params(1024,current_head_dimension-4*(current_head_dimension//6)),rope_params(1024,2*(current_head_dimension//6)),rope_params(1024,2*(current_head_dimension//6))],dim=1)
    current_official_model.current_gguf_reader = current_gguf_reader
    current_official_model.eval().requires_grad_(False)
    return current_official_model
