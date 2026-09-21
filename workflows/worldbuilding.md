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
