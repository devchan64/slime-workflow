# 로컬 작가 AI 에이전트 실행

관리도구의 `#writer-agent` 메뉴 또는 `/writer-agent/`에서 실행한다. 모델은 Qwen3.5-4B Q4_K_M, 임베딩은 Qwen3-Embedding-0.6B Q8_0로 코드에 고정한다. 모델 변경 요청은 API 입력으로 받지 않는다. Linux NVIDIA CUDA GPU가 필요하며 CPU 추론은 지원하지 않는다. 환경 준비와 추론은 샌드박스 밖에서 실행한다.

## 작업 공간 연결

문서·상태 루트는 운영자가 명시적으로 연결하는 입력이며 특정 비공개 저장소 소스에 의존하지 않는다. 설정은 `.local/writer-agent/workspace.yaml`에 저장하고 Git에 추가하지 않는다. 비공개 원문·색인·검색 결과·사용자 프롬프트·변경 제안·실행 기록은 비공개 문서 저장소에 둔다.

```bash
python3 -m generators.writer_agent.cli configure \
  --document-root /absolute/private/documents \
  --state-root /absolute/private/documents/.writer-agent \
  --write-root world --write-root ideas \
  --protect-path world/decisions --exclude-root history
python3 tools/review/serve.py --watch
```

연결 설정은 `schema_version: 1`, `document_root`, `state_root`, `write_roots`, `excluded_roots`, `protected_paths`, `catalog_path`만 허용한다. 경로는 숨김·상위 이동·심볼릭 링크를 거부한다. `catalog_path`의 기본값은 null이며 `--catalog-path CATALOG.md`로 기존 전체 목록을 연결할 수 있다. 연결할 목록은 루트의 Markdown 문서이며 `## 그룹 (개수)`와 `| 문서 | 경로 |` 표, 상대 파일 링크·백틱 경로 열 형식이어야 한다. 신규 문서를 추가할 그룹이 미리 있어야 한다. 목록 갱신도 변경 미리보기에 포함된다.

## 화면의 실행 순서

1. **환경 준비**: 해시가 고정된 모델·CUDA 라이브러리·llama.cpp를 준비한다. `.model/writer-agent`에는 모델만, `.local/writer-agent`에는 실행 환경을 둔다. 최초 준비는 다운로드·컴파일 시간이 필요하다.
2. **학습 · 색인 갱신**: Markdown·YAML 문단, 경로·제목·원문 해시·문서 간 참조와 벡터를 SQLite에 저장한다. 이는 파인튜닝이 아니다. 변경 없는 문단의 벡터는 재사용한다.
3. 프롬프트를 입력하고 **관련 문서 탐색 · 작성 제안**을 누른다. 벡터·키워드 혼합 검색 후 인접 문단·연결 문서·폴더 안내를 참고하여 기존 문서의 새 절 또는 기존 폴더 안의 신규 문서를 제안한다. 모델이 근거 부족을 판단하면 보류한다.
4. **중복 검토**는 입력이 비어 있으면 전체 색인, 입력이 있으면 검색 상위 80개 청크와 연결된 후보를 조사한다. 완전 일치 또는 유사도·단어 중첩으로 후보를 고르고 한 실행에서 상위 12쌍을 모델로 비교한다. 제한 여부와 후보 수를 표시한다.
5. 근거·위치·diff를 확인한 뒤 **확인한 변경을 원본에 적용**한다. 적용 후에는 학습을 갱신한다. 문서나 참조가 제안 이후 바뀌면 적용을 거부한다.

모델은 대상 경로·제목·문단 배열을 반환하고 코드가 파일 존재 여부로 추가·생성을 결정한다. 제목 기호·문단 간격은 코드에서 일관되게 조립한다. 원본 문단 순서를 재편하거나 덮어쓰지 않고 새 절을 뒤에 추가한다. 신규 내용에는 제안 표기를 붙이며 승인 상태로 자동 승격하지 않는다. 기본적으로 README·CATALOG·MANAGEMENT·SUMMARY와 보호 경로는 쓰기 대상에서 제외한다. 목록 갱신은 모델 출력이 아닌 검증된 코드가 만든 변경만 허용한다.

중복 삭제 방향은 읽기 전용·원본 소유 표시, 들어오는 문서 참조 수, 제목·문단 주제 적합도로 정한다. 서로 다른 문서의 점수가 같으면 자동 삭제하지 않는다. 같은 문서에서는 앞선 문단을 남긴다. 고유 사실·예외·수치·서사 맥락을 잃지 않는다고 모델이 0.95 이상으로 판단한 일반 산문만 제안한다. 제목·목록·표·코드·링크·확정/승인 문단은 자동 삭제 후보에서 제외한다. 모델의 confidence는 보정된 정확도 확률이 아니다. 이 점수는 문서 정책을 대신하는 권한 판정이 아니므로 사용자 검토가 필요하다.

## 기록과 복구

`state_root/rag.sqlite3`가 검색 색인이다. `state_root/jobs/작업ID/`에는 request/status/search/context/model-result/proposal/application YAML과 execution/worker/model-server 로그를 저장한다. 준비 작업은 준비·컴파일 로그를 저장한다. 화면에서 최근 40개 작업을 조회하며 개별 API 또는 CLI의 ID 조회로 이전 작업도 볼 수 있다.

```bash
.local/writer-agent/venv/bin/python -m generators.writer_agent.cli learn
.local/writer-agent/venv/bin/python -m generators.writer_agent.cli write --prompt '작성 지시'
.local/writer-agent/venv/bin/python -m generators.writer_agent.cli deduplicate --prompt '정리할 주제'
python3 -m generators.writer_agent.cli show --job-id YYYYMMDD-HHMMSS-xxxxxxxx
```

작업은 4초 간격으로 진행 로그를 남긴다. 동시 작업은 상태·GPU 잠금으로 차단한다. 관리 서버 종료 시 실행 중인 자식 프로세스도 종료한다. 실행 중 문서가 바뀌면 실패하며 이전 색인을 유지한다. 부분 적용의 처리 중 예외는 이미 쓴 파일을 원복하되, 외부 편집이 감지된 파일은 덮어쓰지 않고 충돌을 기록한다. 전원 중단 등으로 application 상태가 `applying` 또는 `rollback_conflict`이면 재적용하지 말고 proposal의 before/after 및 해시와 실제 파일을 비교해 복구한다.

로컬 서버는 127.0.0.1에만 바인딩하며 쓰기 API는 동일 Origin과 세션 토큰을 검사한다. AWS 배포·API·DB 스키마를 변경하지 않으며 외부 유료 API를 호출하지 않는다. GPU는 작업 동안만 적재하고 종료 시 해제한다.

## 검증

```bash
python3 -m unittest discover -s generators/writer_agent/tests -v
python3 -m unittest discover -s tools/review/tests
node tools/review/tests/frame_manager_ui.test.mjs
node generators/writer_agent/tests/manager_ui.test.mjs
```
