# TRELLIS 1 다중 참조 실험 준비

실험 준비 단계다. 생성기 서비스·GUI·게이트웨이·GPU 대기열·모델 설치·추론·메시 출력·리깅은 연결하거나 검증하지 않았다. 상업적 사용 가능 판정도 아니다. 세부 라이선스는 [설계 문서](../../../docs/hermes-3d-combat-animation-design.md#trellis-1-상업적-이용-조사)를 따른다.

2026-11-22 모델 파일 준비: 공식 `microsoft/TRELLIS-image-large` 리비전 `25e0d31ffbebe4b5a97464dd851910efc3002d96`의 19개 파일을 `.model/trellis-image-large`에 받았다. `verify_model.py`는 해당 리비전의 Hub 메타데이터와 파일 크기, LFS SHA-256 또는 Git blob 해시를 대조하고 `verified-manifest.json`에 로컬 SHA-256을 기록한다. 모델 로드나 추론을 확인한 것은 아니다.

설정에서 요구하는 `dinov2_vitl14_reg`의 가중치는 공식 DINOv2 다운로드 주소에서 `.model/trellis-dinov2/dinov2_vitl14_reg4_pretrain.pth`로 받았다. SHA-256 `36e4deffbaef061a2576705b0c36f93621e2ae20bf6274694821b0b492551b51`이 Meta의 [ShapeR 배포 파일](https://huggingface.co/facebook/ShapeR/blob/a7ffd10934ba5057c521208651c1a11446ad6f30/dinov2_vitl14_reg4_pretrain.pth)의 해시와 일치한다. 이 파일을 TRELLIS가 자동으로 읽도록 연결하지 않았으며 모델 파일은 신뢰된 경로에서만 로드해야 한다.

```sh
python3 workflow/domains/trellis_experiment/verify_model.py
```

## 실행 코드와 AMD 환경 조사

2026-11-22 공식 TRELLIS 소스 `193e0502b5cb3eb5997ec457d5340e95d09b158e`, FlexiCubes `815e075`, DINOv2 `7764ea0f912e53c92e82eb78a2a1631e92725fc8`을 `.local/trellis-experiment`의 별도 압축 파일과 디렉터리에 준비했다. 압축 파일의 로컬 SHA-256은 각각 `d1b2883287085757c1d40fc886e7c10d4c3b4218b851aafd277dd48bf079f52e`, `96ac575e8d035c139f2aed8ad876fa5bc38fa81b7ea2c5de46440dd044e4e00e`, `c27dcdaf50e9fb5bbdf2bb529da357716372e19c6afab17d5350f3f0094aed4b`이다. 이 해시는 다운로드 기록이며 별도 신뢰된 배포 해시와 대조한 검증은 아니다. 서브모듈을 소스 트리에 연결하거나 코드를 실행하지 않았다.

`verify_sources.py`는 이 기록된 아카이브 해시와 아카이브 내 일반 파일을 추출된 TRELLIS·FlexiCubes·DINOv2·제3자 대체 구현에 대조한다. TRELLIS 트리에 복사한 FlexiCubes도 따로 비교한다. 각각 207·17·203·76개 파일이 일치했다. 추가 파일의 부재나 아카이브의 최초 출처 신뢰성, 실행 당시 파일의 동일성을 증명하지는 않는다.

현재 `.venv`는 PyTorch `2.13.0+rocm10.0.0`, HIP `7.15.26333`이며 격리 환경 밖에서 Radeon 8060S를 인식했다. `amd-smi process` 조회 당시 GPU 프로세스는 없었다. 기존 `.venv`에는 `spconv`, `torchsparse`, `flash_attn`, `xformers`, `kaolin`, `rembg`가 없다. 공식 희소 어텐션은 `flash_attn` 또는 `xformers`, 희소 합성곱은 `spconv` 또는 `torchsparse`를 선택하므로 일반 어텐션의 SDPA 설정만으로 전체 실행 준비가 되지 않는다. 기존 환경에 패키지를 설치하거나 GPU 추론을 시작하지 않았다.

[trellis-strix-halo](https://github.com/kroqueta-s/trellis-strix-halo)는 동일 GPU 계열의 Windows ROCm에서 TRELLIS 1의 희소 합성곱·어텐션 등을 PyTorch 구현으로 대체했다고 설명하는 제3자 MIT 프로젝트다. 비교 조사 자료로 리비전 `2794cbbd05c921876ebff354af5a67f447f5b7a9` 소스 압축본을 받았고 로컬 SHA-256은 `d7cd1f2af2071aedd0a02b6592ab3d121a776e814cd8009fad7e5d1c128e3d14`다. 이 구현의 Linux 호환성, 다중 이미지 지원, 수치 동등성, 의존성 전체와 상업용 실행 경로는 검증하지 않았다. 외부 코드와 설치 스크립트를 실행하지 않았다.

후속 CPU 준비: `.local/trellis-experiment/venv`를 만들고 기존 `.venv`의 Python 3.14 패키지를 `.pth`로 읽도록 연결했다. 새 패키지는 이 실험 venv에만 설치했지만 기존 환경을 읽는 구성이라 완전히 독립된 환경은 아니다. `easydict`, `trimesh`, `plyfile`, `python-dotenv`, `rembg`, `onnxruntime`, `timm`과 그 의존성, 공식 TRELLIS 설치 스크립트가 지정하는 MIT `utils3d` 리비전 `9a4eb15e4021b67b12c460c7057d642626897ec8`을 설치했다. FlexiCubes 사본을 TRELLIS의 서브모듈 위치에 넣었다.

제3자 대체 구현의 `test_shims.py`를 GPU가 보이지 않는 격리 환경에서 CPU로 실행해 11/11 통과했다. 이는 작은 입력의 합성곱·어텐션 등 검사이지 GPU 정확도나 TRELLIS 전체 결과 검증은 아니다. 대체 구현을 설치한 뒤 `TrellisImageTo3DPipeline`을 CPU에서 import하는 것까지 확인했다. 첫 import는 `utils3d` 누락으로 실패했고 설치 후 성공했다. GPU 추론, 로컬 DINOv2 가중치 연결, 배경 제거 가중치, 다중 참조·비유한값 검사 및 의존성 전체 라이선스 감사는 미실시다. 앞 단락의 외부 코드를 실행하지 않았다는 기술은 이 CPU 검증 이전의 상태다.

추가 CPU 적재 검사: 로컬 DINOv2 소스에서 `pretrained=False`로 모델을 구성하고 해시를 확인한 로컬 가중치를 `torch.load(..., weights_only=True)`와 strict state-dict 검사로 적재했다. 304,372,736개 파라미터의 유한값을 확인했다. 기본 `torch.hub`의 가중치 경로 인자는 읽기 전용 사용자 캐시에 쓰려고 해 실패했으며, 위 명시적 적재로 성공했다. TRELLIS 파이프라인에 이 적재 방식을 연결하거나 인코더의 이미지 출력은 아직 검사하지 않았다. CPU 적재는 GPU 추론 성공이나 3D 결과의 수치 안정성을 뜻하지 않는다.

후속 연결: `offline_loader.py`가 동일한 해시·strict 검사를 거쳐 TRELLIS 인코더 초기화를 로컬 가중치로 대체한다. 독립 호출에서 DINOv2 적재를 확인했다. 공식 전체 파이프라인 적재를 GPU가 없는 격리 환경에서 시험했으나 메시 디코더의 FlexiCubes가 초기화 시 CUDA 장치를 요구해 실패했다. 공식 기본 로더는 이 오류를 포착해 Hub 경로를 재시도하며 원래 원인을 가리므로, 별도 로컬 전용 로더는 파일의 존재와 경로를 확인하고 초기 오류를 그대로 전달한다. CPU 시험에서 실제 `No CUDA GPUs are available` 오류가 전달됨을 확인했다. GPU에서 전체 파이프라인을 적재한 것은 아니며 공용 GPU 대기열에 실험 작업을 연결하고 수치 경계 검사 및 상업적 의존성 감사를 마친 뒤 시험해야 한다.

GPU 대체 연산 검사: 공용 대기열에 `trellis-experiment` 서비스(실측 전 32768 MiB 예약, GPU 단독 실행)를 추가하고 `queue_probe.py`로 ROCm 검사를 등록했다. `.tmp/trellis-experiment/gpu-probe-43b4de070cdf4530934d477cb28d5549`의 상태는 완료이며 로그의 장치는 `cuda`(ROCm PyTorch 장치명), 테스트 결과는 11/11이다. 작은 합성 입력에 대한 희소 합성곱, 어텐션, 배치 정규화 등의 기준 비교이며 실제 TRELLIS 추론·다중 이미지 품질·대표 크기 수치 안정성을 보장하지 않는다. 초기 메모리 예약은 실험값이 아니라 보수적 설정이다.

전체 모델 GPU 적재: `.tmp/trellis-experiment/gpu-probe-fe2d7427eb3b4819bba51e64514e7250`에서 로컬 전용 로더와 대체 연산으로 공식 설정의 6개 모델 및 DINOv2를 ROCm GPU에 적재하고 모든 파라미터의 유한성을 확인했다. 이는 추론 활성값이나 메시를 확인한 것이 아니다. 당시 대기열은 앞선 소형 검사와 같은 명령 식별자를 사용해 설정 32768 MiB 대신 관측 198 MiB를 예약했다. 단독 실행이었으며 이후 `trellis-experiment`는 관측값이 작아도 설정값을 하한으로 적용하도록 수정했고 선별 단위 검사로 확인했다. 이미 실행한 작업의 당시 예약이 소급 변경된 것은 아니다.

8방향 메시 시험: 원본의 흰 배경에서 RGB 각 채널 245 이상이며 테두리에 연결된 영역만 제거한 임시 이진 알파 마스크를 만들었다. 테두리에 연결된 밝은 부분 손실이나 흰 테두리가 있을 수 있어 참조 품질 승인이 아니다. `generate.py`는 이 8개 이미지와 고정 시드 42, 공식 다중 이미지 stochastic 방식 및 단계별 25스텝을 사용하고, 이미지 인코더·두 플로 모델·구조 디코더 출력과 최종 메시의 비유한값을 실패로 처리한다. GPU 대기열 작업 `.tmp/trellis-experiment/generate-e18a2e5c24264940ad2ed9ca3786ab00`을 접수했다. 접수는 생성 성공이나 품질 승인을 뜻하지 않으며 완료 기록과 결과를 별도로 확인해야 한다. 비상업 `nvdiffrast` 렌더·후처리 대신 메시 정점과 면을 직접 PLY로 저장하는 경로이며, 전체 의존성의 상업적 이용 감사는 아직 미완료다.

마스크를 어두운 배경에 합성해 8개 전체를 확인한 결과, 몇몇 팔과 몸 사이의 닫힌 흰 공간과 외곽의 밝은 가장자리가 남는다. 이 첫 시험의 입력은 수정하지 않으며 결과의 형상 오류 원인 후보로 기록한다. 합성 검토 이미지는 `.local/trellis-experiment/masked-views-v1/mask-check.png`에 보존했다.

위 8방향 작업은 완료(종료 코드 0)했다. 원본 PLY는 정점 122,492개·면 243,920개, SHA-256 `92e0fa4f81449be0ffd38e3572a2a8ff7a835a2d845d08005397069c2eb1bd87`이며 파일 해시를 별도로 재확인했다. 측정 메모리 피크는 11,299 MiB(31회 표본)다. trimesh `process=False` 기준 watertight이며 연결 성분 284개다. 이는 스켈레톤·스키닝이나 텍스처 없는 원시 메시이며, watertight가 단일 연결 메시나 리깅 적합성을 보증하지 않는다.

`render_mesh_check.py`의 CPU 정사영 검토 이미지 `mesh-check.png`에서 인체와 머리카락 실루엣은 보이지만 몸 주변에 작은 파편과 불규칙한 형상이 보인다. 광원과 깊이 정렬이 단순한 검수용 이미지이고 카메라 방향 이름은 부여하지 않았다. 8방향 참조와 정량 비교하거나 자동 리깅·모션 변형을 시험하지 않았고, 모델 품질이나 상업적 전체 파이프라인을 승인한 것이 아니다.

연결 성분을 면 수로 정렬하면 가장 큰 성분에 234,684개 면(96.21%)이 속하고 나머지 283개 성분에 9,236개 면이 분산된다. 가장 큰 성분만 남기면 일부 실제 형상이 사라질 수 있으므로 자동 삭제하거나 리깅 가능한 메시로 판정하지 않았다. 다음 리깅 검증에서는 원본을 보존하고 주요 성분과 파편의 위치를 비교한 뒤 UniRig 등으로 뼈·스키닝을 생성해 손·어깨·다리의 변형을 확인해야 한다. 현재는 자동 리깅 실행 환경과 결과가 없다.

원본 보존 대조로 `component_candidate.py`를 사용해 가장 큰 성분만 따로 `largest-candidate/largest-component.glb`에 내보냈다. GLB 왕복 시 정점·면 수는 유지됐고, 단순 8방향 렌더 `largest-check.png`에서는 인체 실루엣을 유지하면서 원본 주변의 점들이 줄었다. 이 비교는 손가락·머리카락 등 삭제된 조각이 전부 불필요하다는 증거가 아니며, 후보를 원본이나 공식 리깅 입력으로 자동 채택하지 않았다. 원본과 후보의 해시·면 수는 `largest-candidate/report.json`에 있다.

추가 분포 확인: 가장 큰 성분의 표면적은 전체의 약 98.70%이며 이 성분 자체도 trimesh 기준 watertight다. 나머지 283개 성분을 각 성분 중심의 높이로 전체 높이의 하단부터 5구간에 나누면 각각 36·53·85·76·33개다. 따라서 제거 대상이 어느 한 구간에만 모여 있지 않다. 이는 인체 부위나 파편 여부의 판정이 아니고, 리깅 변형 품질을 보증하지 않는다.

UniRig 입력 준비: 공식 [사용법](https://github.com/VAST-AI-Research/UniRig#usage)은 OBJ·FBX·GLB·VRM을 입력으로 열거한다. 원본 PLY를 수정하지 않고 같은 작업 폴더의 `unirig-input.glb`로 변환했으며, 재로드한 정점 122,492개·면 243,920개, 정점 좌표와 면 인덱스가 원본과 일치한다. GLB SHA-256은 `8e8e7282566cc438fdea19deb41f33aefea1013cb32edfd971d0e32ccb623f96`이다. 이는 형식 변환 확인이지 UniRig 입력 적합성이나 방향·스켈레톤 검증이 아니다.

`verify_result.py`로 결과 기록의 입력 매니페스트 해시, 8개 이미지 해시, PLY 해시·크기·정점 유한성·면 인덱스 및 GLB 왕복 정점·면 일치를 재확인했다. 이 검사는 데이터 무결성 범위이며 이미지-3D 형상 정확도, 최종 리깅, 상업적 이용을 승인하지 않는다.

UniRig 코드 저장소는 스켈레톤과 스키닝 체크포인트가 공개됐다고 쓰지만 [모델 카드](https://huggingface.co/VAST-AI/UniRig)는 스키닝 가중치가 추후 공개된다고 적어 설명이 서로 다르다. 공식 설치 지침은 Python 3.11, CUDA용 spconv·torch_scatter·torch_cluster 등을 전제로 하므로 현재 Python 3.14 ROCm 환경에서 호환성을 추정하지 않는다. 공개된 실제 파일·가중치 조건과 AMD 구현을 확인하고 스켈레톤 예측, 스키닝 및 변형 검사를 각각 수행해야 한다. 공식 문서는 뼈만 병합한 결과에는 스키닝이 없다고 명시한다.

후속 확인: 공식 모델 저장소 리비전 `36842e2b5947e9e60f89275b83208c8e74071c63`에는 `skeleton/articulation-xl_quantization_256/model.ckpt`(1,439,617,174바이트)와 `skin/articulation-xl/model.ckpt`(4,375,464,854바이트)가 모두 실제로 있다. 공식 코드 리비전 `6793c6640ff01c8fb389f3993434124bb43d2933`의 기본 추론 설정도 각각을 지정한다. 따라서 스키닝 파일이 없다고 판단하지 않는다. 다만 모델 카드와 코드 설명의 불일치는 남아 있고, 파일의 기능·품질과 ROCm 호환성은 실행 전이다. 두 체크포인트만 내려받고 `verify_unirig.py`로 Hub가 제공한 SHA-256 및 크기를 확인할 수 있도록 준비했다. `.ckpt` 파일을 역직렬화하거나 실행하지 않았다. 공식 코드 아카이브의 로컬 SHA-256은 `ebdda5907b520b6ccfa0524f5050c7141475d203289052e9c39024fae039c1a1`이며 신뢰된 별도 해시 대조는 아니다.

두 체크포인트 다운로드가 완료돼 `verify_unirig.py`로 크기와 공식 Hub의 LFS SHA-256을 대조했다(2/2 일치, `.model/unirig/verified-manifest.json`). UniRig 기본 스켈레톤과 스키닝 설정은 각각 이 파일을 참조한다. 현재 실험 Python 환경에서는 `bpy`, `lightning`, `torch_scatter`, `torch_cluster`, `spconv`, `flash_attn`, `open3d`, `fast_simplification`이 발견되지 않았다. 특히 스키닝 소스가 `flash_attn.modules.mha.MHA`를 직접 불러오고 Point Transformer가 spconv를 사용하므로 TRELLIS 희소 연산 대체물이 곧바로 UniRig에도 충분하다고 가정하지 않는다. 체크포인트 로딩·GPU 실행·스키닝 결과는 미검증이다.

체크포인트 CPU 검사: PyTorch `weights_only=True`로 스켈레톤 파일은 정상 적재됐고 최상위 `state_dict`에 텐서 585개가 있었다. 스키닝 파일은 `box.box.Box`가 기본 허용 목록에 없어 안전 가중치 전용 로딩이 거부됐다. pickle 명령을 실행하지 않고 검사했을 때 해당 전역과 PyTorch 텐서·스토리지 및 `OrderedDict` 참조가 나타났다. `python-box`는 현재 실험 환경에 없다. 이 검사는 악성 코드 부재를 증명하지 않으며, 허용 목록 추가나 `weights_only=False` 재시도는 하지 않았다. 두 경우 모두 모델 인스턴스에 가중치를 적용하거나 추론한 것은 아니다.

선택 패키지의 설치 메타데이터는 작업 디렉터리의 `dependency-inventory.json`에 기록했다. 실제 공식 메시·샘플러 코드가 가져오는 `easydict` 1.14는 LGPL-3.0-only로 표시되고, 공식 Gaussian 모듈이 가져오는 `plyfile` 1.1.5는 GPL-3.0 이상으로 표시된다. GPL/LGPL은 상업 사용 자체를 금지하지 않지만 도구 배포 방식에 따른 의무 검토가 필요하다. 설치 사실이나 정적 import 확인만으로 사용된 모든 경로를 확정하지 않았고, 인벤토리는 전이 의존성·가중치·소스 전체의 완전한 법적 감사가 아니다. 출력 메시만 배포하는 경우와 생성 도구를 배포하는 경우를 구분한다.

추가 확인: 실험 venv의 `pip check`는 `utils3d 0.0.2`가 요구하는 `moderngl` 누락을 보고했다. 실제 메시 생성은 완료했지만 누락된 기능과 경로 영향은 검증하지 않았으므로 환경 전체가 정상이라고 표시하지 않는다. `import_inventory.py`로 CPU의 파이프라인 import 시점 모듈 이름과 설치 배포 패키지를 메타데이터로 연결한 결과 60개 패키지가 식별됐으며 `import-inventory-v2.json`에 라이선스 메타데이터와 라이선스 파일 위치를 기록했다. 이는 모듈명 기반 추정이며 모델 로딩·GPU 추론 중 추가 import, 동적 라이브러리와 모든 전이 의존성을 빠뜨릴 수 있다. 일부 패키지에는 분류자·라이선스 식별자가 명시되지 않아 원문 확인이 추가로 필요하고, 이 목록만으로 상업용 전 과정을 승인하지 않는다.

위 CPU import 인벤토리에서 라이선스 식별자와 분류자가 둘 다 빠진 15개 배포 패키지 중 8개는 별도의 `License` 메타데이터에 MIT·BSD·Apache·MPL 등으로 표시돼 있었다. 나머지 7개는 AMD용 PyTorch·torchvision 장치 휠 및 ROCm SDK 관련 패키지로, 해당 메타데이터만으로는 조건을 판정할 수 없다. AMD의 [ROCm 라이선스 안내](https://rocm.docs.amd.com/en/docs-7.2.3/about/license.html)는 구성요소별 조건과 일부 바이너리의 별도 조건을 설명한다. 사용한 실제 휠의 구성요소와 실행 경로를 확인해야 하며 전체 ROCm을 단일 라이선스로 가정하지 않는다. 이 분류는 import 추정에 한정하고 GPU 실행 중 실제로 로드된 항목의 증거로 사용하지 않는다.

설치된 `rocm-sdk-core` 휠의 개별 라이선스 파일 9개를 확인했다. AMD SMI·hipcc·aqlprofile·rocprofiler-register·roctracer 두 구성요소는 MIT 계열 문구, amd_comgr는 Apache 2.0/LLVM 예외, rocminfo와 ROCR은 NCSA 라이선스 문구를 포함한다. 이는 해당 파일의 표기 확인일 뿐, 다른 AMD 장치 휠과 SDK 라이브러리 휠 전체 또는 실제 GPU 실행 바이너리의 조건을 확인한 것은 아니다.

라이선스 메타데이터가 빈 다른 휠의 파일 목록을 확인했다. `amd-torch-device-gfx1151`·`amd-torchvision-device-gfx1151`에는 각각 GPU용 kpack이, `amd-torch-device-gfx115x`에는 AOTriton 이미지가 있다. `rocm-sdk-device-gfx1151`은 디바이스 kpack 등을, `rocm-sdk-libraries`는 MIOpen·hipBLAS 등 공유 라이브러리를 포함한다. 각각의 메타데이터에 라이선스 식별자와 라이선스 파일이 없어, `rocm-sdk-core`의 라이선스 9개를 이 파일들에도 자동 적용하지 않는다. GPU 실행에서 실제 매핑된 파일과 배포 경로별 조건 확인은 남아 있다.

AMD의 [ROCm 10.0.0 구성요소 표](https://rocm.docs.amd.com/en/docs-10.0.0/about/license.html)는 MIOpen·hipBLAS·hipBLASLt·rocBLAS의 소스 구성요소를 MIT로 표시한다. 이는 휠에 포함된 같은 이름 라이브러리를 추적할 근거이나 현재 실험에 설치된 10.0.0 바이너리의 전체 구성·제3자 고지나 kpack 조건을 확인한 것은 아니다. 문서 자체도 구성요소별로 제3자 조건이 추가될 수 있다고 명시한다.

동일 8방향·시드·스텝의 재실행 `.tmp/trellis-experiment/generate-0fa44c4fe8ce42d79e392d54e086b4d9`를 공용 대기열에 등록했다. 생성 후 로드된 Python 모듈과 패키지 메타데이터를 `runtime-imports.json`에 기록하도록 실행기를 보완했다. 등록 시 GPU가 다른 프로세스에서 사용 중이고 메모리가 부족해 대기했다. 대기열 접수는 실행·재현성·상업용 승인을 의미하지 않는다. 기존 생성은 수정하지 않고 새 시도 결과를 확인한 후 파일과 수치를 비교한다.

## 입력 준비

기준 8방향 시트의 해시와 크기를 확인하고 4×2 셀을 PNG로 분리한다. 구분선만 제거하며 배경 제거, 인물 정렬 또는 재작화는 하지 않는다. 파일명은 원래 프롬프트의 의도된 순서이지 실제 방향의 검증 결과가 아니다. 특히 6번의 방향은 원본 기록에서 모호하다. 출력 디렉터리가 이미 있으면 중단한다.

```sh
python3 workflow/domains/trellis_experiment/prepare_views.py \
  baseline/player/default/default-eight-directions-v1.png \
  .local/trellis-experiment/reference-views-v1
```

`manifest.json`은 원본·분할 파일의 SHA-256, 크롭 좌표와 미검증 방향을 기록한다. 흰 배경 RGB이므로 공식 전처리는 배경 제거를 호출할 수 있다. 투명 마스크로 처리한 것으로 간주하지 않는다.

## 실행 전 확인

- 공식 TRELLIS 1의 다중 이미지 추론과 메시 추출에 사용할 소스·서브모듈·가중치 버전과 해시를 고정한다. 기본 처리의 이미지 전처리 및 모든 직접·간접 의존성을 확인한다.
- 상업적 용도에서는 비상업 조건인 `nvdiffrast`, `diffoctreerast`를 사용하는 공식 렌더·후처리를 사용하지 않는다. 이들을 제외한 메시 저장 경로의 import와 실행 가능성은 아직 검증하지 않았다.
- 현재 장비는 AMD Strix Halo다. 공식 저장소의 검증 대상은 NVIDIA GPU이며 ROCm 동작, 확장 빌드, 메모리·수치 안정성과 실제 모델 품질은 확인되지 않았다. 기존 ROCm 운영 규칙과 GPU 대기열을 따른다.
- 8방향 사진은 같은 3D 객체를 실제 촬영한 영상이 아니라 각각 생성된 그림이다. 방향·자세·비율 차이로 일치하는 3D 형상이 존재한다는 보장은 없다. 1·4·8장 등의 입력을 비교하고 기준 카메라 방향을 결과에서 별도 검수한다.
- 메시 생성 성공과 8방향 일치, 토폴로지, 자동 리깅·스키닝 및 무기 부착 가능성은 각각 검증한다. 이 실험 준비는 실행이나 품질을 보장하지 않는다.

## 파편 제거와 기하학적 검증

CPU에서 다음 명령으로 새 출력 폴더에 후보를 만든다. 원본은 변경하지 않으며, 기존 출력 폴더는 덮어쓰지 않는다.

```sh
.local/trellis-experiment/venv/bin/python workflow/domains/trellis_experiment/clean_mesh.py INPUT.ply NEW_OUTPUT_DIR
```

가장 큰 표면적 성분을 기준으로 나머지 성분의 표면적과 면 수가 각각 전체의 0.1% 이하이고, 기준 성분의 가장 가까운 정점까지 거리가 전체 대각선의 0.2% 이상일 때만 제거한다. 정점 간 거리는 표면 간 정확한 거리가 아니며 가까운 작은 조각도 남을 수 있다. `candidate.glb`와 `report.json`에 해시, 성분별 판정, 기준값, 8방향 정사영 실루엣 손실, 표면적 손실, 크기 변화, GLB 왕복 검사 및 통과 여부를 기록한다. 기본 허용치는 각각 실루엣 방향별 2%, 표면적 3%, 대각선 대비 크기 변화 3%다. 실패 시 후보는 진단용으로 보존하되 종료 코드 2를 반환하므로 후속 처리에서 사용하지 않아야 한다. 임계값은 CLI 옵션으로 조절할 수 있으며 경험적 초깃값이다.

이 검증은 제거된 부분의 의미나 손가락·장식의 보존, 참조 이미지 충실도, 뼈·스키닝 품질을 판단하지 못한다. 실루엣은 고정 해상도의 투영이므로 작은 손실은 놓칠 수 있다. 검증 통과는 리깅 또는 상업용 품질 승인과 다르다.

실제 첫 메시 적용 결과: `.tmp/trellis-experiment/clean-v2/report.json`에서 284개 성분 중 282개를 제거했고 표면적 손실은 약 1.21%, 최대 크기 변화는 약 1.13%였다. 8방향 중 최대 실루엣 손실은 약 4.40%로 기본 한도 2%를 넘어 **검증 실패**다. 후보는 진단용으로만 보존하며 자동 채택하지 않는다. 기준 완화만으로 품질을 입증할 수 없으므로 입력 마스크 개선이나 더 보수적인 제거 전략과 추가 검증이 필요하다.

## 참조 색상 자동 투영

`project_colors.py`는 번호가 붙은 8개 RGBA 참조에서 대략적인 정사영 투영과 정점 법선·정점 깊이 비교로 색을 샘플링해 GLB 정점 색상을 만든다. 각 이미지와 메시의 실루엣 경계 상자를 맞추므로 카메라 보정은 아니다. 배경과 밝은 흰 마스크 구멍을 제외하고, 관측되지 않은 정점은 가장 가까운 관측 정점 색으로 채운다. 실제 흰색 의상도 제외될 수 있고 정점 깊이 비교는 면 단위 가림을 정확히 처리하지 않는다. 출력은 UV 텍스처가 아니며 참조 방향과 3D 방향 정합, 조명·색 충실도, 후속 2D 영상 생성 품질은 미검증이다. 원본과 참조의 SHA-256 및 직접 채색과 보간 정점 수를 기록하고 GLB 색상의 왕복을 검사한다.

```sh
.local/trellis-experiment/venv/bin/python workflow/domains/trellis_experiment/project_colors.py INPUT.glb .local/trellis-experiment/masked-views-v1 NEW_OUTPUT_DIR
```

첫 적용 `.tmp/trellis-experiment/colored-v1`은 원본이 아닌 최대 연결 성분 후보를 사용했다. 해당 후보의 세부 형상 보존 및 리깅 적합성은 미검증이다. 117,308개 정점 중 100,575개는 직접 샘플링했고 16,733개는 가까운 정점 색으로 채웠다. 이 색은 최종 스프라이트가 아니라 후속 2D 일관성 보강 영상 생성을 위한 모션 참조용이다.

## 자기 교차 검사와 복원 시험

`inspect_repair_mesh.py`는 PyMeshLab의 자기 교차 면 선택을 실행하고, 교차가 발견되면 복셀화·표면 재구성으로 별도 후보를 만든 뒤 교차·연결성·면 방향 및 8방향 실루엣 손실과 증가를 재검사한다. 원본을 수정하지 않는다. 실루엣 손실과 증가가 각각 모든 방향에서 2% 이내여야 기하 검사 통과다. 이 검사는 사람 신체의 잘못된 연결을 판별하지 못하므로 통과하더라도 자동 리깅 승인 상태로 전환하지 않는다.

```sh
PYTHONPATH=.local/trellis-experiment/mesh-inspection \
 .local/trellis-experiment/venv/bin/python workflow/domains/trellis_experiment/inspect_repair_mesh.py INPUT.glb NEW_OUTPUT_DIR
```

검사 도구는 PyMeshLab 2025.7.post1을 격리 디렉터리에 설치했다. 해당 배포판은 GPL-3 라이선스로 표시되어 상업 사용은 가능하나 도구 배포 시 관련 의무를 검토해야 한다. 현재 환경의 libOpenGL.so.0 누락으로 일부 플러그인은 로드되지 않았으나 자기 교차 선택 필터는 사용 가능했다. 교차하는 두 삼각형과 떨어진 두 삼각형의 합성 검사에서 각각 2개 및 0개의 면을 검출했다. 모든 교차 유형과 수치 한계에 대한 검증은 아니다.

색상 후보 실측: `.tmp/trellis-experiment/topology-v1/report.json`에서 자기 교차 선택 3개 면이 나왔다. 복셀 복원 후보는 동일 필터에서 0개였으나 8방향 실루엣이 약 7.9~8.4% 증가해 허용 기준을 넘었다. 기하 검사 실패이며 리깅에 자동 사용하지 않는다. 잘못된 인체 연결은 이번에 감지하거나 수정하지 못했다. 복원은 잘못된 연결을 새로 만들 수도 있다.

## 손과 몸 분리 시험

`separate_hand_candidate.py`는 `colored-v1`의 고정 SHA-256을 확인한 뒤 양손과 몸이 이어진 것으로 의심되는 좌표의 복셀을 잘라 별도 후보를 만든다. 좌표는 이 한 메시에서 정한 실험값이며 다른 캐릭터에 일반화할 수 없다. 원본은 보존한다. `.tmp/trellis-experiment/hand-separation-v1/report.json`에서 표본 단면 네 높이의 양측 연결 윤곽은 모두 사라졌고, 자기 교차 선택 0, 열린 경계 0, 비다양체 모서리 0이었다. 하지만 이는 손가락 보존이나 모든 높이에서의 완전 분리 증거가 아니다.

전체 복셀 재구성으로 8방향 실루엣이 약 5.2~6.5% 증가해 2% 기준을 초과했고 표면이 계단처럼 변했다. `geometric_checks_passed`는 false이며 후보는 승인하지 않는다. 스켈레톤, 스키닝, 팔을 움직이는 변형 및 무기 부착 시험은 실행하지 않았으므로 리깅 적합성 미확인이다. 좌표를 자동 인식한 범용 수리 기능도 아니다.

## A 포즈 8방향 모델링 준비

새 ImageGen 참조 `.local/trellis-experiment/reference-eight-a-pose-v1.png`의 SHA-256은 `caa5ff38eaa7877f5ff594247f4a8f40e48c67dd3292d4a701d9536daaefbd81`이다. `prepare_a_pose_views.py`로 구분선이 없는 1536×1024 시트를 384×512 이미지 8개로 분할하고 기존 `mask_views.py`로 마스크를 만들었다. 분할과 마스크 출력은 각각 `.local/trellis-experiment/reference-views-a-pose-v1`, `.local/trellis-experiment/masked-views-a-pose-v1`이며 후자의 8개 이미지 해시를 매니페스트와 대조했다. 어두운 배경 검수는 `mask-check.png`다. 이미지 번호와 방향명은 의도된 방향이고 카메라 정합을 증명하지 않는다. 측면에서는 팔이 몸 위로 투영되고 후면 사선 두 장이 유사해 다중 이미지의 자세·방향 정합은 미검증이다.

`generate_a_pose.py`는 새 마스크만 입력으로 고정한 별도 대기열 실행기다. 이전 실험과 동일한 seed 42, stochastic, 25+25 스텝, 메시 단독 저장을 사용한다. 이전 `generate.py` 또는 대기 중인 작업의 입력은 수정하지 않았다. 준비만 완료했으며 GPU 작업은 새로 접수하거나 추론하지 않았다. 실행 시 공용 GPU 대기열과 ROCm 공통 운영 규칙을 따른다. 결과에서는 별도 리깅 전에 손과 몸의 연결, 자기 교차, 실루엣 및 스키닝 변형을 검증해야 한다.
