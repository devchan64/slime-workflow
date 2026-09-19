"""픽셀아트 기반 동작 키프레임 장면 구성 단계."""

from __future__ import annotations

from workflow.interfaces import Payload, PipelineContext

from workflow.core.logger import log
from workflow.core.output_paths import local_output_path


class KeyframeSceneCompositionModule:
    name = "keyframe-scene-composition"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        output = dict(payload)
        output["keyframe_scenes"] = {
            "idle": ["idle-0", "idle-1"],
            "move": ["move-0", "move-1", "move-2", "move-3"],
            "attack": ["attack-0", "attack-1", "attack-2"],
            "hit": ["hit-0"],
        }
        output["keyframe_sheet"] = local_output_path("keyframes", "slime-keyframes.png")
        log(context, self.name, "INFO", "동작별 키프레임 장면을 구성했다")
        return output
