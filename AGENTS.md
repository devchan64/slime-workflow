# AGENTS.md
## Scope
- Web game project
- WebGL frontend
- AWS infrastructure
## Architecture
### Frontend
- Deliver static assets via **S3 + CloudFront**.
- Cache policy:
  - Use hashed filenames for immutable assets.
  - Use short TTL or invalidation for entry files (for example, `index.html`).
### Backend
- Provide API and database per service.
- Keep API versioning paths (for example, `/v1`, `/v2`).
### Deployment
- Default deployment is **Lambda + API Gateway (HTTP API)**.
- Ensure zero-downtime rollout and rollback path for both frontend and backend.
## Zero-Downtime
- DB migration order: **Expand → rollout → Contract**
- Preserve compatibility with at least one previous API version.
- Use release gates based on health checks, error rate, and latency.
## Cost (Minimum-Cost Operations)
- Target minimum cost without breaking required reliability/performance.
- Use serverless-first in early stages.
- Avoid fixed-cost resources unless clearly required.
- Maximize CDN cache hit ratio.
- Keep log/monitoring retention to the minimum required period.
- Remove idle resources regularly.
## Local Development Rules
- Local backend stack: `FastAPI + uvicorn`, `DynamoDB Local (Docker)`, optional `SAM local`.
- Separate environments by stage: `local/dev/prod`.
- Local default config must never point to production resources.
## Management Source Domains
- 관리도구 소스는 [도메인 구조 가이드](tools/review/README.md)를 따른다. 공용 Python은 `tools/review/common/`, 생성기별 서비스는 `tools/review/domains/`, UI는 `tools/review/ui/`에서 관리한다.
- 루트의 이전 서비스 파일은 import·직접 실행 호환 연결이다. 신규 기능은 정식 도메인 모듈에 추가하며 URL·CLI·기록 저장 경로를 디렉터리 이동에 맞춰 바꾸지 않는다.

