# 관리도구 GUI·CLI 클라이언트

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
python3 tools/manager.py command momask generate --action walking --detach
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

저장소 루트에서 실행한다.

```bash
python3 tools/manager.py help
python3 tools/manager.py help momask
python3 tools/manager.py help momask generate
python3 tools/manager.py command momask generate --action walking --directions down_left down_right up_left up_right
python3 tools/manager.py command momask generate --action standing --directions down_left --detach
python3 tools/manager.py command momask history
python3 tools/manager.py command momask status GENERATION_ID
python3 tools/manager.py command momask logs GENERATION_ID
python3 tools/manager.py command momask cancel GENERATION_ID
python3 tools/manager.py command momask history-reset
```

MoMask 신규 생성은 대기(`standing`), 걷기(`walking`), 휴식(`resting`)을 지원한다. 폐기된 스트레칭의 기존 생성 이력·결과 조회는 유지하며 새 생성 입력으로 불러올 수 없다.

`generate` 기본 실행은 완료까지 로그를 출력한다. `--detach`는 ID와 기록 경로를 출력하고 반환한다. 대기 중 Ctrl+C는 해당 작업에 취소를 요청한다. 프롬프트·프레임·모델 설정은 웹과 같은 고정 설정을 사용한다. `--directions` 생략 시 네 방향을 생성한다.

## 공용 기록

- `.tmp/momask-generator/jobs/<생성 ID>/request.json`: 실행 요청
- 같은 폴더의 `status.json`, `worker.log`: 상태와 누적 로그
- 같은 폴더의 `motion-run/`, `result/`, `result.json`: 원본·렌더·결과
- `.tmp/momask-generator/history/<생성 ID>.json`: GUI·CLI 공용 이력

결과는 웹 생성 이력의 ‘결과 보기’에서 재생한다. `history-reset` 또는 GUI 수동 초기화만 이력 목록을 제거하며 결과 파일은 삭제하지 않는다. 초기화 후 실행 중이던 작업이 끝나도 제거된 이력을 복원하지 않는다.

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

`management_gateway.py`가 `momask`, `qwen-2512`, `qwen-2511`, `character-animation`의 허용 명령과 HTTP 경로를 관리한다. GUI의 기존 API 호출은 서버 진입점에서 이 게이트웨이를 통과한다. Qwen 통합 CLI는 `POST /management/command`에 `{service, command, payload}`를 보내 같은 서비스 어댑터를 호출한다. MoMask의 로컬 CLI와 웹 어댑터는 공용 `execute_momask_command`를 사용한다.

```text
GUI 기존 API → 명령 경로 변환 ─┐
                             ├→ 통합 명령 게이트웨이 → 생성기 서비스 → 공용 기록
CLI command → 명령 봉투 ──────┘
```

브라우저 요청마다 CLI 프로세스나 셸을 실행하는 방식이 아니라, 통합 CLI와 명령 계약·디스패처를 공유하는 구조다. 생성 원본·이미지·정적 UI 자산은 기존 파일 조회 경로로 제공한다. `command`와 `help`의 기존 사용법은 유지한다. ANNY·작가 에이전트 등 아직 통합 CLI에 등록되지 않은 관리 기능은 이번 게이트웨이 범위에 포함하지 않는다.

게이트웨이는 Host·Origin·JSON 형식·최대 요청 크기·중복 필드·허용 서비스/명령·생성 ID를 확인한 뒤 기존 입력 검증기로 전달한다. 작업에 임의 실행 파일이나 셸 문자열을 전달할 수 없다.

## CLI·게이트웨이 일체화

`tools/manager.py`는 `management_gateway.execute_gateway_cli()`를 호출하는 진입점만 가진다. 서비스·명령 등록, 최상위 `command`/`help` 파싱, 로컬 실행 디스패치와 HTTP 명령 전송은 모두 게이트웨이에 둔다. 생성기별 CLI 실행 모듈은 제거했다. 옵션 파싱·입력 파일 처리·진행 대기·취소도 게이트웨이에 통합하며 GUI와 CLI는 `execute_management_command`를 사용한다. 게이트웨이 명령 전체의 CLI 도움말 진입을 테스트한다.

기존 GUI 주소·이력 경로·관리 서버 필요 여부는 유지한다.

### 단일 실행 구현

