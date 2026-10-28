"""제작자 UMT5 BF16 가중치를 양자화 없이 CUDA에서 인코딩한다."""
from types import SimpleNamespace
from generators.wan_vace.contracts import VACE_WORKSPACE_ROOT, VACE_MODEL_FILES

VACE_ENCODER_LAYER_MAPPING = {
    'norm1.weight': 'layer.0.layer_norm.weight',
    'attn.q.weight': 'layer.0.SelfAttention.q.weight',
    'attn.k.weight': 'layer.0.SelfAttention.k.weight',
    'attn.v.weight': 'layer.0.SelfAttention.v.weight',
    'attn.o.weight': 'layer.0.SelfAttention.o.weight',
    'pos_embedding.embedding.weight': 'layer.0.SelfAttention.relative_attention_bias.weight',
    'norm2.weight': 'layer.1.layer_norm.weight',
    'ffn.gate.0.weight': 'layer.1.DenseReluDense.wi_0.weight',
    'ffn.fc1.weight': 'layer.1.DenseReluDense.wi_1.weight',
    'ffn.fc2.weight': 'layer.1.DenseReluDense.wo.weight',
}


def convert_encoder_state(current_original_state):
    """이름만 변환하며 누락·추가 키를 거절한다. 텐서 값과 자료형은 유지한다."""
    current_weight_mapping = {'token_embedding.weight': 'shared.weight', 'norm.weight': 'encoder.final_layer_norm.weight'}
    for current_layer_index in range(24):
        for original_layer_name, converted_layer_name in VACE_ENCODER_LAYER_MAPPING.items():
            current_weight_mapping[f'blocks.{current_layer_index}.{original_layer_name}'] = f'encoder.block.{current_layer_index}.{converted_layer_name}'
    if set(current_original_state) != set(current_weight_mapping):
        raise ValueError(f'UMT5 원본 키 불일치: 누락={set(current_weight_mapping)-set(current_original_state)}, 추가={set(current_original_state)-set(current_weight_mapping)}')
    return {current_weight_mapping[current_weight_name]: current_weight_tensor for current_weight_name, current_weight_tensor in current_original_state.items()}


def load_vace_encoder():
    """CPU는 가중치 보관에만 사용하며 Comfy의 레이어 오프로드를 사용한다."""
    import torch
    import comfy.sd
    import comfy.text_encoders.wan
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError('비양자화 UMT5는 BF16 CUDA 지원이 필요합니다.')
    current_original_state = torch.load(VACE_WORKSPACE_ROOT / VACE_MODEL_FILES['encoder'][0], map_location='cpu', weights_only=True, mmap=True)
    if any(current_weight_tensor.dtype != torch.bfloat16 for current_weight_tensor in current_original_state.values()):
        raise ValueError('UMT5 원본 가중치는 모두 BF16이어야 합니다.')
    current_converted_state = convert_encoder_state(current_original_state)
    current_encoder_target = SimpleNamespace(params={}, clip=comfy.text_encoders.wan.te(dtype_t5=torch.bfloat16), tokenizer=comfy.text_encoders.wan.WanT5Tokenizer)
    current_text_encoder = comfy.sd.CLIP(current_encoder_target,
        tokenizer_data={'spiece_model': (VACE_WORKSPACE_ROOT / VACE_MODEL_FILES['tokenizer'][0]).read_bytes()},
        model_options={'dtype': torch.bfloat16, 'initial_device': torch.device('cpu'), 'load_device': torch.device('cuda:0'), 'offload_device': torch.device('cpu')})
    missing_weight_names, unexpected_weight_names = current_text_encoder.load_sd(current_converted_state)
    if missing_weight_names or unexpected_weight_names:
        raise ValueError(f'UMT5 로드 불일치: 누락={missing_weight_names}, 추가={unexpected_weight_names}')
    return current_text_encoder
