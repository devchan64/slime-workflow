"""LightX2V의 ComfyUI 형식 차분을 Animate-2 Diffusers 가중치에 적용한다."""
from collections import defaultdict


def animate2_target_name(name):
    if not name.startswith('diffusion_model.'):
        raise ValueError(f'지원하지 않는 LoRA 키: {name}')
    name = name.removeprefix('diffusion_model.')
    if '.self_attn.' in name or '.cross_attn.' in name:
        for old, new in (('.q.', '.to_q.'), ('.k.', '.to_k.'), ('.v.', '.to_v.'),
                         ('.o.', '.to_out.0.'), ('.k_img.', '.add_k_proj.'),
                         ('.v_img.', '.add_v_proj.'), ('.norm_k_img.', '.norm_added_k.')):
            if old in name:
                name = name.replace(old, new)
                break
    return name


def plan_lightx2v_weights(entries, targets):
    """적용 전에 모든 차분과 모델 텐서의 존재 및 크기를 검증한다."""
    groups = defaultdict(dict)
    suffixes = (('.lora_down.weight', 'down'), ('.lora_up.weight', 'up'),
                ('.diff_b', 'bias'), ('.diff', 'weight'))
    for name, shape in entries.items():
        if name == '__metadata__':
            continue
        for suffix, kind in suffixes:
            if name.endswith(suffix):
                base = animate2_target_name(name[:-len(suffix)] + '.')[:-1]
                groups[base][kind] = (name, tuple(shape))
                break
        else:
            raise ValueError(f'지원하지 않는 LoRA 키: {name}')
    if not groups:
        raise ValueError('LoRA 가중치가 비어 있습니다.')
    plan = []
    for base, group in groups.items():
        for kind in ('weight', 'bias'):
            if kind in group:
                target = base + '.' + kind
                if target not in targets or tuple(targets[target]) != group[kind][1]:
                    raise ValueError(f'LoRA 차분 크기 불일치: {target}')
                plan.append((target, kind, group[kind][0], None))
        if 'down' in group or 'up' in group:
            if 'down' not in group or 'up' not in group:
                raise ValueError(f'LoRA 쌍 누락: {base}')
            down, up = group['down'], group['up']
            target = base + '.weight'
            if (target not in targets or len(down[1]) != 2 or len(up[1]) != 2
                    or down[1][0] != up[1][1]
                    or tuple(targets[target]) != (up[1][0], down[1][1])):
                raise ValueError(f'LoRA 행렬 크기 불일치: {target}')
            plan.append((target, 'lora', down[0], up[0]))
    return plan


def apply_lightx2v_weights(model, filename):
    """모델이 적재된 장치에서 차분을 합친다. 부분 적용 실패 시 작업 전체를 중단한다."""
    import torch
    from safetensors import safe_open
    targets = model.state_dict()
    with safe_open(str(filename), framework='pt', device='cpu') as source:
        plan = plan_lightx2v_weights({key: source.get_slice(key).get_shape() for key in source.keys()},
                                    {key: value.shape for key, value in targets.items()})
        with torch.no_grad():
            for target, kind, first, second in plan:
                destination = targets[target]
                if destination.device.type not in ('cpu', 'cuda'):
                    raise ValueError('지원하지 않는 LoRA 모델 장치입니다.')
                if kind == 'lora':
                    down = source.get_tensor(first).to(device=destination.device, dtype=torch.float32)
                    up = source.get_tensor(second).to(device=destination.device, dtype=torch.float32)
                    # 큰 FFN 행렬의 임시 메모리를 제한한다.
                    for start in range(0, up.shape[0], 256):
                        end = min(start + 256, up.shape[0])
                        destination[start:end].copy_((destination[start:end].float() + up[start:end] @ down).to(destination.dtype))
                else:
                    delta = source.get_tensor(first).to(device=destination.device, dtype=torch.float32)
                    destination.copy_((destination.float() + delta).to(destination.dtype))
    return len(plan)
