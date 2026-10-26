"""모델 입력을 변경하지 않고 시간축 변화량을 기록한다."""
import hashlib
import numpy as np


def summarize_temporal_arrays(current_frame_arrays):
    """프레임 단위로 처리해 진단용 전체 텐서 복사를 피한다."""
    current_tensor_digest = hashlib.sha256()
    current_frame_records = []
    previous_frame_array = None
    for current_frame_array in current_frame_arrays:
        current_frame_array = np.asarray(current_frame_array, dtype=np.float32)
        if not np.isfinite(current_frame_array).all():
            raise ValueError('시간축 진단: 비유한 텐서 값')
        current_frame_bytes = current_frame_array.tobytes(order='C')
        current_tensor_digest.update(current_frame_bytes)
        current_frame_records.append({
            'index': len(current_frame_records),
            'sha256': hashlib.sha256(current_frame_bytes).hexdigest(),
            'mean': float(current_frame_array.mean()),
            'std': float(current_frame_array.std()),
            'zero_fraction': float(np.mean(current_frame_array == 0)),
            'one_fraction': float(np.mean(current_frame_array == 1)),
            'previous_mae': None if previous_frame_array is None else float(np.abs(current_frame_array - previous_frame_array).mean()),
        })
        previous_frame_array = current_frame_array
    return {'sha256': current_tensor_digest.hexdigest(), 'time_count': len(current_frame_records), 'frames': current_frame_records}


def summarize_temporal_tensor(current_tensor_value, current_time_axis):
    current_tensor_view = current_tensor_value.detach().movedim(current_time_axis, 0)
    current_summary_record = summarize_temporal_arrays(current_frame_tensor.float().cpu().numpy() for current_frame_tensor in current_tensor_view)
    return {'shape': list(current_tensor_value.shape), 'dtype': str(current_tensor_value.dtype), 'time_axis': current_time_axis, 'hash_format': '시간축 우선 float32 C-order', **current_summary_record}
