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
     image_edges.py              검정 프레임·텍스처 경계 검출
     image_borders.py            검출 경계 기반 보더 크롭
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

## 마을 맵 원장과 검수 사본

이슬온·갈대나루·돌온재의 블록 배치·건물 크기·층수는 게임 백엔드의 `config/city_layouts/`가 유일한 원장이다. 검수 화면은 런타임에 다른 저장소를 읽지 않고, 게임 데이터에서 명시적으로 내보낸 `assets/world/isloon/game-data/` 사본만 사용한다. 검수 전용 `blocks/<마을>.json` 레이아웃 사본은 두지 않는다. 사본의 `source-manifest.json`에는 세 마을 원장 YAML 해시와 게임 블록 높이를 함께 기록한다.

게임 도시 레이아웃을 다시 컴파일한 뒤 다음 명령으로 검수 사본을 갱신한다.

```bash
cd /home/cbsim/ws/slime-backend
.venv/bin/python scripts/export_city_map_review.py \
  --output-directory /home/cbsim/ws/slime-workflow/assets/world/isloon/game-data
```

검수 빌드는 게임의 60px 블록을 화면 표현 기준인 80px로만 정규화한다. 원장 배치·층수·블록 계층은 변경하지 않는다.

## 공용 이미지 처리

[이미지 엣지 검출·보더 크롭](common/image_borders.md)은 타일 외에도 검은 프레임을 가진 불투명 RGB/RGBA 이미지에서 재사용할 수 있다. 원본 경계 검출과 크롭·보더 계산을 별도 모듈로 관리하며 저장·등록은 호출자가 담당한다.
