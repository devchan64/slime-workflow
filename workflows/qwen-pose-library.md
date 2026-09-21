# Qwen 2511 포즈 편집 라이브러리

`generators/animation/qwen_pose/`가 프롬프트 로딩·참조 검증·고정 모델 추론을 제공하고 `generate_qwen_frame.py`는 CLI만 담당한다. 모델·revision·512px·seed·CFG·VAE 설정은 코드에 고정한다. 기본 추론은 10스텝이며 4/10/20만 허용한다. GPU 작업은 샌드박스 밖에서 실행하고 CUDA 부재 시 즉시 실패한다. CPU weight offload는 CPU 추론이 아니다.

## 기준과 옵션 프롬프트

프로필 YAML은 `id`, 양의 정수 `version`, `templates`만 갖는다. `templates`에는 `rig`와 `openpose`를 각각 정의하며 각 항목은 다음 세 필드만 허용한다.

- `pose_prompt`: 기준 포즈 교체 지시. `{character_image_index}`와 `{pose_image_index}`만 치환한다. **기준 문구 변경 주의: 변경 시 버전을 올리고 동일 참조로 재검증한다.**
- `optional_prompt`: 외형·복장 유지 등 포즈 외 지시. 치환 필드 없는 문자열이며 빈 문자열도 허용한다. 기준 문구에 합치지 않는다.
- `validation_status`: `unverified` 또는 `pose-change-success`. 후자는 기록된 실험의 상태이며 새로운 순서·옵션 조합의 성공을 보증하지 않는다.

관리 원본은 비공개 설계 저장소의 `prompts/qwen-edit-2511-pose-profile-v1.yaml`이다. 공개 라이브러리는 해당 저장소 경로를 하드코딩하거나 직접 의존하지 않는다. 운영자가 파일을 명시적으로 전달하고 실행 결과에 프로필 ID·버전·해시·옵션 사용 여부와 렌더된 프롬프트 해시를 기록한다. 완성 프롬프트는 실행 폴더의 `prompt.txt`에 남는다. 중복 키·누락·알 수 없는 필드·미지원 값은 실패시킨다.

## CLI

```bash
.venv/bin/python generators/animation/generate_qwen_frame.py \
  --output-dir .tmp/새로운-한국시간-실행폴더 \
  --prompt-profile /전달받은/기준-프롬프트.yaml \
  --pose-kind rig \
  --character-image /준비된/standing-reference.png \
  --pose-image /준비된/rig-reference.png \
  --steps 10 --reference-order standing-first
```

입력은 불투명 RGB/RGBA 512×512 PNG다. 방향별 베이스라인 크롭을 흰 배경에 준비하며 기본 포즈 참조는 같은 방향·프레임의 셰이딩된 MoMask 리그 렌더다. OpenPose는 사용자가 명시한 별도 비교 실험에서만 선택한다. 라이브러리는 자동 크롭·리사이즈·포즈 추정을 하지 않는다. `--pose-kind` 기본값은 `rig`다. OpenPose 비교 실험에서만 `--pose-kind openpose`를 명시한다. 경로 생략 시 출력 폴더의 `standing-reference.png`와 `rig-reference.png` 또는 `openpose-reference.png`를 사용한다.

`--reference-order pose-first`는 입력 순서와 기준 프롬프트의 이미지 번호를 함께 뒤집는다. `--omit-optional-prompt`는 옵션만 제외한다. 실험용 완성 문구는 `--prompt-file`로 대체할 수 있으며 프로필과 동시 지정할 수 없다. 완성 문구의 참조 번호는 자동 수정하지 않으며 옵션 제외 플래그와 함께 사용하지 않는다. 과거 OpenPose 실험 재현 시에는 반드시 `--pose-kind openpose`를 명시한다. 리그 실패를 이유로 자동 전환하지 않는다.

## 라이브러리 호출

저장소 루트를 Python import 경로에 둔다. `generators.animation.qwen_pose`의 `load_pose_prompt(profile_path, pose_kind, reference_order, include_optional_prompt=True)`가 문구와 출처를 반환한다. `execute_pose_generation`에 `trial_output_root`, `prompt_text_value`, `character_image_path`, `pose_reference_path`, `pose_reference_kind`, `selected_reference_order`, `selected_inference_steps`, `prompt_source_record`를 키워드 인자로 전달한다. 반환값은 저장된 `result.json`과 같은 결과 기록이다.

완료 시 result.png/result.json, prompt.txt, execution.log를 남긴다. 기존 실행은 덮어쓰지 않는다. 역할별 경로·해시를 기록해 리그를 OpenPose로 오기하지 않는다. 참조 VAE 전역 설정 충돌을 막기 위해 동일 프로세스 동시 추론은 거부한다. 오류 시 traceback과 로그 tail, 실행 중 5초 heartbeat를 출력한다. 결과의 포즈·방향·외형을 검수한 뒤 [아이덴티티 복구](character-pose-repair.md)와 [최종 시트 패킹](character-animation-export.md)을 진행한다.

## AnyPose 고정 경로

[전용 AnyPose 실행기](qwen-anypose.md)는 Base/Helper/Lightning을 적용한다. 기존 무 LoRA 경로의 기본 설정은 유지하며, 별도 실행기를 사용해 설정 혼용을 방지한다.
