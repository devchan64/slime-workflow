# slime-workflow

현재 사용하는 MoMask 모션 생성기와 캐릭터 애니메이션 생성기를 관리한다.

## 생성기별 소스

- `generators/momask/`: CUDA MoMask 관절 모션 생성. SMPL 의존성 없음.
- `generators/animation/`: 기본 리그 검증, 4방향 포즈·Depth 렌더, 참조 준비, Qwen 프레임 생성.
- `generators/terrain/`: 고정 Qwen-Image-Edit-2511 기반 바닥·벽 타일 후보와 높이 변화 미리보기 생성.
- `workflows/`: 현재 작업의 실행 순서·입출력·검증 절차.
- `old/`: 이전 노드·음악 파이프라인·실험 생성기와 해당 문서·테스트. 현재 실행 경로에서 사용하지 않는다.

[캐릭터 애니메이션 제작 절차](workflows/character-animation.md)를 따른다.
[Qwen 맵 타일 생성 워크플로우](workflows/map-tile-generation.md)는 환경 타일 후보를 생성·검수한다.

## 보관 경로

- `.model/`: 모델 다운로드·캐시.
- `assets/`: 기존 승인 리그와 재사용 MoMask 모션. 임시 정리 대상 아님.
- `.tmp/YYYY-MM-DD_HH-mm-ss/`: 한국 시간 기준 실행별 후보 이미지·포즈·프롬프트·로그·출처. Git 제외.
- 정식 채택된 이미지의 관리 원본: `slime-frontend` 에셋 경로. 명시적 채택 후 전달·등록한다.
- 기획·설계: 비공개 `slime-backend/docs/design/`.
- 사용자 지시로 이전한 제작 프롬프트: [prompts/](prompts/README.md). 그 밖의 비공개 프롬프트는 기존 백엔드 경로를 유지한다.

모델 준비·GPU 추론은 샌드박스 밖에서 실행한다. CPU 추론이나 준비 실패 시 대체 실행은 허용하지 않는다. 게임 런타임·AWS 배포 변경은 없다.

## 기본 걷기 참조

걷기는 방향당 8프레임·150ms·1.2초 루프다. 개별 animation-loops 자산은 삭제하고 `assets/pose-sheets/`의 방향별 시트 4장을 유지한다. 출처·배치·해시는 `generators/animation/config/default_walk_pose_sheets.yaml`에서 관리한다.

## 캐릭터 기준 시트

걷기 이미지젠의 동작 참조 원본은 셰이딩을 보강한 리그 8프레임 시트다. 이미지젠은 [최소 사용 정책](workflows/imagegen-usage-policy.md)에 따라 포즈 검수를 통과한 선택 프레임에만 사용한다. 호출당 최대 4프레임만 생성하며, 1–4번·5–8번 리그를 각각 2×2 참조로 나누어 생성한 뒤 4방향 총 32프레임을 최종 4×4 시트 두 장으로 통합한다. 전체 생성·검수·정규화·시트 패킹 규칙은 [캐릭터 애니메이션 생성 규칙](workflows/character-animation.md)에 따른다. `assets/pose-sheets/five-head-walk-8f/v1/`의 OpenPose 시트는 비교 자료로 유지한다. `generators/animation/build_walk_pose_sheets.py`가 렌더 실행 폴더의 8프레임 포즈를 묶고 출처·파일 해시를 기록한다.

[캐릭터 애니메이션 생성 규칙](workflows/character-animation.md)은 신규 캐릭터의 2×2 베이스라인과 최종 애니메이션 생성·검수·정규화를 함께 정의한다. 단일 원화 생성 후 시트로 재생성하는 단계를 기본 경로에서 제거했다.

[스탠딩 시트 제작 절차](workflows/character-standing-sheet.md)는 승인된 2×2 베이스라인 시트 전체를 참조하여 방향별 4프레임의 4×1 소스 시트 4장을 생성하고 최종 프론트엔드 전달 시에는 16프레임을 4×4 한 장으로 패킹한다. 호출당 최대 4프레임 기준을 적용하고 입력 베이스라인 셀과 출력 방향의 대응을 명시한다. 정식 에셋 교체는 사용자 채택 후 수행한다.

## 공통 웹 검수

`tools/review/serve.py`가 앵커·리그·Depth·오버레이 페이지를 제공한다. 생성기별 임시 서버 대신 [공통 검수 절차](workflows/asset-review.md)를 사용한다.

### 워크프레임 관리도구 시작

워크플로우 저장소 루트에서 옵션 없이 실행한다. 시작 전에 프론트엔드에서 `npm run build:review`를 실행해 검증 가능한 UI 검수 빌드를 만든다. 기본 실행은 최신 UI 빌드를 자동으로 포함하므로 애니메이션·타일·게임 UI·기존 웹 검수를 하나의 목록에서 제공한다. Python 환경에 Pillow와 PyYAML이 필요하다.

