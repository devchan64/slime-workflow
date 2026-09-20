# 스탠딩 v2 제작 이력과 단계별 재실행

`assets/recipes/character-default-standing-v2/v1/recipe.yaml`이 기존 스탠딩 v2의 제작 기록 원본이다. 사용자가 스탠딩 기록을 워크플로우로 이전하도록 지시했으므로 이 레시피의 제작 프롬프트도 함께 이동했다. 기존 백엔드 YAML은 삭제하여 이중 관리하지 않는다. 이 예외는 해당 제작 기록에만 적용하며 일반적인 비공개 기획·설계 보관 위치는 바꾸지 않는다.

## 복원한 내용과 한계

- frontend Git 이력에서 스탠딩 v1 입력을 복구해 레시피 옆에 `input-standing-v1.png`로 보관한다. 원본 커밋·경로·SHA-256을 기록한다. 당시 내장 도구에 실제 전달한 이미지 해시는 남아 있지 않다.
- 기존 `initial`, `refinement` 프롬프트 원문을 변경 없이 보관한다. v1 → initial → refinement는 이 단계 이름을 바탕으로 복원한 재실행 절차다. 원래 호출 순서 및 최초 보정 출력은 확인되지 않았다.
- 최종 PNG와 애니메이션 메타데이터의 관리 원본은 frontend에 유지한다. 레시피에 버전·경로·해시를 기록한다. 최종 이미지를 워크플로우에 중복 등록하지 않는다.
- 내장 도구의 모델 버전과 시드를 지정·복구할 수 없으므로 동일 픽셀 재현은 보장하지 않는다. 절차 재실행 준비와 원래 결과 재현 완료를 구분한다.
- 이 레시피에는 과거 비율 보정 지시가 들어 있다. 기존 스탠딩 재실행용이며 현재 4방향 기준 시트의 기본 프롬프트로 사용하지 않는다. 신규 기준 시트는 [별도 절차](character-baseline-sheet.md)를 따른다.

## 1. 최초 보정 입력 준비

워크플로우 루트의 PyYAML 설치 환경에서 실행한다.

```bash
.venv/bin/python generators/animation/prepare_standing_replay.py --stage initial
```

레시피 필드·중복 키·고정 생성기·참조 해시를 검증하고 새 KST `.tmp/YYYY-MM-DD_HH-mm-ss/`에 `prompt.txt`, `reference.png`, `replay.yaml`, `execution.log`를 작성한다. 준비 작업은 추론하지 않으며 짧은 로컬 파일 처리다. 기존 실행 폴더와 충돌하거나 입력이 잘못되면 즉시 실패한다.

출력 폴더의 참조를 이미지 도구로 확인한 다음, Codex 내장 `image_gen`에 `prompt.txt` 원문과 `referenced_image_paths=[reference.png의 절대 경로]`를 전달한다. 준비 명령 자체가 이미지를 생성한다고 간주하지 않는다. 원래 기본 출력 파일은 보존하고 실행 폴더에 `initial-output.png`로 복사한다. 출력 경로·SHA-256·실제 크기·도구 실행 로그를 실행 기록에 추가한다.

## 2. 추가 보정 입력 준비

```bash
.venv/bin/python generators/animation/prepare_standing_replay.py \
  --stage refinement --input /absolute/path/to/initial-output.png
```

이번 initial 단계의 실제 출력을 반드시 전달한다. 과거 최종 이미지나 원형 베이스라인을 대신 넣지 않는다. `--input` 누락·비PNG 입력은 실패하며 자동 대체하지 않는다. 새 실행 폴더의 프롬프트·참조로 내장 도구를 다시 실행하고 결과 및 출처를 기록한다. 입력 경로·해시는 기록하지만 해당 이미지가 실제 initial 단계 출력인지까지 자동 증명하지는 않는다.

## 3. 결과 검수 및 등록

4행은 위에서부터 `down_left`, `down_right`, `up_left`, `up_right`다. 각 행은 4프레임이며 현재 런타임 메타데이터는 400ms×4, 1.6초 루프다. 전신 잘림·방향·셀 간 일관성·발 위치를 검수한다.

기존 1254px 시트의 셀 경계는 `[0, 313, 627, 940, 1254]`이며 313/314px가 섞여 있다. 신규 출력 크기에 과거 셀 좌표나 발 anchor를 그대로 적용하지 않는다. 기존 anchor는 수동 보정 기록으로, 자동 재생성 알고리즘이 복원된 것은 아니다. 기존 메타데이터 자체는 레시피의 frontend 커밋·경로·해시로 복구 가능하다.

후보는 `.tmp`에 보존하고, 사용자 채택 후에만 frontend 새 버전으로 전달·등록한다. 이번 기록 이동은 기존 게임 이미지·애니메이션·배포·AWS 비용을 변경하지 않는다.
