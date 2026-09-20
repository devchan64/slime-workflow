# character-concept-art-generator

- pipeline_id: `character-concept-art-generator`
- version: `0.1.0`
- status: `draft`

## input_contract
- `md`: 캐릭터 SSOT/컨셉 규칙 요약
- `txt`: 프롬프트 초안
- `json`: 프레임 비율, 스타일, 프롬프트 옵션
- `reference_image`: 정면 기준 아트 레퍼런스 (옵션)

## output_contract
- `png`: 최종 캐릭터 콘셉트 아트
- `json`: 콘셉트 메타데이터(스타일, 파일 경로, seed)

## node_harness
1. `concept.design.generate` (`md`,`txt`,`json` -> `json`,`png`)
2. `concept.pixel.generate` (`json`,`png` -> `json`,`png`)
3. `concept.keyframe.compose` (`json`,`png` -> `json`,`png`)
4. `concept.animation.render` (`json`,`png` -> `json`,`png`)

## package_contract
- package_id: `character-concept-art-generator`
- manifest: `workflow/pipelines/character_concept_art_generator.py`
- command: `scripts/workflow/run_character_concept_art_pipeline.sh`
- dependency: `workflow/nodes/concept_image/packages`
- model: `workflow/nodes/concept_image/packages/model-registry.json`

## standards
- 기준 캐릭터 비율/얼굴형상은 새 SRPG 아트 기준에서 정의한다. 이전 액션 캐릭터 레퍼런스는 폐기했으며 새 기준 이미지는 아직 선정하지 않았다.
- 얼굴 형상, 체형, 신발/복장 컬러는 현재 프로젝트 SSOT/운영 규칙을 최우선으로 따른다.
- 생성 산출물은 `artifacts/ai-design/references/generated/characters/` 하위에 임시 임시산출 후, 파이프라인 소비자가 필요 시 게임 자산 경로로 반영한다.

## future_extension_plan
- `prompt.compose`를 SSOT 프롬프트 블록으로 확장
- `image.refine`에 스타일/얼굴 보정 게이트 추가
- 프레임별 QA(얼굴 기준점/비율/등신비) 자동 검사 추가
