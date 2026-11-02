# Fun Control 포즈 시간 인코딩 진단

처리된 `pose_video` 요청에 `pose_encode_full_temporal: true`를 명시하면
포즈 VAE 인코딩의 시간 타일을 입력 전체 길이로 설정한다. 기본은 기존 9프레임이다.
공간 타일·샘플링·디코딩은 유지하며 `encode-policy.json`에 기록한다.
공용 게이트웨이 `generate --payload-file`로 실행하는 진단 필드이며 GUI 기본값에는
추가하지 않는다. GUI에서 입력을 다시 불러온 실행은 이 진단 필드를 보존하지 않는다.

`use_regular_vae: true`는 참조·포즈 인코딩과 결과 디코딩 모두 일반 ComfyUI
VAE 경로를 사용한다. 이때 `pose_encode_full_temporal`은 적용되지 않는다.
OOM 시 자동 타일 대체는 명시적 오류로 차단한다. 두 정책 JSON에 실제 경로를 기록한다.
이 필드 역시 GUI 기본값이나 입력 복원에는 추가하지 않는 진단 옵션이다.
