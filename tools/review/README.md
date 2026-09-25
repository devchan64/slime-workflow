# 관리도구 소스 구조

관리도구의 실행 진입점과 화면 URL은 유지하며, 구현을 도메인별로 관리한다.

```text
tools/manager.py                  통합 CLI 진입점
 tools/review/
   serve.py                      HTTP 서버·watch·서비스 연결
   build_*.py                    검수 산출물 빌드 진입점
   common/
     management_gateway.py       공용 명령 계약·CLI·HTTP 디스패치
     generation_records.py       공용 원자적 기록 저장
     management_log_viewer.py    공용 로그 동작
   domains/
     character_animation/        등록 모션·캐릭터 생성 API·자산·작업
     momask/                     모션 생성·작업·OpenPose 변환
     anny/                       체형 속성·미리보기·렌더 API
     image/                      Qwen 이미지 API·참조 입력 검증
   ui/
     shared/                     공용 스타일·이력·진행·영역 이동
     character_animation/        캐릭터 생성 화면·원본 재생
     momask/                     MoMask 화면 스타일
     anny/                       속성 화면·3D 뷰어
     image/                      텍스트·참조 이미지 생성 화면
     map/                        지도·타일 검수 템플릿
     asset_review/               검수 허브·시트·포즈 비교 템플릿
   ui_assets.py                  UI 파일의 명시적 경로 레지스트리
   tests/                        공용 계약·도메인 회귀 테스트
```

## 의존성과 확장

- 서버와 통합 게이트웨이가 각 도메인을 연결한다. 신규 구현은 `domains/<domain>/`에 추가한다.
- 도메인 공통 기능은 `common/`, 공통 화면 자원은 `ui/shared/`에 둔다. 다른 생성기의 작업 모듈에서 공용 함수를 가져오지 않는다.
- UI 파일은 `resolve_review_ui_asset()`으로 조회한다. 파일명은 레지스트리에 명시하며 사용자 입력 경로를 파일 시스템 경로로 직접 사용하지 않는다.
- 빌드 스크립트와 서버의 위치는 실행 계약이므로 유지한다. 서비스 실행 경로와 모델 실행 코드는 구분하며, 모델 실행기는 기존 `generators/` 도메인에 둔다.
- MoMask의 HTML·스크립트는 아직 도메인 API 모듈 내부에 있다. 이번 정리는 파일의 도메인 소유권을 옮긴 것으로, 모든 화면이 외부 템플릿으로 분리되었다는 뜻은 아니다.
- 작가 에이전트는 기존 `generators/writer_agent/` 도메인에 있다. 이번 관리도구 소스 이동에 포함하지 않는다.

## 호환성과 운영

루트의 이전 서비스 모듈(`character_animation_jobs.py`, `momask_jobs.py` 등)은 이전 import·직접 실행 경로를 위한 얇은 연결이다. 실제 구현은 정식 도메인 모듈 한 곳에 있으며 새 코드는 정식 경로를 사용한다. 기존 작업자가 실행 중 재사용하는 이전 import도 유지한다. 호환 모듈에 기능을 추가하거나 구현을 복사하지 않는다.

HTTP URL, 페이지 해시, CLI 명령, `.tmp` 생성 ID·기록 경로와 `assets` 경로는 변경하지 않는다. 이동 후 서버·CLI import와 실행기 `--help`, 공용 회귀 테스트, 주요 페이지의 CSS·JS 제공을 검증한다.

관련 기준: [UI 가이드](../../workflows/management-ui.md), [클라이언트 가이드](../../workflows/management-clients.md).
