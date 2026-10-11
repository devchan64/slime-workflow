# 워크플로우 재사용 자산

이 경로는 승인된 제작 자산을 식별자·버전·출처·해시와 함께 보관한다. 생성 후보와 게임 런타임 채택은 구분한다.

- 등록된 기본 제작 모션: [HY-Motion 걷기 v2](motion-sheet/hy-motion-walking-v2/README.md). 원본 9~43번을 채택한 35프레임·30FPS, 4방향 원근투영 ANNY RGB·OpenPose를 보관한다.
- ANNY 기준 모델: [anny-neutral-v4](animation-models/anny-neutral-v4/README.md). 선택 설정은 `generators/animation/config/anny_model_baseline.yaml`이다.
- `character-baselines/`: 캐릭터 외형 참조와 출처 기록.
- `generation-records/`: 사용자 지시로 보존한 리포트·생성기 직접 연결 기록. 일반 실행 기록은 `.tmp/test/`에 보관한다.
- [게임용 4fps 포즈 시트](pose-sheets/game-motion-4fps-v1/README.md): 과거 제작 규격의 보존 자산이며 신규 생성의 기본 모션이 아니다.

모션·외형 참조 목록은 `generators/animation/config/character_animation.yaml`에 남아 있다. 이는 폐기된 `character-animation generate`·AnyPose 배치 기능을 활성화하지 않는다. 현재 실행·검수는 [캐릭터 애니메이션 제작](../workflows/character-animation.md)을 따른다.

MoMask 생성기 폐기와 승인된 모션·피팅·리그의 보존은 구분한다. 과거 MoMask 걷기·스트레칭이나 mannequin 버전을 현재 기본값으로 안내하지 않으며, 보존 자산을 임의로 삭제하지 않는다. 모델 다운로드는 `.model/`, 미등록 후보는 `.tmp/test/<실험명>/<한국시간 실행일시>/`에 둔다.

채택된 캐릭터·몬스터 스프라이트와 애니메이션·앵커 메타데이터의 관리 원본은 `slime-assets/assets/sprites/`다. 워크플로우의 모션·리그·중간 결과와 구분하고 사용자 채택 후 명시적으로 전달한다.

외형 베이스라인 경로는 `assets/animation-references/`에서 `assets/character-baselines/`으로 변경했다. 과거 실행 기록의 입력 경로는 당시 출처로 보존한다. 공개 자산에 비공개 설계·인증정보를 포함하지 않는다.
