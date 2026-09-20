"""workflow concept-image 노드 진입점."""

from __future__ import annotations

from workflow.interfaces import StageModule
from workflow.nodes.concept_image.application import (
    AnimationFrameRenderingModule,
    DesignConceptGenerationModule,
    KeyframeSceneCompositionModule,
    PixelArtGenerationModule,
)


def ordered_stages() -> list[StageModule]:
    """workflow 기준 concept-image 단계 순서를 반환한다."""

    return [
        DesignConceptGenerationModule(),
        PixelArtGenerationModule(),
        KeyframeSceneCompositionModule(),
        AnimationFrameRenderingModule(),
    ]


__all__ = ["ordered_stages"]
