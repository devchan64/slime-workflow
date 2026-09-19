"""키프레임 기반 애니메이션 프레임 렌더링 단계."""

from __future__ import annotations

from workflow.interfaces import Payload, PipelineContext

from workflow.core.logger import log
from workflow.core.output_paths import local_output_path


class AnimationFrameRenderingModule:
    name = "animation-frame-rendering"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        keyframes = payload.get("keyframe_scenes", {})
        total_frames = sum(len(v) for v in keyframes.values()) if keyframes else 0

        output = dict(payload)
        output["animation_frames"] = {
            "sheet_path": local_output_path("animation", "slime-animation-sheet.png"),
            "preview_gif": local_output_path("animation", "slime-preview.gif"),
            "total_frames": total_frames,
            "fps": 8,
        }
        log(context, self.name, "INFO", "키프레임 기반 애니메이션 프레임을 렌더링했다")
        return output
