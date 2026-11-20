"""원 서비스 이력 정리 미리보기를 경로 없는 제한된 요약으로 변환한다."""
from collections import Counter
import threading

CLEANUP_PREVIEW_LOCK_GUARD = threading.Lock()
CLEANUP_PREVIEW_SERVICE_LOCKS = {}


def summarize_cleanup_preview_record(current_service_name, current_preview_record):
    """삭제를 실행하지 않으며 원 서비스의 관측 시점 결과만 요약한다."""
    if not isinstance(current_service_name, str) or not current_service_name:
        raise ValueError('정리 검토 서비스 오류')
    if not isinstance(current_preview_record, dict):
        raise ValueError('정리 검토 응답 오류')
    current_job_records = current_preview_record.get('jobs')
    current_blocked_records = current_preview_record.get('blocked_jobs')
    current_job_count = current_preview_record.get('job_count')
    current_reset_allowed = current_preview_record.get('can_reset')
    current_excludes_blocked = current_preview_record.get('excludes_blocked', False)
    if (not isinstance(current_job_records, list) or not isinstance(current_blocked_records, list)
            or type(current_job_count) is not int or current_job_count != len(current_job_records)
            or type(current_reset_allowed) is not bool or type(current_excludes_blocked) is not bool):
        raise ValueError('정리 검토 목록 또는 개수 오류')
    if current_reset_allowed != (bool(current_job_records) if current_excludes_blocked else not bool(current_blocked_records)):
        raise ValueError('정리 가능 여부와 차단 목록이 일치하지 않습니다.')
    current_status_counts = Counter()
    for current_job_record in current_job_records:
        if not isinstance(current_job_record, dict) or not isinstance(current_job_record.get('status'), str):
            raise ValueError('정리 검토 작업 상태 오류')
        current_status_value = current_job_record['status']
        if current_status_value not in ('completed','failed','cancelled','canceled','paused','running','queued','unknown'):
            current_status_value = 'other'
        current_status_counts[current_status_value] += 1
    if any(not isinstance(current_blocked_record, dict) for current_blocked_record in current_blocked_records):
        raise ValueError('정리 검토 차단 목록 오류')
    return {'service': current_service_name, 'job_count': current_job_count,
            'blocked_count': len(current_blocked_records), 'status_counts': dict(sorted(current_status_counts.items())),
            'can_reset': current_reset_allowed, 'excludes_blocked': current_excludes_blocked,
            'note': '원 서비스가 이력과 숨긴 작업을 검사한 시점의 요약입니다. 삭제하지 않았으며 실행 시 대상과 상태를 다시 확인해야 합니다.'}


def read_hermes_cleanup_preview(current_service_name):
    """지원 서비스의 정리 미리보기를 한 번 조회하고 경로 없는 요약만 반환한다."""
    from tools.review.common.management_gateway import MANAGEMENT_SERVICE_COMMANDS, inspect_management_policy_rejection
    from tools.review.common.management_client import execute_remote_management_command
    if (not isinstance(current_service_name, str) or current_service_name not in MANAGEMENT_SERVICE_COMMANDS
            or 'history-reset-preview' not in MANAGEMENT_SERVICE_COMMANDS[current_service_name]):
        raise ValueError('정리 미리보기를 지원하는 서비스를 선택하세요.')
    from generators.music.service_constants import inspect_retired_audio_rejection
    from tools.review.domains.character_animation.retirement_policy import inspect_animation_retirement_policy
    current_policy_reason = (inspect_management_policy_rejection(current_service_name, 'history-reset-preview')
        or inspect_retired_audio_rejection(current_service_name, 'history-reset-preview')
        or (inspect_animation_retirement_policy('history-reset-preview') if current_service_name == 'character-animation' else None))
    if current_policy_reason:
        raise ValueError(current_policy_reason)
    with CLEANUP_PREVIEW_LOCK_GUARD:
        current_service_lock = CLEANUP_PREVIEW_SERVICE_LOCKS.setdefault(current_service_name, threading.Lock())
    if not current_service_lock.acquire(blocking=False):
        raise ValueError('이 서비스의 정리 미리보기가 이미 진행 중입니다. 완료 후 다시 확인하세요.')
    try:
        try:
            current_preview_record = execute_remote_management_command(current_service_name, 'history-reset-preview', {})
            return summarize_cleanup_preview_record(current_service_name, current_preview_record)
        except (OSError, RuntimeError, ValueError, TypeError, KeyError):
            raise ValueError('정리 미리보기를 확인할 수 없습니다. 원 서비스 이력과 작업 상태를 확인하세요.') from None
    finally:
        current_service_lock.release()
