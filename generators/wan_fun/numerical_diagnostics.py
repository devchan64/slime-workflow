"""추론 스텝에서 비유한 값이 처음 나타난 위치를 보존한다."""
import hashlib
import json


def fingerprint_fun_tensor(current_torch_module, current_tensor_value):
    current_detached_tensor = current_tensor_value.detach().to(dtype=current_torch_module.float32, device='cpu').contiguous()
    return {'shape': list(current_detached_tensor.shape), 'sha256': hashlib.sha256(current_detached_tensor.numpy().tobytes()).hexdigest(), 'finite': bool(current_torch_module.isfinite(current_detached_tensor).all().item())}


def record_fun_numerical_step(current_torch_module, current_attempt_root, current_model_stage, current_step_number, current_denoised_tensor, current_sample_tensor):
    current_step_record = {'stage': current_model_stage, 'step': current_step_number, 'callback_sample': '스텝 갱신 전'}
    for current_tensor_name, current_tensor_value in (('denoised', current_denoised_tensor), ('sample', current_sample_tensor)):
        current_tensor_finite = current_torch_module.isfinite(current_tensor_value)
        current_nonfinite_count = int((~current_tensor_finite).sum().item())
        current_step_record[current_tensor_name] = {'nonfinite': current_nonfinite_count, 'max_abs': None if current_nonfinite_count else float(current_tensor_value.abs().max().item())}
    with (current_attempt_root / 'numerical-steps.jsonl').open('a', encoding='utf-8') as current_output_file:
        current_output_file.write(json.dumps(current_step_record, ensure_ascii=False, allow_nan=False) + '\n')
    if any(current_step_record[current_tensor_name]['nonfinite'] for current_tensor_name in ('denoised', 'sample')):
        raise ValueError(f'{current_model_stage} 추론 {current_step_number}단계에서 NaN 또는 무한대가 발견되었습니다. numerical-steps.jsonl을 확인하세요.')
