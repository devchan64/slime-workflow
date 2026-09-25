# 기본 스트레칭 모션 v1

선택 이력: `2026-09-25_09-56-57-42fc2f95`. 120프레임·4방향, 관리도구 재생 4fps·30초. MoMask 원본 시간 기준은 20fps·6초이다. 프레임 생략 없이 등록했다.

ANNY 기준 모델 `anny-39eab167-v1`, 손 자세 `fist-v3`, 팔 회전 `parallel-transport-v3`를 적용했다. `anny/arm-corrections.json`은 실행 당시 보정값이다.

- `motion.npz`: HumanML3D 22관절 원본 모션
- `humanml3d/`: 관절 참조 프레임
- `openpose/`: ANNY 카메라 투영 COCO18 신체 맵·키포인트, 얼굴 제외
- `anny/`: 캐릭터 렌더·Blender/GLB 리그·보정값·검수 기록

선택 설정: `generators/animation/config/default_stretch_motion.yaml`. 게임 런타임 반영과 구분되는 워크플로우 재사용 자산이다. 원본 생성 이력과 기존 다른 동작 에셋은 유지한다. 정확한 닫힌 루프를 보장하지 않는다. Blender Corrective Smooth 결과는 GLB 뷰어에서 동일하게 보이지 않을 수 있다.
