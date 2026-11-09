# Wan2.2 RGB V2V 생성기

기존 RGB MP4를 VAE로 인코딩하고 노이즈를 추가한 잠재값에서 다시 생성한다. Fun Control의 `control_video`에 RGB를 넣는 경로와 다르다. Wan2.2 T2V-A14B에 캐릭터 참조 이미지 조건은 연결하지 않는다. 입력 영상의 외형·동작 보존과 프롬프트에 따른 변화는 실험 대상이다.

- 화면: `/management/frame/wan22-v2v-generator/?tool=wan22-v2v-generator&category=animation-tool`
- 서비스: `wan22-v2v`, 공용 GPU 대기열·취소·재개·우선 실행·이력 삭제/초기화 사용
- 기록: `.tmp/test/wan22-v2v/<생성 ID>/`, 입력 사본 `input.mp4`, 시도별 `attempts/`, 결과 MP4·PNG ZIP
- 입력: 832×480 MP4 최대 32MiB, 앞에서부터 5~81프레임(4n+1), 원본 FPS 유지(1~60fps). 자동 반복·리사이즈·포즈 추출 없음. 오디오는 전달하지 않는다.
- 변경 강도: 0 초과 1 미만, UI 기본 0.3. 높이면 원본 손실도 커진다. 동작 역동성·캐릭터 정체성 개선을 보장하지 않는다.
- 스텝: 실험 기본 20, 2~50. 공식 예제 기본은 50이다.
- 고정: CFG 5, shift 5, 전문가 경계 0.875, BF16, 공식 타일 VAE. 고노이즈 전문가 사용 여부는 강도로 정해진 시작 timestep에 따른다. 기존 Fun Control의 자체 VAE 래퍼는 사용하지 않는다.
- 연산은 CUDA, 가중치는 공식 DiskMap을 이용한 디스크·CPU 오프로드. 양자화/임의 스케줄 변경 없음. **8GB 실제 추론은 미검증**이며 OOM 시 CPU 추론으로 대체하지 않는다.

## 공식 근거와 준비

[DiffSynth 파이프라인](https://github.com/modelscope/DiffSynth-Studio/blob/fdad57bd94d3fbac8a72c44920dd0a23b719ebb9/diffsynth/pipelines/wan_video.py)의 `input_video` / `denoising_strength`, [공식 Wan2.2 예제](https://github.com/modelscope/DiffSynth-Studio/blob/fdad57bd94d3fbac8a72c44920dd0a23b719ebb9/examples/wanvideo/model_inference/Wan2.2-T2V-A14B.py)를 사용한다. 이는 Wan2.2 모델 제작자가 전용 편집 모델 품질을 보장한다는 의미가 아니다.

모델은 `Wan-AI/Wan2.2-T2V-A14B` revision `c8c270b13ee05bfa474194ac9fb07a5868a97cea`, 런타임은 위 고정 commit이다. 기존 Fun Control GGUF는 다른 가중치이므로 사용하지 않는다. 신규 BF16 모델은 별도 디스크·호스트 RAM 공간이 필요하다.

기존 `.venv`에 공식 런타임 의존성을 준비한다. 새 가상환경을 만들지 않는다. 현재 환경에서 누락된 `entropack>=0.1.7` 등은 명시적으로 설치한 뒤 아래 준비 명령을 실행한다. 준비 스크립트는 누락 의존성을 자동 설치하지 않는다.

```bash
.venv/bin/python generators/wan_v2v/prepare.py
.venv/bin/python tools/manager.py command wan22-v2v model-status
.venv/bin/python tools/manager.py command wan22-v2v generate --payload-file /absolute/path/request.json
```

준비/추론은 GPU 접근 가능한 샌드박스 밖에서 실행한다. 준비 명령은 공식 소스를 `.local/wan-v2v/DiffSynth-Studio`에 고정하고, 가중치를 `.model/wan22-v2v`에 받아 파일 크기·SHA-256 준비 기록을 남긴다. 게이트웨이·GUI는 코드 반영 후 재시작해야 한다.

요청 JSON 필수 필드: `action: generate`, `input_video: <MP4 base64>`, `prompt`, `negative_prompt`, `denoising_strength`, `frames`, `steps`, `seed`, `width: 832`, `height: 480`. 다른 필드와 참조 이미지 입력은 거절한다. GUI와 CLI는 같은 검증·기록을 사용한다. 프롬프트는 가공하지 않고 원문·단어 수·해시를 보존한다. 예상시간·진행률·VRAM 관측 피크는 공용 작업자 기록을 사용하며 관측 근거가 없으면 계산 중으로 표시한다.
