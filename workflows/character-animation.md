# 캐릭터 애니메이션 생성 규칙

이 문서는 캐릭터 걷기 애니메이션의 기준·생성·검수·정규화·시트 패킹 규칙을 단일 문서로 관리한다. 이전 애니메이션·Qwen·AnyPose·시트 패킹 문서는 이 문서에 흡수하고 삭제했다. 생성 후보와 중간 산출물은 `slime-workflow/.tmp/`에 보관하며, 사용자가 채택한 최종 이미지와 게임 런타임 등록은 `slime-frontend`에서 관리한다.

## 최종 목표와 고정 규칙

- 걷기는 4방향(`up_left`, `up_right`, `down_left`, `down_right`) × 8프레임이다.
- 방향 이름은 2×2 베이스라인의 좌상·우상·좌하·우하와 각각 대응한다.
- 모든 프레임은 해당 방향의 베이스라인 장면과 같은 시점·방향을 사용한다. 다른 방향 셀을 외형 참조로 섞지 않는다.
- 기본 포즈 생성은 캐릭터 아이덴티와 단일 포즈 참조를 사용하는 Qwen 경로다. 리그 참조와 OpenPose 참조는 서로 독립된 생성 조건으로 실행한다.
- 잘못 생성된 프레임은 검수로 식별한 뒤 AnyPose 포즈 전이 경로로 개별 재생성한다.
- 포즈를 통과한 프레임의 아이덴티·크기·스프라이트 정렬은 ImageGen 또는 Qwen-Image-Edit로 정규화한다.
- 최종 스프라이트에서 캐릭터의 최소 실제 높이는 384px이다. 자세별 바운딩 박스 높이를 매 프레임 같은 값으로 강제하지 않고, 기준 캐릭터의 균일 배율과 앵커를 유지한다.
- 정규화한 프레임은 정해진 셀 격자에 배열한다. 걷기는 4×4 시트 2장으로 전달한다.

## 1. 방향별 베이스라인 참조

승인된 2×2 베이스라인 전체를 외형 기준으로 보관하고, 생성할 방향의 셀만 해당 방향 장면 참조로 크롭한다.

| 베이스라인 위치 | 방향 키 | 걷기 리그 파일 |
| --- | --- | --- |
| 좌상 | `up_left` | `assets/rigs/mannequin-walk/v1/rig-sheets-v2/up_left.png` |
| 우상 | `up_right` | `assets/rigs/mannequin-walk/v1/rig-sheets-v2/up_right.png` |
| 좌하 | `down_left` | `assets/rigs/mannequin-walk/v1/rig-sheets-v2/down_left.png` |
| 우하 | `down_right` | `assets/rigs/mannequin-walk/v1/rig-sheets-v2/down_right.png` |

베이스라인 크롭은 흰 배경의 512×512 PNG로 만들고, 원본 경계·원본 해시·방향 키를 실행 기록에 남긴다. 캐릭터 크롭은 해당 방향을 사용하며, 좌상 캐릭터로 우하 프레임을 생성하는 식의 대체를 허용하지 않는다.

현재 승인 베이스라인 경로:

```text
slime-frontend/src/assets/characters/default/baseline/character-default-white-shirt-four-directions-v2.png
```

## 2. 리그와 OpenPose 준비

재사용 리그는 `assets/rigs/mannequin-walk/v1/rig-sheets-v2/`를 사용한다. 각 방향 시트는 2048×1024, 4열×2행, 셀 512×512이며 행 우선으로 1–4프레임과 5–8프레임을 배치한다. 해당 시트의 `manifest.yaml`에서 자산 버전과 해시를 확인한다.

- 리그 셀: 실제 관절·몸통·발 연결을 보는 셰이딩된 참조
- OpenPose 셀: 같은 MoMask 관절의 투영 참조
- 리그와 OpenPose는 반드시 같은 방향·프레임 번호를 사용한다.
- 방향이나 프레임이 불일치한 참조는 생성에 사용하지 않고 실행을 폐기한다.

OpenPose와 리그는 서로 대체되지 않는 독립 포즈 참조 조건이다. 생성 결과에는 참조 종류·입력 경로·해시를 기록한다.

## 3. 단일 포즈 참조 Qwen 전환

정상 프레임은 다음 두 조건 중 하나로 Qwen-Image-Edit-2511에 전달한다. 3참조 경로는 실험 실패로 분류하며 기본 제작에서 사용하지 않는다.

