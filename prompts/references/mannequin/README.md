# 프롬프트 참고용 마네킨

캐릭터 생성 시 신체 비율과 얼굴 이목구비 비율을 전달하는 참고 이미지다. 게임 캐릭터 에셋이나 모션 생성 결과가 아니다. 현재 버전은 v1이며 정확한 5등신·방향 일관성은 검수 전이다.

| 역할 | 이미지 | 실제 생성 프롬프트·기록 |
| --- | --- | --- |
| 남성 신체 · 관절 분리 | [PNG](v1/male-body-four-directions-v1.png) | [YAML](v1/male-body-four-directions-v1.yaml) |
| 여성 신체 · 관절 분리 | [PNG](v1/female-body-four-directions-v1.png) | [YAML](v1/female-body-four-directions-v1.yaml) |
| 남성 얼굴 이목구비 | [PNG](v1/male-head-four-directions-v1.png) | [YAML](v1/male-head-four-directions-v1.yaml) |
| 여성 얼굴 이목구비 | [PNG](v1/female-head-four-directions-v1.png) | [YAML](v1/female-head-four-directions-v1.yaml) |

## 사용 규칙

- 배치는 2×2이며 좌상 정면, 우상 앞쪽 쿼터, 좌하 측면, 우하 후면이다. 일부 쿼터와 측면의 좌우가 다르므로 연속 회전 시퀀스로 간주하지 않는다.
- 신체 마네킨은 머리 대비 몸통·팔다리 길이와 관절 위치를 참고한다. 관절 틈·회색 표면·기계 구조를 캐릭터 외형에 복제하지 않는다.
- 헤드 마네킨은 눈 간격·크기, 코·입 위치와 턱선을 참고한다. 머리카락·피부색·고유 인상은 캐릭터별 입력에서 지정한다.
- 화풍은 [공통 화풍 문서](../../common/art-style.md), 외관은 [캐릭터 외관 문서](../../common/character-appearance.md)를 함께 사용한다. 이미지의 역할을 각각 명시한다.
- 이미지 참조 없이 생성하라는 요청에는 첨부하지 않는다. 참고 등록만으로 생성기 기본 입력에 자동 적용하지 않는다.
- 새 버전은 새 디렉터리에 이미지와 실제 사용한 프롬프트 YAML을 함께 보존하고 이 색인을 갱신한다.

2026-10-31: 사용자 요청에 따라 `assets/character-baselines/mannequin-standards/v1/`에서 이 경로로 이전했다. 기존 별도 5.5등신 마네킨 자료는 이번 이전 대상이 아니다.
