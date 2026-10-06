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
