# 도구 목록 · 생성기와 관리 기능

2026-11-25 운영 대화의 `/management/assistant/tools` 응답 33개를 기준으로 정리한 목록이다. 등록 이름과 제안 이름을 구분하며 일부 제안 이름을 카탈로그에 적용했으며 나머지는 검토 대상으로 유지한다. 목록은 기준 시점의 스냅샷이고 동적 맵·UI 항목은 실행 환경에 따라 달라진다. 실제 진입 가능 여부와 생성 성공을 보증하지 않는다.

## 이름과 분류 기준

- 생성기는 가능한 한 `모델 또는 서비스명 + 결과물 + 생성기`로 표기한다. 예: `Kimodo 모션 생성기`.
- 추출·편집·검수·관리·번역은 실제 행위를 이름에 사용한다. 생성 기능이 없는 항목에 생성기라는 이름을 붙이지 않는다.
- 화면에 보이는 명칭을 바꾸더라도 기존 ID, 서비스 이름, URL과 과거 이력은 호환성을 유지한다.
- 메뉴에 노출된 상태와 모델 파일 준비, 생성 서비스 실행 가능 상태는 각각 구분한다.

## 탐색 대상과 도구 분야

`탐색 대상`은 사용자가 찾는 정보의 종류를 고른다. 도구·관리 명령, 저장된 자료, 작업·검수 이력, 시스템 상태로 선택지를 묶는다. 관리 명령은 서비스가 제공하는 명령의 설명이고, 서비스 등록 상태는 서비스의 등록·연결 상태다. 생성 이력은 생성기별 결과이며 운영 작업 이력은 운영 작업의 기록이다.

`도구 분야`는 **도구 목록**을 선택했을 때만 표시하는 작업 영역 필터다. 음악·효과음, 모션·포즈·영상·편집, 이미지 생성, 맵·에셋 관리, 게임 UI, 모델 관리, 텍스트·번역으로 표시한다. 한 분야에 생성기와 편집기 등 여러 역할이 있을 수 있으며 항목 이름과 설명에서 역할을 구분한다. 등록되지 않은 분야는 목록에 표시하지 않는다.

화면의 분야 이름만 정리하며 내부 category ID와 기존 URL 매개변수, 이력, 검색 대상을 유지한다. 시스템 상태·저장된 자료·이력 선택에는 도구 분야 필터를 적용하지 않는다.

## 현재 탐색 목록

2026-11-26 실행 중인 8770의 도구 목록은 31개다. 아래 Wan 2.1 I2V·T2V 두 항목은 현재 도구 목록에 없지만 호환 경로가 HTTP 200을 반환해 별도 검토 대상으로 유지한다. 정적 검수 경로는 실행 중인 버전을 기록하며, HTTP 응답만으로 화면 사용성이나 기능 지원을 판정하지 않는다.

