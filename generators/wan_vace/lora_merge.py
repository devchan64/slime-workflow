"""VACE GPU 전문가에 고정된 LoRA를 검증하고 병합한다."""


def merge_adapter(expert, path, strength=1.0):
    return _merge_adapter(expert, path, strength, require_cuda=True)


def _merge_adapter(expert, path, strength=1.0, *, require_cuda):
    import torch
    from safetensors import safe_open

    parameters = dict(expert.named_parameters())
    with safe_open(str(path), framework='pt', device='cpu') as adapter:
        keys = set(adapter.keys())
        pairs = []
        consumed = set()
        for key in sorted(keys):
            if key.endswith('.lora_A.weight'):
                prefix, up_suffix = key[:-len('.lora_A.weight')], '.lora_B.weight'
            elif key.endswith('.lora_down.weight'):
                prefix, up_suffix = key[:-len('.lora_down.weight')], '.lora_up.weight'
            else:
                continue
            up_key = prefix + up_suffix
            target_key = prefix.removeprefix('diffusion_model.') + '.weight'
            if up_key not in keys or target_key not in parameters:
                raise ValueError(f'LoRA 가중치 대상을 찾을 수 없습니다: {prefix}')
            down, up = adapter.get_tensor(key), adapter.get_tensor(up_key)
            target = parameters[target_key]
            if down.ndim != 2 or up.ndim != 2 or target.ndim != 2 or down.shape[0] != up.shape[1] or tuple(target.shape) != (up.shape[0], down.shape[1]):
                raise ValueError(f'LoRA 가중치 크기 불일치: {prefix}')
            if (require_cuda and target.device.type != 'cuda') or target.dtype != torch.bfloat16:
                raise ValueError('LoRA 병합 대상은 GPU BF16이어야 합니다.')
            alpha_key = prefix + '.alpha'
            alpha = float(adapter.get_tensor(alpha_key).item()) / down.shape[0] if alpha_key in keys else 1.0
            if not torch.isfinite(down).all().item() or not torch.isfinite(up).all().item() or not 0 < alpha <= 100:
                raise ValueError(f'LoRA 가중치 또는 alpha 오류: {prefix}')
            pairs.append((key, up_key, target_key, alpha))
            consumed.update((key, up_key))
            if alpha_key in keys:
                consumed.add(alpha_key)
        if not pairs or keys != consumed:
            raise ValueError('LoRA에 인식하지 못한 텐서가 있습니다.')
        with torch.no_grad():
            for down_key, up_key, target_key, alpha in pairs:
                weight = parameters[target_key]
                down = adapter.get_tensor(down_key).to(device=weight.device, dtype=torch.float32)
                up = adapter.get_tensor(up_key).to(device=weight.device, dtype=torch.float32)
                for start in range(0, weight.shape[0], 256):
                    current = weight[start:start + 256]
                    delta = torch.mm(up[start:start + 256], down).mul_(strength * alpha)
                    if not torch.isfinite(delta).all().item():
                        raise ValueError(f'LoRA 병합값에 비유한 값이 있습니다: {target_key}')
                    current.add_(delta.to(dtype=current.dtype))
                    if not torch.isfinite(current).all().item():
                        raise ValueError(f'LoRA 병합 후 가중치에 비유한 값이 있습니다: {target_key}')
    return len(pairs)
