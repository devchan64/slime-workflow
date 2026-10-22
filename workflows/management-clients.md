# 관리도구 GUI·CLI 클라이언트

## 공용 대기열 우선 실행

`python tools/manager.py command hy-motion prioritize <생성-ID>`로 선택한 GPU 대기 작업을 맨 앞으로 이동한다. 재개를 지원하는 다른 서비스도 같은 `prioritize` 계약을 사용한다. GUI의 공용 생성이력 `우선 실행`과 같은 명령이며 실행 중 작업은 선점하지 않는다. 대기 티켓 등록 전·실행 예약 후·중지 요청 상태는 거절한다. GPU 메모리 조건은 그대로 적용된다. 미전환 독립 화면은 별도 연결이 필요하다.

## MoMask 포즈 생성기 폐기

2026-10-09 MoMask 생성 도구·Gradio 화면·메뉴를 폐기했다. GUI 과거 주소와 API는 HTTP 410으로 종료하며 통합 CLI의 MoMask 명령도 폐기 오류를 반환한다. 직접 생성·작업 재개 진입점도 차단한다. `.tmp/momask-generator/`의 과거 작업·렌더 결과·로그·이력은 사용자 지시로 삭제했다. 앞서 삭제한 모델 가중치를 자동 복원하지 않는다.

HY-Motion이 사용하는 리타기팅·스키닝·Blender 단계 실행 코드는 유지한다. `assets/`의 등록 모션·피팅·리그와 다른 생성기의 결과·기록은 삭제하지 않는다. 현행 모션 실행은 `hy-motion`을 사용하며 구형 실행 예시는 이 안내에서 제거했다.

## AnyPose 애니메이션 생성기 폐기

2026-10-09부터 AnyPose 기반 캐릭터 애니메이션 생성기와 기록 화면을 폐기했다. 메뉴에서 제거하며 이전 화면 주소는 HTTP 410을 반환한다. `character-animation`의 `generate`·`resume`·`record-alpha-vnccs`는 폐기 오류로 거절한다. AnyPose 직접 추론·LoRA 준비도 차단한다. 공유 Lightning은 AnyPose 가중치 없이 별도 검증한다.

기존 `.tmp/test/character-animation/`의 작업·결과·로그·이력을 사용자 지시에 따라 삭제했다. 등록 에셋·스프라이트 편집기 작업·앵커 기록·VNCCS 원본 실험은 보존한다. `character-animation` 서비스의 스프라이트·앵커 편집 명령은 계속 제공하며 HY-Motion과 VNCCS 포즈 변환은 별도 도구로 유지한다. 구형 생성·재개·배치 사용법은 이 안내에서 제거했다. 새 단일 포즈 변환은 [VNCCS 안내](pose-transfer.md)를 따른다.

## VNCCS 포즈 변환 · BF16 기준 경로

`pose-transfer`의 신규 작업은 VNCCS PoseStudio V1.1 LoRA와 공식 `QwenImage21Pipeline`을 사용한다. 인코더·DiT·VAE는 BF16 비양자화이며 512×512로 고정하며 스텝은 25·40 중 선택한다(기본 40). GUI와 CLI `--steps 25` 모두 실제 추론·진행률·결과 기록에 선택값을 사용한다. GUI·CLI 기본 시드는 `1695791623`이며 사용자가 지정한 시드와 기존 이력은 유지한다. 모델·LoRA는 코드에서 고정하고 LoRA SHA-256을 검사한다. 기본 프롬프트는 추적 파일 `generators/image/config/pose-transfer-prompt.txt`의 일반화한 전신 포즈 지시문을 사용한다. `2026-10-10_00-30-33-f09d19de`에서 사용자가 채택한 문구로, 공식 이미지 역할(이미지 1=포즈, 이미지 2=캐릭터)을 유지하면서 캐릭터 기준 좌우·관절 상대 배치·손발 위치와 방향을 명시한다. 이 채택은 시드·스텝 기본값을 변경하지 않는다. 사용자 편집은 99단어까지 허용하고 최종 원문·단어 수·해시를 저장한다. 과거 작업 재개는 저장된 프롬프트를 유지한다.

GUI 업로드와 CLI 참조 순서는 기존처럼 **아이덴티티 → 포즈**다. 실행기가 모델 입력만 **포즈 image1 → 아이덴티티 image2**로 바꾼다. 참조 파일 저장 순서와 과거 이력은 변경하지 않는다.

```bash
python3 tools/manager.py command pose-transfer generate --reference /path/identity.png --reference /path/pose.png --resolution 512 --steps 40 --seed 204801 --detach
```

GUI·CLI → 공용 게이트웨이 → 기존 이미지 작업 서비스·GPU 대기열 구조를 유지한다. 작업은 `.tmp/test/pose-transfer/<생성ID>/`에 저장하고 `request.json`의 `vnccs`에 실행 버전·모델 입력 순서·정밀도·LoRA 해시·안전 한계를 기록한다. 상세 로그는 `vnccs-pipeline.log`, 자원 기록은 `vnccs-resources.json`, 결과·품질 경고는 `result.json`에 둔다. 공용 취소는 같은 프로세스 그룹의 감독 작업자와 추론 자식을 함께 중단한다.

가중치는 CPU RAM에 보관하고 모듈 연산은 CUDA에서 수행한다. 5초마다 시스템 RAM 여유·자식 RSS·진행 로그를 확인하며 RAM 여유 12GiB 미만, RSS 42GiB 초과, 실행 20분 초과 시 실패로 중단한다. CPU 추론 대체는 없다. 기존 `vnccs` 필드가 없는 기록은 과거 Qwen 경로·입력 순서·설정으로 재개한다. 과거 입력을 GUI에 불러와 **새로 생성**하면 새 고정 설정과 기본 프롬프트를 적용한다는 안내를 표시한다.

포즈 변환 생성기를 정식 도구로 전환하여 메뉴·화면의 Alpha Ver. 표시를 제거했다. 후속 AnyPose 도구 폐기로 알파 가져오기 사본과 명령은 폐기했으며 VNCCS 원본 실험은 보존한다. 공식 포즈 일부도 부분 추종하므로 작업 완료가 전신 비례·포즈·프레임 일관성의 품질 승인을 뜻하지 않는다. 모델카드의 BF16·40스텝·공식 추론 경로를 따르지만, 512px 출력·VNCCS LoRA·모듈 단위 오프로드는 프로젝트의 명시적 설정이다. 다른 Qwen 생성기와 배포·AWS 비용에는 변경이 없다.

