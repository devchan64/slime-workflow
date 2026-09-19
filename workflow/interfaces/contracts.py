"""workflow 인터페이스 계약."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Protocol


Payload = Dict[str, Any]

PipelineName = Literal["concept-image", "music", "audio", "character", "visual"]


@dataclass
class PipelineContext:
    """파이프라인 실행 컨텍스트."""

    run_id: str
    run_root: str = ""
    area: str = "ai-workflow"
    pipeline: PipelineName = "concept-image"
    stage_logs: List[Dict[str, str]] = field(default_factory=list)

class StageModule(Protocol):
    """모든 단계 모듈이 만족해야 하는 계약."""

    name: str

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        """입력 payload를 받아 다음 단계 payload로 변환한다."""


AllowedIOType = Literal["png", "wav", "mp3", "mid", "midi", "sf2", "txt", "md", "json", "yaml"]


@dataclass(frozen=True)
class UnitIOContract:
    """단위 명령 입출력 계약."""

    required_inputs: List[str]
    optional_inputs: List[str]
    outputs: List[str]
    allowed_types: List[AllowedIOType]


@dataclass(frozen=True)
class UnitPrepareContract:
    """단위 명령 준비 계약."""

    dependency_files: List[str]
    dependency_fetch_commands: List[List[str]]
    install_commands: List[List[str]]
    model_commands: List[List[str]]
    required_model_ids: List[str]


@dataclass(frozen=True)
class UnitPackageSpec:
    """단위 명령 패키지 계약."""

    package_id: str
    version: str
    unit: int
    node_id: str
    command: str
    io: UnitIOContract
    prepare: UnitPrepareContract
    tests: List[Dict[str, Any]]
