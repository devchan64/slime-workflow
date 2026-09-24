# 관리도구 GUI·CLI 클라이언트

MoMask 작업은 `tools/review/momask_jobs.py` 공용 서비스가 관리한다. 웹 페이지는 GUI 클라이언트이고 `tools/manager.py`는 통합 CLI 클라이언트이다. 웹 HTTP 어댑터와 CLI 명령 어댑터는 생성·상태·이력·취소·수동 초기화에 같은 서비스를 호출한다. 통합 명령 레지스트리는 `momask`, `qwen-2512`, `qwen-2511`을 제공한다. Qwen은 아래 설명처럼 웹 HTTP API를 공유한다.

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
