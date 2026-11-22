"""Hermes 요청에 고정할 모델과 최초 GPU 예약 기준."""
import re
COMPLEX_MODEL = 'qwen3.8-27b'
DEFAULT_MODEL = COMPLEX_MODEL
LEGACY_MODEL = 'qwen3.5-4b'
MODEL_FLOORS_MIB = {LEGACY_MODEL: 16384, COMPLEX_MODEL: 32768}
COMPLEX_TASK = re.compile(
    r'코딩|코드.{0,16}(수정|변경|작성|검토|리뷰)|버그|디버깅|리팩[터토]링|구현|'
    r'(원인|장애|오류|실패|로그)\s*(을|를)?\s*(분석|진단|추적)|'
    r'\b(debug|debugging|implement|refactor|root[ -]cause|fix|patch|coding)\b',
    re.IGNORECASE,
)
def route_hermes_request(request):
    return COMPLEX_MODEL


def saved_model_profile(request):
    profile = request.get('model_profile', COMPLEX_MODEL)
    if profile not in MODEL_FLOORS_MIB:
        raise ValueError('지원하지 않는 Hermes 모델입니다.')
    return profile
