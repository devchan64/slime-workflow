# midi_trim_bars 노드

## 1. 목적
- 입력 MIDI를 지정 마디 수(`bars`) 기준으로 정확히 자른다.
- 컷 지점에서 열린 노트는 강제로 note-off를 넣어 hanging note를 방지한다.

## 2. 노드 ID
- `music.midi.trim.bars`

## 3. 입력 계약
- 필수: `midi_path`, `bars`
- 선택: `output_path`, `run_root`

## 4. 출력 계약
- `midi_path` (trim 결과 MIDI)
- `report_path` (json)
- `metadata` (json)

## 5. Fail-Fast 정책
- 입력 MIDI 누락/비정상이면 즉시 실패
- `bars <= 0`이면 즉시 실패
- 박자 분모가 비정상(2의 거듭제곱 아님)이면 즉시 실패

## 6. 산출물
- `.result/.../outputs/midi/*.mid`
- `.result/.../outputs/midi/midi-trim-bars.report.json`
- `.result/.../records/nodes/music.midi.trim.bars/{input,output,error}.json`

## 7. 실행
```bash
python -m workflow.nodes.midi_trim_bars.runtime.cli \
  --midi-path <input.mid> \
  --bars 32 \
  --run-root .result/workflow/nodes/midi-trim-bars/manual
```
