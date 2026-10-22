# 음악생성

관리도구 분류 **소리 관리**에 MiniMax-Music3 고정 생성기를 제공한다.

2026-10-21 MiniMax 채택에 따라 ACE-Step은 메뉴·게이트웨이·직접 실행 진입점·설치 경로에서 폐기했다. 진행 중인 MiniMax 요청의 해시 검증을 위해 공용 runtime.py와 defaults.yaml의 기존 ACE 구현·프로필은 호환용으로만 보존하며 서비스 허용 목록에서 차단한다. 기존 `.tmp/test/music-ace-step/` 결과·이력 및 `.model/music/music-ace-step/` 캐시·가상환경은 보존하지만 활성 도구로 제공하지 않는다. GUI와 통합 CLI가 같은 작업 서비스·공용 GPU 대기열·기록 저장소를 사용한다. 게임에 자동 전달하지 않으며 출력은 청취 검수 전 후보다.

| 서비스 | 고정 모델 | 출력 | 메모리 설정 |
|---|---|---|---|
| `music-minimax` | MiniMax-Music3 | 44.1kHz stereo PCM16 WAV | BF16, component offload + LM leaf-level streaming |

MIDI 출력은 없다. 최대 생성 길이는 기본 30초이며 관리도구의 입력 범위는 MiniMax 5~120초로 제한했다. 이는 목표·최소 길이가 아니며 종료 토큰이 나오면 더 일찍 끝난다. MiniMax Diffusers의 네이티브 출력은 44.1kHz다. 공식 서버의 32kHz 리샘플링 출력과 구분한다. 이 설정의 **실제 8GB 성공·속도·품질은 아직 검증하지 않았다**. MiniMax는 CPU RAM에 큰 가중치를 대기시키므로 VRAM 8GB와 시스템 RAM 요구량은 다르다.

2026-10-15 RTX 5070 Laptop GPU(8,151MiB), 시스템 RAM 61GiB에서 ACE-Step과 MiniMax의 로컬 로더 초기화 및 구성요소별 순차 CUDA 적재를 검증했다. MiniMax의 8.6B 언어모델은 전체 GPU 적재 대신 leaf-level 오프로드로 단일 토큰 forward를 수행하고 CUDA 출력을 확인했다. `nvidia-smi` 프로세스 VRAM 관측 피크는 ACE-Step 4,744MiB, MiniMax 5,182MiB였다. 이는 로딩 검증의 표본 최대값이며 전체 음악 생성의 메모리·성공을 보장하지 않는다. Stable Audio는 2026-10-15 폐기하여 메뉴·게이트웨이·실행 어댑터에서 제외했다. 로딩 검증만으로 `prepared.json`을 생성하지 않는다.

MiniMax의 고정 Diffusers 버전은 Hugging Face Hub 1.x를 요구하므로 Transformers 5.x를 사용한다. 구성요소는 다운로드된 로컬 `model/` 경로를 명시해 오프라인 로딩하고, 필수 구성요소가 누락되면 오프로드 설정 전에 실패한다.

2026-10-15 관리도구 점검에서는 공용 메뉴와 합성된 두 Gradio 페이지를 실제 브라우저에서 검증했다. 격리된 HTTP 게이트웨이와 작업 서비스를 사용하고 GPU 실행만 모의 처리해 생성 확인·취소, CLI/GUI 공유 이력, WAV 재생, 입력 복원, 선택 삭제·전체 초기화의 확인·취소와 실제 시험 파일 삭제를 확인했다. 재연결 후 이력 유지, 390px 화면의 메뉴·확인 영역도 확인했다. 이 검증은 실제 음악 추론·품질 검증을 대신하지 않는다.

`loop_request`는 추적된 반복 구조 문구를 추가하는 선택 입력이다. 심리스 루프를 생성·보장하거나 WAV 끝과 시작을 자동 접합하지 않는다. 기본 반주 문구, 최종 프롬프트 원문·단어 수·SHA-256을 GUI와 실행 기록에서 확인할 수 있다. 보컬 미포함도 모델 출력의 청취 검수가 필요하다.

