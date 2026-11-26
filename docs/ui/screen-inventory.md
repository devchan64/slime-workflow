# 관리 GUI 화면 목록

2026-11-26 소스 기준의 검수 대상 목록이다. `gui/app.jsx`의 독립 라우트와 대화 내 생성기 연결, `workflow/common/management_catalog.py`의 관리 메뉴 기본 항목을 대조했다. 연결이 있다는 사실은 실제 노출, 작동이나 가이드 준수를 뜻하지 않는다. 최신 화면별 확인 조건과 남은 항목은 [적용 현황](adoption-status.md)을 따른다.

| 영역 | 독립 화면 또는 경로 | 대화 내 경로 | 후속 검수 범위 |
| --- | --- | --- | --- |
| 운영 대화 | `hermes-agent` | 대화 본문, 도구 선택, 생성 제안·저장 폼, 질문 폼, 대기열·GPU 패널 | 각 상태의 초점, 오류와 복구, 대화 전환 |
| 이미지 생성 | `minimax-h3-image-generator`; `flux-{image,character,mannequin,billboard,prop,vegetation,building,seamless,expression}-generator` | 각 생성 폼 및 FLUX 제안 폼 | 프로필별 입력·참조·이력 복원, 독립/내장 상태 |
| 영상·동작 생성 | `wan22-fun-control-generator`, `wan22-vace-generator`, `wan22-i2v-generator`, `wan22-animate2-generator`, `minimax-h3-i2v-generator`, `minimax-h3-ref2va-generator`, `dwpose-generator`, `kimodo-generator` | 각 생성 폼; Fun Control과 Kimodo는 별도 내장 연결 | 입력·이력·결과와 접기, 오류 복구 |
| 종료 영상 호환 | `wan21-t2v-generator`, `wan21-i2v-generator` | 코드 연결은 남아 있으나 현재 대화 도구 목록에서는 제외 | 기존 이력·결과와 종료 안내; 실제 내장 접근은 별도 확인 |
| 오디오·텍스트 | `music-heartmula`, `sfx-dasheng-audiogen`, `prompt-translation`, `writer-agent` | 각 생성 폼 | 입력·이력·결과, 음악·효과음 재생 중 접기와 오류 |
| 모델 관리 | `model-management` | 생성기의 모델 준비 링크로 이동 | 목록·카탈로그·백업 비교의 조회 상태와 선택 복구 |
| 편집·에셋 | `sprite-sheet-editor`, `effect-editor`, `building-editor`, `asset-editor` | 대화의 빌보드 검색 등은 별도 선택 흐름 | 원본 선택, 편집·검수, 저장·내보내기의 안전한 검증 범위 |
| 지도 | `world-map`; 도시·필드 지도와 전투필드 검수 | 대화에서 지도 검수로 이동 | 선택·확대·연결, 로딩 오류, 초안과 그래픽 표시 |
| 게임 UI 정적 검수 | 디자인 시스템, 전투 레이아웃 검수 HTML | 도구 목록에서 독립 문서로 이동 | 게시본과 소스의 일치, 확대·키보드·그래픽 렌더 |
| 보관·검색 | `/management/assistant/qwen-archive`; 대화의 표정·빌보드·키프레임 검색 | 대화 검색 패널 | 빈 결과·검색 변경·오류 복구와 선택 |

표의 짧은 독립 화면 이름은 일반적으로 `/management/frame/<이름>/`을 뜻한다. 일부 화면은 `/management/assistant/` 별칭도 있으며 도시·필드 지도는 게이트웨이의 맵별 경로와 매개변수로 연결된다.

2026-11-26 실행 중인 `/management/assistant/tools` 응답에는 운영 대화를 제외한 31개 항목이 있었다. 그중 도시맵은 `/management/frame/map-review/?map=iseulon&townPage=1`로, 게임 UI의 디자인 시스템과 전투 레이아웃은 각각 `/ui-8818ca726cdfbb08/review/design-system.html`, `/ui-8818ca726cdfbb08/review/battlefield-preview.html`로 연결됐다. 두 정적 문서는 HTTP 200으로 응답했으며, 이 확인은 내용·조작 검수가 아니다. UI 번들 경로는 게시 버전에 따라 달라질 수 있다.

게이트웨이와 실제 리디렉션을 확인한 결과 기존 `animation-1` 및 `animation-2` 관리 진입점은 스프라이트 시트 편집기로 연결됐다. 대화 도구 목록은 등록된 애니메이션 항목을 제외할 수 있으므로 이 응답만으로 모든 과거 앵커·걷기 비교 산출물의 존재나 화면 상태를 판정하지 않는다. 메뉴 원본의 다른 맵별 항목과 그 밖의 비 React 화면은 추가 대조가 필요하다. 현재 문서는 전체 경로 대조 완료나 전체 검수 완료의 근거가 아니다.

검수는 사용자 우선순위에 따라 데스크톱과 200% 확대부터 진행하고 모바일은 후순위로 둔다. 기존 작업을 중단하거나 검수용 GPU 작업을 접수하지 않는다. 저장·삭제 등 실제 데이터 변경이 필요한 흐름은 수행 여부와 미검증 범위를 분리해 기록한다.
