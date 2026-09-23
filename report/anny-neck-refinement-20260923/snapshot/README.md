# 목 둘레 추가 축소

직전 후보의 목 단면 가로·깊이를 중심에서 최대 15% 추가 축소하고 경계에서 가우시안 감쇠한다. 전체 목 둘레의 측정 감소율은 아니다. 흉곽·관절 위치·가중치는 유지한다. 오버레이 60%.

원본: .tmp/anny-neck-ribcage-fit/2026-09-23_08-55-01

재현: reduce_circumference.py → run_stage.py build_preview.py → run_stage.py validate_roundtrip.py. 입력과 실행 스크립트를 함께 보관한다.
