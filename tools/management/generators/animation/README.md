# 애니메이션 제작 공용 모듈

MoMask + AnyPose 기반 애니메이션 생성기는 폐기했다. 이 디렉터리에 남은 구형 파일·설정이나 과거 리포트의 코드 사본은 활성 생성기를 뜻하지 않는다. AnyPose 추론·LoRA 준비와 `character-animation generate`·`resume`은 거절한다.

현재 모션 생성은 [`generators/hy_motion/`](../hy_motion/), 외형 포즈 변환은 [`generators/image/vnccs_runtime.py`](../image/vnccs_runtime.py)를 사용한다. 사용자는 공용 게이트웨이의 `hy-motion`·`pose-transfer`로 실행한다. [현행 제작·검수 절차](../../workflows/character-animation.md), [HY-Motion](../../workflows/hy-motion.md), [VNCCS](../../workflows/pose-transfer.md)를 참고한다.

| 용도 | 모듈·설정 | 현재 범위 |
| --- | --- | --- |
| Qwen 2511 공통 실행 | `qwen_pose/` | 다른 이미지 생성기가 재사용하는 코드. AnyPose 실행은 차단 |
| 등록 참조 자산 | `config/character_animation.yaml` | HY-Motion 걷기 v2 및 캐릭터 참조 정보. 구형 배치 생성 활성화와 구분 |
| 기존 포즈 시트·패킹 | `build_walk_pose_sheets.py`, `pack_walk_sheets.py` | 과거 고정 프레임 규격용 도구. 새 모션에 무조건 적용하지 않음 |
| 스탠딩 앵커 검수 | `review_standing_anchors.py` | 기존 시트 검수 보조 도구 |

구형 AnyPose 배치·단일 프레임 실행과 4방향×8프레임 Qwen 배치는 현행 제작 절차로 안내하지 않는다. 재현용 리포트·버전 고정 에셋의 출처는 보존하며, 일반 실험은 `.tmp/test/<실험명>/<한국시간 실행일시>/`에 기록한다.

VNCCS 기본 프롬프트의 현행 원본은 `generators/image/config/pose-transfer-prompt.txt`다. 이 디렉터리의 과거 `config/prompts/` 기록을 VNCCS 입력으로 자동 대체하지 않는다.
