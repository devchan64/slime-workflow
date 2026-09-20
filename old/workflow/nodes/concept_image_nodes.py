"""콘셉트 이미지 단위 노드 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from workflow.nodes.concept_image.entrypoints import ordered_stages


@dataclass(frozen=True)
class WorkflowNodeSpec:
    """workflow 노드 계약 요약."""

    node_id: str
    package_id: str
    package_manifest: str
    stage_name: str
    description: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowEdgeSpec:
    """workflow 노드 연결선 정의."""

    source: str
    target: str


STAGE_NODE_MAP: dict[str, WorkflowNodeSpec] = {
    "design-concept-generation": WorkflowNodeSpec(
        node_id="concept.design.generate",
        package_id="concept-image.unit-1.design-generate",
        package_manifest="workflow/nodes/concept_image/packages/unit-1-design-generate.json",
        stage_name="design-concept-generation",
        description="프롬프트/레퍼런스를 받아 콘셉트 이미지를 준비한다.",
        input_types=("txt", "md", "json", "png"),
        output_types=("json", "png"),
    ),
    "pixel-art-generation": WorkflowNodeSpec(
        node_id="concept.pixel.generate",
        package_id="concept-image.unit-2.pixel-generate",
        package_manifest="workflow/nodes/concept_image/packages/unit-2-pixel-generate.json",
        stage_name="pixel-art-generation",
        description="콘셉트 결과를 픽셀아트 스타일로 변환한다.",
        input_types=("json", "png"),
        output_types=("json", "png"),
    ),
    "keyframe-scene-composition": WorkflowNodeSpec(
        node_id="concept.keyframe.compose",
        package_id="concept-image.unit-3.keyframe-compose",
        package_manifest="workflow/nodes/concept_image/packages/unit-3-keyframe-compose.json",
        stage_name="keyframe-scene-composition",
        description="동작 키프레임 장면을 조합한다.",
        input_types=("json", "png"),
        output_types=("json", "png"),
    ),
    "animation-frame-rendering": WorkflowNodeSpec(
        node_id="concept.animation.render",
        package_id="concept-image.unit-4.animation-render",
        package_manifest="workflow/nodes/concept_image/packages/unit-4-animation-render.json",
        stage_name="animation-frame-rendering",
        description="키프레임 입력으로 프레임 시퀀스를 렌더링한다.",
        input_types=("json", "png"),
        output_types=("json", "png"),
    ),
}


def build_concept_image_node_specs() -> tuple[list[WorkflowNodeSpec], list[WorkflowEdgeSpec]]:
    """콘셉트 이미지 stage 순서를 workflow 노드/엣지 목록으로 변환한다."""

    stage_instances = ordered_stages()
    node_specs: list[WorkflowNodeSpec] = []
    edges: list[WorkflowEdgeSpec] = []

    for index, stage in enumerate(stage_instances):
        spec = STAGE_NODE_MAP.get(stage.name)
        if spec is None:
            raise KeyError(f"등록되지 않은 stage 이름: {stage.name}")
        node_specs.append(spec)
        if index == 0:
            continue
        edges.append(WorkflowEdgeSpec(source=node_specs[index - 1].node_id, target=spec.node_id))

    return node_specs, edges


def build_stage_executor_map() -> dict[str, Callable]:
    """노드 식별자 기준 stage 실행기 매핑을 반환한다."""

    executors: dict[str, Callable] = {}
    for stage in ordered_stages():
        spec = STAGE_NODE_MAP.get(stage.name)
        if spec is None:
            raise KeyError(f"등록되지 않은 stage 이름: {stage.name}")
        executors[spec.node_id] = stage.process
    return executors
