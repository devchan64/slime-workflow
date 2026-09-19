"""MIDI-LLM planner 노드 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.midi_llm_planner.application.stage import MidiLlmPlannerModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MIDI-LLM planner 노드 실행기")
    parser.add_argument("--prompt", default="", help="사용자 작곡 프롬프트")
    parser.add_argument("--input-json", default="", help="입력 JSON 파일")
    parser.add_argument("--run-root", default="")
    parser.add_argument("--planner-model-root", default="")
    parser.add_argument("--composer-model-root", default="")
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "prompt": args.prompt,
        "run_root": args.run_root,
        "planner_model_root": args.planner_model_root,
        "composer_model_root": args.composer_model_root,
    }
    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("--input-json은 JSON 객체여야 합니다")
        payload.update(raw)

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/midi-llm-planner/{_run_id()}"
    payload["run_root"] = run_root
    context = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="music")

    result = MidiLlmPlannerModule().process(context, payload)
    out = Path(run_root) / "result.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out))


if __name__ == "__main__":
    main()
