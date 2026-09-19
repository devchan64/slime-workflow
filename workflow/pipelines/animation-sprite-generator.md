# animation-sprite-generator

- pipeline_id: `animation-sprite-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `png`: 베이스 스프라이트
- `json`: 리깅/애니메이션 설정
- `yaml`: 모션 시퀀스 정의

## output_contract
- `png`: 애니메이션 프레임 시트
- `json`: 프레임 타이밍/본 보정 정보

## node_harness
1. `rig.correct` (`png`,`json`,`yaml` -> `png`,`json`)
2. `sprite.generate` (`png`,`json`,`yaml` -> `png`,`json`)

## future_extension_plan
- IK 기반 보정 노드 추가
- 모션 품질 스코어링 자동 리포트 추가
