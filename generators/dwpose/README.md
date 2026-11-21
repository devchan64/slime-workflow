# DWPose 이미지 추출

생성기 페이지는 `page/`, 변경 기록은 `CHANGELOG.md`에서 관리한다. 기존 실행과 작업 기록은 관리도구 공용 게이트웨이를 사용한다.


## 모델 준비

공용 ROCm 실행 환경을 먼저 준비하고 포즈 모델만 다운로드·검증할 수 있다.

```bash
./scripts/workflow.sh setup --scope wan-fun-runtime
./scripts/workflow.sh model prepare dwpose
./scripts/workflow.sh model status dwpose
```

관리도구 **모델 관리 → DWPose 포즈 모델**에서도 같은 준비·상태·파일 목록을 사용한다. 이미 검증된 모델은 다시 받지 않는다. 준비 작업은 게이트웨이와 분리된 프로세스에서 실행하며 공용 GPU 대기열의 활성 예약이 있으면 실패한다. 준비 중에는 대기열의 새 GPU 작업이 시작되지 않는다. 대기열 밖에서 직접 실행하는 작업은 보호하지 못한다. 실패 원인은 `.local/model-preparation/dwpose-pose/worker.log`에서 확인한다. 모델 파일과 실행 파일 검증은 실제 GPU 추출 성공을 보장하지 않는다.
