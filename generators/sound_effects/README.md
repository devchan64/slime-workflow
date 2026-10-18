# Dasheng-AudioGen 효과음 생성

소리 관리 → Dasheng-AudioGen · 효과음에서 실행한다.
주소: `http://127.0.0.1:8770/management/frame/sfx-dasheng-audiogen/?tool=sfx-dasheng-audiogen&category=sound-management`

- 고정 모델: `mispeech/Dasheng-AudioGen`. 영어 소리 설명·시드·반복 요청·태그를 입력한다.
- 길이는 모델이 예측한다. `duration_seconds`는 생략하거나 null이어야 하며 숫자를 지정하면 거절한다. 자동 잘라내기·연장 없이 실제 길이를 기록한다.
- 최종 입력은 `<|caption|>` 태그와 사용자 설명, 선택한 반복 환경음 문구다. 실제 입력의 단어 수·해시를 기록한다.
- 출력은 16kHz mono PCM16 `sound.wav`다. 스테레오·44.1kHz로 표시하거나 변환하지 않는다. 심리스 루프를 보장하지 않는다.
- 25스텝·CFG 5·batch 1·BF16 CUDA 추론. 텍스트 인코더 → DiT → 디코더 순서로 GPU에 올리고 나머지 가중치는 CPU RAM에 대기시킨다. CPU 모델 연산은 거절한다. 8GB 동작·음질은 실제 생성으로 검증해야 한다.

## 준비와 실행

```bash
.venv-management/bin/python generators/sound_effects/setup_runtime.py
.venv-management/bin/python tools/manager.py command sfx-dasheng-audiogen prepare
.venv-management/bin/python tools/manager.py command sfx-dasheng-audiogen generate --prompt 'A single boxing glove punch, a sharp smack and a heavy thud.' --seed 42 --tag '권투 타격음 실험' --detach
.venv-management/bin/python tools/manager.py command sfx-dasheng-audiogen history
.venv-management/bin/python tools/manager.py command sfx-dasheng-audiogen status <생성ID>
```

`.venv-sfx-dasheng`은 Python 3.12·PyTorch 2.8 CUDA 12.8·Transformers 4.57 전용 환경이다. 모델 본체·텍스트 인코더·오디오 토크나이저의 revision을 `runtime.py`에서 고정하고 `.model/music/sfx-dasheng-audiogen/`에 준비한다. 로컬 원격 코드도 파일 해시를 검증한 뒤 실행한다. 생성 시에는 로컬 파일만 로드한다.

공용 GUI·CLI → 게이트웨이 → 음악 작업 서비스 → GPU 실행기·기록 저장소를 재사용한다. `prepare/model-status/generate/status/logs/history/active/cancel/resume/prioritize/history-delete/history-reset-preview/history-reset`을 지원한다. 생성 이력 표는 썸네일 컬럼을 표시하지 않으며 선택 행동·삭제 확인·청취·다운로드는 공용 구성요소를 사용한다.

기록은 `.tmp/test/sfx-dasheng-audiogen/<생성ID>/`, 이력 색인은 `.tmp/manager-current/sfx-dasheng-audiogen/`에 저장한다. WAV는 `attempts/<UUID>/sound.wav`다. 공용 실행기가 5초 heartbeat·ETA·VRAM 관측 피크와 실패·취소·재개 시도를 기록한다. 길이 자동 예측으로 예상 소요 시간의 편차가 클 수 있으며 표본이 없으면 미정으로 제공한다. 이력 삭제는 확인 후 해당 작업 파일까지 삭제하며 외부 원본·모델은 보호한다.

## 라이선스와 폐기 경계

공식 본체 [Dasheng-AudioGen](https://huggingface.co/mispeech/Dasheng-AudioGen), [FLAN-T5-large](https://huggingface.co/google/flan-t5-large), [Dasheng Tokenizer](https://huggingface.co/mispeech/dashengtokenizer)는 Apache-2.0으로 공개되어 있다. 소프트웨어·가중치 재배포 시 해당 라이선스와 고지를 보존한다. 생성물 권리와 품질을 별도로 검수한다.

`Stable Audio 3 Small SFX`의 `sfx-stable-audio` 서비스·메뉴·GUI 진입점은 폐기한다. 기존 `.tmp/test/sfx-stable-audio/`, 이력 색인·모델 캐시·가상환경은 자동 삭제하거나 Dasheng 기록으로 이동하지 않는다. 이전 작업을 새 모델로 재개하지 않으며 Dasheng 작업을 새로 등록한다. 음악용 `music-stable-audio` 역시 폐기 상태다.

## 검증

공용 자동 회귀 실행기로 `tools.review.tests.test_dasheng_audio_sfx`, `test_music_generation`, `test_music_management_audit`, `test_management_gateway`, `test_management_runtime`을 검사한다. 격리 테스트는 운영 GPU 작업을 생성·취소하지 않는다. 실모델 출력과 실제 8770 화면 검증은 별도로 보고한다.
