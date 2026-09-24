# ANNY 애니메이션 기준 모델 39eab167 · v1

사용자가 선택한 생성 결과 `39eab167`의 재사용 제작 에셋이다. 모델 가중치가 아닌 체형·포즈·메시·104본 스킨 리그를 보관한다.

- `attributes.json`: 원본 ANNY 입력. 기준값은 허리둘레 -0.5, 골반 허리 높이 0, 등 근육 형태 0.
- `anny-raw-rig.blend`, `anny-raw-rig.glb`: 높이 1.6m로 균일 정규화한 스킨 리그.
- `anny-rest-rig.npz`: ANNY 원본 좌표의 메시·본 행렬·가중치.
- `validation.json`: 리그 및 가중치 검증 통과 기록.
- `manifest.yaml`: 출처·버전·좌표계·파일 해시.
- `source-history.json`: 원본 이력 그대로 보존. 당시 실행 상태 표기와 별개로 산출물 검증은 validation.json을 따른다.

선택 설정은 `generators/animation/config/anny_model_baseline.yaml`에서 관리한다. 기존 모션·포즈 시트는 재생성하지 않았으며, 다른 리그 기준의 모션을 적용할 때 본 및 좌표계 호환성을 검증해야 한다.
