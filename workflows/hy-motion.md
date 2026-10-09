# HY-Motion 모션 생성기

## 충돌 인접관계 편집

`generators/hy_motion/config/collision-relations.yaml`을 원본으로 사용한다. 기본 정책은 `check`이며 `rules`에서 팔 본 목록·몸통 본 목록·최대 부모 간선 수로 초기 허용 범위를 지정한다. `pair_overrides`의 `{arm_bone, body_bone, policy, reason}`은 그룹 규칙보다 우선하며 `policy: allow`는 검사 제외, `check`는 검사 복원이다. 겹치는 그룹·중복 예외·없는 본·순환 관계는 거절한다. 기존 8개 허용 쌍을 초기값으로 유지하며 자동 확장하지 않는다.

예: `pair_overrides: [{arm_bone: upperarm01.L, body_bone: spine01, policy: check, reason: 접합부 재검증}]`. 변경 후 같은 원본 모션을 재출력해 비교한다. 단계 시작 시 읽은 규칙·SHA-256·전체 리그 부모 관계는 `retarget/final/collision-relations.json` 및 품질 기록에 보존한다. 전체 관계를 저장하지만 현재 충돌 검사는 팔·손 대 몸통·골반·다리 범위이며 전신 충돌 검사가 아니다. 본 쌍별 최소 간격과 침범 깊이는 아직 개별 설정으로 지원하지 않는다.

생성 이력에서 작업을 선택하면 `선택 이력 삭제`와 대상 ID 확인 단계를 제공한다. CLI도 `hy-motion history-delete <id>` 명령을 지원한다. 선택한 목록 항목만 제거하고 모션·렌더·로그 파일은 보존하며 실행·대기 중인 대상은 거절한다.

## 예상 시간 표시

GUI·CLI는 작업 서비스의 공용 시간 추정 계약을 사용한다. 전체 작업은 동일 모델 설정·렌더 설정·길이·방향·프롬프트 단어 수의 최근 최대 5개 완료 기록 중앙값으로 추정하며 GPU 대기는 제외한다. 렌더 중에는 현재 시도의 최근 최대 5개 이미지 저장 간격을 우선 사용한다. 이 경우 예상 완료 시각은 **렌더 단계만** 대상으로 하며 후속 OpenPose·패키징은 제외한다고 표시한다. 전체 소요 시간을 모르는 경우 숫자를 만들지 않는다.

예상 총 시간·남은 시간·완료 시각·예상 진행률과 표본 수·갱신 시각·범위를 표시한다. 렌더 완료 장수는 별도의 실측 진행률이다. 상태 조회 및 5초 heartbeat에서 갱신하며, 무표본은 계산 조건을 안내하고 예상 시간을 초과하면 지연·재계산 대기로 표시한다. 완료·실패·취소 작업에는 종료 상태를 반환한다.

## 정사영·원근투영 포즈 출력

척추·목은 원본 관절 방향을 직접 전달한다(`absolute_direction`). 기본 피부 제약은 이전 안전 팔 자세에서 목표 회전으로 진행하다 첫 충돌 직전에 멈춘다. 충돌 회피를 위해 바깥쪽·반대 방향으로 돌리는 보정은 하지 않는다. 첫 목표 자세부터 충돌하거나 몸통 이동으로 이전 팔 자세가 충돌하면 안전한 시작점이 없으므로 명확한 오류로 종료한다. 이산 탐색은 연속 시간 전체의 비관통을 보장하지 않는다. 실행 기록의 프로필 내용·해시와 품질 경고를 확인한다.

모션 생성 시 ANNY 렌더를 자동 실행하며 기존 정사영에 원근투영(FOV 30°, 림 음영 추가 없음)을 함께 출력한다. 정사영은 `<방향>/frame-NNNN.png`, 원근투영은 `perspective/<방향>/frame-NNNN.png`이며 각 경로의 `-rgb.png`가 흰 배경 모델 입력이다. ZIP에 두 투영을 모두 포함하고 생성 이력에서 동일 원본 프레임을 두 패널로 동기 비교한다. 기존 URL·명령·저장소와 과거 단일 패널 이력은 유지한다.

투영별 카메라는 선택 구간 전체에 고정한다. 원근투영은 정사영의 중심·방향을 유지하고 `거리 = ortho_scale / (2 × tan(15°))`로 중심 평면의 크기를 맞춘다. 깊이에 따른 크기 차이는 유지되며 극단적인 깊이·동작의 화면 잘림은 검수해야 한다. 재질·조명은 기존 ANNY 기준을 유지하며 스킨 충돌·회전 제약을 기본 적용한다. `vnccs-manifest.json`의 `projection_cameras`와 각 이미지의 `projection`으로 구분한다. 과거 투영 설정이 없는 작업 재개는 정사영만 재현한다.

