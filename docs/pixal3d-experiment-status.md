# Pixal3D 형상 생성 실험 상태

2026-11-22. 입력: `.local/trellis-experiment/masked-views-a-pose-v1/01_front.png`. 8방향 이미지의 카메라 정합이 확인되지 않아 첫 시험은 정면 단일 이미지로 계획했다. 텍스처 베이킹 없이 형상 생성·별도 정점 색상 투영을 목표로 한다.

- 공식 Pixal3D 저장소 `TencentARC/Pixal3D` 모델 리비전 `b0cb2e1b794cab9aa0ac38a95d794a4d9337437f`의 형상 관련 가중치를 `.local/pixal3d-experiment/model-official`에 내려받는 중이며 공식 Hub LFS 해시를 `official-weights-manifest.json`에 기록했다. 다운로드 완료·해시 검증 전에는 사용하지 않는다.
- 공식 DINOv3 `facebook/dinov3-vitl16-pretrain-lvd1689m`은 기존 Hugging Face 로그인에서 HTTP 403을 반환했다. 사용자에게 해당 페이지의 계정 정보 공유 및 라이선스 동의를 직접 검토하고 접근 요청해 달라고 안내했다. 승인 여부와 다운로드는 미완료다. 미러로 권한·조건을 우회하지 않는다.
- ROCm 호환 후보로 격리한 `raven38/pixal3d.cpp` 리비전 `d1b4926452f9e09702b891db5f05acc845e153ed`, ggml `737e88f25d4f62254f3b7a726fd9663036cc94da`. 다른 저장소나 기존 Python 환경을 바꾸지 않았다. 기본 ROCm 10.2 컴파일러는 HIP CMake 파일 누락으로 구성 실패했으며, 시스템을 수정하지 않고 ROCm 10.1 경로를 지정해 HIP/gfx1151 구성을 완료했다. `.local/pixal3d-experiment/build-rocm101`에서 빌드 중이며 컴파일 완료 및 GPU 실행은 미검증이다.
- 로컬 C++ 소스에서 flow의 비유한값을 0으로 치환하는 코드 대신 실패시키고, DINOv3·NAF·sparse decoder 주요 경계에 검사 추가 중이다. NAF GPU 경로가 없을 경우 CPU 추론으로 전환하지 않도록 실패 처리를 추가했다. 아직 컴파일과 시험 전이고 모든 단계에 대한 수치 검사 완성을 뜻하지 않는다.
- NAF 공식 체크포인트는 `.local/pixal3d-experiment/naf/naf_release.pth`에 준비했다. 코드와 체크포인트의 라이선스 적용 범위 및 DINOv3에서 유래한 구성요소 조건은 미확정이다. [NAF 체크포인트 라이선스 문의](https://github.com/valeoai/NAF/issues/13). 비상업 제한이 있는 BRIA RMBG 및 NVIDIA nvdiffrast/nvdiffrec을 사용한 생성·출력은 하지 않는다. Pixal3D 결과물의 전체 상업 이용은 승인되지 않았다.
- 원본 BF16 가중치를 제3자 변환기의 F16 GGUF로 변환할 경우 수치 표현이 달라진다. 출처·해시·변환 차이와 모델 경계별 수치를 확인해야 하며, Q8 양자화 버전을 자동으로 대체하지 않는다.
- GPU 추론은 아직 대기열에 접수하지 않았고 모델도 생성하지 않았다. 이후 라이선스와 접근 권한, 빌드, GPU 전용 실행 및 공용 대기열을 확인해야 한다.

## DINOv3 접근 확인 및 생성 접수

후속 사용자 요청으로 공식 DINOv3 접근을 재확인해 성공했다. `facebook/dinov3-vitl16-pretrain-lvd1689m` 리비전 `ea8dc2863c51be0a264bab82070e3e8836b02d51`의 `model.safetensors`는 공식 LFS SHA-256 `dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179`와 일치했다. Pixal3D 공식 형상 가중치 5개도 `official-weights-manifest.json`의 크기와 SHA-256을 대조해 모두 일치했다.

ROCm 10.1 HIP용 C++ 실행기의 컴파일과 `--help` 호출은 성공했다. 이는 GPU 추론 검증이 아니다. 공식 Hugging Face DINOv3의 분리된 Q/K/V를 C++ 런타임이 요구하는 합친 QKV 형식으로 변환했으며, Pixal3D 형상 및 DINOv3를 F16/F32 GGUF로 변환했다. 이는 BF16 원본과 수치 표현이 다르므로 수치 동등성·해상도별 GPU 안정성은 미검증이다. NAF는 공식 체크포인트를 안전 가중치 전용 로더로 읽어 변환했다. 변환 결과는 실험용이며 상업 이용 승인이 아니다.

Pixal3D 단일 참조, 시드 42, 해상도 1024, 형상 전용 작업 `.tmp/pixal-experiment/generate-cf685faf62e94f909addf28baa1cf716`을 공용 대기열의 `pixal-experiment`로 접수했다. 실측 전 단독 실행 및 65536 MiB 하한을 사용한다. 접수 직후 다른 GPU 예약으로 가용 예약량이 부족해 대기 중이었다. 실행기는 시작 전 입력과 모델 해시 및 GPU 예약을 확인하고 `--require-gpu --no-texture`로 실행하며 결과 메시의 유한 정점·면 인덱스를 검사한다. GPU 추론·리깅 및 추가 변형·상업 이용 조건은 미검증이다.

DINOv3 변환 추가 검사: 24개 블록의 공식 Q·K·V 가중치와 합친 변환 결과를 각각 정확히 대조하고, Q/V 편향과 K의 0 편향을 확인했다. 이는 변환된 F16 전체 모델의 추론값이 원본과 일치한다는 검증은 아니다. `ldd`에서 로컬 HIP 빌드의 공유 라이브러리 경로가 모두 해석됨을 확인했으며 GPU 연산 검증은 아니다. 접수된 대기열 프로세스 PID 645855가 살아 있고, 확인 당시 Hermes 상주 예약이 있어 단독 실행을 기다렸다. 다른 사용자 작업은 중단하지 않았다.

## Hermes 공존 예약 수정

사용자 요청에 따라 공용 대기열을 수정해 Pixal과 Hermes가 함께 있어도 메모리 및 기존 예약 조건이 맞으면 실행한다. Pixal끼리 또는 Pixal과 다른 일반 GPU 생성은 단독 실행을 유지하며 미확인 예약은 차단한다. 65536 MiB 초기 하한은 실측이 없으므로 낮추지 않았다. 선택 로직의 충분·부족 메모리 및 다른 작업 차단 검사는 `workflow.tests.test_pixal_gpu_queue`로 통과했다. 수정 전 접수 기록의 '단독'은 Hermes도 차단하던 당시 상태를 말한다. 수정 후에도 2026-11-22 확인값은 사용 가능 예약량 약 63155 MiB로 하한보다 작아 대기 중이다.

## 생성과 Hermes 양도 결과

사용자 지시에 따라 기존 대기 작업에 대한 명시적 양도를 시작했다. Hermes가 정상 종료된 뒤 작업이 실행되어 `mesh.glb`와 `mesh.ply`를 생성했고, GPU 예약 해제 후 Hermes가 다시 준비 상태가 됐다. 결과는 정점 1,427,127개, 면 2,958,746개의 형상 전용 메시다. 텍스처와 리깅은 없으며 형상 품질, 리깅 적합성, 상업적 이용 조건은 이 결과에 대해 검증하지 않았다.

Pixal 양도 어댑터는 기존 작업과 입력 지문을 확인하고 종료 후 재적재를 추적한다. 현재 양도 시작은 명시적으로 실행해야 하며 메모리 부족을 감지해 모든 대기 작업에 자동 적용하지는 않는다.
