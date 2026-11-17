# slime-workflow

로컬 GPU 기반 이미지·모션·음향 제작과 게임 에셋 검수를 위한 생성기 및 관리도구다. 생성 결과는 후보이며 검수와 명시적인 채택을 거쳐 에셋 저장소에 등록한다.

## 시작하기

저장소 루트에서 최초 준비 또는 의존성 변경 시 실행한다. 준비 스크립트는 모델 가중치를 설치하지 않는다. GPU 환경과 생성기별 모델 준비는 각 사용 설명을 확인한다.

```bash
./scripts/setup_management.sh
```

게이트웨이와 GUI를 별도 터미널에서 실행한다. GPU 작업을 접수하는 게이트웨이는 GPU에 접근할 수 있는 환경에서 실행한다.

```bash
# 터미널 1: 명령 게이트웨이와 작업 서비스
./scripts/run_management_gateway.sh

# 터미널 2: 관리도구 GUI
./scripts/run_management_gui.sh --watch
```

관리도구 주소는 [http://127.0.0.1:8770/](http://127.0.0.1:8770/)이며 게이트웨이는 기본적으로 `127.0.0.1:8771`을 사용한다. GUI 없이도 게이트웨이를 통해 통합 CLI를 사용할 수 있다.

```bash
python3 tools/manager.py command kimodo history
./scripts/run_management_gateway.sh --help
./scripts/run_management_gui.sh --help
```

GUI와 CLI는 공용 명령 게이트웨이, 작업 서비스, GPU 대기열과 이력을 공유한다. GUI를 종료해도 독립 작업과 기록은 유지된다. 접수 중 연결이 끊기면 중복 요청 전에 이력을 확인한다. 포트·환경 변수·변경 감시·로그와 명령별 사용법은 [관리도구 클라이언트 가이드](workflows/management-clients.md)를 따른다. GUI 기본 실행에는 인접 `slime-frontend`와 npm 환경이 필요할 수 있다.

## 주요 기능

- **이미지**: [FLUX 이미지 생성기](workflows/flux-image-generators.md)는 일반 이미지, 캐릭터, 마네킨, 빌보드, 소품, 식생, 건물, 심리스 타일과 표정 작업을 다룬다. 생성 결과의 품질과 반복 경계는 직접 검수한다.
- **모션**: [Kimodo 사용 설명](generators/kimodo/README.md)은 텍스트 모션 생성과 SOMA 렌더·포즈 출력을 설명한다.
- **음악·효과음·영상**: `generators/`의 해당 생성기별 README와 관리도구 화면에서 준비 및 실행 조건을 확인한다.
- **검수·편집**: [공통 검수 절차](workflows/asset-review.md)와 [관리도구 소스 구조](tools/review/README.md)를 참고한다. 맵·타일은 에셋 저장소의 등록 원본을 검증해 직접 읽는다.
- **작가 AI·프롬프트 번역**: [작가 AI 실행 안내](workflows/writer-agent.md)와 [관리도구 클라이언트 가이드](workflows/management-clients.md)를 참고한다. 번역 결과는 의미와 수치를 검토한다.

Qwen 2.1 이미지 계열은 라이선스 사유로 신규 생성·재개와 모델 준비를 중단하고 기존 이력 조회를 보존한다. HY-Motion, VNCCS 포즈 변환과 MoMask 생성은 폐기됐다. 과거 문서와 호환 코드가 있다는 사실이 현행 실행 지원을 뜻하지 않는다. 상세 범위는 [클라이언트 가이드](workflows/management-clients.md)를 확인한다.

## 저장소 구성과 에셋 소유권

| 경로 | 용도 |
| --- | --- |
| `generators/` | 생성기별 구현·설정·사용 설명·변경 기록 |
| `tools/manager.py`, `tools/review/` | 통합 CLI, 게이트웨이, 관리 UI와 검수 도구 |
| `scripts/` | 관리 환경 준비 및 서버 실행 |
| `workflows/` | 작업 절차, 운영 기준과 검증 기록 |
| `prompts/` | 사용자 지시로 이전한 제작 프롬프트 |
| `baseline/` | 승인된 제작 기준 자료와 출처 |
| `.model/` | 로컬 모델과 캐시 |
| `.tmp/`, `.local/` | 로컬 후보·작업 기록 및 실행 데이터 |

채택된 에셋과 런타임 맵의 관리 원본은 인접 `slime-assets` 저장소다. 캐릭터는 `assets/characters/`, 몬스터는 `assets/sprites/`, 건물은 `assets/buildings/`, 빌보드는 `assets/billboards/`, 지형 타일은 `assets/tiles/terrain/`, 맵은 `assets/maps/`에서 관리한다. 등록부의 ID·버전·출처·해시를 보존하고 소비자 잠금 목록을 함께 갱신한다. 생성 후보·모델·로그는 에셋 등록부에 넣지 않는다.

빌보드 등록, 공용 표시 속성 또는 맵 배치를 변경한 경우 [빌보드 카탈로그 안내](../slime-assets/assets/billboards/README.md)에 따라 카탈로그를 동기화하고 검증한다. 생성기 구조와 UI 기준은 [생성기 구성 가이드](workflows/generator-structure.md), [관리도구 UI 가이드](workflows/management-ui.md)를 따른다.
