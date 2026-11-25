# Wan 2.1 I2V 생성기

> **실험 종료:** Wan 2.1 모델 준비, 신규 생성과 재개는 지원하지 않는다. 전용 모델과 LoRA 파일은 정리했으며 기존 작업 이력은 조회할 수 있다. 아래 내용은 과거 실험 기록이다.


관리 화면의 **Wan 2.1 I2V 영상 생성**에서 모델과 첫 프레임을 준비한 뒤 프롬프트와 설정을 확인하고 GPU 대기열에 접수한다. 기본 가속 모드는 4스텝·CFG 1이다. Attack Sprite는 별도 준비 항목의 실험용 동작 LoRA다.

## 별도 Diffusers CLI

`generate.py`는 Wan 2.1 I2V 14B Diffusers 모델과 첫 이미지, 프롬프트 및 선택적인 호환 I2V LoRA를 사용한다. T2V 1.3B와 모델 디렉터리 및 실행기를 공유하지 않는다. 이 CLI는 관리 GUI와 공용 GPU 대기열을 사용하지 않으므로 다른 GPU 작업과 동시에 실행하지 않는다. 별도의 관리 화면은 ComfyUI 형식 모델과 공용 대기열 작업자를 사용한다.

```bash
python generators/wan21_i2v/generate.py \
  --model /path/to/Wan2.1-I2V-14B-480P-Diffusers \
  --image /path/to/first-frame.png \
  --prompt 'A warrior grips a long spear with both hands, steps toward a giant boss, and thrusts. Wide shot, the whole spear remains visible.' \
  --output /tmp/i2v.mp4
```

이미지는 지정한 크기로 늘여 맞춘다. 기본값은 832×480, 81프레임, 40스텝, CFG 5, shift 5, 16fps다. `--lora`로 해당 모델에 호환되는 로컬 LoRA를 지정할 수 있다. T2V 1.3B KXSR LoRA는 이 I2V 모델용이 아니다. [Wan2.1 Fight LoRA](https://huggingface.co/joyfox/Wan2.1-Fight-LoRA)는 14B 720p I2V용 맨손 격투 후보이며, 장병기 동작이나 480p 모델 호환성을 검증하지 않았다.

ROCm/CUDA PyTorch, Wan을 지원하는 diffusers, transformers, accelerate, peft와 영상 저장 의존성 및 별도로 준비한 Diffusers 형식 모델이 필요하다. 자동 다운로드는 하지 않는다. 도움말과 파이썬 문법만 확인했으며 GPU 추론과 LoRA 적용은 미검증이다.

관리 모델 준비 프로필 `wan21-i2v-assets`는 ComfyUI 형식의 480p 본체, 비전 인코더 및 가속·격투 LoRA를 고정 해시로 준비한다. 위 Diffusers CLI는 이 단일 파일 형식을 아직 직접 사용하지 않는다. 후보별 모델 버전과 실험 제약은 [LoRA 조사](LORA_RESEARCH.md)를 참조한다.

2026-11-23 다운로드한 480p 본체와 I2V 가속 LoRA의 1,262개 대상, Fight LoRA의 480개 대상에 대해 safetensors 헤더의 이름과 텐서 크기가 맞는 것을 확인했다. 이는 구조 검사이며 실제 패치 적용·영상 품질 또는 무기 동작의 검증은 아니다.

같은 날 ComfyUI CPU/meta 모델 구성에서 가속 1,262개와 Fight 480개 패치를 단독 및 연속 등록하는 것을 확인했다. 이는 실제 GPU 샘플링이나 480p·무기 동작 품질 검증이 아니다.

관리 화면에서 공격 동작 LoRA를 선택할 수 있다. Attack Sprite high/low는 창 공격 예시가 있는 Wan 2.2 학습 파일이며 2.1용 실험 옵션이다. 두 파일의 400개 패치 등록과 high의 가속 LoRA 조합 GPU 출력을 확인했으나, 제한된 표본에서 무기 동작은 요청과 일치하지 않았다. 파일 준비는 별도의 `wan21-i2v-attack-lora` 항목에서 진행한다.

2026-11-23 ROCm에서 합성 시험 이미지, 832×480, 5프레임, 4스텝, CFG 1, 가속 LoRA로 한 회 실행해 1,262개 패치 등록과 5프레임 MP4 저장을 확인했다. 공격 LoRA 미포함 짧은 시험이며 실제 무기 동작 품질은 확인하지 못했다.

합성 그림을 입력한 21프레임 GPU 시험에서 가속 1,262개와 Attack Sprite high 400개 패치의 동시 등록 및 MP4 저장을 확인했다. 시험 입력이 단순 도형이라 이를 실제 창 전투 품질의 검증으로 보지는 않는다.

창 기준 이미지 한 장으로 Attack Sprite high를 비교한 21프레임 표본에서 강도 0.45는 마지막 프레임의 창끝이 보였지만 창 방향이 바뀌어 지시한 찌르기와 달랐다. 강도 0.8 표본에서는 마지막 창끝이 보이지 않았다. 한 시드의 제한된 시각 검토이며 결과는 이력에서 직접 확인해야 한다.

같은 창 이미지와 시드의 가속 LoRA 단독 대조에서는 관찰한 마지막 프레임까지 창끝과 오른쪽 방향이 유지됐다. Attack Sprite high 적용 두 표본의 마지막 방향 변경·창끝 가림과 비교해 볼 수 있으나, 한 시드의 제한된 검수 결과다.
