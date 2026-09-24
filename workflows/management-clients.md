# 관리도구 GUI·CLI 클라이언트

MoMask 작업은 `tools/review/momask_jobs.py` 공용 서비스가 관리한다. 웹 페이지는 GUI 클라이언트이고 `tools/manager.py`는 통합 CLI 클라이언트이다. 웹 HTTP 어댑터와 CLI 명령 어댑터는 생성·상태·이력·취소·수동 초기화에 같은 서비스를 호출한다. 현재 통합 명령 레지스트리에 등록된 서비스는 `momask`이다.

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
