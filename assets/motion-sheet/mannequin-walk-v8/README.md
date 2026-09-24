# 기본 걷기 모션 v8

선택한 생성 이력 `2026-09-24_22-04-47-42b7a56f`의 32프레임·4fps·4방향 모션이다. 기준 모델은 ANNY 39eab167. 기존 v1~v7의 기본 선택을 대체한다.

`mannequin-motion.npz`는 HumanML3D-22 Y-up 모션이며 `mannequin.blend`와 GLB는 ANNY104 리타기팅 결과다. `pose-sheets/` 및 `rig-sheets/`는 방향별 4열×8행, 512px 셀의 32프레임 참조다. 원본 프레임 픽셀을 그대로 배치했다. 파일 해시는 artifact.json을 따른다.

`humanml3d/`는 22관절 시각화이고, `pose-sheets/` 및 방향별 `openpose-*.png`는 ANNY 카메라 기반 COCO18 신체 맵이다. 코·눈·귀는 결측 처리하며 검출 결과로 표시하지 않는다. 기존 v7 파일은 제거하고 Git 이력으로 보존한다.
