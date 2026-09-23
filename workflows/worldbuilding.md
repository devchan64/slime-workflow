# 로컬 문서 작성·수정 관리도구

## 현재 제공하는 기능

관리 화면에서 자연어 업무 지시를 입력하면 기존 문서의 관련 구간을 찾아 고정 Qwen 모델로 Markdown을 생성·추가·교체한다. 출처와 원본 해시를 작업마다 보존하고, 검증을 통과한 결과를 지정한 문서 루트에 반영한다. 새로운 설정은 제안으로 표시한다.

실행 코드는 `generators/worldbuilding/`, 화면 연결은 `tools/review/serve.py`가 담당한다. 게임 고유 설정·지시·생성 기록은 공개 저장소에 보관하지 않는다. Hermes 설치를 필수로 요구하지 않는 제한된 문서 실행기다. 범용 shell 에이전트·클라우드 API는 사용하지 않는다. 임베딩은 고정 로컬 GPU 모델로 실행한다.

## 실행

현재 연결된 작업 공간에서 다음 명령을 실행한다. **GPU 호스트에서, 샌드박스 밖에서 실행한다.**

```bash
python3 tools/review/serve.py --worldbuilding-only
```

관리 화면: `http://127.0.0.1:8770/worldbuilding/`

일반 관리도구를 실행할 때도 설정 파일이 있으면 상단의 **세계관 작업** 링크로 접근한다. `--worldbuilding-only`는 에셋 검수 빌드를 하지 않는 명시적 실행 모드다. 기존 에셋 형식 오류가 있으면 일반 검수 시작은 그대로 실패한다.

1. **환경 준비 · 모델 다운로드**: 전용 환경·CUDA 도구·llama.cpp 서버·고정 GGUF를 준비한다. 진행 로그를 화면에서 확인한다.
2. **업무 지시**: 기존 설정을 참고해 어떤 문서를 작성할지 입력한다.
3. **작업 종류**: 새 문서 / 기존 문서에 추가 / 특정 구간 교체를 선택한다. 대상 경로는 생략할 수 있다. 생략하면 관련 원문을 읽어 대상을 찾고, 지정하면 해당 경로를 고정한다.
4. **작업 실행**: 대기함에 저장한 뒤 한 작업씩 실행한다. 환경 미준비 시 대기하며 자동으로 다른 모델을 쓰지 않는다.
5. **작업 내역**: 문서를 찾은 과정, 찾은 수정 대상, 참조 문서, 변경 전후, 경고·오류를 확인한다. **이 작업 되돌리기**는 이후 외부 수정이 없는 경우만 수행한다.

**세계관 문서 학습·갱신** 버튼으로 RAG 색인만 갱신할 수도 있다. 이 작업은 문서 원문이나 모델 가중치를 바꾸지 않는다. 일반 업무 실행 전에도 변경된 문서를 자동 색인한다.

페이지를 닫아도 서버가 살아 있으면 대기함을 처리한다. 서버 종료 시 실행 중 작업을 중단한다. 재시작 시 남은 대기 작업은 이어 처리하고 중단된 작업은 실패로 표시한다. 무한 자율 생성이나 시간 예약은 없다. 사용자가 새 지시를 추가할 때마다 최신 원본을 읽는다.

## 처음 설치하거나 다른 문서 루트를 연결할 때

지원 대상은 Linux x86_64, NVIDIA GPU, 동작하는 드라이버와 `nvidia-smi`, Python 3.12 이상, `uv`, `g++`다. GPU 메모리 8GB에서 검증했다. 관리도구 호스트 Python에는 기존 PyYAML과 jsonschema가 필요하며, 아래 준비 후 전용 Python으로 관리 서버를 시작할 수도 있다. 전용 모드는 Pillow를 요구하지 않는다.

