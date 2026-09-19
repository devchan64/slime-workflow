# sprite-file-generator

- pipeline_id: `sprite-file-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `png`: 시트 원본
- `json`: 프레임 컷 정보
- `yaml`: 내보내기 규칙

## output_contract
- `png`: 최종 스프라이트 시트
- `json`: 런타임 스프라이트 메타데이터
- `md`: 변경 이력 요약

## node_harness
1. `sprite.generate` (`png`,`json`,`yaml` -> `png`,`json`)
2. `image.refine` (`png`,`json` -> `png`,`json`)

## future_extension_plan
- 엔진별 export profile(Phaser/Unity) 분리
- 압축 품질/아틀라스 최적화 자동 추천