## 실행 환경

각 모델은 의존성 충돌을 피하려고 별도 Python 3.11 또는 3.12 가상환경을 사용한다. 관리 GUI는 기존 `.venv-management`, 모델 실행기는 아래 경로로 고정된다. 모델 설치가 없으면 명령이 원인과 경로를 출력하고 실패한다. 설치 명령은 저장소 루트에서 실행한다.

```bash

python3.11 -m venv .venv-music-minimax
.venv-music-minimax/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cu128
.venv-music-minimax/bin/python -m pip install -r generators/music/requirements-minimax.txt
```

MiniMax Diffusers commit은 requirements에 고정한다. 호환 CUDA 드라이버와 BF16 지원 GPU가 필요하다. 모델 추론은 CUDA 전용이고 CPU 추론 대체는 없다. CPU에서 토크나이징·파일 입출력·오디오 저장을 하는 것은 모델 추론과 구분한다.

## GUI·CLI

기존 게이트웨이·관리 서버를 실행한 뒤 메뉴에서 **소리 관리 → MiniMax-Music3**을 선택한다. 프롬프트, 최대 생성 길이, 시드, 반복 구조 요청, 이력 태그를 입력한다. 최종 모델 입력 영역에서 `prompt` 원문과 별도로 입력하는 `lyrics`(반주는 `[Instrumental]`)을 확인한다. 최대 생성 길이는 `audio_duration`으로 전달하며 반복 요청은 프롬프트 문구 추가, 이력 태그는 기록용이다. 생성과 모델 준비의 확인은 **Gradio 인라인 영역**이며 모달이 아니다. 취소하면 접수하지 않는다. 랜덤 시드는 값만 바꾸고 생성하지 않는다.

```bash
.venv-management/bin/python tools/manager.py command music-minimax prepare

.venv-management/bin/python tools/manager.py command music-minimax generate --prompt 'Calm fantasy village music with flute and acoustic strings' --duration-seconds 30 --seed 42 --loop-request --tag village --detach
.venv-management/bin/python tools/manager.py command music-minimax status <생성ID>
.venv-management/bin/python tools/manager.py command music-minimax logs <생성ID>
.venv-management/bin/python tools/manager.py command music-minimax history
.venv-management/bin/python tools/manager.py command music-minimax prioritize <생성ID>
.venv-management/bin/python tools/manager.py command music-minimax cancel <생성ID>
.venv-management/bin/python tools/manager.py command music-minimax resume <생성ID>
.venv-management/bin/python tools/manager.py command music-minimax history-delete <생성ID>
```

MiniMax에서 위 명령을 사용한다. `prepare`는 작업 ID를 반환하며 `status/logs`로 준비 상태를 확인한다. 생성은 `--detach`를 생략하면 공용 CLI가 완료까지 기다린다. 프롬프트는 `--prompt-file`로도 전달할 수 있다. `model-status`, 명시적 `history-reset`도 지원한다.

첫 생성은 모델 준비를 먼저 수행한다. 준비는 고정 모델을 다운로드하고 종속 구성요소까지 로드한 후 `prepared.json`을 원자적으로 저장한다. 실패 시 준비 완료로 표시하지 않는다. 생성 시 준비 파일·크기를 검증하고 offline 모드로 로컬 파일을 재사용한다. 가중치의 전체 암호학적 무결성을 재계산하는 검증은 아니다. 준비 리비전·파일 목록·실행 코드 해시를 시도별 manifest에 복사한다. 코드 버전이 달라지거나 파일이 누락되면 `prepare`를 명시적으로 다시 실행한다. `prepare`는 준비 표식을 갱신하며 기존 가중치 캐시를 삭제하지 않는다.

## 이력·측정

