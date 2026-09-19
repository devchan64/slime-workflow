# musicgen_small 노드

## 1. 목적
- `facebook/musicgen-small` 모델로 텍스트 프롬프트 기반 음악 WAV를 생성한다.
- 성능 시험(최대 길이 생성)과 결과 계측(생성 길이/elapsed/RTF)을 표준 출력물로 남긴다.

## 2. 노드 ID / 모델
- node_id: `musicgen.small.generate`
- provider: `huggingface`
- model_id: `facebook/musicgen-small`

## 3. 입력 계약
- 필수
  - `prompt` (txt)
  - `duration_seconds` (json number)
- 선택
  - `guidance_scale` (json number)
  - `temperature` (json number)
  - `top_k` (json number)
  - `top_p` (json number)
  - `run_root` (json string)
  - `model_root` (json string)

## 4. 출력 계약
- `wav_path` (wav)
- `report_path` (json)
- `metadata` (json)

## 5. Fail-Fast 정책
- GPU(CUDA) 미가용 시 즉시 실패한다. (CPU 추론 금지)
- 필수 입력 누락/범위 위반 시 즉시 실패한다.
- 출력 파일 미생성 시 즉시 실패한다.

## 6. 산출물
- WAV: `.result/.../outputs/audio/musicgen-small.wav`
- 리포트: `.result/.../outputs/audio/musicgen-small.report.json`
- 리포트에는 아래를 포함한다.
  - 요청 길이(`duration_seconds_requested`)
  - 생성 길이(`duration_seconds_generated`)
  - 실행 시간(`elapsed_seconds`)
  - 실시간 배수(`realtime_factor`)

## 7. 실행
- CLI:
```bash
python -m workflow.nodes.musicgen_small.runtime.cli \
  --input-json workflow/nodes/musicgen_small/packages/prompt-max-duration.json \
  --run-root .result/workflow/nodes/musicgen-small/manual
```

- 최대길이 성능 시험:
```bash
workflow/tests/run_musicgen_small_max_duration_test.sh
```

## 8. 패키지/테스트
- 패키지 매니페스트: `workflow/nodes/musicgen_small/packages/unit-musicgen-small-generate.json`
- 테스트 프롬프트: `workflow/nodes/musicgen_small/packages/prompt-max-duration.json`
- 노드 테스트: `workflow/nodes/musicgen_small/tests/test_node.py`
