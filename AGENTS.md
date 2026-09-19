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

## Frontend Layout Rules
- Do not hard-code layout constants inside frequently called functions.
- Manage layout values as top-level constants or in a dedicated `constants` module.
- Layout functions should only combine constants and compute derived values.

## Commit Message Rules
- All commit messages must follow **Conventional Commits**.
- Default format: `type(scope): description` or `type: description`.
- `type/scope` must be English; description/body should be Korean-first.
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
