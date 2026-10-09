# HY-Motion 모션 생성기

## 정사영·원근투영 포즈 출력

`export-vnccs` 신규 작업은 기존 정사영에 원근투영(FOV 30°, 림 음영 추가 없음)을 함께 출력한다. 정사영은 `<방향>/frame-NNNN.png`, 원근투영은 `perspective/<방향>/frame-NNNN.png`이며 각 경로의 `-rgb.png`가 흰 배경 모델 입력이다. ZIP에 두 투영을 모두 포함하고 생성 이력에서 동일 원본 프레임을 두 패널로 동기 비교한다. 기존 URL·명령·저장소와 과거 단일 패널 이력은 유지한다.

투영별 카메라는 선택 구간 전체에 고정한다. 원근투영은 정사영의 중심·방향을 유지하고 `거리 = ortho_scale / (2 × tan(15°))`로 중심 평면의 크기를 맞춘다. 깊이에 따른 크기 차이는 유지되며 극단적인 깊이·동작의 화면 잘림은 검수해야 한다. 재질·조명·리타기팅은 변경하지 않는다. `vnccs-manifest.json`의 `projection_cameras`와 각 이미지의 `projection`으로 구분한다. 과거 투영 설정이 없는 작업 재개는 정사영만 재현한다.

순차 렌더이므로 동시 GPU 적재량을 늘리지 않지만 PNG 수·렌더 시간·저장량은 대략 두 배다. 일반 모션 생성의 관절 미리보기는 그대로이며, 포즈 이미지 추가 출력은 완료된 모션에 `export-vnccs`를 실행한다. 이는 렌더 출력 기능이며 VNCCS의 모든 포즈 추종·체형 보존 품질을 보증하지 않는다.

관리도구의 **애니메이션 도구 → HY-Motion 모션 생성기**를 사용한다. MoMask와 같은 공용 생성이력·로그·브라우저 재생기를 사용하며, 생성은 독립 게이트웨이와 GPU 대기열에서 수행한다. 브라우저 종료는 작업을 중지하지 않는다.

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

일반 생성은 후보 원본 모션 검수용이다. ANNY 변환은 별도 출력 명령으로 실행하며 OpenPose 원천 교체·정식 모션 자산 등록·게임 전달은 수행하지 않는다.

