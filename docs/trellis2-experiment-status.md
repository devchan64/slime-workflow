# TRELLIS.2 형상 생성 전환

2026-11-22 사용자 결정으로 Pixal3D 생성 후보와 리그는 후속 제작의 기준에서 제외하고, 기존 산출물은 재현·비교를 위한 실험 기록으로 보존한다. 종전 `trellis-experiment`의 TRELLIS 1 모델은 TRELLIS.2가 아니다.

## 준비한 실행 경로

- 모델: 공식 `microsoft/TRELLIS.2-4B`, 리비전 `af44b45f2e35a493886929c6d786e563ec68364d`. SS flow, 512/1024 shape flow, shape decoder 네 원본 safetensors의 SHA-256을 공식 Hub LFS 메타데이터와 대조했다. 기록은 `.local/trellis2-experiment/official-manifest.json`이다.
- 공식 파이프라인이 참조하는 TRELLIS 1 SS decoder와 공식 DINOv3는 기존 검증본을 재사용한다. shape decoder와 SS decoder 원본은 이전 변환에 사용한 파일과 SHA-256이 같다. 모델 및 DINO의 GGUF 변환은 F16/F32이며 원본 PyTorch/BF16 실행과 수치 동등성이 검증되지 않았다.
- Linux/gfx1151에서 이미 빌드한 GGML HIP 실행기의 TRELLIS.2 경로를 사용한다. 실행 파일은 Pixal3D 포크 빌드 디렉터리에 있으나 TRELLIS.2 모드와 TRELLIS.2 flow 가중치를 사용하며 Pixal3D flow·NAF는 적재하지 않는다. 제3자 포트와 Pixal3D 모델을 혼동하지 않는다.
- 정면 A포즈 RGBA 참조, seed 42, 1024 cascade, 형상만 생성한다. 이미지 8장이 아니라 정면 한 장을 입력한다. BG 제거·텍스처 생성은 요청하지 않는다. `GGML_FA_DEBUG=1`로 어텐션 선택 정보를 기록하며 수치 비교 자체는 별도 작업이다.
- `workflow/domains/trellis_experiment/generate_trellis2.py`는 원본 입력·실행기·모델의 SHA-256을 실행 전에 확인하고, 공용 `trellis-experiment` GPU 대기열을 통해 실행한다. 출력의 메시 정점 유한성과 인덱스를 검사하며 리깅 가능성은 판단하지 않는다. Hermes 양도는 해당 작업 ID와 요청 지문에만 묶는다.

## 상업 이용 범위

[TRELLIS.2 모델 카드](https://huggingface.co/microsoft/TRELLIS.2-4B)와 [공식 코드 라이선스](https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE)는 MIT를 표시한다. DINOv3는 별도 약관을 가지며 사용자가 제공한 2025-08-19 원문과 공식 가중치의 라이선스를 비교한 이전 기록을 따른다. 이용 목적별 제한과 고지를 별도 판단해야 한다. 공식 전체 파이프라인의 배경 제거·텍스처 후처리에 사용될 수 있는 별도 조건의 구성요소는 이번 형상 전용 경로에서 의도적으로 실행하지 않는다. 실행기의 네이티브 의존성 전체 및 출력의 상업적 이용 가능성은 아직 확정하지 않는다.

## 작업 상태

`.tmp/trellis2-experiment/generate-cade4373af0448db91c769d9e0ae3ea2`을 대기열에 접수했다. 이미 실행 중인 다른 GPU 작업을 중단하지 않으며, 생성 완료 여부와 형상 품질은 상태·출력·렌더를 확인한 후 기록한다.

## Pixal3D 폐기

후속 지시에 따라 Pixal3D 생성 및 전용 양도 진입점을 제거했다. 이전 Pixal3D 형상과 리그를 기본 입력으로 재생성하던 UniRig 실행도 차단했다. 이전 실험 결과와 기록은 보관하며, GPU 대기열의 기존 Pixal 예약 판독 규칙은 과거 예약을 잘못 해석하지 않도록 유지한다. TRELLIS.2·UniRig의 공용 양도 코드는 Pixal 모듈에 의존하지 않는다. TRELLIS.2의 종전 대기 작업은 접수 당시 실행기 지문에 묶여 있으므로 작업 도중 실행기를 변경하거나 삭제하지 않는다. 별도로 Pixal3D 포크가 아닌 `pwilkin/trellis.cpp` 상위 소스를 격리해 ROCm 빌드를 검증한다.

신규 작업의 실행기는 `.local/trellis2-experiment/build-rocm101/trellis-cli`이며, 상위 소스 리비전 `6851891d706e2e26a8bb9dd99f28de851d68b64d`, ggml 서브모듈 `f8697b33795db2ee6a2569b40853ca6aaa69f9b9`를 빌드한다. GPU 추론 결과와 수치 동등성은 별도로 검증해야 한다.
