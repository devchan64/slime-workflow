# background-concept-sheet-generator

- pipeline_id: `background-concept-sheet-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `md`: 월드/지역 설정
- `txt`: 시간대/날씨 지시문
- `json`: 캔버스/레이어 옵션

## output_contract
- `png`: 배경 콘셉트 시트
- `json`: 레이어 메타데이터
- `md`: 장면 가이드 노트

## node_harness
1. `prompt.compose` (`md`,`txt`,`json` -> `txt`,`json`)
2. `image.generate` (`txt`,`json` -> `png`,`json`)
3. `image.refine` (`png`,`json` -> `png`,`json`)

## future_extension_plan
- 낮/밤/기후 variant 자동 생성
- 원경/중경/근경 분리 레이어 강제 옵션 추가
