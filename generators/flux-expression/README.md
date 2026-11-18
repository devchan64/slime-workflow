# FLUX 표정 생성기

FLUX 3 Image Klein으로 얼굴 참조 1장에 표정을 적용한다. 관리도구의 이미지 생성 분류에서 FLUX 3 표정 생성기를 선택한다. 기본 캐릭터 정면 얼굴을 불러오거나 다른 불투명 PNG를 지정할 수 있다. 표정·시드·참조를 선택한 뒤 GPU 대기열에 등록하고 생성 이력에서 결과를 원본과 비교한다.

FLUX 생성 이력은 `flux-expression`에 보존한다. 입력 원본 사본·프롬프트·시드·모델 리비전을 새 이력에 기록한다. 마스크와 VAE 타일링을 사용하지 않는다. 색상 및 얼굴 비율 보존은 보장되지 않는다.

CLI 예시:

```bash
.venv/bin/python tools/manager.py command flux-expression generate --expression joy --reference baseline/player/default/default-face-front-v1.png --seed 1770797539 --detach
.venv/bin/python tools/manager.py command flux-expression history
```

FLUX 모델 사용에는 모델 가중치의 FLUX Kommunity License 조건이 적용된다. Qwen 2.1 표정 LoRA는 사용하지 않는다.

768×512 단일 참조 시험에서 프로세스 GPU 메모리 피크 39,166 MiB를 관측했다. 새 표정 작업의 초기 대기열 예약은 45,056 MiB이며, 해상도와 동시 부하에 따라 실제 사용량은 달라진다. 예약량보다 사용 가능한 총 GPU 메모리가 작으면 작업을 거절한다.

한국어 설명을 입력하면 번역 대기열에서 영어로 번역한 뒤 준비 문구와 표정 프리셋에 결합해 자동 생성한다. 번역 실패 시 생성하지 않으며 원문·번역·검토 항목은 이력에서 확인한다. 기존 영어 입력과 이력은 유지한다.

FLUX 모델 구성요소는 CPU 자동 오프로드 없이 ROCm GPU에 순차 적재한다. 실행 중 호스트 여유 메모리가 6 GiB 미만이면서 작업 RSS가 8 GiB 이상이면 해당 작업을 중지하고 실패 사유를 기록한다. 이는 시스템 전체의 OOM 방지를 보장하지 않는다. 기존 오프로드 실행의 실측값은 GPU 상주 실행의 예약 추정에 사용하지 않는다.
