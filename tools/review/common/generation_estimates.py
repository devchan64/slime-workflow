"""GUI·CLI가 공유하는 실측 기반 시간 추정 계약."""
from datetime import datetime, timedelta
import math
import statistics
from zoneinfo import ZoneInfo


def calculate_generation_estimate(current_status_record, current_elapsed_samples, current_basis_text, current_scope_text):
    current_clock_value = datetime.now(ZoneInfo('Asia/Seoul'))
    current_estimate_record = {'remaining': None, 'completion': None, 'total_seconds': None, 'estimated_progress': None, 'sample_count': len(current_elapsed_samples), 'updated_at': current_clock_value.isoformat(), 'scope': current_scope_text, 'basis': current_basis_text}
    if current_status_record['status'] not in ('running', 'queued'):
        return {**current_estimate_record, 'basis': '작업 종료 · ' + current_status_record['status']}
    if current_status_record['status'] == 'queued':
        return {**current_estimate_record, 'basis': 'GPU 대기 중 · 대기 시간은 추정에서 제외'}
    if not current_elapsed_samples or not current_status_record.get('started_at'):
        return current_estimate_record
    if any(not math.isfinite(current_sample_value) or current_sample_value <= 0 for current_sample_value in current_elapsed_samples):
        raise ValueError('시간 추정 표본은 유한한 양수여야 합니다.')
    current_total_seconds = statistics.median(current_elapsed_samples)
    current_elapsed_seconds = max(0, (current_clock_value - datetime.fromisoformat(current_status_record['started_at'])).total_seconds())
    current_remaining_seconds = current_total_seconds - current_elapsed_seconds
    if current_remaining_seconds <= 0:
        return {**current_estimate_record, 'basis': current_basis_text + ' · 지연: 표본 시간을 초과하여 계산 중, 새 완료 표본 필요'}
    return {**current_estimate_record, 'total_seconds': round(current_total_seconds, 1), 'remaining': math.ceil(current_remaining_seconds), 'completion': (current_clock_value + timedelta(seconds=current_remaining_seconds)).isoformat(), 'estimated_progress': round(100 * current_elapsed_seconds / current_total_seconds, 1)}