| 생성기 | 이미지 1 | 이미지 2 |
| --- | --- | --- |
| 리그 AnyPose | 해당 방향 캐릭터 아이덴티 | 동일 방향·프레임 리그 셀 |
| OpenPose Qwen | 해당 방향 캐릭터 아이덴티 | 동일 방향·프레임 OpenPose 셀 |

AnyPose 없이 Lightning LoRA만 사용하는 전용 생성기는 다음 파일이다.

```text
generators/animation/generate_pose_transfer_openpose_qwen.py
```

OpenPose 전용 기본 프롬프트는 `generators/animation/config/pose_transfer_openpose_qwen_prompt.txt`에서 관리하며, 포즈 변경 지시만 포함한다. 방향별 보조 프롬프트는 `DIRECTION_POSE_INSTRUCTIONS`로 분리해 걷기 방향만 지정한다.

```text
Make the person in image 1 do the exact same pose of the person in image 2.
```

두 실행기는 4스텝 Lightning 경로를 사용하며, 모델·LoRA·스텝·시드·입력 순서·입력 해시·출력 해시를 `result.json`과 실행 로그에 남긴다. 리그와 OpenPose 결과는 동일 프레임 번호로 별도 검수한다.

OpenPose 단일 프레임 함수 `generate_pose_transfer_openpose_qwen_frame(...)`은 다른 워크플로 노드에서 라이브러리로 호출할 수 있다. 모델·LoRA 선택은 외부 입력으로 받지 않는다.

### 32프레임 배치

4방향×8프레임은 YAML 목록으로 실행한다. 목록 파일과 참조 자산 경로는 워크플로 루트 기준 상대 경로만 사용한다. 기본 목록은 다음 파일이다.

```text
generators/animation/config/pose_transfer_two_reference_qwen_default_walk.yaml
```

실행기는 목록을 검증한 뒤 `down_left`, `down_right`, `up_left`, `up_right` 각 8프레임을 순서대로 생성한다.

```bash
.venv/bin/python generators/animation/run_pose_transfer_two_reference_qwen_batch.py \
  --batch-file generators/animation/config/pose_transfer_two_reference_qwen_default_walk.yaml \
  --output-dir .tmp/test/openpose-qwen-4step-32frames/<한국시간 실행일시>
```

결과는 지정한 `.tmp/test/<실험명>/<한국시간 실행일시>` 폴더 아래 방향·프레임별 폴더에 저장한다. 리그 조건과 OpenPose 조건은 각각 별도 실행한다. 각 프레임은 캐릭터·포즈 참조, `prompt.txt`, `result.png`, `result.json`, `execution.log`를 가지며 배치 전체에는 `batch-result.yaml`을 남긴다.

OpenPose 조건 실행:

```bash
.venv/bin/python generators/animation/run_pose_transfer_two_reference_qwen_batch.py \
  --batch-file generators/animation/config/pose_transfer_two_reference_qwen_default_walk.yaml \
  --output-dir .tmp/test/openpose-qwen-4step-32frames/<한국시간 실행일시>
```

## AnyPose 배치 생성 기준

2026-09-23 채택 기준은 캐릭터 baseline-v2 + mannequin-walk/v5 리그의 2참조 생성기이다. 전 방향에 짧은 기본 프롬프트를 사용하고 좌상·우상에만 동일한 후면 보조 프롬프트를 추가한다. AnyPose + Lightning 4 steps, seed 10107, 512×512, 4방향 × 8프레임을 사용한다.

```bash
.venv/bin/python generators/animation/run_pose_transfer_any_pose_batch.py
```

기본 설정은 `generators/animation/config/pose_transfer_anypose_baseline_rig_default_walk.yaml`이다. `--batch-file`과 `--output-dir`로 명시적으로 변경할 수 있다. 이전 3참조 배치 YAML은 이 진입점과 호환되지 않으며 자동 변환하지 않는다.

채택 프롬프트 원본은 비공개 문서에서 관리한다. 실행 전에 승인된 `base-prompt.txt`, `auxiliary-prompt.txt`를 `.local/production-prompts/anypose-v5-v1/`에 전달해야 한다. 누락 시 즉시 실패하며 구형 프롬프트로 대체하지 않는다. 공개 저장소는 이 원본 저장소를 런타임 의존성으로 읽지 않는다.

