# Fun Control VAE 처리

참조·포즈 인코딩과 결과 디코딩은 일반 ComfyUI VAE로 고정한다.
타일 VAE 실행·UI 선택은 제거했으며 OOM 시 자동 타일 대체 없이 명시적으로 실패한다.

이전 이력은 보존한다. 입력을 불러와 신규 생성하면 일반 VAE를 사용한다.
CLI 호환을 위해 `use_regular_vae: true`, `pose_encode_full_temporal: false`는 허용하지만,
타일 처리를 요청하는 반대 값은 접수 시 거절한다. 필드 생략도 일반 VAE다.
`encode-policy.json`, `decode-policy.json`에 실제 정책을 기록한다.
