# Hermes 로컬 코딩 에이전트

Hermes는 관리도구의 현재 추적 파일과 Git에서 무시하지 않는 새 파일을 격리 작업 공간에 복사해 작업한다. GUI, 통합 CLI, MCP는 공용 관리 게이트웨이와 같은 작업 기록을 사용한다. 격리된 터미널과 파일 읽기·검색·패치 도구를 제공하며 한 작업의 도구 호출은 최대 20회다. 작업 결과는 검토용 diff이며 원본에 자동 적용하지 않는다.

## 구성과 준비

- **모델:** Qwen3.8-27B IQ4_XS. 모델 관리의 Hermes 코딩 모델에서 다운로드하며 파일 SHA-256은 실행 직전에 다시 확인한다. 고정 출처와 해시는 [모델 준비 구현](../../tools/review/common/hermes_model_download.py)을 따른다.
- **Hermes:** 공식 `v0.23.1`, Git 리비전 `3b421578588243f920886e6fe79a6faa87ea026e`. Git 제외 경로 `.local/hermes-agent-runtime/`에 준비한다. `prepared-local.json`, Git HEAD, 추적 파일 변경과 무시되지 않은 신규 파일을 실행 직전에 검사한다. 이 검사는 `.venv/`의 모든 패키지 파일 해시를 검증하는 기능은 아니다.
- **추론 서버:** 작가 AI가 준비한 ROCm `llama-server` 바이너리와 준비 manifest를 읽고 바이너리 SHA-256을 확인한다. 모델 프로세스는 Hermes 전용이며 작가 AI 서버의 실행 상태를 변경하지 않는다.
- **GPU 프로세스 정리:** PID 재사용에 안전한 프로세스 그룹 종료를 위해 Linux 6.9 이상의 `pidfd_send_signal` 그룹 신호 지원이 필요하다. 지원되지 않으면 GPU 사용 전에 작업을 실패 처리한다.
- **MCP 실행환경:** Python 3.14 전용 별도 환경에 버전 고정 의존성을 설치한다. 아래 명령은 해당 경로에 새 환경을 준비할 때 사용한다.

```bash
python3 -m venv .local/hermes-mcp
.local/hermes-mcp/bin/pip install -r generators/hermes_agent/requirements-mcp.lock
```