순차 렌더이므로 동시 GPU 적재량을 늘리지 않지만 PNG 수·렌더 시간·저장량은 대략 두 배다. 일반 모션 생성은 원본 30 FPS의 선택 방향 전체 프레임에 ANNY·OpenPose를 함께 출력한다. 완료된 과거 모션의 재출력에는 호환 명령 `export-vnccs`를 사용할 수 있다. 이는 렌더 출력 기능이며 VNCCS의 모든 포즈 추종·체형 보존 품질을 보증하지 않는다.

관리도구의 **애니메이션 도구 → HY-Motion 모션 생성기**를 사용한다. 공용 생성이력·로그·브라우저 재생기를 사용하며, 생성은 독립 게이트웨이와 GPU 대기열에서 수행한다. 브라우저 종료는 작업을 중지하지 않는다.

## 준비와 실행

GPU 실행 환경 `.venv`에 CUDA PyTorch와 `generators/hy_motion/requirements.txt` 의존성을 준비한다. GUI는 기존 `.venv-management`를 사용한다. 게이트웨이는 샌드박스 밖에서 실행한다.

```bash
.venv/bin/python -m pip install -r generators/hy_motion/requirements.txt
./scripts/run_management_gateway.sh
./scripts/run_management_gui.sh --watch
python3 tools/manager.py command hy-motion prepare
python3 tools/manager.py command hy-motion model-status
python3 tools/manager.py command hy-motion generate --prompt 'A person walks forward.' --duration-seconds 3 --seed 10107 --directions down_left down_right up_left up_right --detach
python3 tools/manager.py command hy-motion history
python3 tools/manager.py command hy-motion status GENERATION_ID
python3 tools/manager.py command hy-motion logs GENERATION_ID
python3 tools/manager.py command hy-motion cancel GENERATION_ID
python3 tools/manager.py command hy-motion resume GENERATION_ID
```

`prepare`는 준비 작업 ID를 반환한다. 이력에서 완료 여부와 로그를 확인한 뒤 생성한다. 생성의 `--detach`를 생략하면 공용 CLI가 완료까지 대기하며 Ctrl+C로 취소 요청을 보낸다. 입력 파일은 `--prompt-file`로 지정한다. 취소·실패 작업의 재개는 저장된 입력·시드로 새 시도를 시작하며 이전 시도 산출물을 보존한다. 모델 내부 추론 스텝부터 이어 실행하는 기능은 아니다.

## 고정 모델과 메모리

GUI의 **동작 프리셋**에서 대기·걷기를 선택할 수 있다. 선택은 프롬프트와 길이만 변경하며 생성은 별도 버튼으로 실행한다. 시드·방향·태그는 유지한다. 원본은 `generators/hy_motion/config/motion-presets.yaml`에서 추적한다. 대기는 양발을 딛고 팔을 내린 채 천천히 깊게 숨을 들이쉬고 내쉬는 동작이며, 모델의 제자리 정지나 무봉제 루프를 보장하지 않는다. 걷기는 MoMask `standing-loops-v1.json` 버전 30의 걷기 프롬프트를 채택했다. GUI·CLI 모두 선택된 실제 프롬프트와 길이를 기존 `generate` 계약으로 전달한다.

- HY-Motion-1.0-Lite, 50스텝, CFG 5, 샘플 1개를 사용한다. 모델은 입력에서 선택할 수 없다.
- Qwen3-8B는 BF16(미지원 GPU에서는 FP16) 가중치를 CPU RAM에 저장하고 Accelerate 레이어 오프로드로 CUDA에서 연산한다. CLIP 및 모션 모델은 앞 단계 인코더 해제 후 순차 로딩한다. CPU 추론은 사용하지 않는다.
- 프롬프트 재작성과 길이 자동 추정은 사용하지 않는다. 동작 지시는 1~29단어, 시드는 uint32 범위다. 상한은 `MAXIMUM_MOTION_FRAMES = 360`으로 정의하며 고정 30 FPS에서 최대 길이 12초를 계산한다. GUI·CLI 길이 입력은 1~12초를 허용한다. 동작별 전환 시점은 보장하지 않으며 재생 감속으로 길이를 늘리지 않는다. CLIP 77토큰 한도를 넘기면 자르지 않고 실패한다.
- 8GB 구성의 초기 GPU 예약은 7000MiB다. 이는 보장이 아닌 초기 설정이며, 이후 공용 실행기가 성공 실행의 실측 peak를 사용한다. 첫 실행 전 시스템 RAM·가용 VRAM을 확인한다.
- 공식 소스와 모델 SHA는 코드·설정에 고정한다. 모델·리그·통계 캐시는 `.model/hy-motion/`에 준비하며, 준비 manifest에 파일별 SHA-256과 모델 snapshot 경로를 보존한다. 실행 중 외부 모델로 자동 대체하지 않는다.

