# MiniMax H3 I2V 사용설명

첫 프레임 이미지 한 장과 장면·동작 프롬프트로 영상과 오디오를 생성합니다. 이미지는 흰 여백을 넣어 화면에 맞춥니다. 기본 설정은 832×480, 124프레임(24fps, 약 5.17초), Turbo 8스텝이며 시드를 지정하거나 랜덤으로 선택할 수 있습니다. 480p 설정으로 두 차례 생성에 성공했으며 동작 품질은 입력에 따라 달라집니다. 기존 768×448 이력은 계속 열 수 있습니다. 두 해상도는 모델의 일반적인 학습 해상도보다 낮은 실험 설정입니다.

입력을 확인한 뒤 생성 요청을 검토하고 GPU 대기열에 추가합니다. 현재 작업과 예상 시간, 저장된 작업 이력, 결과 영상 및 프레임 ZIP을 같은 화면에서 확인할 수 있습니다. 생성된 동작과 품질은 결과를 직접 검수해야 합니다.

## 프롬프트 작성

[MiniMax 공식 프롬프트 가이드](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/references/base-en.txt)는 첫 이미지 기반 생성에서 **첫 이미지의 구도와 자세 → 동작 시작 → 이어지는 동작 → 마무리 자세** 순서로 묘사하도록 안내합니다. 이미지에서 유지할 인물, 의상, 소품, 위치를 밝히고 카메라와 동작의 순서도 구체적으로 적습니다. 동시에 일어나야 하는 동작은 그 관계를 직접 설명합니다.

공식 가이드는 영상에 보일 내용을 `integrated_multimodal_description`, 장면 속 소리를 `overall_soundscape`, 배경 음악을 `non_diegetic_music`으로 구분하는 형식을 제시합니다. 생성기의 프롬프트 입력란에 해당 형식을 직접 작성할 수 있습니다. 가이드의 첫 프레임 표기 `<Picture 1>`을 이 Diffusers 실행 경로에서 별도 토큰으로 처리하는지는 검증하지 않았습니다. 실제 기준 이미지는 이미지 선택란에 넣어야 합니다.

예를 들어, 한 걸음 전진하며 내려베는 동작은 다음처럼 작성할 수 있습니다.

```text
integrated_multimodal_description: [Shot 1] A full-body sword fighter in the reference image faces right against a plain white background. The camera holds a static side view. The fighter pushes off the rear foot and steps forward. As the foot travels, the hips and center of mass move forward and the right arm raises the sword overhead. While still stepping, the fighter makes one vertical downward slash, driven by the forward weight shift and rotation of the hips and torso. The advancing foot plants as the sword comes down, and the fighter follows through into a low, balanced stance. The steel sword remains in the right hand; the entire body and sword stay visible.

overall_soundscape: A footstep and clothing movement accompany the step, followed by the sound of the sword moving through the air.

non_diegetic_music: N/A
```

이 예시는 공식 형식을 적용한 시험안이며 생성 결과가 검증된 프롬프트는 아닙니다. 음악을 원하면 `non_diegetic_music`에 악기와 속도 등을 설명하고, 음악이 필요하지 않으면 예시처럼 `N/A`를 사용합니다. 모델이 소리를 생성하므로 전체 무음을 원할 때만 소리 항목에 무음을 명시합니다.

## 확인한 사용 경험

2026-11-24 Radeon 8060S에서 768×448 검술 시험은 발 전진과 검 들기가 나왔지만 내려베기는 완성되지 않았습니다. GPU 대기 제외 실행은 약 10분 20초였습니다.

같은 날 832×480 한손검 시험에서는 뒷발 전진과 수직 내려베기가 나왔습니다. 해당 생성은 약 17분 13초가 걸렸습니다. 한 차례 결과이므로 다른 입력의 품질을 보장하지 않습니다. 공식 형식으로 작성한 위 시험안의 효과는 아직 확인하지 않았습니다.

## 모델과 준비

Hugging Face Diffusers 0.43.0, MiniMax H3 FL2VA FP8 저장·GPU BF16 계산, INT8 텍스트 인코더, LightX2V Turbo 8스텝 LoRA, 공식 영상·오디오 VAE를 사용합니다. ROCm GPU에서 연산하며 CPU 추론이나 모델 오프로딩으로 자동 전환하지 않습니다. 파일 크기와 고정 런타임을 준비 상태에서 확인하고, 실행 시 모델 파일 SHA-256을 확인합니다. 구성요소가 없으면 준비 상태에 표시하며 자동으로 다른 모델을 사용하지 않습니다.

MiniMax H3 및 파생 가중치는 MiniMax H3 Community License와 개별 사용 허가 조건을 따릅니다. 기존 허가는 허가받은 사용자의 신청 내용에 따른 것으로, 타인에게 허가가 이전되는 것은 아닙니다. H3 출력은 관련 라이선스 조건에 따라 취급하세요.

## 헤르메스 대화 자동 보고

헤르메스 대화에서 제안을 확인하고 접수한 작업은 생성 완료 후 원 대화에 분석 보고서를 전달합니다. 생성 상태와 보고 상태는 별도로 표시합니다. 시각 모델을 사용할 수 없으면 관찰 불가로 기록하며, 영상 분석은 최종 MP4의 시작·중간·끝 표본과 첫 참조를 사용하므로 전체 동작과 재생 품질을 보증하지 않습니다. 오디오는 파일 정보만 확인하며 내용은 분석하지 않습니다. 독립 생성기에서 접수한 작업은 대화에 자동 연결하지 않습니다.

보고서 작성이 실패했거나 시각 관찰이 불가능했던 경우 대화의 보고 상태에서 재분석할 수 있습니다. 재분석은 생성 결과를 다시 만들지 않으며, 이전 보고서가 있으면 대화에 유지합니다. 시스템 메모리가 부족하면 분석을 대기하고 상태에 사유를 표시합니다.
