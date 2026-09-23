# ANNY 마네킹 생성·재현 워크플로우

## 현재 상태

2026-09-23 사용자 요청으로 리그 에셋 v2·v3·v4를 폐기했다. 해당 바이너리·프레임·입력·버전별 재현 코드는 정식 에셋에서 제거했다. 이 버전들을 대상으로 하던 `reproduce_anny_mannequin.py`도 제거했다. 과거 제작 이력은 Git 커밋 cb50b12에서 확인할 수 있으며 현행 자산으로 사용하지 않는다. 기본 참조는 기존 mannequin-walk/v1로 복원했다.

## 유지하는 ANNY 기준 모델 재현

`report/anny-reference-baseline-20260923-r3/`의 snapshot, 입력 속성, 재현 코드와 검증 기록은 현재 체형 기준 모델 리포트다. 폐기한 v2·v3·v4 리그를 다시 등록하는 경로가 아니다.

```bash
.venv/bin/python report/anny-reference-baseline-20260923-r3/reproduce.py --render
```

CUDA 생성·렌더는 샌드박스 밖에서 실행한다. Python 3.12 `.venv`, ANNY 0.6.0 `.local/anny-runtime`, `.model/anny` 캐시, Blender Python 3.11/bpy 4.5.3 `.local/blender-runtime`을 사용한다. CPU 추론으로 대체하지 않는다.

## 제작 순서와 검수 기준

1. ANNY 계약의 attributes.json에서 phenotype, local changes, local-ref 104본 포즈를 검증한다. unknown label·중복 키·잘못된 회전·GPU 부재는 즉시 실패한다.
2. native ANNY 파라미터로 먼저 체형을 맞춘다. 변형 강도는 실제 길이 증가율이 아니며 age는 실제 나이와 직접 대응하지 않는다.
3. 정점·본 행렬·원본 가중치를 Blender로 옮겨 정면·측면을 검수한다. 높이 1.6m 균일 정규화와 체형 후보정을 구분한다.
4. 재사용 MoMask 원본·파생 루프를 해시로 식별한다. 원본 발목→발끝 길이·각도, 루프 가공과 리타게팅의 효과를 분리해 검수한다.
5. 20fps 루프에서 0,3,6,9,12,15,18,21을 방향별 렌더하면 4방향×8프레임, 150ms 간격이다. 투영 포즈맵과 OpenPose 검출을 구분한다.
6. 좌우 발의 같은 보행 위상, 접지·스윙, GLB 재수입, 루프 끝점을 확인한다. 수치 재현 통과가 동작의 자연스러움이나 AnyPose 인식률을 보증하지 않는다.

새 후보는 `.tmp/<executor-kind>/<한국시간>/`에 입력·코드·로그·결과를 함께 보관하고, 검수 후 명시적 채택 시에만 새 버전으로 등록한다. 이번 발 위상 보정 후보도 실험 상태로 유지한다.