`tools/review/momask_commands.py`와 `qwen_commands.py`는 폐기했다. `execute_gateway_arguments`가 등록된 명령의 인자를 해석하고 `execute_management_command`가 로컬 서비스·HTTP 전송·GUI 서비스 어댑터를 선택한다. CLI는 상태·로그 파일을 직접 읽지 않고 명령 서비스를 통해 조회한다. 생성 완료 대기와 Ctrl+C 취소도 생성기별로 중복 구현하지 않는다.

MoMask도 기본적으로 독립 HTTP 게이트웨이에 연결한다. 서비스 함수의 로컬 호출은 내부 작업 서비스·호환 코드에만 남기며 CLI 기본 경로로 사용하지 않는다.

```bash
python3 tools/manager.py command momask --server-url http://127.0.0.1:8771 history
```

## 등록 모션 기반 캐릭터 애니메이션

관리도구의 `#character-animation`은 등록된 대기 v3(16프레임), 걷기 v8(32프레임), 스트레칭 v1(120프레임)에 캐릭터 레퍼런스를 적용한다. 방향은 전체 또는 일부를 선택한다. 현재 등록된 캐릭터는 기본 흰 셔츠 v2이며 등록 설정을 통해 확장한다. 타겟 FPS는 8만 지원하며 생성 배속 기본값은 2다. 생성 배속은 원본 프레임 선택 간격이다. 시작 프레임 + floor(0부터 시작하는 출력 인덱스 × 생성 배속) 위치를 선택하고, 결과의 기본 재생 FPS도 타겟값으로 기록한다. 대기 16프레임·4 FPS 원본을 8 FPS·2배로 생성하면 방향당 8장·1초가 된다. 비정수 장수는 올림하므로 길이 차이는 타겟 한 프레임 미만이다. 보간·중복 프레임 생성은 하지 않는다.

- `openpose`: 등록된 COCO18 맵과 캐릭터 이미지를 Qwen Image Edit 2511에 입력한다.
- `anny`: 등록된 ANNY 리그 렌더 프레임과 캐릭터 이미지를 Qwen Image Edit 2511 + AnyPose에 입력한다. 원본 리그나 모션을 다시 생성하지 않는다.
- 모델·시드는 공용 Qwen 포즈 실행기의 고정 설정이다. 생성 방식은 4스텝 Lightning(기본) 또는 30스텝 표준 생성이며, 30스텝에서는 Lightning 어댑터를 비활성화한다. 고정 보조 프롬프트는 선택한 방향과 리그의 관절·발 위치·가림을 따른다. 고정 기본·보조 원문은 화면과 `catalog`에서 조회하며, 별도의 방향별 추가 보조 문구는 실행 입력으로 지정할 수 있다. 현재 공용 기본 프롬프트의 걷기 지시는 대기·휴식 모션에도 적용된다.
- 기본·보조 프롬프트 파일 위치와 등록 에셋은 `generators/animation/config/character_animation.yaml`에 둔다. 기본·전방 보조·후방 보조 원문은 `generators/animation/config/prompts/`에서 Git으로 관리한다. 보조 문구는 방향을 지정하고 이미지 2의 팔·다리 위치, 관절 굽힘, 발 위치와 자연스러운 가림을 따른다. 양쪽 발뒤꿈치 노출이나 머리·몸통·발의 동일 방향을 강제하지 않는다. 걷기의 모션별 추가 보조 문구는 중복 방지를 위해 비워 둔다. 파일 누락 시 명확한 오류로 중단한다.

```bash
python3 tools/manager.py help character-animation
python3 tools/manager.py command character-animation catalog
python3 tools/manager.py command character-animation generate --motion standing-v3 --character character-default --source openpose --directions down_left down_right --detach
python3 tools/manager.py command character-animation generate --motion walking-v8 --character character-default --source anny --detach
python3 tools/manager.py command character-animation history
python3 tools/manager.py command character-animation status GENERATION_ID
python3 tools/manager.py command character-animation logs GENERATION_ID
python3 tools/manager.py command character-animation cancel GENERATION_ID
python3 tools/manager.py command character-animation history-reset
```

`--directions` 생략 시 네 방향을 생성한다. `--detach` 생략 시 공용 CLI가 완료까지 상태를 출력한다. GUI와 CLI는 독립 게이트웨이의 같은 작업 서비스를 호출한다. 다른 게이트웨이 주소는 서비스 이름 뒤에 `--server-url http://127.0.0.1:포트`로 지정한다. GPU 실행은 샌드박스 밖에서 수행하고 `.model`에 준비된 모델·어댑터를 사용한다. 이미지 생성기와 공용 GPU 파일 잠금을 사용하므로 기존 작업이 끝날 때까지 대기할 수 있다.

