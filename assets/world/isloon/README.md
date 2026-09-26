# 이슬온 타일 맵

이 디렉터리는 이슬온의 RPG 쯔꾸르 방식 공용 타일·건물 프리셋·맵 원본을 관리한다.

정식 맵은 `maps/iseulon.yaml`이며, 세계 확장 설정의 24×24 안전 도시 배치(청록 샘터, 꽃 화단, 길드 회관·서점·여관·대장간·시장, 서·동·남 출구)를 따른다. 이슬온의 길드 회관·대장간·시장(상점)은 대리석으로 지어진 건물이며, 해당 프리팹은 `marble_wall`과 `marble_small_door`를 사용한다. 서점과 여관은 목재건물로 정의했으며, 목재 벽·문 타일은 향후 생성 후 프리팹 참조를 교체한다. 최종 타일 이미지는 `slime-frontend/src/assets/world/isloon/`에 둔다.

## 조립

```bash
python3 generators/worldbuilding/isloon_tiles.py \
  --map assets/world/isloon/maps/iseulon.yaml \
  --output .tmp/isloon-assembled.json
```

## 검수

`python3 tools/review/build_map_review.py --output .tmp/isloon-map-review`로 검수 패키지를 만들고, `map-review.html`을 연다. 통합 관리도구에서는 `타일맵검수` 항목으로 연다.

타일 원본은 `tile-catalog.yaml`, 구조물은 `building-prefabs.yaml`, 맵 배치는 `maps/*.yaml`에서 수정한다. 후보 생성 결과는 `.tmp/<한국시간>/`에만 두며, 검수 후에만 프론트엔드 에셋 경로에 등록한다.
