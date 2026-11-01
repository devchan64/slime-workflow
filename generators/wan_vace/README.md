# VACE-Fun 부분 편집 실험

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

## 공식 실행부 전환 검증

공식 소스 커밋 `13bb3c625e8b1e457d7124d92207b49e00e4a6fe`와 기존
QuantStack 리비전 `93b339260b1d819e2c171dd7ca9e66a761d4a84d`를 유지한다.
`official_gguf.py`는 공식 모델 구조에 기존 GGUF를 연결한다. 양쪽 전문가의
1,331개 텐서 이름·형상을 엄격히 검사하며 Q4_K·Q6_K는 바이트를 CPU에
보관하고 계층별 CUDA FP32 역양자화 후 BF16 행렬 연산을 수행한다.
GGUF를 새로운 정밀도로 재양자화하지 않는다. UMT5는 기존 BF16 원본을
공식 인코더에 strict 로드하고 Accelerate 계층 오프로드로 CUDA에서 연산한다.
VAE도 기존 가중치를 공식 모델에 strict 로드한다.

공식 소스·토크나이저 파일 해시와 검증 환경 패키지 버전은
`config/official-runtime.yaml`에 기록한다. 공식 파이프라인과 별도 GGUF
연결부를 사용하므로 BF16 공식 예제와 동일한 수치 결과를 의미하지 않는다.
`official_prepare.py`는 고정 소스·토크나이저를 준비하며 전체 BF16 확산 모델을
다운로드하지 않는다. 작업 실행부는 공식 파이프라인을 사용한다.
공식 `VIDEOX_OFFLOAD_VACE_LATENTS=1` 옵션으로 제어 중간 텐서를 CPU에 보관하며
모델 연산은 CUDA에서 수행한다. 시간축 분할 VAE 래퍼는 사용하지 않는다.

2026-11-01 검증: 832×480 영상 부분 편집 21프레임·2스텝이 약 111초에 완료됐다.
공식 제어 텐서 오프로드와 디코딩 전 확산 모델 CPU 이동을 적용했다.
이는 실행 검증이며 20/50스텝 잔상·외형 품질과 81프레임 실행은 미검증이다.

## 키모도 DWPose 입력

`mode: pose`는 키모도의 처리된 DWPose MP4를 `pose_video` base64로 받는다.
캐릭터 외형 참조 PNG 1장을 `images`에 함께 전달한다. 영상은 832×480·16fps,
32MiB 이하이며 요청 프레임 이상이어야 한다. 재검출·프레임 반복을 하지 않는다.
`pose-video.mp4` 사본·SHA-256을 작업 폴더에 보존하고 이력에서 불러올 수 있다.
공식 `predict_v2v_control_ref.py`와 같이 `control_video`와 `subject_ref_images`,
빈 `video` 및 전체 생성 `mask_video`를 전달한다. 사용자 마스크는 받지 않는다.
GUI·CLI 모두 같은 `wan22-vace generate` 명령과 누적 이력을 사용한다.

## 공식 파이프라인 보존 정책

[모델카드](https://huggingface.co/alibaba-pai/Wan2.2-VACE-Fun-A14B)가 안내하는
VideoX-Fun 공식 파이프라인을 고정 소스 해시로 검증한다.
허용되는 구현 차이는 CPU 가중치 오프로드와 고정 Q4_K_M 모델 연결이다.
RoPE·FFN·잔차 연산 분할 및 AST forward 재작성은 제거했다.
스케줄러 step 교체와 자동 단계별 진단 실행도 제거했다.
공식 텍스트 인코딩·VACE 조건 구성·난수 생성·전문가 전환·VAE 연산을 유지한다.
CPU 오프로드는 계층 forward 전후의 가중치 이동만 수행하며 연산은 CUDA에서 한다.
공식 구현의 VACE 잠재 CPU 오프로드 옵션은 보관 위치만 변경한다.

기존 93프레임 실행 성공은 제거된 연산 패치가 포함된 기록이므로 현재 경로의
8GB 실행 보장으로 사용하지 않는다. OOM 발생 시 프레임·해상도·연산을
자동 변경하지 않는다. 양자화 어댑터는 BF16 원본과 동일 출력 보장이 아니며
가중치 이름·형상·지원 자료형 검증을 유지한다. 이전 진단·결과 파일은 보존한다.