기록은 `.tmp/test/character-animation/<YYYY-MM-DD_HH-mm-ss>/<생성 ID>/`에 저장한다. `request.json`에는 고정 프롬프트 원문·해시·단어 수, 모션·캐릭터 매니페스트 해시, 각 참조 프레임 경로·해시가 기록된다. `worker.log`, `status.json`, `progress.json`, `result.json` 및 방향별 프레임을 보관한다. 프레임별 입력은 불투명 512px PNG로 정규화하며 원본을 변경하지 않는다.

이력 인덱스는 `.tmp/test/character-animation/history/`에서 누적한다. 웹의 공용 페이지네이션·ID 복사·로그 조회·수동 초기화 기능을 사용한다. 완료된 이력의 ‘결과 보기 · 재생’에서 방향별 재생·중지·앞뒤 한 프레임 이동을 사용할 수 있다. 초기화는 이력 인덱스만 제거하며 실행 결과를 삭제하지 않는다. 웹 서버 재시작에도 독립 감독 프로세스가 생성·완료 기록을 이어간다.

프레임별 이미지 편집은 동일 레퍼런스·시드를 사용하지만 시간축 일관성을 보장하는 영상 생성 모델은 아니다. 게임 채택 전 프레임 간 외형 변화는 결과 재생으로 검수한다.

캐릭터 애니메이션 화면의 **원본 모션 에셋 검수**에서 생성 전에 선택한 모션을 확인한다. OpenPose와 ANNY 리그 렌더가 같은 프레임으로 나란히 재생된다. 검수 방향은 생성 방향 선택과 독립적이며 네 방향 모두 조회 가능하다. 4 FPS 반복 재생·중지·이전/다음 프레임·슬라이더를 제공한다. 원본 프레임 조회 시 매니페스트 해시와 프레임 범위를 검증하며 생성 작업이나 이력을 만들지 않는다. 브라우저는 다음 프레임을 미리 읽고 캐시 개수를 제한한다.

원본 에셋과 생성 결과 플레이어는 각각 **재생 속도**에서 4·8·12·16 FPS를 선택할 수 있다. 기본은 4 FPS이며 재생 중에도 변경된다. 이는 검수용 재생 속도로, 원본 프레임 수·생성 설정·결과 메타데이터의 FPS는 바꾸지 않는다.

`character-animation generate --target-fps 8 --speed 2`로 CLI에서도 지정한다. 1배는 원본 전체, 2배는 1·3·5…, 4배는 1·5·9…를 선택한다. 원본 FPS와 무관하게 결과는 8 FPS로 재생한다. 요청에는 `target_fps`, `source_fps`, `selected_frame_numbers`와 프롬프트 출처를 기록한다. 결과에는 타겟 `fps`와 원본 프레임 번호를 기록한다. 기존 간격 방식 이력은 수정하지 않으며 신규 `frame_step` 요청은 거절한다. 두 방식의 동시 지정은 거절한다. 원본 검수 플레이어는 항상 전체 원본 프레임을 사용한다.

캐릭터 애니메이션 CLI의 `--steps 4` / `--steps 30`은 웹의 생성 방식 선택과 같다. 예: `python3 tools/manager.py command character-animation generate --motion standing-v3 --character character-default --source anny --steps 30 --detach`. 실행 요청·결과·이력에 선택 스텝을 보존한다. 기존 이력의 스텝 필드가 없으면 기존 방식인 4스텝으로 표시한다.

보조 프롬프트는 `auxiliary`(전방)와 `auxiliary_rear`(후방)의 로컬 파일로 분리한다. 기본 프롬프트는 공통으로 유지한다. 후방은 뒷머리의 머리카락·등·양쪽 발뒤꿈치가 보이도록 명시한다. 방향 앵커는 `back-left`·`back-right`를 사용하고 머리·몸통·발이 같은 방향을 유지하도록 지시한다. 실제 선택한 보조 문구만 기본 프롬프트와 결합하고 화면 단어 수·실행 해시에 반영한다.


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

### 캐릭터 애니메이션 재개

취소·실패 이력의 `이어서 생성` 또는 `python3 tools/manager.py character-animation resume <ID>`로 같은 작업을 재개한다. 저장된 요청과 프롬프트를 유지하며 완료된 `result.json`·유효한 PNG가 있는 프레임은 재사용한다. 미완료 프레임 디렉터리는 `-incomplete-<고유값>` 이름으로 보존한 후 다시 생성한다. 작업 로그는 이어 쓰며 완료 이력을 새로 만들지 않는다. 다른 캐릭터 애니메이션 작업이 실행 중이면 재개를 거절한다.

