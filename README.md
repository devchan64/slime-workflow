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
- `.result/workflow/reusable/`: 기존 승인 리그와 재사용 MoMask 모션. 임시 정리 대상 아님.
- `.tmp/YYYY-MM-DD_HH-mm-ss/`: 한국 시간 기준 실행별 후보 이미지·포즈·프롬프트·로그·출처. Git 제외.
- 정식 채택된 이미지의 관리 원본: `slime-frontend` 에셋 경로. 명시적 채택 후 전달·등록한다.
- 기획·설계와 정식 제작 프롬프트: 비공개 `slime-backend/docs/design/`.

모델 준비·GPU 추론은 샌드박스 밖에서 실행한다. CPU 추론이나 준비 실패 시 대체 실행은 허용하지 않는다. 게임 런타임·AWS 배포 변경은 없다.

## 기본 재사용 루프

`five-head-walk-6f/v1`은 사용자 승인된 5등신 리그의 4방향×6프레임·1.2초 루프다. `generators/animation/config/default_walk_loop.yaml`로 선택하며 `generators/animation/resolve_default_loop.py`가 등록 파일 해시를 검증한다. 자산은 `.result/workflow/reusable/animation-loops/`에 보관하고 임시 정리 대상에서 제외한다.
