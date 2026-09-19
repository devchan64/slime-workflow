# Workflow SSOT (Single Source of Truth)

이 문서는 `workflow/` 기반 AI 제작 파이프라인 구조의 단일 기준 문서다.

## 1) 목표
- 노드/파이프라인 중심 구조로 운영 기준을 통일한다.
- 파이프라인 정의와 확장 계획을 텍스트 기반 규격으로 관리한다.
- 무중단 전환(Expand → rollout → Contract) 가능한 변경 절차를 유지한다.

## 2) 디렉토리 기준
```text
workflow/
  README.md                  # 구조/운영/확장 단일 기준(SSOT)
  nodes/
    README.md                # 노드 계약
    catalog.yaml             # 공통 노드 카탈로그
    <node-family>/
      application/           # 노드 구현
      runtime/               # 노드 실행 CLI/러너
      packages/              # 노드 패키지 계약/의존성/레지스트리
      tests/                 # 노드 회귀 테스트
  pipelines/
    README.md                # 파이프라인 작성 규칙
    catalog.yaml             # 파이프라인 목록/버전/상태
    *.md                     # 파이프라인별 상세 스펙
```

## 3) 표준 계약
- 허용 입출력 타입: `png`, `wav`, `mp3`, `mid`, `midi`, `sf2`, `txt`, `md`, `json`, `yaml`
- 임시 저장소: `.model`, `.result`, `.soundfonts`
- 노드는 완성된 패키지 매니페스트를 요구한다.
- 생성 품질 점검은 기본적으로 경고(`WARN`) 정책이며, 품질 미달만으로 파이프라인을 중단하지 않는다.
- 품질 경고는 결과 메타데이터(`quality_warnings`, `quality_gate_passed`)에 기록하고 최종 품질 검수는 사용자가 수행한다.
- 노드 패키지는 의존성 가져오기, 의존성 설치, 모델 준비, 입출력 계약, 기본 테스트케이스를 함께 포함한다.
- 노드 패키지는 필요한 requirements, 모델 레지스트리, 저장 정책을 자기 패키지 경로에서 소유한다.
- 노드 런타임, 테스트, 패키지는 중앙 디렉터리에 분리하지 않고 해당 `workflow/nodes/<node-family>/` 아래에 병합해 관리한다.
- 사용자용 workflow 실행은 파이프라인 런타임을 통해 노드를 조합하며, 노드 CLI는 파이프라인 내부 실행 단위로 취급한다.
- 모델이 필요 없는 결정적 변환 노드도 `model_commands: []`, `required_model_ids: []`를 명시해 패키지 계약을 유지한다.
- 모든 파이프라인은 아래 메타데이터를 유지한다.
  - `pipeline_id`
  - `version`
  - `status` (`draft`, `active`, `deprecated`)
  - `input_contract`
  - `output_contract`
  - `node_harness`

## 4) 버전/호환성 정책
- 파이프라인 정의는 `major.minor.patch` 버전을 사용한다.
- `major` 변경 시 이전 버전 하나 이상 병행 지원한다.
- deprecated 표시는 최소 1개 릴리스 주기 유지 후 제거한다.

## 5) 확장 계획 (Roadmap)
### Phase 1 (현재)
- 구조 표준화: `nodes/`, `pipelines/`, 카탈로그/스펙 문서화
- 파이프라인 9종 초안 스펙 정의
- `concept-image` 단위 실행 명령을 `scripts/workflow/run_concept_image_pipeline.sh`로 이전
- 캐릭터 디자인시트 기반 8방향 스프라이트 생성 노드를 `workflow/nodes/character_sprite/packages`로 분리
- 이전 완료된 단위 명령은 workflow 경로만 사용한다.

### Phase 2
- 파이프라인 실행 러너(예: CLI) 추가
- `catalog.yaml` 기반 유효성 검사 도구 추가
- 실행 메타데이터(`run_id`, `latency`, `error_rate`) 저장 규약 추가

### Phase 3
- 노드/파이프라인 릴리스 게이트 자동화
- 비용 측정(모델 호출, 렌더링 시간, 캐시 적중률) 리포트 연결
- 운영 대시보드/알림 기준 연동

## 6) 변경 관리
- 아키텍처/배포/비용 영향 변경은 본 문서에 먼저 반영한다.
- 예외가 필요한 경우 사유, 기간, 완화책을 함께 기록한다.
- 문서 간 충돌 시 본 문서를 우선 기준으로 본다.

## 7) 폐기 원칙
- 폐기된 경로/명령 참조는 문서/코드/스크립트에서 즉시 제거한다.
- `workflow` 실행 실패는 대체 결과로 숨기지 않고 원인 정보를 포함해 즉시 실패시킨다.
- 단위기능 테스트케이스는 노드 패키지의 일부이므로, 패키지에서 분리해 별도 암묵 규칙으로 관리하지 않는다.
