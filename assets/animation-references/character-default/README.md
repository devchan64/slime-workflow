# 캐릭터 애니메이션 참조 자산

이 폴더는 3참조 Qwen 포즈 전환 배치에서 재사용하는 방향별 참조 이미지다.

- `baseline-v2/`: 승인된 2×2 베이스라인에서 분할한 512×512 방향별 아이덴티 셀
- `../../rigs/mannequin-walk/v1/pose-sheets-v1/`: 통합 관리되는 2048×1024 OpenPose 4×2 시트

생성 목록과 참조 경로는 `generators/animation/config/pose_transfer_3_reference_qwen_default_walk.yaml`에서 워크플로 루트 기준 상대 경로로 관리한다. 입력 자산을 변경할 때는 실행 목록과 해시를 함께 갱신한다.
