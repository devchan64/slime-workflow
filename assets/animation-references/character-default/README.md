# 캐릭터 애니메이션 참조 자산

이 폴더는 3참조 Qwen 포즈 전환 배치에서 재사용하는 방향별 참조 이미지다.

- `baseline-v2/`: 승인된 2×2 베이스라인에서 분할한 512×512 방향별 아이덴티 셀
- `../../rigs/mannequin-walk/v1/pose-sheets-v1/`: 통합 관리되는 2048×1024 OpenPose 4×2 시트

생성 목록과 참조 경로는 `generators/animation/config/pose_transfer_3_reference_qwen_default_walk.yaml`에서 워크플로 루트 기준 상대 경로로 관리한다. 입력 자산을 변경할 때는 실행 목록과 해시를 함께 갱신한다.

## 기준 시트 원본

`baseline-source-v2/`는 프론트엔드에서 이관한 승인된 2×2 기준 시트와 셀 좌표·출처 sidecar다. `manifest.yaml`의 `baseline_source.path`는 manifest 디렉터리 기준 상대 경로이며 해시로 원본을 검증한다. `baseline-v2/`의 방향별 참조와 구분한다. 게임 런타임에서 사용하지 않는다.
