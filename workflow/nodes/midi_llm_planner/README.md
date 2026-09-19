# midi_llm_planner 노드

## 1. 목적
- 사용자 입력 프롬프트를 LLM으로 분석해 `midi_llm_composer`에 전달할 생성 파라미터를 만든다.
- planner 출력은 composer 입력 JSON 계약으로 고정한다.

## 2. 노드 ID / 모델
- node_id: `music.midi.plan.midillm`
- model_id: `Qwen/Qwen2.5-1.5B-Instruct`

## 3. 입력 계약
- 필수: `prompt`
- 선택: `run_root`, `planner_model_root`, `composer_model_root`

## 4. 출력 계약
- `composer_input` (json object)
- `composer_input_path` (json)
- `report_path` (json)
- `metadata` (json)

## 5. Fail-Fast 정책
- GPU(CUDA) 미가용 시 즉시 실패
- planner 출력이 strict JSON이 아니면 즉시 실패
- 필수 키/허용 범위 위반 시 즉시 실패

## 6. 산출물
- `.result/.../outputs/planner/midi-llm-planner.raw.txt`
- `.result/.../outputs/planner/midi-llm-planner.composer-input.json`
- `.result/.../outputs/planner/midi-llm-planner.report.json`
- `.result/.../records/nodes/music.midi.plan.midillm/{input,output,error}.json`

## 7. 실행
```bash
python -m workflow.nodes.midi_llm_planner.runtime.cli \
  --input-json workflow/nodes/midi_llm_planner/packages/prompt-plan.input.json \
  --run-root .result/workflow/nodes/midi-llm-planner/manual
```