## Management UI Guide
- 전역 스타일은 MoMask 생성기를 기준으로 한 `tools/review/ui/shared/management.css`에서 관리한다. 웹 페이지는 `/management/style.css`를 연결하고, 단독 검수 HTML은 `read_review_shared_styles()`로 삽입한다. 도메인 CSS에는 배치만 추가하며 공용 색상·상태 스타일을 복제하지 않는다.
- 생성 UI는 [예상 시간 표시 규칙](workflows/management-ui.md#생성-예상-시간-표시-규칙)에 따라 예상 남은 시간·완료 시각과 추정 근거를 표시한다. 근거가 없으면 계산 중임을 안내한다.
- 프롬프트 원문을 표시할 때는 [단어 수 표시 규칙](workflows/management-ui.md#프롬프트-단어-수-표시-규칙)에 따라 개별·최종 단어 수를 함께 표시한다. 최종 수치는 방향·변수 치환 후 실제 모델 입력을 기준으로 한다.
- 관리도구 UI를 신규 작성하거나 수정할 때 [관리도구 UI 가이드](workflows/management-ui.md)를 기준으로 한다. 공용 색상·레이아웃, 고정 설정 표시, 생성 버튼 상태, 로그, 누적 이력, 재생 컨트롤과 검증 범위를 다룬다.
- 공통 UI 동작은 공용 코드에서 관리하고 페이지별 복제를 피한다. 비활성 버튼에는 사유와 해결 방법을 표시하며, 실행 중인 사용자 작업을 UI 검증 목적으로 취소하거나 덮어쓰지 않는다.
- GUI·CLI 명령 및 기록 저장 구조는 아래 Management Client and Gateway Standard와 [관리도구 클라이언트 가이드](workflows/management-clients.md)를 함께 따른다.

## Management UI Framework Standard
- 관리도구의 Python UI 프레임워크는 **Gradio**를 채택한다. 신규 페이지와 전환 대상 페이지의 설정·진행 상태·로그·생성이력은 **Gradio Blocks**로 구성한다.
- 이는 전환 기준이며 현재 모든 페이지가 Gradio로 구현된 것은 아니다. **MoMask 생성기**를 첫 전환·검증 페이지로 삼고 검증한 공용 UI를 다른 생성기로 단계적으로 확대한다. 기존 페이지의 일괄 재작성은 별도 작업으로 진행한다.
- Gradio는 GUI 클라이언트 역할만 담당한다. 생성·취소·재개는 기존 공용 명령 게이트웨이를 통해 실행하며 통합 CLI, 작업 서비스, 생성 ID 및 요청·결과·로그·이력 저장 경로를 유지한다.
- GPU 추론·렌더링은 기존 별도 작업 프로세스에서 실행한다. Gradio 이벤트 처리나 큐에 작업 수명·동시 실행 제어·영구 이력 관리를 중복 구현하지 않는다. 브라우저 연결 종료가 작업 종료나 이력 삭제를 의미하지 않는다.
- 프레임 동기 재생·프레임 이동·스프라이트 편집은 브라우저에서 처리하는 공용 사용자 정의 컴포넌트로 연결한다. 프레임마다 Python 서버를 왕복하는 재생 구조를 피하고 기존 JavaScript 기능의 재사용을 우선 검토한다.
- 공용 테마·색상·간격과 설정·이력·로그 컴포넌트를 통합 관리한다. 기존 관리도구 UI 가이드의 예상 시간·프롬프트 단어 수·수동 초기화·결과 재생 규칙을 동일하게 적용한다. 기존 CSS와 Gradio DOM의 호환성을 가정하지 않고 공용 테마에 맞춰 검증한다.
- 전환 검증에는 GUI/CLI 명령 계약, 기존 이력 조회, 취소·재개, 브라우저 재연결, 다중 화면 동기 재생, 응답성과 메모리 사용량을 포함한다. 검증을 위해 사용자의 실행 중 작업을 취소하거나 기록을 덮어쓰지 않는다.

## Management Client and Gateway Standard
- 관리도구의 기준 구조는 **GUI·통합 CLI → 공용 명령 게이트웨이 → 작업 서비스 → 공용 기록 저장소**이다. 상세 구현·사용법은 [관리도구 클라이언트 가이드](workflows/management-clients.md)를 따른다.
- `tools/manager.py`는 CLI 진입점만 담당한다. 서비스·명령 등록, 최상위 `command`·`help`, 실행 디스패치와 HTTP 명령 전송은 `tools/review/common/management_gateway.py`에서 관리한다. 별도 CLI 실행 체계나 중복 서비스 레지스트리를 만들지 않는다.
- CLI 인자 파싱·파일 입력·진행 대기·취소와 명령 디스패치는 게이트웨이의 공통 구현을 사용한다. 생성기별 독립 CLI 실행 모듈이나 로그/상태 직접 조회 루프를 만들지 않는다. GUI와 CLI 모두 `execute_management_command`로 진입하며 실제 생성·상태 변경·기록 저장은 작업 서비스에 둔다.
- 웹 페이지는 GUI 클라이언트다. 명령 요청은 게이트웨이를 거쳐 CLI와 같은 작업 서비스를 호출한다. 기존 웹 API 주소는 호환 어댑터로 유지할 수 있으며, 새 통합 HTTP 명령은 `POST /management/command`의 `{service, command, payload}` 계약을 사용한다.
- 브라우저 요청을 셸 문자열로 변환하거나 요청마다 CLI 프로세스를 실행하지 않는다. 명령 게이트웨이와 서비스 코드를 공유한다. 이미지·프레임·정적 UI 파일 조회는 명령 실행과 구분한다.
- 현재 통합 대상은 `momask`, `qwen-2512`, `qwen-2511`, `character-animation`, `tile-map`이다. MoMask와 캐릭터 애니메이션은 로컬 작업 서비스를 통해 서버 없이 CLI 실행이 가능하고 Qwen 두 종류는 실행 중인 관리 서버 API를 사용한다. ANNY·작가 에이전트 등 미통합 기능까지 완료된 것으로 기술하지 않는다. 신규 관리 기능과 기존 기능의 통합 작업에는 이 구조를 적용한다.
- GUI와 CLI는 같은 생성 ID·요청·상태·로그·결과·이력 경로를 공유한다. 클라이언트별 저장소를 만들거나 기존 경로를 임의로 이전하지 않는다. 현재 서비스별 경로는 클라이언트 가이드를 기준으로 하며, 이 경로에 대한 통합 작업은 일반 실험 폴더 규칙을 이유로 기존 기록을 이동하지 않는다.
- 생성 이력은 누적하고 결과를 양쪽에서 조회할 수 있어야 한다. 초기화는 명시적인 수동 명령으로만 수행하며, 이력 초기화와 결과 파일 삭제를 구분한다. 초기화된 이력을 작업 종료 시 자동 복원하지 않는다.
- 입력 검증·동시 실행 제어·취소·완료/실패 상태 기록은 작업 서비스가 책임진다. HTTP 어댑터는 Host·Origin·요청 크기·JSON 형식 검사를 유지하고, 허용된 서비스·명령만 전달한다. GPU 실행 및 모델 경로 정책도 GUI·CLI에서 동일하게 적용한다.
- 새 명령을 추가하면 게이트웨이 등록·CLI 인자·`help`·GUI 연결·사용 가이드를 함께 갱신한다. 해당 기능의 GUI/CLI 계약 일치, 잘못된 입력 거절, 상태·이력 공유를 검증한다. 구조 변경 시 `test_management_gateway.py`, `test_momask_jobs.py`, `test_qwen_commands.py` 중 영향받는 테스트를 실행하고 필요한 계약 검증을 보강한다.

## Language Rules (Current default in this repository)
- Runtime output/comments/docstrings/markdown should be Korean-first.
- Keep identifiers (variables/functions/files), standard keywords, and AWS resource names in English.
- User/operation guidance should be Korean-first.
## Source Code Naming and Declaration Rules
- 프로젝트에서 정의하는 함수명·변수명은 의미 있는 영어 단어 **3개 이상**으로 구성한다. 파라미터와 주요 상수의 이름에도 같은 원칙을 적용한다.
- 언어 관례에 따라 `snake_case`, `camelCase`, `UPPER_SNAKE_CASE`를 사용한다. 예: `calculate_party_reward`, `currentPlayerHealth`, `FIELD_RECOVERY_PER_MINUTE`.
- 단어 수를 맞추기 위한 무의미한 접두사·접미사를 붙이지 않고 역할·대상·의미가 드러나도록 이름을 정한다.
- 주요 상수·설정값·파라미터 기본값은 사용하는 처리 로직보다 앞에 선언한다. 공통 상수는 모듈 상단 또는 전용 constants/config 모듈에 모으고 함수 안의 주요 파라미터 준비도 사용 전에 배치한다.
- 새로 작성하거나 수정하는 코드에 적용하며, 기존 전체 코드의 일괄 이름 변경은 별도 리팩터링으로 진행한다. 외부 API·DB 필드·프레임워크가 요구하는 식별자는 계약 변경 없이 임의로 바꾸지 않는다.
## Frontend Layout Rules
- Do not hard-code layout constants inside frequently called functions.
- Manage layout values as top-level constants or in a dedicated `constants` module.
- Layout functions should only combine constants and compute derived values.
## Commit Message Rules
- All commit messages must follow **Conventional Commits**.
- Default format: `type(scope): description` or `type: description`.
- `type`과 선택적 `scope`는 영어로 작성하고, 설명(description)과 본문(body)은 한국어로 작성한다. 코드 식별자·표준 용어·고유명은 원문 표기를 유지한다.
- 예: `feat(party): 파티원 보상 분배 규칙 추가`.
- AGENTS.md-related commits follow the same rule.
## Image Commit Rules
- For image commits, verify only:
  - File exists
  - Filename matches
  - Destination path matches
## Script Logging Rules
- Workflow scripts must emit stepwise trace logs.
- Keep a consistent log format including `timestamp/area/stage`.
- On failure, print failing line/command via `trap` or equivalent.
- Long-running jobs must emit heartbeat logs at least every **5 seconds**.
- Heartbeat should include progress summary; during stalls include recent logs/line count/warnings and resource/artifact changes.
- Persist execution logs to file and print tail on failure.
## Security/Ops Baseline
- Never commit secrets.
- Enforce least-privilege IAM.
- Maintain alerts, dashboards, and runbooks.
- Never store secrets/tokens/sensitive keys in `env` files including `.env.local`.
- Keep repository/workflows/tests free from `OPENAI_API_KEY` dependency.
## Change Management
- Explain architecture/deployment/cost-impacting changes against this document.
- For exceptions, document reason, duration, and mitigation.
- Default image commit review is filename/path check only.
## Workflow Model Policy
- Nodes must not select models from user input.
- Model selection must be fixed by code/pipeline configuration.
- Qwen 로컬 생성은 프롬프트 단어 수와 순서의 영향을 크게 받으므로 전체 프롬프트를 100단어 미만으로 유지하고, 캐릭터·동작·카메라·스타일처럼 핵심 요구를 짧고 우선순위가 분명한 양성 지시로 작성한다.
- Qwen 로컬 생성에서 긴 부정적 프롬프트에 의존하지 않는다. 부정적 프롬프트는 기본 보정 수단으로 사용하지 말고, 필요한 경우에도 짧은 금지어만 최소한으로 사용하며 실제 교정은 양성 지시와 참조 이미지로 해결한다.
- 프롬프트에는 의미가 충돌하거나 스타일을 오인시킬 수 있는 표현을 넣지 않는다. 예를 들어 포즈 정밀도를 뜻하는 `pixel accurate` 대신 `match the pose precisely`처럼 작성하고, `pixel art`와 혼동될 수 있는 표현은 명시적으로 피한다.
- 생성 실험은 최종 프롬프트 원문·단어 수·해시를 실행 기록에 보존하고, 프롬프트 변경마다 1프레임 샘플로 먼저 검증한 뒤 배치 생성으로 확대한다.
- Use `.model` only as model download/cache directory.
- Validate model input/output schemas strictly; fail fast on violations.
- Accept only allowed output formats; disallow permissive recovery parsing.
- If rules conflict, model card I/O policy takes precedence.
- For Musician-Llama nodes, prioritize natural-language input + pipe/comma MIDI tuple contract.
- CPU inference is not allowed; fail immediately when GPU (CUDA/MPS) is unavailable.
- GPU 상태 확인·모델 준비·GPU 추론은 샌드박스 밖에서 실행한다. 샌드박스 내부 접근 실패를 GPU 부재로 판단하지 않으며, 외부 실행에서도 GPU를 사용할 수 없을 때 명확한 원인으로 즉시 실패한다.
- All music pipelines must prepare model artifacts before execution.
- If prepare fails, fail immediately (no fallback) and print `model_id/model_root(or download_tmp_dir)/model_path(or bundle)/binary path` to stdout.
- On successful prepare, log resolved output path and reuse it in runtime.
- MIDI node defaults:
  - `MUSIC_MIDI_COMPOSER_MODEL_ID=Ghanibhuti/Musician-Llama-3.2-1B-Instruct`
  - `TEXT2MIDI_MODEL_ROOT=.model/music_midi_composer`
- Recommended model prepare entrypoints:
  - Ollama: `workflow.nodes.music_structure_plan.runtime.prepare`
  - Magenta: `workflow.nodes.music_midi_generate.runtime.prepare`
## Fail-Fast Rules
- Do not add/keep fallback logic by default.
- Unsupported input/missing dependency/invalid state must fail fast with explicit root-cause exception.
- Prefer explicit exceptions over implicit failure return values.
- Quality threshold misses (for example MIDI diversity) are not hard failures; record as `WARN` + `quality_warnings` and continue.
- Final quality approval is the user’s responsibility.
## Repository Boundary
- 이 저장소의 책임은 AI 제작 노드·파이프라인다.
- 다른 저장소의 소스 또는 상대 경로를 런타임 의존성으로 사용하지 않는다.
- 프론트엔드와 백엔드는 버전이 있는 HTTP API로 연결한다.
- 워크플로우 산출물은 검수 후 명시적으로 전달하며 프론트엔드에 직접 쓰지 않는다.
## Design Document Ownership
- SLIME의 기획·설계 문서는 비공개 `slime-backend/docs/design/`에서만 작성·관리한다.
- 공개 `slime-frontend`와 `slime-workflow`에는 설계 문서 원본·복제본·요약본을 커밋하지 않는다.
- 공개 저장소는 구현·실행·검증에 필요한 기술 사용 설명만 관리하며 비공개 문서를 런타임 의존성으로 삼지 않는다.
## Base Data Format
- 프로젝트의 기본 데이터·콘텐츠 테이블·설정 파일은 JSON보다 YAML(`.yaml`)을 우선 사용한다.
- 동일 데이터의 YAML·JSON 원본을 중복 관리하지 않는다.
- 데이터 로딩 시 필수 필드·자료형·허용 값·알 수 없는 필드·중복 키를 엄격히 검증하고, 오류는 명확한 원인과 함께 즉시 실패시킨다.
- API 요청·응답, DB 저장 표현, 도구·표준이 요구하는 JSON 파일과 생성 산출물은 해당 계약을 유지한다. 예: `package.json`, `tsconfig.json`, glTF 및 에셋 sidecar.
- 기존 파일은 관련 작업에서 소비 코드·검증·배포 구성을 함께 변경할 때 전환하며, 확장자만 일괄 변경하지 않는다.
## Asset Generation and Output Ownership
- `slime-workflow`는 에셋 생성 방식·모델 준비·제작 노드·파이프라인·검증·export를 관리한다.
- 최종 전달 이미지·프레임·시트 등 에셋의 관리 원본은 `slime-frontend`에 둔다. 에셋 보관과 게임 런타임 채택은 구분한다.
- 생성 과정의 중간 결과물(관절 모션·SMPL 피팅 결과·Depth·마스크·보정 전 프레임 등)은 `slime-workflow`에 보관한다. 실행별 경로와 출처를 유지하고 최종 전달 에셋과 구분한다.
- MoMask 모션과 SMPL 피팅 산출물은 `slime-workflow`의 재사용 가능한 제작 자산이다. 실행별 임시 파일로 취급하지 않고 식별자·불변 버전·출처·호환 정보를 관리하며 캐시 정리로 삭제하지 않는다.
- 동일 모션·피팅 산출물을 방향별 렌더와 호환되는 외형 생성에 재사용한다. 리그·관절·체형·좌표계·단위·프레임률 등의 호환 조건이 달라지면 재검증하고 필요 시 새 버전으로 피팅한다.
- 실행 기록은 재사용 자산의 식별자·버전·해시를 참조한다. 모델 다운로드·캐시만 `.model`에 두고 재사용 자산·실행 산출물·임시 캐시의 보관 경로와 정리 정책을 구분한다.
- 비공개 기획·설계·내부 프롬프트는 `slime-backend/docs/design/`에서 관리하고 공개 에셋과 함께 복제하지 않는다.
## Unregistered Asset Experiments
- `.result` 디렉터리는 사용하지 않는다. 실험 기록과 후보·중간 산출물은 `.tmp/test/*`에만 저장한다.
- 실험 결과는 반드시 `.tmp/test/<experiment-name>/<YYYY-MM-DD_HH-mm-ss>/*` 구조에 생성한다. 실험명은 생성기·검수기·패커 등 실험 목적과 실행 코드를 식별할 수 있는 안정적인 이름으로 정하고, 시각은 한국 시간(Asia/Seoul)을 사용하며 기존 결과를 덮어쓰지 않는다.
- 실행일시 폴더에는 실험 프롬프트, 참조 이미지, 생성 결과, 실행 로그와 모델·파라미터·출처 기록을 함께 보관한다.
- 실행기는 시작 시각·실행기 구분·출력 루트·입력 목록을 로그에 남기고, 완료 또는 실패 상태를 실행일시 폴더 안의 결과 기록에 남긴다. 실행 중 생성되는 하위 프레임·단계 산출물도 해당 실행일시 폴더 밖에 만들지 않는다.
- 실험 프롬프트는 해당 `.tmp/test/` 실행 폴더에서 작성·수정하고 커밋하지 않는다. 정식 채택된 제작 프롬프트·설계 문서는 `slime-backend/docs/design/`에서 관리한다.
- 후보 이미지는 정식 에셋 폴더·에셋 레지스트리·게임 런타임에 자동 등록하지 않는다. 사용자가 채택 또는 정식 등록을 지시하면 선택한 산출물만 `slime-frontend`의 정식 경로로 옮기거나 복사하고 등록한다.
- `.tmp/`는 각 저장소의 `.gitignore`에 등록하며 후보·실험 산출물은 커밋하지 않는다.
- 이 규칙은 정식 등록되지 않은 후보·실험 에셋에 적용한다. 재사용 가능한 MoMask 모션·피팅·승인된 리그 및 버전이 고정된 제작 자산은 기존 보관 정책을 유지하며 `.tmp` 정리 대상에 포함하지 않는다.
- 재사용 근거가 없고 폐기된 실험 프롬프트는 삭제한다. 현재 실행·재사용 근거가 확인된 제작 방식·정식 채택 에셋의 출처 기록만 유지하며 동일 프롬프트의 불필요한 복사본을 남기지 않는다.
## Animation Pose Reference
- 캐릭터 애니메이션의 OpenPose 형식 포즈 맵은 MoMask가 생성한 모션 관절 데이터를 원천으로 사용한다. 기존 승인된 리그 체형 보정·방향별 투영은 유지할 수 있으며 모션 자산 ID·버전·해시와 변환 경로를 실행 기록에 남긴다.
- 이미지 생성 결과에서 추측한 관절이나 임의로 만든 포즈로 대체하지 않는다. 투영 관절 맵과 실제 OpenPose 검출 결과를 구분해 기록한다.
## Registered Workflow Asset Paths
- 정식 재사용 제작 자산은 Git 추적 대상인 `assets/` 아래에서 식별자·버전·출처·해시와 함께 관리한다. `.tmp/`에만 보관한 상태를 정식 자산 등록으로 간주하지 않는다.
- 승인 루프·MoMask 모션·리그·포즈 맵의 바이너리와 manifest·선택 설정을 함께 커밋한다. 모델 가중치는 계속 `.model/`에 두고 커밋하지 않는다.
## Generation Record Retention
- 일반 생성·후보·검수·재시도·패킹 기록은 `.tmp/test/<experiment-name>/<YYYY-MM-DD_HH-mm-ss>/`에 보관하며 자동으로 Git 추적 대상에 추가하지 않는다.
- 리포트 또는 현재 생성기에 직접 연결된 기록만 저장소 보존 대상으로 검토한다. 생성기 코드 사본·이름 또는 에셋 관리번호가 있다는 사실만으로는 직접 연결로 간주하지 않는다.
- 사용자가 저장소 추적·보존을 명시적으로 지시한 경우에만 해당 기록을 `report/` 또는 `assets/generation-records/`에 사본으로 보관하고, 커밋 지시가 있을 때 커밋한다. 연결 대상·목적·출처·버전·해시를 기록한다.
- 직접 연결 근거가 없는 기존 생성 기록은 추적 경로에서 폐기한다. 기존 리포트 및 승인된 MoMask 모션·리그 등 재사용 제작 자산의 보관 정책은 유지한다.
