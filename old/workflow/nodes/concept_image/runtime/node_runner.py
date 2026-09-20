"""workflow 노드 구조로 콘셉트 이미지 단위를 실행하는 경량 러너."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow.core.output_paths import local_run_root
from workflow.interfaces import PipelineContext
from workflow.nodes.concept_image_nodes import (
    build_concept_image_node_specs,
    build_stage_executor_map,
)


def _utc_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")


def describe_concept_image_graph() -> dict[str, Any]:
    """콘셉트 이미지 workflow 그래프 메타데이터를 반환한다."""

    nodes, edges = build_concept_image_node_specs()
    return {
        "pipeline_id": "concept-image.node-graph",
        "version": "0.1.0",
        "nodes": [asdict(node) for node in nodes],
        "edges": [asdict(edge) for edge in edges],
    }


def run_concept_image_nodes(payload: dict[str, Any], *, run_id: str | None = None) -> dict[str, Any]:
    """콘셉트 이미지 노드를 식별자 순서대로 실행한다."""

    nodes, _ = build_concept_image_node_specs()
    executors = build_stage_executor_map()

    current = dict(payload)
    stage_logs: list[dict[str, str]] = []
    resolved_run_id = run_id or _utc_run_id()
    run_root = str(payload.get("run_root", "")).strip() or local_run_root("concept-image", resolved_run_id)

    context = PipelineContext(
        run_id=resolved_run_id,
        run_root=run_root,
        area="workflow-node-runner",
        pipeline="concept-image",
        stage_logs=stage_logs,
    )

    for node in nodes:
        stage_runner = executors[node.node_id]
        current = stage_runner(context, current)

    return {
        "run_id": resolved_run_id,
        "graph": describe_concept_image_graph(),
        "result": current,
    }


def run_concept_image_unit(payload: dict[str, Any], unit: int, *, run_id: str | None = None) -> dict[str, Any]:
    """콘셉트 이미지 노드 하나만 실행한다."""

    if unit < 1 or unit > 4:
        raise RuntimeError(f"지원하지 않는 concept-image unit이다: {unit}")

    nodes, _ = build_concept_image_node_specs()
    executors = build_stage_executor_map()
    node = nodes[unit - 1]
    resolved_run_id = run_id or _utc_run_id()
    run_root = str(payload.get("run_root", "")).strip() or local_run_root("concept-image", resolved_run_id)
    stage_logs: list[dict[str, str]] = []
    context = PipelineContext(
        run_id=resolved_run_id,
        run_root=run_root,
        area="workflow-node-runner",
        pipeline="concept-image",
        stage_logs=stage_logs,
    )
    result = executors[node.node_id](context, dict(payload))
    return {
        "mode": "unit",
        "unit": unit,
        "node_id": node.node_id,
        "pipeline": "concept-image",
        "run_id": resolved_run_id,
        "result": result,
        "logs": stage_logs,
    }


def export_graph(output_path: str) -> str:
    """그래프 메타데이터를 JSON 파일로 저장한다."""

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(describe_concept_image_graph(), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(destination)
