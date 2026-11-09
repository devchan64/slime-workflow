# 기본 캐릭터

중성형 기본 캐릭터의 현재 등록 자료다. 귀 길이의 갈색 머리, 호박색 눈, 가는 눈썹과 회색 밀착 기본복을 사용한다.

4방향 등록 자료는 사용자 요청으로 폐기했다. 생성기 기본 입력은 자동 변경하지 않는다.

## 8방향 시트

- [8방향 전신](baseline-v1/character-default-eight-directions-v1.png)
- [생성 기록](baseline-v1/character-default-eight-directions-v1.yaml)

4열×2행. 위 행은 정면부터 화면 오른쪽 방향으로 회전한 앞 쿼터·측면·뒤 쿼터, 아래 행은 후면부터 화면 왼쪽 방향의 뒤 쿼터·측면·앞 쿼터 순서다.

## 대기 애니메이션 기준 시트

사용자가 지정한 [쿼터뷰 눈 깜박임 8프레임 시트](baseline-v1/character-default-baseline-idle-blink-front-left-v1.png)와 [기준 정보](baseline-v1/character-default-baseline-idle-blink-front-left-v1.yaml)를 관리한다. 4열×2행이며 배경 잔여물과 프레임 간 차이가 있어 재생·앵커 검수가 필요하다. 기존 게임 대기 애니메이션과는 별도다.

## 정면 개별 이미지

얼굴 정면은 사용자가 채택한 컷인 참조 헤어스타일·화풍 개선본이다. 전신 정면은 최신 8방향에서 생성한 v7을 채택했으며, 각 이미지와 같은 이름의 YAML에서 기록을 관리한다.

- [얼굴 정면](baseline-v1/character-default-face-front-v1.png)
- [전신 정면](baseline-v1/character-default-body-front-v1.png)

제작·검수·등록 절차: [마네킨 기반 기본형 관리](../../../workflows/character-baseline-mannequin.md)

## 채택 이력

얼굴은 화풍 수정 v5, 8방향은 얼굴 적용 v6, 전신 정면은 v7 결과를 baseline-v1에 등록했다. 이전 실험 파일은 현재 보관하지 않으며 생성 당시 출처는 각 YAML에 기록한다.

## 2026-11-09 가슴 형태 보정

8방향·정면 전신·쿼터뷰 전신·걷기·눈 깜박임 시트의 가슴 윤곽과 상의 음영을 평평하게 보정했다. 걷기 시트는 크기와 프레임 위치가 변경되어 셀 분할·앵커·루프 재검수가 필요하다. 휴식 시작·해제 시트도 보정본으로 교체하고 기존 프레임별 앵커를 크기 비율로 변환했다. 앵커의 미세 검수는 필요하다. 눈 깜박임 시트는 기존처럼 배경 잔여물과 프레임 간 위치 차이에 대한 검수가 필요하다.