별도 ANNY 리타기팅 작업에는 사용자 검수로 채택된 후처리 `generators.hy_motion.anny_skin_stage.apply_anny_skin_barrier`를 사용한다. 고정 설정은 `config/anny-skin-barrier.yaml`이며 상완→전완→손목 순서, 인접 연결부 제외, 0.5mm 수치 여유를 유지한다. ANNY 리타기팅이 끝난 Blender 파일과 원본 HY-Motion NPZ(`source_motion_path`)를 함께 입력하면 머리 회전 전달도 기본 적용한다. 프레임 수·FPS·원본 FK가 맞지 않으면 실패한다. 일반 GUI/CLI 모션 생성에는 ANNY 렌더를 자동 추가하지 않는다. 사용법과 저장·보간 충돌의 한계는 [ANNY 리타기팅 기준](anny-anatomical-retarget.md#채택된-피부-제약-후처리)을 따른다.

신규 생성은 PNG 미리보기와 함께 방향별 `<direction>.gif` 및 선택 방향을 동기화한 `overview.gif`를 자동 출력한다. 별도 GPU 추론 없이 검수 PNG를 사용하며 GUI 결과의 다운로드 링크와 CLI 상태 응답의 `result.gifs`에서 확인한다. GIF의 10ms 시간 단위에 맞춰 120/130ms를 교대로 기록해 평균 8 FPS와 전체 재생 시간을 보존한다. 무한 반복 재생하되 끝과 시작의 모션을 연결하거나 이동을 제거하지 않는다. 기존 완료 기록은 자동 변경하지 않는다.

## 기록과 실패

### VNCCS PoseStudio용 MakeHuman 포즈 출력

GUI의 **VNCCS PoseStudio 출력 · MakeHuman 자동 변환**에서 완료된 원본 생성 ID와 프레임 범위·간격·방향을 입력한다. CLI도 같은 게이트웨이 명령을 사용한다.

```bash
.venv-management/bin/python tools/manager.py command hy-motion export-vnccs --payload-file /absolute/path/export-request.json --detach
```

요청 JSON은 `{"source_id":"완료된 원본 생성 ID","start_frame":1,"end_frame":300,"frame_step":1,"directions":["down_left","down_right","up_left","up_right"]}` 형태다. 종료 프레임을 생략하면 원본 끝까지 출력하며 프레임은 1부터 시작한다. GUI의 종료 프레임 0 또는 빈 값은 해당 필드를 생략하는 선택이다. 원본 범위를 벗어나거나 중복 방향·알 수 없는 필드는 거절한다. `--detach` 생략 시 공용 CLI가 완료를 기다린다.

신규 출력은 `rig_backend: makehuman`으로 고정한다. `assets/animation-models/vnccs-makehuman-base-v1/`의 공식 VNCCS 기본 메쉬·본·스킨 가중치를 해시 검증하고 사용한다. CC0 라이선스·업스트림 커밋·팩 해시를 자산 manifest에 보존한다. morph를 적용하지 않은 기본 체형이며 PoseStudio의 최종 외형·텍스처·조명과 동일하다고 간주하지 않는다. Y-up→Z-up 좌표 변환 후 HY-Motion body22의 본 방향을 부모 회전 기반 최소 회전으로 전달한다. 본 길이와 부모 오프셋을 유지하며 루트 이동을 보존한다. 손가락·머리·손목 말단은 부모 회전을 상속한다. 축 회전과 자체 충돌은 미검증이다. 선택 프레임은 CUDA Cycles로 렌더한다. 기존 ANNY 기록은 유지한다.

ZIP의 `makehuman-motion.npz`에는 전체 원본 프레임의 전역 본 회전·위치·기준 본 좌표·이름이 들어간다. `retarget-quality.json`은 원본 관절 방향 대비 최대 각도 오차와 검증 한계를 기록한다. 새 manifest의 `conditioning_status`는 `makehuman-base-retarget-candidate`이다. 본 방향 일치는 이미지 생성 모델의 체형·포즈 추종 보장을 의미하지 않는다.

출력은 방향별 512×512 RGBA 원본 PNG와 흰 배경을 알파 합성한 RGB `frame-NNNN-rgb.png`, `vnccs-package.zip`, `vnccs-manifest.json`, `retarget-quality.json`이다. RGB 입력은 ZIP에서 가져오며 manifest의 `images[].model_input_path`·`model_input_sha256`으로 식별·검증한다. image1에는 RGB 포즈, image2에는 단일 전신 캐릭터 참조를 사용한다. 선택 구간·방향에 공통 크기의 고정 카메라를 사용하고 기존 방향 규약을 유지한다. VNCCS 이미지 생성의 포즈 추종·체형 보존은 미검증이다. VNCCS/Qwen 추론은 실행하지 않는다.

별도 생성 ID와 실행 시도를 만들어 기존 결과를 덮어쓰지 않는다. GUI·CLI의 기존 이력·상태·로그·취소·재개 계약을 공유한다. 실패 후 재개도 새 시도에 기록한다. 패키지는 후보 산출물이므로 정식 자산에 자동 등록하지 않는다.

작업 ID는 공용 게이트웨이 형식 `YYYY-MM-DD_HH-mm-ss-xxxxxxxx`이며, 실제 경로는 `.tmp/test/hy-motion/YYYY-MM-DD_HH-mm-ss/xxxxxxxx/`다. 실행 시도별 산출물은 그 아래 `attempts/`에 누적한다. 이력 인덱스는 `.tmp/manager-current/hy-motion/`에 둔다. GUI·CLI가 같은 요청·상태·로그·결과를 읽는다.

동작 프롬프트 원문·단어 수·해시는 `prompt.json`, 인코더의 실제 chat template 포함 입력은 시도 폴더의 `encoder-prompt.json`에 보존한다. 기본 프롬프트·카메라는 `generators/hy_motion/config/defaults.yaml`, 공식 인코더 시스템 문구는 `config/encoder-system.txt`로 버전 관리한다. 사용자 프롬프트를 인코더가 재작성하는 별도 생성 과정은 없다.

`history-reset`은 사용자 명령으로만 실행하며 목록 인덱스만 제거한다. 실행 중에는 거절하고 결과·로그는 보존한다. 초기화한 목록을 작업 종료·재개 시 자동 복원하지 않는다. 오류 원인과 traceback은 `worker.log`, 최종 상태는 `status.json`에 남는다. 5초 heartbeat는 단계·경과 시간·산출물 수를 기록한다. 예상 시간 근거가 없으면 남은 시간·완료 시각을 계산 중으로 표시한다.

실행 중 예상 시간은 동일 설정·길이·방향·프롬프트 단어 수의 최근 완료 실행(최대 5개)의 중앙값을 사용한다. 모델 준비·GPU 대기·표본 부족·예상 시간 초과 상태에서는 근거와 함께 계산 중으로 표시한다. 최종 Qwen 입력은 GUI에서 펼쳐 볼 수 있으며 실행 시 고정 tokenizer의 실제 입력과 대조한다.

공식 자료: [HY-Motion 소스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0), [모델 라이선스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/main/License.txt). 모델 배포·사용에는 해당 라이선스가 적용된다.
