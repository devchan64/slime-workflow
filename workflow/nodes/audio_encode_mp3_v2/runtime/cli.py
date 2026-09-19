from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.audio_encode_mp3_v2.application.stage import AudioEncodeMp3V2Module


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="audio encode mp3 v2 CLI")
    p.add_argument("--wav-path", default="")
    p.add_argument("--bitrate", default="192k")
    p.add_argument("--input-json", default="")
    p.add_argument("--run-root", default="")
    return p.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "wav_path": args.wav_path,
        "bitrate": args.bitrate,
        "run_root": args.run_root,
    }
    if args.input_json:
        payload.update(json.loads(Path(args.input_json).read_text(encoding="utf-8")))

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/audio-encode-mp3-v2/{_run_id()}"
    payload["run_root"] = run_root
    ctx = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="audio")

    result = AudioEncodeMp3V2Module().process(ctx, payload)
    out = Path(run_root) / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
