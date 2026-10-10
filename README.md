# slime-workflow

로컬 GPU 기반 모션·이미지 생성, 제작 자산과 검수 도구를 관리한다. 모션·포즈 준비는 HY-Motion, 단일 포즈 변환은 VNCCS를 사용한다. MoMask + AnyPose 생성 구조는 폐기했다.

## 생성기별 소스

- `generators/hy_motion/`: HY-Motion 모션 생성·ANNY 변환·방향별 렌더·OpenPose 출력.
- `generators/image/`: Qwen 이미지 생성·VNCCS 단일 포즈 변환.
- `generators/animation/`: 참조 자산 설정·공용 Qwen 실행·기존 시트 검수 도구. AnyPose 생성은 폐기.
- `generators/momask/`: HY-Motion 등이 재사용하는 리타기팅·스키닝·Blender 공용 코드. MoMask 생성·재렌더 경로는 폐기.
- `generators/terrain/`: 고정 Qwen-Image-Edit-2511 기반 바닥·벽 타일 후보와 높이 변화 미리보기 생성.
- `workflows/`: 현재 작업의 실행 순서·입출력·검증 절차.
- `old/`: 이전 노드·음악 파이프라인·실험 생성기와 해당 문서·테스트. 현재 실행 경로에서 사용하지 않는다.

[캐릭터 애니메이션 제작 절차](workflows/character-animation.md)를 따른다.
[Qwen 맵 타일 생성 워크플로우](workflows/map-tile-generation.md)는 환경 타일 후보를 생성·검수한다.

## 보관 경로

- `report/`: 외부 공유용 특정 실험의 이력과 결과 사본. 실행 과정, 입력·파라미터·출처, 검증 결과, 재현 코드 및 확인에 필요한 산출물 사본을 실험별로 묶는다. 원본 제작 자산이나 게임 런타임 채택을 대체하지 않는다. [리포트 목록과 보관 기준](report/README.md)을 참고한다.
- `.model/`: 모델 다운로드·캐시.
- `assets/`: 승인 모션·리그·외형 참조와 출처 기록. 임시 정리 대상 아님.
- `.tmp/test/<실험명>/<YYYY-MM-DD_HH-mm-ss>/`: 한국 시간 기준 실행별 후보 이미지·포즈·프롬프트·로그·출처. Git 제외.
- 정식 채택된 캐릭터·몬스터 스프라이트의 관리 원본: `slime-assets/assets/sprites/`. 맵 타일은 `slime-assets/assets/tiles/`. 명시적 채택 후 등록·전달하며 프론트엔드 사본을 직접 편집하지 않는다.
- 기획·설계: 비공개 `slime-backend/docs/design/`.
- 사용자 지시로 이전한 제작 프롬프트: [prompts/](prompts/README.md). 그 밖의 비공개 프롬프트는 기존 백엔드 경로를 유지한다.

모델 준비·GPU 추론은 샌드박스 밖에서 실행한다. CPU 추론이나 준비 실패 시 대체 실행은 허용하지 않는다. 게임 런타임·AWS 배포 변경은 없다.

## 모션·포즈 변환과 캐릭터 기준

[HY-Motion](workflows/hy-motion.md)에서 모션·ANNY 렌더·OpenPose를 준비하고 [VNCCS 포즈 변환](workflows/pose-transfer.md)에서 외형·포즈 두 참조로 단일 이미지를 생성한다. 별도의 도구·생성 ID를 사용하며 통합 프레임 배치 생성은 제공하지 않는다.

등록된 기본 제작 모션은 [HY-Motion 걷기 v2](assets/motion-sheet/hy-motion-walking-v2/README.md)다. 원본 9~43번의 35프레임·30FPS 및 4방향 원근투영을 사용한다. 과거 8프레임·150ms 규격을 신규 모션에 일괄 적용하지 않는다. 선택·해시·검수·패킹은 [캐릭터 애니메이션 제작 절차](workflows/character-animation.md)를 따른다.

[스탠딩 시트 제작 절차](workflows/character-standing-sheet.md)는 승인 베이스라인을 사용하는 별도 이미지젠 제작 경로다. 로컬 VNCCS 포즈 변환과 구분하며 [이미지젠 최소 사용 정책](workflows/imagegen-usage-policy.md)을 적용한다.

