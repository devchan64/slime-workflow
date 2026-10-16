"""생성기 공용 상태 표시. 서비스의 추정·측정 값을 재계산하지 않는다."""
from tools.review.common.gradio_history import format_generation_status
from tools.review.common.generation_progress_display import render_generation_estimate


def describe_generation_status(current_status_record, include_generation_estimate=True):
    current_status_name = current_status_record['status']
    current_status_text = '상태: ' + format_generation_status(current_status_record)
    if include_generation_estimate:
        current_status_text += '\n\n' + render_generation_estimate(current_status_record.get('estimate') or {}, current_status_name)
    current_metrics_record = current_status_record.get('metrics') or {}
    current_progress_record = current_status_record.get('progress') or {}
    current_stage_label = current_progress_record.get('stage') or current_metrics_record.get('stage') or current_status_record.get('stage')
    if current_stage_label:
        current_status_text += '\n\n단계: ' + str(current_stage_label)
    if current_progress_record.get('total'):
        current_status_text += f" · 단계 진행 {current_progress_record.get('step', current_metrics_record.get('step', 0))}/{current_progress_record['total']} (전체 예상 진행률과 별개)"
    elif current_metrics_record.get('worker_progress'):
        current_worker_progress = current_metrics_record['worker_progress']
        current_status_text += f"\n\n작업자 마지막 관측: {current_worker_progress['stage']} · 단계 진행 {current_worker_progress['step']}/{current_worker_progress['total']} (전체 예상 진행률과 별개)"
        if current_worker_progress.get('scope'):
            current_status_text += " · 관측 범위: " + current_worker_progress['scope']
        current_status_text += f" · 갱신 시각: {current_worker_progress['updated_at']}"
    current_gpu_records = current_metrics_record.get('gpu_observations') or {}
    if not current_gpu_records:
        current_status_text += '\n\nVRAM: 측정 자료 없음 · 서비스 실행 기록을 확인하세요.'
    for current_gpu_identifier, current_gpu_record in current_gpu_records.items():
        current_memory_value = current_gpu_record.get('process_current_mib')
        current_peak_value = current_gpu_record.get('process_peak_mib')
        current_memory_text = '미측정' if current_memory_value is None else f'{current_memory_value} MiB'
        current_peak_text = '미측정' if current_peak_value is None else f'{current_peak_value} MiB'
        current_status_text += f"\n\nGPU {current_gpu_identifier}: 현재 {current_memory_text} · 관측 피크 {current_peak_text} · 측정 범위: {current_gpu_record.get('scope') or '확인되지 않음'}"
        if current_gpu_record.get('measurement_reason'):
            current_status_text += '\n\n측정 안내: ' + str(current_gpu_record['measurement_reason'])
    if current_gpu_records:
        current_status_text += '\n\n관측 피크는 샘플링 값이며 순간 피크를 놓칠 수 있습니다.'
    if current_metrics_record.get('measurement_gaps'):
        current_status_text += '\n\nVRAM 미측정 구간 존재: 실행 기록에서 원인을 확인하세요.'
    if current_status_record.get('message'):
        current_status_text += '\n\n' + str(current_status_record['message'])
    if current_status_record.get('result_error'):
        current_status_text += '\n\n결과 조회 불가: ' + str(current_status_record['result_error'])
    if current_status_record.get('error'):
        current_status_text += '\n\n실패 원인: ' + str(current_status_record['error'])
    return current_status_text
