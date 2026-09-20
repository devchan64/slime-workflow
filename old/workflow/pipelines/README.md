# workflow/pipelines

파이프라인은 특정 동작을 위한 프롬프트/노드 연결 하네스를 정의한 텍스트 파일 묶음이다.
파이프라인 목록/상태는 `workflow/pipelines/catalog.yaml`을 SSOT 인덱스로 사용한다.

## 기본 원칙
- 파이프라인 정의는 사람이 리뷰 가능한 텍스트(`md`, `yaml`, `json`)로 유지한다.
- 노드 간 연결은 입력/출력 타입 계약을 준수한다.
- 파이프라인 실행은 기본적으로 `spec + input` JSON으로 동작한다.
- `workflow/pipelines/runtime/pipeline_json_runner.py`가 스펙의 `nodes` 순서를 해석해 파이프라인을 실행한다.
- 노드는 파이프라인 런타임을 통해 실행하며, 사용자용 workflow 스크립트는 파이프라인을 기본 진입점으로 삼는다.
- `pipeline-json` 런타임은 기본 하트비트를 제공한다.
  - `WORKFLOW_RUNTIME_HEARTBEAT_SECONDS`(기본 5초, `WORKFLOW_HEARTBEAT_SECONDS` 호환)
  - `WORKFLOW_RUNTIME_HEARTBEAT_STALL_LIMIT`(기본 3, `WORKFLOW_HEARTBEAT_STALL_LIMIT` 호환)
  - `WORKFLOW_RUNTIME_STALL_TIMEOUT_SECONDS`(기본 0: 비활성, 0보다 크면 동일한 activity가 이 시간 이상 멈추면 SIGTERM 종료)
- 단계별로 `Expand -> rollout -> Contract` 변경 순서를 지켜 무중단 이전이 가능해야 한다.

## 초기 파이프라인 후보
- `concept-image-reference-generator`
- `sprite-8dir-from-concept`
- `animation-sprite-generator`
- `character-concept-art-generator`
- `map-tile-generator`
- `character-concept-sheet-generator`
- `background-concept-sheet-generator`
- `map-file-generator`
- `sprite-file-generator`

## 파이프라인 스펙 필수 항목
- `pipeline_id`
- `version`
- `status`
- `input_contract`
- `output_contract`
- `node_harness`
- `future_extension_plan`

## 오디오 파이프라인 메모
- 레거시 오디오 노드(`audio.render`, `audio.encode.mp3`)는 폐기되었다.
- 신규 오디오 경로는 `music.audio.plan.render` → `music.audio.render.wav` → `music.audio.encode.mp3`를 사용한다.
