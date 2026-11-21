# Wan Animate-2 동작 전사 실험

**운영 상태:** 2026-11-20 사용자 확인에 따르면 시스템 변경으로 이전에 관측된
메모리 부족과 화면 손상 문제가 해결되어 신규 생성과 재개를 다시 진행한다.
변경 내용과 이번 입력에 대한 독립 실행·품질 검증은 아직 기록되지 않았다.
과거 이력과 결과는 당시 관측으로 보존한다.

공식 Base 체크포인트와 Diffusers의 공식 `WanAnimate2ModularPipeline`을 사용한다.
RGB 인체 동작 MP4와 캐릭터 참조 PNG를 입력한다. DWPose 선 영상·SOMA 관절
JSON을 직접 받지 않는다. Fun Control RGB 편집 실험 및 폐기된 `wan22-animate`와
별도 서비스다. SOMA 체형이 참조 체형으로 교정되는지는 결과 검수 대상이다.

## 준비·실행

GUI 상단의 **모델 다운로드** 또는 `.venv/bin/python tools/manager.py command wan22-animate2 prepare`로 준비를 시작한다. CLI에서 진행 상태는 `command wan22-animate2 model-status`로 조회한다. 실패 원인은 게이트웨이 로그에서 확인할 수 있다.
모델은 `.model/wan22-animate2`, 공식 Diffusers 소스는
`.local/wan-animate2/diffusers`에 준비한다. 별도 가상환경이나 설치된 Diffusers의
일괄 업그레이드를 요구하지 않는다. 모델·소스 revision은 `contracts.py`로 고정한다.
모델 준비 중에는 모델 파일과 공식 소스를 다운로드하고 파일 해시를 기록한다.

GUI: `/management/frame/wan22-animate2-generator/?tool=wan22-animate2-generator&category=animation-tool`

CLI: `.venv/bin/python tools/manager.py command wan22-animate2 generate --payload-file <요청.json>`

요청 필드는 `action: generate`, `images: [PNG의 base64]`, `driving_video: MP4의 base64`,
`prompt`, `frames`, `steps`, `seed`, `width: 832`, `height: 480`이다.
참조는 832×480 PNG 한 장, 동작 영상은 32MiB 이하 MP4다.
16fps 기준 충분한 입력 길이를 요구하고 결과도 16fps로 저장한다. 공식 예시의 24fps와 다른 실험 설정이며 품질 비교는 아직 필요하다. 프레임은 5~81의 4n+1,
스텝은 2~50(공식 Base 기본40), 시드는 0~2147483647이다.
입력 프레임을 시간 기준으로 샘플링하고 자동 반복하지 않는다.

GUI·CLI 모두 공용 게이트웨이와 작업 실행기를 사용한다. 작업 입력 사본·요청·결과·
실행 시도·로그는 `.tmp/test/wan22-animate2/<ID>/`에 남긴다.
`status`, `logs`, `history`, `active`, `cancel`, `resume`, `prioritize`,
`history-delete`, `history-reset`, `model-status`는 공용 명령 계약을 따른다.
선택 삭제·초기화는 작업 파일을 실제 삭제하므로 GUI 확인 범위를 확인한다.

## 추론과 검증 범위

BF16 Base 모델의 스케줄러·CFG·참조 KV 처리·디코딩은 공식 소스를 사용한다.
ROCm에서 관측된 VAE `head_dim=384` 기본 SDPA 출력 손상을 피하기 위해 VAE 인코딩과 디코딩 호출에만 수학 SDPA를 적용한다. Transformer 어텐션은 기존 경로를 사용한다. 과거 짧은 실제 생성은 유한값 검사를 통과했지만 심한 화면 손상이 관측되어 품질 검증에 실패했다. 시스템 변경 후 상태는 위 사용자 확인을 따르며, 실제 실행의 수치·품질·시간 검증 범위는 [ROCm 사례집](../../workflows/rocm-nan-cases.md)을 따른다.
모든 모델 가중치와 참조 KV 캐시는 ROCm GPU에 유지한다. 텍스트·이미지 인코더와
VAE도 GPU에서 연산하며 CPU 오프로드·CPU 추론으로 대체하지 않는다. 공용 작업 실행기가
진행·ETA·VRAM 관측 피크를 기록한다. 모델 기본81프레임 세그먼트를 요청 길이로
줄이는 단일 세그먼트 실험이며 장영상 연결 품질은 검증 범위가 아니다.

8GB 실행 가능성을 보장하지 않는다. 공식 문서는 기본 해상도에서 가중치와
참조 KV 캐시가 단일80GB에 함께 들어가지 않는다고 안내한다. 가중치 오프로드가
활성 텐서·KV 캐시까지 줄인다는 의미는 아니다. OOM은 실행 실패로 기록하며
추론 수식이나 모델을 임의 변경하지 않는다.