Hermes 소스 환경은 현재 수동 준비 단계다. 저장소 루트에서 다음 명령으로 [공식 소스](https://github.com/NousResearch/hermes-agent)의 고정 리비전과 잠금 의존성을 준비할 수 있다. 기존 디렉터리는 덮어쓰지 않는다. 준비가 중간에 실패하면 남은 디렉터리와 로그를 확인한 뒤 처리하며, 다른 사용자의 파일을 자동 삭제하지 않는다.

```bash
if [ -e .local/hermes-agent-runtime ]; then
  printf '기존 Hermes 실행 디렉터리가 있어 준비를 중단합니다.\n'
else
  git clone --no-checkout https://github.com/NousResearch/hermes-agent .local/hermes-agent-runtime &&
  git -C .local/hermes-agent-runtime checkout --detach 3b421578588243f920886e6fe79a6faa87ea026e &&
  (cd .local/hermes-agent-runtime && ../../.venv/bin/uv sync --locked --no-dev) &&
  python3 -c 'import json; from pathlib import Path; Path(".local/hermes-agent-runtime/prepared-local.json").write_text(json.dumps({"revision":"3b421578588243f920886e6fe79a6faa87ea026e","release":"v0.23.1","source":"https://github.com/NousResearch/hermes-agent"}) + "\n")'
fi
```

모델 다운로드만으로 Hermes·ROCm 서버가 준비되는 것은 아니다. 추론 서버 준비는 [작가 AI 실행 안내](../../workflows/writer-agent.md)를 참고한다.

## 실행과 결과

관리 메뉴의 **텍스트 기반 → Hermes 코딩 에이전트**에서 지시와 GPU 대기열 확인을 거쳐 접수한다. 동일한 접수 식별자와 지시는 재시도해도 기존 ID를 돌려주며, 다른 지시에 같은 식별자를 재사용할 수 없다. 응답이 유실되면 새 식별자를 만들기 전에 같은 식별자로 조회 또는 재접수해 결과를 확인한다. 작업 상태는 `queued`, `running`, `completed`, `failed`, `cancelled`이며 접수 중 비정상 종료로 상태가 없으면 `unknown`으로 표시하고 자동 재실행하지 않는다.

선택적으로 공용 회귀 실행기에 등록된 모듈을 최대 5개 지정할 수 있다. Hermes가 최종 수정을 마친 후 추론 서버를 내리고, 같은 격리 사본에서 지정 모듈을 별도 실행한다. 공용 회귀 실행기 파일이 작업 중 변경되면 독립 검증을 거부한다. 테스트 코드 자체는 작업 사본을 사용하므로 검증 통과와 함께 변경 diff도 검토해야 한다. 독립 검증 실패 또는 시간 초과는 에이전트 자체가 성공했더라도 작업 실패로 기록한다. 검증을 지정하지 않은 경우에는 자동으로 테스트를 실행하지 않는다. GPU 예약은 독립 검증이 끝날 때까지 유지하는 보수적 정책이다.

사용할 수 있는 모듈 이름은 `.venv/bin/python tools/review/tests/run_management_audit.py --help`에서 확인한다. 예를 들어 `tools.review.tests.test_hermes_service`를 지정하면 그 모듈만 독립 실행한다.

공용 GPU 대기열은 Hermes의 초기 예약을 32,768 MiB로 잡고 다른 대기열 작업과 배타적으로 실행한다. 이미 실행 중인 작업은 선점하지 않는다. GPU 메모리 부족 시 대기하며 이미지 생성기를 CPU로 대체하지 않는다. 취소는 요청과 실제 종료를 구분한다. Hermes 프로세스 그룹을 정리한 후 예약을 해제하며 가능한 부분 diff와 로그를 보존한다. 대기열 실행기가 비정상 종료되면 다음 대기 작업이 시작 시각과 작업별 식별값이 일치하는 프로세스 그룹을 PID 핸들로 정리하고 기존 작업을 실패로 표시한다. 식별값이 없거나 일치 여부를 확인할 수 없는 예약은 안전하게 대기하므로 운영자가 실제 프로세스를 확인해 복구해야 한다.

격리 공간에는 일반 파일만 복사하고 심볼릭 링크와 2 GiB 초과 복사는 거부한다. Git에서 무시된 파일은 복사하지 않는다. 다만 관리도구의 `.venv`는 격리 작업에서 공용 회귀 실행기를 사용할 수 있도록 읽기 전용으로 연결한다. 이 환경이 없거나 심볼릭 링크라면 작업을 실행하지 않는다. 격리 `/tmp`는 최대 2 GiB의 메모리 파일 시스템이며 이 한도는 프로세스 전체 메모리 사용량에 적용되지 않는다. 외부 네트워크, 호스트 홈, 호스트 `/run`은 보이지 않으며 추론 서버만 전용 로컬 소켓으로 연결한다. 격리 공간에 GPU 장치를 노출하지 않으므로 실제 GPU 생성기 검사는 Hermes 종료 후 공용 대기열에서 별도로 수행한다. `.git`도 읽기 전용이다. 모델 응답과 도구 출력은 작업 로그에 기록되므로 로컬 작업 기록도 비공개로 취급한다. 컨테이너나 VM 수준의 보안 경계를 주장하는 것은 아니다.

Hermes 샌드박스와 독립 검증 프로세스는 호스트 환경변수를 물려받지 않고 필요한 최소 환경만 사용한다. 초기 시험에서는 이 차단이 보장되지 않았다. 시험 로그의 도구 호출에서 명시적인 환경변수 조회 명령은 발견하지 못했으나, 이것만으로 과거 노출이 없었다고 증명할 수는 없다.

상세 화면과 MCP 응답은 상태·변경 diff·도구 출력·최종 답변을 제공한다. diff가 500,000바이트를 넘으면 표시가 잘리며 `diff_truncated`가 참이 된다. 전체 파일은 작업 기록의 `change.diff`에 있고 MCP의 `read_hermes_task_diff`로도 바이트 조각을 읽을 수 있다. 각 조각을 base64에서 디코딩하고 `next_offset`이 `null`이 될 때까지 바이트를 이어 붙인다. 미커밋 변경도 복사한 시점이 기준이므로 diff를 원본에 적용하기 전 기준과 충돌을 직접 확인한다.

## Codex MCP 연결

[Codex MCP 안내](https://developers.openai.com/codex/mcp)의 로컬 stdio 구성을 사용한다. 서버는 `.local/hermes-mcp/bin/python`으로 `tools/review/domains/hermes_agent/mcp_server.py`를 실행한다. 저장소 루트에서 실행하면 다음 명령이 현재 경로를 절대 경로로 등록한다. 이미 같은 이름이 등록되어 있으면 기존 설정을 먼저 확인한다.

```bash
codex mcp add slime-hermes -- "$PWD/.local/hermes-mcp/bin/python" "$PWD/tools/review/domains/hermes_agent/mcp_server.py"
codex mcp get slime-hermes
```

접수·취소에는 Codex의 승인 정책이 적용될 수 있다. 설정 변경을 기존 대화에서 바로 사용할 수 있는지는 클라이언트 세션에 따라 확인한다.

도구는 `submit_hermes_coding_task`, `read_hermes_coding_task`, `list_hermes_coding_tasks`, `read_hermes_task_diff`, `cancel_hermes_coding_task`다. 접수에는 `request_identifier_value`와 `coding_prompt_text`가 필요하며, `verification_module_names`로 선택 검증 모듈을 전달할 수 있다. 같은 접수 식별자로 재시도할 때는 지시와 검증 모듈을 모두 동일하게 유지한다. 조회·취소는 `job_identifier_value`를 사용한다. diff 조회의 `byte_offset_value`와 `byte_limit_value` 기본값은 각각 0과 65,536이며 최대 조각 크기는 262,144바이트다. MCP 서버는 기본적으로 `http://127.0.0.1:8771`의 `/management/command`에만 연결하며, `SLIME_MANAGEMENT_GATEWAY_URL`로 지정하는 주소도 localhost HTTP로 제한한다.

공용 게이트웨이가 이전 코드로 이미 실행 중이면 새 명령이 `400`으로 거절될 수 있다. 작가 작업을 포함한 현재 상태를 확인한 뒤 정식 실행 스크립트의 재시작 절차를 사용한다. 접수 중인 요청이나 별도 GPU 작업의 상태를 확인하지 않은 채 기존 프로세스를 강제 종료하지 않는다. 게이트웨이 재시작과 작업 재접수는 별개다.

## 검증 범위

이 장비에서 64,000 문맥, 전체 66개 레이어 GPU 적재, 단일 함수 결함 수정, 격리 작업의 diff 회수, GPU 적재 중 취소와 실행기 강제 종료 후 예약 복구를 시험했다. 별도 시험 게이트웨이에서는 실제 Codex가 MCP로 코딩 작업을 접수했고 Hermes가 작성한 테스트 2개를 독립된 격리 환경에서 통과시켰다. MCP 중복 접수 방지도 별도 시험했다. 관측 메모리 피크 약 17.9 GiB는 해당 시험의 값이며 모든 작업의 최대치가 아니다. 재시작한 운영 게이트웨이에서 MCP 작업 접수와 브라우저 이력·완료 상태·diff 조회를 확인했다.

최신 단순 파일 작성 시험에서는 실행은 완료됐지만 지정된 텍스트 끝에 줄바꿈을 추가해 정확한 바이트 비교에 실패했다. 에이전트의 완료 응답과 검사 통과를 구분하고 생성된 diff와 독립 검사 결과를 검토해야 한다.

터미널만 제공한 후속 시험에서는 테스트 추가를 마치기 전에 12회 도구 호출 한도에 도달했다. 이후 파일 패치 도구를 추가하고 한도를 20회로 조정했으며, 이 변경의 실제 과제 성능은 별도 시험 결과로 판단한다.

별도의 Codex 위임 시험에서 Hermes는 기존 서비스 테스트에 잘못된 요청 ID 검사를 추가하고 공용 회귀 실행기를 한 차례 사용했다. 첫 검사 뒤 테스트를 다시 수정했지만 최종 수정 후 직접 재실행하지 않았다. 최종 diff는 독립된 격리 환경의 공용 실행기로 확인해 6개 검사가 통과했다. 이 시험의 GPU 메모리 관측 피크는 17,923 MiB였고 모델 로딩을 포함한 실행 시간은 약 9분 15초였다. 같은 모델의 모든 작업 속도를 대표하지는 않는다.

2026-11-17 추가 시험에서는 실제 Codex가 MCP를 통해 요청을 접수하고 Hermes가 격리 사본의 잘못된 요청 ID 검사를 추가했다. 작업 후 지정한 공용 회귀 모듈의 자동 독립 검증 7개가 모두 통과했으며, 관측 GPU 메모리 피크는 17,924 MiB였다. 같은 날 최신 pidfd 방식으로 GPU 적재 중 취소했을 때 작업 상태와 부분 결과를 보존하고 GPU 예약을 해제하는 것도 확인했다. 이 결과는 별도 시험 게이트웨이에서 얻었으며 기존 운영 게이트웨이의 적용 검증을 대신하지 않는다.

운영 게이트웨이 재시작 후 Codex MCP로 격리 코딩 작업을 접수해 요청 ID 거부 검사를 추가했고, 관리 화면에서 같은 작업의 완료 상태와 diff를 확인했다. 이 작업은 자동 검증을 지정하지 않아 별도로 격리 공용 회귀 실행기를 실행했으며 7개 검사가 통과했다. 모델이 직접 실행한 동일 모듈 검사도 통과했다. 변경은 격리 사본에만 존재한다.
