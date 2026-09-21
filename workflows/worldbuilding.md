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
| 입력 / 출력 / 문맥 | 6144 / 2048 / 8192 토큰 |
| 추론 서버 | 127.0.0.1:8769, 요청 중에만 실행 |
| 모델 병렬 / 작업 병렬 | 1 / 1, 임베딩과 생성 모델 순차 적재 |
| 임베딩 모델 | Qwen/Qwen3-Embedding-0.6B-GGUF Q8_0, 1024차원 |
| 임베딩 모델 revision | 370f27d7550e0def9b39c1f16d3fbaa13aa67728 |
| 임베딩 모델 SHA-256 | 06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439 |

Python 의존성은 `requirements.lock`의 버전·해시로 고정한다. 런타임 코드는 `.local/worldbuilding/`, 모델은 `.model/worldbuilding/`에 둔다. 운영 중 모델 자동 교체·CPU 추론·실패 시 클라우드 전환은 없다. 시스템 NVIDIA 드라이버와 전역 Python 환경은 수정하지 않는다.

## 컨텍스트 승계

- 현재 Markdown·YAML을 읽고 파일별 해시를 기록한다. 변경·삭제된 문서 목록을 이전 색인과 비교한다.
- 필수 원문 첫 구간, 지시의 명칭·제목·본문에 맞는 구간, 수정 대상을 토큰 예산 안에서 제공한다. 설계·기준 문서를 우선한다.
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

세계관 작업 화면의 **웹 도서 편집 열기**에서 연결된 문서 루트의 폴더를 선택한다. **목차·문단 배치안 만들기**는 제목·경로·상위 절 키워드로 주제별 목차 초안을 만든다. 자동 분류를 확인하고 장 이름을 수정하거나 문단 순서를 옮긴 뒤 **이 배치로 웹 도서 생성**을 누른다. 동일 장 이름은 한 장으로 모이며 장 순서는 첫 등장 순서, 장 안에서는 배치 순서를 따른다.

본문을 생성·요약하지 않는다. Markdown의 문단·표·목록·코드 블록과 YAML 문서를 원문 단위로 보존한다. 각 문단은 출처 경로·줄 범위·상위 제목·해시를 가진다. 원문 순서로 재조합한 텍스트가 원본과 같은지 확인하며 누락·중복·배치안 작성 후 원문 변경은 실패한다. 분리된 문단의 승인 상태를 추론하지 않으므로 출처의 원문 맥락을 확인해야 한다.

웹 도서는 주제 목차, 주요 용어 색인, 본문 통합 검색, 문단별 보존 원문, 포함된 문서 사이의 링크를 제공한다. 원문 HTML은 실행하지 않으며 이미지는 설명으로 표시하고 참조 안내를 남긴다. 선택 범위 밖 링크도 참조 안내에 남긴다. 브라우저 인쇄와 HTML·Markdown 저장을 지원한다.

결과는 비공개 상태 경로의 `books/<판본 ID>/`에 저장한다. `paragraphs.yaml`은 원문과 배치, `manifest.yaml`은 원본 해시와 판본 정보를 보존한다. 원본을 수정하지 않으며 원본 변경 시 목록에 갱신 필요를 표시한다. 자동 의미 통합이나 모순 해결을 수행하지 않는다. 모델 추론 없이 결정적 편집을 수행하므로 GPU와 모델 준비가 필요 없다. Markdown 렌더러는 `markdown-it-py==3.0.0`을 사용한다.

## 통합 문서 관리와 원본 파일 구조 정리

통합 관리도구의 **세계관 작성·정리**와 **도서 편집** 메뉴로 전환한다. 작성·정리는 기존 원문을 검색해 내용을 생성·수정하며, 도서 편집은 문단 본문을 보존하면서 원본 파일 구조와 읽기용 도서를 관리한다. 메뉴 전환 시 편집 중인 배치안은 유지된다. `--worldbuilding-only`도 같은 관리 화면을 사용한다.

도서 편집에서 원본 폴더의 배치안을 불러오면 초기 파일 배치는 원래 순서다. 이동할 문단을 선택하고 기존 대상 파일 또는 새 `.md` 경로를 지정한다. 새 파일에는 제목도 입력한다. 대상 파일 지정은 선택 문단을 대상의 뒤에 배치하며 화살표로 순서를 조정할 수 있다. 기존 대상 파일은 선택 범위에 포함해야 한다. YAML은 원래 위치를 유지하며 Markdown 파일 간 이동을 지원한다.

**원본 파일 변경 미리보기**는 누락·중복·본문 해시·쓰기 범위·보호 문서·파일 제목·참조 링크를 검사하고 파일별 diff를 만든다. **확인한 변경을 원본에 반영**에서만 파일을 쓴다. 문단 본문은 서버에 보존된 원문으로 구성하고 클라이언트에서 받지 않는다. 새 파일 제목과 문단 사이 구분 줄만 추가한다. 파일이 비워지거나 참조 링크의 의미가 달라지는 이동은 실패하며 자동 삭제·링크 추측 수정은 하지 않는다. 카탈로그 변경도 같은 트랜잭션에 포함한다.

미리보기 이후 원문·설정이 달라지면 반영을 거부한다. 파일 구조 변경 이력에서 되돌릴 수 있으며 이후 외부 편집이 있으면 복구를 차단한다. 비공개 상태의 `reorganizations/<ID>/`에 배치안·변경 전후·저널·실행 로그를 남긴다. 중단 시 `applying` 저널을 복구할 수 있다. 원본 반영 후 도서는 새 배치안으로 갱신하며 기존 판본은 원본 변경 상태로 표시한다.
