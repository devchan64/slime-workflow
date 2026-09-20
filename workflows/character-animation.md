# 캐릭터 애니메이션 제작 절차

저장소 루트에서 실행한다. 이 문서는 생성기 실행 계약이며 게임 기획이나 내부 프롬프트 원본을 포함하지 않는다.

## 1. 원형과 모션 확인

정식 베이스라인을 외형 기준으로 사용하고, OpenPose 형식의 입력은 MoMask 관절 모션에서 만든다. 생성된 다른 프레임을 외형 기준으로 연쇄 사용하지 않는다.

```bash
.venv/bin/python generators/animation/resolve_default_rig.py
```

`generators/animation/config/default_walk_rig.yaml`이 선택한 `five-head-walk/v9`의 manifest·모션·Blender 파일 해시를 검증한다. 원본 모션은 `walk-travel/v1`이다. 기존 승인 자산이 있으면 다시 추론하지 않는다.

새 모션이 필요한 경우 고정 모델 준비 기록과 `.model/motion-depth/` 가중치를 먼저 확인한다. 현재 로컬 준비 기록은 `.result/workflow/runs/motion-depth-attempt-v2/prepared.json`이다. 준비 기록이 없으면 즉시 중단하며 자동 다운로드·CPU 대체 실행을 하지 않는다.

```bash
.venv/bin/python generators/momask/generate_motion.py --help
.venv/bin/python generators/momask/generate_motion.py
```

두 번째 명령은 샌드박스 밖 CUDA에서 실행한다. 96프레임·20fps HumanML3D-22 관절과 출처를 새 `.tmp`에 기록한다. 새 모션을 기존 v9 리그 모션에 자동 교체하지 않는다. 체형 피팅과 검수가 끝난 뒤 별도 불변 버전으로 등록한다.

## 2. 승인된 4방향·6프레임 루프 재사용

사용자 승인 자산 `five-head-walk-6f/v1`을 기본으로 사용한다. 아래 명령으로 등록 manifest와 모든 파일 해시를 검증한다.

```bash
.venv/bin/python generators/animation/resolve_default_loop.py
```

선택 파일은 `generators/animation/config/default_walk_loop.yaml`, 자산 경로는 `assets/animation-loops/five-head-walk-6f/v1/`이다. `.tmp` 정리와 무관하게 보존하며 덮어쓰지 않는다. `preview.html`로 검수한 루프를 재생하고 각 방향의 `openpose-0001.png`~`openpose-0006.png`를 후속 외형 생성에 재사용한다. 원본 샘플 모션·Blender 리그·Depth·마스크·검증 기록도 함께 보관한다.

기존 manifest.json은 실험 시점의 기록으로 유지하며, 정식 승인 상태와 출처·호환 정보의 기준은 artifact.json이다. 루프 승인과 최종 캐릭터 외형 승인은 구분한다. 새로운 모션·체형·프레임률이 필요할 때만 아래 재렌더 절차를 수행하고, 검수 후 새 불변 버전으로 등록한다.

### 새 포즈 렌더 실험

```bash
.local/blender-runtime/bin/python generators/animation/render_pose_frames.py
```

샌드박스 밖 CUDA가 필요하다. `rig_builder.py`는 이 실행기가 사용하는 5등신 리그 구현이며 직접 실행하지 않는다.

- 승인 v9의 24개 시간 구간에서 `0,4,8,12,16,20`을 선택한다. 8프레임 중 앞 6개를 잘라내는 방식이 아니다.
- 프레임당 200ms, 전체 1.2초 루프. 동일한 끝 프레임을 중복 출력하지 않는다.
- 모션·중립 체형을 그대로 유지하고 카메라만 down_left/down_right/up_left/up_right로 변경한다.
- 중립 리그 전체 키 2m, 머리 높이 0.4m로 5등신을 유지한다. 카메라 원근과 굽힌 자세의 겉보기 등신은 별도 검수한다.
- 방향마다 512×512 RGBA 리그 미리보기 6장, 16bit Depth 6장, 마스크 6장, OpenPose 형식 맵 6장과 펼쳐보기 시트를 저장한다.
- OpenPose 맵은 COCO18 호환 리그 투영이다. 실제 검출 결과가 아니며 머리 중심을 nose 슬롯에 사용하고 눈·귀 키포인트는 생략한다.
- `preview.html`은 6→1을 포함한 반복 재생을 제공한다. 원본의 닫힌 끝점·발 회전과 각 구간 변화량은 manifest 및 `foot-validation.json`에 기록한다.

