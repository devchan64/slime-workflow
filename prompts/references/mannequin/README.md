# 프롬프트 참고용 마네킨

캐릭터 생성에 사용하는 신체·얼굴 비율 참고 이미지다. 현재 캐릭터 생성 신체 비율 기준은 [현재 전신 참조 목록](../../../baseline/mannequin/body-reference-catalog.yaml)이다. 아래 연구 이미지는 과거 후보이며 생성기에서 자동 채택하지 않는다. 각 YAML에는 실제 생성 프롬프트와 생성 기록을 보존한다.

## 현재 중성형 신체 기준

사용자가 지정한 첨부 이미지를 `baseline/mannequin/`에 보관한다. 중성형 신체 참조에는 아래 파일을 사용하며, 보존된 연구 후보는 [연구 기록](research/README.md)에서 확인한다.

- [중성형 신체 4방향](../../../baseline/mannequin/neutral-body-four-directions.png)
- [출처·해시 기록](../../../baseline/mannequin/neutral-body-four-directions.yaml)

## 비율 기준

- **성인 평균 5등신**을 기준으로 체형에 맞게 조절한다. 모든 유형을 정확히 5등신으로 고정하지 않는다.
- 아동은 성인 기준보다 큰 머리와 짧은 팔다리로 표현한다. 청소년·노년 전용 시트는 현재 제공하지 않는다.
- 캐릭터 제작용 참고 후보이며 실제 연령별 표준 신체치수가 아니다. 정확한 등신과 방향별 일관성은 사용 전에 검수한다.

## 신체 목록

모두 관절이 분리된 마네킨이다. 머리 대비 몸통·팔다리 길이와 관절 위치를 참고한다.

| 유형 | 선택 기준 | 이미지 | 생성 기록 |
| --- | --- | --- | --- |
| 중성 기본형 | 성별 체형 강조를 줄인 기본 신체 후보 | [PNG](research/v1/neutral-body-four-directions-v1.png) | [YAML](research/v1/neutral-body-four-directions-v1.yaml) |
| 남성 기본형 | 기본 남성 비율 | [PNG](research/v1/male-body-four-directions-v1.png) | [YAML](research/v1/male-body-four-directions-v1.yaml) |
| 남성 넓은 어깨형 | 넓은 어깨와 큰 흉곽 | [PNG](research/v1/male-broad-shoulders-four-directions-v1.png) | [YAML](research/v1/male-broad-shoulders-four-directions-v1.yaml) |
| 남성 슬림형 | 좁은 몸통과 가는 팔다리 | [PNG](research/v1/male-slim-four-directions-v1.png) | [YAML](research/v1/male-slim-four-directions-v1.yaml) |
| 남성 통통형 | 둥근 복부와 부드러운 부피 | [PNG](research/v1/male-full-four-directions-v1.png) | [YAML](research/v1/male-full-four-directions-v1.yaml) |
| 여성 기본형 | 기본 여성 비율 | [PNG](research/v1/female-body-four-directions-v1.png) | [YAML](research/v1/female-body-four-directions-v1.yaml) |
| 여성 슬림형 | 좁은 몸통과 가는 팔다리 | [PNG](research/v1/female-slim-four-directions-v1.png) | [YAML](research/v1/female-slim-four-directions-v1.yaml) |
| 여성 통통형 | 둥근 복부와 부드러운 부피 | [PNG](research/v1/female-full-four-directions-v1.png) | [YAML](research/v1/female-full-four-directions-v1.yaml) |
| 아동 중성형 | 큰 머리와 짧은 팔다리 | [PNG](research/v1/child-neutral-four-directions-v1.png) | [YAML](research/v1/child-neutral-four-directions-v1.yaml) |

## 피부·기본복 적용 기준

사용자가 마네킨과 신체 비율이 맞는 결과로 확인한 정면 참조다. 전신 마네킨만 입력해 피부와 밀착 기본복을 적용했으며, 얼굴 이목구비와 머리카락은 없다. 이후 얼굴을 추가할 때 이 신체 비율을 유지한다.

| 유형 | 이미지 | 생성 기록 |
| --- | --- | --- |
| 피부·기본복 정면 | [PNG](research/v1/body-skin-clothes-front-v1.png) | [YAML](research/v1/body-skin-clothes-front-v1.yaml) |

## 얼굴 목록

사용자가 채택한 현재 기본형 얼굴을 사용한다. 눈 간격·크기, 코·입 위치와 턱선을 참고한다. 머리카락·피부색·고유 인상은 캐릭터별 입력으로 지정한다.

| 유형 | 이미지 | 생성 기록 |
| --- | --- | --- |
| 중성 기본 얼굴 | [PNG](../../../baseline/mannequin/neutral-head-basic-four-directions.png) | [YAML](../../../baseline/mannequin/neutral-head-basic-four-directions.yaml) |

## 사용 방법

1. 신체와 얼굴의 참고 역할을 구분해 필요한 이미지를 선택한다.
2. [공통 화풍](../../common/art-style.md)과 [캐릭터 외관 기준](../../common/character-appearance.md)을 함께 적용한다. 관절 틈·회색 표면·기계 구조는 캐릭터 외형에 복제하지 않는다.
3. 4방향 시트의 2×2 배치는 **좌상 정면 · 우상 앞쪽 쿼터 · 좌하 측면 · 우하 후면**이다. 일부 쿼터·측면의 좌우가 다르므로 연속 회전 시퀀스로 사용하지 않는다.

참고 이미지 등록은 생성기의 기본 입력을 자동 변경하지 않는다. 이미지 참조 없이 생성하라는 요청에는 첨부하지 않는다.

## 관리 규칙

- 이미지와 실제 생성 프롬프트 YAML을 함께 관리한다. 실험 버전은 `research/<버전>/`에 저장하고 목록을 갱신한다. 채택한 현재 기준은 `baseline/mannequin/`에서 관리한다.
- 새 유형은 이름보다 신체 비율과 실루엣의 구별 가능성을 기준으로 추가한다. 유사 유형을 제거할 때 이미지·YAML·색인을 함께 정리한다.
- 변경 내역은 [공통 프롬프트 변경 이력](../../common/CHANGELOG.md)에 기록한다.

## 생성 결과 저장 위치

새 이미지 생성·수정 결과는 `baseline/mannequin/`에 직접 저장하지 않는다. `research/<버전>/`에 이미지와 생성 기록을 보존하고, 사용자가 반영을 지시한 경우에만 `baseline/mannequin/`을 갱신한다.

## 현재 기본형 얼굴

- [중성형 기본 얼굴](../../../baseline/mannequin/neutral-head-basic-four-directions.png)
- [생성·등록 기록](../../../baseline/mannequin/neutral-head-basic-four-directions.yaml)

사용자가 연구 v10을 채택한 현재 기본형 얼굴이다. 이전 얼굴 연구 원본은 사용자 요청으로 폐기했다.