### MoMask 얼굴 포인트

MoMask 화면의 `얼굴 포인트 ON`을 선택하면 모션 생성 완료 과정에서 OpenPose 맵을 자동 생성한다. 기존 신체맵에 ANNY 공식 COCO 회귀점(코·양눈·양귀)을 같은 카메라로 투영하며 표면에 가려진 점은 제외한다. 68점 얼굴 윤곽·표정 검출 기능은 아니다. OFF는 기존 신체 전용 맵을 생성한다. 결과 캡션과 `result.json`의 `openpose_face_enabled`에 실제 적용값을 기록한다.

CLI는 `momask generate ... --face`를 사용한다. `--no-face`는 얼굴을 제외한다. 정점 수가 공식 회귀 데이터와 다르면 오류로 중단한다. 얼굴 회귀 데이터는 NAVER ANNY의 Apache-2.0 데이터에서 현재 ANNY 토폴로지의 정점 순서로 추출했으며 원본 해시를 함께 보관한다.

캐릭터 애니메이션 출력 해상도는 GUI 또는 CLI의 `--resolution 512|768|1024|1280`으로 선택한다. 기본값은 테스트용 512×512이며 참조 입력은 512px 정규화를 유지한다. 선택 해상도는 요청·결과에 보존하며 재개 시 같은 설정을 사용한다. 생성이력의 입력 내용에서 해상도, FPS, 배속, 스텝, 선택 프레임, 참조 경로·매니페스트 해시와 방향별 실제 프롬프트·단어 수를 확인한다.

### Gradio MoMask UI

MoMask 페이지는 Gradio Blocks로 전환한다. `/momask-generator/`는 관리 셸을 거쳐 GUI 서버 포트 + 101의 로컬 Gradio UI로 연결한다(기본 8871). 외부 공개 없이 `127.0.0.1`에 바인딩하고 관리 서버 종료 시 UI 프로세스도 종료한다. 생성 작업은 기존 독립 감독 프로세스에서 계속 실행한다. CLI·HTTP API·기록 경로는 유지한다.

관리 UI 의존성은 모델 환경과 분리한다. 최초 설치와 공통 검수 의존성 갱신은 `scripts/setup_management.sh`로 수행한다. 실행 로그는 `.tmp/manager-current/gradio.log`에 기록한다. 현재 전환 범위는 MoMask이며 다른 생성기는 기존 UI를 유지한다.

설정·보정값·로그·페이지별 이력·수동 초기화는 Gradio에서 구성한다. 결과 ID 또는 이력 라디오 선택 후 ‘결과 보기’로 HumanML3D·ANNY·OpenPose 동기 재생기를 연다. 재생은 브라우저에서 실행하며 Python 프레임별 호출을 하지 않는다. 아직 기존 공용 이력 UI의 썸네일과 파일 관리자 열기 기능은 이 전환 페이지에 이식되지 않았다.

Gradio 이력은 페이지당 8건의 단일 선택 목록으로 표시하며 선택 후 결과 조회 버튼으로 연다. 공용 로그 패널은 `tools/review/common/gradio_logs.py`를 사용한다. 전체 너비의 접이식 패널에 작업 ID·최근 로그·복사·자동 갱신·최신 줄 따라가기·마지막 줄 이동을 제공한다. 자동 갱신을 끄면 표시 내용을 유지하며 작업 실행은 계속된다.

MoMask Gradio 화면은 새 모션 생성과 생성 이력·결과 재생을 한 흐름으로 구성한다. 결과는 이력 카드를 선택한 뒤 `결과 조회`로만 열며, ID 직접 조회 폼은 제공하지 않는다. 실행 로그는 결과·기록 상세 뒤 전체 너비로 배치한다. 화면 폭이 좁으면 한 열로 전환한다. 배치는 `tools/review/ui/gradio/management-layout.css`에서 관리한다.

### MoMask 렌더 재개

Gradio 생성이력에서 취소·실패 이력을 선택하고 ‘생성 재개’을 누르거나 `python3 tools/manager.py command momask resume <ID>`를 실행한다. 현재 재개 범위는 모션 추론과 ANNY 리그 저장이 완료된 이후의 렌더 단계다. 저장된 리그·렌더 스크립트·카메라를 유지하며 정상 PNG를 검증해 재사용하고 미완료 프레임을 렌더한다. 같은 ID·폴더·로그를 유지하며 마지막에 OpenPose 맵을 생성한다. 리그 이전 단계의 중단은 누락 산출물을 안내하고 거절한다. 이력 초기화로 숨겨진 항목은 자동 복원하지 않는다.

