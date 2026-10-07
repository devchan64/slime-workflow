# 기본 캐릭터 제작 참조

기본 캐릭터의 얼굴·신체·복장 기준 이미지와 대기 애니메이션 생성 프롬프트를 관리한다. 게임 런타임용 애니메이션 시트와 구분한다.

## 프롬프트 관리

모든 프롬프트 원문과 단어 수는 [generation-prompts.yaml](generation-prompts.yaml) 한 파일에서 관리한다. `prompts`의 용도별 `text`를 선택하며 `base-prompt`를 자동으로 덧붙이지 않는다. 걷기는 `prompts.walking-identity-generation-prompt.text` 뒤에 `walking_pose_auxiliaries.frames`의 해당 `prompt`를 붙인다. 이미지 참조 순서와 원본 프레임 번호도 같은 YAML에 기록한다. 단어 수는 공백 기준이며 원문 변경 시 개별·합산 수치를 함께 갱신한다.

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

1. [1~4프레임 프롬프트](generation-prompts.yaml) (`prompts.idle-animation-generation-prompt-01-04`): 단일 방향 전신 참조로 기본 자세에서 들숨 정점 직전까지 생성한다.
2. [5~8프레임 프롬프트](generation-prompts.yaml) (`prompts.idle-animation-generation-prompt-05-08`): 참조 1은 같은 전신 이미지, 참조 2는 첫 번째 생성 시트다. 들숨 정점에서 날숨을 거쳐 기본 자세로 돌아오는 구간을 생성한다.

각 시트는 좌측 앞 방향의 가로 4칸이며 왼쪽부터 재생한다. 프롬프트는 공백 기준 각각 50단어와 51단어다. 투명 배경을 요청하지만 실제 결과의 알파는 별도 확인해야 한다. 두 시트 사이 크기·발 기준점·4→5 및 8→1프레임 연결을 검수한 뒤 사용한다.

실험 결과와 로그는 `.tmp/test/<experiment-name>/<YYYY-MM-DD_HH-mm-ss>/`에 보관한다. 생성 결과를 이 폴더나 게임 런타임에 자동 등록하지 않는다. 이전 기준 파일과 등록 기록은 Git 이력에서 확인한다.

## 걷기 샘플 아이덴티티 적용

[걷기 아이덴티티 적용 프롬프트](generation-prompts.yaml) (`prompts.walking-identity-generation-prompt`)는 개별 걷기 프레임에 외형을 적용할 때 사용한다.

- 이미지 1: 아이덴티티 베이스라인. 얼굴 크기·머리 대비 키·몸통 폭·팔다리 길이와 둘레·머리카락·복장·렌더링을 따른다.
- 이미지 2: 해당 프레임의 원본 걷기 포즈. 관절 각도와 발 배치만 참조하며 체격은 가져오지 않는다.

좌측 앞 방향·눈높이 시점의 개별 걷기 프레임에 공통으로 사용하는 프롬프트다. 특정 발의 높이·앞뒤 위치·다리 교차 여부를 문장으로 고정하지 않는다. 프롬프트는 동일하게 유지하고 이미지 2만 해당 프레임의 원본 포즈로 교체한다. 베이스라인 대비 체격·비율과 원본 포즈 대비 관절 각도·팔다리 겹침·발 배치·발끝 방향·접지를 함께 검수한다. 투명 배경은 결과 알파를 확인한다.

### 프레임별 포즈 보조 프롬프트

[12프레임 보조 프롬프트](generation-prompts.yaml) (`walking_pose_auxiliaries`)는 생성 기록 `2026-10-06_22-27-24-e7b5c525`의 `down_left` 원본 4·6·8·10·12·14·16·18·20·22·24·26번에 순서대로 대응한다. 공통 프롬프트 뒤에 해당 보조 문장을 붙이고 원본 포즈를 이미지 2로 첨부한다. 좌우는 화면 기준이며, 체격은 항상 이미지 1을 따른다. 개별·합산 단어 수를 YAML에 기록했다.

일반 프롬프트만 사용한 3번 검증에서 양발 높낮이가 반대로 생성되어 보조 프롬프트를 작성했다. 보조 문장은 원본 관찰에 기반하며 아직 생성 검증 전이다. 6번 원본에는 측면 참조 패널이 섞여 있어 중앙 전신만 참조하도록 명시했다. 보조 프롬프트를 사용한 3번 샘플부터 검증한 뒤 전체 생성으로 확대한다.

## 대기·휴식 전환 시트

사용자 지시로 등록한 경량 보호구 전환 참조다. 대기→휴식 8프레임과 휴식→대기 8프레임, 총 16프레임을 4장으로 관리한다. 각 시트는 왼쪽에서 오른쪽으로 재생한다. 원본 픽셀을 유지하며 프레임 사이에 투명 여백 60px씩을 추가했다. 시트 크기는 1716×1024다. 고정 384px 분할은 손과 신체를 가르므로 사용하지 않는다. 인물 사이의 배경 경계를 따라 나누고 각 인물을 0·60·120·180px 평행 이동했다. 손이 인접 프레임 영역으로 돌출된 곳은 꺾인 분할선을 사용하여 원본 픽셀을 보존했다.

| 구간 | 이미지 | 생성 프롬프트 |
| --- | --- | --- |
| 대기→휴식 1~4 | [시트](light-armor-idle-to-rest-1-4.png) | [프롬프트](generation-prompts.yaml) (`prompts.idle-to-rest-generation-prompt-01-04`) |
| 대기→휴식 5~8 | [시트](light-armor-idle-to-rest-5-8.png) | [프롬프트](generation-prompts.yaml) (`prompts.idle-to-rest-generation-prompt-05-08`) |
| 휴식→대기 1~4 | [시트](light-armor-rest-to-idle-1-4.png) | [프롬프트](generation-prompts.yaml) (`prompts.rest-to-idle-generation-prompt-01-04`) |
| 휴식→대기 5~8 | [시트](light-armor-rest-to-idle-5-8.png) | [프롬프트](generation-prompts.yaml) (`prompts.rest-to-idle-generation-prompt-05-08`) |

휴식 자세는 양반다리다. 최초 입력은 사용자 첨부 단일 방향 전신 이미지이며, 이후 구간에는 같은 원본과 직전 시트를 함께 참조했다. 내장 이미지 생성 도구로 제작했으며 실행 출처는 `.tmp/test/light-armor-rest-transitions/2026-10-06_22-40-25/`다. 이 실행 경로는 출처 확인용이며 런타임 의존성이 아니다.

등록 이미지는 갈색 배경을 포함한다. 시트 간 크기·지면 정렬, 캐릭터 비율과 동작 연속성은 아직 검증하지 않았다. 게임용 프레임 정규화 및 런타임 채택과 구분한다.
