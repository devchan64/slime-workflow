"""공식 연산을 변경하지 않고 CUDA OOM 할당·텐서 저장소를 기록한다."""
from contextlib import contextmanager
import json

VACE_MEMORY_HISTORY_LIMIT = 20000


def collect_traceback_tensors(current_traceback_value):
    """예외 스택의 텐서는 값 복사 없이 메타데이터만 수집한다."""
    import torch
    current_tensor_records = []
    def inspect_tensor_value(current_value_object, current_value_path, current_depth_count=0):
        if isinstance(current_value_object, torch.Tensor):
            if current_value_object.device.type != 'cuda':
                return
            current_storage_object = current_value_object.untyped_storage()
            current_tensor_records.append({
                'name': current_value_path, 'shape': list(current_value_object.shape),
                'dtype': str(current_value_object.dtype), 'device': str(current_value_object.device),
                'logical_bytes': current_value_object.numel() * current_value_object.element_size(),
                'storage_address': current_storage_object.data_ptr(),
                'storage_bytes': current_storage_object.nbytes(),
            })
        elif current_depth_count < 2 and isinstance(current_value_object, (list, tuple, dict)):
            current_item_values = current_value_object.items() if isinstance(current_value_object, dict) else enumerate(current_value_object)
            for current_item_key, current_item_value in current_item_values:
                inspect_tensor_value(current_item_value, f'{current_value_path}[{current_item_key}]', current_depth_count + 1)
    while current_traceback_value is not None:
        current_frame_object = current_traceback_value.tb_frame
        current_frame_label = f'{current_frame_object.f_code.co_filename}:{current_traceback_value.tb_lineno}'
        for current_local_name, current_local_value in current_frame_object.f_locals.items():
            inspect_tensor_value(current_local_value, f'{current_frame_label}/{current_local_name}')
        current_traceback_value = current_traceback_value.tb_next
    return current_tensor_records


@contextmanager
def record_cuda_memory_failure(current_attempt_root):
    """실패 스냅샷과 참조 중 텐서를 실행 시도별로 보존한다."""
    import torch
    torch.cuda.memory._record_memory_history(max_entries=VACE_MEMORY_HISTORY_LIMIT)
    try:
        yield
    except torch.OutOfMemoryError as current_failure_error:
        current_tensor_records = collect_traceback_tensors(current_failure_error.__traceback__)
        current_unique_storages = {
            (current_tensor_record['device'], current_tensor_record['storage_address']): current_tensor_record['storage_bytes']
            for current_tensor_record in current_tensor_records
        }
        current_memory_record = {
            'error': str(current_failure_error),
            'allocated_bytes': torch.cuda.memory_allocated(),
            'reserved_bytes': torch.cuda.memory_reserved(),
            'peak_allocated_bytes': torch.cuda.max_memory_allocated(),
            'traceback_unique_storage_bytes': sum(current_unique_storages.values()),
            'scope': '예외 스택의 CUDA 텐서만 포함하며 모델 전체·외부 CUDA 할당은 포함하지 않는다.',
            'tensors': current_tensor_records,
        }
        (current_attempt_root / 'cuda-oom-tensors.json').write_text(json.dumps(current_memory_record, ensure_ascii=False, indent=2))
        torch.cuda.memory._dump_snapshot(str(current_attempt_root / 'cuda-oom-snapshot.pickle'))
        raise
    finally:
        torch.cuda.memory._record_memory_history(enabled=None)
