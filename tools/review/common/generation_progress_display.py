"""서비스의 ETA 값을 재계산하지 않고 공용 표로 표시한다."""
import html
from datetime import datetime


def format_progress_cell(current_field_value):
    return html.escape(str(current_field_value)).replace('|', '&#124;').replace('\n', ' ')


def format_progress_timestamp(current_timestamp_value):
    if not current_timestamp_value:
        return '계산 중'
    try:
        return datetime.fromisoformat(current_timestamp_value).isoformat(sep=' ', timespec='seconds')
    except (ValueError, TypeError):
        return str(current_timestamp_value)


def render_generation_estimate(current_eta_record, current_status_name):
    if current_status_name not in ('running', 'queued'):
        return '작업 종료 · 예상 시간 갱신 종료'
    def format_estimate_value(current_field_name, current_unit_label):
        current_field_value = current_eta_record.get(current_field_name)
        return '계산 중' if current_field_value is None else f'약 {current_field_value}{current_unit_label}'
    current_table_rows = [
        ('예상 남은 시간', format_estimate_value('remaining', '초')),
        ('예상 완료 시각', format_progress_timestamp(current_eta_record.get('completion'))),
        ('예상 총 소요 시간', format_estimate_value('total_seconds', '초')),
        ('예상 진행률', format_estimate_value('estimated_progress', '%')),
    ]
    if current_eta_record.get('total_units'):
        current_table_rows.append(('실측 렌더 진행', f'{current_eta_record["completed_units"]}/{current_eta_record["total_units"]}장 · {current_eta_record["measured_progress"]}% (렌더 단계만)'))
    current_table_rows.extend([
        ('추정 근거', current_eta_record.get('basis') or '실측 근거 수집 중'),
        ('추정 범위', current_eta_record.get('scope') or '아직 확인되지 않음'),
        ('표본 수', f'{current_eta_record.get("sample_count", 0)}개'),
        ('최근 갱신', format_progress_timestamp(current_eta_record.get('updated_at'))),
    ])
    return '| 항목 | 내용 |\n|---|---|\n' + '\n'.join(f'| {current_row_label} | {format_progress_cell(current_row_value)} |' for current_row_label, current_row_value in current_table_rows) + '\n\n예상값은 GPU 부하와 단계별 처리 상황에 따라 달라집니다.'
