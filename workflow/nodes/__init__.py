"""workflow 노드 패키지.

패키지 import 시점에는 무거운 노드 모듈을 즉시 로드하지 않는다.
일부 실행 환경(예: Python 3.8 컨테이너)에서 불필요한 타입힌트 평가로
실패하는 부작용을 막기 위해 필요 심볼 요청 시점에만 로드한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = [
    "WorkflowEdgeSpec",
    "WorkflowNodeSpec",
    "build_concept_image_node_specs",
    "build_stage_executor_map",
]

if TYPE_CHECKING:
    from .concept_image_nodes import (  # pragma: no cover
        WorkflowEdgeSpec,
        WorkflowNodeSpec,
        build_concept_image_node_specs,
        build_stage_executor_map,
    )


def __getattr__(name: str) -> Any:
    if name in __all__:
        from .concept_image_nodes import (
            WorkflowEdgeSpec,
            WorkflowNodeSpec,
            build_concept_image_node_specs,
            build_stage_executor_map,
        )
        exports = {
            "WorkflowEdgeSpec": WorkflowEdgeSpec,
            "WorkflowNodeSpec": WorkflowNodeSpec,
            "build_concept_image_node_specs": build_concept_image_node_specs,
            "build_stage_executor_map": build_stage_executor_map,
        }
        return exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
