"""Decision rules for a future GPU-reserved reusable Hermes model server.

This module makes decisions only; it does not retain or release a process.
"""
from dataclasses import dataclass
from typing import Literal

from workflow.common.hermes_model_routing import MODEL_FLOORS_MIB

DEFAULT_IDLE_SECONDS = 60
MAX_IDLE_SECONDS = 300


@dataclass(frozen=True)
class ResidencyDecision:
    action: Literal['reuse', 'keep', 'evict']
    reason: str


def decide_residency(*, resident_profile, requested_profile, idle_seconds,
                     idle_limit_seconds=DEFAULT_IDLE_SECONDS, reservation_verified,
                     server_healthy, memory_safe, waiting_other_work, shutdown=False):
    """Fail closed when health, reservation, pressure, or competing work is unknown."""
    if resident_profile not in MODEL_FLOORS_MIB:
        raise ValueError('지원하지 않는 상주 모델입니다.')
    if requested_profile is not None and requested_profile not in MODEL_FLOORS_MIB:
        raise ValueError('지원하지 않는 요청 모델입니다.')
    if type(idle_seconds) not in (int, float) or not 0 <= idle_seconds < float('inf'):
        raise ValueError('유휴 시간 오류')
    if type(idle_limit_seconds) is not int or not 0 <= idle_limit_seconds <= MAX_IDLE_SECONDS:
        raise ValueError('유휴 유지 시간 오류')
    if type(shutdown) is not bool or any(value is not None and type(value) is not bool for value in
            (reservation_verified, server_healthy, memory_safe, waiting_other_work)):
        raise ValueError('모델 상태 형식 오류')
    if shutdown:
        return ResidencyDecision('evict', '서비스 종료')
    if reservation_verified is not True:
        return ResidencyDecision('evict', 'GPU 예약 신원 확인 불가')
    if server_healthy is not True:
        return ResidencyDecision('evict', '모델 서버 상태 확인 불가')
    if memory_safe is not True:
        return ResidencyDecision('evict', '메모리 여유 부족 또는 확인 불가')
    if waiting_other_work is not False:
        return ResidencyDecision('evict', '다른 작업 대기 또는 대기열 확인 불가')
    if requested_profile is not None and requested_profile != resident_profile:
        return ResidencyDecision('evict', '요청 모델 변경')
    if idle_seconds >= idle_limit_seconds:
        return ResidencyDecision('evict', '유휴 유지 시간 만료')
    if requested_profile == resident_profile:
        return ResidencyDecision('reuse', '같은 모델의 후속 요청')
    return ResidencyDecision('keep', '후속 요청 대기')
