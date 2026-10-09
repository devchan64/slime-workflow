// packages/field-renderer/render-constants.mjs
var GAME_INTERNAL_RESOLUTION_SCALE = 2;
var CHARACTER_OUTLINE_BASE_WIDTH = 1;
var CHARACTER_OUTLINE_BASE_COLOR = 6643028;
var CHARACTER_SEPARATOR_BASE_WIDTH = 1;
var CHARACTER_SEPARATOR_BASE_COLOR = 16773836;
var CHARACTER_CONTACT_SHADOW_COLOR = 2368548;
var CHARACTER_CONTACT_SHADOW_ALPHA_SCALE = 1.2;
var MAP_DEFAULT_ZOOM = 2;
var MAP_TILE_WIDTH = 80;
var MAP_TILE_HEIGHT = 40;
var GAME_TILE_SOURCE_SIZES = Object.freeze([64, 128, 256, 512]);
var CHARACTER_BODY_HEIGHT = 80;
var MAP_ELEVATION_HEIGHT = 32;
var MAP_BASE_THICKNESS = 16;
var WORLD_UNIT_MIGRATION = 1.3;
var TOWN_TILE_WIDTH = 160;
var TOWN_TILE_HEIGHT = 80;
var FIELD_ELEVATION_EDGE_STYLE = Object.freeze({ color: 3158064, width: 4, alpha: 0.85 });
var FIELD_MESH_BOUNDARY_STYLE = Object.freeze({ color: 14476783, width: 1, alpha: 0.9 });
var FIELD_ACTOR_CONTACT_SHADOW_PROFILES = Object.freeze({
  baseline: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.3, coreAlpha: 0.24, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  contrast: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.36, coreAlpha: 0.3, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  broad: Object.freeze({ width: 0.44, height: 0.34, alpha: 0.32, coreAlpha: 0.26, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 })
});
var FIELD_ACTOR_CONTACT_SHADOW_COLOR = 1587502;
var FIELD_SAFE_TOWER_PROFILE = Object.freeze({ anchorX: 627, anchorY: 1095, bodyTop: 82, displayHeight: 112 });
var FIELD_SAFE_AURA_PROFILE = Object.freeze({ columns: 4, rows: 2, frames: 8, height: 15, alpha: 0.7, frameDuration: 120, horizontalCrop: 0.02, topCrop: 0.25, bottomCrop: 0.1 });
var FIELD_CONNECTION_SHAPE = Object.freeze({ inset: 0.08, radius: 0.2, half: 0.5 });
var TERRAIN_STAIR_COUNT = 3;
var CHARACTER_OUTLINE_STYLE = Object.freeze({ color: 16774084, cssColor: "#fff3c4", width: 5, outerStrength: 4, quality: 0.1 });
var MAP_ORIGIN = { x: 1040, y: 80 };
var TERRAIN_DEPTH = { stride: 100, base: 100, surface: 1, overlay: 10, actor: 20, annotation: 1e4 };
var BUILDING_RENDER_BLOCK_HEIGHT = 80;
var CITY_BUILDING_STYLE = {
  wallLight: 13153933,
  wallDark: 9404519,
  outlineColor: 4537653,
  outlineWidth: 2,
  selectedColor: 16768376,
  selectedWidth: 4,
  roofAlpha: 0.9,
  labelFont: "17px",
  labelOffset: 12,
  entranceRadius: 7,
  roofColors: { guild: 4619381, bookshop: 7691396, inn: 10841940, workshop: 6451066, market: 13938019 }
};
var HUMAN_REST_HEIGHT_RATIO = 1;
var SLIME_RATIO = 0.5;
var MAX_MONSTER_RATIO = 2;
var ACTOR_CONTACT_SHADOW_CONTRACT = Object.freeze({ profile: "contrast" });
var SPRITE_DEPTH_OFFSET = 0.01;
var CHARACTER_OUTLINE_DEPTH_STEP = 1e-4;
var FIELD_RENDER_METRICS = Object.freeze({ tileWidth: MAP_TILE_WIDTH, tileHeight: MAP_TILE_HEIGHT, elevationHeight: MAP_ELEVATION_HEIGHT, baseThickness: MAP_BASE_THICKNESS });
var TERRAIN_MATERIAL_BOUNDARY_ENABLED = true;
var BUILDING_BOUNDARY_ENABLED = true;
var BUILDING_ROOF_TEXTURE_ROTATION_RADIANS = -Math.PI / 2;