### 로컬 GPU 대기·중지·재개

- MoMask, 캐릭터 애니메이션, Qwen 2511/2512, 타일, ANNY 작업은 공용 `gpu_job_queue.py` 실행기를 사용한다. 클라이언트 연결과 무관한 별도 프로세스가 `.tmp/gpu-queue/`의 접수 순서와 실행 잠금을 관리한다.
- GPU 0의 여유 메모리를 2초마다 조회한다. 초기 입장 기준은 MoMask 4096 MiB, 캐릭터·Qwen·타일 6144 MiB, ANNY 2048 MiB이다. 이는 실측 최대치가 아닌 보수적 실행 입장 기준이며 실제 모델의 최대 사용량을 보장하지 않는다. 기준은 공용 `GPU_MEMORY_REQUIREMENTS`에서 조정한다. 유효 실측 이력이 있으면 최근 20회 중 성공한 작업의 최고 사용량을 예약한다. 현재 여유량에서 실행 중 작업의 미사용 예약분을 뺀 값으로 입장을 판단하며, 고정 안전 여유분은 추가 차감하지 않는다. Qwen 2.1도 해상도·스텝·참조 수와 심리스 파이프라인 버전별로 실측 이력을 분리한다. 공용 대기열은 예약량이 들어가는 작업을 허용하고 각 작업자의 실행 잠금도 유지한다.
- 메모리가 부족하거나 앞선 작업이 실행 중이면 `queued` 상태에 대기 순서·여유/필요 메모리를 저장한다. GPU 조회 실패 또는 전체 메모리 부족은 사유를 기록하고 실패한다. CPU로 우회하지 않는다.
- 생성 이력에서 대기·실행 작업을 중지하고 취소·실패 작업을 재개한다. 중지는 비동기 요청이며 실제 프로세스 종료 후 `cancelled`가 된다. 이력 새로고침으로 확인할 수 있다.
- 같은 ID·저장 입력·참조 사본·누적 로그를 사용한다. 캐릭터 애니메이션은 완료된 프레임을 재사용한다. MoMask는 리그 렌더 재개 자료가 모두 있으면 이어서 렌더하고, 그 이전 단계에서 멈췄으면 저장 입력으로 다시 생성한다. 단일 이미지·ANNY는 저장 입력으로 다시 실행한다.
- 통합 CLI: `tools/manager.py command <서비스> cancel <ID>`, `resume <ID>`, `status <ID>`. 서비스는 `momask`, `character-animation`, `qwen-2511`, `qwen-2512`; ANNY의 이력 상태·중지·재개는 `anny` 서비스에서 제공한다. ANNY 신규 생성은 기존 속성 화면을 사용한다.
- 대기·실행 중인 타일 작업은 파일 초기화 대상에서 제외한다. 서버 재시작은 별도 실행 중 작업을 중단하지 않으며, 운영체제 종료 뒤에는 자동으로 재실행하지 않는다.

휴식은 서서 시작 → 바닥에 앉아 유지 → 완전히 서서 종료하는 순서다. 다리 교차·손 짚기를 강제하지 않는다. 신규 생성은 `motion-quality.json`과 결과 `quality_warnings`에 직립·낮은 자세 유지 검수를 기록한다. 렌더 완료와 자세 검수 통과를 구분하며, 이 검수는 ANNY 스키닝 적합성을 보장하지 않는다.

휴식 검수는 시작·종료 각 10% 구간의 직립 유지와 중앙 1/3 구간의 골반 높이 변화(다리길이 12% 이내), 골반 기준 관절 편차(20% 이내)를 확인한다. 수치는 휴식 후보 판별용 휴리스틱이며 스키닝 통과 판정이 아니다. 프롬프트는 양발 접지 직립, 다리를 앞으로 둔 착석, 정지 유지, 재기립을 순서대로 지시한다.

휴식 신규 생성은 원본 **160프레임 전체**를 사용하며 4 FPS 재생 기준 40초다. 고정 프롬프트: `A person stands fully upright with both feet planted for a few seconds, sits with buttocks on the ground and legs forward for a few seconds, then stands fully upright again.` (31단어). 기존 생성 결과의 프레임 수는 변경하지 않는다.