- 모델: `.model/music/<service>/` (모델·다운로드 캐시만).
- 작업: `.tmp/test/<service>/<KST 시각>-<8자리 ID>/`.
- 색인: `.tmp/manager-current/<service>/`.
- 각 재개는 `attempts/<UUID>/` 아래 새 시도로 실행한다. 실패 지점의 음악 토큰을 이어 생성하는 체크포인트 재개는 아니다.
- 요청·최종 프롬프트·모델 manifest·결과·오류·metrics를 보존한다. 최종 WAV는 `attempts/<UUID>/music.wav`다.
- MiniMax의 `audio_duration`은 최대 길이다. 조기 종료 원인은 실행 로그의 `music-minimax/termination` 및 `attempts/<UUID>/minimax-termination.json`에서 확인한다. `audio_end_token`은 종료 토큰 감지, `max_frames`는 프레임 상한 도달, `not_observed`는 종료 조건 미관측이다. 요청 초·프레임 상한·프레임률·마지막 토큰 ID·종료 토큰 감지 여부·샘플링 프레임 수를 기록하며 첫 준비 샘플과 RVQ 잔여 코드는 프레임 수에서 제외한다. 파이프라인 실패는 별도 상태로 보존하므로 종료 토큰 이후 디코더 실패도 구분할 수 있다. 이 기록은 길이를 강제하거나 연장하지 않으며, 이전 실행의 종료 원인을 소급해서 확정하지 않는다.
- 선택 이력 삭제·초기화는 확인 후 작업 폴더의 입력 사본·WAV·중간 산출물·요청·로그·모든 시도 기록과 이력 인덱스를 실제 삭제한다. 대기·실행 중에는 거절하며, 모델·외부 원본·다른 생성기 기록은 보호한다. 초기화는 목록에서 숨긴 작업도 포함한다.
- 우선 실행은 공용 대기열의 queued 작업만 이동하며 GPU 메모리 조건과 현재 작업을 유지한다.
- 공용 작업자의 5초 heartbeat가 ETA·예상 전체 진행률·완료 시각을 갱신한다. 동일 모델·길이·설정·GPU·실행 코드의 완료 이력을 사용하며 다운로드 포함 실행은 표본에서 제외한다. 첫 실행·지연·대기는 근거와 함께 미정으로 표시한다. 공식 API의 내부 단계별 진행률을 임의 백분율로 만들지 않는다.
- 작업자와 자식 프로세스의 VRAM 현재값·관측 피크를 장치별로 보존한다. 장치 전체 사용량은 다른 프로세스를 포함한다. 5초 표본 사이 순간 피크를 놓칠 수 있으며 PyTorch allocated/reserved는 별도 통계다. 실패·OOM·취소 시에도 확보한 시도별 metrics와 공용 실행기 `gpu-memory.json`을 보존한다.

## 라이선스와 공식 구현

코드 라이선스와 모델·생성물 이용 조건을 구분한다. ACE 모델 카드는 MIT 및 생성 음악의 상업 이용 허용을 안내한다. MiniMax는 Community License의 표시·매출 조건을 확인해야 한다. 메뉴에서 각 원문으로 연결한다. UI를 제공하는 것으로 사용자의 약관 동의를 대신하지 않는다.

