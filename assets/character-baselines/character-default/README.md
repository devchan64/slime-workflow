# 캐릭터 애니메이션 참조 자산

이 폴더는 3참조 Qwen 포즈 전환 배치에서 재사용하는 방향별 참조 이미지다.

- `baseline-v2/`: 승인된 2×2 통합 시트·출처 sidecar와 512×512 방향별 분할 이미지
- `../../rigs/mannequin-walk/v1/pose-sheets-v1/`: 통합 관리되는 2048×1024 OpenPose 4×2 시트

생성 목록과 참조 경로는 `generators/animation/config/pose_transfer_3_reference_qwen_default_walk.yaml`에서 워크플로 루트 기준 상대 경로로 관리한다. 입력 자산을 변경할 때는 실행 목록과 해시를 함께 갱신한다.

## 기준 시트 원본

`baseline-v2/`에서 통합 시트와 방향별 분할 이미지를 함께 관리한다. 통합 시트의 같은 이름 YAML은 셀 좌표·출처·해시를 기록한다. 상위 `manifest.yaml`의 `baseline_source`는 통합 시트, `baseline_crops`는 분할 이미지를 가리킨다. 두 표현은 같은 베이스라인 버전이며 별도 원본 폴더를 만들지 않는다. 게임 런타임에서 사용하지 않는다.

## 기본 캐릭터 정면 얼굴 기준

`face-front-v1/`는 승인된 정면 얼굴 레퍼런스다. 얼굴 비율·갈색 헤어·눈동자·피부색의 제작 기준으로 사용하며 `manifest.yaml`의 `face_reference`에서 원본과 해시를 확인한다. 전신 애니메이션의 방향·체형 참조는 기존 `baseline-v2/`를 사용한다.

## 기본 캐릭터 복장 분리 베이스라인

`separated-baseline-v3/`은 채택된 768×768 RGBA 4방향 분리 레퍼런스다. `body-base/`에는 신체 베이스, `outfit/`에는 복장과 신발을 보관한다. 방향은 `down_left`, `down_right`, `up_left`, `up_right`이며 파일을 리사이즈하거나 알파 보정하지 않고 생성 결과 그대로 등록했다.

하위 `manifest.yaml`에서 관리 ID·불변 버전·방향별 생성 ID·원본 참조·이미지 해시·모델 및 프롬프트 해시를 관리한다. 상위 manifest의 `separated_baseline`이 등록부를 연결한다. 두 레이어는 독립 생성 결과이며 합성 시 위치·실루엣 검수가 필요하다. 기존 `baseline_crops`는 복장 착용 참조로 유지하며, 이번 등록은 애니메이션 생성 입력이나 게임 런타임의 자동 교체를 의미하지 않는다.

## 신체 베이스 v2

현재 애니메이션 입력은 `body-baseline-v3.yaml`과 `separated-baseline-v3/body-base/`다. 전방 좌측(`down_left`)만 승인된 생성 `2026-10-05_15-51-51-a32c9638`의 신체 베이스로 교체했다. 나머지 3방향은 v1을 유지한다. 복장 결과는 교체하지 않으며 생성 출처를 통합 manifest에 보존한다. 이전 파일 버전은 Git 이력에서 확인하며 별도 신체 폴더와 중복 이미지는 유지하지 않는다.

## 신체 베이스 v3

후방 좌측(`up_left`)을 승인된 생성 `2026-10-05_15-57-37-2c4fc3a7`의 신체 베이스로 교체했다. 전방 좌측은 v2의 승인 결과를 유지하며 나머지 두 방향과 복장은 변경하지 않았다. 현재 통합 폴더는 `separated-baseline-v3/`이며 이전 버전은 Git 이력에 보존한다.

## 경량 방어복 4방향 기준 v1

[착용 시트](light-armor-four-directions-v1/default-light-armor-four-directions.png) · [등록 기록](light-armor-four-directions-v1/manifest.yaml) · [50% 오버랩](light-armor-four-directions-v1/baseline-armor-overlay-50.png) · [교대 비교 GIF](light-armor-four-directions-v1/baseline-armor-toggle.gif)

흰 셔츠 4방향 시트 `baseline-v2/character-default-white-shirt-four-directions-v2.png`를 신체 비율 기준으로 사용한 경량 가죽 방어복입니다. 위는 후면좌측·후면우측, 아래는 정면좌측·정면우측입니다. 사용자 요청으로 원본·프롬프트·검수 자료를 등록했습니다. 분리된 outfit 레이어는 아니며 기존 신체 기준과 생성기 입력은 유지합니다.

### 경량 방어복 분리 이미지

[정면좌측 outfit](light-armor-four-directions-v1/outfit-down-left-v1.png) · [첨부 출처·해시](light-armor-four-directions-v1/outfit-down-left-v1.yaml). 사용자 첨부 원본을 가공 없이 추가 보존했습니다.
