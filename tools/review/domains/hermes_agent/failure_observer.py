"""원본 오류를 노출하지 않고 메모리 보호 상태만 표시한다."""


def observe_hermes_failure_reason(current_status_value, current_error_value):
    if current_status_value != 'failed' or not isinstance(current_error_value, str):
        return {}
    if current_error_value.startswith('시스템 RAM 보호:'):
        return {'failure_code': 'host_memory_guard', 'failure_reason': '시스템 메모리 보호로 작업이 중단됐습니다. 메모리 여유를 확인한 후 다시 요청하세요.'}
    if current_error_value.startswith('시스템 RAM 감시 실패:'):
        return {'failure_code': 'host_memory_monitor_failed', 'failure_reason': '시스템 메모리를 감시할 수 없어 작업이 중단됐습니다. 관리도구의 상세 기록을 확인하세요.'}
    return {}
