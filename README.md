# slime-workflow

현재 사용하는 MoMask 모션 생성기와 캐릭터 애니메이션 생성기를 관리한다.

## 생성기별 소스

- `generators/momask/`: CUDA MoMask 관절 모션 생성. SMPL 의존성 없음.
- `generators/animation/`: 기본 리그 검증, 4방향 포즈·Depth 렌더, 참조 준비, Qwen 프레임 생성.
- `workflows/`: 현재 작업의 실행 순서·입출력·검증 절차.
- `old/`: 이전 노드·음악 파이프라인·실험 생성기와 해당 문서·테스트. 현재 실행 경로에서 사용하지 않는다.

[캐릭터 애니메이션 제작 절차](workflows/character-animation.md)를 따른다.

## 보관 경로

- `.model/`: 모델 다운로드·캐시.
- `assets/`: 기존 승인 리그와 재사용 MoMask 모션. 임시 정리 대상 아님.
- `.tmp/YYYY-MM-DD_HH-mm-ss/`: 한국 시간 기준 실행별 후보 이미지·포즈·프롬프트·로그·출처. Git 제외.
- 정식 채택된 이미지의 관리 원본: `slime-frontend` 에셋 경로. 명시적 채택 후 전달·등록한다.
- 기획·설계: 비공개 `slime-backend/docs/design/`.
- 사용자 지시로 이전한 제작 프롬프트: [prompts/](prompts/README.md). 그 밖의 비공개 프롬프트는 기존 백엔드 경로를 유지한다.

모델 준비·GPU 추론은 샌드박스 밖에서 실행한다. CPU 추론이나 준비 실패 시 대체 실행은 허용하지 않는다. 게임 런타임·AWS 배포 변경은 없다.

## 기본 걷기 참조

걷기는 방향당 8프레임·150ms·1.2초 루프다. 개별 animation-loops 자산은 삭제하고 `assets/pose-sheets/`의 방향별 시트 4장을 유지한다. 출처·배치·해시는 `generators/animation/config/default_walk_pose_sheets.yaml`에서 관리한다.

## 캐릭터 기준 시트

걷기 이미지젠의 기본 입력은 셰이딩을 보강한 리그 8프레임 시트다. `assets/pose-sheets/five-head-walk-8f/v1/`의 OpenPose 시트는 비교 자료로 유지한다. `generators/animation/build_walk_pose_sheets.py`가 렌더 실행 폴더의 8프레임 포즈를 묶고 출처·파일 해시를 기록한다.

[캐릭터 생성·4방향 기준 시트 통합 절차](workflows/character-baseline-sheet.md)는 신규 캐릭터를 최대 지원 크기의 2×2 베이스라인으로 한 번에 생성한다. 단일 원화 생성 후 시트로 재생성하는 단계를 기본 경로에서 제거했다. 모든 최종 캐릭터 애니메이션은 이미지젠과 2×2 시트 전체를 사용하며 걷기 동작은 리그 8프레임 시트를 참조한다.

[스탠딩 시트 제작 절차](workflows/character-standing-sheet.md)는 승인된 2×2 베이스라인 시트 전체를 참조하여 4방향×4프레임의 4×4 시트를 생성한다. 입력 셀과 출력 행의 방향 대응을 명시하며 기존 standing-v2를 자동 교체하지 않는다.
