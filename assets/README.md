# 워크플로우 재사용 자산

이 경로는 Git 추적 대상 제작 자산을 버전·출처·해시와 함께 보관한다. 게임 런타임 채택과 구분한다.

- 현재 기본 리그: [mannequin-walk/v2](motion-sheet/mannequin-walk-v2/README.md). ANNY104 리그, MoMask 기반 1.2초 루프, 4방향 × 8프레임 OpenPose·리그 이미지와 대응 시트.
- 이전 리그: motion-sheet/mannequin-walk-v1 보존.
- 원천 모션: motion-sheet/momask-walk-motion-sheet-v1. 같은 버전 파일을 덮어쓰지 않는다.
- 다른 외형 이력: motion-sheet/humanlike-walk-v1 및 v2.
- animation-references/: 외형 참조 이력.
- generation-records/: 관리번호별 생성 이력·재현 입력 및 출력 사본.

기본 선택은 generators/animation/config/default_walk_rig.yaml 및 default_walk_pose_sheets.yaml에서 관리한다. 미리보기 HTML은 실행별 .tmp/에서 제공하며 정식 자산에 중복 등록하지 않는다. 모델 다운로드는 .model/, 승인 전 후보·비공개 실험 프롬프트는 .tmp/에 둔다. 공개 자산에 비공개 기획·설계·프롬프트·인증 정보를 포함하지 않는다.
