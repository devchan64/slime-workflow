"""디자인 컨셉 기반 픽셀아트 생성 단계."""

from __future__ import annotations

from workflow.interfaces import Payload, PipelineContext

from workflow.core.logger import log
from workflow.core.output_paths import local_output_path


class PixelArtGenerationModule:
    name = "pixel-art-generation"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        concept = payload.get("design_concept", {})

        output = dict(payload)
        output["pixel_art"] = {
            "path": local_output_path("pixel", "slime-base.png"),
            "resolution": "64x64",
            "palette": "32-color",
            "source_theme": concept.get("theme", "unknown"),
        }
        log(context, self.name, "INFO", "컨셉 기반 픽셀아트 결과를 기록했다")
        return output
