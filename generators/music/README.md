# 음악생성

관리도구 분류 **음악생성**에 다음 세 고정 생성기를 제공한다. GUI와 통합 CLI가 같은 작업 서비스·공용 GPU 대기열·기록 저장소를 사용한다. 게임에 자동 전달하지 않으며 출력은 청취 검수 전 후보다.

| 서비스 | 고정 모델 | 출력 | 메모리 설정 |
|---|---|---|---|
| `music-stable-audio` | Stable Audio 3 Medium | 44.1kHz stereo PCM16 WAV | FP16, 8스텝, chunked decode |
| `music-ace-step` | ACE-Step 1.5 Turbo + 0.6B LM | 48kHz stereo PCM16 WAV | 단계별 CUDA 로드/CPU 메모리 대기, batch 1, 8스텝 |
| `music-minimax` | MiniMax-Music3 | 44.1kHz stereo PCM16 WAV | BF16, component offload + LM leaf-level streaming |

MIDI 출력은 없다. 기본 30초이며 요청 범위는 Stable/ACE 5~120초, MiniMax 5~60초로 제한했다. MiniMax Diffusers의 네이티브 출력은 44.1kHz다. 공식 서버의 32kHz 리샘플링 출력과 구분한다. 이 설정의 **실제 8GB 성공·속도·품질은 아직 검증하지 않았다**. MiniMax는 CPU RAM에 큰 가중치를 대기시키므로 VRAM 8GB와 시스템 RAM 요구량은 다르다.

2026-10-15 RTX 5070 Laptop GPU(8,151MiB), 시스템 RAM 61GiB에서 ACE-Step과 MiniMax의 로컬 로더 초기화 및 구성요소별 순차 CUDA 적재를 검증했다. MiniMax의 8.6B 언어모델은 전체 GPU 적재 대신 leaf-level 오프로드로 단일 토큰 forward를 수행하고 CUDA 출력을 확인했다. `nvidia-smi` 프로세스 VRAM 관측 피크는 ACE-Step 4,744MiB, MiniMax 5,182MiB였다. 이는 로딩 검증의 표본 최대값이며 전체 음악 생성의 메모리·성공을 보장하지 않는다. Stable Audio는 가중치 접근 403으로 검증하지 못했다. 로딩 검증만으로 `prepared.json`을 생성하지 않는다.

MiniMax의 고정 Diffusers 버전은 Hugging Face Hub 1.x를 요구하므로 Transformers 5.x를 사용한다. 구성요소는 다운로드된 로컬 `model/` 경로를 명시해 오프라인 로딩하고, 필수 구성요소가 누락되면 오프로드 설정 전에 실패한다.

`loop_request`는 추적된 반복 구조 문구를 추가하는 선택 입력이다. 심리스 루프를 생성·보장하거나 WAV 끝과 시작을 자동 접합하지 않는다. 기본 반주 문구, 최종 프롬프트 원문·단어 수·SHA-256을 GUI와 실행 기록에서 확인할 수 있다. 보컬 미포함도 모델 출력의 청취 검수가 필요하다.

## 실행 환경

각 모델은 의존성 충돌을 피하려고 별도 Python 3.11 또는 3.12 가상환경을 사용한다. 관리 GUI는 기존 `.venv-management`, 모델 실행기는 아래 경로로 고정된다. 모델 설치가 없으면 명령이 원인과 경로를 출력하고 실패한다. 설치 명령은 저장소 루트에서 실행한다.

```bash
python3.11 -m venv .venv-music-stable
.venv-music-stable/bin/python -m pip install torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu126
.venv-music-stable/bin/python -m pip install -r generators/music/requirements-stable.txt
```

