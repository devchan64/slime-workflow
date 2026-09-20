"""musicgen-small 노드 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from workflow.interfaces import PipelineContext
from workflow.nodes.musicgen_small.application import MusicgenSmallGenerationModule


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="musicgen-small 생성 노드 실행기")
    parser.add_argument("--prompt", default="", help="생성 프롬프트")
    parser.add_argument("--input-json", default="", help="입력 JSON 파일")
    parser.add_argument("--duration-seconds", type=int, default=30, help="목표 생성 길이(초)")
    parser.add_argument("--run-root", default="", help="결과 루트 디렉터리")
    parser.add_argument("--model-root", default="", help="모델 캐시 루트")
    parser.add_argument("--guidance-scale", type=float, default=3.0)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=250)
    parser.add_argument("--top-p", type=float, default=0.0)
    return parser.parse_args()


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def main() -> None:
    args = parse_args()
    payload = {
        "prompt": args.prompt,
        "duration_seconds": args.duration_seconds,
        "guidance_scale": args.guidance_scale,
        "temperature": args.temperature,
        "top_k": args.top_k,
        "top_p": args.top_p,
        "run_root": args.run_root,
        "model_root": args.model_root,
    }
    if args.input_json:
        raw = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise RuntimeError("--input-json은 JSON 객체여야 합니다")
        payload.update(raw)

    run_root = str(payload.get("run_root", "")).strip() or f".result/workflow/nodes/musicgen-small/{_run_id()}"
    payload["run_root"] = run_root
    context = PipelineContext(run_id=_run_id(), run_root=run_root, area="workflow", pipeline="audio")

    result = MusicgenSmallGenerationModule().process(context, payload)
    output_path = Path(run_root) / "result.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_path))


if __name__ == "__main__":
    main()