폐기된 MoMask·AnyPose 명령과 보존 범위는 [관리도구 클라이언트 가이드](workflows/management-clients.md#momask-포즈-생성기-폐기)에 명시한다. 기존 스프라이트·앵커 편집은 유지한다.

## 공통 웹 검수

`tools/review/serve.py`가 앵커·리그·Depth·오버레이 페이지를 제공한다. 생성기별 임시 서버 대신 [공통 검수 절차](workflows/asset-review.md)를 사용한다.

### 관리도구 실행 스크립트

저장소 루트에서 실행한다. 환경 준비와 서버 실행은 분리되어 있으며, GUI와 게이트웨이는 각각 별도 터미널에서 실행한다.

| 스크립트 | 역할 | 기본값 |
| --- | --- | --- |
| [setup_management.sh](scripts/setup_management.sh) | 가상환경 생성·환경별 의존성 설치 | `.venv`, `.venv-management` |
| [run_management_gateway.sh](scripts/run_management_gateway.sh) | 명령 게이트웨이·작업 서비스 실행, `--watch` 지원 | `127.0.0.1:8771` |
| [run_management_gui.sh](scripts/run_management_gui.sh) | GUI·정적 검수·API 중계 실행 | `127.0.0.1:8770` |
| [watch_review_server.sh](scripts/watch_review_server.sh) | 기존 watch 명령의 호환 진입점 | `run_management_gui.sh --watch` |

최초 준비 또는 의존성 변경 시 서버를 종료한 상태에서 준비 스크립트를 실행한다. 실행 스크립트는 패키지를 자동 설치하지 않으며, 환경이 없으면 준비 명령을 안내하고 실패한다.

```bash
./scripts/setup_management.sh
```

`.venv`에는 루트 `requirements.txt`의 검수 의존성만 설치하고, Gradio는 `.venv-management`에 `tools/review/ui/gradio/requirements.txt`로 설치한다. GPU 모델 환경에 GUI 의존성을 설치하면 `transformers`와 `huggingface-hub` 버전이 충돌할 수 있다. 모델별 추론 의존성 준비는 기존 생성기 절차를 따른다.

터미널 1에서 게이트웨이를 시작한다. GPU 작업을 접수하려면 GPU 접근이 가능한 샌드박스 밖에서 실행한다.

```bash
./scripts/run_management_gateway.sh
```

게이트웨이 코드 변경도 자동 반영하려면 터미널 1의 명령에 `--watch`를 추가한다.

```bash
./scripts/run_management_gateway.sh --watch
```

게이트웨이·공용 서비스·도메인 코드와 작가 작업 공간 설정을 감시하며 GUI·생성 기록은 제외한다. 변경이 0.5초 동안 안정되면 게이트웨이만 재시작한다. 독립 GPU 대기·실행 프로세스는 유지하지만 작가 에이전트 작업은 기존 종료 정책을 따른다. 시작 실패 시 반복 재시도하지 않고 원인을 출력한 뒤 종료한다.

터미널 2에서 GUI를 시작한다. `--watch`를 생략하면 변경 감시 없이 실행한다.

```bash
./scripts/run_management_gui.sh --watch
```

[관리도구 열기](http://127.0.0.1:8770/). 기본 GUI는 인접 `slime-frontend`의 UI 검수 빌드를 확인하며, 입력이 바뀌었거나 빌드 사본이 없으면 `npm run build:review`를 실행한다. 기본 관리 화면에는 프론트엔드 저장소와 npm 환경이 필요하다. 기존 검수 폴더만 제공하려면 `--root`를 사용한다.

GUI 없이 게이트웨이만 실행해도 통합 CLI를 사용할 수 있다. 아래 명령은 생성 이력을 조회한다.

```bash
python3 tools/manager.py command hy-motion history
```

#### 포트·경로 변경

게이트웨이 포트를 바꾸면 GUI·CLI의 접속 주소도 함께 지정한다. 다음 서버 명령은 각각 별도 터미널에서 실행한다.

```bash
# 게이트웨이 터미널
./scripts/run_management_gateway.sh --port 9871

# GUI 터미널
./scripts/run_management_gui.sh --port 9870 --gateway-url http://127.0.0.1:9871 --watch

# CLI 터미널
python3 tools/manager.py command hy-motion --server-url http://127.0.0.1:9871 history
```

| 환경 변수 | 적용 대상·기본값 |
| --- | --- |
| `VIRTUAL_ENVIRONMENT_PATH` | 서버 Python 환경 · `.venv` |
| `MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH` | Gradio 자식 프로세스 환경 · `.venv-management` |
| `REVIEW_SERVER_PORT` | GUI 포트 · `8770` |
| `MANAGEMENT_GATEWAY_PORT` | 게이트웨이 포트 · `8771` |
| `SLIME_MANAGEMENT_GATEWAY_URL` | GUI·CLI 접속 주소 · `http://127.0.0.1:8771` |
| `FRONTEND_REPOSITORY_PATH` | GUI 기본 프론트엔드 · 인접 `slime-frontend` |

명시적인 포트·접속 옵션이 환경 변수보다 우선한다. `--root`, `--walking`, `--frontend-repo`를 지정하면 `FRONTEND_REPOSITORY_PATH`를 사용하지 않는다. 스크립트에 전달한 상대 경로는 저장소 루트 기준이다. 서버 Python 환경 설정은 GPU 모델 실행기의 기존 환경 정책을 변경하지 않는다.

```bash
# 다른 프론트엔드 경로로 GUI 실행
./scripts/run_management_gui.sh --frontend-repo /경로/slime-frontend --watch

# 기존 검수 폴더만 제공
./scripts/run_management_gui.sh --root .tmp/검수폴더 --entry overlay-review.html

# 작가 작업 공간 설정은 게이트웨이에 전달
./scripts/run_management_gateway.sh --writer-agent-config .local/writer-agent/workspace.yaml

# 실행 옵션 확인
./scripts/run_management_gateway.sh --help
./scripts/run_management_gui.sh --help
```

#### 종료·재시작·로그

`Ctrl+C`는 해당 터미널에서 시작한 서버와 같은 프로세스 그룹의 자식만 종료한다. GUI 재시작은 게이트웨이를 재시작하지 않으며, 독립 GPU 대기·실행 프로세스와 기존 생성 기록은 유지한다. 게이트웨이 코드 변경은 `--watch` 실행 시 자동 반영하며, 일반 실행에서는 게이트웨이 터미널에서 종료 후 다시 실행한다. 재시작 중 접수·조회는 잠시 중단될 수 있으므로 실패한 생성 요청은 이력을 확인한 뒤 다시 접수한다. 작가 에이전트는 기존 정책에 따라 게이트웨이 종료 시 작업도 종료한다.

- 실행 스크립트 로그: `.tmp/management-launcher-logs/`
- 게이트웨이 로그: `.tmp/gateway-server-logs/`
- GUI 서버 로그: `.tmp/review-server-logs/`
- Gradio 로그: `.tmp/manager-current/gradio.log`

실행기는 5초마다 heartbeat를 출력하며, 실패 시 원인·실행 명령과 최근 로그를 표시한다. 게이트웨이의 `GET /management/health`는 역할·PID·응답 상태를 제공하고 GUI의 같은 경로는 중계 상태를 확인한다. 자세한 계약은 [관리도구 클라이언트 가이드](workflows/management-clients.md#독립-실행)를 따른다.

### 게임 UI · 디자인 시스템 검수

프론트엔드 저장소에서 먼저 독립 검수 빌드를 만든다. 이 빌드는 게임 배포물에 포함하지 않으며, 실제 API 요청을 보내지 않는다.

```bash
cd /경로/slime-frontend
npm run build:review

cd /경로/slime-workflow
./scripts/run_management_gui.sh --ui-bundle /경로/slime-frontend/.tmp/한국시간/ui-review
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
| 가상 지면 | 앵커 미리보기에 240 × 120px 마름모 타일과 타원형 그림자 표시 |
| 실행 결과 | 워크플로우 `.tmp/한국시간/`에 검수용 사본·출처·로그 생성 |

검색창에서 **한국어 이름, 애니메이션 ID, 검수 종류, 실행 날짜**를 검색한다. `등록 애니메이션`·`타일 후보 · 지정 맵 적용`·`게임 UI · 디자인 시스템` 분류로 좁힐 수 있다. 검색 결과를 선택하거나 Enter를 누르면 열린다. Escape는 검색어를 지우고, **검색 초기화**는 분류까지 초기화한다. 결과가 없어도 현재 검수 화면과 편집값은 유지된다.

현재 위치 표시줄에는 분류·항목명과 검색 결과 내 순서를 표시한다. **이전·다음**은 현재 검색 결과 안에서 이동하며 목록 끝에서는 비활성화된다. 현재 항목이 필터에서 제외되면 **현재 항목 찾기**로 검색·분류를 초기화할 수 있다. 브라우저 뒤로·앞으로 이동은 항목과 당시 검색 조건을 복원하며 편집값을 유지한다. **검색·목록 접기**로 검수 공간을 넓히고, 파일 경로·ID는 **원본 정보**를 펼쳐 확인한다.

기존 걷기 비교·앵커·리그·OpenPose·Depth·오버레이 페이지도 같은 관리 화면에서 연다. 이전 관리도구 스냅샷은 재수집하지 않는다. 검수 HTML이 없는 미등록 이미지는 프레임이나 좌표를 추정하지 않는다. 이미지가 추가되거나 원본이 바뀌면 서버를 종료하고 다시 실행해 새 스냅샷을 만든다.

앵커 미리보기의 가상 타일은 원본 픽셀 기준으로 너비를 32–600px의 짝수로 조절하면 높이는 2:1 비율로 자동 계산된다. 그림자 너비·높이는 타일의 각각 50%로 함께 확대·축소된다. 타일과 그림자는 각각 켜고 끌 수 있으며 게임 타일·앵커·저장 데이터에는 영향을 주지 않는다. 기존 일반 HTML 검수는 해당 페이지의 조작 기능을 유지한다.

메뉴를 전환해도 편집 상태는 유지된다. 새로고침·종료 전에는 **좌표 JSON 다운로드**를 눌러 내려받는다. 프론트엔드 원본이나 게임 에셋에 자동 적용하지 않는다. 원본 소수 앵커는 유지한다.

#### 필요한 경우에만 옵션 지정

```bash
# 프론트엔드가 다른 위치에 있을 때
./scripts/run_management_gui.sh --frontend-repo /경로/slime-frontend

# 기본 포트가 사용 중일 때
./scripts/run_management_gui.sh --port 8780

# 이미 생성한 관리도구 또는 개별 검수 폴더를 그대로 열 때
./scripts/run_management_gui.sh --root .tmp/검수폴더

# 개별 검수 폴더의 다른 진입 페이지
./scripts/run_management_gui.sh --root .tmp/검수폴더 --entry overlay-review.html

# 특정 걷기·스탠딩 후보만 묶을 때
./scripts/run_management_gui.sh --walking .tmp/걷기실행폴더 --standing .tmp/스탠딩검수폴더
```

`--frontend-repo`, `--root`, `--walking/--standing`은 함께 사용할 수 없다. `--entry`는 `--root` 모드에서 지정한다. 기본 저장소가 없거나 포트가 사용 중이면 원인을 표시하고 종료한다. 임의의 저장소·다른 포트로 자동 전환하지 않는다.

방향별 시트는 같은 폴더 `source.json`의 `sheets`, 단일 시트는 `<이름>.animation.json`과 `<이름>.png`를 연결한다. 여러 버전은 모두 표시한다. 새 애니메이션은 한국어 라벨도 등록해야 한다. 잘못된 메타데이터·누락 파일·시트 해시 및 크기 불일치·누락 또는 중복 라벨은 서버 시작 전에 실패한다. 상세 계약은 [공통 검수 절차](workflows/asset-review.md)를 참고한다.

관리도구는 검색 목록에서 대상을 고르고 미리보기 옆에서 좌표를 편집합니다. 상단 변경 이력에서 실행 취소·다시 실행을 할 수 있고, `현재 프레임 원본 복원`도 실행 취소할 수 있습니다. `좌표 JSON 다운로드`는 브라우저에 파일 다운로드를 요청하며 원본 에셋에 자동 반영하지 않습니다. 변경된 대상은 목록에 표시됩니다. 입력란 밖에서 Ctrl/Cmd+Z는 실행 취소, Ctrl/Cmd+Shift+Z는 다시 실행입니다.

## 포즈 오류 프레임과 ANNY 검수

[캐릭터 애니메이션 제작·검수](workflows/character-animation.md)에 따라 외형·포즈 참조와 결과를 같은 방향·원본 프레임 번호로 비교한다. 오류 프레임은 VNCCS에서 별도로 검수·재생성하며 AnyPose로 대체하지 않는다. 반복 재생·작업 완료는 루프 품질이나 최종 에셋 채택을 뜻하지 않는다.

현행 ANNY 모션 변환·렌더는 [HY-Motion 안내](workflows/hy-motion.md), 관절·기준점 검수는 [해부학 리타기팅 안내](workflows/anny-anatomical-retarget.md)를 따른다. [과거 ANNY 마네킹 문서](workflows/anny-mannequin-generation.md)는 공용 리타기팅 설명과 과거 제작 기록을 구분한다. 폐기된 mannequin·MoMask 버전을 현재 기본 참조로 안내하지 않는다.

## 작가 AI 에이전트

관리도구의 [작가 AI 실행 안내](workflows/writer-agent.md)를 통해 문서를 RAG로 학습하고, 아이디어의 작성 위치·본문과 중복 정리안을 검토·적용한다. 검색 근거와 변경 차이·실행 기록을 관리 화면에서 조회한다.
