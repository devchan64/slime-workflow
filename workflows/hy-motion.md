# HY-Motion 모션 생성기

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

- HY-Motion-1.0-Lite, 50스텝, CFG 5, 샘플 1개를 사용한다. 모델은 입력에서 선택할 수 없다.
- Qwen3-8B는 BF16(미지원 GPU에서는 FP16) 가중치를 CPU RAM에 저장하고 Accelerate 레이어 오프로드로 CUDA에서 연산한다. CLIP 및 모션 모델은 앞 단계 인코더 해제 후 순차 로딩한다. CPU 추론은 사용하지 않는다.
- 프롬프트 재작성과 길이 자동 추정은 사용하지 않는다. 동작 지시는 1~29단어, 길이는 1~4.9초, 시드는 uint32 범위다. CLIP 77토큰 한도를 넘기면 자르지 않고 실패한다.
- 8GB 구성의 초기 GPU 예약은 7000MiB다. 이는 보장이 아닌 초기 설정이며, 이후 공용 실행기가 성공 실행의 실측 peak를 사용한다. 첫 실행 전 시스템 RAM·가용 VRAM을 확인한다.
- 공식 소스와 모델 SHA는 코드·설정에 고정한다. 모델·리그·통계 캐시는 `.model/hy-motion/`에 준비하며, 준비 manifest에 파일별 SHA-256과 모델 snapshot 경로를 보존한다. 실행 중 외부 모델로 자동 대체하지 않는다.

2026-10-08 로컬 검증: RTX 5070 Laptop 8GB·시스템 RAM 약 61GiB에서 3초·50스텝·4방향 생성에 15.67초가 걸렸다. 공용 실행기의 GPU 프로세스 표본 최대는 3224MiB, PyTorch 최대 할당은 2986MiB였다. 다운로드 시간은 제외하며 표본형 GPU 측정은 순간 최대값을 놓칠 수 있다. 모든 8GB GPU·RAM 구성·프롬프트에서 같은 성능을 보장하는 수치는 아니다.

## 원본과 미리보기

루트 이동 제거·방향 고정·발 접촉 보정·루프 연결을 추가하지 않는다. 공식 모델 자체의 디코딩·스무딩은 유지한다. 방향은 같은 생성 모션에 대한 카메라 투영이다. 전체 클립에 같은 카메라 범위를 사용하므로 이동 동작도 그대로 보인다.

원본 30 FPS NPZ에는 `rot6d`, `transl`, `root_rotations_mat`, `latent_denorm`, 공식 `keypoints3d`와 루트 평행이동을 적용해 복원한 `world_joints`를 보존한다. `keypoints3d`는 공식 Wooden 리그 52관절이며 원본에서 평행이동이 빠져 있으므로 이를 월드 좌표로 오인하지 않는다. 미리보기는 `world_joints`의 몸체 22관절을 8 FPS로 표본화한다. 재생·프레임 이동은 브라우저에서 처리한다. 원본 NPZ와 출처 JSON은 결과 재생 영역의 링크로 내려받는다.

이 생성기는 후보 모션 검수용이다. ANNY 리타기팅·OpenPose 원천 교체·정식 모션 자산 등록·게임 전달은 수행하지 않는다.

신규 생성은 PNG 미리보기와 함께 방향별 `<direction>.gif` 및 선택 방향을 동기화한 `overview.gif`를 자동 출력한다. 별도 GPU 추론 없이 검수 PNG를 사용하며 GUI 결과의 다운로드 링크와 CLI 상태 응답의 `result.gifs`에서 확인한다. GIF의 10ms 시간 단위에 맞춰 120/130ms를 교대로 기록해 평균 8 FPS와 전체 재생 시간을 보존한다. 무한 반복 재생하되 끝과 시작의 모션을 연결하거나 이동을 제거하지 않는다. 기존 완료 기록은 자동 변경하지 않는다.

## 기록과 실패

작업 ID는 공용 게이트웨이 형식 `YYYY-MM-DD_HH-mm-ss-xxxxxxxx`이며, 실제 경로는 `.tmp/test/hy-motion/YYYY-MM-DD_HH-mm-ss/xxxxxxxx/`다. 실행 시도별 산출물은 그 아래 `attempts/`에 누적한다. 이력 인덱스는 `.tmp/manager-current/hy-motion/`에 둔다. GUI·CLI가 같은 요청·상태·로그·결과를 읽는다.

동작 프롬프트 원문·단어 수·해시는 `prompt.json`, 인코더의 실제 chat template 포함 입력은 시도 폴더의 `encoder-prompt.json`에 보존한다. 기본 프롬프트·카메라는 `generators/hy_motion/config/defaults.yaml`, 공식 인코더 시스템 문구는 `config/encoder-system.txt`로 버전 관리한다. 사용자 프롬프트를 인코더가 재작성하는 별도 생성 과정은 없다.

`history-reset`은 사용자 명령으로만 실행하며 목록 인덱스만 제거한다. 실행 중에는 거절하고 결과·로그는 보존한다. 초기화한 목록을 작업 종료·재개 시 자동 복원하지 않는다. 오류 원인과 traceback은 `worker.log`, 최종 상태는 `status.json`에 남는다. 5초 heartbeat는 단계·경과 시간·산출물 수를 기록한다. 예상 시간 근거가 없으면 남은 시간·완료 시각을 계산 중으로 표시한다.

실행 중 예상 시간은 동일 설정·길이·방향·프롬프트 단어 수의 최근 완료 실행(최대 5개)의 중앙값을 사용한다. 모델 준비·GPU 대기·표본 부족·예상 시간 초과 상태에서는 근거와 함께 계산 중으로 표시한다. 최종 Qwen 입력은 GUI에서 펼쳐 볼 수 있으며 실행 시 고정 tokenizer의 실제 입력과 대조한다.

공식 자료: [HY-Motion 소스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0), [모델 라이선스](https://github.com/Tencent-Hunyuan/HY-Motion-1.0/blob/main/License.txt). 모델 배포·사용에는 해당 라이선스가 적용된다.
