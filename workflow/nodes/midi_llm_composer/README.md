# midi_llm_composer 노드

## 1. 목적
- `slseanwu/MIDI-LLM_Llama-3.2-1B`로 자연어 프롬프트를 MIDI 튜플 시퀀스로 생성한다.
- 성능 측정(생성 토큰 수, 소요시간, tokens/sec)과 실행 기록을 `.result`에 남긴다.

## 2. 노드 ID / 모델
- node_id: `music.midi.generate.midillm`
- provider: `huggingface`
- model_id: `slseanwu/MIDI-LLM_Llama-3.2-1B`

## 3. 입력 계약
- 필수
  - `prompt` (txt)
- 선택
  - `max_new_tokens` (json number, 기본 2048)
  - `temperature` (json number)
  - `top_p` (json number)
  - `top_k` (json number)
  - `repetition_penalty` (json number)
  - `run_root` (json string)
  - `model_root` (json string)

## 4. 출력 계약
- `mid_path` (mid)
- `raw_output_path` (txt)
- `token_output_path` (json)
- `report_path` (json)
- `metadata` (json)

## 5. Fail-Fast 정책
- GPU(CUDA) 미가용 시 즉시 실패한다.
- 입력 누락/범위 위반 시 즉시 실패한다.
- 모델 출력을 숫자 MIDI 튜플로 파싱하지 못하면 즉시 실패한다.

## 6. 산출물
- MIDI: `.result/.../outputs/midi/midi-llm.mid`
- Raw 텍스트: `.result/.../outputs/midi/midi-llm.raw.txt`
- 파싱 토큰: `.result/.../outputs/midi/midi-llm.tokens.json`
- 리포트: `.result/.../outputs/midi/midi-llm.report.json`
- 절차 기록: `.result/.../records/nodes/music.midi.generate.midillm/{input,output,error}.json`

## 7. 실행
```bash
python -m workflow.nodes.midi_llm_composer.runtime.cli \
  --input-json workflow/nodes/midi_llm_composer/packages/test-input.prompt-intent.json \
  --run-root .result/workflow/nodes/midi-llm-composer/manual
```

## 8. 성능 테스트
```bash
workflow/tests/run_midi_llm_composer_performance_test.sh
```
