# map-tile-generator

- pipeline_id: `map-tile-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `png`: 배경 콘셉트 레퍼런스
- `json`: 타일 규격(tile_size, palette)
- `yaml`: 지형 타입 규칙

## output_contract
- `png`: 타일셋 이미지
- `json`: 타일 인덱스/속성

## node_harness
1. `image.refine` (`png`,`json` -> `png`,`json`)
2. `tile.generate` (`png`,`json`,`yaml` -> `png`,`json`)

## future_extension_plan
- 자동 심리스(경계 매칭) 검사 노드 추가
- 시즌/테마별 변형 타일셋 파생 지원