```bash
python3 generators/worldbuilding/worldbuilding.py prepare
python3 generators/worldbuilding/worldbuilding.py configure \
  --document-root /absolute/private-docs \
  --state-root /absolute/private-docs/workflow/.worldbuilding \
  --write-root world \
  --required-source MANAGEMENT.md \
  --required-source world/README.md \
  --required-source world/APPROVAL.md \
  --protected-document MANAGEMENT.md \
  --protected-document world/APPROVAL.md \
  --protected-document CATALOG.md \
  --catalog CATALOG.md
.local/worldbuilding/venv/bin/python tools/review/serve.py --worldbuilding-only
```

경로는 예시이며 실제 존재하는 소유 문서 경로를 지정한다. `configure`는 기존 설정을 덮어쓰지 않는다. 다른 설정 파일은 `--worldbuilding-config /absolute/workspace.yaml`로 관리 서버에 전달한다. 설정 변경 후 서버를 재시작한다. 상태 폴더는 비공개 소유 저장소의 Git 제외 대상으로 관리한다.

## 고정 실행 구성

| 항목 | 값 |
|---|---|
| 원 모델 | Qwen/Qwen3.5-4B |
| GGUF 공급자 | bartowski/Qwen_Qwen3.5-4B-GGUF |
| GGUF | Q4_K_M, 3,013,027,808바이트 |
| 모델 revision | 4168f45a16a1290d65a4ec0fa312ae917a4c15d6 |
| 모델 SHA-256 | 13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983 |
| llama.cpp | b10964, 0.4.1 계열 |
| CUDA 빌드 | 전용 Python 환경의 NVIDIA CUDA 13.2 구성 요소, 호스트 GPU 아키텍처 대상 빌드 |
| 입력 / 출력 / 문맥 | 10240 / 2048 / 12288 토큰 |
| 추론 서버 | 127.0.0.1:8769, 요청 중에만 실행 |
| 모델 병렬 / 작업 병렬 | 1 / 1, 임베딩과 생성 모델 순차 적재 |
| 임베딩 모델 | Qwen/Qwen3-Embedding-0.6B-GGUF Q8_0, 1024차원 |
| 임베딩 모델 revision | 370f27d7550e0def9b39c1f16d3fbaa13aa67728 |
| 임베딩 모델 SHA-256 | 06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439 |

문서 탐색은 YAML도 참고하지만 수정 대상은 Markdown(`.md`)만 선택한다. 명시적으로 지정한 YAML 수정 요청은 실행 전에 거부한다. 필수 승계 원문을 자동 제거하지 않으며, 입력이 10,240토큰을 넘으면 토큰 수와 원문을 실행 기록에 남기고 중단한다.

Python 의존성은 `requirements.lock`의 버전·해시로 고정한다. 런타임 코드는 `.local/worldbuilding/`, 모델은 `.model/worldbuilding/`에 둔다. 운영 중 모델 자동 교체·CPU 추론·실패 시 클라우드 전환은 없다. 시스템 NVIDIA 드라이버와 전역 Python 환경은 수정하지 않는다.

## 컨텍스트 승계

- 현재 Markdown·YAML을 읽고 파일별 해시를 기록한다. 변경·삭제된 문서 목록을 이전 색인과 비교한다.
- 필수 원문 첫 구간, 지시의 명칭·제목·본문에 맞는 구간, 수정 대상을 토큰 예산 안에서 제공한다. 설계·기준 문서를 우선한다.
- 신규 작성·추가 결과의 `proposal_status_text`는 출력 스키마에서 `신규 제안`으로 고정한다. 프로그램이 제목 다음 또는 추가 문단 앞에 상태 표시를 붙인다. 표시를 모델의 자유 본문 생성에 맡기지 않는다.
- 승인 여부를 모델이 추측해 저장하지 않는다. 혼합 상태 문서는 `mixed_or_unresolved`, 과거 이력은 `historical`로 표시하고 원문의 확정·제안을 구분하도록 지시한다.
- 모델이 실제 받은 구간의 ID만 인용할 수 있다. 파일·구간·해시·원문을 실행 기록에 남긴다.
- 제공된 원문 구간만 검토하며 전체 설정의 의미적 무모순을 보장하지 않는다. 8K 예산을 넘는 긴 작업은 범위를 나눠 지시한다.
- 로컬 임베딩 의미 검색과 기존 키워드·링크 검색을 결합한다. 문단별 승인 파서·인물 관계 그래프·자동 요약 기억·독립된 의미 검토 모델은 아직 구현하지 않았다.

