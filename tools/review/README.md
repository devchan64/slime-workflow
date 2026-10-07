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
     gateway_watch.py            게이트웨이 소스 감시·변경 안정화·순차 재시작
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

게임 UI 검수의 신규·수정 작업은 [공용 렌더링 전환 기준](../../workflows/management-ui.md#게임-ui-검수의-렌더링-기준)을 따른다. 게임과 동일한 렌더링 라이브러리를 재사용하고, 프론트엔드 전체 검수 빌드·복사 의존은 단계적으로 줄인다. 필드 지면·고도·결계는 공용 Phaser 렌더러로 전환했으며 마을과 다른 게임 UI의 `build:review` 경로는 아직 전환 전 상태다.

[이미지 엣지 검출·보더 크롭](common/image_borders.md)은 타일 외에도 검은 프레임을 가진 불투명 RGB/RGBA 이미지에서 재사용할 수 있다. 원본 경계 검출과 크롭·보더 계산을 별도 모듈로 관리하며 저장·등록은 호출자가 담당한다.

### 맵 타일 원본 참조

맵 검수의 표시용 매핑 `tools/review/ui/map/config/tile-catalog.yaml`에서 `asset`은 `slime-assets` 기준 등록 경로다. 블록 맵과 기존 맵 게시기는 공용 `common/map_tile_assets.py`를 통해 에셋 저장소의 등록부·버전·SHA-256을 검증하고 원본을 직접 복사한다. 기본 경로는 형제 저장소 `slime-assets`이며 `SLIME_ASSETS_ROOT`로 지정할 수 있다. 누락·미등록·해시 불일치는 즉시 실패한다. 프론트엔드 이미지로 대체하지 않는다.

게시한 텍스처 메타데이터에 원본 저장소·경로·관리 ID·버전·해시를 보존한다. 브라우저는 게시된 정적 사본을 사용한다. 캐릭터와 렌더링 수치의 기존 전달 경로는 맵 타일 원본과 구분한다. 건물별 타일 선택은 마을 공통 선택보다 우선하며, 돌온재 길드회관은 `stonewarm-guild-red-stone-roof`를 사용한다. 원본 또는 카탈로그 변경 후 검수 패키지를 다시 게시해야 한다.

마른 개울(`dry-creek`) 필드도 에셋 저장소 원본을 직접 검수한다. 선인장(`cactus`)은 진입 불가이며 원본은 에셋 저장소의 `assets/tiles/terrain/blocked/sand-cactus-type-a-v1.png`이다. 맵 응답의 `provenance`에 원본 등록 경로·버전·해시를 표시한다.

### 에셋 변경과 GUI 재시작

맵·타일 원본, 에셋 등록부, 프론트엔드 에셋 잠금 목록은 GUI 재시작 감시에서 제외한다. 맵 검수는 화면을 다시 열거나 새로고침할 때 `/management/map-assets/textures`에서 최신 카탈로그·버전·해시를 읽고 맵·이미지를 원본 API로 조회한다. API는 `no-store`로 제공하며 매 요청에서 등록 여부와 SHA-256을 검증한다. 열린 화면에 자동으로 변경을 주입하지 않는다. 소스·UI·생성기 설정 변경의 재시작은 유지한다. 이 규칙은 맵·타일 직접 조회에 적용하며 정적 캐릭터 검수 패키지의 재게시를 대체하지 않는다.

### 필드 공용 렌더링 라이브러리

필드 검수는 게임과 같은 `@slime/field-renderer` 1.0.6와 Phaser 3.90.0을 사용한다. 원본은 `slime-frontend/packages/field-renderer/`이며 `field-surface` 1.0.5의 좌표 계약을 포함한다. `ui/map/vendor/field-renderer/1.0.6/`의 ES 모듈과 엔진 배포본은 `manifest.yaml`의 SHA-256을 게시 전에 검증한다. 게임의 `npm run build:field-renderer`로 만든 배포본만 명시적으로 전달하며 관리도구가 게임 소스를 런타임에 읽거나 게임 전체를 빌드하지 않는다. 배포 후 수정은 새 버전으로 전달한다.

`field-map-renderer.js`는 공용 면 목록을 이용해 범위·클릭 판정만 수행한다. `field-map-view.js`는 Phaser Scene에 에셋과 표시 설정을 연결한다. 실제 지면·암벽·계단·결계탑·오러는 공용 라이브러리가 그리며 별도 Canvas 필드 그리기는 사용하지 않는다. 80×40 타일, 단계당 32px 고도, 16px 외곽 두께를 유지한다. `결계탑 · 결계 오러`와 `메시 경계`로 높이 25px의 외곽 패널·삼각형 분할을 검사한다. 접촉 셀 내부의 오러와 바닥 음영은 생성하지 않는다. 캐릭터 재생·전투 표시·마을 건물은 아직 별도 소비자 구현이다.

맵·타일은 요청 시 등록 원본을 읽으므로 배치·고도·이미지 변경에 프론트엔드 빌드가 필요하지 않다. 결계탑·오러 스프라이트는 등록부 해시를 검증한 검수 사본과 출처를 게시한다. 라이브러리 또는 검수 어댑터 코드 변경은 관리도구 정적 UI 게시 대상이다. 검증은 프론트엔드 `node scripts/run-regression.mjs --with-checks tests/field-renderer.test.mjs tests/elevation.test.mjs tests/field-surface.test.mjs`와 워크플로우 `tools.review.tests.test_map_asset_sources`, `tools.review.tests.test_map_render_profiles`를 사용한다.

### 경비센터 표시 원본

필드맵 검수는 등록된 `assets/ui/guard-centers.yaml`의 도시별 외형과 `assets/sprites/structures/`의 이미지를 해시 검증 후 제공합니다. 도시행 웨이포인트에서 기존 필드 발급 위치를 계산하며, 이미지 URL과 관리 ID·버전·SHA-256을 `guardCenters`에 함께 제공합니다. 게임도 같은 설정을 사용하며 통행 데이터는 변경하지 않습니다.

맵 배치 원본은 `slime-assets/assets/maps/`의 등록 YAML을 직접 검증해 읽습니다. `assets/world`의 과거 맵 사본과 전용 조립기는 폐기했습니다. UI 표시 설정(재질 색상·렌더 크기·타일 별칭)은 `tools/review/ui/map/config/`에서 관리하며 맵 배치 사본을 보관하지 않습니다. `build_map_review.py --map`의 로컬 사본 입력은 명시적으로 거절합니다.

### 마을 캐릭터 시인성 검수

바닥 타일은 에셋 저장소의 128×128 원본을 직접 사용한다. 절벽 면·경사벽·건물은 256×256 기준을 유지한다. 캐릭터 해상도와 타일 배치 크기는 유지하며 화면 전체 바닥 흐림은 사용하지 않는다. 캐릭터는 화면 기준 1px 짙은 외곽선과 밝은 윤곽광을 기본 적용한다. 바닥 대비는 원본이 기본이며 65% 비교 옵션을 제공한다. 이 설정은 마을 검수 전용으로 게임 본편·Phaser 필드에 자동 적용되지 않는다. 사람 중심 100% 버튼은 실제 배율 1을 적용한다.

### 캐릭터 표현 검수

`/?tool=character-review&category=animation-tool`은 등록된 기본 캐릭터의 정면 좌측 대기 첫 프레임을 3×3 반복 바닥 견본 위에 배치합니다. 게임 맵 원본을 추가·변경하지 않는 검수용 절차적 배치입니다. 석판·잔디/들꽃·흙/자갈은 에셋 등록부에서 검증한 타일을 사용합니다.

왼쪽은 외곽선 없는 원본과 기본 접지 그림자, 오른쪽은 선택한 형태선·분리선·접지 그림자 설정입니다. 바닥·위치·회전·배율은 공유하며 초기 배율은 100%입니다. 오른쪽 바닥 클릭으로 캐릭터를 배치하고 드래그로 화면을 이동합니다. 전체 보기는 3×3 전체 범위를 보여주며 실제 크기는 사람 중심·100%로 복귀합니다. 설정은 해당 화면의 검수에만 적용하며 게임 설정을 저장하지 않습니다. 애니메이션 재생·캐릭터 선택은 현재 범위에 포함되지 않습니다.

캐릭터 표현 검수 조정본의 접지 그림자는 중성 회색 `#242424`를 사용합니다. 조정본은 선택한 프로필의 그림자 크기를 유지하고 각 층의 불투명도만 1.2배로 표시합니다. 원본 비교는 기존 색상·크기·농도를 유지합니다.

캐릭터 표현 검수의 형태선은 100% 기준 1px, 회갈색 `#655D54`, 불투명도 100%입니다. 밝은 분리선과 캐릭터 원본의 불투명도는 유지합니다.

캐릭터 표현 검수 캔버스는 표시 크기와 카메라 좌표를 유지하면서 내부 가로·세로 해상도를 각각 2배로 사용합니다. PNG는 내부 픽셀을 보존하므로 표시 영역 768×576의 캡처는 1536×1152입니다.

필드 탐색 검수는 `?tool=map-review-meadow&category=field-map-review`로 통합한다. 폐기한 프론트엔드 `review/terrain-preview.html`은 게시하지 않는다. 게임에서 빌드한 `game-render-profile.mjs`의 내부 해상도·캐릭터 외곽선·접지 그림자를 적용하며, 지형 윗면·계단·측벽·도로 외곽은 화면 2px 경계선을 공유한다. 바닥 대비와 캐릭터 시인성 실험 컨트롤은 필드 맵 검수에 제공하지 않는다.
