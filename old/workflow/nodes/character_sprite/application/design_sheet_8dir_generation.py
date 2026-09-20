"""디자인시트를 8방향 고정 크기 스프라이트 시트로 변환한다."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from workflow.core.logger import log
from workflow.interfaces import Payload, PipelineContext
from ..domain import DIRECTION_IDS, DirectionRegion, SpriteSheetRequest


PACKAGE_DIR = Path("workflow/nodes/character_sprite/packages")
DEFAULT_LAYOUT_PATH = PACKAGE_DIR / "default-8dir-layout.json"


class DesignSheet8DirGenerationModule:
    """캐릭터 디자인시트 기반 8방향 스프라이트 생성 노드."""

    name = "design-sheet-8dir-generation"

    def process(self, context: PipelineContext, payload: Payload) -> Payload:
        request = self._build_request(payload)
        metadata = generate_sprite_sheet_from_design_sheet(request)
        output = dict(payload)
        output["sprite_sheet"] = {
            "path": str(request.output_png),
            "meta_path": str(request.output_meta),
            "frame_width": request.frame_width,
            "frame_height": request.frame_height,
            "directions": list(DIRECTION_IDS),
        }
        output["sprite_metadata"] = metadata
        log(
            context,
            self.name,
            "INFO",
            f"8방향 스프라이트 생성 완료: {request.output_png} ({request.frame_width}x{request.frame_height})",
        )
        return output

    def _build_request(self, payload: Payload) -> SpriteSheetRequest:
        design_sheet = _required_path(payload, "design_sheet")
        output_png = _required_path(payload, "output_png")
        output_meta = _required_path(payload, "output_meta")
        frame_width = _required_positive_int(payload, "frame_width")
        frame_height = _required_positive_int(payload, "frame_height")
        layout_value = str(payload.get("layout_path", "")).strip()
        layout_path = Path(layout_value) if layout_value else None
        return SpriteSheetRequest(
            design_sheet=design_sheet,
            output_png=output_png,
            output_meta=output_meta,
            frame_width=frame_width,
            frame_height=frame_height,
            layout_path=layout_path,
            character_id=str(payload.get("character_id", "character")).strip() or "character",
            animation_id=str(payload.get("animation_id", "idle")).strip() or "idle",
        )


def generate_sprite_sheet_from_design_sheet(request: SpriteSheetRequest) -> dict[str, Any]:
    """디자인시트 PNG를 8방향 1행 스프라이트 시트로 변환한다."""

    if not request.design_sheet.is_file():
        raise RuntimeError(f"디자인시트 파일이 없다: {request.design_sheet}")
    if request.frame_width <= 0 or request.frame_height <= 0:
        raise RuntimeError(f"프레임 크기는 양수여야 한다: {request.frame_width}x{request.frame_height}")

    layout = _load_layout(request.layout_path)
    source = Image.open(request.design_sheet).convert("RGBA")
    regions = _resolve_regions(source.size, layout)
    output = Image.new("RGBA", (request.frame_width * len(DIRECTION_IDS), request.frame_height), (0, 0, 0, 0))
    direction_meta: list[dict[str, Any]] = []

    for index, region in enumerate(regions):
        crop = source.crop((region.x, region.y, region.x + region.width, region.y + region.height))
        frame = _fit_to_frame(crop, request.frame_width, request.frame_height)
        frame_x = index * request.frame_width
        output.alpha_composite(frame, (frame_x, 0))
        direction_meta.append(
            {
                "direction": region.direction,
                "index": index,
                "row": 0,
                "column": index,
                "x": frame_x,
                "y": 0,
                "width": request.frame_width,
                "height": request.frame_height,
                "source_region": {
                    "x": region.x,
                    "y": region.y,
                    "width": region.width,
                    "height": region.height,
                },
            }
        )

    request.output_png.parent.mkdir(parents=True, exist_ok=True)
    request.output_meta.parent.mkdir(parents=True, exist_ok=True)
    output.save(request.output_png)

    metadata: dict[str, Any] = {
        "version": "0.1.0",
        "node_id": "sprite.generate",
        "package_id": "character-sprite.design-sheet-8dir",
        "character_id": request.character_id,
        "animation_id": request.animation_id,
        "source_design_sheet": str(request.design_sheet),
        "sprite_sheet": str(request.output_png),
        "frame": {
            "width": request.frame_width,
            "height": request.frame_height,
            "count": len(DIRECTION_IDS),
        },
        "layout": {
            "rows": 1,
            "columns": len(DIRECTION_IDS),
            "direction_order": list(DIRECTION_IDS),
        },
        "directions": direction_meta,
    }
    request.output_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def create_test_design_sheet(path: Path, cell_width: int = 96, cell_height: int = 128) -> dict[str, Any]:
    """기본 동작 검증용 8방향 디자인시트 PNG를 만든다."""

    if cell_width <= 0 or cell_height <= 0:
        raise RuntimeError(f"테스트 리소스 셀 크기는 양수여야 한다: {cell_width}x{cell_height}")
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (cell_width * len(DIRECTION_IDS), cell_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    palette = [
        (231, 76, 60, 255),
        (230, 126, 34, 255),
        (241, 196, 15, 255),
        (46, 204, 113, 255),
        (26, 188, 156, 255),
        (52, 152, 219, 255),
        (155, 89, 182, 255),
        (149, 165, 166, 255),
    ]
    for index, direction in enumerate(DIRECTION_IDS):
        left = index * cell_width
        color = palette[index]
        body_box = (
            left + max(4, cell_width // 4),
            max(8, cell_height // 5),
            left + cell_width - max(4, cell_width // 4),
            cell_height - max(8, cell_height // 8),
        )
        draw.rectangle((left, 0, left + cell_width - 1, cell_height - 1), outline=(40, 40, 40, 255), width=1)
        draw.ellipse(body_box, fill=color, outline=(20, 20, 20, 255), width=2)
        marker_x = left + cell_width // 2
        marker_y = max(8, cell_height // 8)
        draw.polygon(
            [
                (marker_x, marker_y),
                (marker_x - max(4, cell_width // 12), marker_y + max(8, cell_height // 10)),
                (marker_x + max(4, cell_width // 12), marker_y + max(8, cell_height // 10)),
            ],
            fill=(20, 20, 20, 255),
        )
        draw.text((left + 4, cell_height - 16), str(index + 1), fill=(20, 20, 20, 255))
        draw.text((left + 4, 4), direction[:2], fill=(20, 20, 20, 255))
    image.save(path)
    return {
        "path": str(path),
        "width": image.width,
        "height": image.height,
        "cell_width": cell_width,
        "cell_height": cell_height,
        "directions": list(DIRECTION_IDS),
    }


def _load_layout(layout_path: Path | None) -> dict[str, Any]:
    path = layout_path or DEFAULT_LAYOUT_PATH
    if not path.is_file():
        raise RuntimeError(f"레이아웃 파일이 없다: {path}")
    parsed = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise RuntimeError(f"레이아웃은 JSON 객체여야 한다: {path}")
    return parsed


def _resolve_regions(source_size: tuple[int, int], layout: dict[str, Any]) -> list[DirectionRegion]:
    source_regions = layout.get("source_regions")
    if source_regions is not None:
        return _parse_explicit_regions(source_regions, source_size)

    source_grid = layout.get("source_grid")
    if not isinstance(source_grid, dict):
        raise RuntimeError("레이아웃에는 source_grid 또는 source_regions가 필요하다")
    columns = int(source_grid.get("columns", 0))
    rows = int(source_grid.get("rows", 0))
    if columns != len(DIRECTION_IDS) or rows != 1:
        raise RuntimeError(f"8방향 스프라이트 source_grid는 columns=8, rows=1이어야 한다: {columns}x{rows}")
    width, height = source_size
    if width < columns or height < rows:
        raise RuntimeError(f"디자인시트가 source_grid보다 작다: image={width}x{height}, grid={columns}x{rows}")
    cell_width = int(source_grid.get("cell_width") or width // columns)
    cell_height = int(source_grid.get("cell_height") or height // rows)
    if cell_width <= 0 or cell_height <= 0:
        raise RuntimeError(f"source_grid 셀 크기는 양수여야 한다: {cell_width}x{cell_height}")
    if cell_width * columns > width or cell_height * rows > height:
        raise RuntimeError(
            f"source_grid 셀 범위가 디자인시트 밖으로 벗어난다: "
            f"image={width}x{height}, cell={cell_width}x{cell_height}, grid={columns}x{rows}"
        )
    return [
        DirectionRegion(direction=direction, x=index * cell_width, y=0, width=cell_width, height=cell_height)
        for index, direction in enumerate(DIRECTION_IDS)
    ]


def _parse_explicit_regions(source_regions: Any, source_size: tuple[int, int]) -> list[DirectionRegion]:
    if not isinstance(source_regions, list):
        raise RuntimeError("source_regions는 배열이어야 한다")
    if len(source_regions) != len(DIRECTION_IDS):
        raise RuntimeError(f"source_regions는 정확히 8개여야 한다: {len(source_regions)}")
    regions: list[DirectionRegion] = []
    for index, item in enumerate(source_regions):
        if not isinstance(item, dict):
            raise RuntimeError(f"source_regions[{index}]는 객체여야 한다")
        direction = str(item.get("direction", "")).strip()
        expected = DIRECTION_IDS[index]
        if direction != expected:
            raise RuntimeError(f"방향 순서가 맞지 않는다: index={index}, expected={expected}, actual={direction}")
        region = DirectionRegion(
            direction=direction,
            x=int(item.get("x", -1)),
            y=int(item.get("y", -1)),
            width=int(item.get("width", 0)),
            height=int(item.get("height", 0)),
        )
        if region.x < 0 or region.y < 0 or region.width <= 0 or region.height <= 0:
            raise RuntimeError(f"source_regions[{index}] 영역 값이 올바르지 않다: {item}")
        source_width, source_height = source_size
        if region.x + region.width > source_width or region.y + region.height > source_height:
            raise RuntimeError(
                f"source_regions[{index}] 영역이 디자인시트 밖으로 벗어난다: "
                f"region={item}, image={source_width}x{source_height}"
            )
        regions.append(region)
    return regions


def _fit_to_frame(image: Image.Image, frame_width: int, frame_height: int) -> Image.Image:
    bbox = image.getbbox()
    subject = image.crop(bbox) if bbox else image
    scale = min(frame_width / subject.width, frame_height / subject.height)
    resized_width = max(1, int(subject.width * scale))
    resized_height = max(1, int(subject.height * scale))
    resized = subject.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    x = (frame_width - resized_width) // 2
    y = frame_height - resized_height
    frame.alpha_composite(resized, (x, y))
    return frame


def _required_path(payload: Payload, key: str) -> Path:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise RuntimeError(f"필수 경로 입력이 없다: {key}")
    return Path(value)


def _required_positive_int(payload: Payload, key: str) -> int:
    value = int(payload.get(key, 0))
    if value <= 0:
        raise RuntimeError(f"필수 양수 입력이 없다: {key}")
    return value
