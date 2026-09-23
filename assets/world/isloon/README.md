# 이슬온 타일 맵

이 디렉터리는 RPG 쯔꾸르 방식의 공용 타일·건물 프리셋·맵 원본을 관리한다.

## 조립

```bash
python3 generators/worldbuilding/isloon_tiles.py \
  --map assets/world/isloon/maps/village-01.yaml \
  --output .tmp/isloon-village-assembled.json
```

## 검수

조립 결과 JSON을 `tools/review/isloon-map-review.html`에서 파일 선택으로 연다.
타일 원본은 `tile-catalog.yaml`, 구조물은 `building-prefabs.yaml`, 맵 배치는 `maps/*.yaml`에서 수정한다.