휴식의 착석은 의자 높이의 공중 착석이 아니라 **엉덩이가 바닥에 닿고 다리를 앞으로 뻗은 자세**로 지시한다. 낮은 골반 검수만으로 바닥 접촉을 보장할 수 없으므로 결과에서 엉덩이 접촉을 별도 확인한다.

휴식은 첫 프레임부터 양발을 딛고 완전히 직립한 상태로 시작해 잠시 서 있는 구간을 둔 뒤 착석한다. 시작 직립 검수는 첫 프레임뿐 아니라 시작 10% 구간에 적용한다.

휴식 프롬프트의 시작 직립과 바닥 착석 유지 구간에는 각각 `for a few seconds`를 명시한다. 이는 모델에 유지 구간을 요청하는 표현이며 정확한 초 수를 보장하지 않는다.

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

### 캐릭터 애니메이션 AnyPose 강도

신규 ANNY 요청은 base·helper 강도를 각각 0.7로 고정하며 요청 기록에 저장한다. 프레임 실행은 저장된 강도를 사용하고 실제 어댑터 강도를 프레임 결과에 기록한다. 강도 필드가 없는 이전 요청은 기존 0.7을 유지한다. OpenPose 입력에는 AnyPose를 적용하지 않는다.

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

### 캐릭터 애니메이션 모션별 프롬프트

`generators/animation/config/character_animation.yaml`의 모션별 `action_prompt`가 동작 지시를 선택한다. 대기는 `standing-action.txt`, 걷기는 `walking-action.txt`, 휴식은 `resting-action.txt`를 사용한다. 공통 `base-prompt.txt`는 외형 보존만 담당한다. 동작 문구와 공통 외형 문구를 결합한 기본 프롬프트에 방향별 고정·사용자 보조 문구를 붙이며, 실제 입력은 100단어 미만으로 검증한다. 모션별 경로 누락·파일 누락·빈 문구는 즉시 거절한다.

카탈로그의 각 모션 `prompts`·`direction_prompts`는 해당 모션의 고정 입력이다. GUI는 모션 선택·이력 불러오기·기본 문구 초기화 시 선택 모션의 원문과 단어 수를 표시한다. CLI와 GUI의 실행 요청은 같은 조합 함수를 사용하고 실제 원문·단어 수·해시는 기존 request.json에 보존한다. 이전 생성 이력의 재개는 저장한 프롬프트를 유지한다. 프롬프트 변경 후에는 1프레임 샘플을 먼저 확인하고 배치 생성으로 확대한다.

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
고정 모델·환경은 위 2.1 실행 기준과 같고 40스텝, 기본 출력은 1024×1024다.
512 이상 16의 배수인 출력 해상도를 사용한다. GUI는 512·768·1024·1280을 제공한다.
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


### 심리스 패턴 v6: 가로 연결 후 세로 연결

새 작업은 5단계를 사용한다. 1단계는 사용자 입력 뒤에 영문 기본 문구 `Overhead view, camera pointing straight down at the surface. Softly shaded illustration.`를 줄바꿈으로 구분하여 전달하고 1024×1024로 생성한다.
2단계는 좌·중·우 3등분 중 중앙 세로 띠를 추출하여 같은 크기로 3열 배열한다.
3단계는 배열 중앙 띠를 흰색으로 지운 참조 한 장으로 좌우 연결을 생성한다.
4단계는 3단계 결과를 상·중·하로 나누어 중앙 가로 띠를 3행 배열한다.
5단계는 중앙 가로 띠를 흰색으로 지운 참조 한 장으로 상하 연결을 생성한다.
보정은 768×768, 40스텝이며 프롬프트·단어 수·해시를 기록한다.
각 단계 완료 후 검수 대기하며 기존 GUI 다음 단계/재개와 CLI resume을 사용한다.
최종 전체 768 이미지를 result.png로 보존하고 3×3 반복 미리보기를 제공한다.
별도의 중앙 크롭·256 축소·정식 에셋 등록은 수행하지 않는다.
폐기된 v5 실행 코드는 제거했다. 기존 기록·이미지는 조회할 수 있지만 재개는 지원하지 않는다. 새 작업을 생성한다.

## 애니메이션 분리 생성기

`animation-separation` 서비스의 GUI·CLI 명령, 샘플 검수 조건과 산출물은 [애니메이션 분리 사용 안내](animation-separation.md)를 따른다. Qwen 2.1로 원본별 신체 베이스·복장을 두 프롬프트로 독립 생성하며 공용 GPU 대기열과 이력을 사용한다.
