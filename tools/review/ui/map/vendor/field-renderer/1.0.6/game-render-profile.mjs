// src/game/renderQuality.ts
var GAME_INTERNAL_RESOLUTION_SCALE = 2;
var CHARACTER_OUTLINE_BASE_WIDTH = 1;
var CHARACTER_OUTLINE_BASE_COLOR = 6643028;
var CHARACTER_SEPARATOR_BASE_WIDTH = 1;
var CHARACTER_SEPARATOR_BASE_COLOR = 16773836;
var CHARACTER_CONTACT_SHADOW_COLOR = 2368548;
var CHARACTER_CONTACT_SHADOW_ALPHA_SCALE = 1.2;

// src/game/animation/characterOutline.ts
var CHARACTER_OUTLINE_SAMPLE_OFFSETS = [[-1, 0], [1, 0], [0, -1], [0, 1], [-0.707, -0.707], [0.707, -0.707], [-0.707, 0.707], [0.707, 0.707]];
var CHARACTER_OUTLINE_DEPTH_STEP = 1e-4;
function attachCharacterOutlineLayers(currentActorImage) {
  const currentActorScene = currentActorImage.scene;
  const currentOutlineLayers = [
    { color: CHARACTER_SEPARATOR_BASE_COLOR, radius: CHARACTER_OUTLINE_BASE_WIDTH + CHARACTER_SEPARATOR_BASE_WIDTH, depth: 2 },
    { color: CHARACTER_OUTLINE_BASE_COLOR, radius: CHARACTER_OUTLINE_BASE_WIDTH, depth: 1 }
  ].flatMap((currentLayerStyle) => CHARACTER_OUTLINE_SAMPLE_OFFSETS.map(([currentOffsetHorizontal, currentOffsetVertical]) => ({
    image: currentActorScene.add.image(currentActorImage.x, currentActorImage.y, currentActorImage.texture.key, currentActorImage.frame.name).setTintFill(currentLayerStyle.color).setData("characterOutlineLayer", true),
    horizontal: currentOffsetHorizontal * currentLayerStyle.radius,
    vertical: currentOffsetVertical * currentLayerStyle.radius,
    depth: currentLayerStyle.depth
  })));
  const synchronizeCharacterOutlineLayers = () => {
    for (const currentOutlineLayer of currentOutlineLayers) {
      currentOutlineLayer.image.setTexture(currentActorImage.texture.key, currentActorImage.frame.name).setOrigin(currentActorImage.originX, currentActorImage.originY).setScale(currentActorImage.scaleX, currentActorImage.scaleY).setFlip(currentActorImage.flipX, currentActorImage.flipY).setRotation(currentActorImage.rotation).setPosition(currentActorImage.x + currentOutlineLayer.horizontal, currentActorImage.y + currentOutlineLayer.vertical).setDepth(currentActorImage.depth - currentOutlineLayer.depth * CHARACTER_OUTLINE_DEPTH_STEP).setVisible(currentActorImage.visible).setAlpha(currentActorImage.alpha).setScrollFactor(currentActorImage.scrollFactorX, currentActorImage.scrollFactorY);
    }
  };
  synchronizeCharacterOutlineLayers();
  currentActorScene.events.on("postupdate", synchronizeCharacterOutlineLayers);
  currentActorImage.once("destroy", () => {
    currentActorScene.events.off("postupdate", synchronizeCharacterOutlineLayers);
    for (const currentOutlineLayer of currentOutlineLayers) currentOutlineLayer.image.destroy();
  });
}

// packages/field-surface/field-surface.mjs
var FIELD_RENDER_METRICS = Object.freeze({ tileWidth: 80, tileHeight: 40, elevationHeight: 32, baseThickness: 16 });
var CHARACTER_OUTLINE_STYLE = Object.freeze({ color: 16774084, cssColor: "#fff3c4", width: 5, outerStrength: 4, quality: 0.1 });

// src/game/terrain/renderMetrics.ts
var MAP_TILE_WIDTH = 80;
var MAP_TILE_HEIGHT = 40;
var GAME_TILE_SOURCE_SIZES = Object.freeze([64, 128, 256, 512]);
var TOWN_TILE_WIDTH = 160;
var TOWN_TILE_HEIGHT = 80;
var FIELD_TILE_DIMENSIONS = Object.freeze({ width: MAP_TILE_WIDTH, height: MAP_TILE_HEIGHT });
var TOWN_TILE_DIMENSIONS = Object.freeze({ width: TOWN_TILE_WIDTH, height: TOWN_TILE_HEIGHT });

// src/game/terrain/elevation.ts
var same = (a, b) => a.column === b.column && a.row === b.row;
var inBounds = (p, map) => Number.isInteger(p.column) && Number.isInteger(p.row) && p.column >= 0 && p.row >= 0 && p.column < map.columns && p.row < map.rows;
var heightAt = (p, map) => {
  if (!inBounds(p, map)) return 0;
  if (map.heightSource) return heightAt(map.heightSource.position(p), map.heightSource.surface);
  return map.elevations ? map.elevations[p.row][p.column] : 0;
};
function canStep(start, end, map) {
  if (!inBounds(start, map) || !inBounds(end, map) || Math.abs(start.column - end.column) + Math.abs(start.row - end.row) !== 1) return false;
  return heightAt(start, map) === heightAt(end, map) || !!map.ramps?.some((e) => same(e.start, start) && same(e.end, end) || same(e.start, end) && same(e.end, start));
}

// src/game/terrain/roadTiles.ts
var ROAD_CONNECTIONS = [
  { dc: 0, dr: -1, bit: 1 },
  { dc: 1, dr: 0, bit: 2 },
  { dc: 0, dr: 1, bit: 4 },
  { dc: -1, dr: 0, bit: 8 }
];
function waterConnections(cell, map, water) {
  let mask = 0;
  for (const { dc, dr, bit } of ROAD_CONNECTIONS) {
    const next = { column: cell.column + dc, row: cell.row + dr };
    if (water.has(`${next.column},${next.row}`) && canStep(cell, next, map) && heightAt(cell, map) === heightAt(next, map)) mask |= bit;
  }
  return mask;
}
function roadConnections(cell, map, road) {
  if (!road.has(`${cell.column},${cell.row}`)) throw new Error("\uB3C4\uB85C\uAC00 \uC544\uB2CC \uC140\uC758 \uC5F0\uACB0\uC744 \uC694\uCCAD\uD588\uC2B5\uB2C8\uB2E4.");
  let mask = 0;
  for (const { dc, dr, bit } of ROAD_CONNECTIONS) {
    const next = { column: cell.column + dc, row: cell.row + dr };
    if (road.has(`${next.column},${next.row}`) && canStep(cell, next, map)) mask |= bit;
  }
  return mask;
}
export {
  CHARACTER_CONTACT_SHADOW_ALPHA_SCALE,
  CHARACTER_CONTACT_SHADOW_COLOR,
  CHARACTER_OUTLINE_BASE_COLOR,
  CHARACTER_OUTLINE_BASE_WIDTH,
  CHARACTER_SEPARATOR_BASE_COLOR,
  CHARACTER_SEPARATOR_BASE_WIDTH,
  GAME_INTERNAL_RESOLUTION_SCALE,
  attachCharacterOutlineLayers,
  roadConnections,
  waterConnections
};
