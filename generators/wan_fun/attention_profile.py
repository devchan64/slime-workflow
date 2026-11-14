"""선택한 Wan 진단 실행의 실제 attention 커널과 동기화 시간을 기록한다."""
import json
import time


def install_fun_attention_profile(current_attempt_root, current_ops_module, current_call_limit=4):
    import torch
    from torch.profiler import profile, ProfilerActivity
    current_original_function = current_ops_module.scaled_dot_product_attention
    current_output_path = current_attempt_root / 'attention-profile.jsonl'
    current_profile_state = {'calls': 0}

    def record_attention_event(current_event_record):
        with current_output_path.open('a', encoding='utf-8') as current_output_file:
            current_output_file.write(json.dumps(current_event_record, ensure_ascii=False) + '\n')
        print('wan-attention-profile ' + json.dumps(current_event_record, ensure_ascii=False), flush=True)

    def profile_attention_call(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values):
        if current_query_tensor.ndim != 4 or current_query_tensor.shape[-2] < 8192 or current_profile_state['calls'] >= current_call_limit:
            return current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
        current_profile_state['calls'] += 1
        current_call_number = current_profile_state['calls']
        current_shape_record = {'call': current_call_number, 'query_shape': list(current_query_tensor.shape), 'key_shape': list(current_key_tensor.shape), 'dtype': str(current_query_tensor.dtype)}
        record_attention_event({**current_shape_record, 'status':'started'})
        torch.cuda.synchronize()
        current_started_time = time.monotonic()
        if current_call_number == 1:
            with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA]) as current_profiler:
                current_output_tensor = current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
                torch.cuda.synchronize()
            current_kernel_names = list(dict.fromkeys(current_event.name for current_event in current_profiler.events() if str(current_event.device_type).endswith('CUDA')))
        else:
            current_output_tensor = current_original_function(current_query_tensor, current_key_tensor, current_value_tensor, *current_positional_values, **current_keyword_values)
            torch.cuda.synchronize()
            current_kernel_names = []
        record_attention_event({**current_shape_record, 'status':'completed', 'elapsed_seconds':round(time.monotonic()-current_started_time, 3), 'kernels':current_kernel_names})
        return current_output_tensor

    current_ops_module.scaled_dot_product_attention = profile_attention_call
