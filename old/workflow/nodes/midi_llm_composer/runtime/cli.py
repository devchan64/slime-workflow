"""MIDI-LLM 노드 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_llm_composer.application.stage import MidiLlmComposerModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MIDI-LLM 작곡 노드 실행기")
    parser.add_argument("--prompt", default="", help="작곡 프롬프트")
    parser.add_argument("--input-json", default="", help="입력 JSON 파일")
    parser.add_argument("--max-new-tokens", type=int, default=2048)
    parser.add_argument("--temperature", type=float, default=0.65)
    parser.add_argument("--top-p", type=float, default=0.82)
    parser.add_argument("--top-k", type=int, default=32)
    parser.add_argument("--repetition-penalty", type=float, default=1.08)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--model-root", default="")
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "prompt": args.prompt,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "top_k": args.top_k,
        "repetition_penalty": args.repetition_penalty,
        "run_root": args.run_root,
        "model_root": args.model_root,
    }
    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("--input-json은 JSON 객체여야 합니다")
        payload.update(raw)

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/midi-llm-composer/{_run_id()}"
    payload["run_root"] = run_root
    context = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="music")

    result = MidiLlmComposerModule().process(context, payload)
    output_path = Path(run_root) / "result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