```bash
python3 tools/review/serve.py
```

[관리도구 열기](http://127.0.0.1:8770/) · 종료는 `Ctrl+C`다.

### 게임 UI · 디자인 시스템 검수

프론트엔드 저장소에서 먼저 독립 검수 빌드를 만든다. 이 빌드는 게임 배포물에 포함하지 않으며, 실제 API 요청을 보내지 않는다.

```bash
cd /경로/slime-frontend
npm run build:review

cd /경로/slime-workflow
python3 tools/review/serve.py --ui-bundle /경로/slime-frontend/.tmp/한국시간/ui-review
```

관리도구의 `게임 UI · 디자인 시스템` 분류에서 토큰·기본 컴포넌트, 탐색 메뉴·패널, 캐릭터 설정 대화상자, 전투 레이아웃을 연다. 화면 크기(데스크톱·모바일 세로·모바일 가로), 언어, 초기 상태 복원을 제공한다. 가져오기 전 manifest의 버전·경로·해시를 검증하고 검증된 파일만 관리도구 실행 폴더에 복사한다. 프론트엔드 개발 서버나 소스 경로는 관리도구의 런타임 의존성이 아니다.

### Qwen 타일 후보 검수

Qwen 타일 생성기는 `.tmp/실행폴더/tile-review.json`에 역할별 타일·높이 미리보기·티켓·모델·해시를 남긴다. 옵션으로 전달한 `map-preview.yaml`에는 특정 맵과 적용할 `targetCells`를 기록한다. 관리도구의 기본 실행은 이 기록을 자동 탐색해 **타일 후보 · 지정 맵 적용** 분류에 추가한다. 반복 미리보기와 높이 변화, 지정 셀에 후보 타일을 적용한 등각 맵을 함께 확인한다. 후보·맵 스냅샷은 검수 사본이며 프론트엔드 에셋을 바꾸지 않는다.

기본값은 서버 코드 위치를 기준으로 찾으므로 다른 작업 디렉터리에서 스크립트의 절대 경로로 실행해도 같다.

| 항목 | 기본 동작 |
| --- | --- |
| 프론트엔드 | 워크플로우 저장소와 같은 상위 폴더의 `slime-frontend` |
| 접속 주소 | `http://127.0.0.1:8770/` |
| 애니메이션 | `src/assets/**/*.animation.json`에서 시트·프레임·앵커·버전·재생 시간 탐색 |
| 한국어 이름 | `src/assets/animation-labels.yaml`의 `animationId` → `displayNameKo` |
| 기존 웹 검수 | 워크플로우 `.tmp/실행폴더/*.html`, `.result/실행폴더/*.html`, `assets/` 하위 HTML 자동 통합 |
| 가상 지면 | 앵커 미리보기에 240 × 120px 마름모 타일과 타원형 그림자 표시 |
| 실행 결과 | 워크플로우 `.tmp/한국시간/`에 검수용 사본·출처·로그 생성 |

검색창에서 **한국어 이름, 애니메이션 ID, 검수 종류, 실행 날짜**를 검색한다. `등록 애니메이션`·`기존 웹 검수` 분류로 좁힐 수 있다. 검색 결과를 선택하거나 Enter를 누르면 열린다. Escape는 검색어를 지우고, **검색 초기화**는 분류까지 초기화한다. 결과가 없어도 현재 검수 화면과 편집값은 유지된다.

현재 위치 표시줄에는 분류·항목명과 검색 결과 내 순서를 표시한다. **이전·다음**은 현재 검색 결과 안에서 이동하며 목록 끝에서는 비활성화된다. 현재 항목이 필터에서 제외되면 **현재 항목 찾기**로 검색·분류를 초기화할 수 있다. 브라우저 뒤로·앞으로 이동은 항목과 당시 검색 조건을 복원하며 편집값을 유지한다. **검색·목록 접기**로 검수 공간을 넓히고, 파일 경로·ID는 **원본 정보**를 펼쳐 확인한다.

기존 걷기 비교·앵커·리그·OpenPose·Depth·오버레이 페이지도 같은 관리 화면에서 연다. 이전 관리도구 스냅샷은 재수집하지 않는다. 검수 HTML이 없는 미등록 이미지는 프레임이나 좌표를 추정하지 않는다. 이미지가 추가되거나 원본이 바뀌면 서버를 종료하고 다시 실행해 새 스냅샷을 만든다.

앵커 미리보기의 가상 타일은 원본 픽셀 기준으로 너비를 32–600px의 짝수로 조절하면 높이는 2:1 비율로 자동 계산된다. 그림자 너비·높이는 타일의 각각 50%로 함께 확대·축소된다. 타일과 그림자는 각각 켜고 끌 수 있으며 게임 타일·앵커·저장 데이터에는 영향을 주지 않는다. 기존 일반 HTML 검수는 해당 페이지의 조작 기능을 유지한다.

메뉴를 전환해도 편집 상태는 유지된다. 새로고침·종료 전에는 **좌표 JSON 다운로드**를 눌러 내려받는다. 프론트엔드 원본이나 게임 에셋에 자동 적용하지 않는다. 원본 소수 앵커는 유지한다.

#### 필요한 경우에만 옵션 지정

```bash
# 프론트엔드가 다른 위치에 있을 때
python3 tools/review/serve.py --frontend-repo /경로/slime-frontend

# 기본 포트가 사용 중일 때
python3 tools/review/serve.py --port 8771

# 이미 생성한 관리도구 또는 개별 검수 폴더를 그대로 열 때
python3 tools/review/serve.py --root .tmp/검수폴더

# 개별 검수 폴더의 다른 진입 페이지
python3 tools/review/serve.py --root .tmp/검수폴더 --entry overlay-review.html

# 특정 걷기·스탠딩 후보만 묶을 때
python3 tools/review/serve.py --walking .tmp/걷기실행폴더 --standing .tmp/스탠딩검수폴더
```

`--frontend-repo`, `--root`, `--walking/--standing`은 함께 사용할 수 없다. `--entry`는 `--root` 모드에서 지정한다. 기본 저장소가 없거나 포트가 사용 중이면 원인을 표시하고 종료한다. 임의의 저장소·다른 포트로 자동 전환하지 않는다.

방향별 시트는 같은 폴더 `source.json`의 `sheets`, 단일 시트는 `<이름>.animation.json`과 `<이름>.png`를 연결한다. 여러 버전은 모두 표시한다. 새 애니메이션은 한국어 라벨도 등록해야 한다. 잘못된 메타데이터·누락 파일·시트 해시 및 크기 불일치·누락 또는 중복 라벨은 서버 시작 전에 실패한다. 상세 계약은 [공통 검수 절차](workflows/asset-review.md)를 참고한다.

관리도구는 검색 목록에서 대상을 고르고 미리보기 옆에서 좌표를 편집합니다. 상단 변경 이력에서 실행 취소·다시 실행을 할 수 있고, `현재 프레임 원본 복원`도 실행 취소할 수 있습니다. `좌표 JSON 다운로드`는 브라우저에 파일 다운로드를 요청하며 원본 에셋에 자동 반영하지 않습니다. 변경된 대상은 목록에 표시됩니다. 입력란 밖에서 Ctrl/Cmd+Z는 실행 취소, Ctrl/Cmd+Shift+Z는 다시 실행입니다.

## 걷기 오류 프레임 해결

리그 참조에서 다리 연결이 뒤바뀌는 프레임은 [캐릭터 애니메이션 생성 규칙](workflows/character-animation.md)의 오류 프레임 재생성·정규화 절차를 따른다. Qwen에는 캐릭터 방향 크롭과 OpenPose를, 이미지젠에는 검수된 포즈와 2×2 베이스라인 전체를 전달한다.

[캐릭터 애니메이션 생성 규칙](workflows/character-animation.md)은 리그/OpenPose 독립 참조, 기본 포즈 프롬프트, Qwen 생성, AnyPose 오류 프레임 재생성을 함께 정의한다.

[캐릭터 애니메이션 생성 규칙](workflows/character-animation.md)을 캐릭터 애니메이션의 상위 제작 절차로 사용한다. 포즈 적용부터 외형 복원·시트 통합까지 실행을 연결하고 검수 근거로 다음 버전을 개선한다.

[AnyPose 오류 프레임 재생성](workflows/character-animation.md): 고정 어댑터 해시 검증, 방향별 리그 참조, 4스텝 실행기를 제공한다. Qwen 포즈 전환은 OpenPose 참조 경로를 사용한다.

[Qwen 맵 타일 생성 워크플로우](workflows/map-tile-generation.md): 맵 타일은 Qwen으로 생성하고, 반복 이음새·역할·알파·결정적 패킹을 검수한다. 이미지젠은 타일 기본 경로에 사용하지 않는다.

## 세계관 문서 작업

[로컬 문서 작성·수정 관리도구](workflows/worldbuilding.md)는 기존 비공개 문서를 참고하여 자연어 업무 지시를 수행한다. 환경 준비·고정 Qwen 모델 다운로드·문서 생성/추가/교체·출처·변경 이력·되돌리기를 제공한다. 실행은 GPU 호스트의 샌드박스 밖에서 수행한다.

```bash
python3 tools/review/serve.py --worldbuilding-only
```

`http://127.0.0.1:8770/worldbuilding/`에서 지시를 입력한다. 연결 설정은 Git 제외 경로인 `.local/worldbuilding/workspace.yaml`에 관리한다.
