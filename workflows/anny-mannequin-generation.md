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

## 위치 채널 공통 리타깃 사용

`generators/momask/position_retarget.py`가 공통 회전 계산을 담당하고
`generators/momask/config/humanml22-anny-retarget.yaml`이 HumanML3D-22와 ANNY의
관절 대응·축·분할 본을 정의한다. 프로필은 동작명이나 프레임별 보정값을 받지 않는다.
현재 제공 프로필은 인간형 HumanML3D→ANNY 조합이다. 다른 리그는 검증된 대응
프로필이 필요하며 자동 지원되지 않는다.

원본 `joints` 위치 채널을 사용한다. 프로필 schema 2는 출처·해시가 고정된
MoMask BVH 템플릿의 계층 OFFSET으로 원본 기준 관절을 정의한다. 모션 첫 프레임이나
BVH의 MOTION 프레임을 기준 자세로 사용하지 않는다. 출처는 프로필의
`source_reference`에 있으며 라이선스는 `config/MOMASK-TEMPLATE-LICENSE.txt`에 둔다.

구간의 관측 의미에 따라 `transfer_mode`를 명시한다.
- `absolute_direction`: 팔다리·발의 대응 끝점 방향을 그대로 맞춘다. 원본 T 자세와
  대상의 내려간 팔 기준 자세 차이를 상대 회전으로 중복 적용하지 않는다.
- `reference_delta`: 골반·척추·목·쇄골·어깨 연결 구간은 원본 기준 방향 대비 변화량을
  대상 기준 회전에 전달한다. 관절 랜드마크의 고정 기울기를 동작 회전으로 간주하지 않는다.

두 모드는 모든 동작에 동일하게 적용되며 골격 프로필만 선택한다. 독립 두 방향은
기준 프레임 대비 회전을 복원하고, 단일 방향은 최소 회전을 연속 운반한다.
필수 방향이 퇴화하면 실패한다. 단일 방향의 축 비틀림과 머리의 독립 시선은
위치에서 완전히 관측되지 않으며 복원된 정보로 표시하지 않는다.

대상 본 길이와 가중치를 유지하므로 절대 관절 위치 일치를 보장하지 않는다.
동작별 팔 제한·쇄골 상승·대기 자세 사전 보정·발 첫 프레임 기준 회전·메시 스무딩·
자동 주먹 자세·프레임별 접지 이동은 적용하지 않는다. 미대응 손가락·머리 등은
부모 회전을 상속하며 기준 로컬 자세를 유지한다. 루프 회전 잔차·접촉은 별도 검수한다.

모션 보정 설정·전용 실행기·자동 손 자세 모듈은 폐기했다.
`--arm-correction-config`와 `--animate-hand-closure`는 더 이상 허용하지 않으며
전달하면 CLI 인자 오류로 종료한다. 신규 결과에는 `arm_corrections`,
`legacy_options`, `hand_closure_animation` 필드나 `arm-corrections.json`을 만들지 않는다.
렌더 재개에도 보정 기록 파일은 필수가 아니다. 과거 실행에 남은 보정 기록은
당시 결과의 출처로 유지하며, 기존 설정을 현재 리타깃에 다시 적용하지 않는다.

실행 폴더에 프로필·계산기 사본과 해시를 저장하고 `retarget-contract.json`에
방식 식별자 `position-reference-transport-v3`를 남긴다. `review-metrics.json`은
구간별 전달 방식·예상 대상 방향·실제 리그 방향 오차·원본과의 차이·프레임 간 회전을 기록한다.
`retarget-diagnostics.npz`의 `direction_errors`는 프로필 구간 순서의 실제 본 방향 오차다.
원본과의 직접 방향 차이와 선언된 전달 목표 오차를 구분한다. 골반처럼 다른 구간이 끝점을 구동하는 경우 끝점 오차와 본 회전 오차를 별도로 검수한다.
재개는 저장된 리그와 계약을 사용하며 최신 방식으로 다시 표시하지 않는다.

회귀 검증: `.local/blender-runtime/bin/python tools/review/tests/test_anny_position_retarget.py`.
기준 방향 180° 통과·반대 방향 이동·빠른 동작·좌표 회전·평행 이동·길이 변경·
분할 본·프로필 오류·상태 재개를 검증한다. 일반 Python 환경은 Blender 의존
검사를 skip하므로 실제 검증은 위 명령으로 실행해야 한다.