## 쓰기와 복구 경계

생성은 허용된 폴더의 새 `.md` 파일에만, 추가·교체는 요청에서 지정했거나 에이전트가 읽고 선택한 기존 파일에만 가능하다. 삭제·승인 원장 수정·게임 데이터 YAML 변경은 제공하지 않는다. 추가는 원문을 유지하고, 교체는 실제 제공된 원문에서 유일한 구간만 대상으로 한다.

카탈로그를 지정하면 기존 `## 분류 (개수)` / 문서·경로 표의 해당 분류를 갱신한다. 지원하지 않는 카탈로그 형식은 실패한다. 카탈로그 갱신도 원본 해시 확인·변경 이력·복구에 포함한다.

입출력 스키마, 중복 YAML/JSON 키, 읽지 않은 출처, 경로·심볼릭 링크 이탈, 깨진 상대 파일 링크, 생성 중 원본 변경을 검사한다. 모델 응답을 복구 파싱하지 않는다. 최종 문체와 설정의 적합성은 화면의 경고와 원문을 대조해 검토한다.

작업별 `request.yaml`, `source-snapshot.yaml`, `context.yaml`, `response.json`, `result.yaml`, `changes.yaml`, `transaction.yaml`, 로그를 비공개 상태 폴더에 보관한다. 이력은 자동 삭제하지 않는다. 상태 폴더에 개인정보나 외부 인증키를 넣지 않는다. 로그는 4초 간격 heartbeat를 남긴다.

원본 적용 중 중단되면 `transaction.yaml`을 보존한다. 다른 작업을 실행하기 전에 해당 작업을 되돌려 복구한다. 외부 편집으로 원본 해시가 달라졌으면 자동 복구를 중단하며 그 편집을 덮어쓰지 않는다. 작업별 반영은 원자적 파일 교체와 보상 복구를 사용하며 여러 파일을 하나의 파일시스템 트랜잭션으로 커밋하는 방식은 아니다.

## 검증

```bash
.local/worldbuilding/venv/bin/python -m unittest discover -s generators/worldbuilding/tests -v
python3 -m unittest discover -s tools/review/tests -p 'test_review_*.py' -v
```

GPU 시험은 합성 문서 루트를 별도 설정에 연결해 수행한다. 실제 비공개 세계관을 테스트 fixture로 공개 저장소에 복사하지 않는다. 관리 화면은 127.0.0.1에서만 서비스하며 쓰기 API는 Host·Origin·CSRF 토큰을 검사한다.

기존 생성 환경에 임베딩 모델만 추가하려면 `python3 generators/worldbuilding/worldbuilding.py prepare-embedding`을 실행한다. 전체 `prepare`에도 임베딩 준비가 포함된다.

## 확인한 자료

