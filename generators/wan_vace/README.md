# VACE-Fun 부분 편집 실험

## 영상 전체 조건 실험

`video_condition`은 RGB 원본 MP4와 외형 참조 PNG 1장을 입력한다. 모델에 전체 검정 마스크를
전달해 영상 전체를 조건으로 사용한다. 입력·출력은 자동 합성하지 않으며 자세·외형 보존과
셰이딩 개선은 보장하지 않는다. 사용자가 마스크를 입력하지 않으며 기존 부분 마스크 검증은
유지한다. GUI와 공용 게이트웨이는 동일한 `edit_video` base64를 사용하며 832×480·16fps·
32MiB 이하, 요청 프레임 이상이어야 한다. 8GB 실행 및 품질은 별도 검증한다.

`video_edit`는 완성된 원본 영상에서 지정 영역을 재생성하는 실험 모드다.
GUI·공용 게이트웨이 `wan22-vace generate`에서 기존 입력에 `mode: video_edit`,
`edit_video`, `edit_mask` MP4 base64를 추가한다. 외형 참조 `images`는 PNG 1장이다.
두 영상은 832×480·16fps·각 32MiB 이하이며 요청 프레임 이상이어야 한다.
마스크는 무채색이며 128 이상은 편집, 미만은 보존 조건으로 이진화한다.