2026-10-08 로컬 검증: RTX 5070 Laptop 8GB·시스템 RAM 약 61GiB에서 3초·50스텝·4방향 생성에 15.67초가 걸렸다. 공용 실행기의 GPU 프로세스 표본 최대는 3224MiB, PyTorch 최대 할당은 2986MiB였다. 다운로드 시간은 제외하며 표본형 GPU 측정은 순간 최대값을 놓칠 수 있다. 모든 8GB GPU·RAM 구성·프롬프트에서 같은 성능을 보장하는 수치는 아니다.

## 원본과 미리보기

루트 이동 제거·방향 고정·발 접촉 보정·루프 연결을 추가하지 않는다. 공식 모델 자체의 디코딩·스무딩은 유지한다. 방향은 같은 생성 모션에 대한 카메라 투영이다. 전체 클립에 같은 카메라 범위를 사용하므로 이동 동작도 그대로 보인다.

원본 30 FPS NPZ에는 `rot6d`, `transl`, `root_rotations_mat`, `latent_denorm`, 공식 `keypoints3d`와 루트 평행이동을 적용해 복원한 `world_joints`를 보존한다. `keypoints3d`는 공식 Wooden 리그 52관절이며 원본에서 평행이동이 빠져 있으므로 이를 월드 좌표로 오인하지 않는다. 미리보기는 `world_joints`의 몸체 22관절을 8 FPS로 표본화한다. 재생·프레임 이동은 브라우저에서 처리한다. 원본 NPZ와 출처 JSON은 결과 재생 영역의 링크로 내려받는다.

일반 생성은 원본 NPZ를 보존한 뒤 ANNY 변환·렌더·OpenPose를 자동 실행한다. 새 작업은 `render-config.json`을 접수 시 고정한다. 같은 시도 폴더의 `anny/`에 리그·품질 기록·PNG·ZIP을 저장하고 `result.rendering`으로 연결한다. 렌더 단계 실패 시 작업 전체를 실패로 표시하며 원본 NPZ와 로그는 남긴다. 기존 완료 결과는 변경하지 않는다. 과거 모션 작업을 재개하면 현재 ANNY 설정으로 자동 출력을 적용하고 해당 시도에 설정을 기록한다. 정식 모션 자산 등록·게임 전달은 수행하지 않는다.

기본 파이프라인은 위치 전달 → 팔·손 방향 전달 → 원본 회전 전달 → 스킨 충돌 기반 회전 제한 → ANNY 렌더 순서다. `config/anny-adjacency-barrier.yaml`을 기본 적용하며 쇄골·어깨에서 손목까지 근위→원위 순서로 처리한다. 첫 비인접 충돌 전에 회전을 제한하며 0.5mm 수치 여유와 시간 보간 검사를 사용한다. 이 프로필은 검수 후보 상태이며 완전한 비관통이나 해부학적 각도 제한을 보증하지 않는다. 관절별 고정 각도 제한 기능과 혼동하지 않는다. 머리 회전도 원본에서 전달한다. 프레임 수·FPS·원본 FK가 맞지 않으면 실패한다.

신규 생성은 PNG 미리보기와 함께 선택 방향을 동기화한 `overview.gif`만 자동 출력한다. 방향별 `<direction>.gif` 개별 생성과 GUI 다운로드 표시는 폐기했다. 별도 GPU 추론 없이 검수 PNG를 사용하며 GUI 결과의 다운로드 링크와 CLI 상태 응답의 `result.gifs`에서 확인한다. GIF의 10ms 시간 단위에 맞춰 120/130ms를 교대로 기록해 평균 8 FPS와 전체 재생 시간을 보존한다. 무한 반복 재생하되 끝과 시작의 모션을 연결하거나 이동을 제거하지 않는다. 기존 완료 기록과 파일은 자동 변경하거나 삭제하지 않는다.

## 기록과 실패

### ANNY 자동 출력 및 기존 모션 재출력

새 모션은 별도 출력 버튼 없이 ANNY·OpenPose와 기본 제약을 자동 적용해 저장한다. GUI의 별도 재출력 패널은 제공하지 않는다. 과거 모션 재출력은 호환 CLI 명령으로만 유지하며 AnyPose LoRA 전용 렌더 옵션은 제공하지 않는다.

```bash
.venv-management/bin/python tools/manager.py command hy-motion export-vnccs --payload-file /absolute/path/export-request.json --detach
```

