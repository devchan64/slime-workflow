# 목 높이·다리 길이 수정

원본: .tmp/anny-reference-pose/2026-09-23_12-23-42

measure-neck-height-incr 1→0.5, upperlegs-height-incr 0.5→0.7, lowerlegs-height-incr 0.5→0.7. 목 세로 스케일 0.5와 기타 입력 유지. 메시 후보정 없음.

재현: generate_attributes.py → build_preview.py → validate_roundtrip.py → package_overlay.py. ANNY는 .venv/bin/python, Blender는 .local/blender-runtime/bin/python run_stage.py. CUDA 필요.
