# concept-image-reference-generator

- pipeline_id: `concept-image-reference-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `md`: 아트 디렉션/스타일 가이드
- `txt`: 프롬프트 초안
- `json`: 생성 파라미터(seed, ratio, style)

## output_contract
- `png`: 콘셉트 레퍼런스 이미지
- `json`: 생성 메타데이터(프롬프트/seed/모델 버전)
- `md`: 요약 리포트

## node_harness
1. `prompt.compose` (`md`,`txt`,`json` -> `txt`,`json`)
2. `image.generate` (`txt`,`json` -> `png`,`json`)
3. `image.refine` (`png`,`json` -> `png`,`json`)

## future_extension_plan
- 멀티 레퍼런스 입력(`png` 다중) 지원
- 품질 게이트(해상도, 색상 분포, 노이즈 점수) 자동 검사 추가