요청 JSON은 `{"source_id":"완료된 원본 생성 ID","start_frame":1,"end_frame":300,"frame_step":1,"directions":["down_left","down_right","up_left","up_right"]}` 형태다. 종료 프레임을 생략하면 원본 끝까지 출력하며 프레임은 1부터 시작한다. GUI의 종료 프레임 0 또는 빈 값은 해당 필드를 생략하는 선택이다. 원본 범위를 벗어나거나 중복 방향·알 수 없는 필드는 거절한다. `--detach` 생략 시 공용 CLI가 완료를 기다린다.

MakeHuman 리그 변환·렌더·가져오기 구현은 폐기했다. 과거 MakeHuman 완료 결과의 조회는 유지하지만 해당 설정의 재개는 명확히 거절한다. 등록된 이전 리그 자산 자체는 삭제하지 않는다. 신규 출력은 `rig_backend: anny` 고정이며 `anny-neutral-v4` 기준 리그의 해시를 검증한다.

ZIP에는 제약 적용된 `anny-rig.blend`, 정사영·원근투영 RGBA/RGB PNG, `-openpose.png`·`-openpose.json`, manifest와 품질 기록을 포함한다. OpenPose는 같은 카메라로 투영한 COCO18 신체 관절이며 코·눈·귀는 결측 처리한다. 1은 투영점 존재를 뜻하며 이미지 검출 확률이나 가림 판정이 아니다. 출처는 HY-Motion → ANNY 제약 적용 관절로 기록한다. UI는 관절 미리보기의 같은 원본 프레임에 두 렌더·두 OpenPose를 동기 표시한다.

출력은 방향별 512×512 RGBA 원본 PNG와 흰 배경을 알파 합성한 RGB `frame-NNNN-rgb.png`, `vnccs-package.zip`, `vnccs-manifest.json`, `retarget-quality.json`이다. RGB 입력은 ZIP에서 가져오며 manifest의 `images[].model_input_path`·`model_input_sha256`으로 식별·검증한다. image1에는 RGB 포즈, image2에는 단일 전신 캐릭터 참조를 사용한다. 선택 구간·방향에 공통 크기의 고정 카메라를 사용하고 기존 방향 규약을 유지한다. VNCCS 이미지 생성의 포즈 추종·체형 보존은 미검증이다. VNCCS/Qwen 추론은 실행하지 않는다.

별도 생성 ID와 실행 시도를 만들어 기존 결과를 덮어쓰지 않는다. GUI·CLI의 기존 이력·상태·로그·취소·재개 계약을 공유한다. 실패 후 재개도 새 시도에 기록한다. 패키지는 후보 산출물이므로 정식 자산에 자동 등록하지 않는다.

작업 ID는 공용 게이트웨이 형식 `YYYY-MM-DD_HH-mm-ss-xxxxxxxx`이며, 실제 경로는 `.tmp/test/hy-motion/YYYY-MM-DD_HH-mm-ss/xxxxxxxx/`다. 실행 시도별 산출물은 그 아래 `attempts/`에 누적한다. 이력 인덱스는 `.tmp/manager-current/hy-motion/`에 둔다. GUI·CLI가 같은 요청·상태·로그·결과를 읽는다.

동작 프롬프트 원문·단어 수·해시는 `prompt.json`, 인코더의 실제 chat template 포함 입력은 시도 폴더의 `encoder-prompt.json`에 보존한다. 기본 프롬프트·카메라는 `generators/hy_motion/config/defaults.yaml`, 공식 인코더 시스템 문구는 `config/encoder-system.txt`로 버전 관리한다. 사용자 프롬프트를 인코더가 재작성하는 별도 생성 과정은 없다.

`history-reset`은 사용자 명령으로만 실행하며 목록 인덱스만 제거한다. 실행 중에는 거절하고 결과·로그는 보존한다. 초기화한 목록을 작업 종료·재개 시 자동 복원하지 않는다. 오류 원인과 traceback은 `worker.log`, 최종 상태는 `status.json`에 남는다. 5초 heartbeat는 단계·경과 시간·산출물 수를 기록한다. 예상 시간 근거가 없으면 남은 시간·완료 시각을 계산 중으로 표시한다.

실행 중 예상 시간은 동일 설정·길이·방향·프롬프트 단어 수의 최근 완료 실행(최대 5개)의 중앙값을 사용한다. 모델 준비·GPU 대기·표본 부족·예상 시간 초과 상태에서는 근거와 함께 계산 중으로 표시한다. 최종 Qwen 입력은 GUI에서 펼쳐 볼 수 있으며 실행 시 고정 tokenizer의 실제 입력과 대조한다.

공식 자료: [HY-Motion 소스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0), [모델 라이선스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/main/License.txt). 모델 배포·사용에는 해당 라이선스가 적용된다.
