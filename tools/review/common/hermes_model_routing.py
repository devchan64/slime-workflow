"""Hermes 요청에 고정할 모델과 최초 GPU 예약 기준."""
import re

DEFAULT_MODEL = 'qwen3.5-4b'
COMPLEX_MODEL = 'qwen3.8-27b'
MODEL_FLOORS_MIB = {DEFAULT_MODEL: 16384, COMPLEX_MODEL: 32768}
COMPLEX_TASK = re.compile(
    r'코드.{0,16}(수정|변경|작성|검토|리뷰)|버그|디버깅|리팩[터토]링|구현|'
    r'(원인|장애|오류|실패|로그)\s*(을|를)?\s*(분석|진단|추적)|'
    r'\b(debug|debugging|implement|refactor|root[ -]cause|fix|patch)\b',
    re.IGNORECASE,
)


def route_hermes_request(request):
    prompt = request['prompt'].rsplit('\n\n현재 사용자 요청:\n', 1)[-1]
    if request.get('verification_modules') or COMPLEX_TASK.search(prompt):
        return COMPLEX_MODEL
    return DEFAULT_MODEL


def saved_model_profile(request):
    profile = request.get('model_profile', COMPLEX_MODEL)
    if profile not in MODEL_FLOORS_MIB:
        raise ValueError('지원하지 않는 Hermes 모델입니다.')
    return profile
