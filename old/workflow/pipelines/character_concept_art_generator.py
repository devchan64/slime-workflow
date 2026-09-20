"""character-concept-art-generator 파이프라인 실행기."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow.core.output_paths import local_run_root, local_runtime_output_path
from workflow.nodes.concept_image.runtime.node_runner import run_concept_image_nodes
from workflow.nodes.concept_image_nodes import build_concept_image_node_specs


PIPELINE_ID = "character-concept-art-generator"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="캐릭터 컨셉아트 파이프라인 실행기")
    parser.add_argument("--prompt", required=True, help="캐릭터 프롬프트")
    parser.add_argument("--md", default="", help="SSOT/참조 문서 파일 경로")
    parser.add_argument("--txt", default="", help="추가 텍스트 프롬프트")
    parser.add_argument("--json-attributes", default="", help="추가 속성 JSON")
    parser.add_argument("--reference-image", action="append", default=[], help="레퍼런스 이미지 파일 경로")
    parser.add_argument("--reference-manifest", help="레퍼런스 이미지 목록 JSON 파일 경로")
    parser.add_argument("--model-id", default="sd15-base", help="사용할 생성 모델 ID")
    parser.add_argument("--controlnet-id", default="", help="사용할 ControlNet ID")
    parser.add_argument("--ip-adapter-id", default="", help="사용할 IP-Adapter ID")
    parser.add_argument("--negative-prompt", default="", help="생성 억제용 네거티브 프롬프트")
    parser.add_argument("--generation-prompt", default="", help="모델 추론용 생성 프롬프트")
    parser.add_argument("--generation-negative-prompt", default="", help="모델 추론용 네거티브 프롬프트")
    parser.add_argument("--style", default="cartoon", help="아트 스타일")
    parser.add_argument("--seed", type=int, default=42, help="재현용 시드")
    parser.add_argument("--steps", type=int, default=28, help="추론 스텝 수")
    parser.add_argument("--guidance-scale", type=float, default=8.0, help="CFG 스케일")
    parser.add_argument("--ip-adapter-scale", type=float, default=0.55, help="IP-Adapter 영향도")
    parser.add_argument(
        "--controlnet-conditioning-scale",
        type=float,
        default=1.0,
        help="ControlNet 영향도",
    )
    parser.add_argument("--strength", type=float, default=0.35, help="img2img strength")
    parser.add_argument("--width", type=int, default=512, help="출력 폭")
    parser.add_argument("--height", type=int, default=512, help="출력 높이")
    parser.add_argument("--num-outputs", type=int, default=1, help="생성 후보 수")
    parser.add_argument(
        "--character-mode",
        choices=["dry-run", "worker"],
        default="dry-run",
        help="실행 모드 (dry-run은 실제 생성 없음)",
    )
    parser.add_argument("--run-root", default="", help="파이프라인 실행 루트")
    parser.add_argument(
        "--output",
        default=local_runtime_output_path("character-concept-art-generator-result.json"),
        help="결과 JSON 경로",
    )
    parser.add_argument(
        "--output-image",
        default="",
        help="최종 PNG 산출물 경로(미지정 시 run-root/final/concept-art.png)",
    )
    parser.add_argument("--control-image", help="ControlNet 조건 이미지 파일 경로")
    parser.add_argument("--ip-adapter-image", help="IP-Adapter 조건 이미지 파일 경로")
    return parser.parse_args()


def parse_json_object(value: str, name: str) -> dict[str, Any]:
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{name}는 JSON 객체여야 한다")
    return parsed


def read_optional_text(path_value: str) -> str:
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.is_file():
        raise RuntimeError(f"텍스트 파일이 없다: {path}")
    return path.read_text(encoding="utf-8").strip()


def resolve_reference_images(cli_paths: list[str], manifest_path: str | None) -> list[dict[str, str]]:
    references: list[str] = list(cli_paths)
    if manifest_path:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        manifest_images = manifest.get("images", [])
        if not isinstance(manifest_images, list):
            raise RuntimeError("reference-manifest의 images는 배열이어야 한다")
        references.extend(str(item) for item in manifest_images)

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in references:
        path = Path(raw).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError(f"참조 이미지 파일이 없다: {path}")
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append({"path": key, "name": path.name})
    return normalized


def build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def compose_prompt(base_prompt: str, md_path: str, txt_path: str, attrs: dict[str, Any]) -> str:
    parts = [base_prompt]
    if md_path:
        md_content = read_optional_text(md_path)
        if md_content:
            parts.append(f"[SSOT]\n{md_content}")
    if txt_path:
        txt_content = read_optional_text(txt_path)
        if txt_content:
            parts.append(f"[TXT]\n{txt_content}")
    if attrs_prompt := str(attrs.get("prompt", "")).strip():
        parts.append(f"[ATTRS]\n{attrs_prompt}")
    return "\n\n".join(part for part in parts if part)


def resolve_output_path(args_output_image: str, run_root: Path) -> Path:
    if args_output_image.strip():
        return Path(args_output_image).expanduser()
    return run_root / "final" / "character-concept-art.png"


def resolve_final_image_payload(result_payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    candidate_keys = ("design_concept_sheet_image", "design_concept_render_image", "design_concept_image")
    for key in candidate_keys:
        value = result_payload.get(key)
        if isinstance(value, dict) and value.get("path"):
            return value, key
    return {}, ""


def build_pipeline_nodes() -> list[dict[str, str]]:
    nodes = build_concept_image_node_specs()[0]
    return [{"node_id": node.node_id, "package_id": node.package_id, "manifest": node.package_manifest} for node in nodes]


def main() -> None:
    args = parse_args()
    run_id = build_run_id()
    run_root = Path(args.run_root) if args.run_root else Path(local_run_root("character-concept-art-generator", run_id))
    output_path = Path(args.output)
    output_image_path = resolve_output_path(args.output_image, run_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    reference_images = resolve_reference_images(args.reference_image, args.reference_manifest)
    attr_payload = parse_json_object(args.json_attributes, "json-attributes")

    payload = {
        "pipeline": "concept-image",
        "prompt": compose_prompt(args.prompt, args.md, args.txt, attr_payload),
        "model_id": str(attr_payload.get("model_id", args.model_id)).strip() or args.model_id,
        "controlnet_id": str(attr_payload.get("controlnet_id", args.controlnet_id)).strip(),
        "ip_adapter_id": str(attr_payload.get("ip_adapter_id", args.ip_adapter_id)).strip(),
        "negative_prompt": str(attr_payload.get("negative_prompt", args.negative_prompt)).strip(),
        "generation_prompt": str(attr_payload.get("generation_prompt", args.generation_prompt)).strip(),
        "generation_negative_prompt": str(attr_payload.get("generation_negative_prompt", args.generation_negative_prompt)).strip(),
        "style": str(attr_payload.get("style", args.style)).strip(),
        "seed": int(attr_payload.get("seed", args.seed)),
        "steps": int(attr_payload.get("steps", args.steps)),
        "guidance_scale": float(attr_payload.get("guidance_scale", args.guidance_scale)),
        "ip_adapter_scale": float(attr_payload.get("ip_adapter_scale", args.ip_adapter_scale)),
        "controlnet_conditioning_scale": float(attr_payload.get("controlnet_conditioning_scale", args.controlnet_conditioning_scale)),
        "strength": float(attr_payload.get("strength", args.strength)),
        "width": int(attr_payload.get("width", args.width)),
        "height": int(attr_payload.get("height", args.height)),
        "num_outputs": max(1, int(attr_payload.get("num_outputs", args.num_outputs))),
        "run_id": run_id,
        "run_root": str(run_root),
        "reference_images": reference_images,
    }
    if args.control_image:
        payload["control_image_path"] = str(Path(args.control_image).expanduser().resolve())
    if args.ip_adapter_image:
        payload["ip_adapter_image_path"] = str(Path(args.ip_adapter_image).expanduser().resolve())

    if args.character_mode == "dry-run":
        result_payload = {
            "mode": "dry-run",
            "pipeline": "concept-image",
            "run_id": run_id,
            "result": payload,
            "nodes": build_pipeline_nodes(),
            "prompt": payload["prompt"],
        }
        outputs = {
            "path": str(output_image_path),
            "format": "png",
            "status": "planned",
        }
        result_object = {
            "pipeline": PIPELINE_ID,
            "mode": "dry-run",
            "run_id": run_id,
            "run_root": str(run_root),
            "nodes": build_pipeline_nodes(),
            "inputs": {
                "prompt": args.prompt,
                "style": payload["style"],
                "seed": payload["seed"],
                "steps": payload["steps"],
                "guidance_scale": payload["guidance_scale"],
                "width": payload["width"],
                "height": payload["height"],
                "num_outputs": payload["num_outputs"],
                "reference_count": len(reference_images),
            },
            "outputs": {
                "png": outputs,
                "json": {"path": str(output_path), "format": "json", "status": "planned"},
            },
            "result": result_payload,
        }
    else:
        graph_result = run_concept_image_nodes(payload, run_id=run_id)
        final_image_entry, source_key = resolve_final_image_payload(graph_result.get("result", {}))
        status = "rendered" if source_key else "planned"
        final_image_status = status
        final_image_path = Path(final_image_entry.get("path", "")).resolve() if final_image_entry else output_image_path
        output_image_path = final_image_path

        result_object = {
            "pipeline": PIPELINE_ID,
            "mode": "worker",
            "run_id": run_id,
            "run_root": str(run_root),
            "graph": graph_result["graph"],
            "nodes": build_pipeline_nodes(),
            "inputs": {
                "prompt": args.prompt,
                "style": payload["style"],
                "seed": payload["seed"],
                "steps": payload["steps"],
                "guidance_scale": payload["guidance_scale"],
                "width": payload["width"],
                "height": payload["height"],
                "num_outputs": payload["num_outputs"],
                "reference_count": len(reference_images),
            },
            "outputs": {
                "png": {
                    "path": str(output_image_path),
                    "format": "png",
                    "status": final_image_status,
                    "source": source_key or None,
                },
                "json": {
                    "path": str(output_path),
                    "format": "json",
                    "status": "rendered",
                },
            },
            "result": {
                "mode": "worker",
                "pipeline": "concept-image",
                "graph": graph_result["graph"],
                "concept": graph_result["result"],
            },
        }

    output_path.write_text(json.dumps(result_object, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"결과 저장 완료: {output_path}")
    print(f"최종 PNG 산출 경로: {output_image_path}")


if __name__ == "__main__":
    main()
