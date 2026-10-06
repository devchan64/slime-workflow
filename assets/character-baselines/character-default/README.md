# 기본 캐릭터 제작 참조

기본 캐릭터의 얼굴·신체·복장 기준 이미지와 대기 애니메이션 생성 프롬프트를 관리한다. 게임 런타임용 애니메이션 시트와 구분한다.

## 기준 이미지

| 파일 | 용도 |
| --- | --- |
| [face-baseline.png](face-baseline.png) | 얼굴·머리카락 아이덴티티 참조 |
| [body-baseline.png](body-baseline.png) | 신체 비율 참조 |
| [light-armor-baseline.png](light-armor-baseline.png) | 가벼운 보호구 착용 참조 |
| [medium-armor-baseline.png](medium-armor-baseline.png) | 중간 보호구 착용 참조 |
| [heavy-armor-baseline.png](heavy-armor-baseline.png) | 무거운 보호구 착용 참조 |

## 복장 분리 이미지

- [light-armor-outfit.png](light-armor-outfit.png): 가벼운 보호구 복장
- [medium-armor-outfit.png](medium-armor-outfit.png): 중간 보호구 복장
- [heavy-armor-outfit.png](heavy-armor-outfit.png): 무거운 보호구 복장

복장 분리 이미지는 의상 제작 참조다. 착용 시트와 픽셀 단위로 정렬된 합성 레이어임을 보장하지 않는다.

## 대기 애니메이션 생성

아이덴티티와 신체 비율 유지를 우선하며 짧은 프롬프트를 사용한다. 같은 키에서 얼굴 크기, 어깨·허리 폭과 팔다리 두께가 달라지지 않는지 확인한다.

1. [1~4프레임 프롬프트](idle-animation-generation-prompt-01-04.txt): 단일 방향 전신 참조로 기본 자세에서 들숨 정점 직전까지 생성한다.
2. [5~8프레임 프롬프트](idle-animation-generation-prompt-05-08.txt): 참조 1은 같은 전신 이미지, 참조 2는 첫 번째 생성 시트다. 들숨 정점에서 날숨을 거쳐 기본 자세로 돌아오는 구간을 생성한다.

각 시트는 좌측 앞 방향의 가로 4칸이며 왼쪽부터 재생한다. 프롬프트는 공백 기준 각각 50단어와 51단어다. 투명 배경을 요청하지만 실제 결과의 알파는 별도 확인해야 한다. 두 시트 사이 크기·발 기준점·4→5 및 8→1프레임 연결을 검수한 뒤 사용한다.

실험 결과와 로그는 `.tmp/test/<experiment-name>/<YYYY-MM-DD_HH-mm-ss>/`에 보관한다. 생성 결과를 이 폴더나 게임 런타임에 자동 등록하지 않는다. 이전 기준 파일과 등록 기록은 Git 이력에서 확인한다.

## 걷기 샘플 아이덴티티 적용

[걷기 아이덴티티 적용 프롬프트](walking-identity-generation-prompt.txt)는 개별 걷기 프레임에 외형을 적용할 때 사용한다.

- 이미지 1: 아이덴티티 베이스라인. 얼굴 크기·머리 대비 키·몸통 폭·팔다리 길이와 둘레·머리카락·복장·렌더링을 따른다.
- 이미지 2: 해당 프레임의 원본 걷기 포즈. 관절 각도와 발 배치만 참조하며 체격은 가져오지 않는다.

세 번째 걷기 샘플 재생성에 사용한 프롬프트를 그대로 등록했다. 좌측 앞 방향·눈높이 시점이며 양발을 분리하고 화면 왼쪽 발을 높게, 오른쪽 발을 낮게 배치하는 지시가 포함된다. 다른 프레임에 적용할 때는 이 발 배치 문장을 해당 원본 포즈에 맞게 수정한다. 베이스라인 대비 체격·비율과 원본 포즈 대비 발 모양을 함께 검수한다. 투명 배경은 결과 알파를 확인한다.

## 대기·휴식 전환 시트

사용자 지시로 등록한 경량 보호구 전환 참조다. 대기→휴식 8프레임과 휴식→대기 8프레임, 총 16프레임을 4장으로 관리한다. 각 시트는 왼쪽에서 오른쪽으로 재생한다.

| 구간 | 이미지 | 생성 프롬프트 |
| --- | --- | --- |
| 대기→휴식 1~4 | [시트](light-armor-idle-to-rest-1-4.png) | [프롬프트](idle-to-rest-generation-prompt-01-04.txt) |
| 대기→휴식 5~8 | [시트](light-armor-idle-to-rest-5-8.png) | [프롬프트](idle-to-rest-generation-prompt-05-08.txt) |
| 휴식→대기 1~4 | [시트](light-armor-rest-to-idle-1-4.png) | [프롬프트](rest-to-idle-generation-prompt-01-04.txt) |
| 휴식→대기 5~8 | [시트](light-armor-rest-to-idle-5-8.png) | [프롬프트](rest-to-idle-generation-prompt-05-08.txt) |

휴식 자세는 양반다리다. 최초 입력은 사용자 첨부 단일 방향 전신 이미지이며, 이후 구간에는 같은 원본과 직전 시트를 함께 참조했다. 내장 이미지 생성 도구로 제작했으며 실행 출처는 `.tmp/test/light-armor-rest-transitions/2026-10-06_22-40-25/`다. 이 실행 경로는 출처 확인용이며 런타임 의존성이 아니다.

등록 이미지는 갈색 배경을 포함한다. 시트 간 크기·지면 정렬, 캐릭터 비율과 동작 연속성은 아직 검증하지 않았다. 게임용 프레임 정규화 및 런타임 채택과 구분한다.