라이브러리 진입점은 `execute_pose_transfer_any_pose_batch(batch_definition_path, run_output_root=None)`이다. 프레임별 결과에 실제 결합 프롬프트 해시와 `rear_prompt_applied`를 기록한다. 생성기 기준 채택은 생성 이미지의 품질 승인과 별개이며 신발·머리카락 소실 여부는 계속 검수한다.

## 4. 프레임 검수와 AnyPose 재생성

생성된 8프레임을 방향별 검수 도구에서 리그·OpenPose와 함께 재생한다. 같은 프레임 번호를 기준으로 방향, 골반→무릎→발목 연결, 지지발·이동발, 어깨·팔꿈치·손목, 5등신 외형, 프레임 간 크기·지면 앵커·잘림을 판정한다.

정상 프레임은 재생성하지 않는다. 오류 프레임만 선택하여 다음 AnyPose 생성기를 사용한다.

```text
generators/animation/generate_pose_transfer_any_pose_frame.py
generators/animation/generate_pose_transfer_any_pose_standard_frame.py
```

AnyPose 재생성에서도 캐릭터와 리그는 동일 방향·동일 프레임을 사용한다. 이전에 잘못 생성된 프레임을 포즈 참조로 재사용하지 않는다. AnyPose 결과도 리그 비교를 통과해야 하며, 어댑터 로드 성공은 품질 승인이나 최종 에셋 채택을 의미하지 않는다.

## 5. 아이덴티·크기 정규화

포즈 검수를 통과한 프레임의 외형 및 스프라이트 규격을 정규화한다. 정규화 도구는 ImageGen 또는 Qwen-Image-Edit 중 하나를 선택하며, 선택한 도구·프롬프트·입력·출력·해시를 기록한다.

1. 해당 방향의 승인 베이스라인을 아이덴티 기준으로 사용한다.
2. 캐릭터 전체 높이가 최종 스프라이트에서 최소 384px이 되도록 균일 배율을 적용한다.
3. 비균등 확대·축소로 머리·몸통·팔다리 비율을 바꾸지 않는다.
4. 자세별 바운딩 박스 높이로 프레임마다 캐릭터를 임의 확대·축소하지 않는다.
5. 균일 배율 이후 투명 여백과 지면 앵커 이동으로 셀 안에 배치한다.
6. 신체가 잘리거나 384px 최소 높이를 만족하지 못하면 실패 처리하고 생성 단계로 되돌린다.

## 6. 격자 배열과 최종 시트

각 방향의 8프레임을 동일 셀 규격으로 확정한 뒤 최종 시트에 배열한다. 셀 안의 정상 픽셀은 재생성·재정규화하지 않는다.

| 시트 | 행 1–2 | 행 3–4 |
| --- | --- | --- |
| 1장 | `down_left` 프레임 1–8 | `down_right` 프레임 1–8 |
| 2장 | `up_left` 프레임 1–8 | `up_right` 프레임 1–8 |

각 방향의 8프레임은 4열×2행으로 배열한다. 최종 시트에는 프레임 rect, 방향·프레임 번호, 셀 크기, 배율, 이동량, 앵커, 시트 해시를 함께 기록한다. 원본 시트는 보존하고 수정본에 선택 프레임만 교체한다.

## 7. 최종 검수와 기록

최종 시트는 150ms 간격으로 재생하여 4→5 프레임 묶음 경계와 8→1 루프 경계를 확인한다. 방향 변경, 관절·발 연결 오류, 384px 미만, 배율·앵커 흔들림, 잘림·잔여 픽셀, 시트 격자·rect·순서 오류가 있으면 채택하지 않는다.

실행 폴더에는 프롬프트, 참조 이미지, 리그/OpenPose 버전과 해시, 모델·LoRA·스텝·시드, 로그, 생성 결과, 검수 판정, 최종 시트와 메타데이터를 함께 보관한다. 미등록 후보는 `.tmp/YYYY-MM-DD_HH-mm-ss/` 아래에만 두며, 사용자가 채택한 결과만 프론트엔드 정식 에셋으로 전달한다.

검수 서버와 애니메이션 비교 UI의 운영 규칙은 [에셋 검수 도구](asset-review.md)를 따른다. 이미지젠 호출의 일반 제한과 재시도 정책은 [이미지젠 최소 사용 정책](imagegen-usage-policy.md)을 따른다.
