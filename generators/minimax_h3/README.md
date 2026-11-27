# MiniMax H3 FL2VA 사용설명

이 생성기는 MiniMax H3 FL2VA 모델로 영상과 오디오를 생성합니다. 텍스트만, 첫 프레임, 마지막 프레임, 첫·마지막 프레임 모드를 선택할 수 있습니다. 길이는 124~345프레임 중 17프레임 간격으로 선택합니다. 첫·마지막 프레임 모드는 124·192프레임 GPU 생성이 완료됐습니다. 텍스트만·마지막 프레임 단독 모드와 그 밖의 길이는 실제 GPU 실행 검증 전의 실험 기능입니다. 이미지는 흰 여백을 넣어 화면에 맞춥니다. 기본 설정은 832×480, 124프레임(24fps, 약 5.17초), Turbo 8스텝이며 시드를 지정하거나 랜덤으로 선택할 수 있습니다. 480p 설정으로 두 차례 생성에 성공했으며 동작 품질은 입력에 따라 달라집니다. 기존 768×448 이력은 계속 열 수 있습니다. 두 해상도는 모델의 일반적인 학습 해상도보다 낮은 실험 설정입니다.

입력을 확인한 뒤 생성 요청을 검토하고 GPU 대기열에 추가합니다. 현재 작업과 예상 시간, 저장된 작업 이력, 결과 영상 및 프레임 ZIP을 같은 화면에서 확인할 수 있습니다. 생성된 동작과 품질은 결과를 직접 검수해야 합니다.

## 모델 기능과 현재 생성기 입력 정의

이 생성기는 특정 캐릭터나 동작에 종속되지 않는 범용 영상·오디오 생성기입니다. 아래 모델 기능은 [MiniMax H3 공식 모델 카드](https://huggingface.co/MiniMaxAI/MiniMax-H3)와 [Diffusers 문서](https://huggingface.co/docs/diffusers/main/en/api/pipelines/minimax_h3)를 기준으로 하며, 현재 화면과 CLI에서 제공하는 범위는 별도로 표시합니다.

| 입력 또는 기능 | FL2VA 모델 계열 | 현재 생성기 |
|---|---|---|
| 텍스트 프롬프트 | 생성 내용을 설명하는 입력 | **필수**: 비어 있지 않은 프롬프트 |
| 첫 프레임 이미지 | 선택: 첫 프레임 조건으로 사용 가능 | 첫 프레임·첫/마지막 모드에서 **필수**, 832×480 PNG |
| 마지막 프레임 이미지 | 선택: 단독 또는 첫 프레임과 함께 지정 가능 | 마지막 프레임·첫/마지막 모드에서 **필수**; 첫/마지막 모드 GPU 생성 확인, 마지막 단독은 미검증 |
| 이미지 없는 텍스트 기반 생성 | 지원 | 텍스트만 모드, GPU 검증 전 |
| 영상 길이 | 모델 카드상 4~15초, 24fps. 실행 프레임 제약은 사용 파이프라인에 따름 | **선택**: 124~345프레임, 17프레임 간격, 24fps. 124·192프레임 GPU 생성 확인, 다른 길이는 미검증 |
| 해상도 | 모델 카드상 기본 짧은 변 768px; 전체 H3 시스템의 2K는 별도 재생성 단계 | **고정 설정**: 기본 832×480, 기존 768×448 이력 호환. 2K 재생성 미지원 |
| 스텝과 시드 | 실행 환경과 모델 변형에 따라 다름 | **고정**: Turbo 8스텝. **선택**: 시드 지정 또는 랜덤 |
| 결과 | 영상과 오디오 | 영상·오디오 및 프레임 출력; 결과 품질은 사용자 검수 필요 |

모델 카드의 기능은 이 환경에서의 실행 성공을 보장하지 않습니다. 첫·마지막 프레임 모드는 124·192프레임 생성이 완료됐으나, 텍스트만·마지막 단독과 다른 길이는 GPU 실행 검증 전입니다. 메모리 부족이나 실행 실패가 발생할 수 있습니다. 특정 인물, 포즈, 무기, 카메라, 배경은 사용자가 프롬프트와 이미지로 지정하는 예시이며 생성기 필수 조건이 아닙니다. FL2VA는 시작·끝 프레임을 조건으로 사용하는 생성 방식이며, 정확한 픽셀 일치나 중간 동작을 보장하지 않습니다.

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
