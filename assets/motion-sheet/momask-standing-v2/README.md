# MoMask 대기 모션 v2

승인된 생성 이력 `2026-09-24_20-31-23-13336ffa`를 재사용 제작 에셋으로 등록했다. 16프레임·4fps·4초·4방향이며 샘플링하지 않는다.

- `motion.npz`: MoMask에서 생성하고 대기 보정을 적용한 HumanML3D-22 관절 모션. 보정 이전 원본으로 표시하지 않는다.
- `standing-corrections.yaml`: 적용한 기울기·팔 벌림·가슴 후방 회전 설정.
- `openpose/<방향>/`: 외형 프레임 생성용 OpenPose 참조 16장.
- `anny/`: 기준 모델 anny-39eab167-v1의 모션 리그와 방향별 렌더, 검증 자료.
- `manifest.yaml`: 출처·프레임 계약·파일 해시. 모션 NPZ의 실제 해시는 이 매니페스트를 따른다.

향후 포즈 생성은 `generators/animation/config/default_standing_motion.yaml`을 읽어 경로와 해시를 확인한다. `.tmp` 원본에 의존하지 않는다. 수정 시 새 버전을 만들며 기존 파일을 덮어쓰지 않는다. 게임 런타임 납품·채택은 별도다.
