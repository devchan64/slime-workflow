"""원본 오류를 노출하지 않고 확인된 메모리 실패를 표시한다."""


def observe_hermes_failure_reason(current_status_value, current_error_value):
    if current_status_value != 'failed' or not isinstance(current_error_value, str):
        return {}
    if current_error_value.startswith('시스템 RAM 보호:'):
        return {'failure_code': 'host_memory_guard', 'failure_reason': '시스템 메모리 보호로 작업이 중단됐습니다. 메모리 여유를 확인한 후 다시 요청하세요.'}
    if current_error_value.startswith('시스템 RAM 감시 실패:'):
        return {'failure_code': 'host_memory_monitor_failed', 'failure_reason': '시스템 메모리를 감시할 수 없어 작업이 중단됐습니다. 관리도구의 상세 기록을 확인하세요.'}
    current_error_text=current_error_value.casefold()
    current_gpu_memory_prefixes=('cuda out of memory','cuda error: out of memory','hip out of memory','hip error: out of memory','torch.cuda.outofmemoryerror: cuda out of memory','torch.outofmemoryerror: cuda out of memory','torch.outofmemoryerror: hip out of memory')
    if current_error_text.startswith(current_gpu_memory_prefixes):
        return {'failure_code':'gpu_out_of_memory','failure_reason':'GPU 메모리 부족으로 작업이 실패했습니다. 다른 GPU 작업과 메모리 상태를 확인한 뒤 재개를 검토하세요.'}
    return {}


def observe_hermes_generator_failure(current_status_value, current_error_value):
    """검증된 원인만 분류하고 미분류 실패는 원 서비스 확인을 안내한다."""
    current_failure_record = observe_hermes_failure_reason(current_status_value, current_error_value)
    if current_failure_record or current_status_value != 'failed':
        return current_failure_record
    return {'failure_code':'unclassified_failure', 'failure_reason':'실패 원인을 확인하지 못했습니다. 원 서비스의 작업 상태와 상세 로그를 확인하세요.'}