// src/game/animation/characterOutline.ts
var CHARACTER_OUTLINE_SAMPLE_OFFSETS = [[-1, 0], [1, 0], [0, -1], [0, 1], [-0.707, -0.707], [0.707, -0.707], [-0.707, 0.707], [0.707, 0.707]];
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

// src/game/terrain/renderMetrics.ts
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

// packages/field-renderer/field-renderer.mjs
function resolveFieldActorContactShadow(currentShadowProfileName = "contrast") {
  const currentShadowProfile = FIELD_ACTOR_CONTACT_SHADOW_PROFILES[currentShadowProfileName];
  if (!currentShadowProfile) throw Error("\uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uC811\uC9C0 \uADF8\uB9BC\uC790 \uD504\uB85C\uD544: " + currentShadowProfileName);
  const currentShadowWidth = FIELD_RENDER_METRICS.tileWidth * currentShadowProfile.width * currentShadowProfile.scale;
  const currentShadowHeight = FIELD_RENDER_METRICS.tileHeight * currentShadowProfile.height * currentShadowProfile.scale;
  return { color: FIELD_ACTOR_CONTACT_SHADOW_COLOR, outer: { width: currentShadowWidth, height: currentShadowHeight, alpha: currentShadowProfile.alpha * currentShadowProfile.opacityScale }, core: { width: currentShadowWidth * currentShadowProfile.coreScale, height: currentShadowHeight * currentShadowProfile.coreScale, alpha: currentShadowProfile.coreAlpha * currentShadowProfile.opacityScale } };
}

// src/game/terrain/characterContactShadow.ts
function drawCharacterContactShadow(currentShadowGraphic, currentScreenPosition) {
  const currentShadowMetrics = resolveFieldActorContactShadow("contrast");
  for (const currentShadowLayer of [currentShadowMetrics.outer, currentShadowMetrics.core]) {
    currentShadowGraphic.fillStyle(CHARACTER_CONTACT_SHADOW_COLOR, Math.min(1, currentShadowLayer.alpha * CHARACTER_CONTACT_SHADOW_ALPHA_SCALE));
    currentShadowGraphic.fillEllipse(currentScreenPosition.x, currentScreenPosition.y, currentShadowLayer.width, currentShadowLayer.height);
  }
}
export {
  ACTOR_CONTACT_SHADOW_CONTRACT,
  BUILDING_BOUNDARY_ENABLED,
  BUILDING_RENDER_BLOCK_HEIGHT,
  BUILDING_ROOF_TEXTURE_ROTATION_RADIANS,
  CHARACTER_BODY_HEIGHT,
  CHARACTER_CONTACT_SHADOW_ALPHA_SCALE,
  CHARACTER_CONTACT_SHADOW_COLOR,
  CHARACTER_OUTLINE_BASE_COLOR,
  CHARACTER_OUTLINE_BASE_WIDTH,
  CHARACTER_OUTLINE_DEPTH_STEP,
  CHARACTER_OUTLINE_STYLE,
  CHARACTER_SEPARATOR_BASE_COLOR,
  CHARACTER_SEPARATOR_BASE_WIDTH,
  CITY_BUILDING_STYLE,
  FIELD_ACTOR_CONTACT_SHADOW_COLOR,
  FIELD_ACTOR_CONTACT_SHADOW_PROFILES,
  FIELD_CONNECTION_SHAPE,
  FIELD_ELEVATION_EDGE_STYLE,
  FIELD_MESH_BOUNDARY_STYLE,
  FIELD_RENDER_METRICS,
  FIELD_SAFE_AURA_PROFILE,
  FIELD_SAFE_TOWER_PROFILE,
  GAME_INTERNAL_RESOLUTION_SCALE,
  GAME_TILE_SOURCE_SIZES,
  HUMAN_REST_HEIGHT_RATIO,
  MAP_BASE_THICKNESS,
  MAP_DEFAULT_ZOOM,
  MAP_ELEVATION_HEIGHT,
  MAP_ORIGIN,
  MAP_TILE_HEIGHT,
  MAP_TILE_WIDTH,
  MAX_MONSTER_RATIO,
  SLIME_RATIO,
  SPRITE_DEPTH_OFFSET,
  TERRAIN_DEPTH,
  TERRAIN_MATERIAL_BOUNDARY_ENABLED,
  TERRAIN_STAIR_COUNT,
  TOWN_TILE_HEIGHT,
  TOWN_TILE_WIDTH,
  WORLD_UNIT_MIGRATION,
  attachCharacterOutlineLayers,
  drawCharacterContactShadow,
  roadConnections,
  waterConnections
};
