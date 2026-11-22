# Pixal3D 형상 생성 실험 상태

2026-11-22. 입력: `.local/trellis-experiment/masked-views-a-pose-v1/01_front.png`. 8방향 이미지의 카메라 정합이 확인되지 않아 첫 시험은 정면 단일 이미지로 계획했다. 텍스처 베이킹 없이 형상 생성·별도 정점 색상 투영을 목표로 한다.

- 공식 Pixal3D 저장소 `TencentARC/Pixal3D` 모델 리비전 `b0cb2e1b794cab9aa0ac38a95d794a4d9337437f`의 형상 관련 가중치를 `.local/pixal3d-experiment/model-official`에 내려받는 중이며 공식 Hub LFS 해시를 `official-weights-manifest.json`에 기록했다. 다운로드 완료·해시 검증 전에는 사용하지 않는다.
- 공식 DINOv3 `facebook/dinov3-vitl16-pretrain-lvd1689m`은 기존 Hugging Face 로그인에서 HTTP 403을 반환했다. 사용자에게 해당 페이지의 계정 정보 공유 및 라이선스 동의를 직접 검토하고 접근 요청해 달라고 안내했다. 승인 여부와 다운로드는 미완료다. 미러로 권한·조건을 우회하지 않는다.
- ROCm 호환 후보로 격리한 `raven38/pixal3d.cpp` 리비전 `d1b4926452f9e09702b891db5f05acc845e153ed`, ggml `737e88f25d4f62254f3b7a726fd9663036cc94da`. 다른 저장소나 기존 Python 환경을 바꾸지 않았다. 기본 ROCm 10.2 컴파일러는 HIP CMake 파일 누락으로 구성 실패했으며, 시스템을 수정하지 않고 ROCm 10.1 경로를 지정해 HIP/gfx1151 구성을 완료했다. `.local/pixal3d-experiment/build-rocm101`에서 빌드 중이며 컴파일 완료 및 GPU 실행은 미검증이다.
- 로컬 C++ 소스에서 flow의 비유한값을 0으로 치환하는 코드 대신 실패시키고, DINOv3·NAF·sparse decoder 주요 경계에 검사 추가 중이다. NAF GPU 경로가 없을 경우 CPU 추론으로 전환하지 않도록 실패 처리를 추가했다. 아직 컴파일과 시험 전이고 모든 단계에 대한 수치 검사 완성을 뜻하지 않는다.
- NAF 공식 체크포인트는 `.local/pixal3d-experiment/naf/naf_release.pth`에 준비했다. 코드와 체크포인트의 라이선스 적용 범위 및 DINOv3에서 유래한 구성요소 조건은 미확정이다. [NAF 체크포인트 라이선스 문의](https://github.com/valeoai/NAF/issues/13). 비상업 제한이 있는 BRIA RMBG 및 NVIDIA nvdiffrast/nvdiffrec을 사용한 생성·출력은 하지 않는다. Pixal3D 결과물의 전체 상업 이용은 승인되지 않았다.
- 원본 BF16 가중치를 제3자 변환기의 F16 GGUF로 변환할 경우 수치 표현이 달라진다. 출처·해시·변환 차이와 모델 경계별 수치를 확인해야 하며, Q8 양자화 버전을 자동으로 대체하지 않는다.
- GPU 추론은 아직 대기열에 접수하지 않았고 모델도 생성하지 않았다. 이후 라이선스와 접근 권한, 빌드, GPU 전용 실행 및 공용 대기열을 확인해야 한다.
