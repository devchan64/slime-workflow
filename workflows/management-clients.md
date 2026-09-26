# 관리도구 GUI·CLI 클라이언트

화면 구성·상태·로그·이력·재생 UX 기준은 [관리도구 UI 가이드](management-ui.md)를 따른다.

구현 기준은 [AGENTS.md의 Management Client and Gateway Standard](../AGENTS.md#management-client-and-gateway-standard)에 명시한다. 이 문서는 해당 기준의 현재 구현·명령 사용법·기록 경로를 설명한다.

MoMask 작업은 `tools/review/domains/momask/momask_jobs.py` 공용 서비스가 관리한다. 웹 페이지는 GUI 클라이언트이고 `tools/manager.py`는 통합 CLI 클라이언트이다. 웹 HTTP 어댑터와 CLI 명령 어댑터는 생성·상태·이력·취소·수동 초기화에 같은 서비스를 호출한다. 통합 명령 레지스트리는 `momask`, `qwen-2512`, `qwen-2511`, `character-animation`을 제공한다. Qwen은 아래 설명처럼 웹 HTTP API를 공유한다.

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

관리도구의 `#character-animation`은 등록된 대기 v3(16프레임), 걷기 v8(32프레임), 스트레칭 v1(120프레임)에 캐릭터 레퍼런스를 적용한다. 방향은 전체 또는 일부를 선택한다. 현재 등록된 캐릭터는 기본 흰 셔츠 v2이며 등록 설정을 통해 확장한다. 타겟 FPS는 원본 FPS 이하의 양의 정수로 선택하며 기본값은 4다. 시간축에서 floor(출력 프레임 번호 × 원본 FPS / 타겟 FPS) 위치를 선택하고, 결과의 기본 재생 FPS도 타겟값으로 기록한다. 대기 16프레임·4 FPS 원본을 2 FPS로 생성하면 방향당 8장·4초가 된다. 비정수 장수는 올림하므로 길이 차이는 타겟 한 프레임 미만이다. 보간·중복 프레임 생성은 하지 않는다.

- `openpose`: 등록된 COCO18 맵과 캐릭터 이미지를 Qwen Image Edit 2511에 입력한다.
- `anny`: 등록된 ANNY 리그 렌더 프레임과 캐릭터 이미지를 Qwen Image Edit 2511 + AnyPose에 입력한다. 원본 리그나 모션을 다시 생성하지 않는다.
- 모델·시드는 공용 Qwen 포즈 실행기의 고정 설정이다. 생성 방식은 4스텝 Lightning(기본) 또는 30스텝 표준 생성이며, 30스텝에서는 Lightning 어댑터를 비활성화한다. 보조 프롬프트는 선택한 방향별로 얼굴·시선과 양발·발끝의 동일 방향, 발목과 다리의 정렬을 짧게 명시한다. 기본·보조 프롬프트는 화면과 `catalog`에서 조회만 가능하며 실행 API에서 변경할 수 없다.
- 기본·보조 프롬프트 파일 위치와 등록 에셋은 `generators/animation/config/character_animation.yaml`에 둔다. 프롬프트 원문은 기존 정책에 따라 `.local/production-prompts/`에서 관리하며 저장소에 복제하지 않는다. 다른 환경에서는 설정의 기본·전방 보조·후방 보조 UTF-8 파일을 먼저 배치한다. 파일 누락 시 명확한 오류로 중단한다.

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

캐릭터 애니메이션 화면의 **원본 모션 에셋 검수**에서 생성 전에 선택한 모션을 확인한다. OpenPose와 ANNY 리그 렌더가 같은 프레임으로 나란히 재생된다. 검수 방향은 생성 방향 선택과 독립적이며 네 방향 모두 조회 가능하다. 4 FPS 반복 재생·중지·이전/다음 프레임·슬라이더를 제공한다. 원본 프레임 조회 시 매니페스트 해시와 프레임 범위를 검증하며 생성 작업이나 이력을 만들지 않는다. 브라우저는 다음 프레임을 미리 읽고 캐시 개수를 제한한다.

원본 에셋과 생성 결과 플레이어는 각각 **재생 속도**에서 4·8·12·16 FPS를 선택할 수 있다. 기본은 4 FPS이며 재생 중에도 변경된다. 이는 검수용 재생 속도로, 원본 프레임 수·생성 설정·결과 메타데이터의 FPS는 바꾸지 않는다.

`character-animation generate --target-fps 2`로 CLI에서도 지정한다. 요청에는 `target_fps`, `source_fps`, `selected_frame_numbers`와 프롬프트 출처를 기록한다. 결과에는 타겟 `fps`와 원본 프레임 번호를 기록한다. 기존 간격 방식 이력은 수정하지 않으며 기존 API의 명시적 `frame_step` 요청은 호환 처리한다. 두 방식의 동시 지정은 거절한다. 원본 검수 플레이어는 항상 전체 원본 프레임을 사용한다.

캐릭터 애니메이션 CLI의 `--steps 4` / `--steps 30`은 웹의 생성 방식 선택과 같다. 예: `python3 tools/manager.py command character-animation generate --motion standing-v3 --character character-default --source anny --steps 30 --detach`. 실행 요청·결과·이력에 선택 스텝을 보존한다. 기존 이력의 스텝 필드가 없으면 기존 방식인 4스텝으로 표시한다.

보조 프롬프트는 `auxiliary`(전방)와 `auxiliary_rear`(후방)의 로컬 파일로 분리한다. 기본 프롬프트는 공통으로 유지한다. 후방은 뒷머리의 머리카락·등·양쪽 발뒤꿈치가 보이도록 명시한다. 방향 앵커는 `back-left`·`back-right`를 사용하고 머리·몸통·발이 같은 방향을 유지하도록 지시한다. 실제 선택한 보조 문구만 기본 프롬프트와 결합하고 화면 단어 수·실행 해시에 반영한다.


## 타일맵 생성기

관리도구 `#tile-map-generator`에서 지붕(`rooftop`)·벽(`wall`)·문(`door`)·맵 바닥(`ground`)을 선택한다. `generators/terrain/config/tile_map.yaml`의 기본·화풍 프롬프트는 고정이며 사용자 지시만 편집한다. 서버에서 세 문구를 결합하고 원문·단어 수·SHA-256을 기록한다. 최종 입력은 100단어 미만이며 정사각형 해상도만 지원한다. 생성 이미지는 검수 후보이고, 무봉제 품질이나 게임 에셋 채택을 자동 보장하지 않는다.

Qwen 2512의 공용 작업자·GPU 잠금·준비·취소·진행 조회를 사용한다. 실행 폴더는 `.tmp/test/qwen-image-2512/tile-map/<생성 ID>/`, 누적 이력은 기존 공용 이력 루트의 `tile-map/`이다. 목록 초기화는 수동이며 결과 파일을 삭제하지 않는다. 같은 스텝·크기의 완료 이력이 있을 때만 예상 시간을 표시한다.

```sh
python3 tools/manager.py help tile-map
python3 tools/manager.py command tile-map catalog
python3 tools/manager.py command tile-map generate --tile-type wall --prompt 'Warm stone facade with a wooden window.' --width 512 --height 512 --steps 4 --detach
python3 tools/manager.py command tile-map history
```

GUI와 CLI는 같은 `tile-map` 게이트웨이 서비스와 기록을 사용한다. CLI도 실행 중인 관리 서버가 필요하다. 생성 종류별 별도 추론 실행기는 만들지 않는다.

캐릭터 생성 배속은 `--speed 1|1.5|2|4`로 지정한다. 기본은 1이며 `--target-fps 4 --speed 2`는 동일 FPS에서 원본의 절반 길이를 생성한다. 배속은 요청·결과·이력에 `speed`로 기록한다. 원본 모션 검수 재생에는 적용하지 않는다.

## 스프라이트 정규화 편집기

관리 메뉴 `#sprite-editor`에서 프론트 등록 애니메이션 또는 완료된 캐릭터 애니메이션 결과 ID 하나를 불러온다. 프론트 원본은 검수 빌드가 만든 `sprite-assets.json`과 이미지 사본을 사용한다. 여러 결과 병합은 지원하지 않는다.

중심·바닥·머리 가이드와 기준점, 배치·배율을 프레임별로 편집하고 현재 방향 또는 원본 전체에 적용한다. 이전 프레임 겹침과 머리 연결선으로 정렬을 확인한다. 생성 결과의 초기 가이드는 자동 검출값이 아니므로 사용자가 지정해야 한다.

`프로젝트 저장`은 `.local/sprite-editor/<원본 ID 해시>/`에 버전별 JSON을 누적하고 재진입 시 최신 편집을 복원한다. 원본 버전이 바뀌면 기존 저장 파일을 보존하고 새 편집으로 연다. PNG는 현재 방향을 512×512 셀로 내보내며 원본 배경·투명도를 유지한다. 정규화 JSON에는 원본 프레임과 변환값이 포함된다. 프론트 원본은 덮어쓰지 않는다.

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

MoMask 화면의 `얼굴 포인트 ON`을 선택해 새 모션을 생성하거나, 완료된 이력에서 `OpenPose 맵 생성`을 실행한다. 기존 신체맵에 ANNY 공식 COCO 회귀점(코·양눈·양귀)을 같은 카메라로 투영하며 표면에 가려진 점은 제외한다. 68점 얼굴 윤곽·표정 검출 기능은 아니다. OFF는 기존 신체 전용 맵을 생성한다. 결과 캡션과 `result.json`의 `openpose_face_enabled`에 실제 적용값을 기록한다.

CLI는 `momask generate ... --face` 또는 `momask openpose-map <ID> --face`를 사용한다. `--no-face`는 얼굴을 제외한다. 기존 이력의 얼굴맵 생성에는 `result/anny/mannequin.blend`와 투영 기록이 필요하다. 정점 수가 공식 회귀 데이터와 다르면 오류로 중단한다. 얼굴 회귀 데이터는 NAVER ANNY의 Apache-2.0 데이터에서 현재 ANNY 토폴로지의 정점 순서로 추출했으며 원본 해시를 함께 보관한다.

### 타일 생성 참조 입력

타일 생성기는 선택한 PNG 최대 3장을 순서대로 전달한다. 기존 3참조 검증·입력 저장·Qwen 2511 실행기를 공유하며 512×512 RGB/RGBA 불투명 PNG, 장당 3MB 제한을 적용한다. 참조가 없으면 기존 Qwen 2512를 사용한다. 기본·사용자·화풍 프롬프트를 서버에서 결합하며 참조와 타일 설정은 같은 실행 이력에 저장한다. CLI는 `tile-map generate ... --reference first.png --reference second.png --reference third.png`로 같은 경로를 사용한다.

타일 생성기의 수동 초기화는 예외적으로 `.tmp/test/qwen-image-2512/tile-map/<실행 ID>/`의 참조·결과·로그 파일과 이력 인덱스를 함께 삭제한다. 확인창에서 삭제 범위를 안내하며 생성 중에는 거절한다. 정식 에셋 사본은 삭제하지 않는다. 다른 생성기의 이력 초기화 정책은 유지한다.

타일의 기본·화풍 프롬프트는 각각 ON/OFF할 수 있으며 기본값은 둘 다 ON이다. 원문은 읽기 전용이며 최종 단어 수와 해시는 활성 항목과 사용자 프롬프트를 결합한 실제 입력 기준이다. 이력에는 `use_base_prompt`, `use_style_prompt`를 저장한다. CLI에서는 `--no-use-base-prompt`, `--no-use-style-prompt`로 제외한다. 모든 프롬프트가 비면 요청을 거절한다.

캐릭터 애니메이션 출력 해상도는 GUI 또는 CLI의 `--resolution 512|768|1024|1280`으로 선택한다. 기본값은 테스트용 512×512이며 참조 입력은 512px 정규화를 유지한다. 선택 해상도는 요청·결과에 보존하며 재개 시 같은 설정을 사용한다. 생성이력의 입력 내용에서 해상도, FPS, 배속, 스텝, 선택 프레임, 참조 경로·매니페스트 해시와 방향별 실제 프롬프트·단어 수를 확인한다.

### Gradio MoMask UI

MoMask 페이지는 Gradio Blocks로 전환한다. `/momask-generator/`는 관리 서버 포트 + 100의 로컬 Gradio UI로 연결한다(기본 8870). 외부 공개 없이 `127.0.0.1`에 바인딩하고 관리 서버 종료 시 UI 프로세스도 종료한다. 생성 작업은 기존 독립 감독 프로세스에서 계속 실행한다. CLI·HTTP API·기록 경로는 유지한다.

관리 UI 의존성은 모델 환경과 분리한다. 최초 설치는 `python3 -m venv .venv-management` 이후 `.venv-management/bin/pip install -r tools/review/ui/gradio/requirements.lock`으로 수행한다. 실행 로그는 `.tmp/manager-current/gradio.log`에 기록한다. 현재 전환 범위는 MoMask이며 다른 생성기는 기존 UI를 유지한다.

설정·보정값·로그·페이지별 이력·수동 초기화는 Gradio에서 구성한다. 결과 ID 또는 이력 라디오 선택 후 ‘결과 보기’로 HumanML3D·ANNY·OpenPose 동기 재생기를 연다. 재생은 브라우저에서 실행하며 Python 프레임별 호출을 하지 않는다. 아직 기존 공용 이력 UI의 썸네일과 파일 관리자 열기 기능은 이 전환 페이지에 이식되지 않았다.

Gradio 이력은 페이지당 8건의 단일 선택 목록으로 표시하며 선택 후 결과 조회 버튼으로 연다. 공용 로그 패널은 `tools/review/common/gradio_logs.py`를 사용한다. 전체 너비의 접이식 패널에 작업 ID·최근 로그·복사·자동 갱신·최신 줄 따라가기·마지막 줄 이동을 제공한다. 자동 갱신을 끄면 표시 내용을 유지하며 작업 실행은 계속된다.

MoMask Gradio 화면은 좌측의 ‘새 모션 생성’·‘생성이력 · 결과 조회’ 탭과 우측 결과 재생 영역으로 구성한다. ID 직접 조회·결과 상세는 접이식으로 제공하고, 실행 로그는 두 열 아래 전체 너비로 배치한다. 화면 폭이 좁으면 한 열로 전환한다. 배치는 `tools/review/ui/gradio/management-layout.css`에서 관리한다.

### MoMask 렌더 재개

Gradio 생성이력에서 취소·실패 이력을 선택하고 ‘생성 재개’을 누르거나 `python3 tools/manager.py command momask resume <ID>`를 실행한다. 현재 재개 범위는 모션 추론과 ANNY 리그 저장이 완료된 이후의 렌더 단계다. 저장된 리그·렌더 스크립트·카메라를 유지하며 정상 PNG를 검증해 재사용하고 미완료 프레임을 렌더한다. 같은 ID·폴더·로그를 유지하며 마지막에 OpenPose 맵을 생성한다. 리그 이전 단계의 중단은 누락 산출물을 안내하고 거절한다. 이력 초기화로 숨겨진 항목은 자동 복원하지 않는다.
