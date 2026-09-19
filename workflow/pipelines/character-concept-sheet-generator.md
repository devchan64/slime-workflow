# character-concept-sheet-generator

- pipeline_id: `character-concept-sheet-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `md`: 캐릭터 설정 문서
- `txt`: 포즈/표정 지시문
- `json`: 해상도/레이아웃 옵션

## output_contract
- `png`: 캐릭터 콘셉트 시트
- `json`: 슬롯/레이어 메타데이터
- `md`: 스타일 요약

## node_harness
1. `prompt.compose` (`md`,`txt`,`json` -> `txt`,`json`)
2. `image.generate` (`txt`,`json` -> `png`,`json`)
3. `image.refine` (`png`,`json` -> `png`,`json`)

## future_extension_plan
- 의상/장비 variation 자동 분기 생성
- 팀 컬러 기반 팔레트 자동 확장