시스템 RAM 보호: 별도 대기 실행기가 0.2초 간격으로 Linux `MemAvailable`과
작업자 RSS를 확인한다. 사용 가능 RAM이 6GiB 미만이고 작업자 RSS가 8GiB
이상이면 해당 작업 프로세스 그룹만 강제 종료하고 실패 사유를 기록한다.
측정 실패도 작업 실패로 처리한다. 이는 GPU 메모리 예약과 별개이며, 표본
사이의 급격한 할당이나 다른 프로세스의 메모리 고갈까지 방지한다고 보장하지 않는다.
실행 중인 이전 실행기에는 적용되지 않으며 새 실행 또는 재개부터 적용된다.

공식 자료:
- https://github.com/Wan-Video/Wan-Animate-2
- https://huggingface.co/Wan-AI/Wan2.2-Animate-2-14B-Diffusers
- https://github.com/huggingface/diffusers/blob/8c54b38fea3d624d23d0e43c0c96037f080a79f9/docs/source/en/api/pipelines/wan_animate_2.md

체크포인트의 Transformers 4.57 UMT5는 `shared`와 `encoder.embed_tokens`를
같은 임베딩으로 사용한다. Transformers 5에서 분리 초기화되는 차이는 공식
`set_input_embeddings(shared)`로 연결하여 원본 구조를 유지하고 객체 동일성을 검증한다.
근거: https://github.com/huggingface/transformers/blob/v4.57.0/src/transformers/models/umt5/modeling_umt5.py#L1275

2026-11-09 실행 검증: `2026-11-09_13-19-54-6a325170`, SOMA RGB + 기본복장
참조, 21프레임·40스텝·24fps. RTX 5070 Laptop 8GB에서 첫 스텝 완료 전
참조 캐시 Transformer FFN GELU의 240MiB 할당에 실패했다. 결과 영상 없음.
이 실험으로 캐릭터 일관성 개선 여부를 판단할 수 없다.

아래 CUDA·오프로드 내용은 2026-11-09의 과거 실험 기록이다. 현재 ROCm GPU 상주 실행 설정이나 검증 결과를 뜻하지 않는다.

참조 캐시는 `cache_offload.py`에서 원본 K/V를 CPU에 동일 정밀도로 보관하고,
해당 계층이 읽을 때 CUDA로 동기 복사한다. 공식 attention·RoPE·FFN은 변경하지
않는다. 복사 경계만 컴파일에서 제외한다. CUDA 할당자는
`expandable_segments:True`를 사용한다. 2026-11-09 BF16·FP32 왕복의
`torch.equal` 검증을 통과했다. 이는 전체 출력 동등성 또는 8GB 성공 검증은 아니다.
재시험 ID: `2026-11-09_13-44-10-a0168b0c` (동일 입력·21프레임·40스텝).

Flex 실행 경계: 블록 전체 컴파일은 leaf 오프로드 훅의 재컴파일 한도에 걸려
밀집 attention으로 내려갔다. `attention_compile.py`는 공식 Flex 함수만
Inductor `fullgraph=True`로 컴파일하고 오프로드는 바깥에서 실행한다.
컴파일이 해제되면 예외로 거절하며 마스크·RoPE·CFG는 변경하지 않는다.
공식 `create_mask`의 소형 BF16 CUDA 입력과 FP32 SDPA 비교에서 최대 절대오차
0.001895, 허용오차 atol=0.01/rtol=0.02 검증을 통과했다. 프로파일의
`triton_tem_fused_flex_attention_0` 호출을 확인했다. CUPTI 초기화 실패로
GPU 상세 이벤트는 확보하지 못했다. 전체 영상 동등성 검증과는 구분한다.
재시험: `2026-11-09_13-51-37-9e993a46`, 동일 21프레임·40스텝.

### ROCm VAE 수치 안정성 검증

GPU 초기화 전에 `PYTORCH_ALLOC_CONF=expandable_segments:False`를 고정하고 이전 별칭을 제거한다. VAE 수학 SDPA 및 비유한 값 검사를 함께 유지한다. 2026-11-19 같은 가상 주소를 재사용하는 HSA 재현에서는 PyTorch 없이도 손상이 발생했다. 격리 부팅의 Ubuntu TLB 펜스 백포트와 TLB 호출 추가 대조에서는 HSA 및 실제 65프레임 VAE 잠재값이 제한된 반복에서 기준과 일치했다. 백포트 전체 생성 65프레임·20스텝은 별도 시험에서 1회 검증했다. 이는 특정 환경에서의 근거이며 물리 TLB 내부 상태나 다른 입력의 장기 안정성을 확정하지 않는다. 현재 기본 드라이버에는 실험 패치를 적용하지 않았으며 `False` 정책을 유지한다. 실험 조건과 한계는 [NaN 사례집](../../workflows/rocm-nan-cases.md)을 따른다.
