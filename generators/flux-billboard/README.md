# FLUX 빌보드 가이드 생성기

FLUX 3 공용 실행기와 용도별 설정을 사용한다. 생성 결과는 검수용 후보이며, 기존 Qwen 이력은 아카이브에서 조회한다.

공용 화풍 v1.5.0 원문을 기본으로 조합한다. 참조 이미지는 최대 두 장이며, 투명 참조는 흰색 배경과 합성한다. FLUX 출력은 RGB이며 투명 배경을 보장하지 않는다. 원본 참조 사본·해시·프롬프트·시드·모델 리비전과 생성기별 별도 이력을 보관하고 입력 복원을 지원한다.

CLI 예시: `.venv/bin/python tools/manager.py command flux-billboard generate --prompt 'A simple fantasy object' --reference <참조.png> --detach` (필수 참조: 마네킨·빌보드 가이드·건물).
