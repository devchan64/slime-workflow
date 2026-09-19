# sprite-8dir-from-concept

- pipeline_id: `sprite-8dir-from-concept`
- version: `0.1.0`
- status: `active`

## input_contract
- `design_sheet:png`: 8방향 원본이 1행 8열로 배치된 캐릭터 디자인시트
- `frame_width:json`: 출력 프레임 너비
- `frame_height:json`: 출력 프레임 높이
- `layout:json`(optional): `source_grid` 또는 방향별 `source_regions`
- `character_id:json`(optional): 캐릭터 식별자
- `animation_id:json`(optional): 애니메이션 식별자

## output_contract
- `sprite_sheet:png`: 지정한 프레임 크기의 1행 8열 스프라이트 시트
- `sprite_meta:json`: 방향별 프레임 좌표와 원본 디자인시트 영역 메타데이터

## node_harness
1. `sprite.generate` (`png`,`json` -> `png`,`json`)

## package_contract
- package_id: `character-sprite.design-sheet-8dir`
- manifest: `workflow/nodes/character_sprite/packages/design-sheet-8dir.json`
- command: `scripts/workflow/run_character_sprite_pipeline.sh`
- dependency: `workflow/nodes/character_sprite/packages/requirements.txt`
- model: 없음. 디자인시트에서 결정적 재패킹만 수행한다.

## direction_order
1. `south`
2. `south_west`
3. `west`
4. `north_west`
5. `north`
6. `north_east`
7. `east`
8. `south_east`

## fail_fast_rules
- `design_sheet` 파일이 없으면 즉시 실패한다.
- `frame_width`, `frame_height`가 양수가 아니면 즉시 실패한다.
- `source_regions`를 사용하는 경우 정확히 8개이며 `direction_order`와 같은 순서여야 한다.
- `source_grid`를 사용하는 경우 기본값은 1행 8열이다.

## test_contract
- `--generate-test-resource`로 테스트 디자인시트 PNG를 생성한다.
- 기본 smoke 테스트는 64x96 프레임의 8방향 시트와 JSON 메타데이터를 생성한다.

## future_extension_plan
- 방향 누락 자동 보간 노드 추가
- 16방향 확장 버전(`v2`) 병행 운영
