# 기본 캐릭터 애니메이션 통합 리포트

생성 ID: `2026-10-05_16-28-12-8e29beaf`

[프레임별 참조·결과 비교](preview.html) · [실행 요청](run/request.json) · [결과](run/result.json) · [실행 로그](run/worker.log)

- 기본 캐릭터 신체 베이스, `walking-v13`, ANNY 포즈, `down_left` 방향.
- 원천 프레임 4~26을 2프레임 간격으로 선택한 12장, 768×768, 재생 8 FPS.
- Qwen-Image-Edit-2511 + AnyPose base/helper 각각 0.7 + Lightning, 4스텝. Qwen Image 2.1 실험이 아니다.
- 원본 상태: completed, 종료 코드 0. 모델 revision·시드·라이브러리 버전·어댑터 해시는 프레임별 result.json에 보존했다.

## 보존 및 검증

원본 `.tmp/test/character-animation/2026-10-05_16-28-12/2026-10-05_16-28-12-8e29beaf/`를 변경하지 않고 `run/`에 복사했다. 입력 이미지, 실제 모델 프롬프트, 생성 결과, 로그와 상태를 함께 보존한다. 원본 JSON의 절대 경로는 당시 출처이며 리포트 링크는 상대 경로로 제공한다.

모든 사본을 원본과 SHA-256으로 대조하고, 12프레임의 실제 입력 이미지 해시를 해당 result.json과 대조했다. 요청의 자산 해시와 프레임별 가공된 참조 이미지 해시는 서로 다를 수 있다. 육안 품질 승인·재생 품질 평가·GPU 재현 실행은 이번 보존 작업에 포함하지 않았다. 정식 에셋 등록은 아니다.

이 폴더에서 `sha256sum -c SHA256SUMS`로 보존 파일의 무결성을 확인한다.

## 재현 범위

GPU(CUDA), 해당 모델 및 어댑터 revision, 기록된 PyTorch·Diffusers 환경과 워크플로우 저장소가 필요하다. 실행 진입점과 인자는 `run/gpu-command.json`에 보존했다. 원본 명령을 그대로 실행하면 기존 실행 폴더를 가리키므로 실행하지 않는다. 재실행은 새 `.tmp/test/character-animation/<한국시간>/<새 생성 ID>/`에 요청을 준비하고 다음 형식으로 실행한다.

```bash
.venv/bin/python generators/animation/run_character_animation.py --job-dir <새로운-실행-폴더>
```

저장소 제작 자산과 런타임 코드의 동일 버전 확보가 추가로 필요하다. 본 리포트는 입력·결과 보존본이며 독립 실행 환경 또는 비트 단위 동일 재현을 보장하지 않는다.

## 바디 걷기 애니메이션

[걷기 12프레임 v1](walking-body-v1/README.md) · [12프레임 검수 GIF](walking-body-v1/default-body-down-left-review.gif) · [512 셀 스프라이트시트](walking-body-v1/default-body-down-left-12frames.png)

사용자 요청으로 추가한 검수 후보입니다. 원본 생성 결과와 구분하여 보관하며 품질 승인은 아직 완료되지 않았습니다.

## 가벼운 보호구 걷기 12프레임 보정 · 통합 기록

[리포트](walking-light-armor-normalized-v1/README.md) · [검수 GIF](walking-light-armor-normalized-v1/review.gif) · [가이드라인 비교](walking-light-armor-normalized-v1/baseline-guides-review.gif)

보호구 베이스라인에 맞춰 내장 이미지젠으로 보정한 검수 후보입니다.

[통합 프레임 목록](report-index.yaml)에 보정 12장의 순서·원천 프레임 번호·512 셀 크기·8fps·참조 생성 ID를 기록했습니다. 메인 [검수 화면](preview.html)에서 GIF·베이스라인 가이드 비교·시트를 바로 확인할 수 있습니다. 기존 바디 걷기 기록은 유지합니다. 대기·휴식 바디 버전은 사용자 요청으로 폐기했습니다.

## 가벼운 보호구 대기 8프레임

[기록](idle-light-armor-v1/README.md) · [GIF](idle-light-armor-v1/review.gif) · [베이스라인 비교](idle-light-armor-v1/baseline-guides-review.gif). 이미지젠 생성 검수 후보입니다.

## 가벼운 보호구 휴식 시작·종료

[각 8프레임 기록](rest-light-armor-v1/README.md) · [연결 GIF](rest-light-armor-v1/combined-review.gif). 이미지젠 생성 검수 후보입니다.

## 중간 보호구 대기 8프레임

[기록](idle-medium-armor-v1/README.md) · [GIF](idle-medium-armor-v1/review.gif) · [시트](idle-medium-armor-v1/idle-8frames.png). 대기 베이스라인과 중간 보호구 v7을 참조한 이미지젠 검수 후보이며 개별 프레임 노멀라이즈는 미완료입니다.
