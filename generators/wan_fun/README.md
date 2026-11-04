# Fun Control VAE 처리

참조·포즈 인코딩과 결과 디코딩은 일반 ComfyUI VAE로 고정한다.
타일 VAE 실행·UI 선택은 제거했으며 OOM 시 자동 타일 대체 없이 명시적으로 실패한다.

이전 이력은 보존한다. 입력을 불러와 신규 생성하면 일반 VAE를 사용한다.
CLI 호환을 위해 `use_regular_vae: true`, `pose_encode_full_temporal: false`는 허용하지만,
타일 처리를 요청하는 반대 값은 접수 시 거절한다. 필드 생략도 일반 VAE다.
`encode-policy.json`, `decode-policy.json`에 실제 정책을 기록한다.

### 참조 이미지 + 프롬프트 모드

GUI의 생성 모드에서 `참조 이미지 + 프롬프트 · 실험`을 선택합니다. 참조 1장과 동작 프롬프트가 필수이며, 영상은 숨겨지고 요청에서 제외됩니다. 참조는 첫 프레임 고정이 아닌 외형 조건입니다. 동작과 캐릭터 유지 품질은 GPU 생성 실험 전까지 미검증입니다.

CLI JSON은 `input_mode: "reference-only"`, `images: [참조 PNG base64]`, `control_type: "pose"`를 사용하고 `pose_video`·`driving_video`는 생략합니다. 나머지 공통 파라미터는 동일합니다. 영상 동시 입력은 거절합니다. 모드 생략 시 기존 제어 입력 계약을 유지합니다. worker는 고정 ComfyUI `Wan22FunControlToVideo.execute`에 `control_video=None`을 전달합니다. 검은 영상이나 자체 제로 텐서를 만들지 않으며, 참조 조건·샘플러·노이즈 생성은 변경하지 않습니다.

### 걷기 예제와 프레임 확장

`걷기 예제 불러오기`는 `examples/walk-21frames-50steps/`의 참조 PNG·포즈 MP4·설정을 입력에 복원하며 자동 생성하지 않는다. 원본 작업은 `2026-11-02_23-24-48-85eb00f7`이며 21프레임·50스텝·시드 42·시프트 5·CFG 6·고노이즈 비율 0.3이다.

GUI·CLI 입력 범위는 5~129프레임(`4n+1`)으로 고정한다. 8GB 환경에서 129프레임·20스텝 생성 완료를 확인했다. 161프레임 실험은 첫 추론 스텝의 RoPE 연산에서 CUDA OOM으로 실패하여 지원 범위에서 제외했다. 생성 완료와 품질 승인은 별개다. 포즈 MP4는 요청 프레임 이상이어야 하며 부족한 프레임을 반복하지 않는다.
