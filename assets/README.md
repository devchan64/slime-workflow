# 워크플로우 재사용 자산

이 경로는 Git 추적 대상 제작 자산을 버전·출처·해시와 함께 보관한다. 게임 런타임 채택과 구분한다.

- 애니메이션 기준 모델: [anny-neutral-v4](animation-models/anny-neutral-v4/README.md). 선택 설정은 `generators/animation/config/anny_model_baseline.yaml`.
- 현재 기본 걷기: [momask-walking/v10](motion-sheet/momask-walking-v10/README.md). 중성형 v4, 60프레임·4fps·4방향, 카메라 수평 25°. v8은 신규 생성 선택에서 제외하며 기존 결과·시트의 출처로 보존한다.
- 이전 리그: motion-sheet/mannequin-walk-v1 보존.
- 원천 모션: motion-sheet/momask-walk-motion-sheet-v1. 같은 버전 파일을 덮어쓰지 않는다.
- 다른 외형 이력: motion-sheet/humanlike-walk-v1 및 v2.
- animation-references/: 외형 참조 이력.
- generation-records/: 사용자 지시로 보존한 리포트·생성기 직접 연결 기록만 관리. 일반 생성 기록은 `.tmp/test/`에 보관.

기본 선택은 generators/animation/config/default_walk_rig.yaml 및 default_walk_pose_sheets.yaml에서 관리한다. 미리보기 HTML은 실행별 .tmp/에서 제공하며 정식 자산에 중복 등록하지 않는다. 모델 다운로드는 .model/, 승인 전 후보·비공개 실험 프롬프트는 .tmp/에 둔다. 공개 자산에 비공개 기획·설계·프롬프트·인증 정보를 포함하지 않는다.

- 기본 대기 모션: [momask-standing/v8](motion-sheet/momask-standing-v8/README.md). 120프레임·4fps·4방향, 선택 설정 `generators/animation/config/default_standing_motion.yaml`.

- 기본 스트레칭 모션: [momask-stretch/v1](motion-sheet/momask-stretch-v1/README.md). 120프레임·4fps·4방향, 선택 설정 `generators/animation/config/default_stretch_motion.yaml`.

- 게임용 4fps 포즈 시트: [game-motion-4fps/v1](pose-sheets/game-motion-4fps-v1/README.md). 스탠딩 v3·걷기 v8·스트레칭 v1, 4방향·총 24장. 선택 설정 `generators/animation/config/default_game_pose_sheets.yaml`.
