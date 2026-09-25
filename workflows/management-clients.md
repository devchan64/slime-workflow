# 관리도구 GUI·CLI 클라이언트

구현 기준은 [AGENTS.md의 Management Client and Gateway Standard](../AGENTS.md#management-client-and-gateway-standard)에 명시한다. 이 문서는 해당 기준의 현재 구현·명령 사용법·기록 경로를 설명한다.

MoMask 작업은 `tools/review/momask_jobs.py` 공용 서비스가 관리한다. 웹 페이지는 GUI 클라이언트이고 `tools/manager.py`는 통합 CLI 클라이언트이다. 웹 HTTP 어댑터와 CLI 명령 어댑터는 생성·상태·이력·취소·수동 초기화에 같은 서비스를 호출한다. 통합 명령 레지스트리는 `momask`, `qwen-2512`, `qwen-2511`, `character-animation`을 제공한다. Qwen은 아래 설명처럼 웹 HTTP API를 공유한다.

```text
웹 GUI → HTTP 어댑터 ─┐
                     ├→ 공용 작업 서비스 → 독립 감독 프로세스 → MoMask 실행기
통합 CLI → 명령 어댑터┘                     └→ 공용 기록 저장소
```

웹 서버 실행 여부와 관계없이 CLI를 사용할 수 있다. 감독 프로세스는 웹 서버 재시작이나 `--detach` CLI 종료와 독립적으로 결과 상태를 기록한다. 파일 잠금으로 GUI·CLI의 동시 생성을 막고, 양쪽에서 같은 생성 ID를 조회하거나 취소한다. GPU 실행은 GPU 접근이 가능한 로컬 환경에서 수행한다.

## command와 help

저장소 루트에서 실행한다.

```bash
python3 tools/manager.py help
python3 tools/manager.py help momask
python3 tools/manager.py help momask generate
python3 tools/manager.py command momask generate --action stretch --directions down_left down_right up_left up_right
python3 tools/manager.py command momask generate --action standing --directions down_left --detach
python3 tools/manager.py command momask history
python3 tools/manager.py command momask status GENERATION_ID
python3 tools/manager.py command momask logs GENERATION_ID
python3 tools/manager.py command momask cancel GENERATION_ID
python3 tools/manager.py command momask history-reset
```

`generate` 기본 실행은 완료까지 로그를 출력한다. `--detach`는 ID와 기록 경로를 출력하고 반환한다. 대기 중 Ctrl+C는 해당 작업에 취소를 요청한다. 프롬프트·프레임·모델 설정은 웹과 같은 고정 설정을 사용한다. `--directions` 생략 시 네 방향을 생성한다.

## 공용 기록

- `.tmp/momask-generator/jobs/<생성 ID>/request.json`: 실행 요청
- 같은 폴더의 `status.json`, `worker.log`: 상태와 누적 로그
- 같은 폴더의 `motion-run/`, `result/`, `result.json`: 원본·렌더·결과
- `.tmp/momask-generator/history/<생성 ID>.json`: GUI·CLI 공용 이력

결과는 웹 생성 이력의 ‘결과 보기’에서 재생한다. `history-reset` 또는 GUI 수동 초기화만 이력 목록을 제거하며 결과 파일은 삭제하지 않는다. 초기화 후 실행 중이던 작업이 끝나도 제거된 이력을 복원하지 않는다.

## Qwen 이미지 생성 두 종류

`qwen-2512`(텍스트 이미지)와 `qwen-2511`(텍스트 또는 참조 1~3장)를 지원한다. 두 명령은 GUI와 같은 HTTP API를 호출하므로 **관리도구 서버가 실행 중이어야 한다**. MoMask의 서버 없이 실행하는 방식과 구분한다. 입력 검증·모델 선택·취소·이력 저장은 기존 서버 구현을 그대로 사용한다.

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

2511의 `--reference`는 512×512 RGB 또는 불투명 RGBA PNG를 최대 3장까지 순서대로 지정한다. 생략하면 텍스트 생성이다. 해상도·스텝·참조 검증은 서버가 GUI와 동일하게 수행한다.

기록 경로도 기존 GUI와 같다.

- 2512 결과·로그: `.tmp/test/qwen-image-2512/<생성 ID>/`
- 2511 결과·로그: `.tmp/test/qwen-image-2511-three-reference/<생성 ID>/`
- 이력: `.tmp/manager-current/qwen-2512/`, `.tmp/manager-current/qwen-2511/`

실행 결과는 해당 웹 생성기의 이력에서 조회할 수 있다. `history-reset`은 명시적으로 실행할 때만 누적 이력을 초기화한다.

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

MoMask의 OpenPose 맵 생성도 동일 명령으로 사용할 수 있다.

```bash
python3 tools/manager.py help momask openpose-map
python3 tools/manager.py command momask openpose-map GENERATION_ID
```

기존 GUI 주소·이력 경로·관리 서버 필요 여부는 유지한다.

### 단일 실행 구현

`tools/review/momask_commands.py`와 `qwen_commands.py`는 폐기했다. `execute_gateway_arguments`가 등록된 명령의 인자를 해석하고 `execute_management_command`가 로컬 서비스·HTTP 전송·GUI 서비스 어댑터를 선택한다. CLI는 상태·로그 파일을 직접 읽지 않고 명령 서비스를 통해 조회한다. 생성 완료 대기와 Ctrl+C 취소도 생성기별로 중복 구현하지 않는다.

MoMask는 기본 로컬 실행을 유지하며, 아래처럼 서버 경로를 명시하여 GUI와 같은 HTTP 게이트웨이로 실행할 수도 있다.

```bash
python3 tools/manager.py command momask --server-url http://127.0.0.1:8770 history
```

## 등록 모션 기반 캐릭터 애니메이션

관리도구의 `#character-animation`은 등록된 대기 v3(16프레임), 걷기 v8(32프레임), 스트레칭 v1(120프레임)에 캐릭터 레퍼런스를 적용한다. 방향은 전체 또는 일부를 선택한다. 현재 등록된 캐릭터는 기본 흰 셔츠 v2이며 등록 설정을 통해 확장한다. 프레임을 샘플링하지 않으며 결과 재생은 원본 에셋의 4 FPS를 따른다.

- `openpose`: 등록된 COCO18 맵과 캐릭터 이미지를 Qwen Image Edit 2511 + Lightning에 입력한다.
- `anny`: 등록된 ANNY 리그 렌더 프레임과 캐릭터 이미지를 Qwen Image Edit 2511 + AnyPose + Lightning에 입력한다. 원본 리그나 모션을 다시 생성하지 않는다.
- 모델·4스텝·시드는 공용 Qwen 포즈 실행기의 고정 설정이다. 기본·보조 프롬프트는 화면과 `catalog`에서 조회만 가능하며 실행 API에서 변경할 수 없다.
- 기본·보조 프롬프트 파일 위치와 등록 에셋은 `generators/animation/config/character_animation.yaml`에 둔다. 프롬프트 원문은 기존 정책에 따라 `.local/production-prompts/`에서 관리하며 저장소에 복제하지 않는다. 다른 환경에서는 설정의 두 UTF-8 파일을 먼저 배치한다. 파일 누락 시 명확한 오류로 중단한다.

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

`--directions` 생략 시 네 방향을 생성한다. `--detach` 생략 시 공용 CLI가 완료까지 상태를 출력한다. GUI와 로컬 CLI는 같은 작업 서비스를 호출하며 CLI는 서버 없이도 실행한다. HTTP 게이트웨이를 사용하려면 서비스 이름 뒤에 `--server-url http://127.0.0.1:8770`을 넣는다. GPU 실행은 샌드박스 밖에서 수행하고 `.model`에 준비된 모델·어댑터를 사용한다. 이미지 생성기와 공용 GPU 파일 잠금을 사용하므로 기존 작업이 끝날 때까지 대기할 수 있다.

기록은 `.tmp/test/character-animation/<YYYY-MM-DD_HH-mm-ss>/<생성 ID>/`에 저장한다. `request.json`에는 고정 프롬프트 원문·해시·단어 수, 모션·캐릭터 매니페스트 해시, 각 참조 프레임 경로·해시가 기록된다. `worker.log`, `status.json`, `progress.json`, `result.json` 및 방향별 프레임을 보관한다. 프레임별 입력은 불투명 512px PNG로 정규화하며 원본을 변경하지 않는다.

이력 인덱스는 `.tmp/test/character-animation/history/`에서 누적한다. 웹의 공용 페이지네이션·ID 복사·로그 조회·수동 초기화 기능을 사용한다. 완료된 이력의 ‘결과 보기 · 재생’에서 방향별 재생·중지·앞뒤 한 프레임 이동을 사용할 수 있다. 초기화는 이력 인덱스만 제거하며 실행 결과를 삭제하지 않는다. 웹 서버 재시작에도 독립 감독 프로세스가 생성·완료 기록을 이어간다.

프레임별 이미지 편집은 동일 레퍼런스·시드를 사용하지만 시간축 일관성을 보장하는 영상 생성 모델은 아니다. 게임 채택 전 프레임 간 외형 변화는 결과 재생으로 검수한다.
