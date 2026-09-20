# 포즈 고정 외형 렌더

기본 리그 resolver가 검증한 Blender 장면을 열어 재질·제작용 외형을 추가한다. 기존 본·키프레임은 변경하지 않으며 8개 시점의 전체 본 행렬을 원본과 비교한 뒤 렌더한다. 이미지 생성 모델을 호출하지 않는다.

```bash
.local/blender-runtime/bin/python -u scripts/render_rig_locked_walk.py
```

CUDA 렌더는 샌드박스 밖에서 수행한다. 기존 불변 출력 경로가 있으면 실패한다. 출력은 `.result/workflow/runs/rig-locked-walk-v1`에 4방향 PNG 32개·로그·포즈 검증·manifest, `reusable/rigs/default-styled-walk/v1`에 편집 가능한 Blender 장면과 출처 해시로 보관한다. 모델 캐시가 아니다.

현재 외형은 단순 메시와 재질로 구성한 3D 프로토타입이다. 포즈 동일성 검증은 외형 일치·프레임 샘플링의 자연스러움·발 접지 품질을 보장하지 않는다. 결과는 프론트엔드 walk-v3에 별도로 전달했으며 런타임 등록은 하지 않았다. 원화 스타일 복원은 후속 제작이 필요하다.

## 생성 이미지 폐기 상태

캐릭터 걷기 외형 생성 결과(프론트엔드 walk-v2/v3·개별 프레임 실험·외형 적용 리그)는 사용자 요청으로 폐기했다. 위 출력 설명은 과거 실행 기록이며 현재 이미지가 존재한다는 뜻이 아니다. `.result/workflow/disposals/character-walk-2026-09-20.json`에 폐기 파일·해시를 기록했다. 승인된 기본 v9 리그·MoMask·Depth·스탠딩 참조는 보존한다.
