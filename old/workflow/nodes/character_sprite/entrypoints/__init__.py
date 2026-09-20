"""캐릭터 스프라이트 workflow 노드 진입점."""

from __future__ import annotations

from workflow.interfaces import StageModule

from ..application import DesignSheet8DirGenerationModule


def ordered_stages() -> list[StageModule]:
    """캐릭터 스프라이트 기본 노드 순서를 반환한다."""

    return [DesignSheet8DirGenerationModule()]


__all__ = ["DesignSheet8DirGenerationModule", "ordered_stages"]
