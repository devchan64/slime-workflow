"""긴 참조 self-attention의 ROCm 텐서 배치를 최적화한다."""
from functools import wraps

ANIMATE_ATTENTION_MINIMUM_TOKENS = 8192
ANIMATE_ATTENTION_HEADROOM_BYTES = 2 * 1024**3
ANIMATE_FLEX_HEADS_PER_KERNEL = 4


def prepare_animate_attention_layout(current_query_tensor, current_key_tensor, current_value_tensor, current_available_bytes, current_minimum_tokens=ANIMATE_ATTENTION_MINIMUM_TOKENS):
    """[B,S,H,D] 의미를 보존하며 내부 [B,H,S,D]를 연속 배치한다."""
    current_tensor_values=(current_query_tensor,current_key_tensor,current_value_tensor)
    if any(current_tensor_value.ndim != 4 for current_tensor_value in current_tensor_values):
        return current_tensor_values,False
    if current_query_tensor.shape[1] < current_minimum_tokens or any(current_tensor_value.shape != current_query_tensor.shape for current_tensor_value in current_tensor_values):
        return current_tensor_values,False
    current_copy_bytes=sum(current_tensor_value.numel()*current_tensor_value.element_size() for current_tensor_value in current_tensor_values if not current_tensor_value.transpose(1,2).is_contiguous())
    if current_available_bytes < current_copy_bytes + ANIMATE_ATTENTION_HEADROOM_BYTES:
        return current_tensor_values,False
    return tuple(current_tensor_value.transpose(1,2).contiguous().transpose(1,2) for current_tensor_value in current_tensor_values),bool(current_copy_bytes)


def install_animate_reference_layout(current_transformer_module,current_torch_module):
    """긴 참조와 확인된 헤드 독립 Flex 마스크의 ROCm 배치를 최적화한다."""
    current_original_dispatch=current_transformer_module.dispatch_attention_fn
    current_mask_code_values=tuple(value for value in current_transformer_module.WanAnimate2Transformer3DModel.create_mask.__code__.co_consts if hasattr(value,'co_name') and value.co_name=='attention_mask_logic')
    @wraps(current_original_dispatch)
    def dispatch_animate_attention(current_query_tensor,current_key_tensor,current_value_tensor,*current_dispatch_arguments,**current_dispatch_keywords):
        current_mask_value=current_dispatch_keywords.get('attn_mask')
        current_mask_function=getattr(current_mask_value,'mask_mod',None)
        current_flex_supported=(not current_dispatch_arguments and set(current_dispatch_keywords).issubset({'attn_mask','backend','parallel_config'})
            and current_dispatch_keywords.get('backend') == 'flex' and current_dispatch_keywords.get('parallel_config') is None
            and getattr(current_mask_function,'__code__',None) in current_mask_code_values
            and current_query_tensor.is_cuda and current_torch_module.version.hip
            and current_query_tensor.ndim == current_key_tensor.ndim == current_value_tensor.ndim == 4
            and current_query_tensor.shape[1] >= ANIMATE_ATTENTION_MINIMUM_TOKENS
            and current_query_tensor.shape[0] == current_key_tensor.shape[0] == current_value_tensor.shape[0] == 1
            and current_query_tensor.shape[2:] == current_key_tensor.shape[2:] == current_value_tensor.shape[2:]
            and current_key_tensor.shape == current_value_tensor.shape and current_query_tensor.shape[2] > ANIMATE_FLEX_HEADS_PER_KERNEL)
        if current_flex_supported:
            try:
                current_available_bytes,_=current_torch_module.cuda.mem_get_info(current_query_tensor.device)
            except (RuntimeError,OSError):
                current_available_bytes=0
            current_copy_bytes=sum(value.numel()*value.element_size() for value in (current_query_tensor,current_key_tensor,current_value_tensor)) // current_query_tensor.shape[2] * ANIMATE_FLEX_HEADS_PER_KERNEL
            current_output_bytes=current_query_tensor.numel()*current_query_tensor.element_size()*2
            if current_available_bytes >= current_copy_bytes+current_output_bytes+ANIMATE_ATTENTION_HEADROOM_BYTES:
                current_head_outputs=[]
                for current_head_start in range(0,current_query_tensor.shape[2],ANIMATE_FLEX_HEADS_PER_KERNEL):
                    current_head_end=min(current_head_start+ANIMATE_FLEX_HEADS_PER_KERNEL,current_query_tensor.shape[2])
                    current_head_inputs=tuple(value[:,:,current_head_start:current_head_end,:].transpose(1,2).contiguous().transpose(1,2) for value in (current_query_tensor,current_key_tensor,current_value_tensor))
                    current_head_outputs.append(current_original_dispatch(*current_head_inputs,**current_dispatch_keywords))
                return current_torch_module.cat(current_head_outputs,dim=2)
        if (not current_dispatch_arguments and current_dispatch_keywords.get('attn_mask') is None
            and current_dispatch_keywords.get('backend') is None and current_dispatch_keywords.get('parallel_config') is None
            and current_query_tensor.is_cuda and current_torch_module.version.hip):
            try:
                current_available_bytes,_=current_torch_module.cuda.mem_get_info(current_query_tensor.device)
            except (RuntimeError,OSError):
                current_available_bytes=0
            (current_query_tensor,current_key_tensor,current_value_tensor),_=prepare_animate_attention_layout(current_query_tensor,current_key_tensor,current_value_tensor,current_available_bytes)
        return current_original_dispatch(current_query_tensor,current_key_tensor,current_value_tensor,*current_dispatch_arguments,**current_dispatch_keywords)
    current_transformer_module.dispatch_attention_fn=dispatch_animate_attention
