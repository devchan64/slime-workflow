# AnyPose LoRA 도입 및 실행

기반 Qwen Edit 2511은 유지하고 AnyPose 전용 실행기로 포즈 전이를 검증한다. 기본 포즈 참조는 승인된 MoMask 리그 렌더다. OpenPose로 자동 전환하지 않는다. 기존 LoRA 없는 실행기는 비교·재현 경로로 유지한다.

## 고정 구성

| 항목 | 값 |
| --- | --- |
| AnyPose Base / Helper | lilylilith/AnyPose, 각각 강도 0.7 |
| AnyPose revision | 27c4b1f7688940d39767e652fe8d87faf44a0881 |
| Lightning | lightx2v/Qwen-Image-Edit-2511-Lightning, 4steps V1.0 bf16, 강도 1.0 |
| Lightning revision | d74eba145674fd7e31b949324e148e21e7118abd |
| 추론 | 4스텝, true_cfg_scale=1.0, seed=10107 |
| 이미지 | 입력/출력 512×512, 참조 VAE 512×512, 조건 인코딩 384×384 |
| 입력 순서 | 이미지 1 캐릭터 크롭, 이미지 2 동일 방향·프레임 리그 |

[AnyPose 모델 카드](https://huggingface.co/lilylilith/AnyPose)는 Base/Helper 0.7과 Lightning 4스텝 및 캐릭터 먼저 입력을 안내한다. true_cfg_scale=1.0은 [공개 실행 예제](https://huggingface.co/spaces/abidlabs/Qwen-Image-Edit-2511-AnyPose/blob/main/app.py)의 초기값을 사용한다. guidance_scale=1.0 인자는 기반 모델의 guidance_embeds=false로 무시된다. 512px/VAE 조정은 기존 로컬 실험 설정이며 모델 카드의 모든 조건을 그대로 재현했다는 뜻은 아니다.

## 준비

```bash
.venv/bin/python -m generators.animation.qwen_pose.anypose
```

샌드박스 밖 CUDA 환경에서 실행한다. 코드에 고정된 파일만 `.model/qwen-anypose/<repository>/<revision>/`에 받는다. 공식 LFS 파일 크기와 SHA-256을 검증한 뒤 임시 .part를 최종 파일로 이동한다. 기존 검증 파일은 재사용하며 손상 캐시·미완료 파일은 명시적 오류로 중단한다. 가중치 3개 약 1.44GB를 추가하며 커밋하지 않는다. 결과는 `.model/qwen-anypose/manifest.json`, 로그는 prepare.log다. 5초 heartbeat와 실패 traceback/tail을 남긴다. 추론 중 자동 다운로드나 무 LoRA 전환은 하지 않는다.

AiBook의 고정 revision·필요 파일만 다운로드·해시 검증 원칙을 따르되 이 저장소의 가중치 위치 정책인 `.model`을 적용한다. 모델 카드 기준 양쪽 어댑터 저장소의 라이선스는 Apache-2.0이다.

## 단일 프레임 검증

새 `.tmp/한국시간/`에 불투명 RGB 512px `standing-reference.png`, `rig-reference.png`, `prompt.txt`를 준비한다. 도입 검증에서는 고정 revision 모델 카드의 포즈 전이 지시를 먼저 사용하고 프롬프트 출처·해시를 기록한다. 기존 짧은 rig 기준 프롬프트와 혼합하지 않는다. 프롬프트 변경 비교는 별도 실행으로 남긴다.

```bash
.venv/bin/python generators/animation/generate_qwen_anypose_frame.py \
  --output-dir .tmp/한국시간-실행폴더 \
  --prompt-file .tmp/한국시간-실행폴더/prompt.txt
```

실행기는 모델·어댑터·강도·스텝을 사용자 입력으로 선택하지 않는다. 어댑터를 모두 읽고 set_adapters로 적용한 뒤 CUDA 추론한다. 결과 기록은 각 어댑터 저장소·revision·파일·해시·강도 및 입력 순서를 포함한다. 기존 true CFG 4.0·10스텝·무 LoRA와 여러 조건이 달라지므로 단일 변수 A/B라고 부르지 않는다.

결과를 리그와 비교해 다리 연결·방향·외형을 검수하고 같은 관리번호의 새 이력에 입력·출력·로그·소스·모델 정보와 판정을 남긴다. 가중치 로드 성공은 이미지 품질 승인이나 프론트엔드 채택을 뜻하지 않는다. 최종 시트 반영에는 별도 사용자 채택과 패킹·앵커 검수가 필요하다.

## Lightning 제외 10스텝 경로

사용자 지정 비교 경로는 `generate_qwen_anypose_standard_frame.py`다. AnyPose Base/Helper 각각 0.7만 로드하며 Lightning은 검증 대상·로드·적용에서 제외한다. 10스텝, true_cfg_scale=4.0, 나머지 입력·seed·512px는 유지한다. 기존 4스텝 CFG 1.0 경로와 구분하며 스텝만 바꾼 비교로 기록하지 않는다. 모델 캐시에 있는 Lightning 파일은 삭제하지 않고 기존 경로 재현에 유지한다.

```bash
.venv/bin/python generators/animation/generate_qwen_anypose_standard_frame.py \
  --output-dir .tmp/새로운-실행폴더 \
  --prompt-file .tmp/새로운-실행폴더/prompt.txt
```

`result.json`의 execution_preset은 anypose-standard-v1, lightning_lora는 false, adapters에는 AnyPose 두 개만 있어야 한다.

## Base/Helper 강도 비교

비Lightning 생성기는 `--base-strength`, `--helper-strength`로 어댑터 적용 강도를 각각 지정한다. 기본값은 모두 0.7이며 모델·리비전은 바뀌지 않는다. 유한 숫자 0~1.5만 허용하며 이 범위는 입력 제한이지 품질 권장 범위가 아니다.

참조·프롬프트·시드·10스텝·CFG 4.0을 고정하고 (1.0, 0.7), (0.7, 1.0), (1.0, 1.0)을 기존 (0.7, 0.7)과 비교한다. 강도 증가가 포즈 정확도 증가를 보장하지 않으므로 다리 전후 관계·방향·신체 비율·외형을 함께 검수한다. 실제 적용 강도는 각 `result.json`의 `adapters`에 보관한다. 실험 원본·실행 코드·비교 자료는 실행별 `.tmp`에 유지하며 품질 승인 전 기본값이나 프론트엔드 에셋을 변경하지 않는다.