공식 [마스크 편집 예제](https://github.com/aigc-apps/VideoX-Fun/blob/main/examples/wan2.2_vace_fun/predict_v2v_mask.py)의
`video`, `mask_video`, `subject_ref_images` 조합을 공식 파이프라인에 전달한다.
공식 pipeline의 `input_video = init_video * (mask_condition < 0.5)`에 맞춰
공식 파이프라인이 편집 영역을 정규화 중립값으로 지운다.
조건 강도는 전체 VACE 조건에 적용하며 얼굴 참조 전용 강도가 아니다.
원본과 자동 합성하지 않으므로 마스크 밖도 생성 결과에서 달라질 수 있다.

입력 사본 `edit-video.mp4`, `edit-mask.mp4`와 해시를 작업 폴더에 보존한다.
결과·로그·이력·GPU 측정은 기존 공용 작업 서비스에 저장한다.
원본·참조·편집 결과를 같은 프레임으로 비교하여 외형 개선과 동작 손실을 함께 평가한다.
영상·마스크를 불러온 뒤 다른 모드로 전환할 때는 두 첨부를 지워야 한다.

## 공식 비양자화 모델

공식 `alibaba-pai/Wan2.2-VACE-Fun-A14B` 리비전 `4438caabbfdd7437bbb0283d86cb200d1b7223ba`의 BF16 고·저노이즈 전문가를 고정한다. Q4 모델 생성·재개는 폐기했으며 이력은 보존한다. `python -m generators.wan_vace.prepare`는 고정 가중치·인코더·VAE와 공식 소스·토크나이저를 준비하고 크기와 SHA-256을 검증한다. 전문가 두 파일은 합계 69,350,650,000바이트다.

AMD ROCm에서 두 전문가·텍스트 인코더·VAE와 활성값은 GPU에 상주한다. CPU 오프로드나 자동 양자화 전환은 없다. GPU 메모리가 부족하면 실패하며 8GB 실행을 보장하지 않는다. 비양자화 경로의 전체 생성과 품질은 아직 검증되지 않았다.

## 키모도 DWPose 입력

`mode: pose`는 키모도의 처리된 DWPose MP4를 `pose_video` base64로 받는다.
캐릭터 외형 참조 PNG 1장을 `images`에 함께 전달한다. 영상은 832×480·16fps,
32MiB 이하이며 요청 프레임 이상이어야 한다. 재검출·프레임 반복을 하지 않는다.
`pose-video.mp4` 사본·SHA-256을 작업 폴더에 보존하고 이력에서 불러올 수 있다.
공식 `predict_v2v_control_ref.py`와 같이 `control_video`와 `subject_ref_images`,
빈 `video` 및 전체 생성 `mask_video`를 전달한다. 사용자 마스크는 받지 않는다.
GUI·CLI 모두 같은 `wan22-vace generate` 명령과 누적 이력을 사용한다.

화면의 기본 스텝은 20이다. 제작자 제어 예제의 50스텝은 비교 설정이며 필요할 때 고급 설정에서 직접 선택한다.

화면의 `제어 영상 + 참조 이미지 · 포즈`는 모델카드의 제어 영상과 참조 이미지 조합에 해당하며 현재 DWPose 입력만 받는다. 화면에 표시하는 생성 모드 이름은 입력 안내용이고 API의 `pose`, `reference`, `first_frame`, `text`, `video_edit`, `video_condition` 값은 유지한다. 각 모드를 선택하면 입력과 설정 안내가 바뀌며 설정값을 자동으로 변경하지 않는다.

## 공식 파이프라인 보존 정책

고정 공식 소스와 BF16 가중치를 사용하며 기본 실행에서 공식 수식과 스케줄러를 유지한다. 실험용 attention 격리 요청은 예외이며 실행 기록에 표시한다. 전문가를 포함한 모델과 활성값에 CPU 오프로드를 사용하지 않는다. 과거 Q4·오프로드 검증 결과는 현행 비양자화 모델의 실행 또는 품질 검증이 아니다.

### 초기 노이즈 통제 실험

공용 `wan22-vace generate --payload-file` 요청에 `noise_prefix_frames: 21`을
명시하면 `pose` 모드의 41프레임 작업에만 적용한다. 일반 GUI 생성에는 이 필드를
추가하지 않는다. 기본 경로는 그대로이며 실험 이력의 요청에 해당 값이 남는다.
동일 시드·CUDA·텍스트 인코더 dtype으로 21/41프레임 노이즈를 각각 생성한 뒤,
41프레임 노이즈의 첫 7개 잠재 슬롯(참조 1개 포함)을 21프레임 노이즈로 교체한다.
나머지 슬롯은 원래 41프레임 노이즈를 유지한다. 공식 파이프라인의 `latents`
인자를 사용하며 모델 연산은 바꾸지 않는다. 실행 시도에 `initial-noise.safetensors`와
형상·dtype·해시·공통 구간 일치를 담은 `noise-experiment.json`을 기록한다.
입력값 재사용 시 이 실험 필드를 누락하면 일반 실행이므로 기록을 구분해야 한다.

동일 요청에 `attention_prefix_frames: 21`을 추가하면 진단 전용으로 모든
self-attention에서 앞 7잠재 슬롯의 질의가 뒤쪽 슬롯을 참조하지 않게 한다.
뒤쪽 질의와 텍스트 cross-attention은 유지한다. 이는 공식 연산을 변경하는
원인 분리 실험이며 일반 생성의 품질 개선 옵션이 아니다. 실행 기록에
`official_math_unmodified: false`, `custom_math_patches: true`와
`attention-experiment.json`을 남긴다. `final-latents.safetensors`를 저장하고,
참조 슬롯을 제외한 앞 6잠재 슬롯을 별도로 디코딩한 21프레임 결과를
`comparison-prefix/`에 보관한다. 기본 GUI는 진단 필드를 추가하지 않는다.

분기 비교는 `attention_branch_scope: base`(본체) 또는 `vace`(제어 분기)를
추가한다. 생략하거나 `all`이면 두 분기를 제한한다. 고·저노이즈 전문가에
동일하게 적용하며 선택하지 않은 분기의 attention은 그대로 유지한다.

## AMD ROCm 실행 환경

공용 영상 작업자는 이미지 실행 환경 `.venv`를 사용한다. `./scripts/workflow.sh setup --scope image`로 ROCm·영상 패키지를 준비하고 모델·공식 소스는 관리도구 모델 준비에서 별도로 내려받는다. 환경 준비와 import 성공만으로 전체 생성·수치 정확도·영상 품질이 검증되는 것은 아니다.

ROCm PyTorch는 AMD GPU에서도 `torch.cuda`와 `cuda` 장치 이름을 사용한다. 실행은 BF16 지원 AMD GPU가 필요하며 GPU 백엔드·버전·모델 해시를 기록한다. 모델 및 활성값의 CPU 오프로드는 사용하지 않는다. AMD 전체 생성·메모리 한계는 별도 검증해야 한다.

CUDA 전환 시 데이터 단위·dtype·어텐션과 NaN 검증 절차는 [ROCm 추론 가이드](../../workflows/rocm-inference.md)를 따른다.

VAE 내부 인코딩 출력, 디코딩 제한 전 출력과 조건 텐서를 검사한다. 비유한 값은 단계·형상·stride·dtype을 작업의 `numerical-failure.json`에 기록하고 실패 처리한다. 검사는 GPU 동기화와 실행 시간에 영향을 줄 수 있다. 합성 CPU 테스트만 수행했으며 실제 ROCm VAE 정확도·생성·영상 품질은 검증하지 않았다.

VAE SDPA 진단은 작업자 환경에 `SLIME_VACE_VAE_SDPA_DIAGNOSTIC=1`을 명시할 때만 켜진다. 인코딩·디코딩 각각 첫 호출의 동일 Q/K/V와 마스크로 기본 경로 두 번과 수학 경로 한 번을 실행한다. 작업 시도 폴더의 `vae-sdpa-encode`·`vae-sdpa-decode` JSON에는 원래 shape·stride·dtype, 옵션, 환경, 유한값, 오차, 반복 차이와 시간이 남고 safetensors에는 입력과 마스크를 연속 배치로 저장한다. 실제 선택 커널은 미확인으로 기록한다. 이 진단은 추가 GPU 연산·동기화·입력 복사와 디스크 공간을 사용하며 타이밍·메모리 상태를 바꾼다. dropout이 있으면 반복 비교를 생략한다. 진단 입력은 작업 데이터이므로 Git에 등록하지 않는다. 이 기능은 합성 CPU 테스트만 수행했으며 VACE 실제 입력의 ROCm 비교 및 영상 생성·품질 검증은 수행하지 않았다.

VAE·조건·전문가·스케줄러·최종 출력에서 비유한 값이 감지되면 작업 시도에 `numerical-failure.json`과 가능한 경우 실패 텐서의 연속 CPU 사본 `numerical-failure.safetensors`를 보존한다. VAE 입력이 텐서이면 함께 저장하며 중첩된 출력의 위치와 원래 stride를 기록한다. 실패 텐서 복사는 추가 메모리와 디스크가 필요하다. Transformer 어텐션 실패 행의 수학 경로 비교는 명시적 SDPA이고 마스크·길이·별도 scale·부분 창 등 비교 의미를 바꾸는 옵션이 없을 때만 수행한다. 그 외는 미실행으로 기록한다. 합성 CPU 테스트만 수행했으며 ROCm 실생성과 정확도는 미검증이다.

선택적 어텐션 진단에서 출력이 비유한이면 해당 출력을 작업 시도에 보존하고 실패한다. 오차 통계는 큰 유한 FP32/BF16 출력의 뺄셈 오버플로를 피하려고 FP64로 계산하며 추가 GPU 메모리와 시간이 필요하다. 합성 CPU 테스트만 수행했으며 ROCm 실생성·정확도·품질은 별도 검증한다.
