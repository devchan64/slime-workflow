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
- Use `.model` only as model download/cache directory.
- Validate model input/output schemas strictly; fail fast on violations.
- Accept only allowed output formats; disallow permissive recovery parsing.
- If rules conflict, model card I/O policy takes precedence.
- For Musician-Llama nodes, prioritize natural-language input + pipe/comma MIDI tuple contract.
- CPU inference is not allowed; fail immediately when GPU (CUDA/MPS) is unavailable.
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
