# Wan Animate-2 동작 전사 실험

공식 Base 체크포인트와 Diffusers의 공식 `WanAnimate2ModularPipeline`을 사용한다.
RGB 인체 동작 MP4와 캐릭터 참조 PNG를 입력한다. DWPose 선 영상·SOMA 관절
JSON을 직접 받지 않는다. Fun Control RGB 편집 실험 및 폐기된 `wan22-animate`와
별도 서비스다. SOMA 체형이 참조 체형으로 교정되는지는 결과 검수 대상이다.

## 준비·실행

저장소의 `.venv`에서 `python generators/wan_animate2/prepare.py`를 실행한다.
모델은 `.model/wan22-animate2`, 공식 Diffusers 소스는
`.local/wan-animate2/diffusers`에 준비한다. 별도 가상환경이나 설치된 Diffusers의
일괄 업그레이드를 요구하지 않는다. 모델·소스 revision은 `contracts.py`로 고정한다.
준비 로그는 파일로 보관한다. GPU 확인·모델 준비·추론은 샌드박스 밖에서 실행한다.

GUI: `/management/frame/wan22-animate2-generator/?tool=wan22-animate2-generator&category=animation-tool`

CLI: `.venv/bin/python tools/manager.py command wan22-animate2 generate --payload-file <요청.json>`

요청 필드는 `action: generate`, `images: [PNG의 base64]`, `driving_video: MP4의 base64`,
`prompt`, `frames`, `steps`, `seed`, `width: 832`, `height: 480`이다.
참조는 832×480 PNG 한 장, 동작 영상은 32MiB 이하 MP4다.
24fps 기준 충분한 입력 길이를 요구한다. 프레임은 5~81의 4n+1,
스텝은 2~50(공식 Base 기본40), 시드는 0~2147483647이다.
입력 프레임을 시간 기준으로 샘플링하고 자동 반복하지 않는다.

GUI·CLI 모두 공용 게이트웨이와 작업 실행기를 사용한다. 작업 입력 사본·요청·결과·
실행 시도·로그는 `.tmp/test/wan22-animate2/<ID>/`에 남긴다.
`status`, `logs`, `history`, `active`, `cancel`, `resume`, `prioritize`,
`history-delete`, `history-reset`, `model-status`는 공용 명령 계약을 따른다.
선택 삭제·초기화는 작업 파일을 실제 삭제하므로 GUI 확인 범위를 확인한다.

## 추론과 검증 범위

BF16 Base 모델의 스케줄러·CFG·참조 KV 처리·디코딩은 공식 소스를 사용한다.
가중치는 CPU RAM에 대기시키고 leaf 단위로 CUDA에 올린다. 텍스트·이미지 인코더와
VAE도 CUDA 연산하며 CPU 추론으로 대체하지 않는다. 공용 작업 실행기가
진행·ETA·VRAM 관측 피크를 기록한다. 모델 기본81프레임 세그먼트를 요청 길이로
줄이는 단일 세그먼트 실험이며 장영상 연결 품질은 검증 범위가 아니다.

8GB 실행 가능성을 보장하지 않는다. 공식 문서는 기본 해상도에서 가중치와
참조 KV 캐시가 단일80GB에 함께 들어가지 않는다고 안내한다. 가중치 오프로드가
활성 텐서·KV 캐시까지 줄인다는 의미는 아니다. OOM은 실행 실패로 기록하며
추론 수식이나 모델을 임의 변경하지 않는다.

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
