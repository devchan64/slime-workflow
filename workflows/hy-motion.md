# HY-Motion 폐기

2026-10-29 사용자 요청으로 HY-Motion 모델·생성기·관리 페이지·작업 결과 및 이력을 폐기했다. 신규 생성·모델 준비·재개·과거 결과 조회는 제공하지 않는다. 이전 관리 화면 URL은 HTTP 410을 반환한다.

현행 텍스트 모션 생성기는 [Kimodo](../generators/kimodo/README.md)다. ANNY 공용 렌더·셰이딩은 `generators/animation/anny_render/`, 중복 키를 거절하는 YAML 로더는 `tools/review/common/strict_yaml.py`로 분리했다.

모션·포즈 시트 기준 에셋(`assets/motion-sheet`, `assets/pose-sheets`)은 2026-11-01 폐기했다. 현재 등록된 기본 모션은 없다.
