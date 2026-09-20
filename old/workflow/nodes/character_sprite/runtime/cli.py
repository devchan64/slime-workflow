"""캐릭터 스프라이트 workflow 실행 CLI."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow.core.output_paths import local_run_root
from workflow.interfaces import PipelineContext
from workflow.nodes.character_sprite.application.design_sheet_8dir_generation import create_test_design_sheet
from workflow.nodes.character_sprite_nodes import build_character_sprite_node_specs, build_stage_executor_map


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="캐릭터 디자인시트 기반 8방향 스프라이트 workflow 실행기")
    parser.add_argument("--design-sheet", default="", help="입력 캐릭터 디자인시트 PNG")
    parser.add_argument("--layout", default="", help="방향 영역 또는 source_grid 레이아웃 JSON")
    parser.add_argument("--frame-width", type=int, required=True, help="출력 프레임 너비")
    parser.add_argument("--frame-height", type=int, required=True, help="출력 프레임 높이")
    parser.add_argument("--character-id", default="character", help="캐릭터 식별자")
    parser.add_argument("--animation-id", default="idle", help="애니메이션 식별자")
    parser.add_argument("--output-png", default="", help="출력 스프라이트 시트 PNG")
    parser.add_argument("--output-meta", default="", help="출력 메타데이터 JSON")
    parser.add_argument("--run-root", default="", help="실행 산출물 루트")
    parser.add_argument("--generate-test-resource", default="", help="기본 동작 검증용 디자인시트 PNG 생성 경로")
    return parser.parse_args()


def build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    run_id = build_run_id()
    if args.generate_test_resource:
        resource = create_test_design_sheet(Path(args.generate_test_resource))
        print(f"테스트 디자인시트 생성 완료: {resource['path']}")
        if not args.design_sheet:
            return

    if not args.design_sheet:
        raise RuntimeError("--design-sheet 입력이 필요하다")

    run_root = Path(args.run_root) if args.run_root else Path(local_run_root("character-sprite", run_id))
    output_png = Path(args.output_png) if args.output_png else run_root / "sprite" / f"{args.character_id}_8dir_{args.frame_width}x{args.frame_height}.png"
    output_meta = Path(args.output_meta) if args.output_meta else run_root / "sprite" / f"{args.character_id}_8dir_{args.frame_width}x{args.frame_height}.json"

    nodes = build_character_sprite_node_specs()
    executors = build_stage_executor_map()
    context = PipelineContext(run_id=run_id, run_root=str(run_root), area="ai-workflow", pipeline="character")
    payload: dict[str, Any] = {
        "design_sheet": args.design_sheet,
        "layout_path": args.layout,
        "frame_width": args.frame_width,
        "frame_height": args.frame_height,
        "character_id": args.character_id,
        "animation_id": args.animation_id,
        "output_png": str(output_png),
        "output_meta": str(output_meta),
        "run_id": run_id,
        "run_root": str(run_root),
    }

    current = payload
    for node in nodes:
        current = executors[node.node_id](context, current)

    result_path = run_root / "result.json"
    result = {
        "pipeline": "sprite-8dir-from-concept",
        "run_id": run_id,
        "node_id": nodes[-1].node_id,
        "package": {
            "package_id": nodes[-1].package_id,
            "manifest": nodes[-1].package_manifest,
        },
        "result": current,
        "logs": context.stage_logs,
    }
    save_json(result_path, result)
    print(f"결과 저장 완료: {result_path}")


if __name__ == "__main__":
    main()