- [Qwen 임베딩 모델 카드](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF): 로컬 임베딩 실행 계약.
- [Qwen 모델 카드](https://huggingface.co/Qwen/Qwen3.5-4B): 모델과 비추론 모드.
- [GGUF 배포 원본](https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF): 양자화 파일.
- [llama.cpp 빌드](https://github.com/ggml-org/llama.cpp/blob/b10964/docs/build.md): CUDA 빌드.
- [llama.cpp 서버](https://github.com/ggml-org/llama.cpp/tree/b10964/tools/server): 문맥·구조 출력·GPU 적재.
- [NVIDIA CUDA 설치](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/): Python 패키지 설치 방식.

## 웹 도서 편집

도서 편집은 선택한 도서의 등록 경로에 있는 문서를 파악하는 4단계 작업이다. 한 번에 전체 자동 편집을 실행하지 않고 도서를 선택한 뒤 다음 단계 중 하나를 명령으로 실행한다.

1. **문서 요약**(`document-summary`): 문서를 요약하고 주제별 그룹을 만들어 각 문서의 내용과 목적을 확인한다.
2. **목차 구성**(`table-of-contents`): 요약과 문서 목적을 바탕으로 의도에 맞는 목차를 구성하고 목차별 문서 묶음을 제안한다.
3. **문서 재구성**(`document-reconstruction`): 목차별 묶음에 따라 문서를 문단 단위로 분해하거나 여러 문서를 통합한다. 원문 문단은 보존하고 배치와 대상 파일만 변경한다.
4. **문서 정리**(`document-cleanup`): 재구성 결과의 제목·순서·중복·빈 문서·참조 링크를 검증하고 읽기용 도서 판본과 원본 변경 미리보기를 정리한다.

각 단계의 결과는 다음 단계의 입력으로 저장한다. 사용자가 단계를 다시 실행하면 해당 단계의 결과를 새로 만들며, 원본 파일은 3단계의 변경 미리보기에서 확인한 뒤 4단계의 반영 명령으로만 수정한다.

관리도구의 **도서 편집**에서 **세계관 / 시스템 설계** 중 하나를 선택하고 **선택한 도서 편집**을 누른다. 등록한 루트 폴더의 문서를 자동으로 불러오며 제목·파일명·상위 절 키워드로 주제별 목차 초안을 만든다. 자동 분류를 확인하고 장 이름을 수정하거나 문단 순서를 옮긴 뒤 **이 배치로 웹 도서 생성**을 누른다. 동일 장 이름은 한 장으로 모이며 장 순서는 첫 등장 순서, 장 안에서는 배치 순서를 따른다.

본문을 생성·요약하지 않는다. Markdown의 문단·표·목록·코드 블록과 YAML 문서를 원문 단위로 보존한다. 각 문단은 출처 경로·줄 범위·상위 제목·해시를 가진다. 원문 순서로 재조합한 텍스트가 원본과 같은지 확인하며 누락·중복·배치안 작성 후 원문 변경은 실패한다. 분리된 문단의 승인 상태를 추론하지 않으므로 출처의 원문 맥락을 확인해야 한다.

웹 도서는 주제 목차, 주요 용어 색인, 본문 통합 검색, 문단별 보존 원문, 포함된 문서 사이의 링크를 제공한다. 원문 HTML은 실행하지 않으며 이미지는 설명으로 표시하고 참조 안내를 남긴다. 선택 범위 밖 링크도 참조 안내에 남긴다. 브라우저 인쇄와 HTML·Markdown 저장을 지원한다.

결과는 비공개 상태 경로의 `books/<판본 ID>/`에 저장한다. `paragraphs.yaml`은 원문과 배치, `manifest.yaml`은 원본 해시와 판본 정보를 보존한다. 원본을 수정하지 않으며 원본 변경 시 목록에 갱신 필요를 표시한다. 자동 의미 통합이나 모순 해결을 수행하지 않는다. 모델 추론 없이 결정적 편집을 수행하므로 GPU와 모델 준비가 필요 없다. Markdown 렌더러는 `markdown-it-py==3.0.0`을 사용한다.

## 통합 문서 관리와 원본 파일 구조 정리

통합 관리도구의 **세계관 작성·정리**와 **도서 편집** 메뉴로 전환한다. 작성·정리는 기존 원문을 검색해 내용을 생성·수정하며, 도서 편집은 문단 본문을 보존하면서 원본 파일 구조와 읽기용 도서를 관리한다. 메뉴 전환 시 편집 중인 배치안은 유지된다. `--worldbuilding-only`도 같은 관리 화면을 사용한다.

도서 편집에서 원본 폴더의 배치안을 불러오면 초기 파일 배치는 원래 순서다. 이동할 문단을 선택하고 기존 대상 파일 또는 새 `.md` 경로를 지정한다. 새 파일에는 제목도 입력한다. 대상 파일 지정은 선택 문단을 대상의 뒤에 배치하며 화살표로 순서를 조정할 수 있다. 기존 대상 파일은 선택 범위에 포함해야 한다. YAML은 원래 위치를 유지하며 Markdown 파일 간 이동을 지원한다.

**원본 파일 변경 미리보기**는 누락·중복·본문 해시·쓰기 범위·보호 문서·파일 제목·참조 링크를 검사하고 파일별 diff를 만든다. **확인한 변경을 원본에 반영**에서만 파일을 쓴다. 문단 본문은 서버에 보존된 원문으로 구성하고 클라이언트에서 받지 않는다. 새 파일 제목과 문단 사이 구분 줄만 추가한다. 파일이 비워지거나 참조 링크의 의미가 달라지는 이동은 실패하며 자동 삭제·링크 추측 수정은 하지 않는다. 카탈로그 변경도 같은 트랜잭션에 포함한다.

미리보기 이후 원문·설정이 달라지면 반영을 거부한다. 파일 구조 변경 이력에서 되돌릴 수 있으며 이후 외부 편집이 있으면 복구를 차단한다. 비공개 상태의 `reorganizations/<ID>/`에 배치안·변경 전후·저널·실행 로그를 남긴다. 중단 시 `applying` 저널을 복구할 수 있다. 원본 반영 후 도서는 새 배치안으로 갱신하며 기존 판본은 원본 변경 상태로 표시한다.

## 관리 도서 두 종류와 루트 폴더

도서 선택은 **세계관**과 **시스템 설계** 두 종류로 고정한다. 폴더 체크박스와 자유 도서 제목 입력은 기본 화면에서 제거했다. 생성 결과는 선택한 도서의 판본으로 보관하며 해당 도서의 변경 이력만 표시한다.

루트는 비공개 상태의 `document-collections.yaml`에 저장한다. 기본 세계관은 `world`, 시스템 설계는 존재하는 `gameplay`, `backend`, `frontend`, `ssot`, `workflow` 폴더를 연결한다. **루트 폴더 설정**을 펼치면 연결된 문서 루트 안의 폴더를 추가하거나 연결 해제할 수 있다. 해제는 파일을 삭제하지 않는다. 두 도서 사이 및 같은 도서 안에서 겹치는 루트, 숨김 경로, 루트 이탈, 심볼릭 링크는 거부한다. 원본 선택 루트 전체를 추가해 두 도서의 범위를 섞지 않는다.

도서 편집의 원본 구조 반영은 선택한 도서의 등록 루트 안에만 허용하며 보호 문서 규칙은 유지한다. 세계관 작성 모델의 기존 쓰기 설정은 변경하지 않는다. 루트 설정이 바뀌면 기존 배치안을 거부하고 다시 불러오도록 안내한다. 판본은 도서 ID로 연결하여 루트 추가 후에도 유지하고 갱신 필요 여부를 표시한다.

## 단계별 AI 도서 편집

도서 편집 화면에서 세계관 또는 시스템 설계를 선택하고 1~4단계 중 하나를 선택한 뒤 단계 명령을 실행한다. 고정 Qwen 로컬 GPU 모델은 문서 요약과 그룹화, 목차 구성, 문단 배치, 최종 정리의 단계별 출력만 생성한다. 수동 배치 조정은 3단계의 보조 기능으로 유지한다.

작업은 기존 지속 큐에서 순차 실행한다. 화면을 닫아도 작업은 계속되며 다시 열면 상태와 결과를 확인할 수 있다. 모델의 본문 재작성은 허용하지 않고 원문 ID만 반환하게 한다. 문단 누락·중복, 원문에 없는 색인어, YAML 이동, 보호 파일 변경, 링크 의미 변경, 실행 중 원문 변경은 명시적으로 실패시킨다. 큰 단일 문단이 입력 예산을 넘으면 내용을 잘라내지 않고 중단한다.

완료 시 웹 도서를 자동 생성하고 파일 분해·이동·재배치의 변경 미리보기를 보관한다. 원본 반영은 관리도구의 기존 반영 버튼을 사용하며 되돌리기 저널을 유지한다. 목차와 색인만 바뀌어 원본 변경이 없어도 도서는 생성된다. 모델 입력·응답·진행 로그는 비공개 작업 경로에 저장하며 4초 간격 진행 로그를 남긴다.

## 터미널 도서 편집 실행기

저장소 루트에서 `worldbuilding.py book` 명령을 사용한다. CLI와 웹 관리도구는 `jobs.register_document_job`의 요청 검증·등록, `book_automation.run_automated_book`의 단계 상태·실패 처리, 동일한 GPU·문서 잠금과 편집 파이프라인을 공유한다. 모델 선택 인자는 제공하지 않는다.

```bash
# 관리하는 두 도서와 연결된 루트 확인
python3 generators/worldbuilding/worldbuilding.py book list

# 로컬 터미널에서 실행하고 완료까지 기다리기
python3 generators/worldbuilding/worldbuilding.py book edit --collection world --instruction '내용을 보존하며 목차와 색인을 정리한다.'

# 파일에 적은 지시로 시스템 설계 도서 편집
python3 generators/worldbuilding/worldbuilding.py book edit --collection system-design --instruction-file /절대경로/편집지시.txt

# 실행 중인 관리도구 큐에 등록하고 즉시 종료
python3 generators/worldbuilding/worldbuilding.py book edit --collection world --instruction '도시별로 관련 문단을 모아 정리한다.' --submit

# 작업 ID로 상태 및 완료 결과 조회
python3 generators/worldbuilding/worldbuilding.py book status --task 작업ID
python3 generators/worldbuilding/worldbuilding.py book result --task 작업ID

# 결과의 파일 변경 미리보기를 검토한 후 반영 또는 되돌리기
python3 generators/worldbuilding/worldbuilding.py book apply --reorganization 변경ID
python3 generators/worldbuilding/worldbuilding.py book rollback --reorganization 변경ID
```

`--config /절대경로/workspace.yaml`은 `book` 다음, 하위 명령 앞에 지정한다. 기본 설정은 `.local/worldbuilding/workspace.yaml`이다. `--instruction-file -`는 표준 입력을 UTF-8 지시로 읽으며 `--instruction`과 동시에 사용할 수 없다.

표준 출력은 결과 JSON 한 개이며 단계·진행 로그는 표준 오류와 `execution.log`에 기록한다. 오류는 0이 아닌 종료 코드, `failure_reason_text`, 추적 로그와 마지막 로그로 확인한다. 실행 중 GPU 단계는 웹과 동일하게 4초 간격으로 진행 상황을 기록한다. 원본 파일은 `edit`만으로 반영하지 않는다.

직접 실행 기록은 검수 가능한 `book_review_root/book-cli-jobs/<작업ID>/`에 보관한다. `book_review_root`는 워크플로 저장소의 실행별 `.tmp/YYYY-MM-DD_HH-mm-ss/` 아래로 지정한다. 큐 등록은 비공개 상태의 `jobs/<작업ID>/`에 보관한다. 직접 실행과 웹 큐를 분리해 같은 작업의 이중 실행을 막으며 도서 판본·변경 미리보기·복구 저널은 공유한다. `status`와 `result`는 두 기록 경로를 모두 조회한다. `--submit`은 관리도구가 실행 중일 때만 허용되며, 등록 후에는 터미널 종료와 독립적으로 관리도구가 실행한다.
