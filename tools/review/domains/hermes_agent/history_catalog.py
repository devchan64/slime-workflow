"""Hermes 작업 이력에서 사용하는 공통 상태 표시와 분류."""

HERMES_HISTORY_STATUS_LABELS = {
    'queued': '대기', 'running': '실행 중', 'completed': '완료',
    'failed': '실패', 'cancelled': '취소', 'paused': '일시정지', 'unknown': '확인 불가',
}


def normalize_hermes_history_status(current_status_value):
    """알 수 없거나 잘못된 상태를 확인 불가로 분류한다."""
    return current_status_value if isinstance(current_status_value,str) and current_status_value in HERMES_HISTORY_STATUS_LABELS else 'unknown'
