# slime-workflow

로컬 GPU 기반 이미지·모션·음향 제작과 게임 에셋 검수를 위한 생성기 및 워크플로우다. 생성 결과는 후보이며 검수와 명시적인 채택을 거쳐 에셋 저장소에 등록한다.

관리 GUI 소스는 [gui/](gui)에 있다. [app.jsx](gui/app.jsx)가 헤르메스 대화와 생성기·검수 화면의 진입점이다. `gui/dist/`는 Git에서 관리하지 않는 빌드 산출물이다. 새 저장소를 준비할 때 저장소 루트에서 `npm ci --prefix gui`와 `npm run build --prefix gui`를 실행해야 관리 서버가 제공하는 번들이 생성된다. GUI 소스를 수정한 뒤에는 `npm run build --prefix gui`로 번들을 갱신한다. `./scripts/workflow.sh gui --watch`는 시작할 때 자동으로 빌드한다.

## 시작하기

`scripts/` 디렉터리의 공통 진입점은 `./workflow.sh`다. 관리 환경이 준비되어 있으면 이 디렉터리에서 **`./workflow.sh start`** 한 줄로 게이트웨이와 관리 화면을 시작한다. 전체 명령 목록은 `./workflow.sh --help`로 확인한다.

저장소 루트에서 관리 환경을 준비하고 상태를 확인한 뒤 시작한다. 렌더러와 생성기 GPU 환경·모델은 필요한 경우 아래 선택 준비 명령으로 따로 준비한다. 게이트웨이는 GPU에 접근할 수 있는 환경에서 실행한다.

```bash
./scripts/workflow.sh setup --scope management
./scripts/workflow.sh doctor
./scripts/workflow.sh start
```

`start`는 두 포트가 비어 있을 때 게이트웨이와 GUI를 독립 실행한다. GUI 변경 감시가 필요하거나 두 서비스를 각각 운영하려면 통합 시작 대신 별도 터미널에서 실행한다.

```bash
# 터미널 1: 명령 게이트웨이와 작업 서비스
./scripts/workflow.sh gateway

# 터미널 2: 워크플로우 GUI
./scripts/workflow.sh gui --watch
```

