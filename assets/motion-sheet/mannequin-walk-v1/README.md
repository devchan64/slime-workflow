# mannequin-walk v1

보관과 재생성 입력에 사용하는 마네킹 리그다. 사람형 외형이나 게임 런타임 캐릭터가 아니며, 본 구조·관절 좌표·걷기 키프레임의 기준으로만 사용한다.

기존 `five-head-walk/v9` 자료를 새 식별자 `mannequin-walk/v1`로 정리한 보존 사본이다. 파일을 덮어쓰지 않고 새 버전으로 추가한다.

- `mannequin.blend`: 기준 마네킹 Blender 장면
- 사람형 리그 재생성 참조: `assets/rigs/humanlike-walk/v1/humanlike-walk.blend`
- `mannequin-motion.npz`: 마네킹 체형으로 변환된 25프레임 루프 모션
- `motion-source/source-motion.npz`: 원천 walk-travel 96프레임 모션
- `pose-sheets-v1/`: 포즈·OpenPose 비교용 기준 시트
- `rig-sheets-v2/`: 최신 셰이딩 리그 시트
- `rig-sheets-v2/openpose-walk-v1/`: OpenPose 참조 시트
- `artifact.json`: 모든 파일 해시와 출처
