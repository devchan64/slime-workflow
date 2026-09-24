# 기본 대기 모션 v3

사용자가 선택한 `2026-09-24_21-58-55-a17ffc87`의 16프레임·4fps·4방향 대기 모션. v2를 폐기하고 대체한다.

- `motion.npz`: 보정 적용 HumanML3D-22 Y-up 모션.
- `humanml3d/`: 원천 22관절 시각화. OpenPose가 아니다.
- `openpose/`: ANNY 카메라 투영 기반 COCO18 신체 맵. 코·눈·귀는 결측이며 검출 결과가 아니다.
- `anny/`: ANNY 39eab167 기준 리타기팅 리그와 결과 프레임.
- `standing-corrections.yaml`, `manifest.yaml`: 실제 보정값·출처·파일 해시.

기본 선택은 `generators/animation/config/default_standing_motion.yaml`에서 관리한다. 이전 v2는 Git 이력으로 보존하며 신규 생성에 사용하지 않는다.
