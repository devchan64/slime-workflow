"""Apply Wan LoRA and direct weight/bias deltas without silently dropping patches."""


def apply_adapter(model, path, strength, comfy_sd, comfy_utils):
    old_patches={key:len(value) for key,value in model.patches.items()}
    adapter=comfy_utils.load_torch_file(str(path),safe_load=True)
    weights=set()
    biases=set()
    for key in adapter:
        for suffix in ('.lora_down.weight','.lora_A.weight','.diff','.set_weight','.w_norm'):
            if key.endswith(suffix):
                weights.add(key[:-len(suffix)])
                break
        for suffix in ('.diff_b','.b_norm'):
            if key.endswith(suffix):
                biases.add(key[:-len(suffix)])
                break
    expected=len(weights)+len(biases)
    if not expected:
        raise ValueError(f'LoRA 가중치를 확인할 수 없습니다: {path.name}')
    result,_=comfy_sd.load_lora_for_models(model,None,adapter,strength,0)
    added=sum(len(value)-old_patches.get(key,0) for key,value in result.patches.items())
    if added!=expected:
        raise ValueError(f'LoRA 적용 수 불일치: {path.name}, 예상 {expected}, 적용 {added}')
    return result,added