워크플로우 주소는 [http://127.0.0.1:8770/](http://127.0.0.1:8770/)이며 게이트웨이는 기본적으로 `127.0.0.1:8771`을 사용한다. GUI 없이도 게이트웨이를 통해 통합 CLI를 사용할 수 있다. `gui --help`, `gateway --help`, `test --help`, 검사 목록과 `help <서비스> [명령]`은 관리 가상환경을 설치하기 전에도 확인할 수 있다. 설치 전 서비스 도움말에서 음악 기본값과 표정 프리셋 목록은 생략되며, 관리 환경을 준비한 뒤 다시 확인할 수 있다.

```bash
./scripts/workflow.sh command kimodo history
./scripts/workflow.sh gateway --help
./scripts/workflow.sh gui --help
```

GUI와 CLI는 공용 명령 게이트웨이, 작업 서비스, GPU 대기열과 이력을 공유한다. GUI를 종료해도 독립 작업과 기록은 유지된다. 접수 중 연결이 끊기면 중복 요청 전에 이력을 확인한다. 포트·환경 변수·변경 감시·로그와 명령별 사용법은 [워크플로우 클라이언트 가이드](docs/management-clients.md)를 따른다. GUI 기본 실행에는 인접 `slime-frontend`와 npm 환경이 필요할 수 있다. 렌더러를 새로 준비할 때는 프론트엔드 저장소에서 잠금 파일 기준 `npm ci`를 먼저 실행한다.

공통 구성과 책임, GPU 인계 및 미완료 기능의 구현·검증 기준은 [워크플로우 실행 아키텍처](docs/workflow-execution-architecture.md)를 참고한다.

## 환경 진단과 선택 준비

새 공용 진입점은 기존 실행기와 회귀 실행기를 재사용한다. 진단은 Python 실행 파일·일부 핵심 패키지의 발견 여부, 설정된 로컬 포트 접속 여부와 기존 AMD GPU 상태 조회 결과를 표시하며 패키지 전체 동작·모델 해시·GPU 호환성을 보증하지 않는다. 점유된 관리 포트는 로컬 상태 응답의 역할과 PID를 자체 보고값으로 표시할 수 있으며 실제 소유권 증명은 아니다. GPU 정보를 읽을 수 없으면 유휴 대신 확인 불가로 표시한다. 시스템 RAM의 총량·사용 가능량과 스왑 사용량도 별도로 관측하며 실행 가능 여부를 보장하지 않는다. Python 경로 설정의 실행문은 실행하지 않으며, 실행문 때문에 누락 여부를 확정할 수 없으면 확인 불가로 표시한다. Kimodo는 전용 실행환경 및 경로 설정 대상의 존재를 별도로 확인한다. 이미지·VACE·Animate2는 관리 Python 경로 설정과 별개인 고정 `.venv`의 핵심 패키지 발견 여부를 표시한다. `--dependencies`는 격리 Python에서 pip 검사기를 사용해 이미지·Kimodo·Wan Fun·HeartMuLa·효과음 환경의 설치 메타데이터를 확인하며, site 실행문·읽지 못한 설정·누락 경로가 있으면 결과를 확인 불가로 표시한다. 자체 pip가 없는 환경은 관리 환경의 pip 검사기를 재사용하되 관리 패키지를 대상에 섞지 않는다. Hermes 소스는 고정 리비전·변경 여부를 확인하고 모델은 이전 해시 검증 마커와 파일 속성만 확인한다. 작가 서버 파일은 존재만 확인하며 전체 해시와 GPU 구동은 별도다. `--inventory`는 기존 모델 인벤토리를 재사용해 서비스별 파일 수와 용량을 읽으며, 파일 존재는 다운로드 완료나 해시 검증을 뜻하지 않는다.

```bash
./scripts/workflow.sh doctor
./scripts/workflow.sh doctor --inventory          # 등록 모델의 파일 수·용량 조회
./scripts/workflow.sh doctor --dependencies       # 생성기별 설치 패키지 의존성 검사
./scripts/workflow.sh start                      # 빈 포트에서 게이트웨이·GUI 독립 실행
./scripts/workflow.sh setup --scope writer-runtime --plan # 설치 없이 변경 대상·다운로드 확인
./scripts/workflow.sh setup --scope management  # 관리 Python·FastAPI 서버 의존성 준비
./scripts/workflow.sh setup --scope renderer    # 인접 프론트엔드 렌더러 빌드·설치
./scripts/workflow.sh setup --scope image       # FLUX 및 기존 이미지 ROCm 런타임 준비
./scripts/workflow.sh setup --scope wan-fun-runtime  # Wan Fun ROCm 환경 준비 (Kimodo가 참조할 수 있음)
./scripts/workflow.sh setup --scope sfx-runtime      # 효과음 전용 ROCm 환경만 준비
./scripts/workflow.sh setup --scope kimodo-runtime   # 빈 Kimodo 전용 ROCm 환경 준비
./scripts/workflow.sh setup --scope heartmula-runtime # 빈 HeartMuLa 전용 ROCm 환경 준비
./scripts/workflow.sh setup --scope writer-runtime  # 작가·Hermes 공용 ROCm 서버와 작가 모델
./scripts/workflow.sh setup --scope hermes-runtime  # Hermes 고정 소스와 의존성
./scripts/workflow.sh setup --scope hermes-mcp      # Codex MCP용 별도 환경
./scripts/workflow.sh model list                  # 등록 서비스별 상태·준비 명령 확인
./scripts/workflow.sh model status hermes-model   # 기존 게이트웨이로 상태 조회
./scripts/workflow.sh model prepare hermes-model  # 기존 준비 명령 접수
./scripts/workflow.sh model prepare dwpose        # DWPose 포즈 모델만 준비
./scripts/workflow.sh help hermes-model          # 서비스별 상세 도움말
./scripts/workflow.sh test --list-all            # 등록된 전체 관리 회귀 모듈 확인
./scripts/workflow.sh test --list-group hermes   # 실행 전 모듈 확인
./scripts/workflow.sh test --group hermes        # 등록된 Hermes 관련 회귀만 실행
./scripts/workflow.sh test --group management
./scripts/workflow.sh test --group gpu
```

관리 검사 영역에는 실행기·게이트웨이·단일 포트 외에도 실행 설정, 기존 게이트웨이 인계, GUI·게이트웨이 변경 감시와 시작 검사가 포함된다. `--list-group management`로 실행 전 목록을 확인한다. 영역은 등록된 일부 검사이며 전체 저장소 검사나 실제 GPU·브라우저 검증을 뜻하지 않는다. `--all`은 `--list-all`에 나온 등록 모듈 전체를 뜻하며 저장소의 모든 테스트 파일을 자동 탐색하지 않는다.

`model list`의 `retired`는 사용이 중단된 서비스를 나타낸다. 해당 서비스는 상태·기존 기록 조회를 유지하지만 모델 준비는 제공하지 않는다. 등록된 다른 준비 명령도 실제 사용 가능 여부는 각 서비스 상태에서 확인한다.

`start`는 게이트웨이와 GUI를 독립 세션으로 시작하고 HTTP 응답 및 각 로그 경로를 표시한다. 두 포트 중 하나라도 이미 점유되어 있으면 기존 프로세스를 종료하지 않고 시작을 거부한다. 기동 시 생성한 각 식별값과 서비스 역할을 응답에서 대조하므로 다른 프로세스의 응답을 성공으로 간주하지 않는다. 부분 시작이나 응답 시간 초과 시 이미 시작된 프로세스는 자동 종료하지 않으므로 표시된 로그와 상태를 확인한다. GUI HTTP 응답은 화면 전체 기능 검증을 의미하지 않는다.

공유 `.venv`를 변경하는 설치는 공용 GPU 작업 예약이 남아 있으면 시작을 거절하고, 설치 중에는 별도 예약으로 대기 작업의 시작을 막는다. 대기 작업 취소와 우선순위 변경은 계속 가능하다. 설치 프로세스가 비정상 종료되면 자식 설치 프로세스가 남아 있을 수 있으므로 예약을 자동 삭제하지 않는다. `doctor`에서 예약을 확인하고 호스트의 프로세스·자식 상태를 조사해야 한다. 대기열 밖 작업이나 다른 경로를 통한 수동 설치는 이 보호 범위 밖이다.

설치 중단 후 복구할 때는 출력된 로그와 `.tmp/management-launcher-logs/`의 해당 실행 로그를 먼저 확인한다. `workflow.sh doctor`의 `gpu_reservations`에서 `management-setup` 예약 파일명과 PID를 확인하고 `.tmp/gpu-queue/active/`의 해당 기록을 대조한다. `not_seen_check_host`는 자식 설치 프로세스까지 종료됐다는 뜻이 아니다. 호스트의 설치·빌드 프로세스와 GPU 작업을 확인하고, 모두 종료된 것이 확실할 때만 `.tmp/gpu-queue/execution.lock`에 배타 잠금을 잡은 상태에서 해당 예약 기록을 별도 보존해 해제한다. 다른 예약은 건드리지 않는다. 확인이 불가능하면 예약을 유지한다. 이후 `doctor`와 `setup --scope <범위> --plan`으로 상태를 다시 확인하고 오류 원인을 해결한 뒤 재시도한다. Kimodo·HeartMuLa 등 기존 전용 환경을 거부하는 범위는 남은 디렉터리를 검토·별도 보존해야 새로 준비할 수 있다.

`management` 준비는 모델·GPU 런타임이나 프론트엔드를 설치하지 않는다. GUI 전체와 개별 생성기의 사용 가능 여부는 따로 확인해야 한다. 인자 없는 `workflow.sh setup`은 이전처럼 이미지 환경·관리 환경·렌더러를 함께 준비한다. `image`는 Linux x86_64 Python 3.14, gfx1151과 ROCm 등 기존 제한을 적용하며 FLUX 및 기존 이미지 API import를 확인한다. 실행 중단된 생성기의 지원을 의미하지 않는다. 모델 명령은 기존 서비스의 `prepare` 또는 `download-model`을 호출하며 서비스에 따라 준비 범위가 다르다. 목록은 등록된 명령을 표시할 뿐 실제 사용 가능성을 보장하지 않는다. `prepare: null`과 Qwen 전용 `qwen_archived` 표기를 확인하고, 다른 서비스의 중단·제한과 모델 상태·실행 환경 준비는 해당 안내에서 확인한다. Hermes 실행에는 별도의 모델과 작가 AI ROCm 서버 준비도 필요하다. 생성기별 모델 준비는 기존 모델 관리·해당 사용 안내를 따른다. `gui`와 `gateway`는 통합 진입점의 하위 명령이며 서비스 수명은 유지된다. `--module`과 명시적 `--all`도 기존 검사 실행기에 전달된다.

## Docker 전체 회귀

저장소 루트에서 `./scripts/workflow.sh test --all`을 실행하면 전체 회귀 작업을 접수하고 JSON으로 `run_id`와 `report_path`를 즉시 반환한다. Docker 이미지 준비와 테스트는 호출 터미널과 독립적으로 실행된다. 첫 이미지 준비에는 Docker 데몬과 패키지 레지스트리 연결이 필요하다.

`./scripts/workflow.sh test result <run_id>`로 상태를 확인한다. `queued`와 `running`은 진행 중, `passed`와 `failed`는 테스트 완료, `error`는 실행 또는 집계 오류다. 완료된 작업을 조회하면 테스트 종료 코드를 반환한다. 실행별 `.tmp/test/docker-audit/<run_id>/`에 최종 보고서와 Docker 로그를 보존하고, 테스트가 집계되면 `artifacts/`에 JUnit, 상세 로그, 요약과 종료 코드를 남긴다.

작업자는 인접한 네 저장소에서 Git 추적 파일과 ignore 대상이 아닌 신규 파일의 작업 사본을 만들고 컨테이너에서 검사한다. 모델 캐시와 호스트 가상환경은 복사하지 않는다. 선별 검사는 기존 `test --module`과 `test --group`을 사용한다.

## 주요 기능

- **이미지**: [FLUX 이미지 생성기](docs/flux-image-generators.md)는 일반 이미지, 캐릭터, 마네킨, 빌보드, 소품, 식생, 건물, 심리스 타일과 표정 작업을 다룬다. 생성 결과의 품질과 반복 경계는 직접 검수한다.
- **모션**: [Kimodo 사용 설명](generators/kimodo/README.md)은 텍스트 모션 생성과 SOMA 렌더·포즈 출력을 설명한다.
- **음악·효과음·영상**: `generators/`의 해당 생성기별 README와 워크플로우 화면에서 준비 및 실행 조건을 확인한다.
- **검수·편집**: [공통 검수 절차](docs/asset-review.md)와 [워크플로우 소스 구조](workflow/README.md)를 참고한다. 맵·타일은 에셋 저장소의 등록 원본을 검증해 직접 읽는다.
- **작가 AI·프롬프트 번역**: [작가 AI 실행 안내](docs/writer-agent.md)와 [워크플로우 클라이언트 가이드](docs/management-clients.md)를 참고한다. 번역 결과는 의미와 수치를 검토한다.

Qwen 이미지 생성기 계열은 폐기되어 신규 생성·재개와 모델 준비를 지원하지 않는다. 기존 이력 조회 경로는 유지한다. HY-Motion, VNCCS 포즈 변환과 MoMask 생성은 폐기됐다. 과거 문서와 호환 코드가 있다는 사실이 현행 실행 지원을 뜻하지 않는다. 상세 범위는 [클라이언트 가이드](docs/management-clients.md)를 확인한다.

## 저장소 구성과 에셋 소유권

| 경로 | 용도 |
| --- | --- |
| `generators/` | 생성기별 구현·설정·사용 설명·변경 기록 |
| `gui/`, `gateway/`, `cli/`, `mcp/` | 워크플로우 화면, HTTP 게이트웨이, 명령행 및 MCP 인터페이스 |
| `workflow/` | 도메인 간 공용 코드, 서비스 및 통합 테스트 |
| `scripts/` | 관리 환경 준비 및 서버 실행 |
| `docs/` | 작업 절차, 운영 기준과 검증 기록 |
| `prompts/` | 사용자 지시로 이전한 제작 프롬프트 |
| `baseline/` | 승인된 제작 기준 자료와 출처 |
| `.model/` | 로컬 모델과 캐시 |
| `.tmp/`, `.local/` | 로컬 후보·작업 기록 및 실행 데이터 |

채택된 에셋과 런타임 맵의 관리 원본은 인접 `slime-assets` 저장소다. 캐릭터는 `assets/characters/`, 몬스터는 `assets/sprites/`, 건물은 `assets/buildings/`, 빌보드는 `assets/billboards/`, 지형 타일은 `assets/tiles/terrain/`, 맵은 `assets/maps/`에서 관리한다. 등록부의 ID·버전·출처·해시를 보존하고 소비자 잠금 목록을 함께 갱신한다. 생성 후보·모델·로그는 에셋 등록부에 넣지 않는다.

빌보드 등록, 공용 표시 속성 또는 맵 배치를 변경한 경우 [빌보드 카탈로그 안내](../slime-assets/assets/billboards/README.md)에 따라 카탈로그를 동기화하고 검증한다. 생성기 구조와 UI 기준은 [생성기 구성 가이드](docs/generator-structure.md), [워크플로우 UI 가이드](docs/management-ui.md)를 따른다.

준비 명령은 실행 전에 변경 대상과 다운로드 범위를 출력한다. `--plan`은 로그·예약·설치 없이 계획만 표시한다. 계획은 워크플로우 저장소의 남은 공간도 표시하지만 별도 모델·캐시 경로의 공간까지 보장하지 않는다. 예상 다운로드 크기는 패키지와 기존 파일 상태에 따라 달라 확인 불가로 표시하며, 모델 및 GPU 상태를 완전히 검증하는 기능은 아니다. 설치 실패 후에는 출력된 로그와 기존 파일을 확인하고, 불완전한 전용 환경은 자동 삭제하지 않으므로 원인을 해결하거나 별도 보존한 뒤 재시도한다.