Stable Audio Medium에는 Flash Attention 2가 추가로 필요하다. 장치의 CUDA·PyTorch·Python과 호환되는 버전을 [공식 설치 안내](https://github.com/Stability-AI/stable-audio-3#flash-attention)에 따라 해당 가상환경에 설치한다. Hugging Face에서 Stable Audio와 종속 Gemma 모델의 접근 권한·약관을 사용자가 처리해야 한다. 인증은 Hugging Face CLI/캐시 또는 조직의 비밀 관리 방식을 사용하고 저장소·env 파일에 토큰을 기록하지 않는다.

```bash
python3.11 -m venv .venv-music-ace
.venv-music-ace/bin/python -m pip install -r generators/music/requirements-ace.txt

python3.11 -m venv .venv-music-minimax
.venv-music-minimax/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv-music-minimax/bin/python -m pip install -r generators/music/requirements-minimax.txt
```

ACE의 CUDA 12.8 패키지 색인은 Linux x86_64 기준이다. 요구 파일에 공식 저장소의 `nano-vllm` 소스도 고정하지만 실제 LM 실행은 PyTorch backend를 지정한다. Stable/ACE 소스와 MiniMax Diffusers PR commit은 requirements에 고정한다. 호환 CUDA 드라이버와 BF16 지원 GPU가 필요하다. 모델 추론은 CUDA 전용이고 CPU 추론 대체는 없다. ACE의 CPU VAE fallback은 명시적으로 차단한다. CPU에서 토크나이징·파일 입출력·오디오 저장을 하는 것은 모델 추론과 구분한다.

## GUI·CLI

기존 게이트웨이·관리 서버를 실행한 뒤 메뉴에서 **음악생성 → 모델 이름**을 선택한다. 프롬프트, 길이, 시드, 반복 구조 요청, 이력 태그를 입력한다. 생성과 모델 준비의 확인은 **Gradio 인라인 영역**이며 모달이 아니다. 취소하면 접수하지 않는다. 랜덤 시드는 값만 바꾸고 생성하지 않는다.

```bash
.venv-management/bin/python tools/manager.py command music-stable-audio prepare
.venv-management/bin/python tools/manager.py command music-ace-step prepare
.venv-management/bin/python tools/manager.py command music-minimax prepare

.venv-management/bin/python tools/manager.py command music-ace-step generate --prompt 'Calm fantasy village music with flute and acoustic strings' --duration-seconds 30 --seed 42 --loop-request --tag village --detach
.venv-management/bin/python tools/manager.py command music-ace-step status <생성ID>
.venv-management/bin/python tools/manager.py command music-ace-step logs <생성ID>
.venv-management/bin/python tools/manager.py command music-ace-step history
.venv-management/bin/python tools/manager.py command music-ace-step prioritize <생성ID>
.venv-management/bin/python tools/manager.py command music-ace-step cancel <생성ID>
.venv-management/bin/python tools/manager.py command music-ace-step resume <생성ID>
.venv-management/bin/python tools/manager.py command music-ace-step history-delete <생성ID>
```

서비스 이름을 교체하면 세 모델 모두 같은 명령을 사용한다. `prepare`는 작업 ID를 반환하며 `status/logs`로 준비 상태를 확인한다. 생성은 `--detach`를 생략하면 공용 CLI가 완료까지 기다린다. 프롬프트는 `--prompt-file`로도 전달할 수 있다. `model-status`, 명시적 `history-reset`도 지원한다.

첫 생성은 모델 준비를 먼저 수행한다. 준비는 고정 모델을 다운로드하고 종속 구성요소까지 로드한 후 `prepared.json`을 원자적으로 저장한다. 실패 시 준비 완료로 표시하지 않는다. 생성 시 준비 파일·크기를 검증하고 offline 모드로 로컬 파일을 재사용한다. 가중치의 전체 암호학적 무결성을 재계산하는 검증은 아니다. 준비 리비전·파일 목록·실행 코드 해시를 시도별 manifest에 복사한다. 코드 버전이 달라지거나 파일이 누락되면 `prepare`를 명시적으로 다시 실행한다. `prepare`는 준비 표식을 갱신하며 기존 가중치 캐시를 삭제하지 않는다.

## 이력·측정

- 모델: `.model/music/<service>/` (모델·다운로드 캐시만).
- 작업: `.tmp/test/<service>/<KST 시각>-<8자리 ID>/`.
- 색인: `.tmp/manager-current/<service>/`.
- 각 재개는 `attempts/<UUID>/` 아래 새 시도로 실행한다. 실패 지점의 음악 토큰을 이어 생성하는 체크포인트 재개는 아니다.
- 요청·최종 프롬프트·모델 manifest·결과·오류·metrics를 보존한다. 최종 WAV는 `attempts/<UUID>/music.wav`다.
- 선택 이력 삭제·초기화는 목록만 숨기고 WAV·요청·로그를 보존한다. 대기·실행 중에는 거절한다. 숨긴 이력은 자동 복원하지 않는다.
- 우선 실행은 공용 대기열의 queued 작업만 이동하며 GPU 메모리 조건과 현재 작업을 유지한다.
- 공용 작업자의 5초 heartbeat가 ETA·예상 전체 진행률·완료 시각을 갱신한다. 동일 모델·길이·설정·GPU·실행 코드의 완료 이력을 사용하며 다운로드 포함 실행은 표본에서 제외한다. 첫 실행·지연·대기는 근거와 함께 미정으로 표시한다. 공식 API의 내부 단계별 진행률을 임의 백분율로 만들지 않는다.
- 작업자와 자식 프로세스의 VRAM 현재값·관측 피크를 장치별로 보존한다. 장치 전체 사용량은 다른 프로세스를 포함한다. 5초 표본 사이 순간 피크를 놓칠 수 있으며 PyTorch allocated/reserved는 별도 통계다. 실패·OOM·취소 시에도 확보한 시도별 metrics와 공용 실행기 `gpu-memory.json`을 보존한다.

## 라이선스와 공식 구현

코드 라이선스와 모델·생성물 이용 조건을 구분한다. ACE 모델 카드는 MIT 및 생성 음악의 상업 이용 허용을 안내한다. Stable은 Community License의 등록·매출 조건, MiniMax는 Community License의 표시·매출 조건을 확인해야 한다. 메뉴에서 각 원문으로 연결한다. UI를 제공하는 것으로 사용자의 약관 동의를 대신하지 않는다.

- [Stable Audio 공식 코드](https://github.com/Stability-AI/stable-audio-3), [모델 카드](https://huggingface.co/stabilityai/stable-audio-3-medium)
- [ACE-Step 공식 코드와 추론 API](https://github.com/ace-step/ACE-Step-1.5), [모델 카드](https://huggingface.co/ACE-Step/Ace-Step1.5)
- [MiniMax 모델·low-VRAM 안내](https://huggingface.co/MiniMaxAI/MiniMax-Music3), [Diffusers 네이티브 출력 계약](https://github.com/huggingface/diffusers/blob/dafe3733fcfdbf3c48915fe77be3aef65b5d6a2d/docs/source/en/api/pipelines/minimax_music3.md)

## 검증

```bash
.venv-management/bin/python tools/review/tests/run_music_regression.py
```

자동 실행기가 `.tmp/test/music-regression/<KST 시각>/`에 전체 로그·heartbeat·JUnit·summary·종료 코드를 남긴다. 계약 검증은 모델을 다운로드하거나 실제 GPU 작업을 접수하지 않는다. 실제 음악 품질·8GB 피크 검증은 모델 환경 설치와 다운로드 이후 별도 실행으로 확인해야 한다.
