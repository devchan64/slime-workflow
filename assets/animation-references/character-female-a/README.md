# 여성 캐릭터 참조 자산

`character-default`와 같은 기준 시트·방향별 셀·매니페스트 구조로 관리한다.

- 갈색 단발, 청록색 눈, 회색 긴팔 상의·카고 팬츠, 밝은 운동화.
- 신체 비율은 약 5등신을 목표로 생성했다.
- `baseline-v1/`: 2×2 통합 원본·출처 sidecar·크롭 좌표와 4방향 512×512 분할 참조를 함께 관리한다. 통합과 분할은 동일 베이스라인의 두 표현이며 별도 원본 폴더를 만들지 않는다.
- 후면은 얼굴 옆면이 드러나는 후면 3/4 구도다.
- 모션·포즈 맵 연결과 게임 런타임 채택은 별도다.

크롭은 원본의 실제 행 경계(y=614)를 사용한다. 공통 배율로 512×512 캔버스에 수평 중앙·하단 494px 기준으로 정렬하며 `baseline-v1/crop-layout.yaml`에 원본 영역과 배치 좌표를 기록한다.

## 정면 얼굴 베이스라인

`face-front-v1/`는 전신 좌하 참조를 기준으로 생성한 정면 얼굴이다. 갈색 단발·청록색 눈동자·피부색과 중립 표정을 유지하며 루트 매니페스트의 `face_reference`로 연결한다.

## 워크플로우 네임스페이스

현재 생성 설정의 캐릭터 ID는 `character-female-a`, 복장 분리 원본 ID는 `workflow:character-female-a`다. 자산 루트는 `assets/animation-references/character-female-a/`다. 기존 에셋 관리 ID·파일명·버전·이미지 해시는 유지한다. 저장된 과거 생성 요청의 `character-female`은 실행 당시의 식별자이며 소급 변경하지 않는다. 과거 요청에 기록된 `assets/animation-references/character-female/`는 현재의 `assets/animation-references/character-female-a/`에 해당한다.

## 여성 캐릭터 A 복장 분리 베이스라인

`separated-baseline-v1/`은 채택된 768×768 RGBA 4방향 분리 레퍼런스다. `body-base/`에는 신체 베이스, `outfit/`에는 복장과 신발을 보관한다. 방향은 `down_left`, `down_right`, `up_left`, `up_right`이며 파일을 리사이즈하거나 알파 보정하지 않고 생성 결과 그대로 등록했다.

하위 `manifest.yaml`에서 관리 ID·불변 버전·방향별 생성 ID·원본 참조·이미지 해시·모델 및 프롬프트 해시를 관리한다. 상위 manifest의 `separated_baseline`이 등록부를 연결한다. 두 레이어는 독립 생성 결과이며 합성 시 위치·실루엣 검수가 필요하다. 기존 `baseline_crops`는 복장 착용 참조로 유지하며, 이번 등록은 애니메이션 생성 입력이나 게임 런타임의 자동 교체를 의미하지 않는다.