### OpenPose 형식 맵의 실제 생성 방식

현재 `openpose-0001.png` 등의 파일은 OpenPose 검출 모델의 추론 결과가 아니다. `generators/animation/render_pose_frames.py`에서 NumPy로 좌표를 투영하고 Pillow의 `ImageDraw.line`·`ImageDraw.ellipse`로 관절 연결선과 점을 그린다.

생성 순서는 다음과 같다.

1. MoMask가 생성한 HumanML3D-22 3D 관절 모션을 원천으로 사용한다.
2. 승인된 `five-head-walk/v9` 리그에 체형을 보정한 관절 데이터를 재사용한다.
3. 같은 모션을 방향별 카메라의 오른쪽·위쪽 축으로 직교 투영하여 512×512 픽셀 좌표로 변환한다. 이미지에서 관절을 다시 검출하지 않는다.
4. 관절을 COCO18 호환 슬롯에 대응시키고, 검은 배경에 색상 선과 점으로 그린다.
5. Qwen에는 이 래스터 포즈 맵과 베이스라인 이미지를 참조 이미지로 전달한다.

현재 구현은 관절 14개의 점과 연결선 13개를 사용한다. nose 슬롯에는 실제 코가 아닌 리그 머리 중심을 넣으며 눈·귀와 손가락·얼굴 세부 키포인트는 생략한다. 색상과 연결선은 스크립트의 `POSE_EDGE_COLORS`·`POSE_EDGE_INDICES`에서 지정한다. 따라서 정확한 OpenPose 검출 결과나 표준 렌더러와 동일한 출력으로 간주하지 않는다.

리그 미리보기·Depth·마스크는 Blender로 렌더하고, 포즈 맵은 동일한 관절·카메라 설정으로 별도 그린다. 기록과 보고에서는 **MoMask 기반 리그 투영 포즈 맵**으로 명시한다. MoMask가 포즈 PNG를 직접 출력한다거나 OpenPose 모델로 검출했다는 설명은 사용하지 않는다. 별도 검출기를 사용하는 비교 실험은 해당 모델과 출처를 구분해 기록한다.

## 3. 외형 프레임 생성

실험 프롬프트를 `.tmp` 안에 작성한다. 포즈 교체 지시와 함께 **동작 및 화면 기준 방향을 간단히 명시한다**. 포즈 맵만으로 방향과 동작이 전달된다고 가정하지 않는다. 프롬프트 원문은 공개 문서에 복제하지 않는다.

- 참조 역할: 이미지 1은 MoMask 기반 리그 투영 포즈 맵, 이미지 2는 원형 베이스라인이다.
- 동작: 걷기처럼 해당 모션의 행동을 짧게 기술한다.
- 방향: `down_left`는 화면 좌측 하단, `down_right`는 우측 하단, `up_left`는 좌측 상단, `up_right`는 우측 상단을 향한다고 명시한다. 캐릭터 신체 기준의 좌우와 혼동하지 않는다.
- 걷기 프롬프트는 `down_left`, `down_right`, `up_left`, `up_right`의 **4개 방향 키**로 관리한다. 동일 실험의 `.tmp/YYYY-MM-DD_HH-mm-ss/walk-prompts.yaml`을 단일 원본으로 사용한다.
- 24개 프레임을 각각 별도 문구로 관리하지 않는다. 같은 방향의 6프레임에는 해당 방향 키의 동일한 프롬프트를 적용하고 포즈 맵만 교체한다.
- 공통 포즈 교체·동작 표현은 4개 문구에서 일치시키며 방향 표현만 다르게 유지한다. 수정 시 YAML의 버전을 올리고, 실행 기록에 방향 키·버전·파일 해시와 실제 사용 문구의 해시를 남긴다.
- 실행용 `prompt.txt`가 필요하면 선택된 YAML 항목에서 추출한 실행 기록으로 취급한다. 별도 원본처럼 독립 수정하지 않는다.
- 프롬프트 선택을 자동화할 때에는 필수 4방향 키, 비어 있지 않은 문자열, 알 수 없는 필드와 중복 키를 검증하고 잘못된 방향은 즉시 실패시킨다.
- 프레임별 관절 설명이나 외형 수식어를 불필요하게 추가하지 않는다. 세부 자세는 포즈 맵, 캐릭터 외형은 베이스라인으로 전달한다.

