"""Ref2VA attention: 연속 Q/K/V 경로만 허용하고 지원 불가 시 중단한다."""
import json
from pathlib import Path


def is_supported_self_attention_shape(shape):
    """실제 검증된 480p 모델의 배치·헤드 구성과 길이 상한."""
    return len(shape) == 4 and shape[0] == 1 and 1 <= shape[1] <= 32768 and shape[2:] == (56, 128)


def install_contiguous_attention(attempt, torch):
    from diffusers.models.transformers import transformer_minimax_h3 as h3
    from diffusers.models.attention_dispatch import _AttentionBackendRegistry, AttentionBackendName

    path = Path(attempt) / 'contiguous-attention.jsonl'
    recorded_shapes = set()

    def emit(row):
        with path.open('a', encoding='utf8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')

    def stop(reason, query, **details):
        emit({'event': 'stopped', 'reason': reason, 'shape': list(query.shape),
              'dtype': str(query.dtype), 'device': str(query.device), **details})
        raise RuntimeError('연속 배치 어텐션을 사용할 수 없어 작업을 중단합니다: ' + reason)

    def optimized(query, key, value, *args, **kwargs):
        active, _ = _AttentionBackendRegistry.get_active_backend()
        shape = tuple(query.shape)
        if (args or kwargs.get('backend') is not None or active != AttentionBackendName.NATIVE
                or kwargs.get('attn_mask') is not None or kwargs.get('dropout_p', 0.0) != 0.0
                or kwargs.get('is_causal', False) is not False or kwargs.get('parallel_config') is not None
                or query.device.type != 'cuda' or query.dtype != torch.bfloat16
                or not is_supported_self_attention_shape(shape)
                or key.shape != query.shape or value.shape != query.shape
                or key.dtype != query.dtype or value.dtype != query.dtype
                or key.device != query.device or value.device != query.device):
            stop('지원하지 않는 어텐션 조건', query, active_backend=str(active),
                 key_shape=list(key.shape), value_shape=list(value.shape),
                 mask_present=kwargs.get('attn_mask') is not None)
        free, total = torch.cuda.mem_get_info(query.device)
        needed = sum(t.numel() * t.element_size() for t in (query, key, value))
        if free < needed + 5 * 1024**3:
            stop('GPU 여유 메모리 부족', query, free_bytes=free, copy_bytes=needed)
        q, k, v = (tensor.permute(0, 2, 1, 3).contiguous() for tensor in (query, key, value))
        if not all(tensor.is_contiguous() for tensor in (q, k, v)):
            stop('Q/K/V 연속 배치 확인 실패', query)
        out = torch.nn.functional.scaled_dot_product_attention(
            q, k, v, attn_mask=None, dropout_p=0.0, is_causal=False,
            scale=kwargs.get('scale'), enable_gqa=False).permute(0, 2, 1, 3)
        if shape not in recorded_shapes:
            emit({'event': 'contiguous_attention', 'shape': list(shape), 'dtype': str(query.dtype),
                  'free_bytes_before': free, 'total_bytes': total, 'copy_bytes': needed})
            recorded_shapes.add(shape)
        return out

    h3.dispatch_attention_fn = optimized
    return path
