"""캐릭터 디자인시트 기반 8방향 스프라이트 계약."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DIRECTION_IDS: tuple[str, ...] = (
    "south",
    "south_west",
    "west",
    "north_west",
    "north",
    "north_east",
    "east",
    "south_east",
)


@dataclass(frozen=True)
class DirectionRegion:
    """디자인시트에서 한 방향 원본을 가져올 영역."""

    direction: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class SpriteSheetRequest:
    """8방향 스프라이트 생성 요청."""

    design_sheet: Path
    output_png: Path
    output_meta: Path
    frame_width: int
    frame_height: int
    layout_path: Path | None = None
    character_id: str = "character"
    animation_id: str = "idle"
