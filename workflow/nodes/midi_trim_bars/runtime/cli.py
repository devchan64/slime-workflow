"""MIDI trim bars 노드 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_trim_bars.application import MidiTrimBarsModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MIDI bar trim 노드 실행기")
    parser.add_argument("--midi-path", default="", help="입력 MIDI 파일")
    parser.add_argument("--bars", type=int, default=32, help="트림할 마디 수")
    parser.add_argument("--output-path", default="", help="출력 MIDI 파일 경로")
    parser.add_argument("--run-root", default="", help="실행 루트")
    parser.add_argument("--input-json", default="", help="입력 JSON 파일")
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "midi_path": args.midi_path,
        "bars": args.bars,
        "output_path": args.output_path,
        "run_root": args.run_root,
    }
    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("--input-json은 JSON 객체여야 합니다")
        payload.update(raw)

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/midi-trim-bars/{_run_id()}"
    payload["run_root"] = run_root
    context = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="music")

    result = MidiTrimBarsModule().process(context, payload)
    output = Path(run_root) / "result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))


if __name__ == "__main__":
    main()
