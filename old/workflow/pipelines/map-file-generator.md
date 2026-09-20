# map-file-generator

- pipeline_id: `map-file-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `json`: 타일 인덱스 데이터
- `yaml`: 룰셋(충돌, 스폰, 이벤트)
- `png`: 타일셋 참조

## output_contract
- `json`: 맵 데이터 파일
- `yaml`: 맵 운영 설정

## node_harness
1. `map.compose` (`json`,`yaml`,`png` -> `json`,`yaml`)

## future_extension_plan
- 스테이지 난이도 템플릿 자동 병합
- 검증기(충돌 누락/오브젝트 중첩) 추가