| 현재 이름 | 제안 이름 | 역할 | ID | 현재 경로 |
| --- | --- | --- | --- | --- |
| Dasheng-AudioGen 효과음 생성기 | Dasheng-AudioGen 효과음 생성기 | 생성기 | `sfx-dasheng-audiogen` | `/management/frame/sfx-dasheng-audiogen/` |
| DWPose 이미지 추출 | DWPose 포즈 추출 | 포즈 추출 | `dwpose-generator` | `/management/frame/dwpose-generator/` |
| FLUX 3 건물 생성기 | FLUX 3 건물 생성기 | 생성기 | `flux-building-generator` | `/management/frame/flux-building-generator/` |
| FLUX 3 마네킨 생성기 | FLUX 3 마네킨 생성기 | 생성기 | `flux-mannequin-generator` | `/management/frame/flux-mannequin-generator/` |
| FLUX 3 빌보드 가이드 생성기 | FLUX 3 빌보드 가이드 생성기 | 생성기 | `flux-billboard-generator` | `/management/frame/flux-billboard-generator/` |
| FLUX 3 소품 생성기 | FLUX 3 소품 생성기 | 생성기 | `flux-prop-generator` | `/management/frame/flux-prop-generator/` |
| FLUX 3 식생 생성기 | FLUX 3 식생 생성기 | 생성기 | `flux-vegetation-generator` | `/management/frame/flux-vegetation-generator/` |
| FLUX 3 심리스 타일 생성기 | FLUX 3 심리스 타일 생성기 | 생성기 | `flux-seamless-generator` | `/management/frame/flux-seamless-generator/` |
| FLUX 3 일반 이미지 생성기 | FLUX 3 일반 이미지 생성기 | 생성기 | `flux-image-generator` | `/management/frame/flux-image-generator/` |
| FLUX 3 캐릭터 생성기 | FLUX 3 캐릭터 생성기 | 생성기 | `flux-character-generator` | `/management/frame/flux-character-generator/` |
| FLUX 3 표정 생성기 | FLUX 3 표정 생성기 | 생성기 | `flux-expression-generator` | `/management/frame/flux-expression-generator/` |
| HeartMuLa 3B 음악 생성기 | HeartMuLa 3B 음악 생성기 | 생성기 | `music-heartmula` | `/management/frame/music-heartmula/` |
| Kimodo 모션 생성기 | Kimodo 모션 생성기 | 생성기 | `kimodo-generator` | `/management/frame/kimodo-generator/` |
| MiniMax H3 I2V 영상 생성기 | MiniMax H3 I2V 영상 생성기 | 생성기 | `minimax-h3-i2v-generator` | `/management/frame/minimax-h3-i2v-generator/` |
| MiniMax H3 이미지 생성기 | MiniMax H3 이미지 생성기 | 생성기 | `minimax-h3-image-generator` | `/management/frame/minimax-h3-image-generator/` |
| Wan 2.1 I2V 영상 생성기 | Wan 2.1 I2V 영상 생성기 | 생성기 | `wan21-i2v-generator` | `/management/frame/wan21-i2v-generator/` |
| Wan 2.1 T2V 영상 생성기 | Wan 2.1 T2V 영상 생성기 | 생성기 | `wan21-t2v-generator` | `/management/frame/wan21-t2v-generator/` |
| Wan Animate-2 캐릭터 동작 전사 | Wan Animate-2 동작 전사 생성기 | 생성기 | `wan22-animate2-generator` | `/management/frame/wan22-animate2-generator/` |
| Wan Fun Control 영상 생성기 | Wan Fun Control 영상 생성기 | 생성기 | `wan22-fun-control-generator` | `/management/frame/wan22-fun-control-generator/` |
| Wan2.2 I2V 영상 생성기 | Wan2.2 I2V 영상 생성기 | 생성기 | `wan22-i2v-generator` | `/management/frame/wan22-i2v-generator/` |
| Wan2.2 VACE-Fun 영상 생성기 | Wan2.2 VACE-Fun 영상 생성기 | 생성기 | `wan22-vace-generator` | `/management/frame/wan22-vace-generator/` |
| MiniMax H3 Ref2VA 영상 편집기 | MiniMax H3 영상 편집 | 생성기 | `minimax-h3-ref2va-generator` | `/management/frame/minimax-h3-ref2va-generator/` |
| 건물 에셋 관리 | 건물 에셋 관리 | 관리 | `building-editor` | `/management/frame/building-editor/` |
| 공용 빌보드 에셋 관리 | 공용 빌보드 에셋 관리 | 관리 | `asset-editor` | `/management/frame/asset-editor/` |
| 디자인 시스템 · 토큰과 기본 컴포넌트 | 디자인 시스템 · 토큰과 기본 컴포넌트 | 검수 | `ui-62838d08dcbc31e6-design-system` | `/ui-62838d08dcbc31e6/review/design-system.html` |
| 맵 통합 검수 | 맵 통합 검수 | 검수 | `map-review-iseulon` | `/management/frame/map-review/?map=iseulon&townPage=1` |
| 모델 다운로드·빌드 상태 | 모델 관리 | 관리 | `model-management` | `/management/frame/model-management/` |
| 발광 이펙트 좌표 검수 | 발광 이펙트 좌표 검수 | 검수 | `effect-editor` | `/management/frame/effect-editor/` |
| 스프라이트 시트 편집기 | 스프라이트 시트 편집기 | 편집 | `sprite-sheet-editor` | `/management/frame/sprite-sheet-editor/` |
| 월드맵 검수 | 월드맵 검수 | 검수 | `world-map` | `/management/frame/world-map/` |
| 작가 AI 에이전트 | 작가 AI 에이전트 | 작가 에이전트 | `writer-agent` | `/management/frame/writer-agent/` |
| 전투 레이아웃 · 전체 전장 | 전투 레이아웃 · 전체 전장 | 검수 | `ui-62838d08dcbc31e6-battlefield-layout` | `/ui-62838d08dcbc31e6/review/battlefield-preview.html` |
| 프롬프트 번역 | 프롬프트 번역 | 번역 | `prompt-translation` | `/management/frame/prompt-translation/` |

## 별도 확인된 미등록 기능

| 이름 | 현재 상태 |
| --- | --- |
| AnimationGPT | 모델 파일 준비와 내부 실험 파이프라인만 존재한다. 공용 생성 요청·상태·이력 서비스 및 생성 화면이 없어 탐색에 등록되지 않았다. ROCm 실행기와 생성 서비스를 검증한 뒤 생성기로 등록한다. |

## 변경 관리

- 카탈로그 원본은 `workflow/common/management_catalog.py`이며 탐색 API는 이를 사용한다. 이 문서는 기록과 정리 기준으로 사용한다.
- 신규·이름 변경·폐기 시 카탈로그, 화면 명칭, 생성기 변경 기록 및 이 문서를 함께 갱신하고 실제 화면과 게이트웨이 연결을 검증한다.
- 모델 관리에만 등록된 파일을 생성기로 표시하지 않는다. 생성기는 요청·상태·이력·결과와 화면이 실제 연결된 경우에만 현행으로 표시한다.
- 이전 이름과 동적 항목 검색, 기존 URL 및 작업 이력 호환성을 검증한다.
