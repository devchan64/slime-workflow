"""music_midi_report 노드 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.music_midi_report.application import MusicMidiReportModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MIDI 리포트 노드 실행기")
    parser.add_argument("--midi-path", default="", help="입력 MIDI 경로")
    parser.add_argument("--input-json", default="", help="입력 JSON 파일")
    parser.add_argument("--run-root", default="", help="실행 루트")
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "midi_path": args.midi_path,
        "run_root": args.run_root,
    }
    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("--input-json은 JSON 객체여야 합니다")
        payload.update(raw)

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/music-midi-report/{_run_id()}"
    payload["run_root"] = run_root
    context = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="music")

    result = MusicMidiReportModule().process(context, payload)
    output_path = Path(run_root) / "result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
