# 관리도구 소스 구조

관리도구의 실행 진입점과 화면 URL은 유지하며, 구현을 도메인별로 관리한다.

```text
tools/manager.py                  통합 CLI 진입점
 tools/review/
   serve.py                      GUI HTTP 서버·watch·API 중계
   gateway_server.py             독립 명령 게이트웨이·작업 서비스 서버
   build_*.py                    검수 산출물 빌드 진입점
   common/
     management_gateway.py       공용 명령 계약·CLI·HTTP 디스패치
     management_runtime.py       서비스 연결·기록 경로·수명 관리
     management_environment.py   공용 경로·포트·접속 주소 검증
     management_launcher.py      실행 스크립트 인자 전달·오류 종료
     management_setup.py         명시적 가상환경·의존성 설치
     management_process.py       출력 로그·heartbeat·소유 프로세스 그룹 종료
     management_client.py        GUI 전용 HTTP 명령 클라이언트
     management_transport.py     동일 출처 API 중계·접속 검증
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

- 독립 게이트웨이의 `management_runtime.py`가 각 도메인을 연결한다. `ManagementServiceBinding` 한 항목에서 HTTP 처리·기록 루트·기록 경로 해석기를 정의하고 명령·파일 조회·폴더 열기에 같은 연결을 사용한다. 서비스 이름·URL은 `management_gateway.py`의 등록부를 따르며 연결 누락·알 수 없는 서비스는 시작 시 거절한다. GUI 서버는 작업 서비스를 생성하지 않는다. 신규 구현은 `domains/<domain>/`에 추가한다.
- Gradio는 환경 경로를 `management_environment.py`에서만 가져온다. 설치·프로세스 실행기를 환경 설정 의존성으로 가져오지 않는다. `management_launcher.py`는 스크립트 인자를 전달하며 서비스 명령의 별도 CLI를 만들지 않는다.
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

맵 배치·통행 원본은 `slime-assets/assets/maps/`이며 등록부 해시를 확인해 직접 읽는다. 관리도구의 `/management/map-assets/maps/<id>`는 요청 시 원본 YAML을 해석하며 맵 JSON 사본을 보관하지 않는다. 타일 이미지도 `/management/map-assets/files/assets/tiles/...`에서 등록된 원본을 직접 제공한다. 백엔드는 같은 맵 원본을 읽어 버전이 있는 게임 API로 제공한다.


검수 빌드는 게임의 60px 블록을 화면 표현 기준인 80px로만 정규화한다. 원장 배치·층수·블록 계층은 변경하지 않는다.

## 공용 이미지 처리

[이미지 엣지 검출·보더 크롭](common/image_borders.md)은 타일 외에도 검은 프레임을 가진 불투명 RGB/RGBA 이미지에서 재사용할 수 있다. 원본 경계 검출과 크롭·보더 계산을 별도 모듈로 관리하며 저장·등록은 호출자가 담당한다.

### 맵 타일 원본 참조

맵 검수의 `assets/world/isloon/tile-catalog.yaml`에서 `asset`은 `slime-assets` 기준 등록 경로다. 블록 맵과 기존 맵 게시기는 공용 `common/map_tile_assets.py`를 통해 에셋 저장소의 등록부·버전·SHA-256을 검증하고 원본을 직접 복사한다. 기본 경로는 형제 저장소 `slime-assets`이며 `SLIME_ASSETS_ROOT`로 지정할 수 있다. 누락·미등록·해시 불일치는 즉시 실패한다. 프론트엔드 이미지로 대체하지 않는다.

게시한 텍스처 메타데이터에 원본 저장소·경로·관리 ID·버전·해시를 보존한다. 브라우저는 게시된 정적 사본을 사용한다. 캐릭터와 렌더링 수치의 기존 전달 경로는 맵 타일 원본과 구분한다. 건물별 타일 선택은 마을 공통 선택보다 우선하며, 돌온재 길드회관은 `stonewarm-guild-red-stone-roof`를 사용한다. 원본 또는 카탈로그 변경 후 검수 패키지를 다시 게시해야 한다.

마른 개울(`dry-creek`) 필드도 에셋 저장소 원본을 직접 검수한다. 선인장(`cactus`)은 진입 불가이며 원본은 에셋 저장소의 `assets/tiles/terrain/blocked/cactus-v1.png`이다. 맵 응답의 `provenance`에 원본 등록 경로·버전·해시를 표시한다.
