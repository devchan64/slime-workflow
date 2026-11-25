# Wan 2.1 T2V 생성기

> **실험 종료:** Wan 2.1 모델 준비, 신규 생성과 재개는 지원하지 않는다. 전용 모델과 LoRA 파일은 정리했으며 기존 작업 이력은 조회할 수 있다. 아래 내용은 과거 실험 기록이다.


관리 화면의 **Wan 2.1 T2V 영상 생성**에서 모델을 준비한 뒤 프롬프트와 설정을 확인하고 GPU 대기열에 접수한다. 기본 가속 모드는 4스텝·CFG 1이며 KXSR을 쓰려면 아래 파일이 필요하다. 모델과 출력은 실험 단계다.

## 별도 Diffusers CLI

`generate.py`는 로컬 Diffusers 형식 Wan 2.1 T2V 1.3B 모델과 선택한 LoRA로 MP4를 생성하는 독립 CLI이다. 이 CLI는 관리 GUI와 공용 GPU 대기열을 사용하지 않으므로 다른 GPU 작업과 동시에 실행하지 않는다. 별도의 관리 화면은 ComfyUI 형식 모델과 공용 대기열 작업자를 사용한다. ROCm/CUDA PyTorch, Wan을 지원하는 diffusers, transformers, accelerate, peft와 영상 저장 의존성이 필요하다. 모델과 LoRA는 별도로 준비한다.

```bash
python generators/wan21_t2v/generate.py \
  --model /path/to/Wan2.1-T2V-1.3B-Diffusers \
  --boss-lora /path/to/kxsr-1.3b.safetensors \
  --prompt 'kxsr, a spear warrior fights a giant armored monster in a ruined arena, wide shot, both hands gripping the long spear, a thrust followed by a sweeping strike' \
  --output /tmp/boss-fight.mp4
```

기본값은 832×480, 73프레임, 40스텝, CFG 3.5, shift 4, 16fps다. KXSR은 `kxsr` 트리거를 사용한다. 1.3B의 480p가 공식 권장이다. `--accelerator-lora`로 1.3B용 가속 LoRA를 추가할 수 있으나 스텝·CFG·스케줄러는 해당 LoRA의 조건에 맞춰야 하며 KXSR과 동시 적용한 품질 및 호환성은 미검증이다. 14B 전용 Lightning을 1.3B에 사용하지 않는다.

현재 CLI 도움말만 확인했다. GPU 추론, LoRA 키 형식 및 실제 출력은 검증하지 않았다. 특히 4-step DMD LoRA는 제공자가 별도 LightX2V 샘플러를 지정하므로 이 CLI에서의 사용을 보장하지 않는다. 파일과 모델을 자동 다운로드하지 않는다.

참고: [KXSR 모델 설명](https://www.seaart.ai/ja/models/detail/a974a14de11b76ad1cc6497674ca9989), [Wan 공식 모델](https://github.com/Wan-Video/Wan2.1), [1.3B 4-step DMD LoRA](https://huggingface.co/Perflow-Shuai/Wan2.1-T2V-1.3B-NonAR-DMD-4Step-LoRA-r64-iter1600-Teacher14B), [Wan 2.1 I2V Fight LoRA](https://huggingface.co/joyfox/Wan2.1-Fight-LoRA). 마지막 모델은 14B I2V에서 두 사람의 맨손 격투용이며 장병기 전용으로 검증되지 않았다.

## 고정 파일 준비 작업

관리 모델 준비 프로필 `wan21-t2v-assets`는 ComfyUI 형식의 1.3B 본체와 [Self-Forcing 1.3B 가속 LoRA](https://huggingface.co/Kijai/WanVideo_comfy/tree/main/LoRAs/Wan2_1_self_forcing_1_3B)를 SHA-256으로 검증해 별도 디렉터리에 준비한다. 위 Diffusers CLI는 이 단일 파일 형식을 아직 직접 사용하지 않는다. KXSR 파일은 이 프로필에서 다운로드하지 않으며 별도로 등록한다. Self-Forcing과 KXSR 동시 적용 및 출력 품질은 미검증이다.

관리 화면의 KXSR 파일 경로는 `.model/wan21-t2v/action/kxsr.safetensors`이다. 등록 도구와 모델 준비 검사는 아래의 고정 SHA-256을 확인한다. KXSR의 실제 모델 적용과 GPU 출력은 미검증이다.

2026-11-23 고정 본체와 Self-Forcing LoRA의 safetensors 헤더를 비교해 LoRA·직접 가중치·편향 793개 대상 모두 본체 이름 및 텐서 크기가 맞는 것을 확인했다. 이는 파일 구조 검사이며 ComfyUI 패치 적용, 생성 속도 및 영상 품질 검증은 아니다.

같은 날 ComfyUI CPU/meta 모델 구성에서 Self-Forcing LoRA의 793개 패치가 모두 등록되는 것까지 확인했다. 이 구조 검사만으로는 GPU 출력이나 KXSR 조합을 확인할 수 없다.

2026-11-23 ROCm에서 832×480, 5프레임, 4스텝, CFG 1, Self-Forcing 가속 LoRA로 한 회 실행해 793개 패치 등록과 5프레임 MP4 저장을 확인했다. KXSR 미포함 짧은 동작 시험이며 영상 품질은 별도 검수 대상이다.

KXSR 대상은 Civitai 모델 1392349, 버전 1573723의 `wan-1.3B-Bossfight.safetensors`다. [ModelTrends 공개 색인](https://modeltrends.ai/v1/model/55b08a21.json)에 기재된 SHA-256 `be4273230a772e8132cb2b24258fc6f06ab59361e405a7e694e3b4a2299846c4`과 파일을 대조하며, 일치하지 않으면 실행하지 않는다. 2026-11-23 사용자가 제공한 파일의 해시와 모델 준비 상태를 확인했으며, 실제 모델 적용과 영상 출력은 아직 확인하지 못했다.

이미 보유한 파일을 안전하게 등록하려면 작업 공간에서 `python3 -m generators.wan21_t2v.import_kxsr /path/to/wan-1.3B-Bossfight.safetensors`를 실행한다. 일반 파일과 SHA-256을 확인한 뒤에만 지정 위치에 원자적으로 등록하고 기존 파일은 덮어쓰지 않는다.

73프레임 기준 시험(2026-11-23, 832×480, 4스텝·CFG 1, Self-Forcing, seed 43)은 네 단계의 유한값 검사와 MP4 저장을 통과했다. 선택한 0·36·72프레임에서 거대한 갑옷 보스와 이를 마주한 인물이 보이지만, 이 시험에는 KXSR이 포함되지 않아 해당 LoRA의 효과나 무기 접촉 정확도는 검증하지 못했다. 5초 간격 표본의 작업 프로세스 GPU 메모리 최고치는 38,281 MiB였으며 순간 피크를 보장하지 않는다.
