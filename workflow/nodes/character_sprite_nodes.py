"""캐릭터 스프라이트 단위 노드 정의."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from workflow.nodes.character_sprite.entrypoints import ordered_stages


@dataclass(frozen=True)
class CharacterSpriteNodeSpec:
    """캐릭터 스프라이트 노드 계약 요약."""

    node_id: str
    package_id: str
    package_manifest: str
    stage_name: str
    description: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]


STAGE_NODE_MAP: dict[str, CharacterSpriteNodeSpec] = {
    "design-sheet-8dir-generation": CharacterSpriteNodeSpec(
        node_id="sprite.generate",
        package_id="character-sprite.design-sheet-8dir",
        package_manifest="workflow/nodes/character_sprite/packages/design-sheet-8dir.json",
        stage_name="design-sheet-8dir-generation",
        description="캐릭터 디자인시트를 주어진 프레임 크기의 8방향 스프라이트 시트로 변환한다.",
        input_types=("png", "json"),
        output_types=("png", "json"),
    )
}


def build_character_sprite_node_specs() -> list[CharacterSpriteNodeSpec]:
    """캐릭터 스프라이트 stage 순서를 workflow 노드 목록으로 변환한다."""

    specs: list[CharacterSpriteNodeSpec] = []
    for stage in ordered_stages():
        spec = STAGE_NODE_MAP.get(stage.name)
        if spec is None:
            raise KeyError(f"등록되지 않은 stage 이름: {stage.name}")
        specs.append(spec)
    return specs


def build_stage_executor_map() -> dict[str, Callable]:
    """노드 식별자 기준 stage 실행기 매핑을 반환한다."""

    executors: dict[str, Callable] = {}
    for stage in ordered_stages():
        spec = STAGE_NODE_MAP.get(stage.name)
        if spec is None:
            raise KeyError(f"등록되지 않은 stage 이름: {stage.name}")
        executors[spec.node_id] = stage.process
    return executors