- [ACE-Step 공식 코드와 추론 API](https://github.com/ace-step/ACE-Step-1.5), [모델 카드](https://huggingface.co/ACE-Step/Ace-Step1.5)
- [MiniMax 모델·low-VRAM 안내](https://huggingface.co/MiniMaxAI/MiniMax-Music3), [Diffusers 네이티브 출력 계약](https://github.com/huggingface/diffusers/blob/dafe3733fcfdbf3c48915fe77be3aef65b5d6a2d/docs/source/en/api/pipelines/minimax_music3.md)

## 검증

```bash
.venv-management/bin/python tools/review/tests/run_music_regression.py
```

자동 실행기가 `.tmp/test/music-regression/<KST 시각>/`에 전체 로그·heartbeat·JUnit·summary·종료 코드를 남긴다. 계약 검증은 모델을 다운로드하거나 실제 GPU 작업을 접수하지 않는다. 실제 음악 품질·8GB 피크 검증은 모델 환경 설치와 다운로드 이후 별도 실행으로 확인해야 한다.

### MiniMax 토큰 상한 입력

GUI의 `max_new_tokens`는 오디오 프레임 상한이며 125~3,000 정수(5~120초)를 받는다. 250≈10초, 750≈30초, 1,500≈60초, 3,000≈120초다. 종료 토큰이 나오면 더 짧게 끝나므로 정확한 길이·최소 길이를 보장하지 않는다. 프롬프트 단어 수와는 무관하며 큰 값은 최대 연산량을 늘린다.

로컬 Diffusers는 이 값을 직접 받지 않으므로 공용 서비스가 초당 25프레임 기준으로 `duration_seconds`로 정규화하고 실행기는 기존 `audio_duration`에 전달한다. 저장·입력 복원·ETA는 기존 초 단위 계약을 유지한다. GUI는 초를 읽기 전용으로 환산 표시하고 이력 복원 시 토큰 수를 복원한다. 기존 초 단위 요청도 계속 허용한다.

통합 CLI: `python tools/manager.py command music-minimax generate --prompt 'Calm village instrumental' --max-new-tokens 750 --detach`. `--max-new-tokens`와 `--duration-seconds`는 동시에 지정할 수 없다. HTTP `generate`에도 `max_new_tokens`를 전달할 수 있으며 `duration_seconds`와 동시 지정은 거절한다. 이 운영 한도는 공식 모델의 최대 길이와 구분한다.

### 실험용 최소 생성 길이

MiniMax의 `min_duration_seconds` / CLI `--min-duration-seconds`는 기본 0(해제)이다. 최대 길이 이하의 값을 지정하면 해당 프레임 수까지 LM 출력의 종료 토큰을 top-k 후보 선정 전에 억제한다. 최소 50초·최대 60초 예시는 `--min-duration-seconds 50 --max-new-tokens 1500`이다. 무음 덧붙이기나 반복 편집이 아니며 음악적 자연스러움은 청취 검수가 필요하다. 기존 요청·대기 작업에는 적용하지 않는다. 실험 제어 코드 해시와 최소 길이는 시도별 `duration-control.json`, 종료 억제 단계 수는 `minimax-termination.json`에 남긴다. 최대 길이 도달 시 종결 없이 끊길 수 있다.

### MiniMax 별도 가사 입력

`lyrics`를 지정하면 `prompt`에 반주 문구를 자동 추가하지 않습니다. `loop_request=false`이면 입력 설명을 그대로 전달합니다(앞뒤 공백 제외). 반주는 `[Instrumental]`, 보컬은 `[verse]`·`[chorus]`와 가사를 별도 입력합니다. 가사 생략은 기존 이력의 반주 고정·문구 추가 계약을 유지합니다. GUI의 ‘이전 방식’은 기존 이력 복원용입니다.

CLI는 `--lyrics` 또는 `--lyrics-file`을 지원합니다. 예제 조건은 `--duration-seconds 60 --seed 7 --no-loop-request --lyrics-file lyrics.txt`입니다. GUI에서는 audio_duration 60초(환산 1500프레임), 최소 길이 0, 자동 반주 문구·반복 요청 해제를 사용합니다. 조기 종료 가능성은 동일합니다.

로컬 실행은 검증된 Diffusers·CUDA BF16·CPU 메모리 오프로드를 유지합니다. ModelScope 패키지로 교체하지 않습니다. 별도 입력 어댑터는 `prompt`, `lyrics`, `audio_duration`, CUDA 시드, `output=audios`를 전달하고 Tensor 출력을 명시하여 WAV로 저장합니다. 기존 모델 준비 해시는 유지하고 새 어댑터 해시와 실제 입력은 실행 시도별 `input-adapter.json`에 기록합니다.
