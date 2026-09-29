# 공용 이미지 엣지 검출·보더 크롭 라이브러리

`image_edges.py`의 `trace_black_border(image)`는 네 변의 안쪽 경계와 주사선별 검출 깊이를 반환한다. `crop_traced_tile(image, output_tile_size=256, retained_edge_pixels=2)`는 크롭 이미지·경계 기록·원본 크롭 좌표를 반환한다. 원본 파일이나 이력은 직접 수정하지 않는다.

- RGB 최대 채널 48 이하, 채널 차이 16 이하를 검은 프레임으로 판단한다. 어두운 회색·유색 텍스처가 검정에 포함되지 않도록 범위를 제한한다.
- 모서리를 제외한 각 변 중앙 70%에서 바깥쪽 25% 깊이까지 탐색한다.
- 연속 검정 3픽셀 뒤 연속 비검정 3픽셀이 나타나는 지점을 안쪽 경계로 기록한다.
- 각 변에서 60% 이상의 주사선이 검출돼야 하며, 중앙값으로 돌출 풀잎 등의 영향을 줄인다. 검출 실패는 예외로 보고하며 수동 좌표로 대체하지 않는다.
- 남길 두께는 **최종 출력 픽셀 기준**이다. 원본 여유는 `내용물 길이 × 남길 두께 / (출력 크기 − 2 × 남길 두께)`로 환산한다.
- 직사각형 크롭이므로 불규칙한 테두리의 모든 지점에서 정확히 2px를 보장하지 않는다. 검은 선을 덧그리거나 내용물 경계를 펴지 않으며 중앙값 기준 두께를 유지한다.
- 출력은 지정한 정사각형 규격으로 Lanczos 축소한다. 반복 배치의 무봉제 품질은 별도 검수 대상이다.

승인 에셋에 적용할 때 원본 생성 ID·해시, 크롭 좌표, 추적 경계와 출력 해시를 출처 sidecar에 기록한다. 프론트엔드는 전달된 PNG만 사용하며 이 모듈을 런타임 의존성으로 사용하지 않는다.

## 바깥 → 검정 → 텍스처 경계 검출

`scan_border_transition(pixels)`는 바깥쪽부터 정렬한 한 주사선에서 다음 순서로 탐색한다.

1. 외부 여백을 지나 연속 검정 3픽셀을 찾는다.
2. 처음 검정 3픽셀의 채널별 중앙값을 기준색으로 고정하고 안쪽으로 이동한다.
3. 기준색과 RGB 채널 중 하나라도 12 이상 달라지거나 비검정색이 된 상태가 2픽셀 이어지면 첫 픽셀을 경계로 반환한다. 검정 분류 범위 안의 어두운 텍스처도 검출하며, 단일 픽셀 변화는 무시한다.

검정 뒤 흰 여백으로 되돌아오면 외곽 붓자국으로 보고 다시 검정을 탐색한다. 검정 없이 텍스처만 나타난 주사선은 경계를 추측하지 않는다.

`detect_texture_boundary(image)`는 왼쪽→오른쪽, 오른쪽→왼쪽, 위→아래, 아래→위로 모든 주사선을 탐색한다. 연결 영역 확장이나 중앙값으로 실제 경계를 대체하지 않는다. 기존 `trace_black_border`는 입력에 검은 프레임이 있는지 검증하는 용도로만 사용한다.

반환값은 원본 좌표계의 `texture_boundary_points`·`texture_boundary_mask`, 검정 구간 마스크 `black_frame_mask`, 네 방향 경계 내부의 `texture_region_mask`, `content_crop_bounds`다. `side_transition_records`에는 변별 `(검정 시작 좌표, 텍스처 시작 좌표)`를 보존한다. 경계 좌표는 행 우선으로 정렬되며 연결할 다각형 꼭짓점 목록은 아니다.

`render_texture_boundary(image, result)`는 텍스처 경계를 빨간색으로 표시한다. 검출은 원본을 수정하지 않는다. 색 기반 검출이므로 프레임의 색 얼룩이나 흰 텍스처는 잘못 구분될 수 있어 검수가 필요하다. 민감도를 높인 결과가 의미상 더 정확한지는 경계 표시와 크롭 결과로 검수한다.

`crop_border_contour(image, output_tile_size=256)`는 같은 검출 결과의 네 방향 내부 마스크로 외부를 투명 처리한 0px 크롭을 반환한다. 검출 근거가 없는 주사선의 영역은 제외한다. 직사각형 2px 크롭과 달리 불규칙한 투명 외곽을 가진다.

## 중심에 가까운 경계와 비율 보더

`crop_inner_border(image, retained_border_ratio=0.01)`는 각 변의 가장 안쪽 경계(왼쪽·위 최대값, 오른쪽·아래 최소값)로 텍스처 사각형을 구한다. 모서리 바깥에서 반대편 프레임까지 통과하는 주사선을 제외하기 위해 대표 경계 사각형의 교차축 범위 안에서만 경계 후보를 선택한다.

보더는 원본 텍스처 사각형의 `ceil(가로 × 비율)`을 좌우 각각, `ceil(세로 × 비율)`을 상하 각각 적용한다. 리사이즈·투명화·정사각형 변환 없이 원본 픽셀을 크롭한다. 반환하는 측정값에는 텍스처 경계·크기, 비율, 올림한 보더 픽셀, 최종 크롭 좌표가 포함된다. 검토용 결과는 실험 경로에 보관하며 사용자의 선택 전에는 정식 타일에 덮어쓰지 않는다.

## 공용 import

```python
from tools.review.common.image_edges import (
    detect_texture_boundary,
    render_texture_boundary,
)
from tools.review.common.image_borders import crop_inner_border

boundary_trace_result = detect_texture_boundary(source_image_value)
boundary_overlay_image = render_texture_boundary(source_image_value, boundary_trace_result)
cropped_image_value, crop_measurement_record = crop_inner_border(
    source_image_value, retained_border_ratio=0.01,
)
```

공용 함수는 Pillow 이미지를 받아 이미지·좌표·측정값을 반환한다. 파일 저장, 에셋 등록, 작업 게이트웨이 호출을 수행하지 않으며 다른 저장소의 소스·경로에 의존하지 않는다. 검출 설정 상수는 `image_edges.py`에서 관리한다. 보더 함수는 검출 모듈만 참조하며 검출 모듈은 보더 함수에 의존하지 않는다.

기존 `generators.terrain.tile_border_crop`는 import 호환 연결만 제공한다. 신규 소비 코드는 공용 모듈을 직접 사용한다.
