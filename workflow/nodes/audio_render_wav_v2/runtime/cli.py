from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.audio_render_wav_v2.application.stage import AudioRenderWavV2Module


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="audio render wav v2 CLI")
    p.add_argument("--midi-path", default="")
    p.add_argument("--input-json", default="")
    p.add_argument("--run-root", default="")
    p.add_argument("--soundfont-profile", default="fluidr3-gm")
    p.add_argument("--sample-rate", type=int, default=44100)
    return p.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "midi_path": args.midi_path,
        "run_root": args.run_root,
        "soundfont_profile": args.soundfont_profile,
        "sample_rate": args.sample_rate,
    }
    if args.input_json:
        payload.update(json.loads(Path(args.input_json).read_text(encoding="utf-8")))

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/audio-render-wav-v2/{_run_id()}"
    payload["run_root"] = run_root
    ctx = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="audio")

    result = AudioRenderWavV2Module().process(ctx, payload)
    out = Path(run_root) / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
