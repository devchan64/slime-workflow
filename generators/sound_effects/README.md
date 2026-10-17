# Stable Audio 효과음 생성

관리도구의 **효과음 생성 → Stable Audio 3 · 효과음**에서 사용한다.
주소는 `http://127.0.0.1:8770/?tool=sfx-stable-audio&category=sound-effects`다.

- 고정 모델: `stabilityai/stable-audio-3-small-sfx`. 폐기한 음악용 `music-stable-audio`는 복원하지 않는다.
- 입력: 영어 효과음 설명, 길이 0.5~30초(기본 3초), 정수 시드, 반복 환경음 요청, 이력 태그.
- 출력: 44.1kHz stereo PCM16 WAV. 음악용 반주 문구는 추가하지 않는다.
- 반복 요청은 추적된 환경음 지시를 추가하며 심리스 루프를 보장하지 않는다. 샘플은 사용자가 청취 후 채택한다.
- 고정 8스텝·batch 1·CUDA FP16·분할 디코딩. CPU 모델 추론은 거절한다. 실제 GPU 메모리·속도·품질은 별도 생성 검증 대상이다.

## 실행 환경과 모델 준비

저장소 루트에서 아래 설치기를 실행한다. 관리 GUI와 기존 음악 환경은 변경하지 않는다.
설치기는 공용 로그 실행기를 통해 단계별 출력·5초 heartbeat·실패 명령을 남긴다.

```bash
python3 generators/sound_effects/setup_runtime.py
```

Python 3.12 전용 `.venv-sfx-stable/`과 공식 CUDA 12.8 PyTorch 2.7.1을 사용한다.
공식 Stable Audio 구현은 `requirements.txt`의 Git revision으로 고정한다.
이 설치는 모델 가중치 다운로드나 GPU 추론을 실행하지 않는다.

모델 파일 접근에는 [공식 모델 페이지](https://huggingface.co/stabilityai/stable-audio-3-small-sfx)의 Community License와 Gemma 이용 조건 동의가 필요하다. 사용자 계정에서 동의·로그인한 후 관리페이지의 **모델 다운로드·준비**를 실행한다. 토큰을 프롬프트·설정·env 파일에 넣지 않는다. 기존 Hugging Face 로그인 파일을 사용하며 토큰 값을 기록하지 않는다.

준비는 공용 GPU 대기열의 별도 작업이다. 다운로드 revision과 파일 목록을 기록하고 텍스트 인코더까지 CUDA 적재한 뒤만 준비 완료로 표시한다. 생성은 준비된 로컬 파일을 오프라인으로 사용한다. 접근 거절·의존성 누락·CUDA 오류는 로그에 원인을 남기고 실패한다. 다른 모델이나 CPU 추론으로 대체하지 않는다.

## GUI·CLI 공통 명령

```bash
.venv-management/bin/python tools/manager.py help sfx-stable-audio
.venv-management/bin/python tools/manager.py command sfx-stable-audio model-status
.venv-management/bin/python tools/manager.py command sfx-stable-audio prepare
.venv-management/bin/python tools/manager.py command sfx-stable-audio generate --prompt 'A single soft wet impact, close and dry.' --duration-seconds 3 --seed 42 --detach
.venv-management/bin/python tools/manager.py command sfx-stable-audio history
.venv-management/bin/python tools/manager.py command sfx-stable-audio status <생성ID>
```

`logs`, `active`, `cancel`, `resume`, `prioritize`, `history-delete`, `history-reset-preview`, `history-reset`도 같은 게이트웨이로 실행한다. 재개는 같은 ID 아래 새 실행 시도를 만든다. 우선 실행은 대기 중 작업만 이동하고 실행 작업을 선점하지 않는다.

공용 Gradio 이력의 결과 조회·입력 복원·재개·우선 실행·중지·선택 삭제를 사용한다. 삭제·전체 초기화는 Gradio **인라인 확인 영역**에서 대상·범위·복구 불가를 확인하며 모달이 아니다. 취소 시 무삭제이고 실행·대기·불명확한 경로는 서비스에서 거절한다. 초기화는 숨긴 작업 폴더도 검사하며 작업별 결과·로그·모든 시도와 색인을 함께 정리한다.

## 저장·측정 경계

- 모델·다운로드 캐시: `.model/music/sfx-stable-audio/` (공용 오디오 모델 루트).
- 생성 기록: `.tmp/test/sfx-stable-audio/<한국시간-생성ID>/`.
- 이력 색인: `.tmp/manager-current/sfx-stable-audio/`.
- 시도별 WAV: `attempts/<UUID>/sound.wav`; 조회 `/sfx-stable-audio/jobs/<ID>/attempts/<UUID>/sound.wav`.
- 기본값·반복 지시 원문: `generators/sound_effects/defaults.yaml`.

작업 서비스·기록·GPU 대기열·Gradio 이력은 기존 음악 생성기의 공용 오디오 흐름을 재사용한다. 효과음 추론 어댑터는 `generators/sound_effects/runtime.py`에 둔다. 모델·프롬프트 원문·단어 수·해시·시도별 오류를 보존한다. 재개 시 기본 설정 해시가 달라졌으면 새 작업을 요청한다.

공용 telemetry는 모델 준비·로드·추론·저장을 포함한 ETA와 현재/관측 피크 VRAM을 최대 5초 간격으로 기록한다. 근거가 없으면 ETA는 미정이며 같은 모델·길이·GPU·설정의 완료 표본을 사용한다. 다운로드 포함 실행은 추정 표본에서 제외한다. GPU 대기 시간은 별도다. 프로세스/자식 프로세스 관측치와 장치 전체 값을 구분하며 샘플 사이 순간 피크 누락 가능성과 측정 불가 사유를 표시한다. 완료·실패·취소 시 기록을 유지한다.

AWS 리소스·배포·고정 운영 비용을 추가하지 않는다. 실행 시 로컬 GPU·디스크를 사용하며 결과를 게임에 자동 전달하지 않는다.
