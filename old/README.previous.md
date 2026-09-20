# slime-workflow

게임 이미지·스프라이트·음악을 제작하는 독립 Python 노드·파이프라인 저장소다.

## 구조
- `workflow/`: Python 패키지, 노드, 파이프라인, 테스트
- `scripts/workflow/`: 실행·모델 준비 스크립트
- 설계 문서: [비공개 백엔드 설계 인덱스](https://github.com/devchan64/slime-backend/tree/main/docs/design) (접근 권한 필요)
- 구조와 계약의 단일 기준: [Workflow SSOT](workflow/README.md)

## 독립 실행과 검증
Python 3.11 이상을 사용한다. 이 저장소 루트에서 실행한다.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
./scripts/verify.sh
```

- 위 의존성은 추론 없이 실행하는 19개 계약·변환 테스트용이다. 추론은 실행 노드의 `packages/requirements.txt`와 모델 준비 절차를 따른다.
- 모델 추론은 CUDA/MPS가 필요하며 CPU 추론과 준비 실패 시 대체 실행은 허용하지 않는다.
- 모델은 `.model/`, 결과는 `.result/`, 사운드폰트는 `.soundfonts/`에 두고 Git에 올리지 않는다.
- 워크플로우 실행 명령은 기존 `python -m workflow...` 경로를 유지한다.
- 모든 명령은 이 저장소 루트 기준이다. 프론트엔드·백엔드 디렉터리가 필요하지 않다.

## 산출물 전달
- [프론트엔드](https://github.com/devchan64/slime-frontend) 또는 [백엔드](https://github.com/devchan64/slime-backend)의 경로에 직접 쓰지 않는다.
- 버전과 메타데이터를 포함한 결과를 검수한 뒤 소비 저장소로 명시적으로 전달한다.
- 게임·제작 설계는 비공개 백엔드에서 작성한다. 이 공개 저장소에는 설계 문서 원본·복제본을 포함하지 않는다.
- 별도 제작 환경으로 운영하며 게임 런타임 배포에 모델을 포함하지 않는다. 이번 분리로 AWS 리소스를 추가하지 않는다.

## 전체 테스트의 기존 제한
분리 전 커밋 `d41b786`과 분리 후 모두 동일 환경에서 전체 탐색 테스트가 40개 중 17개 오류로 종료됐다. 추론용 `torch` 누락에 따른 import 오류 8개와 파이프라인 테스트·현재 런타임 계약 불일치 9개다. 이들은 저장소 이동으로 발생한 회귀가 아니며 전체 테스트 통과로 표시하지 않는다. 모델 추론 및 GPU E2E는 별도 준비가 필요하다.

## 기본 걷기 리그

기본 제작 리그는 `workflow/config/default_walk_rig.yaml`에서 지정한 `five-head-walk/v9`다. `scripts/resolve_default_walk_rig.py`로 해시 검증 후 재사용 경로를 확인한다. [실행·검증 안내](scripts/render_five_head_walk.md)를 따른다.

스탠딩 참조 미리보기는 `workflow/config/default_standing_preview.yaml`에 등록되어 있다. 로컬 자료 `.result/workflow/reusable/previews/default-standing/v1/preview.html`에서 네 방향 스탠딩을 재생하고 기본 리그와 비교할 수 있다.
