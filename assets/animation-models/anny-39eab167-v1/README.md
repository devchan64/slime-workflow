# ANNY 여성 타입 A · 버전 1

사용자가 선택한 생성 결과 `39eab167`의 재사용 제작 에셋이다. 모델 가중치가 아닌 체형·포즈·메시·104본 스킨 리그를 보관한다.

- `attributes.json`: 원본 ANNY 입력. 기준값은 허리둘레 -0.5, 골반 허리 높이 0, 등 근육 형태 0.
- `anny-raw-rig.blend`, `anny-raw-rig.glb`: 높이 1.6m로 균일 정규화한 스킨 리그.
- `anny-rest-rig.npz`: ANNY 원본 좌표의 메시·본 행렬·가중치.
- `validation.json`: 리그 및 가중치 검증 통과 기록.
- `manifest.yaml`: 출처·버전·좌표계·파일 해시.
- `source-history.json`: 원본 이력 그대로 보존. 당시 실행 상태 표기와 별개로 산출물 검증은 validation.json을 따른다.

현재 기본 선택은 `generators/animation/config/anny_model_baseline.yaml`이 가리키는 `generators/animation/config/anny_profiles/female_type_a.yaml`의 여성 타입 A · 버전 1 프로필이다. 이 에셋의 원본 생성 ID는 유지하므로, 기존 모션·포즈 시트의 이력 참조는 변경하지 않는다. 다른 리그 기준의 모션을 적용할 때 본 및 좌표계 호환성을 검증해야 한다.

관리 식별자는 `female_type_a_v1`이다. 기존 `anny-39eab167-v1` 경로와 생성 ID는 출처 및 과거 모션 호환을 위해 유지한다. 이 재분류는 체형 속성·메시·스키닝을 변경하지 않는다.
