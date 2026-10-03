# 애니메이션 앵커 편집기 공통 컴포넌트

- `editor.html`: 저장 도구, 방향·프레임 선택, 좌표 편집, 미리보기의 공통 DOM.
- `editor.css`: 앵커 작업 영역 배치, 반응형 레이아웃과 Gradio 통합 스타일. 색상은 공용 관리도구 토큰을 사용한다.
- `editor.js`: 프레임 재생, 좌표 수정·실행 취소·복원, 캔버스와 JSON 내보내기.

Python 진입점은 `tools.review.ui_assets.read_animation_anchor_template()`다. HTML·CSS·JavaScript를 조립한 뒤 호출자가 `__FRAME_RECORDS__`, `__SOURCE_METADATA__`에 검증된 JSON을 삽입한다. 메타데이터에는 `gameRenderMetrics`가 필수다. 공용 색상은 기존 `read_review_shared_styles()`로 함께 삽입한다.

등록 에셋 검수, 생성 시트 검수, 프레임 관리 도구, 기존 스탠딩 검수 실행기가 동일 함수를 사용한다. 생성된 HTML은 외부 스크립트 요청 없이 독립 실행되며 이미지 경로와 내보내기 계약은 유지한다. 변경 후 이미 생성된 검수 사본은 다시 빌드해야 한다.

## 기본 캐릭터 통합 검수

기본 캐릭터 대기·휴식·걷기는 `animation-1` 메뉴에서 동작과 등록된 방향을 선택한다. 기존 `animation-2`, `animation-3` 메뉴 링크는 통합 검수로 연결한다. 동작 선택은 해당 원본 메타데이터를 사용하며 좌표 저장·불러오기·이력 초기화는 선택한 `animationId`와 `animationVersion`에 한정한다. 동작 전환 중 미저장 좌표는 탭의 sessionStorage에 출처·버전별로 임시 보관하며, 정식 저장은 좌표 저장 버튼으로만 수행한다.