ANNY 기준점 후보 지정·축 검수는 [해부학 리타기팅 검수](anny-anatomical-retarget.md#anny-기준점-후보-검수-도구)를 따른다. `anny-landmarks` 서비스의 `landmark-source/preview/save/load/history` 명령은 모두 `--payload-file` JSON을 받으며 GUI와 `.tmp/test/anny-landmarks/<KST 시각>/<고유 ID>/` 기록을 공유한다. 승인·리타기팅 적용 명령은 없다.

HY-Motion Lite 생성·모델 준비·8GB 오프로드·기록 계약은 [HY-Motion 생성기](hy-motion.md)를 따른다. 서비스 이름은 `hy-motion`, GUI는 `/management/frame/hy-motion-generator/`이며 공용 게이트웨이와 GPU 실행기를 사용한다.

HY-Motion 신규 `generate`는 ANNY 리그 변환·스킨 충돌 기반 회전 제약·정사영·원근투영·OpenPose를 같은 생성 ID에 자동 저장한다. `export-vnccs`는 기존 모션 재출력용 호환 명령이며 MakeHuman은 폐기됐다. AnyPose LoRA 전용 렌더 옵션은 제공하지 않는다. 입력·저장·후보 품질 한계는 [HY-Motion 안내](hy-motion.md)를 따른다.

화면 구성·상태·로그·이력·재생 UX 기준은 [관리도구 UI 가이드](management-ui.md)를 따른다.

구현 기준은 [AGENTS.md의 Management Client and Gateway Standard](../AGENTS.md#management-client-and-gateway-standard)에 명시한다. 이 문서는 해당 기준의 현재 구현·명령 사용법·기록 경로를 설명한다.

## 독립 실행

관리도구는 GUI 서버, 명령 게이트웨이·작업 서비스, 별도 GPU 대기·실행 프로세스로 나눈다. GUI와 CLI는 같은 HTTP 명령 계약을 사용한다.

```text
Gradio GUI → GUI 서버(8770)의 API 중계 ─┐
Gradio Python 콜백 → HTTP 클라이언트 ───┼→ 게이트웨이(8771) → 작업 서비스 → GPU 대기·실행기
통합 CLI → HTTP 클라이언트 ────────────┘                         └→ 기존 공용 기록 저장소
```

서로 다른 터미널에서 실행한다. GPU 작업을 접수할 게이트웨이는 GPU 접근이 가능한 샌드박스 밖에서 시작한다.

```bash
# 최초 또는 의존성 변경 시 준비 (서버 시작과 분리)
./scripts/setup_management.sh

# 터미널 1: 게이트웨이·작업 서비스 (GUI 없이 CLI 사용 가능)
./scripts/run_management_gateway.sh

# 터미널 2: GUI·정적 검수·Gradio (GUI 코드 변경만 자동 재시작)
./scripts/run_management_gui.sh --watch

# 터미널 3: 같은 게이트웨이에 작업 접수
python3 tools/manager.py command hy-motion generate --prompt 'A person walks forward.' --duration-seconds 3 --detach
```

- 기본 주소는 GUI `http://127.0.0.1:8770`, 게이트웨이 `http://127.0.0.1:8771`이다. GUI 포트와 게이트웨이 포트를 같게 지정할 수 없다.
- 게이트웨이 포트를 바꾸면 `scripts/run_management_gateway.sh --port 9871`, GUI `scripts/run_management_gui.sh --gateway-url http://127.0.0.1:9871`, CLI `<서비스> --server-url http://127.0.0.1:9871 <명령>`을 사용한다. GUI·CLI 기본 접속 주소는 `SLIME_MANAGEMENT_GATEWAY_URL`로 지정할 수도 있다.
- 기존 브라우저 명령·결과·로그 URL은 GUI 서버가 중계한다. GUI 종료 중에도 CLI는 게이트웨이로 직접 접수·조회·취소·재개할 수 있다. Gradio Python 콜백은 공용 HTTP 클라이언트를 사용하며 로컬 서비스로 우회하지 않는다.
- `GET /management/health`는 게이트웨이 역할·PID·응답 상태를 반환한다. GUI 주소에서도 같은 경로로 중계 상태를 확인할 수 있다. GPU 가용성은 별도 상태 조회로 확인한다.
- GUI `--watch`는 게이트웨이·작업 서비스 코드를 감시하지 않는다. `scripts/run_management_gateway.sh --watch` 또는 `python3 tools/review/gateway_server.py --watch`로 실행하면 게이트웨이 코드 변경도 해당 프로세스만 자동 재시작한다. 일반 실행에서는 명시적으로 재시작한다. 기존 GPU 대기·실행기는 별도 프로세스와 기록을 유지한다. 접수 중 연결이 끊기면 자동 재전송하지 않으므로 이력을 확인한 뒤 다시 요청한다.
- `--writer-agent-config`는 `gateway_server.py`의 옵션으로 이동했다. 작가 작업은 아직 공용 GPU 실행기로 통합되지 않았으며 게이트웨이 종료 시 기존 종료 정책을 따른다. GUI 재시작은 작가 작업 수명에 영향을 주지 않는다.
- 게이트웨이 서비스 초기화 실패도 `.tmp/gateway-server-logs/`에 원인과 함께 기록한다. 정상 실행은 같은 경로에 로그를 저장하고 5초 heartbeat를 출력한다. GUI 로그·생성 ID·대기열·요청·결과·이력 경로는 유지한다.

### 게이트웨이 변경 감시

`--watch`는 `gateway_server.py`, `tools/review/common/`, `tools/review/domains/`, `generators/writer_agent/`의 Python·YAML·JSON과 지정한 작가 작업 공간 YAML을 감시한다. 파일 추가·수정·삭제를 감지하며 0.5초 동안 변경이 없으면 이전 게이트웨이 종료를 기다린 뒤 같은 포트·작가 설정으로 새 프로세스를 시작한다. GUI·Gradio 모듈·테스트·숨김 폴더·생성 기록은 감시하지 않는다. 감시기와 실행기 자체(`gateway_watch.py`, `management_launcher.py`, `management_process.py`, `management_setup.py`) 변경은 watch 명령을 다시 시작해야 반영된다.

명령 등록·작업 서비스와 요청·이력 경로는 그대로 유지한다. 별도 세션의 GPU 대기·실행기는 재시작하지 않는다. 작가 에이전트는 게이트웨이 수명에 묶인 기존 정책을 유지하므로 watch 재시작 때 진행 작업이 종료된다. 재시작 중 짧은 API 연결 중단이 있으며 접수 응답이 끊긴 경우 자동 재전송하지 말고 이력을 먼저 확인한다.

감시 로그는 `.tmp/management-launcher-logs/*-gateway-watch-*.log`에 저장한다. 5초 heartbeat·변경에 따른 재시작·실패 원인을 기록한다. 시작 또는 실행 실패는 감시 명령을 종료하며 무한 재시도하지 않는다. `Ctrl+C`·SIGTERM은 감시기와 그 게이트웨이를 함께 종료한다.

### 실행 스크립트 계약

| 스크립트 | 역할 |
| --- | --- |
| `scripts/setup_management.sh` | `.venv`·`.venv-management` 준비와 환경별 의존성 설치 |
| `scripts/run_management_gateway.sh` | 독립 게이트웨이 시작; `--watch` 지원; 프론트엔드·Gradio 환경 불필요 |
| `scripts/run_management_gui.sh` | GUI 시작; `--watch`, `--root`, `--frontend-repo` 등 기존 옵션 전달 |
| `scripts/watch_review_server.sh` | `run_management_gui.sh --watch` 호환 연결 |

공용 진입점은 `tools/review/common/management_launcher.py`다. 환경·접속 설정은 `management_environment.py`, 명시적 설치는 `management_setup.py`, 로그·heartbeat·프로세스 그룹 수명은 `management_process.py`가 맡는다. Gradio는 환경 설정 모듈만 참조한다. 서버 실행 시 패키지를 설치하거나 환경을 자동 복구하지 않는다. 환경이 없으면 준비 명령을 안내하고 즉시 실패한다. `setup`은 서버가 실행 중이지 않을 때 최초 준비 또는 의존성 갱신 목적으로 명시적으로 실행한다.

`VIRTUAL_ENVIRONMENT_PATH`는 서버 Python 환경, `MANAGEMENT_VIRTUAL_ENVIRONMENT_PATH`는 실제 Gradio 자식 환경을 지정한다. GPU 모델 실행기의 기존 환경 정책은 별개다. 상대 경로와 전달한 상대 파일 인자는 저장소 루트를 기준으로 한다. `REVIEW_SERVER_PORT`·`MANAGEMENT_GATEWAY_PORT`는 각 서버 포트이며 명시적인 `--port`가 우선한다. `FRONTEND_REPOSITORY_PATH`는 GUI 기본 프론트엔드 경로로만 사용하고 `--root`·`--walking`·`--frontend-repo`를 지정하면 적용하지 않는다. 게이트웨이 포트를 바꿔도 GUI·CLI 목적지는 자동 변경하지 않으므로 `--gateway-url`·`--server-url` 또는 `SLIME_MANAGEMENT_GATEWAY_URL`도 설정한다.

시작·명령·출력·5초 heartbeat와 실패 traceback은 `.tmp/management-launcher-logs/`에 누적한다. 실패 시 명령과 최근 로그를 출력하고 종료 코드를 반환한다. `Ctrl+C` 또는 SIGTERM은 해당 실행기가 시작한 서버 프로세스 그룹에만 전달한다. GUI와 게이트웨이는 별도 그룹이며 독립 세션으로 시작한 GPU 작업·대기열은 정리 대상이 아니다. 부모 종료 뒤 같은 그룹에 남아 SIGTERM을 무시하는 자식은 강제 종료한다. 다른 실행기가 시작한 그룹과 독립 세션은 건드리지 않는다. 검증이나 재시작을 위해 기존 서버의 포트 점유 프로세스를 강제로 종료하지 않는다.

기존 단일 서버에서 전환할 때 새 게이트웨이를 먼저 시작하고 GUI를 새 명령으로 다시 시작한다. 검증을 위해 실행 중인 생성 작업을 취소하지 않는다. 롤백은 이전 코드의 단일 서버로 복귀하며 기록을 이동하거나 초기화하지 않는다. 로컬 프로세스가 하나 추가되지만 AWS 배포·고정 비용 리소스는 변경하지 않는다.

## command와 help

저장소 루트에서 실행한다. `help`는 명령·옵션을 확인하고 실제 작업은 `command`로 접수한다.

```bash
python3 tools/manager.py help
python3 tools/manager.py help hy-motion
python3 tools/manager.py help hy-motion generate
python3 tools/manager.py help pose-transfer generate
python3 tools/manager.py command hy-motion generate --prompt 'A person walks forward.' --duration-seconds 3 --directions down_left down_right up_left up_right --detach
python3 tools/manager.py command hy-motion history
python3 tools/manager.py command hy-motion status GENERATION_ID
python3 tools/manager.py command hy-motion logs GENERATION_ID
python3 tools/manager.py command hy-motion cancel GENERATION_ID
python3 tools/manager.py command hy-motion resume GENERATION_ID
```

모델 준비·고정 파라미터·입력 제한은 [HY-Motion](hy-motion.md), 외형·포즈 참조 순서는 [VNCCS 포즈 변환](pose-transfer.md)을 따른다. `generate`의 `--detach`를 생략하면 완료까지 진행 로그를 표시하며 Ctrl+C는 해당 작업에 취소를 요청한다. 모션 프리셋 선택과 실제 생성 실행은 구분한다.

## 공용 기록

Phantom·VACE 영상 기록의 `status`는 생성 작업의 종료 상태를 보존한다. 완료 후 결과 파일이 누락되거나 결과 경로 검증이 실패하면 `result_error`에 원인을 제공하고 `video`·`download`·`image` URL은 제공하지 않는다. 이 상태에서도 이력과 작업 상태를 조회할 수 있다. 결과 오류를 생성 작업의 실패나 정상 다운로드 가능 상태로 해석하지 않는다. GUI는 결과 조회 영역에 원인을 표시하며, CLI는 같은 상태 응답의 `result_error`를 확인한다. 파일 복구 후 상태를 다시 조회하면 결과 경로를 재검증한다.

GUI와 CLI는 서비스별 동일한 작업·이력을 조회하며 서로 다른 저장소를 만들지 않는다.

| 서비스 | 작업 기록 | 이력 인덱스 |
| --- | --- | --- |
| `hy-motion` | `.tmp/test/hy-motion/<한국시간>/<고유 ID>/` | `.tmp/manager-current/hy-motion/` |
| `pose-transfer` | `.tmp/test/pose-transfer/<생성 ID>/` | `.tmp/manager-current/pose-transfer/` |

입력·상태·로그·결과와 시도별 산출물은 서비스의 기존 구조를 유지한다. HY-Motion 재개는 새 시도로 기록하며 기존 시도 산출물을 보존한다. 생성기의 전체 `history-reset`은 작업 폴더의 입력 사본·중간 산출물·결과·모든 시도의 로그와 기록 및 이력 인덱스를 함께 삭제하는 디스크 정리 계약이다. 외부 원본·등록 에셋·모델은 보호한다. 생성기의 선택 `history-delete`도 선택한 작업 ID의 동일 범위 파일과 이력 인덱스를 함께 삭제하고 삭제 용량을 보고한다. 앵커·좌표 편집 이력은 별도 계약을 확인한다. 기존 목록 전용 구현의 전환 여부를 구분하며 상세 기준은 AGENTS.md의 Generator History Reset Disk Cleanup Standard를 따른다. 이미 폐기된 MoMask·AnyPose 작업 경로는 현행 기록 저장소로 다시 사용하지 않는다.

## Qwen 이미지 생성 두 종류

`qwen-2512`(텍스트 이미지)와 `qwen-2511`(텍스트 또는 참조 1~3장)를 지원한다. 모든 통합 CLI 명령은 GUI와 같은 독립 게이트웨이 HTTP API를 호출하므로 **게이트웨이가 실행 중이어야 한다**. GUI 서버는 필요하지 않다. 입력 검증·모델 선택·취소·이력 저장은 기존 서버 구현을 그대로 사용한다.

```bash
python3 tools/manager.py help qwen-2512 generate
python3 tools/manager.py help qwen-2511 generate
python3 tools/manager.py command qwen-2512 generate --prompt-file /tmp/prompt.txt --width 1024 --height 1024 --steps 4 --detach
python3 tools/manager.py command qwen-2511 generate --prompt-file /tmp/prompt.txt --reference /tmp/reference-1.png --reference /tmp/reference-2.png --steps 30 --detach
python3 tools/manager.py command qwen-2511 history
python3 tools/manager.py command qwen-2512 status GENERATION_ID
python3 tools/manager.py command qwen-2512 logs GENERATION_ID
python3 tools/manager.py command qwen-2511 cancel GENERATION_ID
python3 tools/manager.py command qwen-2512 history-reset
```

두 서비스 모두 `generate`, `status`, `logs`, `history`, `active`, `model-status`, `cancel`, `history-reset`을 제공한다. 2512에는 `prepare`도 제공한다. `--detach`를 생략하면 진행 상태를 표시하며 완료까지 대기하고 결과·로그 URL을 출력한다. Ctrl+C는 서버에 취소를 요청한다. `--seed`를 지정할 수 있고 기본값은 GUI와 동일하다. 다른 포트는 서비스 뒤에 `--server-url http://127.0.0.1:포트`를 지정한다.

2511의 최소·기본 출력은 512×512이며 `--width`·`--height`로 변경할 수 있다. 최종 맵 타일 규격 256×256과 생성 해상도는 구분한다. 2511의 `--reference`는 크기·비율 제한 없이 RGB 또는 불투명 RGBA PNG를 최대 3장까지 순서대로 지정한다. 생략하면 텍스트 생성이다. 해상도·스텝·참조 검증은 서버가 GUI와 동일하게 수행한다.

기록 경로도 기존 GUI와 같다.

- 2512 결과·로그: `.tmp/test/qwen-image-2512/<생성 ID>/`
- 2511 결과·로그: `.tmp/test/qwen-image-2511-three-reference/<생성 ID>/`
- 이력: `.tmp/manager-current/qwen-2512/`, `.tmp/manager-current/qwen-2511/`

실행 결과는 해당 웹 생성기의 이력에서 조회할 수 있다. `history-reset`은 명시적으로 실행할 때만 누적 이력을 초기화한다. Qwen 2512의 전체 초기화는 이전에 목록에서 제거된 작업도 포함하여 `.tmp/test/qwen-image-2512/` 바로 아래의 생성·준비 작업 폴더(입력·결과·로그)를 삭제한다. 실행·대기 중이거나 상태가 불명확한 작업이 있으면 삭제 전에 거절한다. 하위 `tile-map/`, 정식 등록 에셋, 모델 캐시는 제외한다. Qwen 2511·표정·건물 타일·바닥 타일에도 동일하게 적용한다. 개별 이력 삭제는 선택한 작업 폴더의 입력·결과·로그와 이력 인덱스를 함께 삭제한다. 등록 에셋 원본과 모델 캐시는 삭제하지 않는다.

## 통합 명령 게이트웨이

`management_gateway.py`가 `hy-motion`, `pose-transfer`, Qwen 이미지 서비스 및 스프라이트·앵커 편집 명령의 등록과 HTTP 경로를 관리한다. GUI의 기존 API 호출은 서버 진입점에서 이 게이트웨이를 통과한다. Qwen 통합 CLI는 `POST /management/command`에 `{service, command, payload}`를 보내 같은 서비스 어댑터를 호출한다. MoMask는 폐기되어 모든 명령을 저장소 접근 전에 거절한다. 이전 HTTP 주소에는 410 안내만 제공한다.

```text
GUI 기존 API → 명령 경로 변환 ─┐
                             ├→ 통합 명령 게이트웨이 → 생성기 서비스 → 공용 기록
CLI command → 명령 봉투 ──────┘
```

브라우저 요청마다 CLI 프로세스나 셸을 실행하는 방식이 아니라, 통합 CLI와 명령 계약·디스패처를 공유하는 구조다. 생성 원본·이미지·정적 UI 자산은 기존 파일 조회 경로로 제공한다. `command`와 `help`의 기존 사용법은 유지한다. 서비스의 실제 지원 범위는 게이트웨이 등록과 `help`를 기준으로 확인한다. 등록 이름이나 호환 경로가 남아 있다는 이유만으로 폐기된 생성 기능을 지원한다고 판단하지 않는다.

게이트웨이는 Host·Origin·JSON 형식·최대 요청 크기·중복 필드·허용 서비스/명령·생성 ID를 확인한 뒤 기존 입력 검증기로 전달한다. 작업에 임의 실행 파일이나 셸 문자열을 전달할 수 없다.

## CLI·게이트웨이 일체화

`tools/manager.py`는 `management_gateway.execute_gateway_cli()`를 호출하는 진입점만 가진다. 서비스·명령 등록, 최상위 `command`/`help` 파싱, 로컬 실행 디스패치와 HTTP 명령 전송은 모두 게이트웨이에 둔다. 생성기별 CLI 실행 모듈은 제거했다. 옵션 파싱·입력 파일 처리·진행 대기·취소도 게이트웨이에 통합하며 GUI와 CLI는 `execute_management_command`를 사용한다. 게이트웨이 명령 전체의 CLI 도움말 진입을 테스트한다.

기존 GUI 주소·이력 경로·관리 서버 필요 여부는 유지한다.

### 단일 실행 구현

`tools/review/momask_commands.py`와 `qwen_commands.py`는 폐기했다. `execute_gateway_arguments`가 등록된 명령의 인자를 해석하고 `execute_management_command`가 로컬 서비스·HTTP 전송·GUI 서비스 어댑터를 선택한다. CLI는 상태·로그 파일을 직접 읽지 않고 명령 서비스를 통해 조회한다. 생성 완료 대기와 Ctrl+C 취소도 생성기별로 중복 구현하지 않는다.

HY-Motion과 포즈 변환 CLI는 독립 HTTP 게이트웨이에 연결한다. 서비스 함수의 로컬 호출은 내부 작업 서비스·호환 코드에만 남기며 CLI 기본 경로로 사용하지 않는다.

```bash
python3 tools/manager.py command hy-motion --server-url http://127.0.0.1:8771 history
```

## 모션·포즈 변환과 기존 편집 기능

모션·ANNY 렌더·OpenPose 생성은 `hy-motion`, 아이덴티티·포즈 두 참조의 단일 이미지 생성은 `pose-transfer`로 실행한다. 등록된 HY-Motion 걷기 v2는 제작 참조 자산이며, 구형 `character-animation` 배치 생성의 활성화를 뜻하지 않는다. [캐릭터 애니메이션 제작·검수](character-animation.md)에서 방향·원본 프레임·출처를 연결한다.

`character-animation` 이름은 기존 스프라이트·앵커 편집 명령의 호환 서비스로 남는다. 아래 편집 명령을 생성·재개 기능과 혼동하지 않는다. 과거 생성 결과 조회용 코드가 남아 있어도 삭제된 작업·이력을 자동 복원하거나 신규 실행하지 않는다.

## 건물 타일 생성기 폐기

건물 타일 생성기(`tile-map`)의 GUI·CLI·HTTP 등록을 폐기했다. 기존 생성 결과와 이력 파일은 보존하며 맵 타일 생성기는 계속 제공한다.

## 스프라이트 정규화 편집기

관리 메뉴 `?tool=sprite-editor&category=animation-tool`에서 프론트 등록 애니메이션을 선택해 불러온다. 생성 결과 ID 직접 입력 UI는 제거했다. 프론트 원본은 검수 빌드가 만든 `sprite-assets.json`과 이미지 사본만 사용한다. 기본 캐릭터 대기가 등록되어 있으면 자동 선택한다. 여러 결과 병합은 지원하지 않는다.

대기 v6는 384×384 셀·4방향×4프레임·4 FPS로 열린다. 편집본 확대, 4방향 동기 재생, 이전/다음·타임라인·0.5/1/2배속, 투명 체크/흰색/어두운 배경과 전체 시트 검수를 제공한다. 첫 로딩은 원본 캔버스 배치를 유지하며 자동으로 높이를 바꾸지 않는다. 가이드는 alpha 128 이상 영역의 머리·바닥에서 시작하며 불투명 배경의 이미지에는 몸체 검출값으로 사용할 수 없다. 필요하면 직접 지정한다.

편집 작업대는 기본 200%로 표시하며 화면 확대 100/150/200/300/400%와 너비 맞춤을 지원한다. 확대는 화면 표시만 바꾸며 출력 셀 크기에 영향을 주지 않는다. 확대 영역 안에서 스크롤하고 드래그로 배치를 조정한다. 중복 원본 확대 영역 없이 편집본만 표시하며 전체 방향 검수는 접이식 영역에 둔다. 가이드는 대비 외곽선·머리/중심/바닥 라벨·기준점 원형 십자로 표시한다.

중심·바닥·머리 가이드와 기준점, 배치·배율을 편집한다. 정렬·높이 맞춤은 선택/현재 방향/전체 범위의 **각 프레임 가이드**로 계산한다. 현재 설정 복사는 별도 버튼이다. 출력 크기 변경은 배치·배율을 같은 비율로 바꾸며 실행 취소로 복원할 수 있다. PNG에는 배경 체크·가이드·겹침 표시를 포함하지 않는다.

`프로젝트 저장`은 `.local/sprite-editor/<원본 ID 해시>/`에 버전별 JSON을 누적한다. v2 문서는 프레임 설정과 `output.cellSize`(128/256/384/512), `output.targetHeight`를 보존한다. 기존 v1 문서는 계속 조회·저장할 수 있으며 GUI가 512px 기준 배치를 유지해 v2로 읽는다. 원본 버전이 바뀌면 이전 저장본을 보존하고 새 편집으로 연다. 사용자가 저장하지 않은 편집은 재접속 시 복원되지 않는다.

현재 방향 PNG는 한 행, 전체 방향 PNG는 전방 좌측→전방 우측→후방 좌측→후방 우측의 행과 시간순 열로 내보낸다. 대기 v6의 전체 내보내기는 1536×1536(4×4)이며 각 행의 원본 프레임은 1→5→9→13이다. 최대 128프레임이며 메모리 상한을 넘는 시트는 명확한 오류로 거절한다. 정규화 JSON에 프레임 변환·출력 크기·배치·FPS가 포함된다. 프론트 원본은 덮어쓰지 않는다.

GUI와 CLI는 같은 명령·저장소를 사용한다.

```sh
python3 tools/manager.py character-animation sprite-source asset:character.default.white-shirt.idle
python3 tools/manager.py character-animation sprite-load asset:character.default.white-shirt.idle
python3 tools/manager.py character-animation sprite-save asset:character.default.white-shirt.idle --document-file project.json
```

`--document-file`에는 내보낸 JSON의 `project` 객체를 전달한다.

### 폐기된 생성 화면과 현행 UI

MoMask의 얼굴 포인트·커스텀 포즈·렌더 재개와 AnyPose 애니메이션의 생성 배속·해상도·강도 설정은 폐기된 생성 화면의 기능이다. 현행 명령으로 안내하지 않는다. HY-Motion의 렌더 프레임 스텝·투영·OpenPose 출력과 VNCCS의 단일 이미지 입력은 각 도구 안내를 따른다.

현행 Gradio UI는 `.venv-management`에서 실행하며 설정·이력·로그·브라우저 재생을 공용 컴포넌트로 구성한다. 설치는 `scripts/setup_management.sh`, GUI 로그는 `.tmp/manager-current/gradio.log`를 사용한다. 폐기된 MoMask 화면을 UI 전환·검증 대상으로 다시 실행하지 않는다.

### 로컬 GPU 대기·중지·재개

- HY-Motion, VNCCS 포즈 변환, Qwen 이미지 및 ANNY 작업은 공용 `gpu_job_queue.py` 실행기를 사용한다. 클라이언트 연결과 무관한 별도 프로세스가 `.tmp/gpu-queue/`의 접수 순서와 실행 잠금을 관리한다.
- GPU 0의 여유 메모리를 2초마다 조회한다. 초기 입장 기준은 HY-Motion 7000 MiB, 이미지 작업 6144 MiB, ANNY 2048 MiB이다. 실제 예약량은 서비스·실행 프로필과 관측 이력을 함께 확인한다. 이는 실측 최대치가 아닌 보수적 실행 입장 기준이며 실제 모델의 최대 사용량을 보장하지 않는다. 기준은 공용 `GPU_MEMORY_REQUIREMENTS`에서 조정한다. 유효 실측 이력이 있으면 최근 20회 중 성공한 작업의 최고 사용량을 예약한다. 현재 여유량에서 실행 중 작업의 미사용 예약분을 뺀 값으로 입장을 판단하며, 고정 안전 여유분은 추가 차감하지 않는다. Qwen 2.1도 해상도·스텝·참조 수와 심리스 파이프라인 버전별로 실측 이력을 분리한다. 공용 대기열은 예약량이 들어가는 작업을 허용하고 각 작업자의 실행 잠금도 유지한다.
- 메모리가 부족하거나 앞선 작업이 실행 중이면 `queued` 상태에 대기 순서·여유/필요 메모리를 저장한다. GPU 조회 실패 또는 전체 메모리 부족은 사유를 기록하고 실패한다. CPU로 우회하지 않는다.
- 생성 이력에서 대기·실행 작업을 중지하고 취소·실패 작업을 재개한다. 중지는 비동기 요청이며 실제 프로세스 종료 후 `cancelled`가 된다. 이력 새로고침으로 확인할 수 있다.
- 같은 ID·저장 입력·참조 사본·누적 로그를 사용한다. HY-Motion은 새 시도에서 다시 실행하며 이전 시도 결과를 보존한다. 포즈 변환·단일 이미지·ANNY는 저장 입력과 서비스의 재개 계약에 따라 다시 실행한다. 폐기된 MoMask·AnyPose 작업은 재개하지 않는다.
- 통합 CLI: `tools/manager.py command <서비스> cancel <ID>`, `resume <ID>`, `status <ID>`. 현행 예시는 `hy-motion`, `pose-transfer`, `qwen-21`; ANNY의 이력 상태·중지·재개는 `anny` 서비스에서 제공한다. ANNY 신규 생성은 기존 속성 화면을 사용한다.
- 대기·실행 중인 타일 작업은 파일 초기화 대상에서 제외한다. 서버 재시작은 별도 실행 중 작업을 중단하지 않으며, 운영체제 종료 뒤에는 자동으로 재실행하지 않는다.

### 앵커 좌표 생성 이력

공통 앵커 편집기의 `좌표 저장`은 `character-animation anchor-save` 명령을 사용한다. 저장마다 `.tmp/test/animation-anchor-edits/<한국시간>/<생성ID>/`에 request.json, coordinates.json, result.json, status.json을 보관하며 기존 기록을 덮어쓰지 않는다. 원본 애니메이션 에셋 적용과 좌표 저장은 별개다.

```sh
python tools/manager.py command character-animation anchor-save --document-file coordinates.json
python tools/manager.py command character-animation anchor-history --animation-id character.default.white-shirt.idle --animation-version 6
python tools/manager.py command character-animation anchor-load 2026-09-27_22-00-00-12345678
```

GUI의 좌표 생성 이력에서 저장 시각·완료 상태·프레임 수를 확인하고 불러올 수 있다. 불러오기는 현재 애니메이션 버전·시트 해시·좌표 모드·프레임 구성을 확인한 뒤 편집 화면에 적용한다. 좌표 JSON 다운로드는 제공하지 않는다. 이력은 공용 저장형 카드 UI에서 8건씩 탐색하고, 카드 선택 후 입력값 조회와 불러오기를 분리한다.

좌표 이력 전체 초기화는 현재 애니메이션 ID·버전의 목록만 비우고 원본 파일을 유지한다. GUI 마지막 접이식 영역에서 확인 후 실행하거나 `python3 tools/manager.py command character-animation anchor-history-reset --animation-id <ID> --animation-version <VERSION>`을 사용한다. 초기화 이후 새 저장은 다시 목록에 추가된다.

### 추가 가이드라인

스프라이트 편집기의 `가로 가이드 추가`·`세로 가이드 추가`로 전체 프레임 공통 가이드를 최대 32개 추가한다. 위치 입력은 출력 셀의 왼쪽(X)·위(Y) 기준 px이며 개별 삭제와 실행 취소를 지원한다. 프로젝트 저장 시 v2 문서의 선택 필드 `guides`에 `{axis: horizontal|vertical, position: 0~1}`로 보존한다. 출력 크기가 바뀌면 상대 위치를 유지하며 PNG에는 포함하지 않는다. 기존 가이드 없는 v1/v2 저장본도 그대로 읽는다. GUI·CLI의 `sprite-save`는 같은 방향·좌표·개수 검증을 사용한다.

### 스프라이트 저장 이력 공통 UI

프로젝트 저장은 기존 `.local/sprite-editor/<원본 ID 해시>/`의 누적 버전을 유지한다. 공통 `saved-record-history.js`의 카드·선택·8건 페이지 탐색·새로고침을 사용하며, 선택 이력은 입력값 조회 또는 편집기로 불러올 수 있다. 불러오기는 저장본을 덮어쓰지 않으며 실행 취소할 수 있다. 원본 버전이 다른 이력은 조회만 허용한다.

GUI와 CLI는 `character-animation sprite-history <원본 ID>` 명령을 공유한다. 응답 `items`에는 `id`, `created_at`, `frames`, `label`, `compatible`, `document`가 포함된다. 예: `python tools/manager.py character-animation sprite-history asset:character.default.white-shirt.idle`. 새 저장은 `sprite-save`, 최신 저장본 조회는 기존 `sprite-load`를 사용한다.

스프라이트 이력 카드를 선택하면 `선택 이력 초기화`, 목록 마지막의 `이력 수동 초기화`를 펼치면 `전체 이력 초기화`를 제공한다. 전체 범위는 현재 원본 ID의 저장 이력이다. 두 동작은 대상·범위를 확인한 뒤 목록에서만 제외하며 저장 JSON과 원본 이미지·현재 편집은 보존한다. 제외된 최신 저장본은 재접속 시 자동 복원하지 않는다. 이후 새로 저장한 이력만 목록에 추가된다. GUI/CLI는 `sprite-history-delete <원본 ID> --revision <이력 ID>`와 `sprite-history-reset <원본 ID>`를 공유한다. 제외 목록은 기존 저장소의 `hidden-history.json`에 영구 보존한다.

프로젝트 저장은 서버에서 각 프레임의 배치·배율을 렌더링해 동일 이력 ID의 `.png`를 `.json`과 함께 보존한다. PNG는 방향별 행·시간순 열의 투명 시트이며 가이드·검수 배경을 포함하지 않는다. 시트 생성 실패 시 성공 이력을 게시하지 않는다. 정규화 JSON·PNG 시트의 브라우저 다운로드 기능은 폐기했다. 프로젝트 저장으로 서버에 보관하고 저장 이력으로 관리한다. 이전 JSON 전용 이력은 입력값을 불러온 후 다시 저장하면 PNG가 생성된다. 초기화는 PNG 파일도 보존한다.

출력 크기 선택·목표 높이 입력 UI는 제거했다. 원본 선택은 항상 표시하고, 저장 시 원본과 동일한 정사각형 셀 크기를 사용한다. 과거 출력 크기가 다른 편집은 배치·배율을 비례 환산한다. 현재 지원 범위는 동일한 크기의 정사각형 원본 셀이며, 크기가 다르거나 직사각형이면 명확한 오류로 거절한다.

### 스프라이트 출력 앵커 하단 여백

새 편집 문서는 v3이며 출력 앵커 Y를 셀 높이의 90%로 둔다. 384px 셀에서는 `(192, 346)`으로 하단 38px를 확보한다. 미리보기와 저장 PNG는 같은 위치를 사용한다. v1/v2 저장본은 불러올 때 배치 Y를 보정하여 기존 출력 위치를 유지하고 다음 저장부터 v3로 보존한다. 기존 저장 PNG는 변경하지 않는다. 수동 이동·확대로 셀을 벗어난 프레임은 기존 잘림 경고를 확인한다.

## 맵 타일 생성기

`floor-tile` GUI와 CLI는 공용 게이트웨이를 통해 Qwen-Image-Edit-2511의 참조 없는 텍스트 생성으로 **512×512·4스텝 단일 이미지**를 생성한다. 사용자 프롬프트를 맨 앞에 두고 `Top down view. Close up. Square. Blank margins. Webtoon style.`를 붙인다. 예: `잔디밭. Top down view. Close up. Square. Blank margins. Webtoon style.` 기본 Seed는 251204이며 무작위 선택과 직접 입력을 지원한다.

사용자 프롬프트(한글) → 시점·클로즈업·정사각형(영문) → 선택적 `Blank margins.` → `Webtoon style.` 순서다. GUI의 **여백 추가**는 기본 ON이며 OFF일 때 여백 문구만 제외한다. CLI는 `--add-margins` / `--no-add-margins`로 지정하며 생략하면 서버 기본값을 따른다. 요청·이력에 `add_margins`를 저장하고 입력 재사용 시 복원한다. 옵션이 없는 과거 이력의 입력 재사용은 OFF로 표시한다.

기본 프롬프트는 `generators/terrain/config/floor_tile.yaml`에서 관리한다. 크기·스텝·고정 문구 변경 요청은 서버에서 거절한다. GUI에는 사용자·기본·최종 단어 수와 실제 전달 문구를 표시한다.

```bash
python3 tools/manager.py command floor-tile generate --prompt '잔디와 들꽃' --detach
python3 tools/manager.py command floor-tile status GENERATION_ID
```

신규 생성은 Qwen 2511을 한 번 실행하며 격자 생성·중앙 크롭·재생성 단계를 실행하지 않는다. 모델은 서버에서 고정하며 요청으로 선택할 수 없다. 모델 준비는 생성 시 검증하므로 별도 `prepare` 명령은 제공하지 않는다. 최종 원본은 `result.png`다. 요청·프롬프트 해시·결과·로그와 생성 이력 경로는 `.tmp/test/qwen-image-2512/floor-tile/<생성 ID>/`, `.tmp/manager-current/floor-tile/`를 유지한다. 새 요청에 모델 ID와 빈 참조 목록을 보존한다. 예상 시간은 같은 모델의 이력만 사용한다. 기존 2512 단일 생성과 다단계 이력은 조회만 가능하다. 이전 기록은 저장된 GPU 명령 유무와 관계없이 서버에서 재개를 거절하며, 현재 설정으로 새로 생성해야 한다.

## 표정 생성기

표정 생성과 Qwen 2511 참조 생성은 이력을 분리 운영한다. 표정 이력은 `.tmp/manager-current/expression/`, 실행 결과는 `.tmp/test/expression-generator/`에 저장한다. Qwen 2511 참조 이력은 `.tmp/manager-current/qwen-2511/`, 실행 결과는 `.tmp/test/qwen-image-2511-three-reference/`에 저장한다. 조회·삭제·초기화는 요청한 서비스의 이력에만 적용하며 다른 생성기의 기록은 변경하지 않는다.

관리 메뉴의 **표정 생성기**(`/?tool=expression-generator`)는 Qwen-Image-Edit-2511 고정 모델로 참조 PNG 1~3장을 받아 한 표정을 생성한다. 첫 이미지를 편집 대상으로, 추가 이미지를 동일 캐릭터의 외형 참고로 사용한다. 불투명 RGB/RGBA PNG·장당 3MB 이하이며 크기·비율은 기존 Qwen 참조 입력 검증을 따른다.

AiBook P7-5.9 `v2026.09.16`의 현행 39개 표정을 프리셋으로 채택했다. AU 목록은 얼굴 움직임을 기술하는 설계 참고이며 AU 검출값·감정 판정·FACS 강도 측정이 아니다. 얼굴 동일성, 좌우 눈 감김, 입술·볼 변화는 결과에서 직접 검수한다. 자료의 20스텝 실험을 재현하는 모드는 아니며 기존 실행기의 4스텝 Lightning 또는 30스텝 표준 설정을 사용한다.

실행용 원본은 `generators/image/config/expression_presets.yaml`이다. AiBook 원본 spec 해시·자료 버전과 움직임 지시·AU를 보존하며 다른 저장소를 런타임에 읽지 않는다. 모델 입력은 움직임 지시와 외형 유지 지시를 결합한 100단어 미만의 양성 프롬프트다. GUI는 개별·최종 단어 수를 표시하고 요청에는 선택 ID·AU·출처·설정 해시·최종 프롬프트·단어 수·SHA-256을 기록한다. 참조 사본도 순서·해시를 보존하며 재개 시 검증한다.

```bash
python3 tools/manager.py help expression generate
python3 tools/manager.py command expression generate --expression joy --reference face.png --detach
python3 tools/manager.py command expression history
python3 tools/manager.py command expression status GENERATION_ID
python3 tools/manager.py command expression cancel GENERATION_ID
python3 tools/manager.py command expression resume GENERATION_ID
```

`--expression`의 선택 목록은 help에서 확인한다. HTTP 계약은 기존 이미지 요청과 같은 `prompt` 필드에 표정 ID를 전달한다. 모델명·임의 추가 필드는 거절한다. 기본값은 512×512·4스텝·Seed 10107이다. GUI·CLI는 `expression` 서비스와 공용 게이트웨이·GPU 작업 실행기를 공유한다. 결과는 `.tmp/test/expression-generator/<한국시간-생성ID>/`, 이력 인덱스는 `.tmp/manager-current/expression/`에 누적한다. 이력 삭제·수동 초기화는 해당 작업의 결과·참조·로그 파일도 함께 삭제한다. 브라우저 종료는 작업 종료가 아니다.

새 메뉴와 서비스 반영에는 GUI·게이트웨이 코드 갱신이 필요하다. 생성 품질 확인은 참조를 입력한 단일 이미지부터 진행한다. 정식 에셋 등록은 별도 채택 후 수행한다. 이번 추가는 로컬 서비스·UI 확장이며 AWS 배포 구조나 고정 비용 리소스에는 변경이 없다.

## 이전 심리스 타일 연결 보정 (schema 1·2)

이미지 생성 분류의 **심리스 타일 생성기** (`?tool=seamless-tile-generator`)는
정사각형 불투명 PNG 한 장을 받아 256×256으로 정규화하고 3×3 반복 이미지를 만듭니다.
고정 Qwen-Image-Edit-2511 모델이 768×768 연결 보정을 수행한 뒤 중앙 좌표
`(256, 256, 512, 512)`를 기계식으로 추출합니다. 4/30스텝을 지원합니다.
최종 프롬프트는 사용자 표면 설명과 추적 설정 `generators/image/config/seamless_tile.yaml`을
합치며 100단어 미만으로 제한합니다.

```bash
python3 tools/manager.py command seamless-tile generate --prompt '잔디밭' --reference /absolute/path/tile.png --detach
python3 tools/manager.py command seamless-tile status 생성_ID
python3 tools/manager.py command seamless-tile resume 생성_ID
```

GUI와 CLI는 `/seamless-tile-generator` 공용 서비스와
`.tmp/test/seamless-tile-generator/<생성_ID>/` 기록을 공유합니다.
원본 `reference-1.png`, 반복 입력 `grid-input.png`, 보정본 `grid-edited.png`,
중앙 타일 `result.png`, 반복 검수본 `tiled-preview.png`와 프롬프트·해시 기록을 보관합니다.
재개는 저장된 입력·프롬프트로 보정부터 재실행합니다. 이력 삭제·초기화는 이 생성기의 기록에만 적용됩니다.

AI 편집은 반대편 경계의 주기적 일치를 보장하지 않습니다. 반복 검수본을 확인한 뒤
채택해야 하며 결과는 자동으로 정식 에셋에 등록하지 않습니다.

### 심리스 생성기 Qwen Image 2.1 실행

새 심리스 작업은 고정 `Qwen/Qwen-Image-2.1` revision
`d26bb61231c349cf6b7896fa83353113880e1ba3`과 40스텝을 사용한다.
GUI와 `tools/manager.py command seamless-tile generate`는 같은 공용 게이트웨이와 이력을 사용한다.
원본은 256×256으로 정규화한 뒤 768×768 반복 참조를 전달하고, 중앙 256 타일 및 반복 미리보기를 저장한다.
기본 프롬프트는 `generators/image/config/seamless_tile.yaml`에서 추적한다.
이전 schema 1 기록의 재개는 2511 실행기를 유지하며 새 schema 2 기록은 2.1 실행기로 고정된다.
기존 URL·서비스 이름·기록 저장 경로는 변경하지 않는다.

2.1 작업자는 `.venv-qwen21` 분리 환경에서 실행한다. 검증 환경은 Python 3.12,
PyTorch 2.11.0+cu128, diffusers git `8b33bfc04b6b5e8bb58a58e55f68746c1bbee4cd`,
transformers 5.18.0, accelerate 1.13.0이다. 모델은
`.model/qwen-image-2.1/<revision>/`에 공식 snapshot 전체를 준비한다.
환경·모델이 없으면 접수 전에 실패하며 실행 중 자동 설치나 다른 모델 대체는 없다.
현재 실험 환경은 기존 `.venv` 패키지를 `.pth`로 재사용하고 diffusers·transformers만 분리 설치했다.
기존 환경 삭제·갱신 시 해당 의존성을 재검증해야 한다.
GPU 추론에는 sequential CPU offload와 VAE tiling을 사용한다. CPU 단독 추론은 허용하지 않는다.
2.1 모델 실행 성공과 심리스 품질 승인은 구분하며 반복 검수 후 사용자 채택을 받는다.

### Qwen 2.1 이미지 생성기 — 추가 프롬프트 없음

이미지 생성 분류의 `Qwen 2.1 이미지 생성기`는 입력한 프롬프트 원문을 그대로 전달한다.
자동 기본·화풍·부정 프롬프트는 추가하지 않으며 공백·줄바꿈도 유지한다. 입력은 1~99단어다.
고정 모델·환경은 위 2.1 실행 기준과 같고 스텝은 20·30·40·50 중 선택한다(기본 40). 기본 출력은 768×768이다.
256 이상 16의 배수인 출력 해상도를 사용한다. GUI는 256·512·768·1024·1280을 제공하며 기본값은 768이다.
참조가 없으면 텍스트 생성, 참조가 있으면 번호 순서대로 이미지 편집을 수행한다.
모델 카드의 최대 10장까지 지원하며 각 참조는 RGB/RGBA PNG, 3MB 이하다. Qwen 2.1은 투명 영역을 흰색 배경에 합성하고 모델에 전달할 RGB 사본을 저장한다. GUI와 CLI에 동일하게 적용하며 원본 파일은 변경하지 않는다.
공용 파일 불러오기·클립보드 붙여넣기를 사용한다. 처음 한 칸에서 `이미지 추가`로 최대 10칸까지 늘린다. 각 칸의 `삭제`는 뒤의 참조를 앞으로 이동하며, 빈 칸은 모델에 전달하지 않는다. 이력 복원은 저장된 참조 수만큼 입력 칸을 펼친다. 실제 GPU 사용량은 참조 수와 해상도에 따라 달라진다.

```bash
.venv/bin/python tools/manager.py command qwen-21 generate --prompt '붉은 사과 하나. 흰 배경.' --detach
.venv/bin/python tools/manager.py command qwen-21 generate --prompt-file /tmp/prompt.txt --reference /tmp/one.png --reference /tmp/two.png --width 512 --height 512 --detach
.venv/bin/python tools/manager.py command qwen-21 history
```

서비스는 `qwen-21`, 페이지는 `?tool=qwen-21-generator`, API는 `/image-generation-21`이다.
기록은 `.tmp/test/qwen-image-21/<생성 ID>/`와 공용 이력 저장소의 `qwen-21`에 저장한다.
참조 순서·해시·원문·단어 수·모델 revision을 보존하고 재개 시 다시 검증한다.
이 생성기의 초기화·삭제는 심리스 및 기존 2511·2512 이력에 영향을 주지 않는다.

### 이미지 생성 이력의 재시작 보존

Qwen 2511·2512·2.1, 심리스, 표정, 건물·바닥 생성기는 `common/generation_records.py`의 공용 조회를 사용한다. 기존 색인 경로를 유지하며 색인이 누락된 경우 해당 생성기 작업 폴더의 `request.json`·`status.json`을 합쳐 조회한다. 작업 ID 형식이 아닌 실험 폴더는 포함하지 않는다. 삭제 표시와 이전 초기화 시각은 존중하며, 종료된 작업의 명시적 삭제·초기화는 기존대로 파일도 제거한다. 조회 자체는 색인을 다시 쓰지 않는다.

검수 화면 재빌드는 자신이 만든 화면 파일·애니메이션 게시 폴더만 정리한다. 생성기 이름별 보존 목록을 사용하지 않으며 알 수 없는 폴더, 생성 이력, 서버 기록은 보존한다. 이력 색인 갱신은 공용 원자적 저장을 사용한다.

### 이전 심리스 패턴 단계 생성 (schema 3)

참조 없이 패턴 프롬프트를 입력하면 Qwen 2.1이 768×768의 3×3 패턴을 생성한다. 중앙 256×256을 추출해 경계를 중앙으로 옮기고 512×512로 확대한 뒤 가로·세로 32px의 흰 십자를 만든다. 두 번째 생성은 십자를 주변 패턴으로 채우며, 경계 주변만 합성·역이동하여 최종 256 타일과 3×3 반복 검수 이미지를 저장한다. AI의 3×3 배열 준수와 경계 연결은 보장되지 않으며 단계 미리보기로 검수한다.

```bash
.venv/bin/python tools/manager.py command seamless-tile generate --prompt '가을 낙엽 무늬' --seed 3410256389 --detach
```

각 추론은 40스텝이다. 고정 설정·두 단계 보조 프롬프트는 `generators/image/config/seamless_pattern.yaml`에서 추적하며 최종 프롬프트·단어 수·해시를 요청에 저장한다. 단계별 request/result/checkpoint와 UI 중간 미리보기를 같은 작업 경로에 저장한다. 실패·취소 후 기존 resume 명령은 완료 단계의 입력·출력 해시를 검증해 재사용하고 미완료 단계부터 실행한다. 해시 불일치는 실패한다. 기존 schema 1·2 이력의 조회·재개와 참조 한 장 CLI 요청은 기존 방식으로 유지한다. GUI에서 과거 입력을 불러와 새로 생성하면 새 패턴 방식으로 실행한다.

### 이전 별도 편집 마스크 (schema 4)

schema 4 기록의 두 번째 단계는 내용이 지워지지 않은 원본(`repair-input.png`)과 별도의 RGB 흑백 마스크(`repair-mask.png`)를 순서대로 전달한다. 마스크는 가로·세로 16px 십자이며 흰 영역은 편집, 검은 영역은 보존을 뜻한다. 보정 프롬프트는 재질에 종속되지 않는 고정 지시만 사용한다. 이는 모델의 강제 인페인팅 입력이 아니라 참조 해석이다.

모델 출력 전체를 채택하지 않고 마스크 내부만 원본에 합성한다(`repair-composite.png`). 합성 해상도 512에서 마스크 밖 픽셀을 보존하고 역이동·256 축소 후 반복 검수한다. 최종 축소의 보간까지 원본 픽셀과 같다는 의미는 아니다. 설정·마스크·입력·출력 해시와 단계 체크포인트를 저장한다. 기존 schema 3 작업은 저장된 흰 십자 삭제·페더 합성 방식을 유지하여 재개한다.

### 심리스 패턴 v7: 마스크 없이 가로 연결 후 세로 연결

새 작업은 5단계를 사용한다. 1단계는 사용자 입력 뒤에 영문 기본 문구 `Overhead view, camera pointing straight down at the surface. Softly shaded illustration.`를 줄바꿈으로 구분하여 전달하고 768×768로 생성한다.
2단계는 좌·중·우 3등분 중 중앙 세로 띠를 추출하여 같은 크기로 3열 배열한다.
3단계는 원본 3열 배열 한 장으로 좌우 경계를 연결한다.
4단계는 3단계 결과를 상·중·하로 나누어 중앙 가로 띠를 3행 배열한다.
5단계는 원본 3행 배열 한 장으로 상하 경계를 연결한다. 새 작업(schema 7)은 중앙을 지우거나 마스크를 전달하지 않으며 두 보정 단계 모두 `Connect the boundaries naturally.`를 사용한다. 기존 schema 6 작업도 아직 실행하지 않은 보정 단계는 원본 배열과 현재 보정 프롬프트를 사용한다. 실제 프롬프트는 단계별 request.json에 저장하며 완료된 체크포인트는 덮어쓰지 않는다.
보정은 768×768, 40스텝이며 프롬프트·단어 수·해시를 기록한다.
각 단계 완료 후 검수 대기하며 기존 GUI 다음 단계/재개와 CLI resume을 사용한다.
5단계 전체 768×768 보정 원본은 stage-5-vertical/result.png에 보존한다. 중앙 256×256 영역을 최종 산출물 result.png로 저장하고 이 타일로 3×3 반복 미리보기를 제공한다. 경계 지표도 중앙 타일을 기준으로 계산하며 크롭 좌표와 타일 크기를 result.json에 기록한다.
중앙 타일은 크기 변형 없이 추출하며 정식 에셋 등록은 수행하지 않는다.
폐기된 v5 실행 코드는 제거했다. 기존 기록·이미지는 조회할 수 있지만 재개는 지원하지 않는다. 새 작업을 생성한다.

## 캐릭터 레퍼런스 복장 분리 생성

`animation-separation` 서비스의 GUI·CLI 명령, 참조 이미지 1장 입력과 산출물은 [애니메이션 분리 사용 안내](animation-separation.md)를 따른다. Qwen 2.1로 원본별 신체 베이스·복장을 두 프롬프트로 독립 생성하며 공용 GPU 대기열과 이력을 사용한다.

### Qwen 2.1 순환 VAE 실험
- 이미지 생성 분류의 `qwen-21-circular-generator`는 공용 Qwen UI·시드·이력·게이트웨이를 재사용합니다.
- 서비스 `qwen-21-circular`, 기본 512×512·40스텝. 프롬프트 원문만 사용합니다.
- 신규 v2는 최종 잠재값의 XY 반대편을 8칸씩 여백으로 붙여 일반 VAE로 복원한 뒤 여백을 잘라냅니다. 같은 잠재값의 일반 복원 결과와 반복 비교도 저장합니다. 인코더·Transformer는 변경하지 않으며 분할 디코딩을 끕니다. 기존 v1 이력은 합성곱 순환 패딩 방식으로 재개합니다.
- 출력 전체가 타일이고 `tiled-preview.png`는 전체 출력의 3×3 반복입니다. 심리스 품질 보장은 아니며 최종 검수가 필요합니다.
- 기록은 `.tmp/test/qwen-image-21-circular/<생성ID>/`에 누적하고 일반 생성 이력과 분리합니다.
- CLI: `tools/manager.py command qwen-21-circular generate --prompt-file <파일> --width 512 --height 512 --steps 40 --seed 10107 --detach`.

순환 생성기 신규 v3 실험은 512×512 텍스트 입력에 생성 토큰 경계 K/V와 상대 RoPE를 추가합니다. 일반 VAE를 사용하며 참조 입력은 거절합니다. v1·v2 기록의 재개 방식은 보존합니다. ComfyUI-AdvancedTiling의 사각형 순환 Attention 원리를 참고한 Qwen 2.1 전용 구현이며 호환·품질 보장은 아닙니다.

현재 v7은 좌우·상하 경계 참조 반경을 각각 8토큰으로 적용하고, 동일 잠재값을 일반 VAE와 순환 VAE로 복원하여 비교합니다. v4의 국소 경계 참조, v5의 VAE 비교, v6의 좌우 2·상하 4토큰을 포함한 이전 기록 설정은 재개 시 유지합니다. 기본 출력은 512×512이며 반경은 이미지 삭제 폭이 아닌 Attention 참조 범위입니다.

현재 v8 실험은 v7의 양방향 반경 8토큰과 VAE 비교를 유지하고, 반대편 경계 K/V 참조를 1줄에서 2줄로 늘립니다. 모서리 대각선 참조는 추가하지 않으며 이전 기록은 저장된 설정을 유지합니다.

v9는 2줄 참조 실험의 품질 저하에 따라 참조 폭을 1줄로 복원하고 네 모서리의 대각선 K/V 참조를 추가합니다. 양방향 반경 8토큰·VAE 비교는 유지하며 v8 이력은 기존 2줄 설정으로 재개합니다.

v10은 기준 v7의 1줄 참조로 돌아가 대각선 참조를 끄고 좌우·상하 반경만 12토큰으로 확대합니다. 비교 실험은 같은 프롬프트·시드·크기를 유지하며 이전 기록의 설정은 보존합니다.

순환 생성기의 순환 참조 반경은 UI에서 4·8·12·16·24토큰을 선택합니다(기본 12). CLI는 --circular-radius 4|8|12|16|24, 게이트웨이 입력은 circular_radius 정수를 사용합니다. 신규 v16/v17은 상하·좌우와 경계 수직·평행 방향 모두에 선택한 같은 반경을 적용하는 정사각형 참조 창을 사용하고, 반대편 가장자리의 실제 2줄 K/V를 순환 좌표로 확장합니다. 따라서 경계 바로 안쪽 줄눈·질감까지 접합 문맥으로 사용합니다. 모서리 대각선 참조는 사용하지 않으며, v10~v15 이력은 저장된 마스크와 스트립 폭을 유지합니다.

순환 생성기의 부드러운 음영 옵션은 기본 OFF입니다. ON이면 사용자 입력 뒤에 추적된 기본 문구 Illustration with soft shading.을 추가합니다. CLI는 --soft-shading/--no-soft-shading, 게이트웨이는 soft_shading 불리언을 사용합니다. 원문·선택값·최종 프롬프트 및 최종 단어 수·해시를 기록하고 이력 불러오기에서 원문과 선택값을 복원합니다.

탑뷰·반복 패턴·클로즈업 옵션은 기본 ON이며 Top view. Repeat pattern. Close-up을 사용자 입력 다음에 추가합니다. 기본 입력은 잔디와 꽃을 그린다.로 분리합니다. CLI는 --pattern-view/--no-pattern-view, 게이트웨이는 pattern_view 불리언을 사용합니다. 음영 옵션과 독립적이며 순서는 사용자 입력 → 시점 문구 → 음영 문구입니다. 옵션 도입 전 이력은 프롬프트 원문을 유지하고 옵션 OFF로 불러와 중복 추가를 방지합니다.

일반 VAE 비교 생성은 기본 OFF입니다. GUI 체크박스·CLI --baseline-decode/--no-baseline-decode·게이트웨이 baseline_decode 불리언으로 선택합니다. OFF는 일반 VAE 디코딩·비교 이미지·잠재값 비교용 저장을 생략하고 순환 결과와 3×3 반복만 생성합니다. 기존 이력과 저장된 비교 ON 설정은 유지합니다.

순환 생성기의 신규 생성 기본 크기는 UI·CLI 모두 512×512, 순환 참조 반경은 12토큰입니다. 기존 생성 이력을 불러오거나 재개하면 해당 기록의 크기와 반경을 유지합니다.

## 복장 착용 생성기

이미지 생성 분류의 `outfit-transfer-generator`는 Qwen Image 2.1을 사용합니다. 첫 참조는 바디(외형·신체 비율·자세 기준), 두 번째는 아웃핏(의상·신발 디자인)이며 정확히 두 장이 필요합니다. 공용 파일 업로드·클립보드 입력, 랜덤 시드, 이력·취소·재개를 사용합니다. 출력은 512 또는 768 정사각형이며 기본 768·40스텝입니다. 기본 프롬프트는 `generators/image/config/outfit-transfer-prompt.txt`에서 추적하며 UI에서 고정 프롬프트를 해제하면 편집할 수 있습니다. 모델 출력의 신체 비율·착용 정합은 검수가 필요합니다.

```bash
python3 tools/manager.py command outfit-transfer generate --reference /path/body.png --reference /path/outfit.png --resolution 768 --detach
```

HTTP 서비스는 `outfit-transfer`, 명령은 `generate`이며 `images`에 바디·아웃핏 순서의 base64 PNG 두 장을 전달합니다. 나머지 프롬프트·크기·스텝·시드 계약은 Qwen 2.1과 같습니다. 기록은 `.tmp/test/outfit-transfer/`에 보존하고 기존 생성기의 이력과 구분합니다.

순환 생성기 v17은 참조 이미지 1~10장을 선택적으로 지원합니다. 공용 업로드·클립보드·추가/삭제 UI와 이력 입력 복원을 사용합니다. CLI는 `--reference <PNG>`를 반복하며, 게이트웨이는 기존 `images` 배열을 사용합니다. 참조 인코더와 참조·텍스트 prefix는 기존 Qwen 처리를 유지하고 생성 이미지 토큰만 순환 확장합니다. 순환 VAE는 디코더에만 적용합니다. 참조 없는 신규 작업도 v16의 2줄 경계 스트립과 동일 반경 참조 창을 사용하며, 과거 기록은 저장된 설정을 유지합니다. 참조 장수와 크기에 따라 GPU 메모리 사용이 늘어나므로 첫 검증은 작은 해상도와 참조 1장으로 진행합니다.

## 스프라이트 정규화 편집기 v2

`?tool=sprite-editor-v2&category=animation-tool`에서 독립 작업을 만든다. 기본 출력 셀은 384×384이고 256×256을 선택할 수 있다. 레퍼런스 한 장과 시간순 프레임을 파일·드래그·클립보드로 등록한다. 입력은 정지 PNG/JPEG/WebP(한 장당 8MB, 1600만 픽셀), 최대 128프레임이다. 붙여넣기 버튼이 브라우저 권한으로 거절되면 대상 선택 후 Ctrl+V 또는 파일 불러오기를 사용한다.

참조와 프레임은 동일한 출력 좌표계에서 표시한다. 이미지의 긴 변을 셀에 맞춘 상태가 배율 1이다. 1px 조이패드는 출력 좌표 기준이고 배율 패드는 0.01 단위다. 얼굴 원과 신체 가이드는 독립 측정값이며 이미지 이동에 따라 자동 변경되지 않는다. 원의 크기를 기준에 맞추고 중심을 각 프레임 얼굴로 이동하거나, 지름을 측정해 비율을 비교한다. 위치 정렬과 얼굴·체형 자체를 다시 그리는 AI 보정은 별도 작업이다. 앉거나 굽힌 프레임의 몸체 높이를 서 있는 참조와 강제로 맞추지 않는다.

가이드라인 편집에서 선택한 선의 이름·가로/세로 방향·좌표를 수정한다. 가이드 선택은 신체 가이드 조절 모드로 전환하며 드래그와 1px 패드로 이동한다. 얼굴 원은 중심 X/Y와 지름을 직접 입력할 수 있다. 레퍼런스 가이드·얼굴 원 복사는 편집 대상 프레임의 측정값을 교체하며 이미지 배치는 변경하지 않는다. 실행 취소와 수정본 저장·이력 불러오기를 지원한다.

원본 이미지·편집 문서·불변 수정 이력·출력 ZIP은 `.tmp/test/sprite-editor-v2/<한국 시각>/<작업 ID>/`에 저장한다. 이미지 원본은 SHA-256으로 구분하고 덮어쓰지 않는다. 수정본 저장은 새 버전을 추가하며, 다른 화면이 먼저 저장한 경우 저장을 거절한다. 과거 버전 불러오기는 기존 이력을 보존하며 저장 시 새 버전을 만든다. 브라우저 종료 전 저장하지 않은 편집은 보존되지 않는다. Git 추적·리포트 등록은 별도 사용자 지시에 따른다.

출력은 개별 RGBA PNG, 빈칸 없는 시트, 흰 배경 GIF, 편집·프레임 유지 시간 메타데이터를 ZIP으로 묶는다. 시트는 프레임 수를 정확히 나누는 행·열 조합 중 차이가 가장 작은 조합으로 배치하고 열 수를 행 수 이상으로 둔다. 예를 들어 8장은 4열×2행, 9장은 3열×3행, 12장은 4열×3행이며, 7장처럼 소수인 경우 7열×1행이다. 프레임은 왼쪽에서 오른쪽, 위에서 아래 순서다. 원본의 알파를 유지하며 불투명 배경을 자동 제거하지 않는다. 가이드는 출력하지 않는다. GIF는 형식 제약에 따라 10ms 단위로 시간을 반올림한다.

GUI와 CLI는 `character-animation` 서비스의 `sprite-v2-create/list/upload/save/load/history/export/delete` 명령을 공유한다. 통합 CLI의 각 명령은 `--payload-file <JSON 파일>`을 받는다. 생성 입력은 `{"name":"작업명","cellSize":384}`, 목록은 `{}`, 업로드는 `{"id":"작업 ID","data":"이미지 base64"}`, 불러오기·내보내기는 `{"id":"작업 ID","revision":null}`, 이력은 `{"id":"작업 ID"}`, 저장은 `{"id":"작업 ID","parent":"최신 수정 버전","document":{...}}`이다. 업로드 응답의 asset 해시를 문서의 reference·frames가 참조한다. load는 편집 문서와 등록 이미지, 최신 수정 버전을 반환한다. 개별 프레임은 id·asset·name·x·y·scale·duration·face·guides를 포함하며, duration 0은 문서 fps를 사용한다.

- 정규화 편집기 작업 삭제: `sprite-v2-delete`에 `{"id":"작업 ID","confirm":true}`를 전달한다. 선택 작업의 등록 이미지·수정 이력·출력 파일을 삭제하며 복구할 수 없다. GUI는 대상 ID 확인 후 실행하고, 삭제한 작업이 열려 있으면 브라우저 초안도 비운다.

- 선택 수정본 삭제는 `sprite-v2-revision-delete`와 `{"id":"작업 ID","revision":"수정본 ID","confirm":true}`를 사용한다. 최신 삭제 시 남은 가장 최근 저장본을 최신으로 지정하고 마지막 수정본 삭제는 거절한다. 이미지·내보낸 파일과 과거 출처용 parent 값은 유지한다.

### 캐릭터 표현 검수 PNG 캡처

GUI의 **렌더링 PNG 캡처**와 CLI는 `character-review capture` 명령을 공유합니다. 별도의 Chrome/Chromium 헤드리스 프로세스가 공용 맵 렌더러와 등록 에셋을 읽으며, 열려 있는 브라우저 탭이나 관리 UI 서버에 의존하지 않습니다. 명령 게이트웨이는 실행 중이어야 합니다.

```bash
python3 tools/manager.py help character-review capture
python3 tools/manager.py command character-review capture --payload-file /tmp/character-capture.json
```

입력 JSON 예시:
```json
{"ground":"paving","zoom":1,"column":1,"row":1,"outline":true,"rim":true,"shadow":true,"width":768,"height":576}
```

빈 객체 `{}`도 기본 설정으로 실행합니다. 바닥은 `paving`, `grass`, `meadow-road`, 배율은 0.05–4, 위치는 0–2, 회전 `rotation`은 0–3입니다. `shadow_profile`은 `baseline`·`contrast`·`broad`, 바닥 `contrast`는 `original`·`soft`입니다. 너비는 256–1600, 높이는 256–1200이며, 임의 URL·출력 경로는 허용하지 않습니다.

`.tmp/test/character-review-capture/<한국시간>/`에 `baseline.png`, `adjusted.png`, `comparison.png`, `result.yaml`, 로그와 렌더 입력을 저장합니다. 비교 PNG의 왼쪽은 원본, 오른쪽은 조정본입니다. GUI 캡처는 현재 바닥·위치·표현 설정을 200% 배율로 768×576 캔버스 중앙에 재배치하여 저장합니다. CLI 기본 배율도 200%이며 `zoom`으로 변경할 수 있습니다. 화면의 스크롤·드래그 오프셋과 UI 컨트롤은 캡처에 포함하지 않습니다. 애니메이션 첫 프레임을 사용합니다.

캡처의 `outline_width`는 어두운 형태선의 100% 기준 픽셀 폭(1–4, 소수 허용, 기본 1)입니다. 밝은 분리선은 형태선 바깥 100% 기준 1px 띠입니다. 두 선 모두 배율에 선형 비례하며 200%에서는 기본 형태선 2px·분리선 2px로 표시됩니다.

캐릭터 검수 캡처의 width·height는 화면 표시 크기이며 PNG의 가로·세로는 각각 2배입니다. 기본 768×576 영역은 1536×1152 PNG로 저장하며 줌과 캐릭터의 화면 크기는 유지합니다.

### Qwen 2.1 일반 생성기 프롬프트 옵션

`공용 화풍 추가`와 `투명 배경 요청`은 기본 OFF이며 GUI와 CLI에서 동일하게 사용합니다.
CLI는 `--common-style`과 `--transparent-background`를 지원합니다. 게이트웨이 필드는
`common_style`, `transparent_background` 불리언입니다. 공용 기준은 `prompts/art-style.yaml`이며
Qwen 실행용 짧은 영문은 `generators/image/config/qwen_21_prompt_options.yaml`에서 관리합니다.
화풍 문구는 `Hand-painted game illustration, soft shading, clear materials, moderate detail.`입니다.
조합 순서는 **투명 배경 시작 문구 → 공용 화풍 → 사용자 입력 → 투명 배경 마무리 문구**입니다.
투명 문구는 `This is an RGBA image with transparency.`와 `The image has alpha channel and the background is transparent.`를 사용합니다.
선택한 옵션만 합치며 GUI 최종 미리보기와 CLI는 같은 조합 함수를 사용합니다.
신규 작업에는 옵션 문구 사본과 조합 버전을 저장합니다. 대기·재개 작업은 저장된 최종 문구를 검증하며 현재 설정으로 다시 조합하지 않습니다. 입력을 불러와 새로 접수할 때는 현재 설정을 적용합니다.
원문·옵션·추가 문구·최종 단어 수와 해시를 보존하며, 옵션 포함 99단어를 초과하면 거절합니다.
이력 불러오기에서 원문과 옵션을 복원합니다. 투명 배경은 네이티브 RGBA 출력을 요청하며
출력 알파를 보존합니다. 체크무늬를 그리거나 색상 제거 후처리로 투명화를 대신하지 않습니다.

## Wan2.1 VACE R2V 영상 생성기

애니메이션 도구의 **Wan2.1 VACE 영상 생성기**(`?tool=wan21-vace-generator&category=animation-tool`)는 로컬 `Wan-AI/Wan2.1-VACE-1.3B-diffusers` 모델을 사용한다. 참조 PNG 한 장과 프롬프트로 생성하며 `video=None`, `mask=None`이다. 첫 프레임 확장과 중간 포즈 제어는 이 도구의 입력이 아니다. 참조는 전체 이미지를 흰 배경에 합성한 뒤 비율을 유지해 선택한 출력 해상도로 흰 패딩한다. 방향 시트를 자동 분할하지 않으므로 단일 방향 이미지를 첨부한다.

```bash
python3 tools/manager.py command wan21-vace generate --reference /absolute/character.png --prompt-file /absolute/prompt.txt --width 832 --height 480 --frames 81 --steps 50 --flow-shift 5 --guidance-scale 5 --conditioning-scale 1 --seed 42 --detach
python3 tools/manager.py command wan21-vace status <생성ID>
```

GUI·CLI는 `wan21-vace` 서비스의 `generate/status/logs/history/active/model-status/cancel/resume/prioritize/history-delete/history-reset`을 공유한다. 생성 payload는 `{action: "generate", images: ["base64 PNG"], prompt: "장면 묘사", frames: 65, seed: 42, tag: "선택 태그"}`이며 알 수 없는 필드는 거절한다. 참조는 RGB/RGBA PNG 한 장, 3MB 이하이다. 기본값은 832×480·81프레임·50스텝·shift 5·CFG 5·conditioning 1이다. 해상도는 832×480, 480×832, 512×512를 지원한다. 프레임 수는 1~161 범위의 `4n+1` 정수만 허용한다(161은 로컬 도구 운영 상한이며 모델 최대치 주장이 아니다). 16fps 고정으로 81프레임은 5.0625초이며 1프레임은 정지 샘플이다. 스텝은 1~200, shift는 0.1~30, CFG는 1~20, conditioning은 0~2 범위에서 조절한다. API 필드는 `width/height/steps/flow_shift/guidance_scale/conditioning_scale`이고 CLI는 `--width/--height/--steps/--flow-shift/--guidance-scale/--conditioning-scale`이다. 범위는 도구 입력 제한이며 모든 조합의 품질·VRAM 적합성을 보장하지 않는다. 기존 512×512·30스텝 이력은 저장 설정으로 복원·재개한다. 난수 생성은 기존 CPU RNG를 유지하며 모델 연산은 CUDA에서 수행한다. 프롬프트는 자동 확장하지 않고 원문·실제 입력 단어 수·SHA-256을 기록한다. 512 토큰을 넘으면 추론 전에 거절한다. 기본 파라미터와 부정 프롬프트는 `generators/vace/config/defaults.yaml`에서 추적한다.

모델은 `.model/vace-1.3b/weights`에 사전 준비해야 한다. CUDA 연산만 허용하고 CPU 가중치 오프로드·VAE 타일링을 사용한다. 모델 다운로드나 API 호출을 자동 수행하지 않는다. 실제 가중치 revision은 검증되지 않았으며 기록에도 그 한계를 표시한다.

공용 생성 ID 계약에 따라 `.tmp/test/wan21-vace/<한국시간>-<ID>/`에 요청·참조·로그·상태를 보존한다. 실행 시도마다 `attempts/<UUID>/`에 입력 계약·영상·PNG 프레임 ZIP·프롬프트·실행기·ETA·장치별 VRAM 기록을 저장한다. 재개는 저장 입력으로 새 시도를 시작하며 이전 시도는 보존한다. 선택 이력 삭제와 초기화는 목록에서만 숨기며 파일을 삭제하지 않는다. 기존 독립 실험은 이동하거나 자동 이력 등록하지 않는다.

5초 heartbeat에서 공용 추정 코드로 전체 소요·남은 시간·완료 시각·예상 진행률을 기록한다. 같은 설정의 완료 표본이 없으면 전체 ETA는 계산 중으로 표시하며, 최근 추론 스텝에 근거한 추론 종료 추정은 별도로 제공한다. GPU 대기 시간은 제외한다. VRAM은 장치별 프로세스·자식 프로세스 사용량과 장치 전체를 구분해 관측하며 순간 피크 누락 가능성이 있다. 실패·중지·재개 시에도 시도별 기록을 보존한다. 결과 검수는 브라우저 영상 재생과 PNG ZIP으로 수행한다. 생성 성공은 보행·일관성 품질 승인을 의미하지 않는다.

VACE 부정 프롬프트는 GUI의 `부정 프롬프트` 또는 CLI `--negative-prompt`로 실행별 전체 대체한다. 생략하면 기존 기본값을 사용하며 빈 문자열은 부정 프롬프트를 비운다. 저장 입력 복원·재개는 해당 실행값을 유지한다. 양성·부정 입력은 각각 512 토큰을 초과하면 실패하며 원문·단어 수·해시를 실행 기록에 보존한다.

## Phantom R2V 참조 영상 생성기

VACE는 운영 중지되었으며 생성·재개를 거절한다. 기존 이력·결과는 보존하고 조회·삭제·취소 명령은 유지한다. 메뉴에서는 Phantom으로 대체한다.

Phantom 1.3B는 참조 PNG 1~4장으로 S2V 영상을 생성한다. 첫 프레임·비디오 입력은 없다. 기본 832×480, 81프레임/16fps, 50스텝, shift 5, 이미지 가이던스 5, 텍스트 가이던스 7.5, seed 42이다. 해상도는 832×480 고정이며 1~161의 4n+1 프레임만 받는다. 프롬프트는 자동 확장하지 않고 원문을 전달한다. 참조는 공식 비율 유지 Lanczos 리사이즈와 흰 패딩을 적용한다. CUDA 난수·CUDA 모델 연산과 CPU 가중치 오프로드를 사용한다. 모델은 사전 준비된 `.model/phantom-1.3b`와 `.model/wan21-phantom-components`만 사용한다. 실행 코드·VAE 설정·기본값은 `generators/phantom/`에서 추적하며 실험 폴더를 런타임 의존성으로 사용하지 않는다.

```bash
python3 tools/manager.py command phantom generate --reference /absolute/character.png --prompt-file /absolute/prompt.txt --frames 81 --steps 50 --guidance-scale 7.5 --conditioning-scale 5 --detach
python3 tools/manager.py command phantom history
python3 tools/manager.py command phantom status <생성ID>
```

GUI는 `/management/frame/phantom-generator/`이며 기본 입력·영상 길이·접힌 고급 설정·공용 인라인 대기열 확인을 제공한다. 확인 취소는 생성하지 않는다. API `phantom`의 생성 payload는 VACE와 동일한 필드명을 사용하지만 `guidance_scale`은 텍스트, `conditioning_scale`은 이미지 가이던스이다. 저장 경로는 `.tmp/test/phantom/<생성ID>/`이고 시도별 결과·프롬프트·ETA·VRAM은 `attempts/<UUID>/`에 기록한다. 이력 조회·복원·재개·우선 실행·중지·선택 이력 삭제는 공용 게이트웨이를 사용한다. 과거 독립 Phantom 실험은 자동 등록하지 않는다.

Phantom 다중 참조는 공식 README의 최대 4장 규칙을 따른다. GUI에서 이미지 추가·삭제·인접 순서 교환을 제공하며 빈 슬롯은 제외한다. CLI는 `--reference a.png --reference b.png`처럼 반복 지정하고 API는 `images` 배열 순서를 사용한다. 모든 참조의 스냅샷·해시·순서를 저장·복원·재개에서 유지한다. 다중 대상과 같은 대상의 여러 참조를 자동 분류하지 않으므로 프롬프트에서 대상과 행동을 설명한다. 최대 4장은 입력 규칙이며 8GB GPU에서 모든 길이·참조 조합의 메모리 적합성을 검증한 것은 아니다.

사용자 화면·메뉴의 명칭은 **Phantom R2V 영상 생성기**다. R2V는 참조 이미지 기반 영상 생성 방식을 뜻하며, Phantom 원본의 내부 작업 식별자 `s2v-1.3B` 및 저장 계약 `task: s2v`는 그대로 유지한다.

Phantom R2V는 참조 → 장면·부정 프롬프트 → 영상 설정 → 생성 → 상태·결과 순으로 세로 배치한다. 두 프롬프트의 기본값은 없음(빈 문자열)이며 `장면 프롬프트 초기화`와 `부정 프롬프트 초기화`는 각각 해당 입력만 비운다. 장면 프롬프트는 생성 전에 직접 입력해야 한다. 부정 프롬프트를 생략하면 추가 문구 없이 빈 값으로 전달한다. 걷기 예시는 품질 승인 후 별도 샘플로 제공하며 현재 기본값으로 채우지 않는다.

Phantom의 `영상 생성 · 대기열 등록`은 기존 작업의 실행·대기 중에도 사용할 수 있다. 공용 인라인 확인에서 입력을 확인한 뒤 새 작업으로 접수하며, 상태 갱신은 등록 버튼을 비활성화하지 않는다. 실행 중 작업은 선점하거나 중지하지 않는다.

## iframe 제거와 클라이언트 계약

복장 분리(`animation-separation`)의 결과 탭과 생성 이력은 Gradio 안의 캔버스 재생기로 표시한다. 기존 `status`·`history`·`generate`·`cancel`·`resume`·`history-delete` 계약, 생성 ID와 로그·결과 보관 경로는 유지한다. GUI 전환을 위해 CLI 프로세스나 별도 작업 서비스를 실행하지 않는다.

동기 재생·프레임 번호 이동·원본/합성/분리 보기·겹쳐보기 위치와 배율은 브라우저의 해당 재생기에만 적용한다. 결과 탭과 이력 재생기는 서로의 프레임·위치를 바꾸지 않으며 이미지 원본을 저장하거나 덮어쓰지 않는다. 조회한 결과를 바꾸면 기존 재생·요청을 폐기하고 새 결과를 준비한다. 단일 프레임 결과는 재생 대신 비교 안내를 제공한다. 외곽 메뉴와 앵커 래퍼는 직접 합성으로 전환했으며 전장도 번들 v2의 직접 마운트로 전환했다.

앵커 검수 게시 데이터는 `anchor-review-data` JSON 블록으로 분리했다. 이는 브라우저 표시 입력이며 새 게이트웨이 서비스나 CLI 명령을 추가하지 않는다. `character-animation`의 `anchor-save`·`anchor-history`·`anchor-load`·`anchor-history-reset`과 저장 문서의 원본 식별자·버전은 유지한다. 앵커 내부 iframe은 제거하고 공용 캔버스 편집기를 Gradio 문서에 연결했다. 동작 변경 시 브라우저 URL의 `action`과 동작별 초안은 유지하고 이전 요청·재생을 정리한다. 이력 초기화는 대상 동작·버전을 고정한 Gradio 인라인 확인을 거치며 취소·확인 대상 변경·중복 접수는 실행하지 않는다. 모달 확인창은 사용하지 않는다.

이전 형식의 앵커 게시 HTML은 새 템플릿으로 재게시해야 한다. JSON 데이터가 없거나 잘못되면 원인을 표시하고 중단하며 실행 스크립트를 읽어 복구하지 않는다. 재게시 대상은 파생 표시 문서이며 저장 좌표·누적 이력·등록 이미지의 재작성과 구분한다. 외곽 메뉴는 직접 합성으로 전환했다. 전장도 번들 v2로 재게시해 직접 마운트한다.


정적 검수(`gradio-static`)는 메뉴 Sidebar와 해당 Blocks를 한 문서에서 실행한다. `/?tool=<ID>`는 `/management/frame/static-review/?review=<ID>&tool=<ID>`로 연결되며 이 호환 URL의 `frame` 이름은 iframe 사용을 뜻하지 않는다. 검색·분류는 `search`·`category`, 앵커 동작은 `action`으로 유지한다. 같은 도구의 필터 변경은 편집 화면을 다시 로드하지 않고 도구 이동은 브라우저 탐색을 사용하므로 뒤로/앞으로 이동할 수 있다. 현행 생성·맵·편집 도구도 같은 공용 메뉴 합성을 사용한다. 디자인 시스템과 전장은 번들 모듈을 직접 마운트한다. 브라우저 탐색은 작업 서비스의 취소·재개 명령을 호출하지 않는다.


Phantom·HY-Motion·Qwen 계열·복장 분리·ANNY·작가·맵·스프라이트 v2의 GUI 진입점은 공용 메뉴와 한 문서에서 실행된다. 공용 메뉴는 화면만 구성하며 `generate`·`cancel`·`resume`·이력 삭제 등 작업 명령을 대신 실행하지 않는다. 다른 도구로 이동하면 새 GUI 문서를 열고, 같은 도구의 검색·분류 갱신은 입력·재생 화면을 유지한다. 이전 `/management/frame/...` 주소는 호환 주소로 계속 사용한다. 원본 경로로 접속해도 해당 도구를 선택하며, 맵별 주소는 `frameIdentifier`·`frameQuery` 등록을 같은 경로 계산에서 해석한다. 도구 전환 시 다른 도구의 `action`·`map` 등 전용 매개변수를 가져가지 않는다.


디자인 시스템 검수의 번들 v2는 `componentModules`에 페이지 ID와 JS 모듈 경로를 선언한다. 가져오기에서 페이지 등록·JS 파일 존재·경로·해시를 검증하고, GUI는 게시 사본의 `mountReviewPage(host, {locale}) → {dispose()}` 계약을 사용한다. 게임 토큰과 컴포넌트 CSS는 Shadow DOM 내부에만 적용한다. 화면 이탈은 요청 중단·컴포넌트 해제를 수행하며 게이트웨이에 작업 명령을 보내지 않는다. v1 가져오기는 이전 번들 검증용으로 유지하지만 디자인 시스템·전장 직접 표시는 v2 재게시가 필요하며 이전 HTML 실행으로 복구하지 않는다.


전장 모듈은 `readState()`와 `selectField(id)`를 추가로 제공하며 기존 Gradio 선택·렌더 상태 컨트롤이 같은 인스턴스를 사용한다. 선택은 브라우저 URL의 `field`에 보존한다. 미등록 전장은 기존 상태를 변경하기 전에 거절한다. 전체/단일 전장 전환은 이전 타이머·Preact 패널·Phaser 게임을 해제하고, 준비 중인 과거 응답은 새 화면에 적용하지 않는다. 게임 패널의 행동 확인은 검수용 상태 메시지만 갱신하고 실제 전투·게이트웨이 명령을 보내지 않는다.

독립 허브의 `preview.html#항목ID`도 공용 메뉴로 연결한다. `serve.py --root <게시 폴더>`는 `manager-source.json`이 있는 루트의 `preview.html`을 현재 호환 문서로 제공하며 과거 파일은 수정하지 않는다. 새 허브를 게시하면 같은 연결문을 저장한다. 걷기 비교는 독립 문서 링크로 유지하며 앵커 여부는 게시 항목의 `anchorEditor`를 사용하므로 `standing/preview.html`도 기존 주소에서 Gradio 편집기로 열린다. 메뉴의 절대 경로와 게시 목록의 상대 경로는 같은 경로로 비교한다. 이 변경은 조회·탐색에 한정하며 게이트웨이 명령·저장 경로를 추가하거나 변경하지 않는다.


### Wan2.1 VACE V2V 희소 프레임 생성

애니메이션 도구의 `vace-v2v-generator`는 고정 Wan2.1 VACE 1.3B를 사용한다. Phantom R2V와 별도 서비스 `wan21-vace-v2v`로 실행하며 기존 VACE R2V 운영 중지는 유지한다.

번호가 있는 PNG를 여러 장 첨부하면 원래 번호대로 배치한다. 화면은 1부터, 게이트웨이의 `frame_entries[].frame`은 0부터 시작한다. 수정 가능 체크는 흰 마스크, 해제는 검은 마스크이며 현재는 프레임 전체에 적용한다. 첫 프레임도 기본 수정 대상이다. 누락 프레임은 RGB 127 영상과 흰 마스크로 채운다. 마지막 번호가 35이면 총 37프레임으로 올려 `4n+1`을 만족한다. 원본은 변경하지 않고 입력 사본과 해시를 실행 기록에 보존한다.

CLI는 `tools/manager.py command wan21-vace-v2v generate --payload-file <요청.json>`을 사용한다. 요청은 기존 VACE 생성 설정과 PNG base64 문자열 배열 `images`, 같은 순서의 `frame_entries: [{"frame": 0, "editable": true}]`를 포함한다. GUI와 CLI 모두 공용 게이트웨이에서 상태·로그·이력·재개·우선 실행·취소·선택 이력 삭제를 공유한다. 결과는 `.tmp/test/wan21-vace-v2v/<생성 ID>/`에 기록한다.

이 페이지는 번호별 이미지로 입력 영상을 조립하는 V2V 입력을 제공한다. 동영상 파일 업로드·영역별 마스크 편집은 현재 제공하지 않는다. 외형 참조 이미지는 선택적으로 1장을 첨부할 수 있다. API/CLI에서는 `identity_reference_count: 1`과 함께 `images`의 마지막에 외형 참조 PNG를 추가한다. `frame_entries`에는 포즈 입력만 포함한다. 생략 또는 0이면 기존 동작을 유지한다. 참조는 입력 사본·해시와 함께 보존하며 입력값 불러오기·재개에서도 동일하게 전달한다. 수정 가능 프레임의 포즈와 신체 비율을 그대로 유지하거나 교정할 것을 보장하지 않으며 결과 검수가 필요하다.

VACE V2V의 Flow shift 기본값은 3.0이다. GUI 초기값과 CLI/API 요청에서 `flow_shift`를 생략한 경우 동일하게 적용한다. 이력 불러오기와 명시적으로 입력한 값은 실행 당시 설정을 유지한다.

VACE V2V 출력은 832×480(480P)으로 고정한다. GUI 선택은 제거하며 CLI/API도 다른 해상도의 신규 생성·재개를 거절한다. 기존 이력은 그대로 조회하며 입력값 불러오기 후 새 생성은 832×480으로 전환한다. 원본 이미지는 비율을 유지하고 선택한 색상(기본 흰색)의 여백을 추가한다.

포즈·외형 참조 입력이 832×480이 아니면 GUI 업로드 시 경고한다. 생성 등록 시 공용 입력 검증에서 비율을 유지해 리사이즈하고 선택한 색상으로 여백을 추가한 PNG를 저장하므로 CLI/API에도 동일하게 적용된다. 사용자 원본 파일은 수정하지 않으며 과거 이력 검증은 저장 당시 입력을 유지한다.

VACE V2V의 `padding_color`는 `#RRGGBB` 형식의 여백 색상이며 기본값은 `#FFFFFF`입니다. GUI 색상 선택과 CLI `--payload-file` 요청에 동일하게 적용하고 이력에 보존합니다. 포즈·외형 참조 이미지의 비율을 유지해 832×480 안에 맞춘 뒤 남는 공간만 채웁니다. 누락 프레임의 회색 입력과 수정 마스크 색상은 변경하지 않습니다.

## 음악생성

`music-minimax`를 공용 게이트웨이에 등록한다. GUI는 **소리 관리** 분류의 MiniMax Gradio 화면이며, `generate/prepare/model-status/status/logs/history/active/cancel/resume/prioritize/history-delete/history-reset` 명령을 공유한다. `generate` 입력은 `prompt`, `duration_seconds`, `seed`, `loop_request`, `tag`다. 모델·파일 경로를 클라이언트가 지정하지 않는다.

각 서비스는 `/music-…/jobs`, `/music-…/history` 호환 경로를 유지한다. 최종 WAV 조회는 `/music-…/jobs/<id>/attempts/<attempt>/music.wav`다. 모델 준비·실행 환경·저장소·재개·라이선스·8GB 검증 범위는 [음악생성 사용법](../generators/music/README.md)을 따른다. 외부 클라우드 API나 배포 리소스는 추가하지 않는다.

### 생성 이력 파일 정리 적용 범위

공용 이미지 서비스(Qwen·포즈 변환 등), VACE R2V/V2V, Phantom, HY-Motion, 음악 생성기, ANNY 렌더 및 과거 캐릭터 생성 기록의 `history-delete`·`history-reset`은 작업 폴더와 색인을 실제 삭제한다. ANNY도 공용 게이트웨이에서 두 명령을 지원한다. 삭제 응답의 `deleted_jobs`·`deleted_bytes`는 삭제한 작업 수와 파일 크기 합계이며 파일시스템의 실제 여유 공간 증가량과는 다를 수 있다. 전체 초기화는 이전에 목록에서 숨겼던 작업 폴더도 포함한다. 작업 폴더 밖의 원본은 삭제 대상에 포함하지 않으며 심볼릭 링크·상태 미확인·실행 중 작업이 있으면 사전 검증에서 거절한다. 앵커·스프라이트 편집 이력은 이 생성 파일 정리 계약과 구분한다.

### 초기화 대상 사전 조회

`history-reset-preview`는 삭제하지 않고 서비스 소유 작업 폴더의 작업 수·상태·삭제 범위를 반환한다. 목록에서 숨긴 작업도 포함하며 `can_reset=false`이면 `blocked_jobs`의 작업 종료 또는 상태 오류 해결이 필요하다. 조회 후 실제 초기화에서도 잠금 아래 상태를 다시 검증한다.

```bash
python3 tools/manager.py command pose-transfer history-reset-preview
python3 tools/manager.py command hy-motion history-reset-preview
```

이미지 공통 서비스, VACE·Phantom, 음악, HY-Motion 및 ANNY에 적용한다. ANNY의 별도 브라우저 이력도 작업 수를 사전 조회한다. 공용 Gradio 이력은 `삭제 대상 확인 → 작업 수·복구 불가 확인 → 전체 삭제` 순서이며, 확인 뒤 목록·상태가 변경되면 다시 확인하도록 거절한다. 취소는 파일을 삭제하지 않는다.

### ANNY 프리뷰·렌더 접수

Gradio와 통합 CLI는 `anny` 서비스의 `anny-preview`(메시 프리뷰)와 `anny-render`(이미지 렌더)를 사용한다. 기존 `/anny-attributes/preview`·`/render`는 같은 작업 서비스의 호환 경로다. 속성 JSON에는 기본 체형의 허용 속성과 선택적인 `rotation_y`를 전달하며, 알 수 없는 속성·범위 밖 값은 생성 전에 거절한다.

```bash
python3 tools/manager.py command anny anny-preview --payload-file /absolute/path/attributes.json
python3 tools/manager.py command anny anny-render --payload-file /absolute/path/attributes.json
python3 tools/manager.py command anny status 12345678
```

접수는 생성 ID를 반환한다. 기존 ANNY 작업 폴더·입력·상태·이력·로그 경로를 유지하며 클라이언트별 사본 저장소를 만들지 않는다.

### 작가 문서 작업 공용 명령

작가 Gradio 화면과 CLI는 `writer-agent` 서비스의 `writer-state`, `writer-detail`, `writer-submit`, `writer-apply`를 사용한다. 기존 `/writer-agent/api/` 호환 경로와 문서·색인·작업 기록 경로는 유지한다. 공용 클라이언트가 같은 게이트웨이에서 작가 세션 토큰을 조회해 전달하며 Host·Origin·JSON 크기·세션 토큰 검사를 유지한다.

```bash
python3 tools/manager.py command writer-agent writer-state
python3 tools/manager.py command writer-agent writer-submit --payload-file /absolute/path/request.json
python3 tools/manager.py command writer-agent writer-detail --payload-file /absolute/path/job.json
```

접수 입력은 기존 `{mode, prompt}` 계약이며 mode는 `prepare`, `learn`, `write`, `deduplicate`다. 상세 조회는 `{id}`, 원본 적용은 `{id, proposal_hash}`를 전달한다. `writer-apply`는 조회한 제안 해시와 현재 제안·검토 상태를 다시 검사한다. 적용은 문서 변경 명령이므로 제안 차이를 검토한 후 명시적으로 실행한다. 공용 명령 등록은 GPU 생성기 이력 삭제·재개 기능 구현을 의미하지 않는다.


## 효과음 생성

`sfx-dasheng-audiogen` 서비스는 Dasheng-AudioGen을 고정 사용한다. 공용 음악 작업 서비스·GPU 대기열·Gradio 이력을 재사용하며 음악용 `music-stable-audio` 폐기는 유지한다. `generate/prepare/model-status/status/logs/history/active/cancel/resume/prioritize/history-delete/history-reset-preview/history-reset`을 제공한다. 입력은 `prompt`, `seed`, `loop_request`, `tag`다. 길이는 모델이 자동 예측하며 숫자 duration_seconds는 거절한다. 16kHz mono WAV로 저장하며 최종 프롬프트에 `<|caption|>`를 붙인다. 기존 `sfx-stable-audio`는 폐기하고 이전 기록·캐시는 보존한다. [효과음 사용법](../generators/sound_effects/README.md)에 설치·모델 접근·기록 경로를 정리했다.

### 맵 원본 크기 검수

맵 검수의 `원본 크기 검수 · 저장`에서 선택 맵의 정적 PNG를 고르고 긴 변 64·128·256·384·512px로 비교한다. 노란 마름모는 160×80 타일, 파란 사각형은 이미지 영역, 빨간 점은 접지 앵커다. 선택한 해상도로 먼저 축소한 뒤 기존 맵 표시 크기에 그려 화질을 비교한다. 게임의 `displayHeight`와 건물 점유 크기는 변경하지 않는다. 종횡비·알파를 유지하며 애니메이션 시트와 원본보다 큰 크기의 저장은 거절한다.

GUI와 CLI는 `tools/manager.py command map-assets resize --payload-file <파일>` 명령을 공유한다. 입력 JSON은 `path`(등록 원본 경로), `sha256`(검수한 원본 해시), `size`(선택한 긴 변)로 구성한다. 서비스는 최신 해시 확인 후 원본·등록부 해상도/해시·프론트엔드 잠금을 갱신한다. 축소 전 원본과 요청/결과는 `.tmp/map-asset-resize/<ID>/`에 보관한다. 저장 후 검수 화면을 새로고침한다.

`map-assets map-anchor-save --payload-file <파일>`은 동일 에셋의 공통 앵커를 저장한다. 선택 맵은 편집 대상과 기존 값 검증에만 사용한다. 입력은 `map`, `kind`(town/field), `texture`, `anchorX`, `anchorY`, `expected`(에셋 공용 속성 전체 객체, 최초 등록은 null)이다. 기존 값이 달라지면 저장을 거절한다. `slime-assets/assets/maps/sprite-display-properties.yaml`·등록부·백엔드 잠금을 함께 갱신한다. 게임과 검수 로더는 에셋 공용값만 사용한다. 빌보드 공용값이 없거나 맵 원본에 `anchorX`·`anchorY`·`groundFootprintColumns`·`groundFootprintRows`·`displayHeight`가 있으면 명시적으로 실패한다. 신규 빌보드는 배치 전에 공용값을 등록해야 한다. 맵에는 위치·원본 선택과 애니메이션 계약만 보존하며, 타일 배치의 `groundOverrides`는 `position`·`textureKey`만 허용한다. 타일 크기·투영은 공용 렌더러 상수를 사용한다.

빌보드 배치 설정은 `groundFootprintColumns`·`groundFootprintRows`(각 1~8칸)와 `displayHeight`(0 초과 1024px 이하)를 지원한다. 바닥 크기는 접지 영역 검수 기준이며 통행 차단을 추가하는 설정이 아니다. `map-anchor-save`의 선택적 `layout`에 세 값을 함께 전달하고 `expected`에는 공용 원본의 현재 전체 값을 전달한다. 배치별 기대값 목록은 받지 않는다. 건물은 기존 점유 크기 계약을 사용하므로 이 설정으로 변경하지 않는다. 원본 해상도 저장과 에셋 공통 속성 저장은 별도 동작이다. 공통 속성은 이후 추가되는 같은 에셋 배치에도 적용된다.

### VACE F2V 첫 프레임 페이지

`/management/frame/vace-f2v-generator/`는 첫 프레임 이미지 1장을 보존 조건으로 사용하는 전용 GUI다. 파일 이름은 자유이며 입력은 832×480에 비율을 유지해 맞춘다. 이후 프레임은 생성하고 별도 외형 참조는 받지 않는다. VAE 복원 때문에 원본과 픽셀 단위 동일성을 보장하지 않는다.

GUI는 독립 `wan21-vace-f2v` 게이트웨이에 `frame_entries: [{frame: 0, editable: false}]`, 이미지 1장, `identity_reference_count: 0`과 `F2V · 첫 프레임 보존` 태그를 전달한다. 통합 CLI에서도 같은 서비스의 `generate --payload-file`을 사용한다. 모델·GPU 실행 코드·ETA·VRAM 관측 코드는 재사용하되 작업 서비스와 대기열·이력은 V2V와 분리한다. F2V 작업 입력·결과·로그는 `.tmp/test/wan21-vace-f2v/`, 이력은 공용 이력 루트의 `wan21-vace-f2v`에 저장한다. 삭제·초기화는 F2V에만 적용한다. 기존 V2V 저장 작업은 이동하지 않는다. GPU 자원 배정은 공용 실행기가 담당하여 동시 추론 충돌을 막는다. F2V 입력값 불러오기는 첫 프레임 1장 보존 이력만 허용한다.

기본은 81프레임·16fps·50스텝·shift 3·CFG 5·조건 강도 1·시드 42다. 프롬프트는 직접 입력한다. `대기열에 추가` 후 인라인 확인에서 `확인 후 대기열에 추가`로 접수한다.

## 건물 생성 페이지 · Qwen 2.1

`/management/frame/building-generator/`는 기존 `qwen-21` 서비스의 건물 제작용 GUI다. 모델·GPU 대기열·취소·재개·ETA·VRAM 기록·선택 삭제를 공용 구현으로 사용한다. 별도 서비스나 이력 저장소는 만들지 않으며 **일반 Qwen 2.1과 이력 및 이력 초기화 범위를 공유한다.** 건물 이름을 생성 태그로 남긴다.

기본 문구는 Git 관리 대상 `generators/image/config/building-qwen-prompt.txt`다. 기존 ImageGen 직교투영 베이스라인을 변경하지 않는 Qwen 전용 문구이며, 평행선·일정한 축척·바닥 축·출입구 정렬을 지시한다. 실제 맵에서 타일 경계와 건물 바닥 영역·입구를 표시한 레이아웃 이미지를 첫 참조에 업로드하거나 붙여 넣는다. 추가 참조는 외형·자재 기준이며 총 10장까지 지원한다. 임의의 등각 각도를 강제하는 가상 프리셋은 사용하지 않는다.

건물 용도·자재를 문구에 추가하고 최종 99단어 이내인지 확인한다. GUI는 레이아웃 미선택·단어 제한 초과 시 접수를 차단한다. 공용 확인 영역에서 취소하면 작업을 접수하지 않는다. 기본 문구 복원은 프롬프트만 복원한다. 서비스는 최종 문구·단어 수·SHA-256과 참조 사본·해시를 기존 `.tmp/test/qwen-image-21/<ID>/`에 기록한다. 일반 서비스의 텍스트 전용 생성 계약은 유지한다.

CLI에서는 같은 `qwen-21 generate`에 `--prompt-file generators/image/config/building-qwen-prompt.txt --reference /path/layout.png`를 전달한다. 첫 참조가 레이아웃이 되도록 순서를 유지한다. 결과는 자동 등록하지 않으며 실제 맵에서 검수 후 승인된 건물만 `slime-assets/assets/buildings/`로 전달한다. 기본 출력은 512px이며 AWS 배포나 운영 비용 구조에는 변경이 없다.

### 소품 생성 페이지

`/management/frame/prop-generator/`는 상자·가판대·작업대·표지판 등 소품용 Qwen 2.1 GUI다. 추적 기본 문구 `generators/image/config/prop-qwen-prompt.txt`는 직교투영·일정한 축척·접지점·투명 배경을 지시하며 복원 버튼을 제공한다. 대상·용도·자재를 추가하고 옵션 포함 최종 99단어 이내로 유지한다. 레이아웃·외형 참조는 최대 10장 선택 입력이며 텍스트만으로도 생성할 수 있다. 기본 출력은 512×512다.

`prop-generator` 전용 서비스의 대기열·상태·로그·이력을 사용한다. CLI도 `prop-generator generate --prompt-file generators/image/config/prop-qwen-prompt.txt`와 선택 `--reference`로 같은 서비스를 사용한다. 결과는 자동 등록하지 않으며 검수 후 `slime-assets/assets/billboards/`에 소품로 등록한다. 새 모델·작업 실행기·AWS 인프라는 추가하지 않는다.

### 자연물 생성 페이지

`/management/frame/vegetation-generator/`는 나무·관목·풀·꽃·갈대 등 자연물 빌보드용 Qwen 2.1 GUI다. 기본 문구는 추적 파일 `generators/image/config/vegetation-qwen-prompt.txt`에서 관리한다. 직교투영·접지점·완전한 수관·투명 배경을 지시하며 식물 종류·계절·색상·군락 밀도를 추가한다. 옵션 포함 최종 99단어 이내이며 기본 문구 복원을 제공한다. 레이아웃·식물 참조는 선택 사항으로 최대 10장, 기본 출력은 512×512다.

`vegetation-generator` 전용 서비스의 대기열·ETA·VRAM·로그·이력·초기화 범위를 사용한다. CLI는 `vegetation-generator generate --prompt-file generators/image/config/vegetation-qwen-prompt.txt`와 선택 `--reference`를 사용한다. 결과는 자동 등록하지 않으며 검수 후 `slime-assets/assets/billboards/`에 자연물으로 등록한다. 모델·실행기·AWS 인프라는 추가하지 않는다.

### 건물 구도 참조 프리셋

건물 페이지에 2×2·3×3·4×3 점유 크기와 남쪽·동쪽 입구를 조합한 6개 구도 그림을 제공한다. 도시맵 렌더러의 타일 비율 160:80을 적용한 직교투영 가이드이며 파란 부피 선은 높이 참고, 초록 바닥은 점유 영역, 주황 점은 입구다. 위의 가상 프리셋 미사용 설명은 이 기능으로 대체한다. 실제 특정 맵의 고도·주변 건물까지 재현하는 그림은 아니므로 필요한 경우 직접 그린 구도 또는 실제 맵 캡처를 업로드한다.

프리셋 선택은 미리보기만 변경한다. `선택한 구도를 레이아웃 참조에 적용`을 누르면 첫 참조에 그림이 입력된다. 나머지 참조·프롬프트는 유지하며 생성은 자동 실행하지 않는다. 원본 PNG는 `generators/image/config/building-layouts/`에서 Git으로 관리하고 생성 시 기존 참조 사본·해시 기록 계약을 사용한다.

건물 구도 프리셋의 높이는 지면부터 지붕 최고점까지이며 낮음 0.95배(80/84), 보통 1.67배(140/84), 높음 2.38배(200/84) 중 선택한다. 바닥·입구 6종과 조합하여 18종을 제공한다. 파랑 윗면과 오른쪽 눈금으로 표시한다. 층수·실제 미터·맵 배치 높이를 의미하지 않는다. 선택은 미리보기만 바꾸고 적용 버튼으로 첫 참조에 반영한다.

건물 기본 문구는 `건물 기본 프롬프트 추가` 체크박스(기본 켜짐)로 선택한다. 사용자 입력 뒤에 기본 문구와 공용 옵션을 합쳐 최종 단어 수를 계산하고 동일 문구를 게이트웨이로 전달한다. 이력은 합성된 문구를 보존하며 입력값 복원 시 기본 문구 옵션을 끄고 저장 문구를 불러와 중복 추가를 방지한다.

### 건물 생성 대기열 분리
건물 생성 GUI·CLI는 `building-generator` 서비스를 사용한다. 작업은 `.tmp/test/building-generator`, 이력은 공용 이력 루트의 `building-generator`에 보존한다. `python tools/manager.py help building-generator`로 명령을 확인한다. generate/status/history/active/logs/cancel/resume/prioritize/history-delete/history-reset은 이 서비스 범위에서 처리한다. GPU 메모리·동시 실행 잠금은 공용 실행기를 유지한다. 기존 공유 Qwen 작업은 자동 이동하지 않으며 일반 Qwen 화면에서 계속 조회한다. 새 건물 작업부터 독립 저장·관리한다.

### 소품·자연물 대기열 분리
새 소품 작업은 `prop-generator`, 자연물 작업은 `vegetation-generator` 서비스로 등록한다. 작업 저장 경로는 각각 `.tmp/test/prop-generator`, `.tmp/test/vegetation-generator`이며 공용 이력 루트에서도 동일 서비스명으로 분리한다. GUI와 `python tools/manager.py command prop-generator history`, `python tools/manager.py command vegetation-generator history`가 같은 저장소를 조회한다. generate/status/logs/history/active/cancel/resume/prioritize/history-delete/history-reset은 해당 서비스 범위로 처리한다. 기존 Qwen 공유 작업은 이동·삭제하지 않으며 일반 Qwen에서 조회한다. GPU 실행 순서·메모리 보호는 기존 공용 실행기로 유지한다.

### 전체 맵 PNG 캡처 (헤드리스 Chrome)

`map-review capture --payload-file <설정.json>`은 관리 화면을 열거나 맵 불러오기를 누르지 않고 공용 WebGL 렌더러로 전체 맵 PNG를 저장한다. GUI의 ‘화면 로딩 없이 PNG 생성’도 같은 게이트웨이 명령을 사용한다. Chrome/Chromium과 8770 에셋 서버는 필요하다. 야외필드·도시맵을 지원하며 전투필드는 현재 대상이 아니다.

설정 예: `{"map":"ash-edge","show_character":true,"show_safe_boundary":true,"edges":false,"tile_edges":false}`. `map`은 필수이며 나머지는 예시 값이 기본값이다. 원본 맵의 타일·빌보드 배율을 그대로 사용한다. 투명 RGBA PNG, 긴 변 최대 4096px이며 화면 캡처와 같은 전체 범위 계산을 사용한다.

실행: `PYTHONPATH=. .venv-management/bin/python tools/manager.py command map-review capture --payload-file /tmp/map-capture.json`. 응답의 `images.map`이 결과 경로다. 기존 캡처 저장소 `.tmp/test/character-review-capture/<실행 시각>/`에 `map.png`, `result.yaml`, `worker.log`, `browser.log`를 보존한다. 별도 Chrome 프로필을 사용하고 종료 후 정리한다. 입력 오류·리소스 오류·빈 PNG·시간 초과는 실패 처리하며 사용자 브라우저나 실행 중 생성기를 조작하지 않는다.

### 공용 빌보드 에셋 편집

`/management/frame/asset-editor/?tool=asset-editor&category=map-review`에서 전체 빌보드의 표시 높이·점유 열/행·타일 기준 앵커를 편집한다. `billboardAnchorMode: tile-bottom-center`에서 `anchorX/Y`는 투명 여백을 포함한 이미지 사각형 아랫변 중앙의 타일 좌표다. (0.5, 0.5)는 중앙이며 타일 외부 좌표를 보존하기 위해 -16~16을 허용한다. top/bottom은 Y와 0.5를 비교한 읽기 전용 판정으로 공용 원본에 저장하지 않는다. 이미지 원점은 (0.5, 1)로 고정한다. 건물의 이미지 내부 앵커와 구버전 계약은 별도로 유지한다. 맵 검수와 공용 Gradio 속성 입력·썸네일·점유 타일 미리보기를 공유한다. 야외 80×40/0.5배와 마을·전투 160×80/1배를 비교할 수 있다. 별도 프레임 메타데이터가 있는 원본은 시트 표시임을 안내하며 개별 프레임 접지 검수가 필요하다.

- `map-assets asset-list`: 입력 `{}`. `revision`, `assets`를 반환한다.
- `map-assets asset-preview`: `{"revision":"목록 revision","changes":[{"texture":"에셋 ID","values":{"displayHeight":150}}]}`. 공용 규격과 사용 맵의 점유 충돌·고도를 검증하고 변경 전후와 `token`을 반환한다.
- `map-assets asset-save`: 검증 요청에 반환된 `token`을 추가한다. 검증 후 변경된 값·원본은 거절한다. 통행 차단은 배치·점유 크기·공용 높이 80 기준으로 자동 산출한다.

통합 CLI는 `tools/manager.py command map-assets asset-preview --payload-file <요청.json>` 형식으로 같은 게이트웨이를 사용한다. 저장은 공용 속성 YAML·등록부 해시·빌보드 카탈로그·소비자 해시 잠금을 함께 갱신한다. `.tmp/map-asset-editor/`에 검증 요청·저장 영수증·변경 전 백업을 보관한다. 일반 예외 시 원본을 복원한다. 외부 프로세스의 동시 편집을 피하고, 저장 후 목록을 새로고침하여 확인한다. 미리보기/취소는 에셋을 변경하지 않으며 이미지 해상도·맵 좌표는 수정하지 않는다.

공용 빌보드 편집기는 그림자 열·행 이동(-4~4타일)과 가로·세로 배율(0.1~4)을 제공한다. 기본값은 중앙 0·0과 배율 1·1이며, 값은 공용 표시 속성에 저장되어 게임·맵 검수에 함께 적용된다. 미리보기는 동일 렌더러를 사용한다. 타원은 화면 가로·세로, 긴 점유 직사각형은 지면 열·행 길이 배율이다.

### 빌보드 폐기

공용 에셋 편집기의 `선택 빌보드 폐기`는 Gradio 인라인 확인·취소 영역으로 대상을 확인한다. CLI도 `map-assets asset-retire-preview --payload-file`에 `{revision, texture}`를 전달한 뒤 반환된 `token`을 포함하여 `asset-retire`를 호출한다. `revision`은 `asset-list` 응답을 사용한다. 확인 후 선택 대상이나 원본이 변경되면 다시 확인해야 한다.

폐기는 이미지 삭제가 아니라 `assets/retired/billboards/` 이동이다. 등록부 출처·해시를 보존하고 활성 카탈로그·공용 속성·맵 객체·프론트엔드 목록·소비자 잠금을 함께 갱신한다. 실패 시 원복한다. 프레임 메타데이터가 있는 빌보드는 별도 검수가 필요하므로 UI 폐기를 거절한다. 취소는 아무것도 변경하지 않는다.

### 빌보드 교차점 기준 수동 배치 · 2026-10-21

`tile-intersection`은 열·행별 기준 거리를 1칸=0.5, 나머지=칸 수−1로 계산한다. 이 교차점에서 이미지 아랫변 중심까지의 화면 가로·세로 이동을 anchorX×tileWidth, anchorY×tileHeight로 수동 지정한다. 두 값이 0이면 교차점에 놓인다. 점유 크기 변경이나 저장은 수동 앵커를 덮어쓰지 않는다. 이전 tile-bottom-center는 호환 계약으로 유지한다.

그림자 이동 0·0도 같은 교차점이다. 열·행 오프셋은 지면 축을 따라 적용하며 이미지 앵커와 독립적이다. 1×1 미리보기에는 교차점에 맞닿는 주변 네 타일을 흰색·회색 점선으로 표시한다. 보조 타일은 실제 점유나 통행 차단에 포함하지 않는다.

실제 점유 열×행은 유지한다. 3×3 이상에서는 외곽 한 줄을 제외한 내부만 자동 차단한다. 통행 차단만 읽기 전용 파생 값이며, 표시 높이·앵커·그림자 이동은 수동 편집한다.

### MiniMax 토큰 상한 입력

GUI의 `max_new_tokens`는 오디오 프레임 상한이며 125~3,000 정수(5~120초)를 받는다. 250≈10초, 750≈30초, 1,500≈60초, 3,000≈120초다. 종료 토큰이 나오면 더 짧게 끝나므로 정확한 길이·최소 길이를 보장하지 않는다. 프롬프트 단어 수와는 무관하며 큰 값은 최대 연산량을 늘린다.

로컬 Diffusers는 이 값을 직접 받지 않으므로 공용 서비스가 초당 25프레임 기준으로 `duration_seconds`로 정규화하고 실행기는 기존 `audio_duration`에 전달한다. 저장·입력 복원·ETA는 기존 초 단위 계약을 유지한다. GUI는 초를 읽기 전용으로 환산 표시하고 이력 복원 시 토큰 수를 복원한다. 기존 초 단위 요청도 계속 허용한다.

통합 CLI: `python tools/manager.py command music-minimax generate --prompt 'Calm village instrumental' --max-new-tokens 750 --detach`. `--max-new-tokens`와 `--duration-seconds`는 동시에 지정할 수 없다. HTTP `generate`에도 `max_new_tokens`를 전달할 수 있으며 `duration_seconds`와 동시 지정은 거절한다. 이 운영 한도는 공식 모델의 최대 길이와 구분한다.

### 실험용 최소 생성 길이

MiniMax의 `min_duration_seconds` / CLI `--min-duration-seconds`는 기본 0(해제)이다. 최대 길이 이하의 값을 지정하면 해당 프레임 수까지 LM 출력의 종료 토큰을 top-k 후보 선정 전에 억제한다. 최소 50초·최대 60초 예시는 `--min-duration-seconds 50 --max-new-tokens 1500`이다. 무음 덧붙이기나 반복 편집이 아니며 음악적 자연스러움은 청취 검수가 필요하다. 기존 요청·대기 작업에는 적용하지 않는다. 실험 제어 코드 해시와 최소 길이는 시도별 `duration-control.json`, 종료 억제 단계 수는 `minimax-termination.json`에 남긴다. 최대 길이 도달 시 종결 없이 끊길 수 있다.

### MiniMax 별도 가사 입력

`lyrics`를 지정하면 `prompt`에 반주 문구를 자동 추가하지 않습니다. `loop_request=false`이면 입력 설명을 그대로 전달합니다(앞뒤 공백 제외). 반주는 `[Instrumental]`, 보컬은 `[verse]`·`[chorus]`와 가사를 별도 입력합니다. 가사 생략은 기존 이력의 반주 고정·문구 추가 계약을 유지합니다. GUI의 ‘이전 방식’은 기존 이력 복원용입니다.

CLI는 `--lyrics` 또는 `--lyrics-file`을 지원합니다. 예제 조건은 `--duration-seconds 60 --seed 7 --no-loop-request --lyrics-file lyrics.txt`입니다. GUI에서는 audio_duration 60초(환산 1500프레임), 최소 길이 0, 자동 반주 문구·반복 요청 해제를 사용합니다. 조기 종료 가능성은 동일합니다.

로컬 실행은 검증된 Diffusers·CUDA BF16·CPU 메모리 오프로드를 유지합니다. ModelScope 패키지로 교체하지 않습니다. 별도 입력 어댑터는 `prompt`, `lyrics`, `audio_duration`, CUDA 시드, `output=audios`를 전달하고 Tensor 출력을 명시하여 WAV로 저장합니다. 기존 모델 준비 해시는 유지하고 새 어댑터 해시와 실제 입력은 실행 시도별 `input-adapter.json`에 기록합니다.

### 야외 맵 배치·지형 편집

`map-assets`의 `map-edit-load`, `map-edit-preview`, `map-edit-save`는 GUI와 통합 CLI가 공유합니다. `python tools/manager.py command map-assets map-edit-load --payload-file request.json`으로 `{"map":"crystal-cut"}`을 조회합니다. 반환된 `revision`과 함께 `cells`(column·row·tile·height·blocked), `objects`(장식 전체 목록)를 preview에 전달하고, 반환된 `token`을 같은 입력에 추가해 save를 호출합니다. 타일 코드는 조회 결과 `codes`를 사용하고 높이는 0~20 정수입니다. ID·좌표·타일·등록 빌보드·접지·충돌·시작점/출구 연결·고립 셀을 검사합니다.

맵 통합 검수의 **맵 편집 · 야외필드 타일·높이·빌보드**에서 원본을 불러온 뒤 셀을 클릭하고 `선택 셀 가져오기`로 좌표를 가져옵니다. 셀 변경과 빌보드 추가·이동·삭제는 초안에 누적합니다. `한 단계 되돌리기`, `검증·미리보기`, `검증한 변경 저장`을 제공합니다. 삭제도 저장 전에는 원본에 적용되지 않습니다. 초안 버리기는 확인란을 선택해야 하며, 초안 JSON은 별도 보관할 수 있습니다. 브라우저를 닫거나 새로고침하기 전 저장 또는 초안 보관을 완료하세요.

저장 시 맵 YAML 두 파일과 에셋 등록부·백엔드 잠금 해시·빌보드 카탈로그를 갱신합니다. 공용 이미지 변경 잠금 아래 재검증하고 `.tmp/map-layout-editor/<token>-backup/`에 저장 전 원본을 보관합니다. 저장 오류 시 원복합니다. 외부에서 맵이나 공용 에셋 속성이 바뀌면 저장을 거절하고 GUI 초안은 유지합니다. 현재 도시맵·전투필드 편집, 크기 변경, 시작점·출구·건물 변경은 지원하지 않습니다.


#### 맵 검수 화면의 작업 순서

1. 맵 종류와 맵을 고른 뒤 맵 불러오기를 실행합니다. 전체 보기·확대/축소·표시 옵션으로 통행과 배치를 검수합니다.
2. 작업 모드는 미리보기로 시작합니다. 편집을 선택하면 맵 오른쪽에 속성 패널이 나타납니다. 좁은 화면에서는 기본 Gradio 레이아웃에 따라 아래로 배치됩니다. 모드 전환은 초안을 초기화하지 않습니다.
3. 맵에서 타일을 클릭해 선택 셀 가져오기를 누르거나, 열·행을 입력해 좌표의 셀 읽기를 누릅니다. 원본은 자동 준비됩니다.
4. 지형, 빌보드 삭제, 추가, 이동 탭에서 작업합니다. 이동 대상 ID와 목적지 좌표는 별도로 지정합니다. 타일 삭제는 해당 좌표가 배치 기준점인 빌보드 전체, ID 삭제는 선택한 한 개에 적용합니다.
5. 작업과 되돌리기는 자동 검증·미리보기를 수행합니다. 검증 실패 시 초안은 유지하고 마지막 정상 미리보기를 표시합니다. 변경 요약에서 추가·이동·삭제 수와 삭제 ID를 확인합니다.
6. 검증한 변경 저장으로 원본에 반영합니다. PNG 내보내기는 현재 미리보기를 이미지로 내려받는 기능이며 맵 데이터 저장과 다릅니다. 원본 다시 읽기·초안 보관·취소·새로고침은 접힌 보조 영역에 있습니다.

야외필드만 편집할 수 있습니다. 도시맵은 건물·통행 미리보기, 전투필드는 전장·스폰지역 검수를 사용합니다.

#### 반복 편집 툴바

편집 모드의 기본 도구는 화면 이동입니다. 바닥 페인팅·옆면 페인팅·타일 빌보드 삭제·빌보드 삭제·높이 +1·높이 −1 중 선택해 맵을 클릭하거나 드래그합니다. 선택 중인 도구를 다시 누르면 화면 이동으로 돌아갑니다. 바닥과 옆면 재질은 별도 선택하며 옆면 페인팅은 클릭한 벽면을 소유한 셀의 옆면 재질을 바꿉니다. 빌보드 삭제는 보이는 이미지의 불투명 영역을, 타일 빌보드 삭제는 해당 타일을 기준점으로 하는 장식 전체를 대상으로 합니다.

스트로크 중 동일 대상은 한 번만 처리하고, 포인터를 놓으면 한 단계로 초안에 누적해 검증합니다. 실패한 검증은 초안을 보존하고 마지막 정상 미리보기를 유지합니다. 원본에는 `검증한 변경 저장`으로 반영합니다. GUI·CLI의 기존 `map-edit-preview`/`map-edit-save` 계약에서 `cells` 항목의 선택적 `wall` 필드는 등록된 벽면 타일 ID이며, 생략하면 기존 옆면 재질을 유지합니다.

편집 이력은 `한 단계 되돌리기`와 `한 단계 다시 실행`으로 이동합니다. 현재 단계·전체 단계와 각 방향의 남은 횟수를 표시하며, 실행할 이력이 없는 버튼은 비활성화합니다. 새 변경을 적용하면 이후 다시 실행 이력을 비웁니다. 저장은 현재 결과를 새 기준으로 확정하고 이력을 초기화합니다. 이력 이동도 자동 검증·미리보기를 거치며 원본 저장은 별도입니다.

### 맵 편집 임시저장

- 편집 작업을 초안에 반영하면 현재 탭의 `sessionStorage`에 맵별 초안과 Undo/Redo 이력을 자동 보관한다. 입력란만 바꾸고 반영하지 않은 값은 포함하지 않는다.
- 같은 탭을 새로고침한 뒤 맵을 불러오고 편집 모드로 전환하면 복구·검증·미리보기를 실행한다. 원본 revision이 달라지면 자동 복구를 중단하고 임시본을 보존한다.
- 원본 저장 성공 또는 초안 버리기 시 해당 임시본을 정리한다. 저장 실패 시 유지한다. 임시본 JSON 조회와 확인 후 삭제는 `원본 다시 읽기 · 초안 보관과 취소`에서 제공한다.
- 탭 종료 전에는 원본 저장 또는 JSON 보관을 사용한다. 임시저장은 원본 저장을 대신하지 않으며 브라우저 저장 공간 오류를 상태에 표시한다.

### 맵 에셋 선택기

- 바닥·옆면 페인팅 도구에서 해당 선택기를 열어 이름/ID 검색과 5열·1행 배치와 5개씩 페이지 이동을 사용한다. 바닥 썸네일은 공용 렌더러의 재질 매핑을 사용하며 옆면은 등록된 벽 타일로 제한한다.
- 상세 패널의 셀 바닥·추가할 빌보드·배치된 빌보드도 같은 선택기를 사용한다. 배치된 목록에는 현재 초안에 남아 있는 대상과 좌표를 표시한다.
- 썸네일 클릭은 선택값만 바꾸고 선택기를 닫는다. 닫기나 검색은 맵을 변경하지 않는다.
- Gradio 6.28에는 모달 컨테이너가 없어 표준 Group 기반 인라인 선택 영역을 사용한다. 화면 위에 뜨는 모달로 구현된 것은 아니다.
