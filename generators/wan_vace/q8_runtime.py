"""Q8_0 GGUF experts with packed weights resident on ROCm GPU."""
from pathlib import Path
import mmap
import numpy as np
import torch
import torch.nn.functional as F
import gguf
import yaml
from diffusers.quantizers.gguf.utils import dequantize_functions
from generators.wan_vace.q8_assets import DIRECTORY, FILES
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT


class Q8Linear(torch.nn.Module):
    """Keep Q8 bytes on device; materialize one BF16 matrix for each call."""
    def __init__(self, packed, shape, bias=None):
        super().__init__()
        self.register_buffer('packed', packed.contiguous())
        self.register_buffer('bias', bias)
        self.shape = tuple(shape)
        self._adapter_count = 0

    def add_adapter(self, down, up, scale):
        index = self._adapter_count
        self.register_buffer(f'adapter_down_{index}', down)
        self.register_buffer(f'adapter_up_{index}', up)
        setattr(self, f'adapter_scale_{index}', float(scale))
        self._adapter_count += 1

    def forward(self, inputs):
        block, size = gguf.GGML_QUANT_SIZES[gguf.GGMLQuantizationType.Q8_0]
        weight = dequantize_functions[gguf.GGMLQuantizationType.Q8_0](self.packed.reshape(-1, size), block, size, dtype=inputs.dtype).reshape(self.shape)
        result = F.linear(inputs, weight, self.bias)
        for i in range(self._adapter_count):
            down = getattr(self, f'adapter_down_{i}')
            up = getattr(self, f'adapter_up_{i}')
            result = result + F.linear(F.linear(inputs, down), up) * getattr(self, f'adapter_scale_{i}')
        return result


def load_q8_expert(stage, model_class):
    """Read validated GGUF into GPU Q8 buffers; never silently dequantize on CPU."""
    from accelerate.utils import set_module_tensor_to_device
    from videox_fun.models.wan_transformer3d import rope_params
    if stage not in FILES or not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('Q8 VACE에는 검증된 모델과 ROCm GPU가 필요합니다.')
    path = DIRECTORY / FILES[stage][0]
    config = yaml.safe_load((Path(__file__).parent / 'config/official-model.yaml').read_text())
    with torch.device('meta'):
        model = model_class(**config)
    reader = gguf.GGUFReader(str(path))
    tensors = {entry.name: entry for entry in reader.tensors}
    state = model.state_dict()
    if set(tensors) != set(state):
        raise ValueError('Q8 GGUF와 VACE 텐서 이름이 일치하지 않습니다.')
    for name, expected in state.items():
        if tuple(expected.shape) != tuple(int(v) for v in tensors[name].shape[::-1]):
            raise ValueError(f'Q8 GGUF 텐서 형상 불일치: {name}')
    def release_file_pages():
        mapping = getattr(reader.data, '_mmap', None)
        if mapping is not None and hasattr(mapping, 'madvise'):
            mapping.madvise(mmap.MADV_DONTNEED)
    replaced = set()
    for name, module in list(model.named_modules()):
        key = name + '.weight'
        if not isinstance(module, torch.nn.Linear) or tensors[key].tensor_type != gguf.GGMLQuantizationType.Q8_0:
            continue
        bias_key = name + '.bias'
        bias = None
        if bias_key in tensors:
            bias = torch.from_numpy(gguf.dequantize(tensors[bias_key].data, tensors[bias_key].tensor_type).copy()).to('cuda', dtype=torch.bfloat16)
            replaced.add(bias_key)
        packed = torch.from_numpy(np.array(tensors[key].data, copy=True)).to('cuda')
        parent, child = name.rsplit('.', 1)
        setattr(model.get_submodule(parent), child, Q8Linear(packed, state[key].shape, bias))
        replaced.add(key)
        release_file_pages()
    for name, expected in state.items():
        if name in replaced:
            continue
        record = tensors[name]
        if record.tensor_type not in (gguf.GGMLQuantizationType.F32, gguf.GGMLQuantizationType.F16, gguf.GGMLQuantizationType.BF16):
            raise ValueError(f'지원하지 않는 Q8 비선형 텐서: {name}')
        value = torch.from_numpy(gguf.dequantize(record.data, record.tensor_type).copy())
        set_module_tensor_to_device(model, name, 'cuda', value=value, dtype=torch.bfloat16)
        del value
        release_file_pages()
    q8_modules = [module for module in model.modules() if isinstance(module, Q8Linear)]
    if not q8_modules or any(module.packed.device.type != 'cuda' or module.packed.dtype != torch.uint8 for module in q8_modules):
        raise RuntimeError('Q8 가중치는 GPU에 Q8_0 바이트로 상주해야 합니다.')
    if any(value.device.type != 'cuda' for value in model.state_dict().values()):
        raise RuntimeError('Q8 전문가 텐서가 GPU에 상주하지 않습니다.')
    dim = model.dim // model.num_heads
    model.freqs = torch.cat([rope_params(1024, dim - 4*(dim//6)), rope_params(1024, 2*(dim//6)), rope_params(1024, 2*(dim//6))], dim=1).to('cuda')
    model._vace_q8_expert = True
    return model.eval().requires_grad_(False)
