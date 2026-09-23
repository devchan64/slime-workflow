# 애니메이션 생성기

현재 워크플로우에 연결된 실행기와 공통 모듈만 유지한다. 과거 실험 코드가 리포트나 승인 에셋에 사본으로 남아 있는 것은 활성 생성기를 유지할 근거가 아니다.

| 용도 | 진입점·모듈 | 사용 근거 |
|---|---|---|
| AnyPose 배치 | run_pose_transfer_any_pose_batch.py, run_pose_transfer_anypose_baseline_rig_batch.py | workflows/character-animation.md |
| AnyPose 단일 프레임 | generate_pose_transfer_any_pose_frame.py, generate_pose_transfer_any_pose_standard_frame.py | 같은 문서 및 표준 스텝 실험 |
| Qwen OpenPose | generate_pose_transfer_openpose_qwen.py, run_pose_transfer_two_reference_qwen_batch.py | workflows/character-animation.md |
| 공통 포즈 편집 | qwen_pose/ | 활성 AnyPose·OpenPose 생성기가 import |
| MoMask 리그 렌더 | render_momask_rig.py, resolve_default_rig.py | workflows/momask-rig-render.md |
| 포즈 시트·최종 패킹 | build_walk_pose_sheets.py, pack_walk_sheets.py | README.md 및 캐릭터 애니메이션의 시트 제작·패킹 단계 |
| 스탠딩 앵커 검수 | review_standing_anchors.py, review_standing_anchors.html | workflows/character-standing-sheet.md 및 tools/review |

2026-09-23에 워크플로우 연결이 없는 구형 Qwen/2512 생성기·입력 준비기·구형 리그 렌더·과거 사람형 리그 검증기를 폐기했다. 사본과 폐기 근거는 `.tmp/test/animation-generator-retirement/`에 보관한다. 재현용 리포트·버전 고정 에셋 사본은 변경하지 않는다. 일반 실험 기록은 `.tmp/test/`에 작성하고 명시적 지시 없이 저장소에 승격하지 않는다.