```bash
.venv/bin/python generators/animation/prepare_frame_inputs.py \
  --appearance /absolute/path/to/approved-baseline.png \
  --pose /absolute/path/to/pose-run/down_left/openpose-0001.png \
  --prompt-file /absolute/path/to/.tmp/prompt.txt
```

출력된 날짜시간 실험 폴더 경로를 아래 두 인자에 동일하게 지정한다.

```bash
.venv/bin/python generators/animation/generate_qwen_frame.py \
  --steps 10 --reference-order pose-first \
  --output-dir .tmp/YYYY-MM-DD_HH-mm-ss \
  --prompt-file .tmp/YYYY-MM-DD_HH-mm-ss/prompt.txt
```

샌드박스 밖 CUDA에서 고정 Qwen-Image-Edit-2511 BF16을 사용한다. 참조 VAE·출력은 512×512이며 4/10/20스텝을 지원한다. Diffusers 0.37.0의 참조 확대 상수를 실행 중에만 보정하고 종료 시 복구한다. 입력 순서는 OpenPose, 원형 이미지다. 원형 한 장은 모든 프레임에서 같은 출처로 고정한다.

Qwen 동작을 Codex 이미지젠의 동작 참조로 사용해 원형 일러스트의 자세를 바꾸는 경로도 가능하다. 이 단계는 Codex 내장 도구에서 수행하며 API 키 기반 별도 실행기를 사용하지 않는다. 결과와 실험 프롬프트를 동일한 `.tmp` 실험 폴더에 기록한다.

## 4. 검수와 정식 등록

방향·양쪽 다리의 교대·발 회전·캐릭터 외형·전신 잘림을 확인한다. 4방향×6프레임은 같은 순서와 시간을 사용하며 마지막→첫 프레임 연결을 확인한다. 원형과 같은 높이로 맞춘 가이드 비교는 참고 자료이며 자동 미술 승인으로 취급하지 않는다.

채택 지시가 있으면 선택한 결과만 프론트엔드 정식 에셋 폴더와 레지스트리에 등록한다. 생성기 코드는 이 저장소에, 정식 이미지 원본은 프론트엔드에 둔다. 실패 후보와 재사용 근거 없는 프롬프트는 삭제한다. 정식 채택 프롬프트는 비공개 제작 기록으로 옮긴다.

## 실행 환경과 확인 범위

- MoMask·Qwen: 로컬 `.venv` (CUDA PyTorch). Qwen 실험 검증 환경은 diffusers 0.37.0이다.
- 리그 렌더: `.local/blender-runtime/bin/python` (bpy 4.5.3, NumPy, Pillow).
- 소스 이동 뒤에는 컴파일·기본 리그 해시 검증·CLI 도움말·6프레임 재렌더로 연결을 확인한다. MoMask 새 모델 추론과 Qwen 추가 추론을 단순 경로 변경 검사 때문에 반복 실행하지 않는다.
- `old/`의 이전 테스트는 현재 생성기 검증으로 간주하지 않는다.

## 포즈 맵 원본 경로

후속 이미지 생성에는 `assets/animation-loops/five-head-walk-6f/v1/`의 포즈 맵을 직접 사용한다. 기본 선택은 `generators/animation/config/default_walk_loop.yaml`과 `resolve_default_loop.py`로 검증한다.

- `down_left/`, `down_right/`, `up_left/`, `up_right/` 각각의 `openpose-0001.png`~`openpose-0006.png`, 총 24장이 원본이다.
- 투영 관절 좌표는 동일 루프의 `openpose-keypoints.json`에서 읽는다.
- 루프의 `artifact.json`에 등록된 출처·버전·호환 정보·해시를 기준으로 사용한다. 중복 포즈 이미지와 별도 선택 설정은 유지하지 않는다.
- 원본 루프·v9 리그·MoMask 모션은 재사용 제작 자산이다. 사용자 승인 없이 임시 정리 대상으로 취급하지 않는다.
