# workflow/nodes

노드는 AI 단위 명령 처리기를 의미한다.
공통 노드 인덱스는 `workflow/nodes/catalog.yaml`을 기준으로 관리한다.

## 책임
- 단일 목적 처리만 담당한다.
- 입력 타입 검증 후 출력 타입을 명시적으로 생성한다.
- 파이프라인 하네스가 연결 가능한 형태의 메타데이터를 남긴다.

## 노드 단위 원칙
- 노드는 입력 JSON을 받아 산출물을 생성하고, 다음 노드 전달에 필요한 값을 출력 JSON으로 명시한다.
- 노드 내부에 파이프라인 정책/토폴로지/실행 순서를 하드코딩하지 않는다.
- LLM 노드는 규칙 기반 휴리스틱/스텁으로 결과를 대체하지 않고, 입력 기반으로 실제 모델 산출물을 생성한다.
- 코드의 역할은 산출물 생성이 아니라 계약 검증과 런타임 오케스트레이션에 한정한다.
- 계약 위반(필수 필드 누락/타입 불일치/허용 범위 위반)은 복구하지 않고 즉시 실패(Fail-Fast)한다.
- 정규화가 필요하면 코드 상수로 강제 보정하지 않고 LLM 산출 단계에서 수행한다.
- 노드 실행 환경(이미지/바이너리/의존성)은 노드 단위로 선언하며, 전역 환경변수에 의존한 정책 주입을 금지한다.
- 노드에서 사용하는 LLM 프롬프트는 코드 문자열 하드코딩 대신 JSON 파일로 작성/버전관리하여 운영한다.
- LLM 프롬프트 JSON은 입력 변수, 출력 계약, 검증 규칙을 명시해야 하며 노드는 해당 JSON을 로드해 실행한다.

## 입출력 계약
- 허용 입력/출력 확장자: `png`, `wav`, `mp3`, `mid`, `midi`, `sf2`, `txt`, `md`, `json`, `yaml`
- 노드는 계약 외 확장자를 직접 생성하지 않는다.

## 노드별 병합
- 노드 런타임은 `workflow/nodes/<node-family>/runtime/`에 둔다.
- 노드 패키지는 `workflow/nodes/<node-family>/packages/`에 둔다.
- 노드 테스트는 `workflow/nodes/<node-family>/tests/`에 둔다.
- 패키지 매니페스트의 `tests` 항목은 노드 테스트와 같은 계약을 검증해야 한다.
- 신규 노드는 구현, 런타임, 패키지, 테스트를 같은 노드 디렉터리 아래에 추가한다.
- 모델 검증 이력은 노드 디렉터리의 `MODEL_TEST_HISTORY.md`로 관리한다.

## 노드 정의 템플릿
노드 정의는 텍스트 기반 선언으로 관리한다.

```yaml
id: example.node
version: 0.1.0
description: 노드 목적 설명
inputs:
  - name: source
    type: png
outputs:
  - name: result
    type: json
runtime:
  cache_dir: .result
```

## 실행 산출물 위치
- 모델 캐시: `.model`
- 중간/최종 결과: `.result`
- 사운드폰트 캐시: `.soundfonts`

## 절차 검증용 기록 규칙
- 모든 노드는 실행 입력/출력/오류 기록을 `.result` 하위에 남겨야 한다.
- 기본 경로 규칙:
  - 입력: `run_root/records/nodes/<node-id>/input.json`
  - 성공 출력: `run_root/records/nodes/<node-id>/output.json`
  - 실패 출력: `run_root/records/nodes/<node-id>/error.json`
- `run_root`는 파이프라인/테스트 실행 루트이며, 없으면 `.result/workflow/runtime/run`을 기본값으로 사용한다.
- 계약 검증은 복구하지 않고 Fail-Fast하되, 실패 원인(`error.json`)은 반드시 기록해야 한다.
- E2E/스모크 테스트 스크립트는 `.result` 하위 결과 디렉터리를 생성하고, 핵심 산출물 경로를 결과 JSON에 명시해야 한다.

## 노드 테스트 규약
- 노드 테스트는 반드시 `실행 스크립트(shell)` + `검증 소스코드` 2요소로 구성한다.
- `실행 스크립트(shell)` 책임:
  - 테스트 run 디렉터리를 `.result/workflow/tests/<test-name>/<timestamp>`로 생성한다.
  - 단계 로그(`timestamp/area/stage`)와 heartbeat(5초 이내)를 출력한다.
  - 노드 CLI를 실제로 호출하고 실패 시 즉시 종료한다.
- `검증 소스코드` 책임:
  - 산출물 존재/형식/계약 필수 필드를 검증한다.
  - 계약 위반 시 복구 없이 실패(Fail-Fast)한다.
  - 검증 결과(요약 지표)를 stdout으로 출력한다.
- 권장 파일 배치:
  - 실행 스크립트: `workflow/tests/run_<node-or-pipeline>_*.sh`
  - 검증 소스코드: `workflow/nodes/<node-family>/tests/test_*.py`
- shell만 있거나 소스코드만 있는 단독 테스트는 규약 위반으로 간주한다.

## 확장 규칙
- 신규 노드를 추가하면 해당 노드 디렉터리에 목적/입출력/실행/Fail-Fast/테스트를 설명하는 `README.md`를 반드시 작성한다.
- 노드 README는 해당 노드 단독 운영 문서이며, 타 노드 구조 템플릿으로 사용하지 않는다.

## 개편 안내
- 현재 `musicgen_small` 노드는 신규 기준 README를 우선 적용한 파일럿 노드다.
- 그 외 기존 노드들은 동일 구조 참고를 금지한다.
- 기존 노드 README/구조는 단계적 개편 예정이며, 개편 전까지는 개별 노드 계약 문서와 패키지 매니페스트를 우선 기준으로 본다.

- 신규 노드 추가 시 `catalog.yaml`에 `id`, `role`, `inputs`, `outputs`를 먼저 등록한다.
- 기존 노드 계약 변경 시 하위 호환성(이전 출력 타입)을 최소 1개 버전 동안 유지한다.

## workflow 단위기능 매핑
- `workflow/nodes/concept_image_nodes.py`는 concept-image 단위 노드(1~4)의 순서와 노드 ID를 정의한다.
- 각 단위 구현은 `workflow/nodes/concept_image/application/` 아래에서 workflow 소유 코드로 유지한다.
- 현재 매핑은 아래 순서를 따른다.
  1. `design-concept-generation` → `concept.design.generate`
  2. `pixel-art-generation` → `concept.pixel.generate`
  3. `keyframe-scene-composition` → `concept.keyframe.compose`
  4. `animation-frame-rendering` → `concept.animation.render`
- 파이프라인 연결선은 인접 노드 단방향(`A -> B`)으로 자동 생성한다.
