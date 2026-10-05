# 워크플로우 재사용 자산

이 경로는 Git 추적 대상 제작 자산을 버전·출처·해시와 함께 보관한다. 게임 런타임 채택과 구분한다.

- 애니메이션 기준 모델: [anny-neutral-v4](animation-models/anny-neutral-v4/README.md). 선택 설정은 `generators/animation/config/anny_model_baseline.yaml`. 최종 v4만 보관하며 이전 v1·v2·v3 원본은 폐기했다.
- 현재 기본 걷기: [momask-walking/v13](motion-sheet/momask-walking-v13/README.md). 중성형 v4, 60프레임·4fps·4방향, 방위각 30°·325°·140°·215°. 이전 걷기 버전은 폐기했다.
- 이전 리그: motion-sheet/mannequin-walk-v1 보존.
- 다른 외형 이력: motion-sheet/humanlike-walk-v1 및 v2.
- animation-references/: 외형 참조 이력.
- generation-records/: 사용자 지시로 보존한 리포트·생성기 직접 연결 기록만 관리. 일반 생성 기록은 `.tmp/test/`에 보관.

현재 모션 선택은 generators/animation/config/character_animation.yaml에서 관리한다. 구형 default_walk 설정은 폐기 상태다. 미리보기 HTML은 실행별 .tmp/에서 제공하며 정식 자산에 중복 등록하지 않는다. 모델 다운로드는 .model/, 승인 전 후보·비공개 실험 프롬프트는 .tmp/에 둔다. 공개 자산에 비공개 기획·설계·프롬프트·인증 정보를 포함하지 않는다.


- 기본 스트레칭 모션: [momask-stretch/v1](motion-sheet/momask-stretch-v1/README.md). 120프레임·4fps·4방향, 선택 설정 `generators/animation/config/default_stretch_motion.yaml`.

- 게임용 4fps 포즈 시트: [game-motion-4fps/v1](pose-sheets/game-motion-4fps-v1/README.md). 스탠딩 v3·걷기 v8·스트레칭 v1, 4방향·총 24장. 선택 설정 `generators/animation/config/default_game_pose_sheets.yaml`.
