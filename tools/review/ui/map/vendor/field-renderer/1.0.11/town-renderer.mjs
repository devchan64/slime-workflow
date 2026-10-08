// packages/field-renderer/render-constants.mjs
var MAP_TILE_WIDTH = 80;
var MAP_TILE_HEIGHT = 40;
var GAME_TILE_SOURCE_SIZES = Object.freeze([64, 128, 256, 512]);
var MAP_ELEVATION_HEIGHT = 32;
var MAP_BASE_THICKNESS = 16;
var TOWN_TILE_WIDTH = 160;
var TOWN_TILE_HEIGHT = 80;
var FIELD_ELEVATION_EDGE_STYLE = Object.freeze({ color: 3158064, width: 4, alpha: 0.85 });
var FIELD_MESH_BOUNDARY_STYLE = Object.freeze({ color: 14476783, width: 1, alpha: 0.9 });
var FIELD_ACTOR_CONTACT_SHADOW_PROFILES = Object.freeze({
  baseline: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.3, coreAlpha: 0.24, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  contrast: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.36, coreAlpha: 0.3, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  broad: Object.freeze({ width: 0.44, height: 0.34, alpha: 0.32, coreAlpha: 0.26, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 })
});
var FIELD_SAFE_TOWER_PROFILE = Object.freeze({ anchorX: 627, anchorY: 1095, bodyTop: 82, displayHeight: 112 });
var FIELD_SAFE_AURA_PROFILE = Object.freeze({ columns: 4, rows: 2, frames: 8, height: 15, alpha: 0.7, frameDuration: 120, horizontalCrop: 0.02, topCrop: 0.25, bottomCrop: 0.1 });
var FIELD_CONNECTION_SHAPE = Object.freeze({ inset: 0.08, radius: 0.2, half: 0.5 });
var CHARACTER_OUTLINE_STYLE = Object.freeze({ color: 16774084, cssColor: "#fff3c4", width: 5, outerStrength: 4, quality: 0.1 });
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
var ACTOR_CONTACT_SHADOW_CONTRACT = Object.freeze({ profile: "contrast" });
var FIELD_RENDER_METRICS = Object.freeze({ tileWidth: MAP_TILE_WIDTH, tileHeight: MAP_TILE_HEIGHT, elevationHeight: MAP_ELEVATION_HEIGHT, baseThickness: MAP_BASE_THICKNESS });

// ../slime-assets/assets/tiles/terrain/blocked/ramp-earth-stone-wall-v1.png
var ramp_earth_stone_wall_v1_default = "assets/tiles/terrain/blocked/ramp-earth-stone-wall-v1.png";

// ../slime-assets/assets/tiles/terrain/non-road/grass-ground-v2.png
var grass_ground_v2_default = "assets/tiles/terrain/non-road/grass-ground-v2.png";

// ../slime-assets/assets/tiles/terrain/blocked/dry-ground-tree-stump-v1.png
var dry_ground_tree_stump_v1_default = "assets/tiles/terrain/blocked/dry-ground-tree-stump-v1.png";

// ../slime-assets/assets/tiles/terrain/road/ochre-pebble-road-v1.png
var ochre_pebble_road_v1_default = "assets/tiles/terrain/road/ochre-pebble-road-v1.png";

// ../slime-assets/assets/tiles/terrain/blocked/transparent-deep-water-v2.png
var transparent_deep_water_v2_default = "assets/tiles/terrain/blocked/transparent-deep-water-v2.png";

// ../slime-assets/assets/tiles/terrain/blocked/transparent-shallow-water-v2.png
var transparent_shallow_water_v2_default = "assets/tiles/terrain/blocked/transparent-shallow-water-v2.png";

// ../slime-assets/assets/tiles/terrain/blocked/sand-cactus-type-a-v1.png
var sand_cactus_type_a_v1_default = "assets/tiles/terrain/blocked/sand-cactus-type-a-v1.png";

// ../slime-assets/assets/tiles/terrain/road/limestone-road-v3.png
var limestone_road_v3_default = "assets/tiles/terrain/road/limestone-road-v3.png";

// ../slime-assets/assets/tiles/buildings/wood/wood-roof-v4.png
var wood_roof_v4_default = "assets/tiles/buildings/wood/wood-roof-v4.png";

// ../slime-assets/assets/tiles/buildings/wood/wood-crossbar-wall-v1.png
var wood_crossbar_wall_v1_default = "assets/tiles/buildings/wood/wood-crossbar-wall-v1.png";

// ../slime-assets/assets/tiles/buildings/wood/wood-door-wall-v1.png
var wood_door_wall_v1_default = "assets/tiles/buildings/wood/wood-door-wall-v1.png";

// ../slime-assets/assets/tiles/buildings/wood/wood-window-wall-v1.png
var wood_window_wall_v1_default = "assets/tiles/buildings/wood/wood-window-wall-v1.png";

// ../slime-assets/assets/tiles/buildings/wood/wood-wall-v2.png
var wood_wall_v2_default = "assets/tiles/buildings/wood/wood-wall-v2.png";

// ../slime-assets/assets/tiles/buildings/stone/stone-roof-v1.png
var stone_roof_v1_default = "assets/tiles/buildings/stone/stone-roof-v1.png";

// ../slime-assets/assets/tiles/buildings/red-stone/red-stone-roof-v2.png
var red_stone_roof_v2_default = "assets/tiles/buildings/red-stone/red-stone-roof-v2.png";

// ../slime-assets/assets/tiles/terrain/non-road/leaf-litter-v2.png
var leaf_litter_v2_default = "assets/tiles/terrain/non-road/leaf-litter-v2.png";

// ../slime-assets/assets/tiles/terrain/road/marble-circular-road-v1.png
var marble_circular_road_v1_default = "assets/tiles/terrain/road/marble-circular-road-v1.png";

// ../slime-assets/assets/tiles/terrain/blocked/cliff-rock-face-v1.png
var cliff_rock_face_v1_default = "assets/tiles/terrain/blocked/cliff-rock-face-v1.png";

// src/game/terrain/renderMetrics.ts
var FIELD_TILE_DIMENSIONS = Object.freeze({ width: MAP_TILE_WIDTH, height: MAP_TILE_HEIGHT });
var TOWN_TILE_DIMENSIONS = Object.freeze({ width: TOWN_TILE_WIDTH, height: TOWN_TILE_HEIGHT });
function resolveMapTileSize(currentMapSurface) {
  return currentMapSurface.safeTown ? TOWN_TILE_DIMENSIONS : FIELD_TILE_DIMENSIONS;
}
function validateTerrainSourceDimensions(currentSourceKey, currentSourceWidth, currentSourceHeight) {
  if (currentSourceWidth !== currentSourceHeight || !GAME_TILE_SOURCE_SIZES.includes(currentSourceWidth)) {
    throw new Error(`\uD0C0\uC77C \uC6D0\uBCF8 \uD06C\uAE30 \uC624\uB958: ${currentSourceKey}\uB294 64\xD764px, 128\xD7128px, 256\xD7256px \uB610\uB294 512\xD7512px\uC5EC\uC57C \uD569\uB2C8\uB2E4. \uC2E4\uC81C ${currentSourceWidth}\xD7${currentSourceHeight}px.`);
  }
}

// src/game/terrain/elevation.ts
var same = (a3, b2) => a3.column === b2.column && a3.row === b2.row;
var inBounds = (p2, map2) => Number.isInteger(p2.column) && Number.isInteger(p2.row) && p2.column >= 0 && p2.row >= 0 && p2.column < map2.columns && p2.row < map2.rows;
var heightAt = (p2, map2) => {
  if (!inBounds(p2, map2)) return 0;
  if (map2.heightSource) return heightAt(map2.heightSource.position(p2), map2.heightSource.surface);
  return map2.elevations ? map2.elevations[p2.row][p2.column] : 0;
};
var cellDepth = (p2) => TERRAIN_DEPTH.base + (p2.column + p2.row) * TERRAIN_DEPTH.stride;
var mapAnnotationDepth = (map2) => Math.max(
  TERRAIN_DEPTH.annotation,
  cellDepth({ column: map2.columns - 1, row: map2.rows - 1 }) + TERRAIN_DEPTH.stride
);
function canStep(start, end, map2) {
  if (!inBounds(start, map2) || !inBounds(end, map2) || Math.abs(start.column - end.column) + Math.abs(start.row - end.row) !== 1) return false;
  return heightAt(start, map2) === heightAt(end, map2) || !!map2.ramps?.some((e3) => same(e3.start, start) && same(e3.end, end) || same(e3.start, end) && same(e3.end, start));
}

// src/game/terrain/meadow.ts
var TEXTURE_SIZE = 128;
var TERRAIN_KINDS = ["grass", "dew", "road", "flowers"];
var FIELD_TERRAIN_KINDS = [...TERRAIN_KINDS, "dry-soil-branches", "water", "shallow-water", "deep-water", "cactus", "ash", "boulder", "gravel", "leaf-litter", "moss", "mud", "paving", "reed-bed", "stone", "tree-base", "wall"];

// src/game/terrain/roadTiles.ts
var ROAD_CONNECTIONS = [
  { dc: 0, dr: -1, bit: 1 },
  { dc: 1, dr: 0, bit: 2 },
  { dc: 0, dr: 1, bit: 4 },
  { dc: -1, dr: 0, bit: 8 }
];
var ROAD_TILE_COUNT = 16;
var roadFrame = (mask) => `road-${mask}`;
function waterConnections(cell, map2, water) {
  let mask = 0;
  for (const { dc, dr, bit } of ROAD_CONNECTIONS) {
    const next = { column: cell.column + dc, row: cell.row + dr };
    if (water.has(`${next.column},${next.row}`) && canStep(cell, next, map2) && heightAt(cell, map2) === heightAt(next, map2)) mask |= bit;
  }
  return mask;
}
function roadConnections(cell, map2, road) {
  if (!road.has(`${cell.column},${cell.row}`)) throw new Error("\uB3C4\uB85C\uAC00 \uC544\uB2CC \uC140\uC758 \uC5F0\uACB0\uC744 \uC694\uCCAD\uD588\uC2B5\uB2C8\uB2E4.");
  let mask = 0;
  for (const { dc, dr, bit } of ROAD_CONNECTIONS) {
    const next = { column: cell.column + dc, row: cell.row + dr };
    if (road.has(`${next.column},${next.row}`) && canStep(cell, next, map2)) mask |= bit;
  }
  return mask;
}
var DIRT_ROAD_VARIANT_PERIOD = 3;
var STONE_SLAB_ROAD_MAPS = /* @__PURE__ */ new Set(["broken-quarry", "crystal-cut"]);
function selectFieldRoadFrame(connectionMaskValue, currentCellPosition, currentMapIsTown, currentMapIdentifier = "") {
  if (currentMapIdentifier === "meadow") return "meadow-road";
  if (!currentMapIsTown && STONE_SLAB_ROAD_MAPS.has(currentMapIdentifier)) return `stone-road-${connectionMaskValue}`;
  const roadVariantIndex = ((currentCellPosition.column + currentCellPosition.row) % DIRT_ROAD_VARIANT_PERIOD + DIRT_ROAD_VARIANT_PERIOD) % DIRT_ROAD_VARIANT_PERIOD;
  return !currentMapIsTown && roadVariantIndex === 0 ? `dirt-road-${connectionMaskValue}` : roadFrame(connectionMaskValue);
}

// src/game/terrain/textures.ts
var UNIFIED_WOOD_ROOF_TEXTURE = "wood-roof-v4";
var WOOD_CROSSBAR_WALL_TEXTURE = "wood-crossbar-wall-v1";
var WOOD_DOOR_WALL_TEXTURE = "wood-door-wall-v1";
var WOOD_WINDOW_WALL_TEXTURE = "wood-window-wall-v1";
var UNIFIED_WOOD_WALL_TEXTURE = "unified-wood-wall-v2";
var STONEWARM_ROOF_TEXTURE = "stonewarm-stone-roof";
var STONEWARM_GUILD_ROOF_TEXTURE = "stonewarm-guild-red-stone-roof-v2";
var TERRAIN_ATLAS = "meadow-terrain";
var RAMP_TREAD_TEXTURE = "ramp-tread-surface-v1";
var CLIFF_WALL_TEXTURE = "dew-meadow-cliff-face-v1";
var STONEWARM_PAVING_FRAME = "stonewarm-paving";
var STONEWARM_MARBLE_PAVING_FRAME = "stonewarm-marble-paving";
var ISEULON_GRASS_FRAME = "iseulon-grass-mud-frame";
var REEDHAVEN_DIRT_ROAD_FRAME = "reedhaven-dirt-road";
var SOURCES = { "dry-soil-branches": grass_ground_v2_default, "deep-water": transparent_deep_water_v2_default, "shallow-water": transparent_shallow_water_v2_default, cactus: sand_cactus_type_a_v1_default, grass: grass_ground_v2_default, dew: grass_ground_v2_default, road: limestone_road_v3_default, flowers: grass_ground_v2_default, water: transparent_shallow_water_v2_default, "ash": grass_ground_v2_default, "boulder": grass_ground_v2_default, "gravel": grass_ground_v2_default, "leaf-litter": leaf_litter_v2_default, "moss": grass_ground_v2_default, "mud": grass_ground_v2_default, "paving": limestone_road_v3_default, "reed-bed": grass_ground_v2_default, "stone": grass_ground_v2_default, "tree-base": grass_ground_v2_default, "wall": cliff_rock_face_v1_default };
var SOURCE_KINDS = FIELD_TERRAIN_KINDS;
var SPECIAL_TERRAIN_SOURCES = [
  { frame: "battle-rock-a", source: grass_ground_v2_default },
  { frame: "battle-rock-b", source: grass_ground_v2_default },
  { frame: "battle-rock-c", source: grass_ground_v2_default },
  { frame: "battle-thicket", source: dry_ground_tree_stump_v1_default },
  { frame: "meadow-flowers", source: grass_ground_v2_default },
  { frame: "meadow-road", source: ochre_pebble_road_v1_default },
  { frame: ISEULON_GRASS_FRAME, source: grass_ground_v2_default },
  { frame: REEDHAVEN_DIRT_ROAD_FRAME, source: limestone_road_v3_default },
  { frame: STONEWARM_PAVING_FRAME, source: limestone_road_v3_default },
  { frame: STONEWARM_MARBLE_PAVING_FRAME, source: marble_circular_road_v1_default }
];
var TRANSPARENT_TERRAIN_KINDS = /* @__PURE__ */ new Set(["boulder", "tree-base"]);
var FRAME_W = TEXTURE_SIZE;
var FRAME_H = TEXTURE_SIZE / 2;
var FRAME_PADDING = 2;
var FRAME_STRIDE = FRAME_W + FRAME_PADDING * 2;
var ATLAS_COLUMNS = 8;
var FRAME_COUNT = SOURCE_KINDS.length + SPECIAL_TERRAIN_SOURCES.length + ROAD_TILE_COUNT * 4;
var framePosition = (index) => ({
  x: index % ATLAS_COLUMNS * FRAME_STRIDE + FRAME_PADDING,
  y: Math.floor(index / ATLAS_COLUMNS) * (FRAME_H + FRAME_PADDING * 2) + FRAME_PADDING
});
var ROAD_SHAPE = { inset: TEXTURE_SIZE * 0.08, radius: TEXTURE_SIZE * 0.2, half: TEXTURE_SIZE / 2 };
var FLOWER_BLEND = { center: TEXTURE_SIZE / 2, radius: TEXTURE_SIZE * 0.64, innerStop: 0.8 };
function readValidatedTileSource(currentPhaserScene, currentSourceKey) {
  const currentSourceImage = currentPhaserScene.textures.get(currentSourceKey).getSourceImage();
  validateTerrainSourceDimensions(currentSourceKey, currentSourceImage.width, currentSourceImage.height);
  return currentSourceImage;
}
function clipRoad(ctx, mask) {
  const { inset, radius, half } = ROAD_SHAPE;
  const width = TEXTURE_SIZE - inset * 2;
  ctx.beginPath();
  ctx.roundRect(inset, inset, width, width, radius);
  if (mask & 1) ctx.rect(inset, 0, width, half);
  if (mask & 2) ctx.rect(half, inset, half, width);
  if (mask & 4) ctx.rect(inset, half, width, half);
  if (mask & 8) ctx.rect(0, inset, half, width);
  if ((mask & 3) === 3) ctx.rect(half, 0, half, half);
  if ((mask & 6) === 6) ctx.rect(half, half, half, half);
  if ((mask & 12) === 12) ctx.rect(0, half, half, half);
  if ((mask & 9) === 9) ctx.rect(0, 0, half, half);
  ctx.clip();
}
function preloadTerrain(scene) {
  scene.load.image("terrain-source-dirt-road", limestone_road_v3_default);
  scene.load.image("terrain-source-stone-road", limestone_road_v3_default);
  scene.load.image(UNIFIED_WOOD_WALL_TEXTURE, wood_wall_v2_default);
  scene.load.image(UNIFIED_WOOD_ROOF_TEXTURE, wood_roof_v4_default);
  scene.load.image(WOOD_WINDOW_WALL_TEXTURE, wood_window_wall_v1_default);
  scene.load.image(WOOD_DOOR_WALL_TEXTURE, wood_door_wall_v1_default);
  scene.load.image(WOOD_CROSSBAR_WALL_TEXTURE, wood_crossbar_wall_v1_default);
  scene.load.image(STONEWARM_GUILD_ROOF_TEXTURE, red_stone_roof_v2_default);
  scene.load.image(STONEWARM_ROOF_TEXTURE, stone_roof_v1_default);
  for (const kind of SOURCE_KINDS) scene.load.image(`terrain-source-${kind}`, SOURCES[kind]);
  for (const specialSourceRecord of SPECIAL_TERRAIN_SOURCES) scene.load.image(`terrain-source-${specialSourceRecord.frame}`, specialSourceRecord.source);
  scene.load.image(RAMP_TREAD_TEXTURE, ramp_earth_stone_wall_v1_default);
  scene.load.image(CLIFF_WALL_TEXTURE, cliff_rock_face_v1_default);
}
function resolveGrassFrameForMap(currentMapIdentifier) {
  return currentMapIdentifier === "iseulon" ? ISEULON_GRASS_FRAME : "grass";
}
function resolvePavingFrameForMap(currentMapIdentifier) {
  if (currentMapIdentifier === "stonewarm") return STONEWARM_MARBLE_PAVING_FRAME;
  if (currentMapIdentifier === "saltford") return STONEWARM_PAVING_FRAME;
  if (currentMapIdentifier === "reedhaven" || currentMapIdentifier === "grainstead") return REEDHAVEN_DIRT_ROAD_FRAME;
  return "paving";
}
function createTerrainAtlas(scene) {
  if (scene.textures.exists(TERRAIN_ATLAS)) return;
  const atlas = scene.textures.createCanvas(
    TERRAIN_ATLAS,
    FRAME_STRIDE * ATLAS_COLUMNS,
    (FRAME_H + FRAME_PADDING * 2) * Math.ceil(FRAME_COUNT / ATLAS_COLUMNS)
  );
  if (!atlas) throw new Error("\uCD08\uC6D0 \uD0C0\uC77C \uC544\uD2C0\uB77C\uC2A4\uB97C \uB9CC\uB4E4 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.");
  const ctx = atlas.getContext();
  const grassSource = readValidatedTileSource(scene, "terrain-source-grass");
  readValidatedTileSource(scene, CLIFF_WALL_TEXTURE);
  const flowerPatch = document.createElement("canvas");
  flowerPatch.width = flowerPatch.height = TEXTURE_SIZE;
  const flowerContext = flowerPatch.getContext("2d");
  if (!flowerContext) throw new Error("\uAF43\uBC2D \uACBD\uACC4 \uD569\uC131 \uCE94\uBC84\uC2A4\uB97C \uB9CC\uB4E4 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.");
  flowerContext.drawImage(
    scene.textures.get("terrain-source-flowers").getSourceImage(),
    0,
    0,
    TEXTURE_SIZE,
    TEXTURE_SIZE
  );
  flowerContext.globalCompositeOperation = "destination-in";
  const { center, radius, innerStop } = FLOWER_BLEND;
  const fade = flowerContext.createRadialGradient(center, center, 0, center, center, radius);
  fade.addColorStop(innerStop, "#fff");
  fade.addColorStop(1, "#ffffff00");
  flowerContext.fillStyle = fade;
  flowerContext.fillRect(0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
  SOURCE_KINDS.forEach((kind, index) => {
    const sourceKey = `terrain-source-${kind}`;
    if (!scene.textures.exists(sourceKey)) throw new Error(`\uCD08\uC6D0 \uD0C0\uC77C \uB204\uB77D: ${kind}`);
    const source = readValidatedTileSource(scene, sourceKey);
    const { x: x2, y: y3 } = framePosition(index);
    ctx.save();
    ctx.translate(x2 + FRAME_W / 2, y3);
    ctx.transform(
      FRAME_W / (2 * TEXTURE_SIZE),
      FRAME_H / (2 * TEXTURE_SIZE),
      -FRAME_W / (2 * TEXTURE_SIZE),
      FRAME_H / (2 * TEXTURE_SIZE),
      0,
      0
    );
    if (kind === "flowers") {
      ctx.drawImage(grassSource, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
      ctx.drawImage(flowerPatch, 0, 0);
    } else {
      if (TRANSPARENT_TERRAIN_KINDS.has(kind)) ctx.drawImage(grassSource, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
      ctx.drawImage(source, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
    }
    ctx.restore();
    atlas.add(kind, 0, x2, y3, FRAME_W, FRAME_H);
  });
  SPECIAL_TERRAIN_SOURCES.forEach((specialSourceRecord, specialSourceIndex) => {
    const source = readValidatedTileSource(scene, `terrain-source-${specialSourceRecord.frame}`);
    const { x: x2, y: y3 } = framePosition(SOURCE_KINDS.length + specialSourceIndex);
    ctx.save();
    ctx.translate(x2 + FRAME_W / 2, y3);
    ctx.transform(
      FRAME_W / (2 * TEXTURE_SIZE),
      FRAME_H / (2 * TEXTURE_SIZE),
      -FRAME_W / (2 * TEXTURE_SIZE),
      FRAME_H / (2 * TEXTURE_SIZE),
      0,
      0
    );
    ctx.drawImage(source, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
    ctx.restore();
    atlas.add(specialSourceRecord.frame, 0, x2, y3, FRAME_W, FRAME_H);
  });
  for (const [surfaceIndex, surface] of ["road", "water", "dirt-road", "stone-road"].entries()) {
    const surfaceSource = surface === "dirt-road" || surface === "stone-road" ? scene.textures.get(`terrain-source-${surface}`).getSourceImage() : readValidatedTileSource(scene, `terrain-source-${surface}`);
    for (let mask = 0; mask < ROAD_TILE_COUNT; mask++) {
      const { x: x2, y: y3 } = framePosition(SOURCE_KINDS.length + SPECIAL_TERRAIN_SOURCES.length + surfaceIndex * ROAD_TILE_COUNT + mask);
      ctx.save();
      ctx.translate(x2 + FRAME_W / 2, y3);
      ctx.transform(
        FRAME_W / (2 * TEXTURE_SIZE),
        FRAME_H / (2 * TEXTURE_SIZE),
        -FRAME_W / (2 * TEXTURE_SIZE),
        FRAME_H / (2 * TEXTURE_SIZE),
        0,
        0
      );
      ctx.drawImage(grassSource, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
      clipRoad(ctx, mask);
      ctx.drawImage(surfaceSource, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE);
      ctx.restore();
      atlas.add(surface === "road" ? roadFrame(mask) : `${surface}-${mask}`, 0, x2, y3, FRAME_W, FRAME_H);
    }
  }
  atlas.refresh();
}

// src/game/terrain/blockGeometry.ts
var BLOCK_LAYER_HEIGHT = 60;
var BLOCK_CORNER_OFFSETS = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]];
var BLOCK_NEIGHBOR_OFFSETS = [[0, -1], [1, 0], [0, 1], [-1, 0]];
var BLOCK_HEIGHT_EPSILON = 1e-5;
function resolveBlockSurfaceHeight(currentBlockRecord, currentLocalColumn, currentLocalRow) {
  const currentBaseHeight = currentBlockRecord.layer * BLOCK_LAYER_HEIGHT + currentBlockRecord.offsetHeight;
  if (currentBlockRecord.shape !== "ramp") return currentBaseHeight + currentBlockRecord.height;
  const currentSlopeRatio = { east: currentLocalColumn, west: 1 - currentLocalColumn, south: currentLocalRow, north: 1 - currentLocalRow }[currentBlockRecord.highSide];
  return currentBaseHeight + currentBlockRecord.height * currentSlopeRatio;
}
function clipBlockSurfacePolygon(currentPolygonPoints, evaluatePlaneDistance) {
  const resultingPolygonPoints = [];
  for (let currentVertexIndex = 0; currentVertexIndex < currentPolygonPoints.length; currentVertexIndex++) {
    const previousVertexPoint = currentPolygonPoints[(currentVertexIndex + currentPolygonPoints.length - 1) % currentPolygonPoints.length], currentVertexPoint = currentPolygonPoints[currentVertexIndex];
    const previousPlaneDistance = evaluatePlaneDistance(previousVertexPoint), currentPlaneDistance = evaluatePlaneDistance(currentVertexPoint);
    if (previousPlaneDistance > 0 !== currentPlaneDistance > 0) {
      const intersectionRatioValue = previousPlaneDistance / (previousPlaneDistance - currentPlaneDistance);
      resultingPolygonPoints.push({ column: previousVertexPoint.column + (currentVertexPoint.column - previousVertexPoint.column) * intersectionRatioValue, row: previousVertexPoint.row + (currentVertexPoint.row - previousVertexPoint.row) * intersectionRatioValue, height: previousVertexPoint.height + (currentVertexPoint.height - previousVertexPoint.height) * intersectionRatioValue });
    }
    if (currentPlaneDistance >= 0) resultingPolygonPoints.push(currentVertexPoint);
  }
  return resultingPolygonPoints;
}
function buildBlockSurfaceFaces(currentBlockRecords) {
  const currentCellIndex = /* @__PURE__ */ new Map();
  const currentIdentifierSet = /* @__PURE__ */ new Set();
  for (const currentBlockRecord of currentBlockRecords) {
    if (currentIdentifierSet.has(currentBlockRecord.id) || !["full", "ramp"].includes(currentBlockRecord.shape) || ![currentBlockRecord.column, currentBlockRecord.row, currentBlockRecord.layer, currentBlockRecord.offsetHeight, currentBlockRecord.height].every(Number.isInteger) || currentBlockRecord.height !== BLOCK_LAYER_HEIGHT || currentBlockRecord.offsetHeight !== 0 || currentBlockRecord.shape === "ramp" && !["north", "south", "east", "west"].includes(currentBlockRecord.highSide)) throw new Error("\uC798\uBABB\uB41C \uBE14\uB85D \uB370\uC774\uD130");
    currentIdentifierSet.add(currentBlockRecord.id);
    const currentCellKey = `${currentBlockRecord.column},${currentBlockRecord.row}`;
    currentCellIndex.set(currentCellKey, [...currentCellIndex.get(currentCellKey) ?? [], currentBlockRecord]);
  }
  const resultingSurfaceFaces = [];
  for (const currentBlockRecord of currentBlockRecords) {
    const currentBaseHeight = currentBlockRecord.layer * BLOCK_LAYER_HEIGHT + currentBlockRecord.offsetHeight;
    const currentTopCorners = BLOCK_CORNER_OFFSETS.map(([currentColumnOffset, currentRowOffset]) => ({ column: currentBlockRecord.column + currentColumnOffset, row: currentBlockRecord.row + currentRowOffset, height: resolveBlockSurfaceHeight(currentBlockRecord, currentColumnOffset + 0.5, currentRowOffset + 0.5) }));
    const currentUpperNeighbors = currentCellIndex.get(`${currentBlockRecord.column},${currentBlockRecord.row}`);
    const currentTopCovered = currentUpperNeighbors.some((currentNeighborBlock) => currentNeighborBlock !== currentBlockRecord && currentTopCorners.every((currentCornerPoint) => Math.abs(currentCornerPoint.height - (currentNeighborBlock.layer * BLOCK_LAYER_HEIGHT + currentNeighborBlock.offsetHeight)) < BLOCK_HEIGHT_EPSILON));
    if (!currentTopCovered) resultingSurfaceFaces.push({ vertices: currentTopCorners, material: currentBlockRecord.material, top: true });
    for (let currentEdgeIndex = 0; currentEdgeIndex < 4; currentEdgeIndex++) {
      const currentEdgeStart = currentTopCorners[currentEdgeIndex], currentEdgeEnd = currentTopCorners[(currentEdgeIndex + 1) % 4];
      let currentVisiblePolygons = [[{ ...currentEdgeStart, height: currentBaseHeight }, { ...currentEdgeEnd, height: currentBaseHeight }, currentEdgeEnd, currentEdgeStart]];
      const [neighborColumnOffset, neighborRowOffset] = BLOCK_NEIGHBOR_OFFSETS[currentEdgeIndex];
      for (const currentNeighborBlock of currentCellIndex.get(`${currentBlockRecord.column + neighborColumnOffset},${currentBlockRecord.row + neighborRowOffset}`) ?? []) {
        const neighborBottomHeight = currentNeighborBlock.layer * BLOCK_LAYER_HEIGHT + currentNeighborBlock.offsetHeight;
        currentVisiblePolygons = currentVisiblePolygons.flatMap((currentPolygonPoints) => [
          clipBlockSurfacePolygon(currentPolygonPoints, (currentVertexPoint) => neighborBottomHeight - currentVertexPoint.height),
          clipBlockSurfacePolygon(currentPolygonPoints, (currentVertexPoint) => currentVertexPoint.height - resolveBlockSurfaceHeight(currentNeighborBlock, currentVertexPoint.column - currentNeighborBlock.column + 0.5, currentVertexPoint.row - currentNeighborBlock.row + 0.5))
        ]).filter((currentPolygonPoints) => currentPolygonPoints.length >= 3);
      }
      for (const currentPolygonPoints of currentVisiblePolygons) {
        const currentHeightRange = Math.max(...currentPolygonPoints.map((currentVertexPoint) => currentVertexPoint.height)) - Math.min(...currentPolygonPoints.map((currentVertexPoint) => currentVertexPoint.height));
        const currentSurfaceArea = Math.abs(currentPolygonPoints.reduce((currentAreaValue, currentVertexPoint, currentVertexIndex) => {
          const nextVertexPoint = currentPolygonPoints[(currentVertexIndex + 1) % currentPolygonPoints.length];
          const currentHorizontalValue = neighborColumnOffset === 0 ? currentVertexPoint.column : currentVertexPoint.row;
          const nextHorizontalValue = neighborColumnOffset === 0 ? nextVertexPoint.column : nextVertexPoint.row;
          return currentAreaValue + currentHorizontalValue * nextVertexPoint.height - nextHorizontalValue * currentVertexPoint.height;
        }, 0));
        if (currentHeightRange > BLOCK_HEIGHT_EPSILON && currentSurfaceArea > BLOCK_HEIGHT_EPSILON) resultingSurfaceFaces.push({ vertices: currentPolygonPoints, material: currentBlockRecord.material, top: false });
      }
    }
  }
  return resultingSurfaceFaces;
}
function buildRenderedBlockFaces(currentBlockRecords) {
  return buildBlockSurfaceFaces(currentBlockRecords).map((currentSurfaceFace) => ({ ...currentSurfaceFace, vertices: currentSurfaceFace.vertices.map((currentVertexPoint) => ({ ...currentVertexPoint, height: currentVertexPoint.height * BUILDING_RENDER_BLOCK_HEIGHT / BLOCK_LAYER_HEIGHT })) }));
}

// shared-phaser:shared-phaser
import * as Phaser from "./phaser.mjs";
var shared_phaser_default = Phaser;

// node_modules/preact/dist/preact.module.js
var n;
var l;
var u;
var t;
var i;
var r;
var o;
var e;
var f;
var c;
var s;
var a;
var h;
var p;
var v;
var y;
var d = {};
var w = [];
var _ = /acit|ex(?:s|g|n|p|$)|rph|grid|ows|mnc|ntw|ine[ch]|zoo|^ord|itera/i;
var g = Array.isArray;
function m(n2, l3) {
  for (var u3 in l3) n2[u3] = l3[u3];
  return n2;
}
function b(n2) {
  n2 && n2.parentNode && n2.parentNode.removeChild(n2);
}
function x(n2, t4, i3, r3, o2) {
  var e3 = { type: n2, props: t4, key: i3, ref: r3, __k: null, __: null, __b: 0, __e: null, __c: null, constructor: void 0, __v: null == o2 ? ++u : o2, __i: -1, __u: 0 };
  return null == o2 && null != l.vnode && l.vnode(e3), e3;
}
function S(n2) {
  return n2.children;
}
function C(n2, l3) {
  this.props = n2, this.context = l3;
}
function $(n2, l3) {
  if (null == l3) return n2.__ ? $(n2.__, n2.__i + 1) : null;
  for (var u3; l3 < n2.__k.length; l3++) if (null != (u3 = n2.__k[l3]) && null != u3.__e) return u3.__e;
  return "function" == typeof n2.type ? $(n2) : null;
}
function I(n2) {
  if (n2.__P && n2.__d) {
    var u3 = n2.__v, t4 = u3.__e, i3 = [], r3 = [], o2 = m({}, u3);
    o2.__v = u3.__v + 1, l.vnode && l.vnode(o2), q(n2.__P, o2, u3, n2.__n, n2.__P.namespaceURI, 32 & u3.__u ? [t4] : null, i3, null == t4 ? $(u3) : t4, !!(32 & u3.__u), r3), o2.__v = u3.__v, o2.__.__k[o2.__i] = o2, D(i3, o2, r3), u3.__e = u3.__ = null, o2.__e != t4 && P(o2);
  }
}
function P(n2) {
  if (null != (n2 = n2.__) && null != n2.__c) return n2.__e = n2.__c.base = null, n2.__k.some(function(l3) {
    if (null != l3 && null != l3.__e) return n2.__e = n2.__c.base = l3.__e;
  }), P(n2);
}
function A(n2) {
  (!n2.__d && (n2.__d = true) && i.push(n2) && !H.__r++ || r != l.debounceRendering) && ((r = l.debounceRendering) || o)(H);
}
function H() {
  try {
    for (var n2, l3 = 1; i.length; ) i.length > l3 && i.sort(e), n2 = i.shift(), l3 = i.length, I(n2);
  } finally {
    i.length = H.__r = 0;
  }
}
function L(n2, l3, u3, t4, i3, r3, o2, e3, f3, c3, s3) {
  var a3, h2, p2, v3, y3, _2, g2, m3 = t4 && t4.__k || w, b2 = l3.length;
  for (f3 = T(u3, l3, m3, f3, b2), a3 = 0; a3 < b2; a3++) null != (p2 = u3.__k[a3]) && (h2 = -1 != p2.__i && m3[p2.__i] || d, p2.__i = a3, _2 = q(n2, p2, h2, i3, r3, o2, e3, f3, c3, s3), v3 = p2.__e, p2.ref && h2.ref != p2.ref && (h2.ref && J(h2.ref, null, p2), s3.push(p2.ref, p2.__c || v3, p2)), null == y3 && null != v3 && (y3 = v3), (g2 = !!(4 & p2.__u)) || h2.__k === p2.__k ? (f3 = j(p2, f3, n2, g2), g2 && h2.__e && (h2.__e = null)) : "function" == typeof p2.type && void 0 !== _2 ? f3 = _2 : v3 && (f3 = v3.nextSibling), p2.__u &= -7);
  return u3.__e = y3, f3;
}
function T(n2, l3, u3, t4, i3) {
  var r3, o2, e3, f3, c3, s3 = u3.length, a3 = s3, h2 = 0;
  for (n2.__k = new Array(i3), r3 = 0; r3 < i3; r3++) null != (o2 = l3[r3]) && "boolean" != typeof o2 && "function" != typeof o2 ? ("string" == typeof o2 || "number" == typeof o2 || "bigint" == typeof o2 || o2.constructor == String ? o2 = n2.__k[r3] = x(null, o2, null, null, null) : g(o2) ? o2 = n2.__k[r3] = x(S, { children: o2 }, null, null, null) : void 0 === o2.constructor && o2.__b > 0 ? o2 = n2.__k[r3] = x(o2.type, o2.props, o2.key, o2.ref ? o2.ref : null, o2.__v) : n2.__k[r3] = o2, f3 = r3 + h2, o2.__ = n2, o2.__b = n2.__b + 1, e3 = null, -1 != (c3 = o2.__i = O(o2, u3, f3, a3)) && (a3--, (e3 = u3[c3]) && (e3.__u |= 2)), null == e3 || null == e3.__v ? (-1 == c3 && (i3 > s3 ? h2-- : i3 < s3 && h2++), "function" != typeof o2.type && (o2.__u |= 4)) : c3 != f3 && (c3 == f3 - 1 ? h2-- : c3 == f3 + 1 ? h2++ : (c3 > f3 ? h2-- : h2++, o2.__u |= 4))) : n2.__k[r3] = null;
  if (a3) for (r3 = 0; r3 < s3; r3++) null != (e3 = u3[r3]) && 0 == (2 & e3.__u) && (e3.__e == t4 && (t4 = $(e3)), K(e3, e3));
  return t4;
}
function j(n2, l3, u3, t4) {
  var i3, r3;
  if ("function" == typeof n2.type) {
    for (i3 = n2.__k, r3 = 0; i3 && r3 < i3.length; r3++) i3[r3] && (i3[r3].__ = n2, l3 = j(i3[r3], l3, u3, t4));
    return l3;
  }
  n2.__e != l3 && (t4 && (l3 && n2.type && !l3.parentNode && (l3 = $(n2)), u3.insertBefore(n2.__e, l3 || null)), l3 = n2.__e);
  do {
    l3 = l3 && l3.nextSibling;
  } while (null != l3 && 8 == l3.nodeType);
  return l3;
}
function O(n2, l3, u3, t4) {
  var i3, r3, o2, e3 = n2.key, f3 = n2.type, c3 = l3[u3], s3 = null != c3 && 0 == (2 & c3.__u);
  if (null === c3 && null == e3 || s3 && e3 == c3.key && f3 == c3.type) return u3;
  if (t4 > (s3 ? 1 : 0)) {
    for (i3 = u3 - 1, r3 = u3 + 1; i3 >= 0 || r3 < l3.length; ) if (null != (c3 = l3[o2 = i3 >= 0 ? i3-- : r3++]) && 0 == (2 & c3.__u) && e3 == c3.key && f3 == c3.type) return o2;
  }
  return -1;
}
function z(n2, l3, u3) {
  "-" == l3[0] ? n2.setProperty(l3, null == u3 ? "" : u3) : n2[l3] = null == u3 ? "" : "number" != typeof u3 || _.test(l3) ? u3 : u3 + "px";
}
function N(n2, l3, u3, t4, i3) {
  var r3, o2;
  n: if ("style" == l3) if ("string" == typeof u3) n2.style.cssText = u3;
  else {
    if ("string" == typeof t4 && (n2.style.cssText = t4 = ""), t4) for (l3 in t4) u3 && l3 in u3 || z(n2.style, l3, "");
    if (u3) for (l3 in u3) t4 && u3[l3] == t4[l3] || z(n2.style, l3, u3[l3]);
  }
  else if ("o" == l3[0] && "n" == l3[1]) r3 = l3 != (l3 = l3.replace(a, "$1")), o2 = l3.toLowerCase(), l3 = o2 in n2 || "onFocusOut" == l3 || "onFocusIn" == l3 ? o2.slice(2) : l3.slice(2), n2.l || (n2.l = {}), n2.l[l3 + r3] = u3, u3 ? t4 ? u3[s] = t4[s] : (u3[s] = h, n2.addEventListener(l3, r3 ? v : p, r3)) : n2.removeEventListener(l3, r3 ? v : p, r3);
  else {
    if ("http://www.w3.org/2000/svg" == i3) l3 = l3.replace(/xlink(H|:h)/, "h").replace(/sName$/, "s");
    else if ("width" != l3 && "height" != l3 && "href" != l3 && "list" != l3 && "form" != l3 && "tabIndex" != l3 && "download" != l3 && "rowSpan" != l3 && "colSpan" != l3 && "role" != l3 && "popover" != l3 && l3 in n2) try {
      n2[l3] = null == u3 ? "" : u3;
      break n;
    } catch (n3) {
    }
    "function" == typeof u3 || (null == u3 || false === u3 && "-" != l3[4] ? n2.removeAttribute(l3) : n2.setAttribute(l3, "popover" == l3 && 1 == u3 ? "" : u3));
  }
}
function V(n2) {
  return function(u3) {
    if (this.l) {
      var t4 = this.l[u3.type + n2];
      if (null == u3[c]) u3[c] = h++;
      else if (u3[c] < t4[s]) return;
      return t4(l.event ? l.event(u3) : u3);
    }
  };
}
function q(n2, u3, t4, i3, r3, o2, e3, f3, c3, s3) {
  var a3, h2, p2, v3, y3, d3, _2, k2, x2, M, $2, I2, P2, A2, H2, T2 = u3.type;
  if (void 0 !== u3.constructor) return null;
  128 & t4.__u && (c3 = !!(32 & t4.__u), o2 = [f3 = u3.__e = t4.__e]), (a3 = l.__b) && a3(u3);
  n: if ("function" == typeof T2) try {
    if (k2 = u3.props, x2 = T2.prototype && T2.prototype.render, M = (a3 = T2.contextType) && i3[a3.__c], $2 = a3 ? M ? M.props.value : a3.__ : i3, t4.__c ? _2 = (h2 = u3.__c = t4.__c).__ = h2.__E : (x2 ? u3.__c = h2 = new T2(k2, $2) : (u3.__c = h2 = new C(k2, $2), h2.constructor = T2, h2.render = Q), M && M.sub(h2), h2.state || (h2.state = {}), h2.__n = i3, p2 = h2.__d = true, h2.__h = [], h2._sb = []), x2 && null == h2.__s && (h2.__s = h2.state), x2 && null != T2.getDerivedStateFromProps && (h2.__s == h2.state && (h2.__s = m({}, h2.__s)), m(h2.__s, T2.getDerivedStateFromProps(k2, h2.__s))), v3 = h2.props, y3 = h2.state, h2.__v = u3, p2) x2 && null == T2.getDerivedStateFromProps && null != h2.componentWillMount && h2.componentWillMount(), x2 && null != h2.componentDidMount && h2.__h.push(h2.componentDidMount);
    else {
      if (x2 && null == T2.getDerivedStateFromProps && k2 !== v3 && null != h2.componentWillReceiveProps && h2.componentWillReceiveProps(k2, $2), u3.__v == t4.__v || !h2.__e && null != h2.shouldComponentUpdate && false === h2.shouldComponentUpdate(k2, h2.__s, $2)) {
        u3.__v != t4.__v && (h2.props = k2, h2.state = h2.__s, h2.__d = false), u3.__e = t4.__e, u3.__k = t4.__k, u3.__k.some(function(n3) {
          n3 && (n3.__ = u3);
        }), w.push.apply(h2.__h, h2._sb), h2._sb = [], h2.__h.length && e3.push(h2);
        break n;
      }
      null != h2.componentWillUpdate && h2.componentWillUpdate(k2, h2.__s, $2), x2 && null != h2.componentDidUpdate && h2.__h.push(function() {
        h2.componentDidUpdate(v3, y3, d3);
      });
    }
    if (h2.context = $2, h2.props = k2, h2.__P = n2, h2.__e = false, I2 = l.__r, P2 = 0, x2) h2.state = h2.__s, h2.__d = false, I2 && I2(u3), a3 = h2.render(h2.props, h2.state, h2.context), w.push.apply(h2.__h, h2._sb), h2._sb = [];
    else do {
      h2.__d = false, I2 && I2(u3), a3 = h2.render(h2.props, h2.state, h2.context), h2.state = h2.__s;
    } while (h2.__d && ++P2 < 25);
    h2.state = h2.__s, null != h2.getChildContext && (i3 = m(m({}, i3), h2.getChildContext())), x2 && !p2 && null != h2.getSnapshotBeforeUpdate && (d3 = h2.getSnapshotBeforeUpdate(v3, y3)), A2 = null != a3 && a3.type === S && null == a3.key ? E(a3.props.children) : a3, f3 = L(n2, g(A2) ? A2 : [A2], u3, t4, i3, r3, o2, e3, f3, c3, s3), h2.base = u3.__e, u3.__u &= -161, h2.__h.length && e3.push(h2), _2 && (h2.__E = h2.__ = null);
  } catch (n3) {
    if (u3.__v = null, c3 || null != o2) if (n3.then) {
      for (u3.__u |= c3 ? 160 : 128; f3 && 8 == f3.nodeType && f3.nextSibling; ) f3 = f3.nextSibling;
      o2[o2.indexOf(f3)] = null, u3.__e = f3;
    } else {
      for (H2 = o2.length; H2--; ) b(o2[H2]);
      B(u3);
    }
    else u3.__e = t4.__e, u3.__k = t4.__k, n3.then || B(u3);
    l.__e(n3, u3, t4);
  }
  else null == o2 && u3.__v == t4.__v ? (u3.__k = t4.__k, u3.__e = t4.__e) : f3 = u3.__e = G(t4.__e, u3, t4, i3, r3, o2, e3, c3, s3);
  return (a3 = l.diffed) && a3(u3), 128 & u3.__u ? void 0 : f3;
}
function B(n2) {
  n2 && (n2.__c && (n2.__c.__e = true), n2.__k && n2.__k.some(B));
}
function D(n2, u3, t4) {
  for (var i3 = 0; i3 < t4.length; i3++) J(t4[i3], t4[++i3], t4[++i3]);
  l.__c && l.__c(u3, n2), n2.some(function(u4) {
    try {
      n2 = u4.__h, u4.__h = [], n2.some(function(n3) {
        n3.call(u4);
      });
    } catch (n3) {
      l.__e(n3, u4.__v);
    }
  });
}
function E(n2) {
  return "object" != typeof n2 || null == n2 || n2.__b > 0 ? n2 : g(n2) ? n2.map(E) : m({}, n2);
}
function G(u3, t4, i3, r3, o2, e3, f3, c3, s3) {
  var a3, h2, p2, v3, y3, w3, _2, m3 = i3.props || d, k2 = t4.props, x2 = t4.type;
  if ("svg" == x2 ? o2 = "http://www.w3.org/2000/svg" : "math" == x2 ? o2 = "http://www.w3.org/1998/Math/MathML" : o2 || (o2 = "http://www.w3.org/1999/xhtml"), null != e3) {
    for (a3 = 0; a3 < e3.length; a3++) if ((y3 = e3[a3]) && "setAttribute" in y3 == !!x2 && (x2 ? y3.localName == x2 : 3 == y3.nodeType)) {
      u3 = y3, e3[a3] = null;
      break;
    }
  }
  if (null == u3) {
    if (null == x2) return document.createTextNode(k2);
    u3 = document.createElementNS(o2, x2, k2.is && k2), c3 && (l.__m && l.__m(t4, e3), c3 = false), e3 = null;
  }
  if (null == x2) m3 === k2 || c3 && u3.data == k2 || (u3.data = k2);
  else {
    if (e3 = e3 && n.call(u3.childNodes), !c3 && null != e3) for (m3 = {}, a3 = 0; a3 < u3.attributes.length; a3++) m3[(y3 = u3.attributes[a3]).name] = y3.value;
    for (a3 in m3) y3 = m3[a3], "dangerouslySetInnerHTML" == a3 ? p2 = y3 : "children" == a3 || a3 in k2 || "value" == a3 && "defaultValue" in k2 || "checked" == a3 && "defaultChecked" in k2 || N(u3, a3, null, y3, o2);
    for (a3 in k2) y3 = k2[a3], "children" == a3 ? v3 = y3 : "dangerouslySetInnerHTML" == a3 ? h2 = y3 : "value" == a3 ? w3 = y3 : "checked" == a3 ? _2 = y3 : c3 && "function" != typeof y3 || m3[a3] === y3 || N(u3, a3, y3, m3[a3], o2);
    if (h2) c3 || p2 && (h2.__html == p2.__html || h2.__html == u3.innerHTML) || (u3.innerHTML = h2.__html), t4.__k = [];
    else if (p2 && (u3.innerHTML = ""), L("template" == t4.type ? u3.content : u3, g(v3) ? v3 : [v3], t4, i3, r3, "foreignObject" == x2 ? "http://www.w3.org/1999/xhtml" : o2, e3, f3, e3 ? e3[0] : i3.__k && $(i3, 0), c3, s3), null != e3) for (a3 = e3.length; a3--; ) b(e3[a3]);
    c3 || (a3 = "value", "progress" == x2 && null == w3 ? u3.removeAttribute("value") : null != w3 && (w3 !== u3[a3] || "progress" == x2 && !w3 || "option" == x2 && w3 != m3[a3]) && N(u3, a3, w3, m3[a3], o2), a3 = "checked", null != _2 && _2 != u3[a3] && N(u3, a3, _2, m3[a3], o2));
  }
  return u3;
}
function J(n2, u3, t4) {
  try {
    if ("function" == typeof n2) {
      var i3 = "function" == typeof n2.__u;
      i3 && n2.__u(), i3 && null == u3 || (n2.__u = n2(u3));
    } else n2.current = u3;
  } catch (n3) {
    l.__e(n3, t4);
  }
}
function K(n2, u3, t4) {
  var i3, r3;
  if (l.unmount && l.unmount(n2), (i3 = n2.ref) && (i3.current && i3.current != n2.__e || J(i3, null, u3)), null != (i3 = n2.__c)) {
    if (i3.componentWillUnmount) try {
      i3.componentWillUnmount();
    } catch (n3) {
      l.__e(n3, u3);
    }
    i3.base = i3.__P = null;
  }
  if (i3 = n2.__k) for (r3 = 0; r3 < i3.length; r3++) i3[r3] && K(i3[r3], u3, t4 || "function" != typeof n2.type);
  t4 || b(n2.__e), n2.__c = n2.__ = n2.__e = void 0;
}
function Q(n2, l3, u3) {
  return this.constructor(n2, u3);
}
n = w.slice, l = { __e: function(n2, l3, u3, t4) {
  for (var i3, r3, o2; l3 = l3.__; ) if ((i3 = l3.__c) && !i3.__) try {
    if ((r3 = i3.constructor) && null != r3.getDerivedStateFromError && (i3.setState(r3.getDerivedStateFromError(n2)), o2 = i3.__d), null != i3.componentDidCatch && (i3.componentDidCatch(n2, t4 || {}), o2 = i3.__d), o2) return i3.__E = i3;
  } catch (l4) {
    n2 = l4;
  }
  throw n2;
} }, u = 0, t = function(n2) {
  return null != n2 && void 0 === n2.constructor;
}, C.prototype.setState = function(n2, l3) {
  var u3;
  u3 = null != this.__s && this.__s != this.state ? this.__s : this.__s = m({}, this.state), "function" == typeof n2 && (n2 = n2(m({}, u3), this.props)), n2 && m(u3, n2), null != n2 && this.__v && (l3 && this._sb.push(l3), A(this));
}, C.prototype.forceUpdate = function(n2) {
  this.__v && (this.__e = true, n2 && this.__h.push(n2), A(this));
}, C.prototype.render = S, i = [], o = "function" == typeof Promise ? Promise.prototype.then.bind(Promise.resolve()) : setTimeout, e = function(n2, l3) {
  return n2.__v.__b - l3.__v.__b;
}, H.__r = 0, f = Math.random().toString(8), c = "__d" + f, s = "__a" + f, a = /(PointerCapture)$|Capture$/i, h = 0, p = V(false), v = V(true), y = 0;

// node_modules/preact/hooks/dist/hooks.module.js
var t2;
var r2;
var u2;
var i2;
var f2 = [];
var c2 = l;
var e2 = c2.__b;
var a2 = c2.__r;
var v2 = c2.diffed;
var l2 = c2.__c;
var m2 = c2.unmount;
var s2 = c2.__;
function j2() {
  for (var n2; n2 = f2.shift(); ) {
    var t4 = n2.__H;
    if (n2.__P && t4) try {
      t4.__h.some(z2), t4.__h.some(B2), t4.__h = [];
    } catch (r3) {
      t4.__h = [], c2.__e(r3, n2.__v);
    }
  }
}
c2.__b = function(n2) {
  r2 = null, e2 && e2(n2);
}, c2.__ = function(n2, t4) {
  n2 && t4.__k && t4.__k.__m && (n2.__m = t4.__k.__m), s2 && s2(n2, t4);
}, c2.__r = function(n2) {
  a2 && a2(n2), t2 = 0;
  var i3 = (r2 = n2.__c).__H;
  i3 && (u2 === r2 ? (i3.__h = [], r2.__h = [], i3.__.some(function(n3) {
    n3.__N && (n3.__ = n3.__N), n3.u = n3.__N = void 0;
  })) : (i3.__h.some(z2), i3.__h.some(B2), i3.__h = [], t2 = 0)), u2 = r2;
}, c2.diffed = function(n2) {
  v2 && v2(n2);
  var t4 = n2.__c;
  t4 && t4.__H && (t4.__H.__h.length && (1 !== f2.push(t4) && i2 === c2.requestAnimationFrame || ((i2 = c2.requestAnimationFrame) || w2)(j2)), t4.__H.__.some(function(n3) {
    n3.u && (n3.__H = n3.u), n3.u = void 0;
  })), u2 = r2 = null;
}, c2.__c = function(n2, t4) {
  t4.some(function(n3) {
    try {
      n3.__h.some(z2), n3.__h = n3.__h.filter(function(n4) {
        return !n4.__ || B2(n4);
      });
    } catch (r3) {
      t4.some(function(n4) {
        n4.__h && (n4.__h = []);
      }), t4 = [], c2.__e(r3, n3.__v);
    }
  }), l2 && l2(n2, t4);
}, c2.unmount = function(n2) {
  m2 && m2(n2);
  var t4, r3 = n2.__c;
  r3 && r3.__H && (r3.__H.__.some(function(n3) {
    try {
      z2(n3);
    } catch (n4) {
      t4 = n4;
    }
  }), r3.__H = void 0, t4 && c2.__e(t4, r3.__v));
};
var k = "function" == typeof requestAnimationFrame;
function w2(n2) {
  var t4, r3 = function() {
    clearTimeout(u3), k && cancelAnimationFrame(t4), setTimeout(n2);
  }, u3 = setTimeout(r3, 35);
  k && (t4 = requestAnimationFrame(r3));
}
function z2(n2) {
  var t4 = r2, u3 = n2.__c;
  "function" == typeof u3 && (n2.__c = void 0, u3()), r2 = t4;
}
function B2(n2) {
  var t4 = r2;
  n2.__c = n2.__(), r2 = t4;
}

// node_modules/yaml/browser/dist/nodes/identity.js
var ALIAS = Symbol.for("yaml.alias");
var DOC = Symbol.for("yaml.document");
var MAP = Symbol.for("yaml.map");
var PAIR = Symbol.for("yaml.pair");
var SCALAR = Symbol.for("yaml.scalar");
var SEQ = Symbol.for("yaml.seq");
var NODE_TYPE = Symbol.for("yaml.node.type");
var isAlias = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === ALIAS;
var isDocument = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === DOC;
var isMap = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === MAP;
var isPair = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === PAIR;
var isScalar = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SCALAR;
var isSeq = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SEQ;
function isCollection(node) {
  if (node && typeof node === "object")
    switch (node[NODE_TYPE]) {
      case MAP:
      case SEQ:
        return true;
    }
  return false;
}
function isNode(node) {
  if (node && typeof node === "object")
    switch (node[NODE_TYPE]) {
      case ALIAS:
      case MAP:
      case SCALAR:
      case SEQ:
        return true;
    }
  return false;
}
var hasAnchor = (node) => (isScalar(node) || isCollection(node)) && !!node.anchor;

// node_modules/yaml/browser/dist/visit.js
var BREAK = Symbol("break visit");
var SKIP = Symbol("skip children");
var REMOVE = Symbol("remove node");
function visit(node, visitor) {
  const visitor_ = initVisitor(visitor);
  if (isDocument(node)) {
    const cd = visit_(null, node.contents, visitor_, Object.freeze([node]));
    if (cd === REMOVE)
      node.contents = null;
  } else
    visit_(null, node, visitor_, Object.freeze([]));
}
visit.BREAK = BREAK;
visit.SKIP = SKIP;
visit.REMOVE = REMOVE;
function visit_(key, node, visitor, path) {
  const ctrl = callVisitor(key, node, visitor, path);
  if (isNode(ctrl) || isPair(ctrl)) {
    replaceNode(key, path, ctrl);
    return visit_(key, ctrl, visitor, path);
  }
  if (typeof ctrl !== "symbol") {
    if (isCollection(node)) {
      path = Object.freeze(path.concat(node));
      for (let i3 = 0; i3 < node.items.length; ++i3) {
        const ci = visit_(i3, node.items[i3], visitor, path);
        if (typeof ci === "number")
          i3 = ci - 1;
        else if (ci === BREAK)
          return BREAK;
        else if (ci === REMOVE) {
          node.items.splice(i3, 1);
          i3 -= 1;
        }
      }
    } else if (isPair(node)) {
      path = Object.freeze(path.concat(node));
      const ck = visit_("key", node.key, visitor, path);
      if (ck === BREAK)
        return BREAK;
      else if (ck === REMOVE)
        node.key = null;
      const cv = visit_("value", node.value, visitor, path);
      if (cv === BREAK)
        return BREAK;
      else if (cv === REMOVE)
        node.value = null;
    }
  }
  return ctrl;
}
async function visitAsync(node, visitor) {
  const visitor_ = initVisitor(visitor);
  if (isDocument(node)) {
    const cd = await visitAsync_(null, node.contents, visitor_, Object.freeze([node]));
    if (cd === REMOVE)
      node.contents = null;
  } else
    await visitAsync_(null, node, visitor_, Object.freeze([]));
}
visitAsync.BREAK = BREAK;
visitAsync.SKIP = SKIP;
visitAsync.REMOVE = REMOVE;
async function visitAsync_(key, node, visitor, path) {
  const ctrl = await callVisitor(key, node, visitor, path);
  if (isNode(ctrl) || isPair(ctrl)) {
    replaceNode(key, path, ctrl);
    return visitAsync_(key, ctrl, visitor, path);
  }
  if (typeof ctrl !== "symbol") {
    if (isCollection(node)) {
      path = Object.freeze(path.concat(node));
      for (let i3 = 0; i3 < node.items.length; ++i3) {
        const ci = await visitAsync_(i3, node.items[i3], visitor, path);
        if (typeof ci === "number")
          i3 = ci - 1;
        else if (ci === BREAK)
          return BREAK;
        else if (ci === REMOVE) {
          node.items.splice(i3, 1);
          i3 -= 1;
        }
      }
    } else if (isPair(node)) {
      path = Object.freeze(path.concat(node));
      const ck = await visitAsync_("key", node.key, visitor, path);
      if (ck === BREAK)
        return BREAK;
      else if (ck === REMOVE)
        node.key = null;
      const cv = await visitAsync_("value", node.value, visitor, path);
      if (cv === BREAK)
        return BREAK;
      else if (cv === REMOVE)
        node.value = null;
    }
  }
  return ctrl;
}
function initVisitor(visitor) {
  if (typeof visitor === "object" && (visitor.Collection || visitor.Node || visitor.Value)) {
    return Object.assign({
      Alias: visitor.Node,
      Map: visitor.Node,
      Scalar: visitor.Node,
      Seq: visitor.Node
    }, visitor.Value && {
      Map: visitor.Value,
      Scalar: visitor.Value,
      Seq: visitor.Value
    }, visitor.Collection && {
      Map: visitor.Collection,
      Seq: visitor.Collection
    }, visitor);
  }
  return visitor;
}
function callVisitor(key, node, visitor, path) {
  if (typeof visitor === "function")
    return visitor(key, node, path);
  if (isMap(node))
    return visitor.Map?.(key, node, path);
  if (isSeq(node))
    return visitor.Seq?.(key, node, path);
  if (isPair(node))
    return visitor.Pair?.(key, node, path);
  if (isScalar(node))
    return visitor.Scalar?.(key, node, path);
  if (isAlias(node))
    return visitor.Alias?.(key, node, path);
  return void 0;
}
function replaceNode(key, path, node) {
  const parent = path[path.length - 1];
  if (isCollection(parent)) {
    parent.items[key] = node;
  } else if (isPair(parent)) {
    if (key === "key")
      parent.key = node;
    else
      parent.value = node;
  } else if (isDocument(parent)) {
    parent.contents = node;
  } else {
    const pt = isAlias(parent) ? "alias" : "scalar";
    throw new Error(`Cannot replace node with ${pt} parent`);
  }
}

// node_modules/yaml/browser/dist/doc/directives.js
var escapeChars = {
  "!": "%21",
  ",": "%2C",
  "[": "%5B",
  "]": "%5D",
  "{": "%7B",
  "}": "%7D"
};
var escapeTagName = (tn) => tn.replace(/[!,[\]{}]/g, (ch) => escapeChars[ch]);
var Directives = class _Directives {
  constructor(yaml, tags) {
    this.docStart = null;
    this.docEnd = false;
    this.yaml = Object.assign({}, _Directives.defaultYaml, yaml);
    this.tags = Object.assign({}, _Directives.defaultTags, tags);
  }
  clone() {
    const copy = new _Directives(this.yaml, this.tags);
    copy.docStart = this.docStart;
    return copy;
  }
  /**
   * During parsing, get a Directives instance for the current document and
   * update the stream state according to the current version's spec.
   */
  atDocument() {
    const res = new _Directives(this.yaml, this.tags);
    switch (this.yaml.version) {
      case "1.1":
        this.atNextDocument = true;
        break;
      case "1.2":
        this.atNextDocument = false;
        this.yaml = {
          explicit: _Directives.defaultYaml.explicit,
          version: "1.2"
        };
        this.tags = Object.assign({}, _Directives.defaultTags);
        break;
    }
    return res;
  }
  /**
   * @param onError - May be called even if the action was successful
   * @returns `true` on success
   */
  add(line, onError) {
    if (this.atNextDocument) {
      this.yaml = { explicit: _Directives.defaultYaml.explicit, version: "1.1" };
      this.tags = Object.assign({}, _Directives.defaultTags);
      this.atNextDocument = false;
    }
    const parts = line.trim().split(/[ \t]+/);
    const name = parts.shift();
    switch (name) {
      case "%TAG": {
        if (parts.length !== 2) {
          onError(0, "%TAG directive should contain exactly two parts");
          if (parts.length < 2)
            return false;
        }
        const [handle, prefix] = parts;
        this.tags[handle] = prefix;
        return true;
      }
      case "%YAML": {
        this.yaml.explicit = true;
        if (parts.length !== 1) {
          onError(0, "%YAML directive should contain exactly one part");
          return false;
        }
        const [version] = parts;
        if (version === "1.1" || version === "1.2") {
          this.yaml.version = version;
          return true;
        } else {
          const isValid = /^\d+\.\d+$/.test(version);
          onError(6, `Unsupported YAML version ${version}`, isValid);
          return false;
        }
      }
      default:
        onError(0, `Unknown directive ${name}`, true);
        return false;
    }
  }
  /**
   * Resolves a tag, matching handles to those defined in %TAG directives.
   *
   * @returns Resolved tag, which may also be the non-specific tag `'!'` or a
   *   `'!local'` tag, or `null` if unresolvable.
   */
  tagName(source, onError) {
    if (source === "!")
      return "!";
    if (source[0] !== "!") {
      onError(`Not a valid tag: ${source}`);
      return null;
    }
    if (source[1] === "<") {
      const verbatim = source.slice(2, -1);
      if (verbatim === "!" || verbatim === "!!") {
        onError(`Verbatim tags aren't resolved, so ${source} is invalid.`);
        return null;
      }
      if (source[source.length - 1] !== ">")
        onError("Verbatim tags must end with a >");
      return verbatim;
    }
    const [, handle, suffix] = source.match(/^(.*!)([^!]*)$/s);
    if (!suffix)
      onError(`The ${source} tag has no suffix`);
    const prefix = this.tags[handle];
    if (prefix) {
      try {
        return prefix + decodeURIComponent(suffix);
      } catch (error) {
        onError(String(error));
        return null;
      }
    }
    if (handle === "!")
      return source;
    onError(`Could not resolve tag: ${source}`);
    return null;
  }
  /**
   * Given a fully resolved tag, returns its printable string form,
   * taking into account current tag prefixes and defaults.
   */
  tagString(tag) {
    for (const [handle, prefix] of Object.entries(this.tags)) {
      if (tag.startsWith(prefix))
        return handle + escapeTagName(tag.substring(prefix.length));
    }
    return tag[0] === "!" ? tag : `!<${tag}>`;
  }
  toString(doc) {
    const lines = this.yaml.explicit ? [`%YAML ${this.yaml.version || "1.2"}`] : [];
    const tagEntries = Object.entries(this.tags);
    let tagNames;
    if (doc && tagEntries.length > 0 && isNode(doc.contents)) {
      const tags = {};
      visit(doc.contents, (_key, node) => {
        if (isNode(node) && node.tag)
          tags[node.tag] = true;
      });
      tagNames = Object.keys(tags);
    } else
      tagNames = [];
    for (const [handle, prefix] of tagEntries) {
      if (handle === "!!" && prefix === "tag:yaml.org,2002:")
        continue;
      if (!doc || tagNames.some((tn) => tn.startsWith(prefix)))
        lines.push(`%TAG ${handle} ${prefix}`);
    }
    return lines.join("\n");
  }
};
Directives.defaultYaml = { explicit: false, version: "1.2" };
Directives.defaultTags = { "!!": "tag:yaml.org,2002:" };

// node_modules/yaml/browser/dist/doc/anchors.js
function anchorIsValid(anchor) {
  if (/[\x00-\x19\s,[\]{}]/.test(anchor)) {
    const sa = JSON.stringify(anchor);
    const msg = `Anchor must not contain whitespace or control characters: ${sa}`;
    throw new Error(msg);
  }
  return true;
}
function anchorNames(root) {
  const anchors = /* @__PURE__ */ new Set();
  visit(root, {
    Value(_key, node) {
      if (node.anchor)
        anchors.add(node.anchor);
    }
  });
  return anchors;
}
function findNewAnchor(prefix, exclude) {
  for (let i3 = 1; true; ++i3) {
    const name = `${prefix}${i3}`;
    if (!exclude.has(name))
      return name;
  }
}
function createNodeAnchors(doc, prefix) {
  const aliasObjects = [];
  const sourceObjects = /* @__PURE__ */ new Map();
  let prevAnchors = null;
  return {
    onAnchor: (source) => {
      aliasObjects.push(source);
      prevAnchors ?? (prevAnchors = anchorNames(doc));
      const anchor = findNewAnchor(prefix, prevAnchors);
      prevAnchors.add(anchor);
      return anchor;
    },
    /**
     * With circular references, the source node is only resolved after all
     * of its child nodes are. This is why anchors are set only after all of
     * the nodes have been created.
     */
    setAnchors: () => {
      for (const source of aliasObjects) {
        const ref = sourceObjects.get(source);
        if (typeof ref === "object" && ref.anchor && (isScalar(ref.node) || isCollection(ref.node))) {
          ref.node.anchor = ref.anchor;
        } else {
          const error = new Error("Failed to resolve repeated object (this should not happen)");
          error.source = source;
          throw error;
        }
      }
    },
    sourceObjects
  };
}

// node_modules/yaml/browser/dist/doc/applyReviver.js
function applyReviver(reviver, obj, key, val) {
  if (val && typeof val === "object") {
    if (Array.isArray(val)) {
      for (let i3 = 0, len = val.length; i3 < len; ++i3) {
        const v0 = val[i3];
        const v1 = applyReviver(reviver, val, String(i3), v0);
        if (v1 === void 0)
          delete val[i3];
        else if (v1 !== v0)
          val[i3] = v1;
      }
    } else if (val instanceof Map) {
      for (const k2 of Array.from(val.keys())) {
        const v0 = val.get(k2);
        const v1 = applyReviver(reviver, val, k2, v0);
        if (v1 === void 0)
          val.delete(k2);
        else if (v1 !== v0)
          val.set(k2, v1);
      }
    } else if (val instanceof Set) {
      for (const v0 of Array.from(val)) {
        const v1 = applyReviver(reviver, val, v0, v0);
        if (v1 === void 0)
          val.delete(v0);
        else if (v1 !== v0) {
          val.delete(v0);
          val.add(v1);
        }
      }
    } else {
      for (const [k2, v0] of Object.entries(val)) {
        const v1 = applyReviver(reviver, val, k2, v0);
        if (v1 === void 0)
          delete val[k2];
        else if (v1 !== v0)
          val[k2] = v1;
      }
    }
  }
  return reviver.call(obj, key, val);
}

// node_modules/yaml/browser/dist/nodes/toJS.js
function toJS(value, arg, ctx) {
  if (Array.isArray(value))
    return value.map((v3, i3) => toJS(v3, String(i3), ctx));
  if (value && typeof value.toJSON === "function") {
    if (!ctx || !hasAnchor(value))
      return value.toJSON(arg, ctx);
    const data = { aliasCount: 0, count: 1, res: void 0 };
    ctx.anchors.set(value, data);
    ctx.onCreate = (res2) => {
      data.res = res2;
      delete ctx.onCreate;
    };
    const res = value.toJSON(arg, ctx);
    if (ctx.onCreate)
      ctx.onCreate(res);
    return res;
  }
  if (typeof value === "bigint" && !ctx?.keep)
    return Number(value);
  return value;
}

// node_modules/yaml/browser/dist/nodes/Node.js
var NodeBase = class {
  constructor(type) {
    Object.defineProperty(this, NODE_TYPE, { value: type });
  }
  /** Create a copy of this node.  */
  clone() {
    const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  /** A plain JavaScript representation of this node. */
  toJS(doc, { mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
    if (!isDocument(doc))
      throw new TypeError("A document argument is required");
    const ctx = {
      anchors: /* @__PURE__ */ new Map(),
      doc,
      keep: true,
      mapAsMap: mapAsMap === true,
      mapKeyWarned: false,
      maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
    };
    const res = toJS(this, "", ctx);
    if (typeof onAnchor === "function")
      for (const { count, res: res2 } of ctx.anchors.values())
        onAnchor(res2, count);
    return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
  }
};

// node_modules/yaml/browser/dist/nodes/Alias.js
var Alias = class extends NodeBase {
  constructor(source) {
    super(ALIAS);
    this.source = source;
    Object.defineProperty(this, "tag", {
      set() {
        throw new Error("Alias nodes cannot have tags");
      }
    });
  }
  /**
   * Resolve the value of this alias within `doc`, finding the last
   * instance of the `source` anchor before this node.
   */
  resolve(doc, ctx) {
    let nodes;
    if (ctx?.aliasResolveCache) {
      nodes = ctx.aliasResolveCache;
    } else {
      nodes = [];
      visit(doc, {
        Node: (_key, node) => {
          if (isAlias(node) || hasAnchor(node))
            nodes.push(node);
        }
      });
      if (ctx)
        ctx.aliasResolveCache = nodes;
    }
    let found = void 0;
    for (const node of nodes) {
      if (node === this)
        break;
      if (node.anchor === this.source)
        found = node;
    }
    return found;
  }
  toJSON(_arg, ctx) {
    if (!ctx)
      return { source: this.source };
    const { anchors, doc, maxAliasCount } = ctx;
    const source = this.resolve(doc, ctx);
    if (!source) {
      const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
      throw new ReferenceError(msg);
    }
    let data = anchors.get(source);
    if (!data) {
      toJS(source, null, ctx);
      data = anchors.get(source);
    }
    if (data?.res === void 0) {
      const msg = "This should not happen: Alias anchor was not resolved?";
      throw new ReferenceError(msg);
    }
    if (maxAliasCount >= 0) {
      data.count += 1;
      if (data.aliasCount === 0)
        data.aliasCount = getAliasCount(doc, source, anchors);
      if (data.count * data.aliasCount > maxAliasCount) {
        const msg = "Excessive alias count indicates a resource exhaustion attack";
        throw new ReferenceError(msg);
      }
    }
    return data.res;
  }
  toString(ctx, _onComment, _onChompKeep) {
    const src = `*${this.source}`;
    if (ctx) {
      anchorIsValid(this.source);
      if (ctx.options.verifyAliasOrder && !ctx.anchors.has(this.source)) {
        const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
        throw new Error(msg);
      }
      if (ctx.implicitKey)
        return `${src} `;
    }
    return src;
  }
};
function getAliasCount(doc, node, anchors) {
  if (isAlias(node)) {
    const source = node.resolve(doc);
    const anchor = anchors && source && anchors.get(source);
    return anchor ? anchor.count * anchor.aliasCount : 0;
  } else if (isCollection(node)) {
    let count = 0;
    for (const item of node.items) {
      const c3 = getAliasCount(doc, item, anchors);
      if (c3 > count)
        count = c3;
    }
    return count;
  } else if (isPair(node)) {
    const kc = getAliasCount(doc, node.key, anchors);
    const vc = getAliasCount(doc, node.value, anchors);
    return Math.max(kc, vc);
  }
  return 1;
}

// node_modules/yaml/browser/dist/nodes/Scalar.js
var isScalarValue = (value) => !value || typeof value !== "function" && typeof value !== "object";
var Scalar = class extends NodeBase {
  constructor(value) {
    super(SCALAR);
    this.value = value;
  }
  toJSON(arg, ctx) {
    return ctx?.keep ? this.value : toJS(this.value, arg, ctx);
  }
  toString() {
    return String(this.value);
  }
};
Scalar.BLOCK_FOLDED = "BLOCK_FOLDED";
Scalar.BLOCK_LITERAL = "BLOCK_LITERAL";
Scalar.PLAIN = "PLAIN";
Scalar.QUOTE_DOUBLE = "QUOTE_DOUBLE";
Scalar.QUOTE_SINGLE = "QUOTE_SINGLE";

// node_modules/yaml/browser/dist/doc/createNode.js
var defaultTagPrefix = "tag:yaml.org,2002:";
function findTagObject(value, tagName, tags) {
  if (tagName) {
    const match = tags.filter((t4) => t4.tag === tagName);
    const tagObj = match.find((t4) => !t4.format) ?? match[0];
    if (!tagObj)
      throw new Error(`Tag ${tagName} not found`);
    return tagObj;
  }
  return tags.find((t4) => t4.identify?.(value) && !t4.format);
}
function createNode(value, tagName, ctx) {
  if (isDocument(value))
    value = value.contents;
  if (isNode(value))
    return value;
  if (isPair(value)) {
    const map2 = ctx.schema[MAP].createNode?.(ctx.schema, null, ctx);
    map2.items.push(value);
    return map2;
  }
  if (value instanceof String || value instanceof Number || value instanceof Boolean || typeof BigInt !== "undefined" && value instanceof BigInt) {
    value = value.valueOf();
  }
  const { aliasDuplicateObjects, onAnchor, onTagObj, schema: schema4, sourceObjects } = ctx;
  let ref = void 0;
  if (aliasDuplicateObjects && value && typeof value === "object") {
    ref = sourceObjects.get(value);
    if (ref) {
      ref.anchor ?? (ref.anchor = onAnchor(value));
      return new Alias(ref.anchor);
    } else {
      ref = { anchor: null, node: null };
      sourceObjects.set(value, ref);
    }
  }
  if (tagName?.startsWith("!!"))
    tagName = defaultTagPrefix + tagName.slice(2);
  let tagObj = findTagObject(value, tagName, schema4.tags);
  if (!tagObj) {
    if (value && typeof value.toJSON === "function") {
      value = value.toJSON();
    }
    if (!value || typeof value !== "object") {
      const node2 = new Scalar(value);
      if (ref)
        ref.node = node2;
      return node2;
    }
    tagObj = value instanceof Map ? schema4[MAP] : Symbol.iterator in Object(value) ? schema4[SEQ] : schema4[MAP];
  }
  if (onTagObj) {
    onTagObj(tagObj);
    delete ctx.onTagObj;
  }
  const node = tagObj?.createNode ? tagObj.createNode(ctx.schema, value, ctx) : typeof tagObj?.nodeClass?.from === "function" ? tagObj.nodeClass.from(ctx.schema, value, ctx) : new Scalar(value);
  if (tagName)
    node.tag = tagName;
  else if (!tagObj.default)
    node.tag = tagObj.tag;
  if (ref)
    ref.node = node;
  return node;
}

// node_modules/yaml/browser/dist/nodes/Collection.js
function collectionFromPath(schema4, path, value) {
  let v3 = value;
  for (let i3 = path.length - 1; i3 >= 0; --i3) {
    const k2 = path[i3];
    if (typeof k2 === "number" && Number.isInteger(k2) && k2 >= 0) {
      const a3 = [];
      a3[k2] = v3;
      v3 = a3;
    } else {
      v3 = /* @__PURE__ */ new Map([[k2, v3]]);
    }
  }
  return createNode(v3, void 0, {
    aliasDuplicateObjects: false,
    keepUndefined: false,
    onAnchor: () => {
      throw new Error("This should not happen, please report a bug.");
    },
    schema: schema4,
    sourceObjects: /* @__PURE__ */ new Map()
  });
}
var isEmptyPath = (path) => path == null || typeof path === "object" && !!path[Symbol.iterator]().next().done;
var Collection = class extends NodeBase {
  constructor(type, schema4) {
    super(type);
    Object.defineProperty(this, "schema", {
      value: schema4,
      configurable: true,
      enumerable: false,
      writable: true
    });
  }
  /**
   * Create a copy of this collection.
   *
   * @param schema - If defined, overwrites the original's schema
   */
  clone(schema4) {
    const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
    if (schema4)
      copy.schema = schema4;
    copy.items = copy.items.map((it) => isNode(it) || isPair(it) ? it.clone(schema4) : it);
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  /**
   * Adds a value to the collection. For `!!map` and `!!omap` the value must
   * be a Pair instance or a `{ key, value }` object, which may not have a key
   * that already exists in the map.
   */
  addIn(path, value) {
    if (isEmptyPath(path))
      this.add(value);
    else {
      const [key, ...rest] = path;
      const node = this.get(key, true);
      if (isCollection(node))
        node.addIn(rest, value);
      else if (node === void 0 && this.schema)
        this.set(key, collectionFromPath(this.schema, rest, value));
      else
        throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
    }
  }
  /**
   * Removes a value from the collection.
   * @returns `true` if the item was found and removed.
   */
  deleteIn(path) {
    const [key, ...rest] = path;
    if (rest.length === 0)
      return this.delete(key);
    const node = this.get(key, true);
    if (isCollection(node))
      return node.deleteIn(rest);
    else
      throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
  }
  /**
   * Returns item at `key`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  getIn(path, keepScalar) {
    const [key, ...rest] = path;
    const node = this.get(key, true);
    if (rest.length === 0)
      return !keepScalar && isScalar(node) ? node.value : node;
    else
      return isCollection(node) ? node.getIn(rest, keepScalar) : void 0;
  }
  hasAllNullValues(allowScalar) {
    return this.items.every((node) => {
      if (!isPair(node))
        return false;
      const n2 = node.value;
      return n2 == null || allowScalar && isScalar(n2) && n2.value == null && !n2.commentBefore && !n2.comment && !n2.tag;
    });
  }
  /**
   * Checks if the collection includes a value with the key `key`.
   */
  hasIn(path) {
    const [key, ...rest] = path;
    if (rest.length === 0)
      return this.has(key);
    const node = this.get(key, true);
    return isCollection(node) ? node.hasIn(rest) : false;
  }
  /**
   * Sets a value in this collection. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  setIn(path, value) {
    const [key, ...rest] = path;
    if (rest.length === 0) {
      this.set(key, value);
    } else {
      const node = this.get(key, true);
      if (isCollection(node))
        node.setIn(rest, value);
      else if (node === void 0 && this.schema)
        this.set(key, collectionFromPath(this.schema, rest, value));
      else
        throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
    }
  }
};

// node_modules/yaml/browser/dist/stringify/stringifyComment.js
var stringifyComment = (str) => str.replace(/^(?!$)(?: $)?/gm, "#");
function indentComment(comment, indent) {
  if (/^\n+$/.test(comment))
    return comment.substring(1);
  return indent ? comment.replace(/^(?! *$)/gm, indent) : comment;
}
var lineComment = (str, indent, comment) => str.endsWith("\n") ? indentComment(comment, indent) : comment.includes("\n") ? "\n" + indentComment(comment, indent) : (str.endsWith(" ") ? "" : " ") + comment;

// node_modules/yaml/browser/dist/stringify/foldFlowLines.js
var FOLD_FLOW = "flow";
var FOLD_BLOCK = "block";
var FOLD_QUOTED = "quoted";
function foldFlowLines(text, indent, mode = "flow", { indentAtStart, lineWidth = 80, minContentWidth = 20, onFold, onOverflow } = {}) {
  if (!lineWidth || lineWidth < 0)
    return text;
  if (lineWidth < minContentWidth)
    minContentWidth = 0;
  const endStep = Math.max(1 + minContentWidth, 1 + lineWidth - indent.length);
  if (text.length <= endStep)
    return text;
  const folds = [];
  const escapedFolds = {};
  let end = lineWidth - indent.length;
  if (typeof indentAtStart === "number") {
    if (indentAtStart > lineWidth - Math.max(2, minContentWidth))
      folds.push(0);
    else
      end = lineWidth - indentAtStart;
  }
  let split = void 0;
  let prev = void 0;
  let overflow = false;
  let i3 = -1;
  let escStart = -1;
  let escEnd = -1;
  if (mode === FOLD_BLOCK) {
    i3 = consumeMoreIndentedLines(text, i3, indent.length);
    if (i3 !== -1)
      end = i3 + endStep;
  }
  for (let ch; ch = text[i3 += 1]; ) {
    if (mode === FOLD_QUOTED && ch === "\\") {
      escStart = i3;
      switch (text[i3 + 1]) {
        case "x":
          i3 += 3;
          break;
        case "u":
          i3 += 5;
          break;
        case "U":
          i3 += 9;
          break;
        default:
          i3 += 1;
      }
      escEnd = i3;
    }
    if (ch === "\n") {
      if (mode === FOLD_BLOCK)
        i3 = consumeMoreIndentedLines(text, i3, indent.length);
      end = i3 + indent.length + endStep;
      split = void 0;
    } else {
      if (ch === " " && prev && prev !== " " && prev !== "\n" && prev !== "	") {
        const next = text[i3 + 1];
        if (next && next !== " " && next !== "\n" && next !== "	")
          split = i3;
      }
      if (i3 >= end) {
        if (split) {
          folds.push(split);
          end = split + endStep;
          split = void 0;
        } else if (mode === FOLD_QUOTED) {
          while (prev === " " || prev === "	") {
            prev = ch;
            ch = text[i3 += 1];
            overflow = true;
          }
          const j3 = i3 > escEnd + 1 ? i3 - 2 : escStart - 1;
          if (escapedFolds[j3])
            return text;
          folds.push(j3);
          escapedFolds[j3] = true;
          end = j3 + endStep;
          split = void 0;
        } else {
          overflow = true;
        }
      }
    }
    prev = ch;
  }
  if (overflow && onOverflow)
    onOverflow();
  if (folds.length === 0)
    return text;
  if (onFold)
    onFold();
  let res = text.slice(0, folds[0]);
  for (let i4 = 0; i4 < folds.length; ++i4) {
    const fold = folds[i4];
    const end2 = folds[i4 + 1] || text.length;
    if (fold === 0)
      res = `
${indent}${text.slice(0, end2)}`;
    else {
      if (mode === FOLD_QUOTED && escapedFolds[fold])
        res += `${text[fold]}\\`;
      res += `
${indent}${text.slice(fold + 1, end2)}`;
    }
  }
  return res;
}
function consumeMoreIndentedLines(text, i3, indent) {
  let end = i3;
  let start = i3 + 1;
  let ch = text[start];
  while (ch === " " || ch === "	") {
    if (i3 < start + indent) {
      ch = text[++i3];
    } else {
      do {
        ch = text[++i3];
      } while (ch && ch !== "\n");
      end = i3;
      start = i3 + 1;
      ch = text[start];
    }
  }
  return end;
}

// node_modules/yaml/browser/dist/stringify/stringifyString.js
var getFoldOptions = (ctx, isBlock2) => ({
  indentAtStart: isBlock2 ? ctx.indent.length : ctx.indentAtStart,
  lineWidth: ctx.options.lineWidth,
  minContentWidth: ctx.options.minContentWidth
});
var containsDocumentMarker = (str) => /^(%|---|\.\.\.)/m.test(str);
function lineLengthOverLimit(str, lineWidth, indentLength) {
  if (!lineWidth || lineWidth < 0)
    return false;
  const limit = lineWidth - indentLength;
  const strLen = str.length;
  if (strLen <= limit)
    return false;
  for (let i3 = 0, start = 0; i3 < strLen; ++i3) {
    if (str[i3] === "\n") {
      if (i3 - start > limit)
        return true;
      start = i3 + 1;
      if (strLen - start <= limit)
        return false;
    }
  }
  return true;
}
function doubleQuotedString(value, ctx) {
  const json = JSON.stringify(value);
  if (ctx.options.doubleQuotedAsJSON)
    return json;
  const { implicitKey } = ctx;
  const minMultiLineLength = ctx.options.doubleQuotedMinMultiLineLength;
  const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
  let str = "";
  let start = 0;
  for (let i3 = 0, ch = json[i3]; ch; ch = json[++i3]) {
    if (ch === " " && json[i3 + 1] === "\\" && json[i3 + 2] === "n") {
      str += json.slice(start, i3) + "\\ ";
      i3 += 1;
      start = i3;
      ch = "\\";
    }
    if (ch === "\\")
      switch (json[i3 + 1]) {
        case "u":
          {
            str += json.slice(start, i3);
            const code = json.substr(i3 + 2, 4);
            switch (code) {
              case "0000":
                str += "\\0";
                break;
              case "0007":
                str += "\\a";
                break;
              case "000b":
                str += "\\v";
                break;
              case "001b":
                str += "\\e";
                break;
              case "0085":
                str += "\\N";
                break;
              case "00a0":
                str += "\\_";
                break;
              case "2028":
                str += "\\L";
                break;
              case "2029":
                str += "\\P";
                break;
              default:
                if (code.substr(0, 2) === "00")
                  str += "\\x" + code.substr(2);
                else
                  str += json.substr(i3, 6);
            }
            i3 += 5;
            start = i3 + 1;
          }
          break;
        case "n":
          if (implicitKey || json[i3 + 2] === '"' || json.length < minMultiLineLength) {
            i3 += 1;
          } else {
            str += json.slice(start, i3) + "\n\n";
            while (json[i3 + 2] === "\\" && json[i3 + 3] === "n" && json[i3 + 4] !== '"') {
              str += "\n";
              i3 += 2;
            }
            str += indent;
            if (json[i3 + 2] === " ")
              str += "\\";
            i3 += 1;
            start = i3 + 1;
          }
          break;
        default:
          i3 += 1;
      }
  }
  str = start ? str + json.slice(start) : json;
  return implicitKey ? str : foldFlowLines(str, indent, FOLD_QUOTED, getFoldOptions(ctx, false));
}
function singleQuotedString(value, ctx) {
  if (ctx.options.singleQuote === false || ctx.implicitKey && value.includes("\n") || /[ \t]\n|\n[ \t]/.test(value))
    return doubleQuotedString(value, ctx);
  const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
  const res = "'" + value.replace(/'/g, "''").replace(/\n+/g, `$&
${indent}`) + "'";
  return ctx.implicitKey ? res : foldFlowLines(res, indent, FOLD_FLOW, getFoldOptions(ctx, false));
}
function quotedString(value, ctx) {
  const { singleQuote } = ctx.options;
  let qs;
  if (singleQuote === false)
    qs = doubleQuotedString;
  else {
    const hasDouble = value.includes('"');
    const hasSingle = value.includes("'");
    if (hasDouble && !hasSingle)
      qs = singleQuotedString;
    else if (hasSingle && !hasDouble)
      qs = doubleQuotedString;
    else
      qs = singleQuote ? singleQuotedString : doubleQuotedString;
  }
  return qs(value, ctx);
}
var blockEndNewlines;
try {
  blockEndNewlines = new RegExp("(^|(?<!\n))\n+(?!\n|$)", "g");
} catch {
  blockEndNewlines = /\n+(?!\n|$)/g;
}
function blockString({ comment, type, value }, ctx, onComment, onChompKeep) {
  const { blockQuote, commentString, lineWidth } = ctx.options;
  if (!blockQuote || /\n[\t ]+$/.test(value)) {
    return quotedString(value, ctx);
  }
  const indent = ctx.indent || (ctx.forceBlockIndent || containsDocumentMarker(value) ? "  " : "");
  const literal = blockQuote === "literal" ? true : blockQuote === "folded" || type === Scalar.BLOCK_FOLDED ? false : type === Scalar.BLOCK_LITERAL ? true : !lineLengthOverLimit(value, lineWidth, indent.length);
  if (!value)
    return literal ? "|\n" : ">\n";
  let chomp;
  let endStart;
  for (endStart = value.length; endStart > 0; --endStart) {
    const ch = value[endStart - 1];
    if (ch !== "\n" && ch !== "	" && ch !== " ")
      break;
  }
  let end = value.substring(endStart);
  const endNlPos = end.indexOf("\n");
  if (endNlPos === -1) {
    chomp = "-";
  } else if (value === end || endNlPos !== end.length - 1) {
    chomp = "+";
    if (onChompKeep)
      onChompKeep();
  } else {
    chomp = "";
  }
  if (end) {
    value = value.slice(0, -end.length);
    if (end[end.length - 1] === "\n")
      end = end.slice(0, -1);
    end = end.replace(blockEndNewlines, `$&${indent}`);
  }
  let startWithSpace = false;
  let startEnd;
  let startNlPos = -1;
  for (startEnd = 0; startEnd < value.length; ++startEnd) {
    const ch = value[startEnd];
    if (ch === " ")
      startWithSpace = true;
    else if (ch === "\n")
      startNlPos = startEnd;
    else
      break;
  }
  let start = value.substring(0, startNlPos < startEnd ? startNlPos + 1 : startEnd);
  if (start) {
    value = value.substring(start.length);
    start = start.replace(/\n+/g, `$&${indent}`);
  }
  const indentSize = indent ? "2" : "1";
  let header = (startWithSpace ? indentSize : "") + chomp;
  if (comment) {
    header += " " + commentString(comment.replace(/ ?[\r\n]+/g, " "));
    if (onComment)
      onComment();
  }
  if (!literal) {
    const foldedValue = value.replace(/\n+/g, "\n$&").replace(/(?:^|\n)([\t ].*)(?:([\n\t ]*)\n(?![\n\t ]))?/g, "$1$2").replace(/\n+/g, `$&${indent}`);
    let literalFallback = false;
    const foldOptions = getFoldOptions(ctx, true);
    if (blockQuote !== "folded" && type !== Scalar.BLOCK_FOLDED) {
      foldOptions.onOverflow = () => {
        literalFallback = true;
      };
    }
    const body = foldFlowLines(`${start}${foldedValue}${end}`, indent, FOLD_BLOCK, foldOptions);
    if (!literalFallback)
      return `>${header}
${indent}${body}`;
  }
  value = value.replace(/\n+/g, `$&${indent}`);
  return `|${header}
${indent}${start}${value}${end}`;
}
function plainString(item, ctx, onComment, onChompKeep) {
  const { type, value } = item;
  const { actualString, implicitKey, indent, indentStep, inFlow } = ctx;
  if (implicitKey && value.includes("\n") || inFlow && /[[\]{},]/.test(value)) {
    return quotedString(value, ctx);
  }
  if (/^[\n\t ,[\]{}#&*!|>'"%@`]|^[?-]$|^[?-][ \t]|[\n:][ \t]|[ \t]\n|[\n\t ]#|[\n\t :]$/.test(value)) {
    return implicitKey || inFlow || !value.includes("\n") ? quotedString(value, ctx) : blockString(item, ctx, onComment, onChompKeep);
  }
  if (!implicitKey && !inFlow && type !== Scalar.PLAIN && value.includes("\n")) {
    return blockString(item, ctx, onComment, onChompKeep);
  }
  if (containsDocumentMarker(value)) {
    if (indent === "") {
      ctx.forceBlockIndent = true;
      return blockString(item, ctx, onComment, onChompKeep);
    } else if (implicitKey && indent === indentStep) {
      return quotedString(value, ctx);
    }
  }
  const str = value.replace(/\n+/g, `$&
${indent}`);
  if (actualString) {
    const test = (tag) => tag.default && tag.tag !== "tag:yaml.org,2002:str" && tag.test?.test(str);
    const { compat, tags } = ctx.doc.schema;
    if (tags.some(test) || compat?.some(test))
      return quotedString(value, ctx);
  }
  return implicitKey ? str : foldFlowLines(str, indent, FOLD_FLOW, getFoldOptions(ctx, false));
}
function stringifyString(item, ctx, onComment, onChompKeep) {
  const { implicitKey, inFlow } = ctx;
  const ss = typeof item.value === "string" ? item : Object.assign({}, item, { value: String(item.value) });
  let { type } = item;
  if (type !== Scalar.QUOTE_DOUBLE) {
    if (/[\x00-\x08\x0b-\x1f\x7f-\x9f\u{D800}-\u{DFFF}]/u.test(ss.value))
      type = Scalar.QUOTE_DOUBLE;
  }
  const _stringify = (_type) => {
    switch (_type) {
      case Scalar.BLOCK_FOLDED:
      case Scalar.BLOCK_LITERAL:
        return implicitKey || inFlow ? quotedString(ss.value, ctx) : blockString(ss, ctx, onComment, onChompKeep);
      case Scalar.QUOTE_DOUBLE:
        return doubleQuotedString(ss.value, ctx);
      case Scalar.QUOTE_SINGLE:
        return singleQuotedString(ss.value, ctx);
      case Scalar.PLAIN:
        return plainString(ss, ctx, onComment, onChompKeep);
      default:
        return null;
    }
  };
  let res = _stringify(type);
  if (res === null) {
    const { defaultKeyType, defaultStringType } = ctx.options;
    const t4 = implicitKey && defaultKeyType || defaultStringType;
    res = _stringify(t4);
    if (res === null)
      throw new Error(`Unsupported default string type ${t4}`);
  }
  return res;
}

// node_modules/yaml/browser/dist/stringify/stringify.js
function createStringifyContext(doc, options) {
  const opt = Object.assign({
    blockQuote: true,
    commentString: stringifyComment,
    defaultKeyType: null,
    defaultStringType: "PLAIN",
    directives: null,
    doubleQuotedAsJSON: false,
    doubleQuotedMinMultiLineLength: 40,
    falseStr: "false",
    flowCollectionPadding: true,
    indentSeq: true,
    lineWidth: 80,
    minContentWidth: 20,
    nullStr: "null",
    simpleKeys: false,
    singleQuote: null,
    trailingComma: false,
    trueStr: "true",
    verifyAliasOrder: true
  }, doc.schema.toStringOptions, options);
  let inFlow;
  switch (opt.collectionStyle) {
    case "block":
      inFlow = false;
      break;
    case "flow":
      inFlow = true;
      break;
    default:
      inFlow = null;
  }
  return {
    anchors: /* @__PURE__ */ new Set(),
    doc,
    flowCollectionPadding: opt.flowCollectionPadding ? " " : "",
    indent: "",
    indentStep: typeof opt.indent === "number" ? " ".repeat(opt.indent) : "  ",
    inFlow,
    options: opt
  };
}
function getTagObject(tags, item) {
  if (item.tag) {
    const match = tags.filter((t4) => t4.tag === item.tag);
    if (match.length > 0)
      return match.find((t4) => t4.format === item.format) ?? match[0];
  }
  let tagObj = void 0;
  let obj;
  if (isScalar(item)) {
    obj = item.value;
    let match = tags.filter((t4) => t4.identify?.(obj));
    if (match.length > 1) {
      const testMatch = match.filter((t4) => t4.test);
      if (testMatch.length > 0)
        match = testMatch;
    }
    tagObj = match.find((t4) => t4.format === item.format) ?? match.find((t4) => !t4.format);
  } else {
    obj = item;
    tagObj = tags.find((t4) => t4.nodeClass && obj instanceof t4.nodeClass);
  }
  if (!tagObj) {
    const name = obj?.constructor?.name ?? (obj === null ? "null" : typeof obj);
    throw new Error(`Tag not resolved for ${name} value`);
  }
  return tagObj;
}
function stringifyProps(node, tagObj, { anchors, doc }) {
  if (!doc.directives)
    return "";
  const props = [];
  const anchor = (isScalar(node) || isCollection(node)) && node.anchor;
  if (anchor && anchorIsValid(anchor)) {
    anchors.add(anchor);
    props.push(`&${anchor}`);
  }
  const tag = node.tag ?? (tagObj.default ? null : tagObj.tag);
  if (tag)
    props.push(doc.directives.tagString(tag));
  return props.join(" ");
}
function stringify(item, ctx, onComment, onChompKeep) {
  if (isPair(item))
    return item.toString(ctx, onComment, onChompKeep);
  if (isAlias(item)) {
    if (ctx.doc.directives)
      return item.toString(ctx);
    if (ctx.resolvedAliases?.has(item)) {
      throw new TypeError(`Cannot stringify circular structure without alias nodes`);
    } else {
      if (ctx.resolvedAliases)
        ctx.resolvedAliases.add(item);
      else
        ctx.resolvedAliases = /* @__PURE__ */ new Set([item]);
      item = item.resolve(ctx.doc);
    }
  }
  let tagObj = void 0;
  const node = isNode(item) ? item : ctx.doc.createNode(item, { onTagObj: (o2) => tagObj = o2 });
  tagObj ?? (tagObj = getTagObject(ctx.doc.schema.tags, node));
  const props = stringifyProps(node, tagObj, ctx);
  if (props.length > 0)
    ctx.indentAtStart = (ctx.indentAtStart ?? 0) + props.length + 1;
  const str = typeof tagObj.stringify === "function" ? tagObj.stringify(node, ctx, onComment, onChompKeep) : isScalar(node) ? stringifyString(node, ctx, onComment, onChompKeep) : node.toString(ctx, onComment, onChompKeep);
  if (!props)
    return str;
  return isScalar(node) || str[0] === "{" || str[0] === "[" ? `${props} ${str}` : `${props}
${ctx.indent}${str}`;
}

// node_modules/yaml/browser/dist/stringify/stringifyPair.js
function stringifyPair({ key, value }, ctx, onComment, onChompKeep) {
  const { allNullValues, doc, indent, indentStep, options: { commentString, indentSeq, simpleKeys } } = ctx;
  let keyComment = isNode(key) && key.comment || null;
  if (simpleKeys) {
    if (keyComment) {
      throw new Error("With simple keys, key nodes cannot have comments");
    }
    if (isCollection(key) || !isNode(key) && typeof key === "object") {
      const msg = "With simple keys, collection cannot be used as a key value";
      throw new Error(msg);
    }
  }
  let explicitKey = !simpleKeys && (!key || keyComment && value == null && !ctx.inFlow || isCollection(key) || (isScalar(key) ? key.type === Scalar.BLOCK_FOLDED || key.type === Scalar.BLOCK_LITERAL : typeof key === "object"));
  ctx = Object.assign({}, ctx, {
    allNullValues: false,
    implicitKey: !explicitKey && (simpleKeys || !allNullValues),
    indent: indent + indentStep
  });
  let keyCommentDone = false;
  let chompKeep = false;
  let str = stringify(key, ctx, () => keyCommentDone = true, () => chompKeep = true);
  if (!explicitKey && !ctx.inFlow && str.length > 1024) {
    if (simpleKeys)
      throw new Error("With simple keys, single line scalar must not span more than 1024 characters");
    explicitKey = true;
  }
  if (ctx.inFlow) {
    if (allNullValues || value == null) {
      if (keyCommentDone && onComment)
        onComment();
      return str === "" ? "?" : explicitKey ? `? ${str}` : str;
    }
  } else if (allNullValues && !simpleKeys || value == null && explicitKey) {
    str = `? ${str}`;
    if (keyComment && !keyCommentDone) {
      str += lineComment(str, ctx.indent, commentString(keyComment));
    } else if (chompKeep && onChompKeep)
      onChompKeep();
    return str;
  }
  if (keyCommentDone)
    keyComment = null;
  if (explicitKey) {
    if (keyComment)
      str += lineComment(str, ctx.indent, commentString(keyComment));
    str = `? ${str}
${indent}:`;
  } else {
    str = `${str}:`;
    if (keyComment)
      str += lineComment(str, ctx.indent, commentString(keyComment));
  }
  let vsb, vcb, valueComment;
  if (isNode(value)) {
    vsb = !!value.spaceBefore;
    vcb = value.commentBefore;
    valueComment = value.comment;
  } else {
    vsb = false;
    vcb = null;
    valueComment = null;
    if (value && typeof value === "object")
      value = doc.createNode(value);
  }
  ctx.implicitKey = false;
  if (!explicitKey && !keyComment && isScalar(value))
    ctx.indentAtStart = str.length + 1;
  chompKeep = false;
  if (!indentSeq && indentStep.length >= 2 && !ctx.inFlow && !explicitKey && isSeq(value) && !value.flow && !value.tag && !value.anchor) {
    ctx.indent = ctx.indent.substring(2);
  }
  let valueCommentDone = false;
  const valueStr = stringify(value, ctx, () => valueCommentDone = true, () => chompKeep = true);
  let ws = " ";
  if (keyComment || vsb || vcb) {
    ws = vsb ? "\n" : "";
    if (vcb) {
      const cs = commentString(vcb);
      ws += `
${indentComment(cs, ctx.indent)}`;
    }
    if (valueStr === "" && !ctx.inFlow) {
      if (ws === "\n" && valueComment)
        ws = "\n\n";
    } else {
      ws += `
${ctx.indent}`;
    }
  } else if (!explicitKey && isCollection(value)) {
    const vs0 = valueStr[0];
    const nl0 = valueStr.indexOf("\n");
    const hasNewline = nl0 !== -1;
    const flow = ctx.inFlow ?? value.flow ?? value.items.length === 0;
    if (hasNewline || !flow) {
      let hasPropsLine = false;
      if (hasNewline && (vs0 === "&" || vs0 === "!")) {
        let sp0 = valueStr.indexOf(" ");
        if (vs0 === "&" && sp0 !== -1 && sp0 < nl0 && valueStr[sp0 + 1] === "!") {
          sp0 = valueStr.indexOf(" ", sp0 + 1);
        }
        if (sp0 === -1 || nl0 < sp0)
          hasPropsLine = true;
      }
      if (!hasPropsLine)
        ws = `
${ctx.indent}`;
    }
  } else if (valueStr === "" || valueStr[0] === "\n") {
    ws = "";
  }
  str += ws + valueStr;
  if (ctx.inFlow) {
    if (valueCommentDone && onComment)
      onComment();
  } else if (valueComment && !valueCommentDone) {
    str += lineComment(str, ctx.indent, commentString(valueComment));
  } else if (chompKeep && onChompKeep) {
    onChompKeep();
  }
  return str;
}

// node_modules/yaml/browser/dist/log.js
function warn(logLevel, warning) {
  if (logLevel === "debug" || logLevel === "warn") {
    console.warn(warning);
  }
}

// node_modules/yaml/browser/dist/schema/yaml-1.1/merge.js
var MERGE_KEY = "<<";
var merge = {
  identify: (value) => value === MERGE_KEY || typeof value === "symbol" && value.description === MERGE_KEY,
  default: "key",
  tag: "tag:yaml.org,2002:merge",
  test: /^<<$/,
  resolve: () => Object.assign(new Scalar(Symbol(MERGE_KEY)), {
    addToJSMap: addMergeToJSMap
  }),
  stringify: () => MERGE_KEY
};
var isMergeKey = (ctx, key) => (merge.identify(key) || isScalar(key) && (!key.type || key.type === Scalar.PLAIN) && merge.identify(key.value)) && ctx?.doc.schema.tags.some((tag) => tag.tag === merge.tag && tag.default);
function addMergeToJSMap(ctx, map2, value) {
  value = ctx && isAlias(value) ? value.resolve(ctx.doc) : value;
  if (isSeq(value))
    for (const it of value.items)
      mergeValue(ctx, map2, it);
  else if (Array.isArray(value))
    for (const it of value)
      mergeValue(ctx, map2, it);
  else
    mergeValue(ctx, map2, value);
}
function mergeValue(ctx, map2, value) {
  const source = ctx && isAlias(value) ? value.resolve(ctx.doc) : value;
  if (!isMap(source))
    throw new Error("Merge sources must be maps or map aliases");
  const srcMap = source.toJSON(null, ctx, Map);
  for (const [key, value2] of srcMap) {
    if (map2 instanceof Map) {
      if (!map2.has(key))
        map2.set(key, value2);
    } else if (map2 instanceof Set) {
      map2.add(key);
    } else if (!Object.prototype.hasOwnProperty.call(map2, key)) {
      Object.defineProperty(map2, key, {
        value: value2,
        writable: true,
        enumerable: true,
        configurable: true
      });
    }
  }
  return map2;
}

// node_modules/yaml/browser/dist/nodes/addPairToJSMap.js
function addPairToJSMap(ctx, map2, { key, value }) {
  if (isNode(key) && key.addToJSMap)
    key.addToJSMap(ctx, map2, value);
  else if (isMergeKey(ctx, key))
    addMergeToJSMap(ctx, map2, value);
  else {
    const jsKey = toJS(key, "", ctx);
    if (map2 instanceof Map) {
      map2.set(jsKey, toJS(value, jsKey, ctx));
    } else if (map2 instanceof Set) {
      map2.add(jsKey);
    } else {
      const stringKey = stringifyKey(key, jsKey, ctx);
      const jsValue = toJS(value, stringKey, ctx);
      if (stringKey in map2)
        Object.defineProperty(map2, stringKey, {
          value: jsValue,
          writable: true,
          enumerable: true,
          configurable: true
        });
      else
        map2[stringKey] = jsValue;
    }
  }
  return map2;
}
function stringifyKey(key, jsKey, ctx) {
  if (jsKey === null)
    return "";
  if (typeof jsKey !== "object")
    return String(jsKey);
  if (isNode(key) && ctx?.doc) {
    const strCtx = createStringifyContext(ctx.doc, {});
    strCtx.anchors = /* @__PURE__ */ new Set();
    for (const node of ctx.anchors.keys())
      strCtx.anchors.add(node.anchor);
    strCtx.inFlow = true;
    strCtx.inStringifyKey = true;
    const strKey = key.toString(strCtx);
    if (!ctx.mapKeyWarned) {
      let jsonStr = JSON.stringify(strKey);
      if (jsonStr.length > 40)
        jsonStr = jsonStr.substring(0, 36) + '..."';
      warn(ctx.doc.options.logLevel, `Keys with collection values will be stringified due to JS Object restrictions: ${jsonStr}. Set mapAsMap: true to use object keys.`);
      ctx.mapKeyWarned = true;
    }
    return strKey;
  }
  return JSON.stringify(jsKey);
}

// node_modules/yaml/browser/dist/nodes/Pair.js
function createPair(key, value, ctx) {
  const k2 = createNode(key, void 0, ctx);
  const v3 = createNode(value, void 0, ctx);
  return new Pair(k2, v3);
}
var Pair = class _Pair {
  constructor(key, value = null) {
    Object.defineProperty(this, NODE_TYPE, { value: PAIR });
    this.key = key;
    this.value = value;
  }
  clone(schema4) {
    let { key, value } = this;
    if (isNode(key))
      key = key.clone(schema4);
    if (isNode(value))
      value = value.clone(schema4);
    return new _Pair(key, value);
  }
  toJSON(_2, ctx) {
    const pair = ctx?.mapAsMap ? /* @__PURE__ */ new Map() : {};
    return addPairToJSMap(ctx, pair, this);
  }
  toString(ctx, onComment, onChompKeep) {
    return ctx?.doc ? stringifyPair(this, ctx, onComment, onChompKeep) : JSON.stringify(this);
  }
};

// node_modules/yaml/browser/dist/stringify/stringifyCollection.js
function stringifyCollection(collection, ctx, options) {
  const flow = ctx.inFlow ?? collection.flow;
  const stringify4 = flow ? stringifyFlowCollection : stringifyBlockCollection;
  return stringify4(collection, ctx, options);
}
function stringifyBlockCollection({ comment, items }, ctx, { blockItemPrefix, flowChars, itemIndent, onChompKeep, onComment }) {
  const { indent, options: { commentString } } = ctx;
  const itemCtx = Object.assign({}, ctx, { indent: itemIndent, type: null });
  let chompKeep = false;
  const lines = [];
  for (let i3 = 0; i3 < items.length; ++i3) {
    const item = items[i3];
    let comment2 = null;
    if (isNode(item)) {
      if (!chompKeep && item.spaceBefore)
        lines.push("");
      addCommentBefore(ctx, lines, item.commentBefore, chompKeep);
      if (item.comment)
        comment2 = item.comment;
    } else if (isPair(item)) {
      const ik = isNode(item.key) ? item.key : null;
      if (ik) {
        if (!chompKeep && ik.spaceBefore)
          lines.push("");
        addCommentBefore(ctx, lines, ik.commentBefore, chompKeep);
      }
    }
    chompKeep = false;
    let str2 = stringify(item, itemCtx, () => comment2 = null, () => chompKeep = true);
    if (comment2)
      str2 += lineComment(str2, itemIndent, commentString(comment2));
    if (chompKeep && comment2)
      chompKeep = false;
    lines.push(blockItemPrefix + str2);
  }
  let str;
  if (lines.length === 0) {
    str = flowChars.start + flowChars.end;
  } else {
    str = lines[0];
    for (let i3 = 1; i3 < lines.length; ++i3) {
      const line = lines[i3];
      str += line ? `
${indent}${line}` : "\n";
    }
  }
  if (comment) {
    str += "\n" + indentComment(commentString(comment), indent);
    if (onComment)
      onComment();
  } else if (chompKeep && onChompKeep)
    onChompKeep();
  return str;
}
function stringifyFlowCollection({ items }, ctx, { flowChars, itemIndent }) {
  const { indent, indentStep, flowCollectionPadding: fcPadding, options: { commentString } } = ctx;
  itemIndent += indentStep;
  const itemCtx = Object.assign({}, ctx, {
    indent: itemIndent,
    inFlow: true,
    type: null
  });
  let reqNewline = false;
  let linesAtValue = 0;
  const lines = [];
  for (let i3 = 0; i3 < items.length; ++i3) {
    const item = items[i3];
    let comment = null;
    if (isNode(item)) {
      if (item.spaceBefore)
        lines.push("");
      addCommentBefore(ctx, lines, item.commentBefore, false);
      if (item.comment)
        comment = item.comment;
    } else if (isPair(item)) {
      const ik = isNode(item.key) ? item.key : null;
      if (ik) {
        if (ik.spaceBefore)
          lines.push("");
        addCommentBefore(ctx, lines, ik.commentBefore, false);
        if (ik.comment)
          reqNewline = true;
      }
      const iv = isNode(item.value) ? item.value : null;
      if (iv) {
        if (iv.comment)
          comment = iv.comment;
        if (iv.commentBefore)
          reqNewline = true;
      } else if (item.value == null && ik?.comment) {
        comment = ik.comment;
      }
    }
    if (comment)
      reqNewline = true;
    let str = stringify(item, itemCtx, () => comment = null);
    reqNewline || (reqNewline = lines.length > linesAtValue || str.includes("\n"));
    if (i3 < items.length - 1) {
      str += ",";
    } else if (ctx.options.trailingComma) {
      if (ctx.options.lineWidth > 0) {
        reqNewline || (reqNewline = lines.reduce((sum, line) => sum + line.length + 2, 2) + (str.length + 2) > ctx.options.lineWidth);
      }
      if (reqNewline) {
        str += ",";
      }
    }
    if (comment)
      str += lineComment(str, itemIndent, commentString(comment));
    lines.push(str);
    linesAtValue = lines.length;
  }
  const { start, end } = flowChars;
  if (lines.length === 0) {
    return start + end;
  } else {
    if (!reqNewline) {
      const len = lines.reduce((sum, line) => sum + line.length + 2, 2);
      reqNewline = ctx.options.lineWidth > 0 && len > ctx.options.lineWidth;
    }
    if (reqNewline) {
      let str = start;
      for (const line of lines)
        str += line ? `
${indentStep}${indent}${line}` : "\n";
      return `${str}
${indent}${end}`;
    } else {
      return `${start}${fcPadding}${lines.join(" ")}${fcPadding}${end}`;
    }
  }
}
function addCommentBefore({ indent, options: { commentString } }, lines, comment, chompKeep) {
  if (comment && chompKeep)
    comment = comment.replace(/^\n+/, "");
  if (comment) {
    const ic = indentComment(commentString(comment), indent);
    lines.push(ic.trimStart());
  }
}

// node_modules/yaml/browser/dist/nodes/YAMLMap.js
function findPair(items, key) {
  const k2 = isScalar(key) ? key.value : key;
  for (const it of items) {
    if (isPair(it)) {
      if (it.key === key || it.key === k2)
        return it;
      if (isScalar(it.key) && it.key.value === k2)
        return it;
    }
  }
  return void 0;
}
var YAMLMap = class extends Collection {
  static get tagName() {
    return "tag:yaml.org,2002:map";
  }
  constructor(schema4) {
    super(MAP, schema4);
    this.items = [];
  }
  /**
   * A generic collection parsing method that can be extended
   * to other node classes that inherit from YAMLMap
   */
  static from(schema4, obj, ctx) {
    const { keepUndefined, replacer } = ctx;
    const map2 = new this(schema4);
    const add = (key, value) => {
      if (typeof replacer === "function")
        value = replacer.call(obj, key, value);
      else if (Array.isArray(replacer) && !replacer.includes(key))
        return;
      if (value !== void 0 || keepUndefined)
        map2.items.push(createPair(key, value, ctx));
    };
    if (obj instanceof Map) {
      for (const [key, value] of obj)
        add(key, value);
    } else if (obj && typeof obj === "object") {
      for (const key of Object.keys(obj))
        add(key, obj[key]);
    }
    if (typeof schema4.sortMapEntries === "function") {
      map2.items.sort(schema4.sortMapEntries);
    }
    return map2;
  }
  /**
   * Adds a value to the collection.
   *
   * @param overwrite - If not set `true`, using a key that is already in the
   *   collection will throw. Otherwise, overwrites the previous value.
   */
  add(pair, overwrite) {
    let _pair;
    if (isPair(pair))
      _pair = pair;
    else if (!pair || typeof pair !== "object" || !("key" in pair)) {
      _pair = new Pair(pair, pair?.value);
    } else
      _pair = new Pair(pair.key, pair.value);
    const prev = findPair(this.items, _pair.key);
    const sortEntries = this.schema?.sortMapEntries;
    if (prev) {
      if (!overwrite)
        throw new Error(`Key ${_pair.key} already set`);
      if (isScalar(prev.value) && isScalarValue(_pair.value))
        prev.value.value = _pair.value;
      else
        prev.value = _pair.value;
    } else if (sortEntries) {
      const i3 = this.items.findIndex((item) => sortEntries(_pair, item) < 0);
      if (i3 === -1)
        this.items.push(_pair);
      else
        this.items.splice(i3, 0, _pair);
    } else {
      this.items.push(_pair);
    }
  }
  delete(key) {
    const it = findPair(this.items, key);
    if (!it)
      return false;
    const del = this.items.splice(this.items.indexOf(it), 1);
    return del.length > 0;
  }
  get(key, keepScalar) {
    const it = findPair(this.items, key);
    const node = it?.value;
    return (!keepScalar && isScalar(node) ? node.value : node) ?? void 0;
  }
  has(key) {
    return !!findPair(this.items, key);
  }
  set(key, value) {
    this.add(new Pair(key, value), true);
  }
  /**
   * @param ctx - Conversion context, originally set in Document#toJS()
   * @param {Class} Type - If set, forces the returned collection type
   * @returns Instance of Type, Map, or Object
   */
  toJSON(_2, ctx, Type) {
    const map2 = Type ? new Type() : ctx?.mapAsMap ? /* @__PURE__ */ new Map() : {};
    if (ctx?.onCreate)
      ctx.onCreate(map2);
    for (const item of this.items)
      addPairToJSMap(ctx, map2, item);
    return map2;
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    for (const item of this.items) {
      if (!isPair(item))
        throw new Error(`Map items must all be pairs; found ${JSON.stringify(item)} instead`);
    }
    if (!ctx.allNullValues && this.hasAllNullValues(false))
      ctx = Object.assign({}, ctx, { allNullValues: true });
    return stringifyCollection(this, ctx, {
      blockItemPrefix: "",
      flowChars: { start: "{", end: "}" },
      itemIndent: ctx.indent || "",
      onChompKeep,
      onComment
    });
  }
};

// node_modules/yaml/browser/dist/schema/common/map.js
var map = {
  collection: "map",
  default: true,
  nodeClass: YAMLMap,
  tag: "tag:yaml.org,2002:map",
  resolve(map2, onError) {
    if (!isMap(map2))
      onError("Expected a mapping for this tag");
    return map2;
  },
  createNode: (schema4, obj, ctx) => YAMLMap.from(schema4, obj, ctx)
};

// node_modules/yaml/browser/dist/nodes/YAMLSeq.js
var YAMLSeq = class extends Collection {
  static get tagName() {
    return "tag:yaml.org,2002:seq";
  }
  constructor(schema4) {
    super(SEQ, schema4);
    this.items = [];
  }
  add(value) {
    this.items.push(value);
  }
  /**
   * Removes a value from the collection.
   *
   * `key` must contain a representation of an integer for this to succeed.
   * It may be wrapped in a `Scalar`.
   *
   * @returns `true` if the item was found and removed.
   */
  delete(key) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      return false;
    const del = this.items.splice(idx, 1);
    return del.length > 0;
  }
  get(key, keepScalar) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      return void 0;
    const it = this.items[idx];
    return !keepScalar && isScalar(it) ? it.value : it;
  }
  /**
   * Checks if the collection includes a value with the key `key`.
   *
   * `key` must contain a representation of an integer for this to succeed.
   * It may be wrapped in a `Scalar`.
   */
  has(key) {
    const idx = asItemIndex(key);
    return typeof idx === "number" && idx < this.items.length;
  }
  /**
   * Sets a value in this collection. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   *
   * If `key` does not contain a representation of an integer, this will throw.
   * It may be wrapped in a `Scalar`.
   */
  set(key, value) {
    const idx = asItemIndex(key);
    if (typeof idx !== "number")
      throw new Error(`Expected a valid index, not ${key}.`);
    const prev = this.items[idx];
    if (isScalar(prev) && isScalarValue(value))
      prev.value = value;
    else
      this.items[idx] = value;
  }
  toJSON(_2, ctx) {
    const seq2 = [];
    if (ctx?.onCreate)
      ctx.onCreate(seq2);
    let i3 = 0;
    for (const item of this.items)
      seq2.push(toJS(item, String(i3++), ctx));
    return seq2;
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    return stringifyCollection(this, ctx, {
      blockItemPrefix: "- ",
      flowChars: { start: "[", end: "]" },
      itemIndent: (ctx.indent || "") + "  ",
      onChompKeep,
      onComment
    });
  }
  static from(schema4, obj, ctx) {
    const { replacer } = ctx;
    const seq2 = new this(schema4);
    if (obj && Symbol.iterator in Object(obj)) {
      let i3 = 0;
      for (let it of obj) {
        if (typeof replacer === "function") {
          const key = obj instanceof Set ? it : String(i3++);
          it = replacer.call(obj, key, it);
        }
        seq2.items.push(createNode(it, void 0, ctx));
      }
    }
    return seq2;
  }
};
function asItemIndex(key) {
  let idx = isScalar(key) ? key.value : key;
  if (idx && typeof idx === "string")
    idx = Number(idx);
  return typeof idx === "number" && Number.isInteger(idx) && idx >= 0 ? idx : null;
}

// node_modules/yaml/browser/dist/schema/common/seq.js
var seq = {
  collection: "seq",
  default: true,
  nodeClass: YAMLSeq,
  tag: "tag:yaml.org,2002:seq",
  resolve(seq2, onError) {
    if (!isSeq(seq2))
      onError("Expected a sequence for this tag");
    return seq2;
  },
  createNode: (schema4, obj, ctx) => YAMLSeq.from(schema4, obj, ctx)
};

// node_modules/yaml/browser/dist/schema/common/string.js
var string = {
  identify: (value) => typeof value === "string",
  default: true,
  tag: "tag:yaml.org,2002:str",
  resolve: (str) => str,
  stringify(item, ctx, onComment, onChompKeep) {
    ctx = Object.assign({ actualString: true }, ctx);
    return stringifyString(item, ctx, onComment, onChompKeep);
  }
};

// node_modules/yaml/browser/dist/schema/common/null.js
var nullTag = {
  identify: (value) => value == null,
  createNode: () => new Scalar(null),
  default: true,
  tag: "tag:yaml.org,2002:null",
  test: /^(?:~|[Nn]ull|NULL)?$/,
  resolve: () => new Scalar(null),
  stringify: ({ source }, ctx) => typeof source === "string" && nullTag.test.test(source) ? source : ctx.options.nullStr
};

// node_modules/yaml/browser/dist/schema/core/bool.js
var boolTag = {
  identify: (value) => typeof value === "boolean",
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/,
  resolve: (str) => new Scalar(str[0] === "t" || str[0] === "T"),
  stringify({ source, value }, ctx) {
    if (source && boolTag.test.test(source)) {
      const sv = source[0] === "t" || source[0] === "T";
      if (value === sv)
        return source;
    }
    return value ? ctx.options.trueStr : ctx.options.falseStr;
  }
};

// node_modules/yaml/browser/dist/stringify/stringifyNumber.js
function stringifyNumber({ format, minFractionDigits, tag, value }) {
  if (typeof value === "bigint")
    return String(value);
  const num = typeof value === "number" ? value : Number(value);
  if (!isFinite(num))
    return isNaN(num) ? ".nan" : num < 0 ? "-.inf" : ".inf";
  let n2 = Object.is(value, -0) ? "-0" : JSON.stringify(value);
  if (!format && minFractionDigits && (!tag || tag === "tag:yaml.org,2002:float") && /^\d/.test(n2)) {
    let i3 = n2.indexOf(".");
    if (i3 < 0) {
      i3 = n2.length;
      n2 += ".";
    }
    let d3 = minFractionDigits - (n2.length - i3 - 1);
    while (d3-- > 0)
      n2 += "0";
  }
  return n2;
}

// node_modules/yaml/browser/dist/schema/core/float.js
var floatNaN = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: stringifyNumber
};
var floatExp = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/,
  resolve: (str) => parseFloat(str),
  stringify(node) {
    const num = Number(node.value);
    return isFinite(num) ? num.toExponential() : stringifyNumber(node);
  }
};
var float = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$/,
  resolve(str) {
    const node = new Scalar(parseFloat(str));
    const dot = str.indexOf(".");
    if (dot !== -1 && str[str.length - 1] === "0")
      node.minFractionDigits = str.length - dot - 1;
    return node;
  },
  stringify: stringifyNumber
};

// node_modules/yaml/browser/dist/schema/core/int.js
var intIdentify = (value) => typeof value === "bigint" || Number.isInteger(value);
var intResolve = (str, offset, radix, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str.substring(offset), radix);
function intStringify(node, radix, prefix) {
  const { value } = node;
  if (intIdentify(value) && value >= 0)
    return prefix + value.toString(radix);
  return stringifyNumber(node);
}
var intOct = {
  identify: (value) => intIdentify(value) && value >= 0,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^0o[0-7]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 2, 8, opt),
  stringify: (node) => intStringify(node, 8, "0o")
};
var int = {
  identify: intIdentify,
  default: true,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 0, 10, opt),
  stringify: stringifyNumber
};
var intHex = {
  identify: (value) => intIdentify(value) && value >= 0,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^0x[0-9a-fA-F]+$/,
  resolve: (str, _onError, opt) => intResolve(str, 2, 16, opt),
  stringify: (node) => intStringify(node, 16, "0x")
};

// node_modules/yaml/browser/dist/schema/core/schema.js
var schema = [
  map,
  seq,
  string,
  nullTag,
  boolTag,
  intOct,
  int,
  intHex,
  floatNaN,
  floatExp,
  float
];

// node_modules/yaml/browser/dist/schema/json/schema.js
function intIdentify2(value) {
  return typeof value === "bigint" || Number.isInteger(value);
}
var stringifyJSON = ({ value }) => JSON.stringify(value);
var jsonScalars = [
  {
    identify: (value) => typeof value === "string",
    default: true,
    tag: "tag:yaml.org,2002:str",
    resolve: (str) => str,
    stringify: stringifyJSON
  },
  {
    identify: (value) => value == null,
    createNode: () => new Scalar(null),
    default: true,
    tag: "tag:yaml.org,2002:null",
    test: /^null$/,
    resolve: () => null,
    stringify: stringifyJSON
  },
  {
    identify: (value) => typeof value === "boolean",
    default: true,
    tag: "tag:yaml.org,2002:bool",
    test: /^true$|^false$/,
    resolve: (str) => str === "true",
    stringify: stringifyJSON
  },
  {
    identify: intIdentify2,
    default: true,
    tag: "tag:yaml.org,2002:int",
    test: /^-?(?:0|[1-9][0-9]*)$/,
    resolve: (str, _onError, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str, 10),
    stringify: ({ value }) => intIdentify2(value) ? value.toString() : JSON.stringify(value)
  },
  {
    identify: (value) => typeof value === "number",
    default: true,
    tag: "tag:yaml.org,2002:float",
    test: /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?$/,
    resolve: (str) => parseFloat(str),
    stringify: stringifyJSON
  }
];
var jsonError = {
  default: true,
  tag: "",
  test: /^/,
  resolve(str, onError) {
    onError(`Unresolved plain scalar ${JSON.stringify(str)}`);
    return str;
  }
};
var schema2 = [map, seq].concat(jsonScalars, jsonError);

// node_modules/yaml/browser/dist/schema/yaml-1.1/binary.js
var binary = {
  identify: (value) => value instanceof Uint8Array,
  // Buffer inherits from Uint8Array
  default: false,
  tag: "tag:yaml.org,2002:binary",
  /**
   * Returns a Buffer in node and an Uint8Array in browsers
   *
   * To use the resulting buffer as an image, you'll want to do something like:
   *
   *   const blob = new Blob([buffer], { type: 'image/jpeg' })
   *   document.querySelector('#photo').src = URL.createObjectURL(blob)
   */
  resolve(src, onError) {
    if (typeof atob === "function") {
      const str = atob(src.replace(/[\n\r]/g, ""));
      const buffer = new Uint8Array(str.length);
      for (let i3 = 0; i3 < str.length; ++i3)
        buffer[i3] = str.charCodeAt(i3);
      return buffer;
    } else {
      onError("This environment does not support reading binary tags; either Buffer or atob is required");
      return src;
    }
  },
  stringify({ comment, type, value }, ctx, onComment, onChompKeep) {
    if (!value)
      return "";
    const buf = value;
    let str;
    if (typeof btoa === "function") {
      let s3 = "";
      for (let i3 = 0; i3 < buf.length; ++i3)
        s3 += String.fromCharCode(buf[i3]);
      str = btoa(s3);
    } else {
      throw new Error("This environment does not support writing binary tags; either Buffer or btoa is required");
    }
    type ?? (type = Scalar.BLOCK_LITERAL);
    if (type !== Scalar.QUOTE_DOUBLE) {
      const lineWidth = Math.max(ctx.options.lineWidth - ctx.indent.length, ctx.options.minContentWidth);
      const n2 = Math.ceil(str.length / lineWidth);
      const lines = new Array(n2);
      for (let i3 = 0, o2 = 0; i3 < n2; ++i3, o2 += lineWidth) {
        lines[i3] = str.substr(o2, lineWidth);
      }
      str = lines.join(type === Scalar.BLOCK_LITERAL ? "\n" : " ");
    }
    return stringifyString({ comment, type, value: str }, ctx, onComment, onChompKeep);
  }
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/pairs.js
function resolvePairs(seq2, onError) {
  if (isSeq(seq2)) {
    for (let i3 = 0; i3 < seq2.items.length; ++i3) {
      let item = seq2.items[i3];
      if (isPair(item))
        continue;
      else if (isMap(item)) {
        if (item.items.length > 1)
          onError("Each pair must have its own sequence indicator");
        const pair = item.items[0] || new Pair(new Scalar(null));
        if (item.commentBefore)
          pair.key.commentBefore = pair.key.commentBefore ? `${item.commentBefore}
${pair.key.commentBefore}` : item.commentBefore;
        if (item.comment) {
          const cn = pair.value ?? pair.key;
          cn.comment = cn.comment ? `${item.comment}
${cn.comment}` : item.comment;
        }
        item = pair;
      }
      seq2.items[i3] = isPair(item) ? item : new Pair(item);
    }
  } else
    onError("Expected a sequence for this tag");
  return seq2;
}
function createPairs(schema4, iterable, ctx) {
  const { replacer } = ctx;
  const pairs2 = new YAMLSeq(schema4);
  pairs2.tag = "tag:yaml.org,2002:pairs";
  let i3 = 0;
  if (iterable && Symbol.iterator in Object(iterable))
    for (let it of iterable) {
      if (typeof replacer === "function")
        it = replacer.call(iterable, String(i3++), it);
      let key, value;
      if (Array.isArray(it)) {
        if (it.length === 2) {
          key = it[0];
          value = it[1];
        } else
          throw new TypeError(`Expected [key, value] tuple: ${it}`);
      } else if (it && it instanceof Object) {
        const keys = Object.keys(it);
        if (keys.length === 1) {
          key = keys[0];
          value = it[key];
        } else {
          throw new TypeError(`Expected tuple with one key, not ${keys.length} keys`);
        }
      } else {
        key = it;
      }
      pairs2.items.push(createPair(key, value, ctx));
    }
  return pairs2;
}
var pairs = {
  collection: "seq",
  default: false,
  tag: "tag:yaml.org,2002:pairs",
  resolve: resolvePairs,
  createNode: createPairs
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/omap.js
var YAMLOMap = class _YAMLOMap extends YAMLSeq {
  constructor() {
    super();
    this.add = YAMLMap.prototype.add.bind(this);
    this.delete = YAMLMap.prototype.delete.bind(this);
    this.get = YAMLMap.prototype.get.bind(this);
    this.has = YAMLMap.prototype.has.bind(this);
    this.set = YAMLMap.prototype.set.bind(this);
    this.tag = _YAMLOMap.tag;
  }
  /**
   * If `ctx` is given, the return type is actually `Map<unknown, unknown>`,
   * but TypeScript won't allow widening the signature of a child method.
   */
  toJSON(_2, ctx) {
    if (!ctx)
      return super.toJSON(_2);
    const map2 = /* @__PURE__ */ new Map();
    if (ctx?.onCreate)
      ctx.onCreate(map2);
    for (const pair of this.items) {
      let key, value;
      if (isPair(pair)) {
        key = toJS(pair.key, "", ctx);
        value = toJS(pair.value, key, ctx);
      } else {
        key = toJS(pair, "", ctx);
      }
      if (map2.has(key))
        throw new Error("Ordered maps must not include duplicate keys");
      map2.set(key, value);
    }
    return map2;
  }
  static from(schema4, iterable, ctx) {
    const pairs2 = createPairs(schema4, iterable, ctx);
    const omap2 = new this();
    omap2.items = pairs2.items;
    return omap2;
  }
};
YAMLOMap.tag = "tag:yaml.org,2002:omap";
var omap = {
  collection: "seq",
  identify: (value) => value instanceof Map,
  nodeClass: YAMLOMap,
  default: false,
  tag: "tag:yaml.org,2002:omap",
  resolve(seq2, onError) {
    const pairs2 = resolvePairs(seq2, onError);
    const seenKeys = [];
    for (const { key } of pairs2.items) {
      if (isScalar(key)) {
        if (seenKeys.includes(key.value)) {
          onError(`Ordered maps must not include duplicate keys: ${key.value}`);
        } else {
          seenKeys.push(key.value);
        }
      }
    }
    return Object.assign(new YAMLOMap(), pairs2);
  },
  createNode: (schema4, iterable, ctx) => YAMLOMap.from(schema4, iterable, ctx)
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/bool.js
function boolStringify({ value, source }, ctx) {
  const boolObj = value ? trueTag : falseTag;
  if (source && boolObj.test.test(source))
    return source;
  return value ? ctx.options.trueStr : ctx.options.falseStr;
}
var trueTag = {
  identify: (value) => value === true,
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:Y|y|[Yy]es|YES|[Tt]rue|TRUE|[Oo]n|ON)$/,
  resolve: () => new Scalar(true),
  stringify: boolStringify
};
var falseTag = {
  identify: (value) => value === false,
  default: true,
  tag: "tag:yaml.org,2002:bool",
  test: /^(?:N|n|[Nn]o|NO|[Ff]alse|FALSE|[Oo]ff|OFF)$/,
  resolve: () => new Scalar(false),
  stringify: boolStringify
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/float.js
var floatNaN2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
  resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
  stringify: stringifyNumber
};
var floatExp2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "EXP",
  test: /^[-+]?(?:[0-9][0-9_]*)?(?:\.[0-9_]*)?[eE][-+]?[0-9]+$/,
  resolve: (str) => parseFloat(str.replace(/_/g, "")),
  stringify(node) {
    const num = Number(node.value);
    return isFinite(num) ? num.toExponential() : stringifyNumber(node);
  }
};
var float2 = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  test: /^[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*$/,
  resolve(str) {
    const node = new Scalar(parseFloat(str.replace(/_/g, "")));
    const dot = str.indexOf(".");
    if (dot !== -1) {
      const f3 = str.substring(dot + 1).replace(/_/g, "");
      if (f3[f3.length - 1] === "0")
        node.minFractionDigits = f3.length;
    }
    return node;
  },
  stringify: stringifyNumber
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/int.js
var intIdentify3 = (value) => typeof value === "bigint" || Number.isInteger(value);
function intResolve2(str, offset, radix, { intAsBigInt }) {
  const sign = str[0];
  if (sign === "-" || sign === "+")
    offset += 1;
  str = str.substring(offset).replace(/_/g, "");
  if (intAsBigInt) {
    switch (radix) {
      case 2:
        str = `0b${str}`;
        break;
      case 8:
        str = `0o${str}`;
        break;
      case 16:
        str = `0x${str}`;
        break;
    }
    const n3 = BigInt(str);
    return sign === "-" ? BigInt(-1) * n3 : n3;
  }
  const n2 = parseInt(str, radix);
  return sign === "-" ? -1 * n2 : n2;
}
function intStringify2(node, radix, prefix) {
  const { value } = node;
  if (intIdentify3(value)) {
    const str = value.toString(radix);
    return value < 0 ? "-" + prefix + str.substr(1) : prefix + str;
  }
  return stringifyNumber(node);
}
var intBin = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "BIN",
  test: /^[-+]?0b[0-1_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 2, 2, opt),
  stringify: (node) => intStringify2(node, 2, "0b")
};
var intOct2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "OCT",
  test: /^[-+]?0[0-7_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 1, 8, opt),
  stringify: (node) => intStringify2(node, 8, "0")
};
var int2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  test: /^[-+]?[0-9][0-9_]*$/,
  resolve: (str, _onError, opt) => intResolve2(str, 0, 10, opt),
  stringify: stringifyNumber
};
var intHex2 = {
  identify: intIdentify3,
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "HEX",
  test: /^[-+]?0x[0-9a-fA-F_]+$/,
  resolve: (str, _onError, opt) => intResolve2(str, 2, 16, opt),
  stringify: (node) => intStringify2(node, 16, "0x")
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/set.js
var YAMLSet = class _YAMLSet extends YAMLMap {
  constructor(schema4) {
    super(schema4);
    this.tag = _YAMLSet.tag;
  }
  add(key) {
    let pair;
    if (isPair(key))
      pair = key;
    else if (key && typeof key === "object" && "key" in key && "value" in key && key.value === null)
      pair = new Pair(key.key, null);
    else
      pair = new Pair(key, null);
    const prev = findPair(this.items, pair.key);
    if (!prev)
      this.items.push(pair);
  }
  /**
   * If `keepPair` is `true`, returns the Pair matching `key`.
   * Otherwise, returns the value of that Pair's key.
   */
  get(key, keepPair) {
    const pair = findPair(this.items, key);
    return !keepPair && isPair(pair) ? isScalar(pair.key) ? pair.key.value : pair.key : pair;
  }
  set(key, value) {
    if (typeof value !== "boolean")
      throw new Error(`Expected boolean value for set(key, value) in a YAML set, not ${typeof value}`);
    const prev = findPair(this.items, key);
    if (prev && !value) {
      this.items.splice(this.items.indexOf(prev), 1);
    } else if (!prev && value) {
      this.items.push(new Pair(key));
    }
  }
  toJSON(_2, ctx) {
    return super.toJSON(_2, ctx, Set);
  }
  toString(ctx, onComment, onChompKeep) {
    if (!ctx)
      return JSON.stringify(this);
    if (this.hasAllNullValues(true))
      return super.toString(Object.assign({}, ctx, { allNullValues: true }), onComment, onChompKeep);
    else
      throw new Error("Set items must all have null values");
  }
  static from(schema4, iterable, ctx) {
    const { replacer } = ctx;
    const set2 = new this(schema4);
    if (iterable && Symbol.iterator in Object(iterable))
      for (let value of iterable) {
        if (typeof replacer === "function")
          value = replacer.call(iterable, value, value);
        set2.items.push(createPair(value, null, ctx));
      }
    return set2;
  }
};
YAMLSet.tag = "tag:yaml.org,2002:set";
var set = {
  collection: "map",
  identify: (value) => value instanceof Set,
  nodeClass: YAMLSet,
  default: false,
  tag: "tag:yaml.org,2002:set",
  createNode: (schema4, iterable, ctx) => YAMLSet.from(schema4, iterable, ctx),
  resolve(map2, onError) {
    if (isMap(map2)) {
      if (map2.hasAllNullValues(true))
        return Object.assign(new YAMLSet(), map2);
      else
        onError("Set items must all have null values");
    } else
      onError("Expected a mapping for this tag");
    return map2;
  }
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/timestamp.js
function parseSexagesimal(str, asBigInt) {
  const sign = str[0];
  const parts = sign === "-" || sign === "+" ? str.substring(1) : str;
  const num = (n2) => asBigInt ? BigInt(n2) : Number(n2);
  const res = parts.replace(/_/g, "").split(":").reduce((res2, p2) => res2 * num(60) + num(p2), num(0));
  return sign === "-" ? num(-1) * res : res;
}
function stringifySexagesimal(node) {
  let { value } = node;
  let num = (n2) => n2;
  if (typeof value === "bigint")
    num = (n2) => BigInt(n2);
  else if (isNaN(value) || !isFinite(value))
    return stringifyNumber(node);
  let sign = "";
  if (value < 0) {
    sign = "-";
    value *= num(-1);
  }
  const _60 = num(60);
  const parts = [value % _60];
  if (value < 60) {
    parts.unshift(0);
  } else {
    value = (value - parts[0]) / _60;
    parts.unshift(value % _60);
    if (value >= 60) {
      value = (value - parts[0]) / _60;
      parts.unshift(value);
    }
  }
  return sign + parts.map((n2) => String(n2).padStart(2, "0")).join(":").replace(/000000\d*$/, "");
}
var intTime = {
  identify: (value) => typeof value === "bigint" || Number.isInteger(value),
  default: true,
  tag: "tag:yaml.org,2002:int",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+$/,
  resolve: (str, _onError, { intAsBigInt }) => parseSexagesimal(str, intAsBigInt),
  stringify: stringifySexagesimal
};
var floatTime = {
  identify: (value) => typeof value === "number",
  default: true,
  tag: "tag:yaml.org,2002:float",
  format: "TIME",
  test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*$/,
  resolve: (str) => parseSexagesimal(str, false),
  stringify: stringifySexagesimal
};
var timestamp = {
  identify: (value) => value instanceof Date,
  default: true,
  tag: "tag:yaml.org,2002:timestamp",
  // If the time zone is omitted, the timestamp is assumed to be specified in UTC. The time part
  // may be omitted altogether, resulting in a date format. In such a case, the time part is
  // assumed to be 00:00:00Z (start of day, UTC).
  test: RegExp("^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:(?:t|T|[ \\t]+)([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}(\\.[0-9]+)?)(?:[ \\t]*(Z|[-+][012]?[0-9](?::[0-9]{2})?))?)?$"),
  resolve(str) {
    const match = str.match(timestamp.test);
    if (!match)
      throw new Error("!!timestamp expects a date, starting with yyyy-mm-dd");
    const [, year, month, day, hour, minute, second] = match.map(Number);
    const millisec = match[7] ? Number((match[7] + "00").substr(1, 3)) : 0;
    let date = Date.UTC(year, month - 1, day, hour || 0, minute || 0, second || 0, millisec);
    const tz = match[8];
    if (tz && tz !== "Z") {
      let d3 = parseSexagesimal(tz, false);
      if (Math.abs(d3) < 30)
        d3 *= 60;
      date -= 6e4 * d3;
    }
    return new Date(date);
  },
  stringify: ({ value }) => value?.toISOString().replace(/(T00:00:00)?\.000Z$/, "") ?? ""
};

// node_modules/yaml/browser/dist/schema/yaml-1.1/schema.js
var schema3 = [
  map,
  seq,
  string,
  nullTag,
  trueTag,
  falseTag,
  intBin,
  intOct2,
  int2,
  intHex2,
  floatNaN2,
  floatExp2,
  float2,
  binary,
  merge,
  omap,
  pairs,
  set,
  intTime,
  floatTime,
  timestamp
];

// node_modules/yaml/browser/dist/schema/tags.js
var schemas = /* @__PURE__ */ new Map([
  ["core", schema],
  ["failsafe", [map, seq, string]],
  ["json", schema2],
  ["yaml11", schema3],
  ["yaml-1.1", schema3]
]);
var tagsByName = {
  binary,
  bool: boolTag,
  float,
  floatExp,
  floatNaN,
  floatTime,
  int,
  intHex,
  intOct,
  intTime,
  map,
  merge,
  null: nullTag,
  omap,
  pairs,
  seq,
  set,
  timestamp
};
var coreKnownTags = {
  "tag:yaml.org,2002:binary": binary,
  "tag:yaml.org,2002:merge": merge,
  "tag:yaml.org,2002:omap": omap,
  "tag:yaml.org,2002:pairs": pairs,
  "tag:yaml.org,2002:set": set,
  "tag:yaml.org,2002:timestamp": timestamp
};
function getTags(customTags, schemaName, addMergeTag) {
  const schemaTags = schemas.get(schemaName);
  if (schemaTags && !customTags) {
    return addMergeTag && !schemaTags.includes(merge) ? schemaTags.concat(merge) : schemaTags.slice();
  }
  let tags = schemaTags;
  if (!tags) {
    if (Array.isArray(customTags))
      tags = [];
    else {
      const keys = Array.from(schemas.keys()).filter((key) => key !== "yaml11").map((key) => JSON.stringify(key)).join(", ");
      throw new Error(`Unknown schema "${schemaName}"; use one of ${keys} or define customTags array`);
    }
  }
  if (Array.isArray(customTags)) {
    for (const tag of customTags)
      tags = tags.concat(tag);
  } else if (typeof customTags === "function") {
    tags = customTags(tags.slice());
  }
  if (addMergeTag)
    tags = tags.concat(merge);
  return tags.reduce((tags2, tag) => {
    const tagObj = typeof tag === "string" ? tagsByName[tag] : tag;
    if (!tagObj) {
      const tagName = JSON.stringify(tag);
      const keys = Object.keys(tagsByName).map((key) => JSON.stringify(key)).join(", ");
      throw new Error(`Unknown custom tag ${tagName}; use one of ${keys}`);
    }
    if (!tags2.includes(tagObj))
      tags2.push(tagObj);
    return tags2;
  }, []);
}

// node_modules/yaml/browser/dist/schema/Schema.js
var sortMapEntriesByKey = (a3, b2) => a3.key < b2.key ? -1 : a3.key > b2.key ? 1 : 0;
var Schema = class _Schema {
  constructor({ compat, customTags, merge: merge2, resolveKnownTags, schema: schema4, sortMapEntries, toStringDefaults }) {
    this.compat = Array.isArray(compat) ? getTags(compat, "compat") : compat ? getTags(null, compat) : null;
    this.name = typeof schema4 === "string" && schema4 || "core";
    this.knownTags = resolveKnownTags ? coreKnownTags : {};
    this.tags = getTags(customTags, this.name, merge2);
    this.toStringOptions = toStringDefaults ?? null;
    Object.defineProperty(this, MAP, { value: map });
    Object.defineProperty(this, SCALAR, { value: string });
    Object.defineProperty(this, SEQ, { value: seq });
    this.sortMapEntries = typeof sortMapEntries === "function" ? sortMapEntries : sortMapEntries === true ? sortMapEntriesByKey : null;
  }
  clone() {
    const copy = Object.create(_Schema.prototype, Object.getOwnPropertyDescriptors(this));
    copy.tags = this.tags.slice();
    return copy;
  }
};

// node_modules/yaml/browser/dist/stringify/stringifyDocument.js
function stringifyDocument(doc, options) {
  const lines = [];
  let hasDirectives = options.directives === true;
  if (options.directives !== false && doc.directives) {
    const dir = doc.directives.toString(doc);
    if (dir) {
      lines.push(dir);
      hasDirectives = true;
    } else if (doc.directives.docStart)
      hasDirectives = true;
  }
  if (hasDirectives)
    lines.push("---");
  const ctx = createStringifyContext(doc, options);
  const { commentString } = ctx.options;
  if (doc.commentBefore) {
    if (lines.length !== 1)
      lines.unshift("");
    const cs = commentString(doc.commentBefore);
    lines.unshift(indentComment(cs, ""));
  }
  let chompKeep = false;
  let contentComment = null;
  if (doc.contents) {
    if (isNode(doc.contents)) {
      if (doc.contents.spaceBefore && hasDirectives)
        lines.push("");
      if (doc.contents.commentBefore) {
        const cs = commentString(doc.contents.commentBefore);
        lines.push(indentComment(cs, ""));
      }
      ctx.forceBlockIndent = !!doc.comment;
      contentComment = doc.contents.comment;
    }
    const onChompKeep = contentComment ? void 0 : () => chompKeep = true;
    let body = stringify(doc.contents, ctx, () => contentComment = null, onChompKeep);
    if (contentComment)
      body += lineComment(body, "", commentString(contentComment));
    if ((body[0] === "|" || body[0] === ">") && lines[lines.length - 1] === "---") {
      lines[lines.length - 1] = `--- ${body}`;
    } else
      lines.push(body);
  } else {
    lines.push(stringify(doc.contents, ctx));
  }
  if (doc.directives?.docEnd) {
    if (doc.comment) {
      const cs = commentString(doc.comment);
      if (cs.includes("\n")) {
        lines.push("...");
        lines.push(indentComment(cs, ""));
      } else {
        lines.push(`... ${cs}`);
      }
    } else {
      lines.push("...");
    }
  } else {
    let dc = doc.comment;
    if (dc && chompKeep)
      dc = dc.replace(/^\n+/, "");
    if (dc) {
      if ((!chompKeep || contentComment) && lines[lines.length - 1] !== "")
        lines.push("");
      lines.push(indentComment(commentString(dc), ""));
    }
  }
  return lines.join("\n") + "\n";
}

// node_modules/yaml/browser/dist/doc/Document.js
var Document = class _Document {
  constructor(value, replacer, options) {
    this.commentBefore = null;
    this.comment = null;
    this.errors = [];
    this.warnings = [];
    Object.defineProperty(this, NODE_TYPE, { value: DOC });
    let _replacer = null;
    if (typeof replacer === "function" || Array.isArray(replacer)) {
      _replacer = replacer;
    } else if (options === void 0 && replacer) {
      options = replacer;
      replacer = void 0;
    }
    const opt = Object.assign({
      intAsBigInt: false,
      keepSourceTokens: false,
      logLevel: "warn",
      prettyErrors: true,
      strict: true,
      stringKeys: false,
      uniqueKeys: true,
      version: "1.2"
    }, options);
    this.options = opt;
    let { version } = opt;
    if (options?._directives) {
      this.directives = options._directives.atDocument();
      if (this.directives.yaml.explicit)
        version = this.directives.yaml.version;
    } else
      this.directives = new Directives({ version });
    this.setSchema(version, options);
    this.contents = value === void 0 ? null : this.createNode(value, _replacer, options);
  }
  /**
   * Create a deep copy of this Document and its contents.
   *
   * Custom Node values that inherit from `Object` still refer to their original instances.
   */
  clone() {
    const copy = Object.create(_Document.prototype, {
      [NODE_TYPE]: { value: DOC }
    });
    copy.commentBefore = this.commentBefore;
    copy.comment = this.comment;
    copy.errors = this.errors.slice();
    copy.warnings = this.warnings.slice();
    copy.options = Object.assign({}, this.options);
    if (this.directives)
      copy.directives = this.directives.clone();
    copy.schema = this.schema.clone();
    copy.contents = isNode(this.contents) ? this.contents.clone(copy.schema) : this.contents;
    if (this.range)
      copy.range = this.range.slice();
    return copy;
  }
  /** Adds a value to the document. */
  add(value) {
    if (assertCollection(this.contents))
      this.contents.add(value);
  }
  /** Adds a value to the document. */
  addIn(path, value) {
    if (assertCollection(this.contents))
      this.contents.addIn(path, value);
  }
  /**
   * Create a new `Alias` node, ensuring that the target `node` has the required anchor.
   *
   * If `node` already has an anchor, `name` is ignored.
   * Otherwise, the `node.anchor` value will be set to `name`,
   * or if an anchor with that name is already present in the document,
   * `name` will be used as a prefix for a new unique anchor.
   * If `name` is undefined, the generated anchor will use 'a' as a prefix.
   */
  createAlias(node, name) {
    if (!node.anchor) {
      const prev = anchorNames(this);
      node.anchor = // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
      !name || prev.has(name) ? findNewAnchor(name || "a", prev) : name;
    }
    return new Alias(node.anchor);
  }
  createNode(value, replacer, options) {
    let _replacer = void 0;
    if (typeof replacer === "function") {
      value = replacer.call({ "": value }, "", value);
      _replacer = replacer;
    } else if (Array.isArray(replacer)) {
      const keyToStr = (v3) => typeof v3 === "number" || v3 instanceof String || v3 instanceof Number;
      const asStr = replacer.filter(keyToStr).map(String);
      if (asStr.length > 0)
        replacer = replacer.concat(asStr);
      _replacer = replacer;
    } else if (options === void 0 && replacer) {
      options = replacer;
      replacer = void 0;
    }
    const { aliasDuplicateObjects, anchorPrefix, flow, keepUndefined, onTagObj, tag } = options ?? {};
    const { onAnchor, setAnchors, sourceObjects } = createNodeAnchors(
      this,
      // eslint-disable-next-line @typescript-eslint/prefer-nullish-coalescing
      anchorPrefix || "a"
    );
    const ctx = {
      aliasDuplicateObjects: aliasDuplicateObjects ?? true,
      keepUndefined: keepUndefined ?? false,
      onAnchor,
      onTagObj,
      replacer: _replacer,
      schema: this.schema,
      sourceObjects
    };
    const node = createNode(value, tag, ctx);
    if (flow && isCollection(node))
      node.flow = true;
    setAnchors();
    return node;
  }
  /**
   * Convert a key and a value into a `Pair` using the current schema,
   * recursively wrapping all values as `Scalar` or `Collection` nodes.
   */
  createPair(key, value, options = {}) {
    const k2 = this.createNode(key, null, options);
    const v3 = this.createNode(value, null, options);
    return new Pair(k2, v3);
  }
  /**
   * Removes a value from the document.
   * @returns `true` if the item was found and removed.
   */
  delete(key) {
    return assertCollection(this.contents) ? this.contents.delete(key) : false;
  }
  /**
   * Removes a value from the document.
   * @returns `true` if the item was found and removed.
   */
  deleteIn(path) {
    if (isEmptyPath(path)) {
      if (this.contents == null)
        return false;
      this.contents = null;
      return true;
    }
    return assertCollection(this.contents) ? this.contents.deleteIn(path) : false;
  }
  /**
   * Returns item at `key`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  get(key, keepScalar) {
    return isCollection(this.contents) ? this.contents.get(key, keepScalar) : void 0;
  }
  /**
   * Returns item at `path`, or `undefined` if not found. By default unwraps
   * scalar values from their surrounding node; to disable set `keepScalar` to
   * `true` (collections are always returned intact).
   */
  getIn(path, keepScalar) {
    if (isEmptyPath(path))
      return !keepScalar && isScalar(this.contents) ? this.contents.value : this.contents;
    return isCollection(this.contents) ? this.contents.getIn(path, keepScalar) : void 0;
  }
  /**
   * Checks if the document includes a value with the key `key`.
   */
  has(key) {
    return isCollection(this.contents) ? this.contents.has(key) : false;
  }
  /**
   * Checks if the document includes a value at `path`.
   */
  hasIn(path) {
    if (isEmptyPath(path))
      return this.contents !== void 0;
    return isCollection(this.contents) ? this.contents.hasIn(path) : false;
  }
  /**
   * Sets a value in this document. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  set(key, value) {
    if (this.contents == null) {
      this.contents = collectionFromPath(this.schema, [key], value);
    } else if (assertCollection(this.contents)) {
      this.contents.set(key, value);
    }
  }
  /**
   * Sets a value in this document. For `!!set`, `value` needs to be a
   * boolean to add/remove the item from the set.
   */
  setIn(path, value) {
    if (isEmptyPath(path)) {
      this.contents = value;
    } else if (this.contents == null) {
      this.contents = collectionFromPath(this.schema, Array.from(path), value);
    } else if (assertCollection(this.contents)) {
      this.contents.setIn(path, value);
    }
  }
  /**
   * Change the YAML version and schema used by the document.
   * A `null` version disables support for directives, explicit tags, anchors, and aliases.
   * It also requires the `schema` option to be given as a `Schema` instance value.
   *
   * Overrides all previously set schema options.
   */
  setSchema(version, options = {}) {
    if (typeof version === "number")
      version = String(version);
    let opt;
    switch (version) {
      case "1.1":
        if (this.directives)
          this.directives.yaml.version = "1.1";
        else
          this.directives = new Directives({ version: "1.1" });
        opt = { resolveKnownTags: false, schema: "yaml-1.1" };
        break;
      case "1.2":
      case "next":
        if (this.directives)
          this.directives.yaml.version = version;
        else
          this.directives = new Directives({ version });
        opt = { resolveKnownTags: true, schema: "core" };
        break;
      case null:
        if (this.directives)
          delete this.directives;
        opt = null;
        break;
      default: {
        const sv = JSON.stringify(version);
        throw new Error(`Expected '1.1', '1.2' or null as first argument, but found: ${sv}`);
      }
    }
    if (options.schema instanceof Object)
      this.schema = options.schema;
    else if (opt)
      this.schema = new Schema(Object.assign(opt, options));
    else
      throw new Error(`With a null YAML version, the { schema: Schema } option is required`);
  }
  // json & jsonArg are only used from toJSON()
  toJS({ json, jsonArg, mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
    const ctx = {
      anchors: /* @__PURE__ */ new Map(),
      doc: this,
      keep: !json,
      mapAsMap: mapAsMap === true,
      mapKeyWarned: false,
      maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
    };
    const res = toJS(this.contents, jsonArg ?? "", ctx);
    if (typeof onAnchor === "function")
      for (const { count, res: res2 } of ctx.anchors.values())
        onAnchor(res2, count);
    return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
  }
  /**
   * A JSON representation of the document `contents`.
   *
   * @param jsonArg Used by `JSON.stringify` to indicate the array index or
   *   property name.
   */
  toJSON(jsonArg, onAnchor) {
    return this.toJS({ json: true, jsonArg, mapAsMap: false, onAnchor });
  }
  /** A YAML representation of the document. */
  toString(options = {}) {
    if (this.errors.length > 0)
      throw new Error("Document with errors cannot be stringified");
    if ("indent" in options && (!Number.isInteger(options.indent) || Number(options.indent) <= 0)) {
      const s3 = JSON.stringify(options.indent);
      throw new Error(`"indent" option must be a positive integer, not ${s3}`);
    }
    return stringifyDocument(this, options);
  }
};
function assertCollection(contents) {
  if (isCollection(contents))
    return true;
  throw new Error("Expected a YAML collection as document contents");
}

// node_modules/yaml/browser/dist/errors.js
var YAMLError = class extends Error {
  constructor(name, pos, code, message) {
    super();
    this.name = name;
    this.code = code;
    this.message = message;
    this.pos = pos;
  }
};
var YAMLParseError = class extends YAMLError {
  constructor(pos, code, message) {
    super("YAMLParseError", pos, code, message);
  }
};
var YAMLWarning = class extends YAMLError {
  constructor(pos, code, message) {
    super("YAMLWarning", pos, code, message);
  }
};
var prettifyError = (src, lc) => (error) => {
  if (error.pos[0] === -1)
    return;
  error.linePos = error.pos.map((pos) => lc.linePos(pos));
  const { line, col } = error.linePos[0];
  error.message += ` at line ${line}, column ${col}`;
  let ci = col - 1;
  let lineStr = src.substring(lc.lineStarts[line - 1], lc.lineStarts[line]).replace(/[\n\r]+$/, "");
  if (ci >= 60 && lineStr.length > 80) {
    const trimStart = Math.min(ci - 39, lineStr.length - 79);
    lineStr = "\u2026" + lineStr.substring(trimStart);
    ci -= trimStart - 1;
  }
  if (lineStr.length > 80)
    lineStr = lineStr.substring(0, 79) + "\u2026";
  if (line > 1 && /^ *$/.test(lineStr.substring(0, ci))) {
    let prev = src.substring(lc.lineStarts[line - 2], lc.lineStarts[line - 1]);
    if (prev.length > 80)
      prev = prev.substring(0, 79) + "\u2026\n";
    lineStr = prev + lineStr;
  }
  if (/[^ ]/.test(lineStr)) {
    let count = 1;
    const end = error.linePos[1];
    if (end?.line === line && end.col > col) {
      count = Math.max(1, Math.min(end.col - col, 80 - ci));
    }
    const pointer = " ".repeat(ci) + "^".repeat(count);
    error.message += `:

${lineStr}
${pointer}
`;
  }
};

// node_modules/yaml/browser/dist/compose/resolve-props.js
function resolveProps(tokens, { flow, indicator, next, offset, onError, parentIndent, startOnNewline }) {
  let spaceBefore = false;
  let atNewline = startOnNewline;
  let hasSpace = startOnNewline;
  let comment = "";
  let commentSep = "";
  let hasNewline = false;
  let reqSpace = false;
  let tab = null;
  let anchor = null;
  let tag = null;
  let newlineAfterProp = null;
  let comma = null;
  let found = null;
  let start = null;
  for (const token of tokens) {
    if (reqSpace) {
      if (token.type !== "space" && token.type !== "newline" && token.type !== "comma")
        onError(token.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
      reqSpace = false;
    }
    if (tab) {
      if (atNewline && token.type !== "comment" && token.type !== "newline") {
        onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
      }
      tab = null;
    }
    switch (token.type) {
      case "space":
        if (!flow && (indicator !== "doc-start" || next?.type !== "flow-collection") && token.source.includes("	")) {
          tab = token;
        }
        hasSpace = true;
        break;
      case "comment": {
        if (!hasSpace)
          onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
        const cb = token.source.substring(1) || " ";
        if (!comment)
          comment = cb;
        else
          comment += commentSep + cb;
        commentSep = "";
        atNewline = false;
        break;
      }
      case "newline":
        if (atNewline) {
          if (comment)
            comment += token.source;
          else if (!found || indicator !== "seq-item-ind")
            spaceBefore = true;
        } else
          commentSep += token.source;
        atNewline = true;
        hasNewline = true;
        if (anchor || tag)
          newlineAfterProp = token;
        hasSpace = true;
        break;
      case "anchor":
        if (anchor)
          onError(token, "MULTIPLE_ANCHORS", "A node can have at most one anchor");
        if (token.source.endsWith(":"))
          onError(token.offset + token.source.length - 1, "BAD_ALIAS", "Anchor ending in : is ambiguous", true);
        anchor = token;
        start ?? (start = token.offset);
        atNewline = false;
        hasSpace = false;
        reqSpace = true;
        break;
      case "tag": {
        if (tag)
          onError(token, "MULTIPLE_TAGS", "A node can have at most one tag");
        tag = token;
        start ?? (start = token.offset);
        atNewline = false;
        hasSpace = false;
        reqSpace = true;
        break;
      }
      case indicator:
        if (anchor || tag)
          onError(token, "BAD_PROP_ORDER", `Anchors and tags must be after the ${token.source} indicator`);
        if (found)
          onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.source} in ${flow ?? "collection"}`);
        found = token;
        atNewline = indicator === "seq-item-ind" || indicator === "explicit-key-ind";
        hasSpace = false;
        break;
      case "comma":
        if (flow) {
          if (comma)
            onError(token, "UNEXPECTED_TOKEN", `Unexpected , in ${flow}`);
          comma = token;
          atNewline = false;
          hasSpace = false;
          break;
        }
      // else fallthrough
      default:
        onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.type} token`);
        atNewline = false;
        hasSpace = false;
    }
  }
  const last = tokens[tokens.length - 1];
  const end = last ? last.offset + last.source.length : offset;
  if (reqSpace && next && next.type !== "space" && next.type !== "newline" && next.type !== "comma" && (next.type !== "scalar" || next.source !== "")) {
    onError(next.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
  }
  if (tab && (atNewline && tab.indent <= parentIndent || next?.type === "block-map" || next?.type === "block-seq"))
    onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
  return {
    comma,
    found,
    spaceBefore,
    comment,
    hasNewline,
    anchor,
    tag,
    newlineAfterProp,
    end,
    start: start ?? end
  };
}

// node_modules/yaml/browser/dist/compose/util-contains-newline.js
function containsNewline(key) {
  if (!key)
    return null;
  switch (key.type) {
    case "alias":
    case "scalar":
    case "double-quoted-scalar":
    case "single-quoted-scalar":
      if (key.source.includes("\n"))
        return true;
      if (key.end) {
        for (const st of key.end)
          if (st.type === "newline")
            return true;
      }
      return false;
    case "flow-collection":
      for (const it of key.items) {
        for (const st of it.start)
          if (st.type === "newline")
            return true;
        if (it.sep) {
          for (const st of it.sep)
            if (st.type === "newline")
              return true;
        }
        if (containsNewline(it.key) || containsNewline(it.value))
          return true;
      }
      return false;
    default:
      return true;
  }
}

// node_modules/yaml/browser/dist/compose/util-flow-indent-check.js
function flowIndentCheck(indent, fc, onError) {
  if (fc?.type === "flow-collection") {
    const end = fc.end[0];
    if (end.indent === indent && (end.source === "]" || end.source === "}") && containsNewline(fc)) {
      const msg = "Flow end indicator should be more indented than parent";
      onError(end, "BAD_INDENT", msg, true);
    }
  }
}

// node_modules/yaml/browser/dist/compose/util-map-includes.js
function mapIncludes(ctx, items, search) {
  const { uniqueKeys } = ctx.options;
  if (uniqueKeys === false)
    return false;
  const isEqual = typeof uniqueKeys === "function" ? uniqueKeys : (a3, b2) => a3 === b2 || isScalar(a3) && isScalar(b2) && a3.value === b2.value;
  return items.some((pair) => isEqual(pair.key, search));
}

// node_modules/yaml/browser/dist/compose/resolve-block-map.js
var startColMsg = "All mapping items must start at the same column";
function resolveBlockMap({ composeNode: composeNode2, composeEmptyNode: composeEmptyNode2 }, ctx, bm, onError, tag) {
  const NodeClass = tag?.nodeClass ?? YAMLMap;
  const map2 = new NodeClass(ctx.schema);
  if (ctx.atRoot)
    ctx.atRoot = false;
  let offset = bm.offset;
  let commentEnd = null;
  for (const collItem of bm.items) {
    const { start, key, sep, value } = collItem;
    const keyProps = resolveProps(start, {
      indicator: "explicit-key-ind",
      next: key ?? sep?.[0],
      offset,
      onError,
      parentIndent: bm.indent,
      startOnNewline: true
    });
    const implicitKey = !keyProps.found;
    if (implicitKey) {
      if (key) {
        if (key.type === "block-seq")
          onError(offset, "BLOCK_AS_IMPLICIT_KEY", "A block sequence may not be used as an implicit map key");
        else if ("indent" in key && key.indent !== bm.indent)
          onError(offset, "BAD_INDENT", startColMsg);
      }
      if (!keyProps.anchor && !keyProps.tag && !sep) {
        commentEnd = keyProps.end;
        if (keyProps.comment) {
          if (map2.comment)
            map2.comment += "\n" + keyProps.comment;
          else
            map2.comment = keyProps.comment;
        }
        continue;
      }
      if (keyProps.newlineAfterProp || containsNewline(key)) {
        onError(key ?? start[start.length - 1], "MULTILINE_IMPLICIT_KEY", "Implicit keys need to be on a single line");
      }
    } else if (keyProps.found?.indent !== bm.indent) {
      onError(offset, "BAD_INDENT", startColMsg);
    }
    ctx.atKey = true;
    const keyStart = keyProps.end;
    const keyNode = key ? composeNode2(ctx, key, keyProps, onError) : composeEmptyNode2(ctx, keyStart, start, null, keyProps, onError);
    if (ctx.schema.compat)
      flowIndentCheck(bm.indent, key, onError);
    ctx.atKey = false;
    if (mapIncludes(ctx, map2.items, keyNode))
      onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
    const valueProps = resolveProps(sep ?? [], {
      indicator: "map-value-ind",
      next: value,
      offset: keyNode.range[2],
      onError,
      parentIndent: bm.indent,
      startOnNewline: !key || key.type === "block-scalar"
    });
    offset = valueProps.end;
    if (valueProps.found) {
      if (implicitKey) {
        if (value?.type === "block-map" && !valueProps.hasNewline)
          onError(offset, "BLOCK_AS_IMPLICIT_KEY", "Nested mappings are not allowed in compact mappings");
        if (ctx.options.strict && keyProps.start < valueProps.found.offset - 1024)
          onError(keyNode.range, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit block mapping key");
      }
      const valueNode = value ? composeNode2(ctx, value, valueProps, onError) : composeEmptyNode2(ctx, offset, sep, null, valueProps, onError);
      if (ctx.schema.compat)
        flowIndentCheck(bm.indent, value, onError);
      offset = valueNode.range[2];
      const pair = new Pair(keyNode, valueNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      map2.items.push(pair);
    } else {
      if (implicitKey)
        onError(keyNode.range, "MISSING_CHAR", "Implicit map keys need to be followed by map values");
      if (valueProps.comment) {
        if (keyNode.comment)
          keyNode.comment += "\n" + valueProps.comment;
        else
          keyNode.comment = valueProps.comment;
      }
      const pair = new Pair(keyNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      map2.items.push(pair);
    }
  }
  if (commentEnd && commentEnd < offset)
    onError(commentEnd, "IMPOSSIBLE", "Map comment with trailing content");
  map2.range = [bm.offset, offset, commentEnd ?? offset];
  return map2;
}

// node_modules/yaml/browser/dist/compose/resolve-block-seq.js
function resolveBlockSeq({ composeNode: composeNode2, composeEmptyNode: composeEmptyNode2 }, ctx, bs, onError, tag) {
  const NodeClass = tag?.nodeClass ?? YAMLSeq;
  const seq2 = new NodeClass(ctx.schema);
  if (ctx.atRoot)
    ctx.atRoot = false;
  if (ctx.atKey)
    ctx.atKey = false;
  let offset = bs.offset;
  let commentEnd = null;
  for (const { start, value } of bs.items) {
    const props = resolveProps(start, {
      indicator: "seq-item-ind",
      next: value,
      offset,
      onError,
      parentIndent: bs.indent,
      startOnNewline: true
    });
    if (!props.found) {
      if (props.anchor || props.tag || value) {
        if (value?.type === "block-seq")
          onError(props.end, "BAD_INDENT", "All sequence items must start at the same column");
        else
          onError(offset, "MISSING_CHAR", "Sequence item without - indicator");
      } else {
        commentEnd = props.end;
        if (props.comment)
          seq2.comment = props.comment;
        continue;
      }
    }
    const node = value ? composeNode2(ctx, value, props, onError) : composeEmptyNode2(ctx, props.end, start, null, props, onError);
    if (ctx.schema.compat)
      flowIndentCheck(bs.indent, value, onError);
    offset = node.range[2];
    seq2.items.push(node);
  }
  seq2.range = [bs.offset, offset, commentEnd ?? offset];
  return seq2;
}

// node_modules/yaml/browser/dist/compose/resolve-end.js
function resolveEnd(end, offset, reqSpace, onError) {
  let comment = "";
  if (end) {
    let hasSpace = false;
    let sep = "";
    for (const token of end) {
      const { source, type } = token;
      switch (type) {
        case "space":
          hasSpace = true;
          break;
        case "comment": {
          if (reqSpace && !hasSpace)
            onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
          const cb = source.substring(1) || " ";
          if (!comment)
            comment = cb;
          else
            comment += sep + cb;
          sep = "";
          break;
        }
        case "newline":
          if (comment)
            sep += source;
          hasSpace = true;
          break;
        default:
          onError(token, "UNEXPECTED_TOKEN", `Unexpected ${type} at node end`);
      }
      offset += source.length;
    }
  }
  return { comment, offset };
}

// node_modules/yaml/browser/dist/compose/resolve-flow-collection.js
var blockMsg = "Block collections are not allowed within flow collections";
var isBlock = (token) => token && (token.type === "block-map" || token.type === "block-seq");
function resolveFlowCollection({ composeNode: composeNode2, composeEmptyNode: composeEmptyNode2 }, ctx, fc, onError, tag) {
  const isMap2 = fc.start.source === "{";
  const fcName = isMap2 ? "flow map" : "flow sequence";
  const NodeClass = tag?.nodeClass ?? (isMap2 ? YAMLMap : YAMLSeq);
  const coll = new NodeClass(ctx.schema);
  coll.flow = true;
  const atRoot = ctx.atRoot;
  if (atRoot)
    ctx.atRoot = false;
  if (ctx.atKey)
    ctx.atKey = false;
  let offset = fc.offset + fc.start.source.length;
  for (let i3 = 0; i3 < fc.items.length; ++i3) {
    const collItem = fc.items[i3];
    const { start, key, sep, value } = collItem;
    const props = resolveProps(start, {
      flow: fcName,
      indicator: "explicit-key-ind",
      next: key ?? sep?.[0],
      offset,
      onError,
      parentIndent: fc.indent,
      startOnNewline: false
    });
    if (!props.found) {
      if (!props.anchor && !props.tag && !sep && !value) {
        if (i3 === 0 && props.comma)
          onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
        else if (i3 < fc.items.length - 1)
          onError(props.start, "UNEXPECTED_TOKEN", `Unexpected empty item in ${fcName}`);
        if (props.comment) {
          if (coll.comment)
            coll.comment += "\n" + props.comment;
          else
            coll.comment = props.comment;
        }
        offset = props.end;
        continue;
      }
      if (!isMap2 && ctx.options.strict && containsNewline(key))
        onError(
          key,
          // checked by containsNewline()
          "MULTILINE_IMPLICIT_KEY",
          "Implicit keys of flow sequence pairs need to be on a single line"
        );
    }
    if (i3 === 0) {
      if (props.comma)
        onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
    } else {
      if (!props.comma)
        onError(props.start, "MISSING_CHAR", `Missing , between ${fcName} items`);
      if (props.comment) {
        let prevItemComment = "";
        loop: for (const st of start) {
          switch (st.type) {
            case "comma":
            case "space":
              break;
            case "comment":
              prevItemComment = st.source.substring(1);
              break loop;
            default:
              break loop;
          }
        }
        if (prevItemComment) {
          let prev = coll.items[coll.items.length - 1];
          if (isPair(prev))
            prev = prev.value ?? prev.key;
          if (prev.comment)
            prev.comment += "\n" + prevItemComment;
          else
            prev.comment = prevItemComment;
          props.comment = props.comment.substring(prevItemComment.length + 1);
        }
      }
    }
    if (!isMap2 && !sep && !props.found) {
      const valueNode = value ? composeNode2(ctx, value, props, onError) : composeEmptyNode2(ctx, props.end, sep, null, props, onError);
      coll.items.push(valueNode);
      offset = valueNode.range[2];
      if (isBlock(value))
        onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
    } else {
      ctx.atKey = true;
      const keyStart = props.end;
      const keyNode = key ? composeNode2(ctx, key, props, onError) : composeEmptyNode2(ctx, keyStart, start, null, props, onError);
      if (isBlock(key))
        onError(keyNode.range, "BLOCK_IN_FLOW", blockMsg);
      ctx.atKey = false;
      const valueProps = resolveProps(sep ?? [], {
        flow: fcName,
        indicator: "map-value-ind",
        next: value,
        offset: keyNode.range[2],
        onError,
        parentIndent: fc.indent,
        startOnNewline: false
      });
      if (valueProps.found) {
        if (!isMap2 && !props.found && ctx.options.strict) {
          if (sep)
            for (const st of sep) {
              if (st === valueProps.found)
                break;
              if (st.type === "newline") {
                onError(st, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
                break;
              }
            }
          if (props.start < valueProps.found.offset - 1024)
            onError(valueProps.found, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit flow sequence key");
        }
      } else if (value) {
        if ("source" in value && value.source?.[0] === ":")
          onError(value, "MISSING_CHAR", `Missing space after : in ${fcName}`);
        else
          onError(valueProps.start, "MISSING_CHAR", `Missing , or : between ${fcName} items`);
      }
      const valueNode = value ? composeNode2(ctx, value, valueProps, onError) : valueProps.found ? composeEmptyNode2(ctx, valueProps.end, sep, null, valueProps, onError) : null;
      if (valueNode) {
        if (isBlock(value))
          onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
      } else if (valueProps.comment) {
        if (keyNode.comment)
          keyNode.comment += "\n" + valueProps.comment;
        else
          keyNode.comment = valueProps.comment;
      }
      const pair = new Pair(keyNode, valueNode);
      if (ctx.options.keepSourceTokens)
        pair.srcToken = collItem;
      if (isMap2) {
        const map2 = coll;
        if (mapIncludes(ctx, map2.items, keyNode))
          onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
        map2.items.push(pair);
      } else {
        const map2 = new YAMLMap(ctx.schema);
        map2.flow = true;
        map2.items.push(pair);
        const endRange = (valueNode ?? keyNode).range;
        map2.range = [keyNode.range[0], endRange[1], endRange[2]];
        coll.items.push(map2);
      }
      offset = valueNode ? valueNode.range[2] : valueProps.end;
    }
  }
  const expectedEnd = isMap2 ? "}" : "]";
  const [ce, ...ee] = fc.end;
  let cePos = offset;
  if (ce?.source === expectedEnd)
    cePos = ce.offset + ce.source.length;
  else {
    const name = fcName[0].toUpperCase() + fcName.substring(1);
    const msg = atRoot ? `${name} must end with a ${expectedEnd}` : `${name} in block collection must be sufficiently indented and end with a ${expectedEnd}`;
    onError(offset, atRoot ? "MISSING_CHAR" : "BAD_INDENT", msg);
    if (ce && ce.source.length !== 1)
      ee.unshift(ce);
  }
  if (ee.length > 0) {
    const end = resolveEnd(ee, cePos, ctx.options.strict, onError);
    if (end.comment) {
      if (coll.comment)
        coll.comment += "\n" + end.comment;
      else
        coll.comment = end.comment;
    }
    coll.range = [fc.offset, cePos, end.offset];
  } else {
    coll.range = [fc.offset, cePos, cePos];
  }
  return coll;
}

// node_modules/yaml/browser/dist/compose/compose-collection.js
function resolveCollection(CN2, ctx, token, onError, tagName, tag) {
  const coll = token.type === "block-map" ? resolveBlockMap(CN2, ctx, token, onError, tag) : token.type === "block-seq" ? resolveBlockSeq(CN2, ctx, token, onError, tag) : resolveFlowCollection(CN2, ctx, token, onError, tag);
  const Coll = coll.constructor;
  if (tagName === "!" || tagName === Coll.tagName) {
    coll.tag = Coll.tagName;
    return coll;
  }
  if (tagName)
    coll.tag = tagName;
  return coll;
}
function composeCollection(CN2, ctx, token, props, onError) {
  const tagToken = props.tag;
  const tagName = !tagToken ? null : ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg));
  if (token.type === "block-seq") {
    const { anchor, newlineAfterProp: nl } = props;
    const lastProp = anchor && tagToken ? anchor.offset > tagToken.offset ? anchor : tagToken : anchor ?? tagToken;
    if (lastProp && (!nl || nl.offset < lastProp.offset)) {
      const message = "Missing newline after block sequence props";
      onError(lastProp, "MISSING_CHAR", message);
    }
  }
  const expType = token.type === "block-map" ? "map" : token.type === "block-seq" ? "seq" : token.start.source === "{" ? "map" : "seq";
  if (!tagToken || !tagName || tagName === "!" || tagName === YAMLMap.tagName && expType === "map" || tagName === YAMLSeq.tagName && expType === "seq") {
    return resolveCollection(CN2, ctx, token, onError, tagName);
  }
  let tag = ctx.schema.tags.find((t4) => t4.tag === tagName && t4.collection === expType);
  if (!tag) {
    const kt = ctx.schema.knownTags[tagName];
    if (kt?.collection === expType) {
      ctx.schema.tags.push(Object.assign({}, kt, { default: false }));
      tag = kt;
    } else {
      if (kt) {
        onError(tagToken, "BAD_COLLECTION_TYPE", `${kt.tag} used for ${expType} collection, but expects ${kt.collection ?? "scalar"}`, true);
      } else {
        onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, true);
      }
      return resolveCollection(CN2, ctx, token, onError, tagName);
    }
  }
  const coll = resolveCollection(CN2, ctx, token, onError, tagName, tag);
  const res = tag.resolve?.(coll, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg), ctx.options) ?? coll;
  const node = isNode(res) ? res : new Scalar(res);
  node.range = coll.range;
  node.tag = tagName;
  if (tag?.format)
    node.format = tag.format;
  return node;
}

// node_modules/yaml/browser/dist/compose/resolve-block-scalar.js
function resolveBlockScalar(ctx, scalar, onError) {
  const start = scalar.offset;
  const header = parseBlockScalarHeader(scalar, ctx.options.strict, onError);
  if (!header)
    return { value: "", type: null, comment: "", range: [start, start, start] };
  const type = header.mode === ">" ? Scalar.BLOCK_FOLDED : Scalar.BLOCK_LITERAL;
  const lines = scalar.source ? splitLines(scalar.source) : [];
  let chompStart = lines.length;
  for (let i3 = lines.length - 1; i3 >= 0; --i3) {
    const content = lines[i3][1];
    if (content === "" || content === "\r")
      chompStart = i3;
    else
      break;
  }
  if (chompStart === 0) {
    const value2 = header.chomp === "+" && lines.length > 0 ? "\n".repeat(Math.max(1, lines.length - 1)) : "";
    let end2 = start + header.length;
    if (scalar.source)
      end2 += scalar.source.length;
    return { value: value2, type, comment: header.comment, range: [start, end2, end2] };
  }
  let trimIndent = scalar.indent + header.indent;
  let offset = scalar.offset + header.length;
  let contentStart = 0;
  for (let i3 = 0; i3 < chompStart; ++i3) {
    const [indent, content] = lines[i3];
    if (content === "" || content === "\r") {
      if (header.indent === 0 && indent.length > trimIndent)
        trimIndent = indent.length;
    } else {
      if (indent.length < trimIndent) {
        const message = "Block scalars with more-indented leading empty lines must use an explicit indentation indicator";
        onError(offset + indent.length, "MISSING_CHAR", message);
      }
      if (header.indent === 0)
        trimIndent = indent.length;
      contentStart = i3;
      if (trimIndent === 0 && !ctx.atRoot) {
        const message = "Block scalar values in collections must be indented";
        onError(offset, "BAD_INDENT", message);
      }
      break;
    }
    offset += indent.length + content.length + 1;
  }
  for (let i3 = lines.length - 1; i3 >= chompStart; --i3) {
    if (lines[i3][0].length > trimIndent)
      chompStart = i3 + 1;
  }
  let value = "";
  let sep = "";
  let prevMoreIndented = false;
  for (let i3 = 0; i3 < contentStart; ++i3)
    value += lines[i3][0].slice(trimIndent) + "\n";
  for (let i3 = contentStart; i3 < chompStart; ++i3) {
    let [indent, content] = lines[i3];
    offset += indent.length + content.length + 1;
    const crlf = content[content.length - 1] === "\r";
    if (crlf)
      content = content.slice(0, -1);
    if (content && indent.length < trimIndent) {
      const src = header.indent ? "explicit indentation indicator" : "first line";
      const message = `Block scalar lines must not be less indented than their ${src}`;
      onError(offset - content.length - (crlf ? 2 : 1), "BAD_INDENT", message);
      indent = "";
    }
    if (type === Scalar.BLOCK_LITERAL) {
      value += sep + indent.slice(trimIndent) + content;
      sep = "\n";
    } else if (indent.length > trimIndent || content[0] === "	") {
      if (sep === " ")
        sep = "\n";
      else if (!prevMoreIndented && sep === "\n")
        sep = "\n\n";
      value += sep + indent.slice(trimIndent) + content;
      sep = "\n";
      prevMoreIndented = true;
    } else if (content === "") {
      if (sep === "\n")
        value += "\n";
      else
        sep = "\n";
    } else {
      value += sep + content;
      sep = " ";
      prevMoreIndented = false;
    }
  }
  switch (header.chomp) {
    case "-":
      break;
    case "+":
      for (let i3 = chompStart; i3 < lines.length; ++i3)
        value += "\n" + lines[i3][0].slice(trimIndent);
      if (value[value.length - 1] !== "\n")
        value += "\n";
      break;
    default:
      value += "\n";
  }
  const end = start + header.length + scalar.source.length;
  return { value, type, comment: header.comment, range: [start, end, end] };
}
function parseBlockScalarHeader({ offset, props }, strict, onError) {
  if (props[0].type !== "block-scalar-header") {
    onError(props[0], "IMPOSSIBLE", "Block scalar header not found");
    return null;
  }
  const { source } = props[0];
  const mode = source[0];
  let indent = 0;
  let chomp = "";
  let error = -1;
  for (let i3 = 1; i3 < source.length; ++i3) {
    const ch = source[i3];
    if (!chomp && (ch === "-" || ch === "+"))
      chomp = ch;
    else {
      const n2 = Number(ch);
      if (!indent && n2)
        indent = n2;
      else if (error === -1)
        error = offset + i3;
    }
  }
  if (error !== -1)
    onError(error, "UNEXPECTED_TOKEN", `Block scalar header includes extra characters: ${source}`);
  let hasSpace = false;
  let comment = "";
  let length = source.length;
  for (let i3 = 1; i3 < props.length; ++i3) {
    const token = props[i3];
    switch (token.type) {
      case "space":
        hasSpace = true;
      // fallthrough
      case "newline":
        length += token.source.length;
        break;
      case "comment":
        if (strict && !hasSpace) {
          const message = "Comments must be separated from other tokens by white space characters";
          onError(token, "MISSING_CHAR", message);
        }
        length += token.source.length;
        comment = token.source.substring(1);
        break;
      case "error":
        onError(token, "UNEXPECTED_TOKEN", token.message);
        length += token.source.length;
        break;
      /* istanbul ignore next should not happen */
      default: {
        const message = `Unexpected token in block scalar header: ${token.type}`;
        onError(token, "UNEXPECTED_TOKEN", message);
        const ts = token.source;
        if (ts && typeof ts === "string")
          length += ts.length;
      }
    }
  }
  return { mode, indent, chomp, comment, length };
}
function splitLines(source) {
  const split = source.split(/\n( *)/);
  const first = split[0];
  const m3 = first.match(/^( *)/);
  const line0 = m3?.[1] ? [m3[1], first.slice(m3[1].length)] : ["", first];
  const lines = [line0];
  for (let i3 = 1; i3 < split.length; i3 += 2)
    lines.push([split[i3], split[i3 + 1]]);
  return lines;
}

// node_modules/yaml/browser/dist/compose/resolve-flow-scalar.js
function resolveFlowScalar(scalar, strict, onError) {
  const { offset, type, source, end } = scalar;
  let _type;
  let value;
  const _onError = (rel, code, msg) => onError(offset + rel, code, msg);
  switch (type) {
    case "scalar":
      _type = Scalar.PLAIN;
      value = plainValue(source, _onError);
      break;
    case "single-quoted-scalar":
      _type = Scalar.QUOTE_SINGLE;
      value = singleQuotedValue(source, _onError);
      break;
    case "double-quoted-scalar":
      _type = Scalar.QUOTE_DOUBLE;
      value = doubleQuotedValue(source, _onError);
      break;
    /* istanbul ignore next should not happen */
    default:
      onError(scalar, "UNEXPECTED_TOKEN", `Expected a flow scalar value, but found: ${type}`);
      return {
        value: "",
        type: null,
        comment: "",
        range: [offset, offset + source.length, offset + source.length]
      };
  }
  const valueEnd = offset + source.length;
  const re = resolveEnd(end, valueEnd, strict, onError);
  return {
    value,
    type: _type,
    comment: re.comment,
    range: [offset, valueEnd, re.offset]
  };
}
function plainValue(source, onError) {
  let badChar = "";
  switch (source[0]) {
    /* istanbul ignore next should not happen */
    case "	":
      badChar = "a tab character";
      break;
    case ",":
      badChar = "flow indicator character ,";
      break;
    case "%":
      badChar = "directive indicator character %";
      break;
    case "|":
    case ">": {
      badChar = `block scalar indicator ${source[0]}`;
      break;
    }
    case "@":
    case "`": {
      badChar = `reserved character ${source[0]}`;
      break;
    }
  }
  if (badChar)
    onError(0, "BAD_SCALAR_START", `Plain value cannot start with ${badChar}`);
  return foldLines(source);
}
function singleQuotedValue(source, onError) {
  if (source[source.length - 1] !== "'" || source.length === 1)
    onError(source.length, "MISSING_CHAR", "Missing closing 'quote");
  return foldLines(source.slice(1, -1)).replace(/''/g, "'");
}
function foldLines(source) {
  let first, line;
  try {
    first = new RegExp("(.*?)(?<![ 	])[ 	]*\r?\n", "sy");
    line = new RegExp("[ 	]*(.*?)(?:(?<![ 	])[ 	]*)?\r?\n", "sy");
  } catch {
    first = /(.*?)[ \t]*\r?\n/sy;
    line = /[ \t]*(.*?)[ \t]*\r?\n/sy;
  }
  let match = first.exec(source);
  if (!match)
    return source;
  let res = match[1];
  let sep = " ";
  let pos = first.lastIndex;
  line.lastIndex = pos;
  while (match = line.exec(source)) {
    if (match[1] === "") {
      if (sep === "\n")
        res += sep;
      else
        sep = "\n";
    } else {
      res += sep + match[1];
      sep = " ";
    }
    pos = line.lastIndex;
  }
  const last = /[ \t]*(.*)/sy;
  last.lastIndex = pos;
  match = last.exec(source);
  return res + sep + (match?.[1] ?? "");
}
function doubleQuotedValue(source, onError) {
  let res = "";
  for (let i3 = 1; i3 < source.length - 1; ++i3) {
    const ch = source[i3];
    if (ch === "\r" && source[i3 + 1] === "\n")
      continue;
    if (ch === "\n") {
      const { fold, offset } = foldNewline(source, i3);
      res += fold;
      i3 = offset;
    } else if (ch === "\\") {
      let next = source[++i3];
      const cc = escapeCodes[next];
      if (cc)
        res += cc;
      else if (next === "\n") {
        next = source[i3 + 1];
        while (next === " " || next === "	")
          next = source[++i3 + 1];
      } else if (next === "\r" && source[i3 + 1] === "\n") {
        next = source[++i3 + 1];
        while (next === " " || next === "	")
          next = source[++i3 + 1];
      } else if (next === "x" || next === "u" || next === "U") {
        const length = { x: 2, u: 4, U: 8 }[next];
        res += parseCharCode(source, i3 + 1, length, onError);
        i3 += length;
      } else {
        const raw = source.substr(i3 - 1, 2);
        onError(i3 - 1, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
        res += raw;
      }
    } else if (ch === " " || ch === "	") {
      const wsStart = i3;
      let next = source[i3 + 1];
      while (next === " " || next === "	")
        next = source[++i3 + 1];
      if (next !== "\n" && !(next === "\r" && source[i3 + 2] === "\n"))
        res += i3 > wsStart ? source.slice(wsStart, i3 + 1) : ch;
    } else {
      res += ch;
    }
  }
  if (source[source.length - 1] !== '"' || source.length === 1)
    onError(source.length, "MISSING_CHAR", 'Missing closing "quote');
  return res;
}
function foldNewline(source, offset) {
  let fold = "";
  let ch = source[offset + 1];
  while (ch === " " || ch === "	" || ch === "\n" || ch === "\r") {
    if (ch === "\r" && source[offset + 2] !== "\n")
      break;
    if (ch === "\n")
      fold += "\n";
    offset += 1;
    ch = source[offset + 1];
  }
  if (!fold)
    fold = " ";
  return { fold, offset };
}
var escapeCodes = {
  "0": "\0",
  // null character
  a: "\x07",
  // bell character
  b: "\b",
  // backspace
  e: "\x1B",
  // escape character
  f: "\f",
  // form feed
  n: "\n",
  // line feed
  r: "\r",
  // carriage return
  t: "	",
  // horizontal tab
  v: "\v",
  // vertical tab
  N: "\x85",
  // Unicode next line
  _: "\xA0",
  // Unicode non-breaking space
  L: "\u2028",
  // Unicode line separator
  P: "\u2029",
  // Unicode paragraph separator
  " ": " ",
  '"': '"',
  "/": "/",
  "\\": "\\",
  "	": "	"
};
function parseCharCode(source, offset, length, onError) {
  const cc = source.substr(offset, length);
  const ok = cc.length === length && /^[0-9a-fA-F]+$/.test(cc);
  const code = ok ? parseInt(cc, 16) : NaN;
  if (isNaN(code)) {
    const raw = source.substr(offset - 2, length + 2);
    onError(offset - 2, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
    return raw;
  }
  return String.fromCodePoint(code);
}

// node_modules/yaml/browser/dist/compose/compose-scalar.js
function composeScalar(ctx, token, tagToken, onError) {
  const { value, type, comment, range } = token.type === "block-scalar" ? resolveBlockScalar(ctx, token, onError) : resolveFlowScalar(token, ctx.options.strict, onError);
  const tagName = tagToken ? ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg)) : null;
  let tag;
  if (ctx.options.stringKeys && ctx.atKey) {
    tag = ctx.schema[SCALAR];
  } else if (tagName)
    tag = findScalarTagByName(ctx.schema, value, tagName, tagToken, onError);
  else if (token.type === "scalar")
    tag = findScalarTagByTest(ctx, value, token, onError);
  else
    tag = ctx.schema[SCALAR];
  let scalar;
  try {
    const res = tag.resolve(value, (msg) => onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg), ctx.options);
    scalar = isScalar(res) ? res : new Scalar(res);
  } catch (error) {
    const msg = error instanceof Error ? error.message : String(error);
    onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg);
    scalar = new Scalar(value);
  }
  scalar.range = range;
  scalar.source = value;
  if (type)
    scalar.type = type;
  if (tagName)
    scalar.tag = tagName;
  if (tag.format)
    scalar.format = tag.format;
  if (comment)
    scalar.comment = comment;
  return scalar;
}
function findScalarTagByName(schema4, value, tagName, tagToken, onError) {
  if (tagName === "!")
    return schema4[SCALAR];
  const matchWithTest = [];
  for (const tag of schema4.tags) {
    if (!tag.collection && tag.tag === tagName) {
      if (tag.default && tag.test)
        matchWithTest.push(tag);
      else
        return tag;
    }
  }
  for (const tag of matchWithTest)
    if (tag.test?.test(value))
      return tag;
  const kt = schema4.knownTags[tagName];
  if (kt && !kt.collection) {
    schema4.tags.push(Object.assign({}, kt, { default: false, test: void 0 }));
    return kt;
  }
  onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, tagName !== "tag:yaml.org,2002:str");
  return schema4[SCALAR];
}
function findScalarTagByTest({ atKey, directives, schema: schema4 }, value, token, onError) {
  const tag = schema4.tags.find((tag2) => (tag2.default === true || atKey && tag2.default === "key") && tag2.test?.test(value)) || schema4[SCALAR];
  if (schema4.compat) {
    const compat = schema4.compat.find((tag2) => tag2.default && tag2.test?.test(value)) ?? schema4[SCALAR];
    if (tag.tag !== compat.tag) {
      const ts = directives.tagString(tag.tag);
      const cs = directives.tagString(compat.tag);
      const msg = `Value may be parsed as either ${ts} or ${cs}`;
      onError(token, "TAG_RESOLVE_FAILED", msg, true);
    }
  }
  return tag;
}

// node_modules/yaml/browser/dist/compose/util-empty-scalar-position.js
function emptyScalarPosition(offset, before, pos) {
  if (before) {
    pos ?? (pos = before.length);
    for (let i3 = pos - 1; i3 >= 0; --i3) {
      let st = before[i3];
      switch (st.type) {
        case "space":
        case "comment":
        case "newline":
          offset -= st.source.length;
          continue;
      }
      st = before[++i3];
      while (st?.type === "space") {
        offset += st.source.length;
        st = before[++i3];
      }
      break;
    }
  }
  return offset;
}

// node_modules/yaml/browser/dist/compose/compose-node.js
var CN = { composeNode, composeEmptyNode };
function composeNode(ctx, token, props, onError) {
  const atKey = ctx.atKey;
  const { spaceBefore, comment, anchor, tag } = props;
  let node;
  let isSrcToken = true;
  switch (token.type) {
    case "alias":
      node = composeAlias(ctx, token, onError);
      if (anchor || tag)
        onError(token, "ALIAS_PROPS", "An alias node must not specify any properties");
      break;
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "block-scalar":
      node = composeScalar(ctx, token, tag, onError);
      if (anchor)
        node.anchor = anchor.source.substring(1);
      break;
    case "block-map":
    case "block-seq":
    case "flow-collection":
      try {
        node = composeCollection(CN, ctx, token, props, onError);
        if (anchor)
          node.anchor = anchor.source.substring(1);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        onError(token, "RESOURCE_EXHAUSTION", message);
      }
      break;
    default: {
      const message = token.type === "error" ? token.message : `Unsupported token (type: ${token.type})`;
      onError(token, "UNEXPECTED_TOKEN", message);
      isSrcToken = false;
    }
  }
  node ?? (node = composeEmptyNode(ctx, token.offset, void 0, null, props, onError));
  if (anchor && node.anchor === "")
    onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
  if (atKey && ctx.options.stringKeys && (!isScalar(node) || typeof node.value !== "string" || node.tag && node.tag !== "tag:yaml.org,2002:str")) {
    const msg = "With stringKeys, all keys must be strings";
    onError(tag ?? token, "NON_STRING_KEY", msg);
  }
  if (spaceBefore)
    node.spaceBefore = true;
  if (comment) {
    if (token.type === "scalar" && token.source === "")
      node.comment = comment;
    else
      node.commentBefore = comment;
  }
  if (ctx.options.keepSourceTokens && isSrcToken)
    node.srcToken = token;
  return node;
}
function composeEmptyNode(ctx, offset, before, pos, { spaceBefore, comment, anchor, tag, end }, onError) {
  const token = {
    type: "scalar",
    offset: emptyScalarPosition(offset, before, pos),
    indent: -1,
    source: ""
  };
  const node = composeScalar(ctx, token, tag, onError);
  if (anchor) {
    node.anchor = anchor.source.substring(1);
    if (node.anchor === "")
      onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
  }
  if (spaceBefore)
    node.spaceBefore = true;
  if (comment) {
    node.comment = comment;
    node.range[2] = end;
  }
  return node;
}
function composeAlias({ options }, { offset, source, end }, onError) {
  const alias = new Alias(source.substring(1));
  if (alias.source === "")
    onError(offset, "BAD_ALIAS", "Alias cannot be an empty string");
  if (alias.source.endsWith(":"))
    onError(offset + source.length - 1, "BAD_ALIAS", "Alias ending in : is ambiguous", true);
  const valueEnd = offset + source.length;
  const re = resolveEnd(end, valueEnd, options.strict, onError);
  alias.range = [offset, valueEnd, re.offset];
  if (re.comment)
    alias.comment = re.comment;
  return alias;
}

// node_modules/yaml/browser/dist/compose/compose-doc.js
function composeDoc(options, directives, { offset, start, value, end }, onError) {
  const opts = Object.assign({ _directives: directives }, options);
  const doc = new Document(void 0, opts);
  const ctx = {
    atKey: false,
    atRoot: true,
    directives: doc.directives,
    options: doc.options,
    schema: doc.schema
  };
  const props = resolveProps(start, {
    indicator: "doc-start",
    next: value ?? end?.[0],
    offset,
    onError,
    parentIndent: 0,
    startOnNewline: true
  });
  if (props.found) {
    doc.directives.docStart = true;
    if (value && (value.type === "block-map" || value.type === "block-seq") && !props.hasNewline)
      onError(props.end, "MISSING_CHAR", "Block collection cannot start on same line with directives-end marker");
  }
  doc.contents = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, start, null, props, onError);
  const contentEnd = doc.contents.range[2];
  const re = resolveEnd(end, contentEnd, false, onError);
  if (re.comment)
    doc.comment = re.comment;
  doc.range = [offset, contentEnd, re.offset];
  return doc;
}

// node_modules/yaml/browser/dist/compose/composer.js
function getErrorPos(src) {
  if (typeof src === "number")
    return [src, src + 1];
  if (Array.isArray(src))
    return src.length === 2 ? src : [src[0], src[1]];
  const { offset, source } = src;
  return [offset, offset + (typeof source === "string" ? source.length : 1)];
}
function parsePrelude(prelude) {
  let comment = "";
  let atComment = false;
  let afterEmptyLine = false;
  for (let i3 = 0; i3 < prelude.length; ++i3) {
    const source = prelude[i3];
    switch (source[0]) {
      case "#":
        comment += (comment === "" ? "" : afterEmptyLine ? "\n\n" : "\n") + (source.substring(1) || " ");
        atComment = true;
        afterEmptyLine = false;
        break;
      case "%":
        if (prelude[i3 + 1]?.[0] !== "#")
          i3 += 1;
        atComment = false;
        break;
      default:
        if (!atComment)
          afterEmptyLine = true;
        atComment = false;
    }
  }
  return { comment, afterEmptyLine };
}
var Composer = class {
  constructor(options = {}) {
    this.doc = null;
    this.atDirectives = false;
    this.prelude = [];
    this.errors = [];
    this.warnings = [];
    this.onError = (source, code, message, warning) => {
      const pos = getErrorPos(source);
      if (warning)
        this.warnings.push(new YAMLWarning(pos, code, message));
      else
        this.errors.push(new YAMLParseError(pos, code, message));
    };
    this.directives = new Directives({ version: options.version || "1.2" });
    this.options = options;
  }
  decorate(doc, afterDoc) {
    const { comment, afterEmptyLine } = parsePrelude(this.prelude);
    if (comment) {
      const dc = doc.contents;
      if (afterDoc) {
        doc.comment = doc.comment ? `${doc.comment}
${comment}` : comment;
      } else if (afterEmptyLine || doc.directives.docStart || !dc) {
        doc.commentBefore = comment;
      } else if (isCollection(dc) && !dc.flow && dc.items.length > 0) {
        let it = dc.items[0];
        if (isPair(it))
          it = it.key;
        const cb = it.commentBefore;
        it.commentBefore = cb ? `${comment}
${cb}` : comment;
      } else {
        const cb = dc.commentBefore;
        dc.commentBefore = cb ? `${comment}
${cb}` : comment;
      }
    }
    if (afterDoc) {
      Array.prototype.push.apply(doc.errors, this.errors);
      Array.prototype.push.apply(doc.warnings, this.warnings);
    } else {
      doc.errors = this.errors;
      doc.warnings = this.warnings;
    }
    this.prelude = [];
    this.errors = [];
    this.warnings = [];
  }
  /**
   * Current stream status information.
   *
   * Mostly useful at the end of input for an empty stream.
   */
  streamInfo() {
    return {
      comment: parsePrelude(this.prelude).comment,
      directives: this.directives,
      errors: this.errors,
      warnings: this.warnings
    };
  }
  /**
   * Compose tokens into documents.
   *
   * @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
   * @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
   */
  *compose(tokens, forceDoc = false, endOffset = -1) {
    for (const token of tokens)
      yield* this.next(token);
    yield* this.end(forceDoc, endOffset);
  }
  /** Advance the composer by one CST token. */
  *next(token) {
    switch (token.type) {
      case "directive":
        this.directives.add(token.source, (offset, message, warning) => {
          const pos = getErrorPos(token);
          pos[0] += offset;
          this.onError(pos, "BAD_DIRECTIVE", message, warning);
        });
        this.prelude.push(token.source);
        this.atDirectives = true;
        break;
      case "document": {
        const doc = composeDoc(this.options, this.directives, token, this.onError);
        if (this.atDirectives && !doc.directives.docStart)
          this.onError(token, "MISSING_CHAR", "Missing directives-end/doc-start indicator line");
        this.decorate(doc, false);
        if (this.doc)
          yield this.doc;
        this.doc = doc;
        this.atDirectives = false;
        break;
      }
      case "byte-order-mark":
      case "space":
        break;
      case "comment":
      case "newline":
        this.prelude.push(token.source);
        break;
      case "error": {
        const msg = token.source ? `${token.message}: ${JSON.stringify(token.source)}` : token.message;
        const error = new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", msg);
        if (this.atDirectives || !this.doc)
          this.errors.push(error);
        else
          this.doc.errors.push(error);
        break;
      }
      case "doc-end": {
        if (!this.doc) {
          const msg = "Unexpected doc-end without preceding document";
          this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", msg));
          break;
        }
        this.doc.directives.docEnd = true;
        const end = resolveEnd(token.end, token.offset + token.source.length, this.doc.options.strict, this.onError);
        this.decorate(this.doc, true);
        if (end.comment) {
          const dc = this.doc.comment;
          this.doc.comment = dc ? `${dc}
${end.comment}` : end.comment;
        }
        this.doc.range[2] = end.offset;
        break;
      }
      default:
        this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", `Unsupported token ${token.type}`));
    }
  }
  /**
   * Call at end of input to yield any remaining document.
   *
   * @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
   * @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
   */
  *end(forceDoc = false, endOffset = -1) {
    if (this.doc) {
      this.decorate(this.doc, true);
      yield this.doc;
      this.doc = null;
    } else if (forceDoc) {
      const opts = Object.assign({ _directives: this.directives }, this.options);
      const doc = new Document(void 0, opts);
      if (this.atDirectives)
        this.onError(endOffset, "MISSING_CHAR", "Missing directives-end indicator line");
      doc.range = [0, endOffset, endOffset];
      this.decorate(doc, false);
      yield doc;
    }
  }
};

// node_modules/yaml/browser/dist/parse/cst-visit.js
var BREAK2 = Symbol("break visit");
var SKIP2 = Symbol("skip children");
var REMOVE2 = Symbol("remove item");
function visit2(cst, visitor) {
  if ("type" in cst && cst.type === "document")
    cst = { start: cst.start, value: cst.value };
  _visit(Object.freeze([]), cst, visitor);
}
visit2.BREAK = BREAK2;
visit2.SKIP = SKIP2;
visit2.REMOVE = REMOVE2;
visit2.itemAtPath = (cst, path) => {
  let item = cst;
  for (const [field, index] of path) {
    const tok = item?.[field];
    if (tok && "items" in tok) {
      item = tok.items[index];
    } else
      return void 0;
  }
  return item;
};
visit2.parentCollection = (cst, path) => {
  const parent = visit2.itemAtPath(cst, path.slice(0, -1));
  const field = path[path.length - 1][0];
  const coll = parent?.[field];
  if (coll && "items" in coll)
    return coll;
  throw new Error("Parent collection not found");
};
function _visit(path, item, visitor) {
  let ctrl = visitor(item, path);
  if (typeof ctrl === "symbol")
    return ctrl;
  for (const field of ["key", "value"]) {
    const token = item[field];
    if (token && "items" in token) {
      for (let i3 = 0; i3 < token.items.length; ++i3) {
        const ci = _visit(Object.freeze(path.concat([[field, i3]])), token.items[i3], visitor);
        if (typeof ci === "number")
          i3 = ci - 1;
        else if (ci === BREAK2)
          return BREAK2;
        else if (ci === REMOVE2) {
          token.items.splice(i3, 1);
          i3 -= 1;
        }
      }
      if (typeof ctrl === "function" && field === "key")
        ctrl = ctrl(item, path);
    }
  }
  return typeof ctrl === "function" ? ctrl(item, path) : ctrl;
}

// node_modules/yaml/browser/dist/parse/cst.js
var BOM = "\uFEFF";
var DOCUMENT = "";
var FLOW_END = "";
var SCALAR2 = "";
function tokenType(source) {
  switch (source) {
    case BOM:
      return "byte-order-mark";
    case DOCUMENT:
      return "doc-mode";
    case FLOW_END:
      return "flow-error-end";
    case SCALAR2:
      return "scalar";
    case "---":
      return "doc-start";
    case "...":
      return "doc-end";
    case "":
    case "\n":
    case "\r\n":
      return "newline";
    case "-":
      return "seq-item-ind";
    case "?":
      return "explicit-key-ind";
    case ":":
      return "map-value-ind";
    case "{":
      return "flow-map-start";
    case "}":
      return "flow-map-end";
    case "[":
      return "flow-seq-start";
    case "]":
      return "flow-seq-end";
    case ",":
      return "comma";
  }
  switch (source[0]) {
    case " ":
    case "	":
      return "space";
    case "#":
      return "comment";
    case "%":
      return "directive-line";
    case "*":
      return "alias";
    case "&":
      return "anchor";
    case "!":
      return "tag";
    case "'":
      return "single-quoted-scalar";
    case '"':
      return "double-quoted-scalar";
    case "|":
    case ">":
      return "block-scalar-header";
  }
  return null;
}

// node_modules/yaml/browser/dist/parse/lexer.js
function isEmpty(ch) {
  switch (ch) {
    case void 0:
    case " ":
    case "\n":
    case "\r":
    case "	":
      return true;
    default:
      return false;
  }
}
var hexDigits = new Set("0123456789ABCDEFabcdef");
var tagChars = new Set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-#;/?:@&=+$_.!~*'()");
var flowIndicatorChars = new Set(",[]{}");
var invalidAnchorChars = new Set(" ,[]{}\n\r	");
var isNotAnchorChar = (ch) => !ch || invalidAnchorChars.has(ch);
var Lexer = class {
  constructor() {
    this.atEnd = false;
    this.blockScalarIndent = -1;
    this.blockScalarKeep = false;
    this.buffer = "";
    this.flowKey = false;
    this.flowLevel = 0;
    this.indentNext = 0;
    this.indentValue = 0;
    this.lineEndPos = null;
    this.next = null;
    this.pos = 0;
  }
  /**
   * Generate YAML tokens from the `source` string. If `incomplete`,
   * a part of the last line may be left as a buffer for the next call.
   *
   * @returns A generator of lexical tokens
   */
  *lex(source, incomplete = false) {
    if (source) {
      if (typeof source !== "string")
        throw TypeError("source is not a string");
      this.buffer = this.buffer ? this.buffer + source : source;
      this.lineEndPos = null;
    }
    this.atEnd = !incomplete;
    let next = this.next ?? "stream";
    while (next && (incomplete || this.hasChars(1)))
      next = yield* this.parseNext(next);
  }
  atLineEnd() {
    let i3 = this.pos;
    let ch = this.buffer[i3];
    while (ch === " " || ch === "	")
      ch = this.buffer[++i3];
    if (!ch || ch === "#" || ch === "\n")
      return true;
    if (ch === "\r")
      return this.buffer[i3 + 1] === "\n";
    return false;
  }
  charAt(n2) {
    return this.buffer[this.pos + n2];
  }
  continueScalar(offset) {
    let ch = this.buffer[offset];
    if (this.indentNext > 0) {
      let indent = 0;
      while (ch === " ")
        ch = this.buffer[++indent + offset];
      if (ch === "\r") {
        const next = this.buffer[indent + offset + 1];
        if (next === "\n" || !next && !this.atEnd)
          return offset + indent + 1;
      }
      return ch === "\n" || indent >= this.indentNext || !ch && !this.atEnd ? offset + indent : -1;
    }
    if (ch === "-" || ch === ".") {
      const dt = this.buffer.substr(offset, 3);
      if ((dt === "---" || dt === "...") && isEmpty(this.buffer[offset + 3]))
        return -1;
    }
    return offset;
  }
  getLine() {
    let end = this.lineEndPos;
    if (typeof end !== "number" || end !== -1 && end < this.pos) {
      end = this.buffer.indexOf("\n", this.pos);
      this.lineEndPos = end;
    }
    if (end === -1)
      return this.atEnd ? this.buffer.substring(this.pos) : null;
    if (this.buffer[end - 1] === "\r")
      end -= 1;
    return this.buffer.substring(this.pos, end);
  }
  hasChars(n2) {
    return this.pos + n2 <= this.buffer.length;
  }
  setNext(state) {
    this.buffer = this.buffer.substring(this.pos);
    this.pos = 0;
    this.lineEndPos = null;
    this.next = state;
    return null;
  }
  peek(n2) {
    return this.buffer.substr(this.pos, n2);
  }
  *parseNext(next) {
    switch (next) {
      case "stream":
        return yield* this.parseStream();
      case "line-start":
        return yield* this.parseLineStart();
      case "block-start":
        return yield* this.parseBlockStart();
      case "doc":
        return yield* this.parseDocument();
      case "flow":
        return yield* this.parseFlowCollection();
      case "quoted-scalar":
        return yield* this.parseQuotedScalar();
      case "block-scalar":
        return yield* this.parseBlockScalar();
      case "plain-scalar":
        return yield* this.parsePlainScalar();
    }
  }
  *parseStream() {
    let line = this.getLine();
    if (line === null)
      return this.setNext("stream");
    if (line[0] === BOM) {
      yield* this.pushCount(1);
      line = line.substring(1);
    }
    if (line[0] === "%") {
      let dirEnd = line.length;
      let cs = line.indexOf("#");
      while (cs !== -1) {
        const ch = line[cs - 1];
        if (ch === " " || ch === "	") {
          dirEnd = cs - 1;
          break;
        } else {
          cs = line.indexOf("#", cs + 1);
        }
      }
      while (true) {
        const ch = line[dirEnd - 1];
        if (ch === " " || ch === "	")
          dirEnd -= 1;
        else
          break;
      }
      const n2 = (yield* this.pushCount(dirEnd)) + (yield* this.pushSpaces(true));
      yield* this.pushCount(line.length - n2);
      this.pushNewline();
      return "stream";
    }
    if (this.atLineEnd()) {
      const sp = yield* this.pushSpaces(true);
      yield* this.pushCount(line.length - sp);
      yield* this.pushNewline();
      return "stream";
    }
    yield DOCUMENT;
    return yield* this.parseLineStart();
  }
  *parseLineStart() {
    const ch = this.charAt(0);
    if (!ch && !this.atEnd)
      return this.setNext("line-start");
    if (ch === "-" || ch === ".") {
      if (!this.atEnd && !this.hasChars(4))
        return this.setNext("line-start");
      const s3 = this.peek(3);
      if ((s3 === "---" || s3 === "...") && isEmpty(this.charAt(3))) {
        yield* this.pushCount(3);
        this.indentValue = 0;
        this.indentNext = 0;
        return s3 === "---" ? "doc" : "stream";
      }
    }
    this.indentValue = yield* this.pushSpaces(false);
    if (this.indentNext > this.indentValue && !isEmpty(this.charAt(1)))
      this.indentNext = this.indentValue;
    return yield* this.parseBlockStart();
  }
  *parseBlockStart() {
    const [ch0, ch1] = this.peek(2);
    if (!ch1 && !this.atEnd)
      return this.setNext("block-start");
    if ((ch0 === "-" || ch0 === "?" || ch0 === ":") && isEmpty(ch1)) {
      const n2 = (yield* this.pushCount(1)) + (yield* this.pushSpaces(true));
      this.indentNext = this.indentValue + 1;
      this.indentValue += n2;
      return yield* this.parseBlockStart();
    }
    return "doc";
  }
  *parseDocument() {
    yield* this.pushSpaces(true);
    const line = this.getLine();
    if (line === null)
      return this.setNext("doc");
    let n2 = yield* this.pushIndicators();
    switch (line[n2]) {
      case "#":
        yield* this.pushCount(line.length - n2);
      // fallthrough
      case void 0:
        yield* this.pushNewline();
        return yield* this.parseLineStart();
      case "{":
      case "[":
        yield* this.pushCount(1);
        this.flowKey = false;
        this.flowLevel = 1;
        return "flow";
      case "}":
      case "]":
        yield* this.pushCount(1);
        return "doc";
      case "*":
        yield* this.pushUntil(isNotAnchorChar);
        return "doc";
      case '"':
      case "'":
        return yield* this.parseQuotedScalar();
      case "|":
      case ">":
        n2 += yield* this.parseBlockScalarHeader();
        n2 += yield* this.pushSpaces(true);
        yield* this.pushCount(line.length - n2);
        yield* this.pushNewline();
        return yield* this.parseBlockScalar();
      default:
        return yield* this.parsePlainScalar();
    }
  }
  *parseFlowCollection() {
    let nl, sp;
    let indent = -1;
    do {
      nl = yield* this.pushNewline();
      if (nl > 0) {
        sp = yield* this.pushSpaces(false);
        this.indentValue = indent = sp;
      } else {
        sp = 0;
      }
      sp += yield* this.pushSpaces(true);
    } while (nl + sp > 0);
    const line = this.getLine();
    if (line === null)
      return this.setNext("flow");
    if (indent !== -1 && indent < this.indentNext && line[0] !== "#" || indent === 0 && (line.startsWith("---") || line.startsWith("...")) && isEmpty(line[3])) {
      const atFlowEndMarker = indent === this.indentNext - 1 && this.flowLevel === 1 && (line[0] === "]" || line[0] === "}");
      if (!atFlowEndMarker) {
        this.flowLevel = 0;
        yield FLOW_END;
        return yield* this.parseLineStart();
      }
    }
    let n2 = 0;
    while (line[n2] === ",") {
      n2 += yield* this.pushCount(1);
      n2 += yield* this.pushSpaces(true);
      this.flowKey = false;
    }
    n2 += yield* this.pushIndicators();
    switch (line[n2]) {
      case void 0:
        return "flow";
      case "#":
        yield* this.pushCount(line.length - n2);
        return "flow";
      case "{":
      case "[":
        yield* this.pushCount(1);
        this.flowKey = false;
        this.flowLevel += 1;
        return "flow";
      case "}":
      case "]":
        yield* this.pushCount(1);
        this.flowKey = true;
        this.flowLevel -= 1;
        return this.flowLevel ? "flow" : "doc";
      case "*":
        yield* this.pushUntil(isNotAnchorChar);
        return "flow";
      case '"':
      case "'":
        this.flowKey = true;
        return yield* this.parseQuotedScalar();
      case ":": {
        const next = this.charAt(1);
        if (this.flowKey || isEmpty(next) || next === ",") {
          this.flowKey = false;
          yield* this.pushCount(1);
          yield* this.pushSpaces(true);
          return "flow";
        }
      }
      // fallthrough
      default:
        this.flowKey = false;
        return yield* this.parsePlainScalar();
    }
  }
  *parseQuotedScalar() {
    const quote = this.charAt(0);
    let end = this.buffer.indexOf(quote, this.pos + 1);
    if (quote === "'") {
      while (end !== -1 && this.buffer[end + 1] === "'")
        end = this.buffer.indexOf("'", end + 2);
    } else {
      while (end !== -1) {
        let n2 = 0;
        while (this.buffer[end - 1 - n2] === "\\")
          n2 += 1;
        if (n2 % 2 === 0)
          break;
        end = this.buffer.indexOf('"', end + 1);
      }
    }
    const qb = this.buffer.substring(0, end);
    let nl = qb.indexOf("\n", this.pos);
    if (nl !== -1) {
      while (nl !== -1) {
        const cs = this.continueScalar(nl + 1);
        if (cs === -1)
          break;
        nl = qb.indexOf("\n", cs);
      }
      if (nl !== -1) {
        end = nl - (qb[nl - 1] === "\r" ? 2 : 1);
      }
    }
    if (end === -1) {
      if (!this.atEnd)
        return this.setNext("quoted-scalar");
      end = this.buffer.length;
    }
    yield* this.pushToIndex(end + 1, false);
    return this.flowLevel ? "flow" : "doc";
  }
  *parseBlockScalarHeader() {
    this.blockScalarIndent = -1;
    this.blockScalarKeep = false;
    let i3 = this.pos;
    while (true) {
      const ch = this.buffer[++i3];
      if (ch === "+")
        this.blockScalarKeep = true;
      else if (ch > "0" && ch <= "9")
        this.blockScalarIndent = Number(ch) - 1;
      else if (ch !== "-")
        break;
    }
    return yield* this.pushUntil((ch) => isEmpty(ch) || ch === "#");
  }
  *parseBlockScalar() {
    let nl = this.pos - 1;
    let indent = 0;
    let ch;
    loop: for (let i4 = this.pos; ch = this.buffer[i4]; ++i4) {
      switch (ch) {
        case " ":
          indent += 1;
          break;
        case "\n":
          nl = i4;
          indent = 0;
          break;
        case "\r": {
          const next = this.buffer[i4 + 1];
          if (!next && !this.atEnd)
            return this.setNext("block-scalar");
          if (next === "\n")
            break;
        }
        // fallthrough
        default:
          break loop;
      }
    }
    if (!ch && !this.atEnd)
      return this.setNext("block-scalar");
    if (indent >= this.indentNext) {
      if (this.blockScalarIndent === -1)
        this.indentNext = indent;
      else {
        this.indentNext = this.blockScalarIndent + (this.indentNext === 0 ? 1 : this.indentNext);
      }
      do {
        const cs = this.continueScalar(nl + 1);
        if (cs === -1)
          break;
        nl = this.buffer.indexOf("\n", cs);
      } while (nl !== -1);
      if (nl === -1) {
        if (!this.atEnd)
          return this.setNext("block-scalar");
        nl = this.buffer.length;
      }
    }
    let i3 = nl + 1;
    ch = this.buffer[i3];
    while (ch === " ")
      ch = this.buffer[++i3];
    if (ch === "	") {
      while (ch === "	" || ch === " " || ch === "\r" || ch === "\n")
        ch = this.buffer[++i3];
      nl = i3 - 1;
    } else if (!this.blockScalarKeep) {
      do {
        let i4 = nl - 1;
        let ch2 = this.buffer[i4];
        if (ch2 === "\r")
          ch2 = this.buffer[--i4];
        const lastChar = i4;
        while (ch2 === " ")
          ch2 = this.buffer[--i4];
        if (ch2 === "\n" && i4 >= this.pos && i4 + 1 + indent > lastChar)
          nl = i4;
        else
          break;
      } while (true);
    }
    yield SCALAR2;
    yield* this.pushToIndex(nl + 1, true);
    return yield* this.parseLineStart();
  }
  *parsePlainScalar() {
    const inFlow = this.flowLevel > 0;
    let end = this.pos - 1;
    let i3 = this.pos - 1;
    let ch;
    while (ch = this.buffer[++i3]) {
      if (ch === ":") {
        const next = this.buffer[i3 + 1];
        if (isEmpty(next) || inFlow && flowIndicatorChars.has(next))
          break;
        end = i3;
      } else if (isEmpty(ch)) {
        let next = this.buffer[i3 + 1];
        if (ch === "\r") {
          if (next === "\n") {
            i3 += 1;
            ch = "\n";
            next = this.buffer[i3 + 1];
          } else
            end = i3;
        }
        if (next === "#" || inFlow && flowIndicatorChars.has(next))
          break;
        if (ch === "\n") {
          const cs = this.continueScalar(i3 + 1);
          if (cs === -1)
            break;
          i3 = Math.max(i3, cs - 2);
        }
      } else {
        if (inFlow && flowIndicatorChars.has(ch))
          break;
        end = i3;
      }
    }
    if (!ch && !this.atEnd)
      return this.setNext("plain-scalar");
    yield SCALAR2;
    yield* this.pushToIndex(end + 1, true);
    return inFlow ? "flow" : "doc";
  }
  *pushCount(n2) {
    if (n2 > 0) {
      yield this.buffer.substr(this.pos, n2);
      this.pos += n2;
      return n2;
    }
    return 0;
  }
  *pushToIndex(i3, allowEmpty) {
    const s3 = this.buffer.slice(this.pos, i3);
    if (s3) {
      yield s3;
      this.pos += s3.length;
      return s3.length;
    } else if (allowEmpty)
      yield "";
    return 0;
  }
  *pushIndicators() {
    switch (this.charAt(0)) {
      case "!":
        return (yield* this.pushTag()) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
      case "&":
        return (yield* this.pushUntil(isNotAnchorChar)) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
      case "-":
      // this is an error
      case "?":
      // this is an error outside flow collections
      case ":": {
        const inFlow = this.flowLevel > 0;
        const ch1 = this.charAt(1);
        if (isEmpty(ch1) || inFlow && flowIndicatorChars.has(ch1)) {
          if (!inFlow)
            this.indentNext = this.indentValue + 1;
          else if (this.flowKey)
            this.flowKey = false;
          return (yield* this.pushCount(1)) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
        }
      }
    }
    return 0;
  }
  *pushTag() {
    if (this.charAt(1) === "<") {
      let i3 = this.pos + 2;
      let ch = this.buffer[i3];
      while (!isEmpty(ch) && ch !== ">")
        ch = this.buffer[++i3];
      return yield* this.pushToIndex(ch === ">" ? i3 + 1 : i3, false);
    } else {
      let i3 = this.pos + 1;
      let ch = this.buffer[i3];
      while (ch) {
        if (tagChars.has(ch))
          ch = this.buffer[++i3];
        else if (ch === "%" && hexDigits.has(this.buffer[i3 + 1]) && hexDigits.has(this.buffer[i3 + 2])) {
          ch = this.buffer[i3 += 3];
        } else
          break;
      }
      return yield* this.pushToIndex(i3, false);
    }
  }
  *pushNewline() {
    const ch = this.buffer[this.pos];
    if (ch === "\n")
      return yield* this.pushCount(1);
    else if (ch === "\r" && this.charAt(1) === "\n")
      return yield* this.pushCount(2);
    else
      return 0;
  }
  *pushSpaces(allowTabs) {
    let i3 = this.pos - 1;
    let ch;
    do {
      ch = this.buffer[++i3];
    } while (ch === " " || allowTabs && ch === "	");
    const n2 = i3 - this.pos;
    if (n2 > 0) {
      yield this.buffer.substr(this.pos, n2);
      this.pos = i3;
    }
    return n2;
  }
  *pushUntil(test) {
    let i3 = this.pos;
    let ch = this.buffer[i3];
    while (!test(ch))
      ch = this.buffer[++i3];
    return yield* this.pushToIndex(i3, false);
  }
};

// node_modules/yaml/browser/dist/parse/line-counter.js
var LineCounter = class {
  constructor() {
    this.lineStarts = [];
    this.addNewLine = (offset) => this.lineStarts.push(offset);
    this.linePos = (offset) => {
      let low = 0;
      let high = this.lineStarts.length;
      while (low < high) {
        const mid = low + high >> 1;
        if (this.lineStarts[mid] < offset)
          low = mid + 1;
        else
          high = mid;
      }
      if (this.lineStarts[low] === offset)
        return { line: low + 1, col: 1 };
      if (low === 0)
        return { line: 0, col: offset };
      const start = this.lineStarts[low - 1];
      return { line: low, col: offset - start + 1 };
    };
  }
};

// node_modules/yaml/browser/dist/parse/parser.js
function includesToken(list, type) {
  for (let i3 = 0; i3 < list.length; ++i3)
    if (list[i3].type === type)
      return true;
  return false;
}
function findNonEmptyIndex(list) {
  for (let i3 = 0; i3 < list.length; ++i3) {
    switch (list[i3].type) {
      case "space":
      case "comment":
      case "newline":
        break;
      default:
        return i3;
    }
  }
  return -1;
}
function isFlowToken(token) {
  switch (token?.type) {
    case "alias":
    case "scalar":
    case "single-quoted-scalar":
    case "double-quoted-scalar":
    case "flow-collection":
      return true;
    default:
      return false;
  }
}
function getPrevProps(parent) {
  switch (parent.type) {
    case "document":
      return parent.start;
    case "block-map": {
      const it = parent.items[parent.items.length - 1];
      return it.sep ?? it.start;
    }
    case "block-seq":
      return parent.items[parent.items.length - 1].start;
    /* istanbul ignore next should not happen */
    default:
      return [];
  }
}
function getFirstKeyStartProps(prev) {
  if (prev.length === 0)
    return [];
  let i3 = prev.length;
  loop: while (--i3 >= 0) {
    switch (prev[i3].type) {
      case "doc-start":
      case "explicit-key-ind":
      case "map-value-ind":
      case "seq-item-ind":
      case "newline":
        break loop;
    }
  }
  while (prev[++i3]?.type === "space") {
  }
  return prev.splice(i3, prev.length);
}
function fixFlowSeqItems(fc) {
  if (fc.start.type === "flow-seq-start") {
    for (const it of fc.items) {
      if (it.sep && !it.value && !includesToken(it.start, "explicit-key-ind") && !includesToken(it.sep, "map-value-ind")) {
        if (it.key)
          it.value = it.key;
        delete it.key;
        if (isFlowToken(it.value)) {
          if (it.value.end)
            Array.prototype.push.apply(it.value.end, it.sep);
          else
            it.value.end = it.sep;
        } else
          Array.prototype.push.apply(it.start, it.sep);
        delete it.sep;
      }
    }
  }
}
var Parser = class {
  /**
   * @param onNewLine - If defined, called separately with the start position of
   *   each new line (in `parse()`, including the start of input).
   */
  constructor(onNewLine) {
    this.atNewLine = true;
    this.atScalar = false;
    this.indent = 0;
    this.offset = 0;
    this.onKeyLine = false;
    this.stack = [];
    this.source = "";
    this.type = "";
    this.lexer = new Lexer();
    this.onNewLine = onNewLine;
  }
  /**
   * Parse `source` as a YAML stream.
   * If `incomplete`, a part of the last line may be left as a buffer for the next call.
   *
   * Errors are not thrown, but yielded as `{ type: 'error', message }` tokens.
   *
   * @returns A generator of tokens representing each directive, document, and other structure.
   */
  *parse(source, incomplete = false) {
    if (this.onNewLine && this.offset === 0)
      this.onNewLine(0);
    for (const lexeme of this.lexer.lex(source, incomplete))
      yield* this.next(lexeme);
    if (!incomplete)
      yield* this.end();
  }
  /**
   * Advance the parser by the `source` of one lexical token.
   */
  *next(source) {
    this.source = source;
    if (this.atScalar) {
      this.atScalar = false;
      yield* this.step();
      this.offset += source.length;
      return;
    }
    const type = tokenType(source);
    if (!type) {
      const message = `Not a YAML token: ${source}`;
      yield* this.pop({ type: "error", offset: this.offset, message, source });
      this.offset += source.length;
    } else if (type === "scalar") {
      this.atNewLine = false;
      this.atScalar = true;
      this.type = "scalar";
    } else {
      this.type = type;
      yield* this.step();
      switch (type) {
        case "newline":
          this.atNewLine = true;
          this.indent = 0;
          if (this.onNewLine)
            this.onNewLine(this.offset + source.length);
          break;
        case "space":
          if (this.atNewLine && source[0] === " ")
            this.indent += source.length;
          break;
        case "explicit-key-ind":
        case "map-value-ind":
        case "seq-item-ind":
          if (this.atNewLine)
            this.indent += source.length;
          break;
        case "doc-mode":
        case "flow-error-end":
          return;
        default:
          this.atNewLine = false;
      }
      this.offset += source.length;
    }
  }
  /** Call at end of input to push out any remaining constructions */
  *end() {
    while (this.stack.length > 0)
      yield* this.pop();
  }
  get sourceToken() {
    const st = {
      type: this.type,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
    return st;
  }
  *step() {
    const top = this.peek(1);
    if (this.type === "doc-end" && top?.type !== "doc-end") {
      while (this.stack.length > 0)
        yield* this.pop();
      this.stack.push({
        type: "doc-end",
        offset: this.offset,
        source: this.source
      });
      return;
    }
    if (!top)
      return yield* this.stream();
    switch (top.type) {
      case "document":
        return yield* this.document(top);
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return yield* this.scalar(top);
      case "block-scalar":
        return yield* this.blockScalar(top);
      case "block-map":
        return yield* this.blockMap(top);
      case "block-seq":
        return yield* this.blockSequence(top);
      case "flow-collection":
        return yield* this.flowCollection(top);
      case "doc-end":
        return yield* this.documentEnd(top);
    }
    yield* this.pop();
  }
  peek(n2) {
    return this.stack[this.stack.length - n2];
  }
  *pop(error) {
    const token = error ?? this.stack.pop();
    if (!token) {
      const message = "Tried to pop an empty stack";
      yield { type: "error", offset: this.offset, source: "", message };
    } else if (this.stack.length === 0) {
      yield token;
    } else {
      const top = this.peek(1);
      if (token.type === "block-scalar") {
        token.indent = "indent" in top ? top.indent : 0;
      } else if (token.type === "flow-collection" && top.type === "document") {
        token.indent = 0;
      }
      if (token.type === "flow-collection")
        fixFlowSeqItems(token);
      switch (top.type) {
        case "document":
          top.value = token;
          break;
        case "block-scalar":
          top.props.push(token);
          break;
        case "block-map": {
          const it = top.items[top.items.length - 1];
          if (it.value) {
            top.items.push({ start: [], key: token, sep: [] });
            this.onKeyLine = true;
            return;
          } else if (it.sep) {
            it.value = token;
          } else {
            Object.assign(it, { key: token, sep: [] });
            this.onKeyLine = !it.explicitKey;
            return;
          }
          break;
        }
        case "block-seq": {
          const it = top.items[top.items.length - 1];
          if (it.value)
            top.items.push({ start: [], value: token });
          else
            it.value = token;
          break;
        }
        case "flow-collection": {
          const it = top.items[top.items.length - 1];
          if (!it || it.value)
            top.items.push({ start: [], key: token, sep: [] });
          else if (it.sep)
            it.value = token;
          else
            Object.assign(it, { key: token, sep: [] });
          return;
        }
        /* istanbul ignore next should not happen */
        default:
          yield* this.pop();
          yield* this.pop(token);
      }
      if ((top.type === "document" || top.type === "block-map" || top.type === "block-seq") && (token.type === "block-map" || token.type === "block-seq")) {
        const last = token.items[token.items.length - 1];
        if (last && !last.sep && !last.value && last.start.length > 0 && findNonEmptyIndex(last.start) === -1 && (token.indent === 0 || last.start.every((st) => st.type !== "comment" || st.indent < token.indent))) {
          if (top.type === "document")
            top.end = last.start;
          else
            top.items.push({ start: last.start });
          token.items.splice(-1, 1);
        }
      }
    }
  }
  *stream() {
    switch (this.type) {
      case "directive-line":
        yield { type: "directive", offset: this.offset, source: this.source };
        return;
      case "byte-order-mark":
      case "space":
      case "comment":
      case "newline":
        yield this.sourceToken;
        return;
      case "doc-mode":
      case "doc-start": {
        const doc = {
          type: "document",
          offset: this.offset,
          start: []
        };
        if (this.type === "doc-start")
          doc.start.push(this.sourceToken);
        this.stack.push(doc);
        return;
      }
    }
    yield {
      type: "error",
      offset: this.offset,
      message: `Unexpected ${this.type} token in YAML stream`,
      source: this.source
    };
  }
  *document(doc) {
    if (doc.value)
      return yield* this.lineEnd(doc);
    switch (this.type) {
      case "doc-start": {
        if (findNonEmptyIndex(doc.start) !== -1) {
          yield* this.pop();
          yield* this.step();
        } else
          doc.start.push(this.sourceToken);
        return;
      }
      case "anchor":
      case "tag":
      case "space":
      case "comment":
      case "newline":
        doc.start.push(this.sourceToken);
        return;
    }
    const bv = this.startBlockValue(doc);
    if (bv)
      this.stack.push(bv);
    else {
      yield {
        type: "error",
        offset: this.offset,
        message: `Unexpected ${this.type} token in YAML document`,
        source: this.source
      };
    }
  }
  *scalar(scalar) {
    if (this.type === "map-value-ind") {
      const prev = getPrevProps(this.peek(2));
      const start = getFirstKeyStartProps(prev);
      let sep;
      if (scalar.end) {
        sep = scalar.end;
        sep.push(this.sourceToken);
        delete scalar.end;
      } else
        sep = [this.sourceToken];
      const map2 = {
        type: "block-map",
        offset: scalar.offset,
        indent: scalar.indent,
        items: [{ start, key: scalar, sep }]
      };
      this.onKeyLine = true;
      this.stack[this.stack.length - 1] = map2;
    } else
      yield* this.lineEnd(scalar);
  }
  *blockScalar(scalar) {
    switch (this.type) {
      case "space":
      case "comment":
      case "newline":
        scalar.props.push(this.sourceToken);
        return;
      case "scalar":
        scalar.source = this.source;
        this.atNewLine = true;
        this.indent = 0;
        if (this.onNewLine) {
          let nl = this.source.indexOf("\n") + 1;
          while (nl !== 0) {
            this.onNewLine(this.offset + nl);
            nl = this.source.indexOf("\n", nl) + 1;
          }
        }
        yield* this.pop();
        break;
      /* istanbul ignore next should not happen */
      default:
        yield* this.pop();
        yield* this.step();
    }
  }
  *blockMap(map2) {
    const it = map2.items[map2.items.length - 1];
    switch (this.type) {
      case "newline":
        this.onKeyLine = false;
        if (it.value) {
          const end = "end" in it.value ? it.value.end : void 0;
          const last = Array.isArray(end) ? end[end.length - 1] : void 0;
          if (last?.type === "comment")
            end?.push(this.sourceToken);
          else
            map2.items.push({ start: [this.sourceToken] });
        } else if (it.sep) {
          it.sep.push(this.sourceToken);
        } else {
          it.start.push(this.sourceToken);
        }
        return;
      case "space":
      case "comment":
        if (it.value) {
          map2.items.push({ start: [this.sourceToken] });
        } else if (it.sep) {
          it.sep.push(this.sourceToken);
        } else {
          if (this.atIndentedComment(it.start, map2.indent)) {
            const prev = map2.items[map2.items.length - 2];
            const end = prev?.value?.end;
            if (Array.isArray(end)) {
              Array.prototype.push.apply(end, it.start);
              end.push(this.sourceToken);
              map2.items.pop();
              return;
            }
          }
          it.start.push(this.sourceToken);
        }
        return;
    }
    if (this.indent >= map2.indent) {
      const atMapIndent = !this.onKeyLine && this.indent === map2.indent;
      const atNextItem = atMapIndent && (it.sep || it.explicitKey) && this.type !== "seq-item-ind";
      let start = [];
      if (atNextItem && it.sep && !it.value) {
        const nl = [];
        for (let i3 = 0; i3 < it.sep.length; ++i3) {
          const st = it.sep[i3];
          switch (st.type) {
            case "newline":
              nl.push(i3);
              break;
            case "space":
              break;
            case "comment":
              if (st.indent > map2.indent)
                nl.length = 0;
              break;
            default:
              nl.length = 0;
          }
        }
        if (nl.length >= 2)
          start = it.sep.splice(nl[1]);
      }
      switch (this.type) {
        case "anchor":
        case "tag":
          if (atNextItem || it.value) {
            start.push(this.sourceToken);
            map2.items.push({ start });
            this.onKeyLine = true;
          } else if (it.sep) {
            it.sep.push(this.sourceToken);
          } else {
            it.start.push(this.sourceToken);
          }
          return;
        case "explicit-key-ind":
          if (!it.sep && !it.explicitKey) {
            it.start.push(this.sourceToken);
            it.explicitKey = true;
          } else if (atNextItem || it.value) {
            start.push(this.sourceToken);
            map2.items.push({ start, explicitKey: true });
          } else {
            this.stack.push({
              type: "block-map",
              offset: this.offset,
              indent: this.indent,
              items: [{ start: [this.sourceToken], explicitKey: true }]
            });
          }
          this.onKeyLine = true;
          return;
        case "map-value-ind":
          if (it.explicitKey) {
            if (!it.sep) {
              if (includesToken(it.start, "newline")) {
                Object.assign(it, { key: null, sep: [this.sourceToken] });
              } else {
                const start2 = getFirstKeyStartProps(it.start);
                this.stack.push({
                  type: "block-map",
                  offset: this.offset,
                  indent: this.indent,
                  items: [{ start: start2, key: null, sep: [this.sourceToken] }]
                });
              }
            } else if (it.value) {
              map2.items.push({ start: [], key: null, sep: [this.sourceToken] });
            } else if (includesToken(it.sep, "map-value-ind")) {
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start, key: null, sep: [this.sourceToken] }]
              });
            } else if (isFlowToken(it.key) && !includesToken(it.sep, "newline")) {
              const start2 = getFirstKeyStartProps(it.start);
              const key = it.key;
              const sep = it.sep;
              sep.push(this.sourceToken);
              delete it.key;
              delete it.sep;
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start: start2, key, sep }]
              });
            } else if (start.length > 0) {
              it.sep = it.sep.concat(start, this.sourceToken);
            } else {
              it.sep.push(this.sourceToken);
            }
          } else {
            if (!it.sep) {
              Object.assign(it, { key: null, sep: [this.sourceToken] });
            } else if (it.value || atNextItem) {
              map2.items.push({ start, key: null, sep: [this.sourceToken] });
            } else if (includesToken(it.sep, "map-value-ind")) {
              this.stack.push({
                type: "block-map",
                offset: this.offset,
                indent: this.indent,
                items: [{ start: [], key: null, sep: [this.sourceToken] }]
              });
            } else {
              it.sep.push(this.sourceToken);
            }
          }
          this.onKeyLine = true;
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const fs = this.flowScalar(this.type);
          if (atNextItem || it.value) {
            map2.items.push({ start, key: fs, sep: [] });
            this.onKeyLine = true;
          } else if (it.sep) {
            this.stack.push(fs);
          } else {
            Object.assign(it, { key: fs, sep: [] });
            this.onKeyLine = true;
          }
          return;
        }
        default: {
          const bv = this.startBlockValue(map2);
          if (bv) {
            if (bv.type === "block-seq") {
              if (!it.explicitKey && it.sep && !includesToken(it.sep, "newline")) {
                yield* this.pop({
                  type: "error",
                  offset: this.offset,
                  message: "Unexpected block-seq-ind on same line with key",
                  source: this.source
                });
                return;
              }
            } else if (atMapIndent) {
              map2.items.push({ start });
            }
            this.stack.push(bv);
            return;
          }
        }
      }
    }
    yield* this.pop();
    yield* this.step();
  }
  *blockSequence(seq2) {
    const it = seq2.items[seq2.items.length - 1];
    switch (this.type) {
      case "newline":
        if (it.value) {
          const end = "end" in it.value ? it.value.end : void 0;
          const last = Array.isArray(end) ? end[end.length - 1] : void 0;
          if (last?.type === "comment")
            end?.push(this.sourceToken);
          else
            seq2.items.push({ start: [this.sourceToken] });
        } else
          it.start.push(this.sourceToken);
        return;
      case "space":
      case "comment":
        if (it.value)
          seq2.items.push({ start: [this.sourceToken] });
        else {
          if (this.atIndentedComment(it.start, seq2.indent)) {
            const prev = seq2.items[seq2.items.length - 2];
            const end = prev?.value?.end;
            if (Array.isArray(end)) {
              Array.prototype.push.apply(end, it.start);
              end.push(this.sourceToken);
              seq2.items.pop();
              return;
            }
          }
          it.start.push(this.sourceToken);
        }
        return;
      case "anchor":
      case "tag":
        if (it.value || this.indent <= seq2.indent)
          break;
        it.start.push(this.sourceToken);
        return;
      case "seq-item-ind":
        if (this.indent !== seq2.indent)
          break;
        if (it.value || includesToken(it.start, "seq-item-ind"))
          seq2.items.push({ start: [this.sourceToken] });
        else
          it.start.push(this.sourceToken);
        return;
    }
    if (this.indent > seq2.indent) {
      const bv = this.startBlockValue(seq2);
      if (bv) {
        this.stack.push(bv);
        return;
      }
    }
    yield* this.pop();
    yield* this.step();
  }
  *flowCollection(fc) {
    const it = fc.items[fc.items.length - 1];
    if (this.type === "flow-error-end") {
      let top;
      do {
        yield* this.pop();
        top = this.peek(1);
      } while (top?.type === "flow-collection");
    } else if (fc.end.length === 0) {
      switch (this.type) {
        case "comma":
        case "explicit-key-ind":
          if (!it || it.sep)
            fc.items.push({ start: [this.sourceToken] });
          else
            it.start.push(this.sourceToken);
          return;
        case "map-value-ind":
          if (!it || it.value)
            fc.items.push({ start: [], key: null, sep: [this.sourceToken] });
          else if (it.sep)
            it.sep.push(this.sourceToken);
          else
            Object.assign(it, { key: null, sep: [this.sourceToken] });
          return;
        case "space":
        case "comment":
        case "newline":
        case "anchor":
        case "tag":
          if (!it || it.value)
            fc.items.push({ start: [this.sourceToken] });
          else if (it.sep)
            it.sep.push(this.sourceToken);
          else
            it.start.push(this.sourceToken);
          return;
        case "alias":
        case "scalar":
        case "single-quoted-scalar":
        case "double-quoted-scalar": {
          const fs = this.flowScalar(this.type);
          if (!it || it.value)
            fc.items.push({ start: [], key: fs, sep: [] });
          else if (it.sep)
            this.stack.push(fs);
          else
            Object.assign(it, { key: fs, sep: [] });
          return;
        }
        case "flow-map-end":
        case "flow-seq-end":
          fc.end.push(this.sourceToken);
          return;
      }
      const bv = this.startBlockValue(fc);
      if (bv)
        this.stack.push(bv);
      else {
        yield* this.pop();
        yield* this.step();
      }
    } else {
      const parent = this.peek(2);
      if (parent.type === "block-map" && (this.type === "map-value-ind" && parent.indent === fc.indent || this.type === "newline" && !parent.items[parent.items.length - 1].sep)) {
        yield* this.pop();
        yield* this.step();
      } else if (this.type === "map-value-ind" && parent.type !== "flow-collection") {
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        fixFlowSeqItems(fc);
        const sep = fc.end.splice(1, fc.end.length);
        sep.push(this.sourceToken);
        const map2 = {
          type: "block-map",
          offset: fc.offset,
          indent: fc.indent,
          items: [{ start, key: fc, sep }]
        };
        this.onKeyLine = true;
        this.stack[this.stack.length - 1] = map2;
      } else {
        yield* this.lineEnd(fc);
      }
    }
  }
  flowScalar(type) {
    if (this.onNewLine) {
      let nl = this.source.indexOf("\n") + 1;
      while (nl !== 0) {
        this.onNewLine(this.offset + nl);
        nl = this.source.indexOf("\n", nl) + 1;
      }
    }
    return {
      type,
      offset: this.offset,
      indent: this.indent,
      source: this.source
    };
  }
  startBlockValue(parent) {
    switch (this.type) {
      case "alias":
      case "scalar":
      case "single-quoted-scalar":
      case "double-quoted-scalar":
        return this.flowScalar(this.type);
      case "block-scalar-header":
        return {
          type: "block-scalar",
          offset: this.offset,
          indent: this.indent,
          props: [this.sourceToken],
          source: ""
        };
      case "flow-map-start":
      case "flow-seq-start":
        return {
          type: "flow-collection",
          offset: this.offset,
          indent: this.indent,
          start: this.sourceToken,
          items: [],
          end: []
        };
      case "seq-item-ind":
        return {
          type: "block-seq",
          offset: this.offset,
          indent: this.indent,
          items: [{ start: [this.sourceToken] }]
        };
      case "explicit-key-ind": {
        this.onKeyLine = true;
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        start.push(this.sourceToken);
        return {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start, explicitKey: true }]
        };
      }
      case "map-value-ind": {
        this.onKeyLine = true;
        const prev = getPrevProps(parent);
        const start = getFirstKeyStartProps(prev);
        return {
          type: "block-map",
          offset: this.offset,
          indent: this.indent,
          items: [{ start, key: null, sep: [this.sourceToken] }]
        };
      }
    }
    return null;
  }
  atIndentedComment(start, indent) {
    if (this.type !== "comment")
      return false;
    if (this.indent <= indent)
      return false;
    return start.every((st) => st.type === "newline" || st.type === "space");
  }
  *documentEnd(docEnd) {
    if (this.type !== "doc-mode") {
      if (docEnd.end)
        docEnd.end.push(this.sourceToken);
      else
        docEnd.end = [this.sourceToken];
      if (this.type === "newline")
        yield* this.pop();
    }
  }
  *lineEnd(token) {
    switch (this.type) {
      case "comma":
      case "doc-start":
      case "doc-end":
      case "flow-seq-end":
      case "flow-map-end":
      case "map-value-ind":
        yield* this.pop();
        yield* this.step();
        break;
      case "newline":
        this.onKeyLine = false;
      // fallthrough
      case "space":
      case "comment":
      default:
        if (token.end)
          token.end.push(this.sourceToken);
        else
          token.end = [this.sourceToken];
        if (this.type === "newline")
          yield* this.pop();
    }
  }
};

// node_modules/yaml/browser/dist/public-api.js
function parseOptions(options) {
  const prettyErrors = options.prettyErrors !== false;
  const lineCounter = options.lineCounter || prettyErrors && new LineCounter() || null;
  return { lineCounter, prettyErrors };
}
function parseDocument(source, options = {}) {
  const { lineCounter, prettyErrors } = parseOptions(options);
  const parser = new Parser(lineCounter?.addNewLine);
  const composer = new Composer(options);
  let doc = null;
  for (const _doc of composer.compose(parser.parse(source), true, source.length)) {
    if (!doc)
      doc = _doc;
    else if (doc.options.logLevel !== "silent") {
      doc.errors.push(new YAMLParseError(_doc.range.slice(0, 2), "MULTIPLE_DOCS", "Source contains multiple documents; please use YAML.parseAllDocuments()"));
      break;
    }
  }
  if (prettyErrors && lineCounter) {
    doc.errors.forEach(prettifyError(source, lineCounter));
    doc.warnings.forEach(prettifyError(source, lineCounter));
  }
  return doc;
}

// src/i18n/catalog.mjs
function parsePack(source, name) {
  const document2 = parseDocument(source, { uniqueKeys: true });
  if (document2.errors.length) throw new Error(`${name}: ${document2.errors[0].message}`);
  const data = document2.toJS({ maxAliasCount: 0 });
  if (!data || typeof data !== "object" || Array.isArray(data)) throw new Error(`${name}: \uBC88\uC5ED \uAC1D\uCCB4\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4.`);
  for (const [key, value] of Object.entries(data)) {
    if (!/^[a-z][A-Za-z0-9]*$/.test(key) || typeof value !== "string" || !value.trim()) throw new Error(`${name}: \uC798\uBABB\uB41C \uBC88\uC5ED ${key}`);
  }
  return data;
}
var parameters = (text) => [...new Set([...text.matchAll(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g)].map((match) => match[1]))].sort();
function validatePair(base, translated, name) {
  if (Object.keys(base).sort().join("\n") !== Object.keys(translated).sort().join("\n")) throw new Error(`${name}: \uBC88\uC5ED \uD0A4\uAC00 \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.`);
  for (const key of Object.keys(base)) {
    if (parameters(base[key]).join() !== parameters(translated[key]).join()) throw new Error(`${name}.${key}: \uCE58\uD658 \uBCC0\uC218\uAC00 \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.`);
  }
}
function formatMessage(message, values = {}) {
  if (parameters(message).join() !== Object.keys(values).sort().join()) throw new Error("\uBC88\uC5ED \uCE58\uD658 \uBCC0\uC218\uAC00 \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.");
  return message.replace(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g, (_2, key) => String(values[key]));
}

// src/i18n/index.ts
var STORAGE_KEY = "slime.locale";
var sources = { "./locales/ko/achievements.yaml": 'title: "\uC5C5\uC801"\naway: "\uC790\uB9AC\uBE44\uC6C0 \xB7 \uB9F5\uC5D0\uC11C\uC758 \uC774\uB3D9\uACFC \uC870\uC6B0\uAC00 \uC911\uB2E8\uB429\uB2C8\uB2E4."\nreturn: "\uBA54\uB274\uB85C \uB3CC\uC544\uAC00\uAE30"\nretry: "\uB2E4\uC2DC \uBD88\uB7EC\uC624\uAE30"\nloading: "\uC5C5\uC801\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\uC785\uB2C8\uB2E4."\nbalance: "\uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uC131\uC7A5 \uD3EC\uC778\uD2B8"\nunsupported: "\uD655\uC778 \uD544\uC694"\nbalanceHelp: "\uD604\uC7AC \uC794\uACE0\uC785\uB2C8\uB2E4. \uC544\uB798 \uC9C0\uAE09 \uB0B4\uC5ED\uC758 \uB204\uC801 \uD68D\uB4DD\uB7C9\uACFC\uB294 \uB2E4\uB985\uB2C8\uB2E4."\ncategory: "\uC5C5\uC801 \uBD84\uB958"\ngeneral: "\uC77C\uBC18\uC5C5\uC801"\nseasonal: "\uC2DC\uC98C\uC5C5\uC801"\ncompletedCount: "{done}/{total} \uB2EC\uC131"\nseason: "\uD604\uC7AC \uC2DC\uC98C: {season}"\nempty: "\uB4F1\uB85D\uB41C \uC5C5\uC801\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."\ncomplete: "\uB2EC\uC131 \uC644\uB8CC"\ninProgress: "\uC9C4\uD589 \uC911"\nreward: "\uBCF4\uC0C1"\nskill: "\uC2A4\uD0AC \uD68D\uB4DD: {name}"\nhistory: "\uD3EC\uC778\uD2B8 \uC9C0\uAE09 \uB0B4\uC5ED \xB7 {count}\uAC74"\nhistoryHelp: "\uC120\uD0DD\uD55C \uC2DC\uC98C\uACFC \uBD84\uB958\uC758 \uC9C0\uAE09 \uAE30\uB85D\uC785\uB2C8\uB2E4. CP\uC640 SP\uB294 \uAC01\uAC01 \uAE30\uB85D\uB429\uB2C8\uB2E4."\nnoHistory: "\uC544\uC9C1 \uC9C0\uAE09 \uB0B4\uC5ED\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."\nsupplement: "\uC18C\uAE09 \uBCF4\uC644 \uC9C0\uAE09"\nawarded: "\uC5C5\uC801 \uB2EC\uC131 \uC9C0\uAE09"\nviewSeason: "\uC870\uD68C\uD560 \uC2DC\uC98C"\ncurrentSeason: "\uD604\uC7AC \uC2DC\uC98C"\narchivedHelp: "\uC774\uC804 \uC2DC\uC98C\uC758 \uAE30\uB85D\uC785\uB2C8\uB2E4. \uB2F9\uC2DC \uBCF4\uC0C1\uC740 \uD604\uC7AC \uC794\uACE0\uC5D0 \uD3EC\uD568\uB418\uC9C0 \uC54A\uC73C\uBA70 \uB2E4\uC2DC \uC9C0\uAE09\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\npagination: \uC5C5\uC801 \uD398\uC774\uC9C0 \uC774\uB3D9\nhistoryPagination: \uD3EC\uC778\uD2B8 \uC9C0\uAE09 \uB0B4\uC5ED \uD398\uC774\uC9C0 \uC774\uB3D9\nprevious: \uC774\uC804\nnext: \uB2E4\uC74C\npage: "{page} / {total}\uD398\uC774\uC9C0"\n', "./locales/ko/app.yaml": 'reportRegion: "\uC804\uD22C \uACB0\uACFC \uD655\uC778"\nmenu: "\uBA54\uB274"\nbackToMap: "\uB9F5\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30"\ngameMenu: "\uAC8C\uC784 \uBA54\uB274"\ncharacterNavigation: "\uCE90\uB9AD\uD130 \uC124\uC815 \uD398\uC774\uC9C0 \uC774\uB3D9"\nback: "\uB3CC\uC544\uAC00\uAE30"\ncharacterSelectLink: "\uCE90\uB9AD\uD130 \uC120\uD0DD\uC73C\uB85C"\ncharacterSelect: "\uCE90\uB9AD\uD130 \uC120\uD0DD"\ncharacterCreate: "\uCE90\uB9AD\uD130 \uC0DD\uC131"\nmyCharacter: "\uB0B4 \uCE90\uB9AD\uD130"\ncontinueAdventure: "\uC774 \uCE90\uB9AD\uD130\uB85C \uBAA8\uD5D8\uC744 \uC774\uC5B4\uAC00\uC138\uC694."\ncharacterSettings: "\uCE90\uB9AD\uD130 \uC124\uC815"\ncharacterLimit: "\uCE90\uB9AD\uD130 1 / 1 \xB7 \uACC4\uC815\uB2F9 \uD55C \uBA85\uC758 \uCE90\uB9AD\uD130\uB97C \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nnoCharacter: "\uC544\uC9C1 \uCE90\uB9AD\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uCCAB \uBAA8\uD5D8\uAC00\uB97C \uB9CC\uB4E4\uC5B4 \uC8FC\uC138\uC694."\ncreateLimit: "\uACC4\uC815\uB2F9 \uD55C \uBA85\uC758 \uCE90\uB9AD\uD130\uB97C \uC0DD\uC131\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\ncreating: "\uC0DD\uC131 \uC911\u2026"\nmapMenu: "\uB9F5 \uBA54\uB274"\nbattleMap: "\uC804\uD22C\uD544\uB4DC \uCE74\uB4DC"\nfieldMap: "\uC57C\uC678\uD544\uB4DC \uCE74\uB4DC"\ncameraControls: "\uB9F5 \uD654\uBA74 \uC870\uC815"\nzoomOut: "\uB9F5 \uCD95\uC18C"\nzoomIn: "\uB9F5 \uD655\uB300"\nrotateLeft: "\uB9F5 \uC67C\uCABD\uC73C\uB85C 90\uB3C4 \uD68C\uC804"\nrotateRight: "\uB9F5 \uC624\uB978\uCABD\uC73C\uB85C 90\uB3C4 \uD68C\uC804"\nresetView: "\uC2DC\uC810 \uBCF5\uADC0"\nmapExplore: "\uB9F5 \uD0D0\uC0C9 \xB7 \uBC29\uD5A5\uD0A4\uB85C \uC704\uCE58 \uC120\uD0DD"\nfieldControls: "\uC57C\uC678\uD544\uB4DC \uC870\uC791 \uCE74\uB4DC"\nreconnectHelp: "\uD654\uBA74\uC744 \uBCF5\uAD6C\uD558\uB824\uBA74 \uB2E4\uC2DC \uC811\uC18D\uD558\uC138\uC694."\nconnectingHelp: "\uC11C\uBC84\uC5D0 \uC5F0\uACB0 \uC911\uC785\uB2C8\uB2E4. \uC5F0\uACB0 \uD6C4 \uD589\uB3D9\uD560 \uC218 \uC788\uC5B4\uC694."\npreparingMap: "\uB9F5\uC744 \uC900\uBE44\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4."\nprocessing: "\uC694\uCCAD\uC744 \uCC98\uB9AC\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4."\nfieldHelp: "\uC57C\uC678\uD544\uB4DC \uB3C4\uC6C0\uB9D0 \uCE74\uB4DC"\nfieldControlsHelp: "\uB9F5\uC744 \uD074\uB9AD\uD558\uAC70\uB098 \uB9F5\uC5D0 \uCD08\uC810\uC744 \uB9DE\uCD98 \uB4A4 \uBC29\uD5A5\uD0A4\uB85C \uC120\uD0DD\uD558\uC138\uC694. \uB9F5\uC744 \uB04C\uC5B4 \uC2DC\uC810\uC744 \uC774\uB3D9\uD558\uACE0 \uD720\uC774\uB098 \uD655\uB300\xB7\uCD95\uC18C \uBC84\uD2BC\uC744 \uC0AC\uC6A9\uD558\uC138\uC694. \u21B6\xB7\u21B7 \uBC84\uD2BC\uC73C\uB85C 90\uB3C4\uC529 \uD68C\uC804\uD558\uC5EC \uB192\uC740 \uC9C0\uD615 \uB4A4\uB97C \uD655\uC778\uD558\uC138\uC694."\nbattleLegend: "\uD30C\uB791: \uC774\uB3D9 \xB7 \uBC88\uD638\uC120: \uACBD\uB85C \xB7 \uC8FC\uD669: \uB3C4\uCC29 \uD6C4 \uACF5\uACA9 \uBC94\uC704"\nreserved: "\uC870\uC6B0 \uC900\uBE44 \uC911"\nexploring: "\uD0D0\uC0C9 \uC911"\nselectCell: "\uC140\uC744 \uC120\uD0DD\uD558\uC138\uC694"\nkeyboardHelp: "\xB7 \uBC29\uD5A5\uD0A4 \uC120\uD0DD / \uD720 \uD655\uB300"\nsettlementHelp: "\uC815\uC0B0\uC744 \uAE30\uB2E4\uB9B0 \uB4A4 \uC2DC\uC791\uC810\uC5D0\uC11C \uC785\uC7A5\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nnearbyHeading: "\uC8FC\uBCC0 \uD0D0\uC0C9\uACFC \uC6E8\uC774\uD3EC\uC778\uD2B8"\npartyHeading: "\uD568\uAED8 \uD0D0\uC0C9\uD558\uAE30"\nchat: "\uB300\uD654"\nleaveParty: "\uD30C\uD2F0 \uD0C8\uD1F4"\ndisbandParty: "\uD30C\uD2F0 \uD574\uC0B0"\ncreateParty: "\uD30C\uD2F0 \uB9CC\uB4E4\uAE30"\nkick: "\uCD94\uBC29"\ninvite: "\uCD08\uB300"\npartyCpOutOfRange: "\uB204\uC801 CP \uC870\uAC74 \uBBF8\uCDA9\uC871 (\uD30C\uD2F0\uC7A5 \uAE30\uC900 \xB120%)"\ncommandBusy: "\uBA85\uB839 \uCC98\uB9AC \uC911\u2026"\nloadingRegion: "\uACF5\uAC04 \uC774\uB3D9 \uB85C\uB529"\nloadingFailed: "\uB85C\uB529\uC5D0 \uC2E4\uD328\uD588\uC2B5\uB2C8\uB2E4"\nloading: "\uB85C\uB529 \uC911\u2026"\nreconnect: "\uB2E4\uC2DC \uC811\uC18D"\ninvitationCount: " \xB7 \uCD08\uB300 {count}"\npartySummary: "\uD30C\uD2F0 {count}/4 \xB7 \uD30C\uD2F0\uC7A5 {leader}"\nacceptInvitation: "{name}\uB2D8\uC758 \uCD08\uB300 \uC218\uB77D"\nposition: "\uB0B4 \uC704\uCE58 {column}, {row} \xB7 {status}"\nselectedTile: "\uC120\uD0DD {column}, {row}"\nselectedBlocked: "\uC120\uD0DD {column}, {row} \xB7 \uC774\uB3D9 \uBD88\uAC00"\nresultSummary: "{result} \xB7 \uC7AC\uD654 +{coins}"\nrecentBattle: "\uCD5C\uADFC \uC804\uD22C"\nbattleHeading: "{name} \xB7 \uB77C\uC6B4\uB4DC {round}"\nbattlefield: "\uC804\uC220 \uC804\uC7A5"\nwebglReconnect: "WebGL \uD654\uBA74\uC744 \uBCF5\uAD6C\uD558\uB824\uBA74 \uB2E4\uC2DC \uC811\uC18D\uD558\uC138\uC694."\nwebglUnsupported: "\uC774 \uBE0C\uB77C\uC6B0\uC800\uC5D0\uC11C WebGL\uC744 \uC2E4\uD589\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4."\nsessionRelogin: "\uB2E4\uC2DC \uB85C\uADF8\uC778\uD574 \uC8FC\uC138\uC694. \uC11C\uBC84\uC758 \uAE30\uC874 \uC804\uD22C\uB294 \uACC4\uC18D \uC9C4\uD589\uB429\uB2C8\uB2E4."\nloggedOut: "\uB85C\uADF8\uC544\uC6C3\uD588\uC2B5\uB2C8\uB2E4."\nnoRouteError: "\uD604\uC7AC \uC704\uCE58\uC5D0\uC11C \uAC08 \uC218 \uC788\uB294 \uACBD\uB85C\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."\nmovementFpError: "\uC774\uB3D9\uC5D0 \uD544\uC694\uD55C FP\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4. 1\uCE78\uB2F9 1 FP\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4."\n\nbag: "\uAC00\uBC29"\nemptyBag: "\uAC00\uBC29\uC774 \uBE44\uC5B4 \uC788\uC2B5\uB2C8\uB2E4."\nbagUnavailable: "\uAC00\uBC29 \uC815\uBCF4\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC5F0\uACB0\uD574 \uC8FC\uC138\uC694."\n\nbagWeight: "\uD655\uC778\uB41C \uBB34\uAC8C {weight}g / \uC18C\uC9C0 \uAE30\uC900 {capacity}g"\nbagUnknownWeight: "\uC18C\uC9C0\uD488 {count}\uAC1C\uC758 \uBB34\uAC8C\uAC00 \uC544\uC9C1 \uC815\uD574\uC9C0\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4."\nitemWeight: "\uAC1C\uB2F9 {weight}g"\n\nfieldHelpSelect: "\uB9F5\uC774\uB098 \uC8FC\uBCC0 \uC20F\uCEF7\uC5D0\uC11C \uBAA9\uC801\uC9C0\uB97C \uC120\uD0DD\uD558\uC138\uC694. \uC774\uB3D9\xB7\uC870\uC6B0\uB294 \uC704 \uC870\uC791 \uCE74\uB4DC\uC5D0\uC11C \uC2E4\uD589\uD569\uB2C8\uB2E4."\nfieldHelpEncounter: "\uC870\uC791 \uCE74\uB4DC\uC5D0\uC11C \uC811\uADFC\xB7\uC870\uC6B0\uB97C \uC120\uD0DD\uD558\uC138\uC694. \uC774\uB984 \uC0C9\uC740 \uC120\uACF5 \uC5EC\uBD80\uC774\uBA70, \uC704\uD5D8\uB3C4\uB294 \uC815\uCC30\uD574\uC57C \uC54C \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nfieldHelpSelection: "\uCE90\uB9AD\uD130\xB7\uBAAC\uC2A4\uD130\uB97C \uB204\uB974\uBA74 \uBC1C\uBC11 \uD0C0\uC77C\uC744 \uC120\uD0DD\uD569\uB2C8\uB2E4. \uACB9\uCE5C \uC601\uC5ED\uC740 \uBC18\uBCF5\uD574\uC11C \uB20C\uB7EC \uB300\uC0C1\uC744 \uBC14\uAFC9\uB2C8\uB2E4. \uBC29\uD5A5\uD0A4\uB85C\uB3C4 \uD0C0\uC77C\uC744 \uC120\uD0DD\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nfieldHelpCamera: "\uC2DC\uC810 \xB7 \uB4DC\uB798\uADF8 / \uD655\uB300 \xB7 \uD720\xB7\xB1 / \uD68C\uC804 \xB7 \u21B6\u21B7"\nfieldHelpReset: "\uC870\uC900\uC810 \xB7 \uB0B4 \uC704\uCE58\uC640 \uAE30\uBCF8 \uBC30\uC728\uB85C \uBCF5\uADC0"\ncurrentCharacter: \uD604\uC7AC \uCE90\uB9AD\uD130\n\nbagLoading: "\uC18C\uC9C0\uD488\uACFC \uBB34\uAC8C\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4."\nbagChanged: "\uAC00\uBC29\uC774 \uBCC0\uACBD\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC0C8\uB85C\uACE0\uCE68\uD574 \uC8FC\uC138\uC694."\nbagMaterials: "\uC7AC\uB8CC\xB7\uC18C\uBAA8\uD488"\nuseHealingItem: "{count}\uAC1C \uC0AC\uC6A9 \xB7 HP +{amount}"\nuseMarkerItem: "{count}\uAC1C \uC0AC\uC6A9 \xB7 \uD604\uC7AC \uC704\uCE58\uC5D0 \uAC1C\uC778 \uD45C\uC2DD {seconds}\uCD08"\n\nworldMap: "\uC6D4\uB4DC\uB9F5"\nmapTown: "\uB9C8\uC744\uD544\uB4DC"\nmapField: "\uC57C\uC678\uD544\uB4DC"\nmapUnknownKind: "\uC5F0\uACB0 \uB9F5"\nworldMapHelp: "\uC804\uCCB4 \uB9F5\uC758 \uC0C1\uB300 \uBC30\uCE58\uC640 \uC5F0\uACB0\uC744 \uD0D0\uC0C9\uD569\uB2C8\uB2E4. \uC9C0\uB3C4\uB97C \uB4DC\uB798\uADF8\uD574 \uC774\uB3D9\uD558\uACE0 \uBC84\uD2BC \uB610\uB294 \uB9C8\uC6B0\uC2A4 \uD720\uB85C \uD655\uB300\xB7\uCD95\uC18C\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uB9F5\uC744 \uC120\uD0DD\uD558\uBA74 \uC5F0\uACB0\uB41C \uC9C0\uC5ED\uC744 \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC2E4\uC81C \uC774\uB3D9\uC740 \uD544\uB4DC\uC758 \uC6E8\uC774\uD3EC\uC778\uD2B8\uC5D0\uC11C \uC9C4\uD589\uD569\uB2C8\uB2E4."\nworldMapCurrent: "\uD604\uC7AC \uC704\uCE58"\nworldMapConnections: "\uC5F0\uACB0\uB41C \uC9C0\uC5ED"\nworldMapLoading: "\uC6D4\uB4DC\uB9F5\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\u2026"\nworldMapRetry: "\uB2E4\uC2DC \uC2DC\uB3C4"\nmapAssetsFailed: "\uB9F5 \uC790\uC6D0\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC811\uC18D\uD574 \uC8FC\uC138\uC694."\nmapSceneFailed: "\uB9F5 \uD654\uBA74\uC744 \uAD6C\uC131\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC811\uC18D\uD574 \uC8FC\uC138\uC694."\n\nbagSupplies: "\uC218\uC9D1\uD488\xB7\uC7AC\uB8CC\xB7\uC18C\uBAA8\uD488"\nbagCollection: "\uC218\uC9D1\uD488 \xB7 \uC815\uC81C \uC804 \uC6D0\uBB3C"\nbagRefinedMaterial: "\uC815\uC81C \uC7AC\uB8CC"\nrefiningGradeLow: "\uD558\uAE09"\nrefiningGradeMedium: "\uC911\uAE09"\nrefiningGradeHigh: "\uC0C1\uAE09"\n\npartyListedMembers: "\uBAA9\uB85D \uC778\uC6D0 {count}\uBA85"\n\nonlinePartyUnavailable: \uC628\uB77C\uC778 \uD30C\uD2F0\uB294 \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uAE38\uB4DC\uC758 \uBAA8\uD5D8\uAC00 \uB300\uC5EC\xB7\uD3B8\uC131\uC744 \uC774\uC6A9\uD558\uC138\uC694.\n\ntownMap: "\uB9C8\uC744\uD544\uB4DC \uCE74\uB4DC"\n\ndeveloperTitle: "\uAC1C\uBC1C\uC790 \uB3C4\uAD6C"\ndeveloperInvalid: "\uAC1C\uBC1C\uC790 API \uC751\uB2F5\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\ndeveloperConfirm: "{asset} \uC794\uACE0\uB97C {before}\uC5D0\uC11C {after}\uB85C \uBCC0\uACBD\uD560\uAE4C\uC694?"\ndeveloperCompleted: "\uC870\uC815\uC744 \uC644\uB8CC\uD588\uC2B5\uB2C8\uB2E4."\ndeveloperSelf: "\uB85C\uCEEC \uAC1C\uBC1C\uC790 \uBCF8\uC778 \uCE90\uB9AD\uD130 \uC804\uC6A9\uC785\uB2C8\uB2E4."\ndeveloperRefresh: "\uCD5C\uC2E0 \uC0C1\uD0DC \uC870\uD68C"\ndeveloperBalance: "\uC7AC\uC0B0 \uC870\uC815"\ndeveloperAsset: "\uC870\uC815 \uB300\uC0C1"\ndeveloperOperation: "\uC791\uC5C5"\ndeveloperAdd: "\uCD94\uAC00"\ndeveloperRemove: "\uC0AD\uC81C"\ndeveloperQuantity: "\uC218\uB7C9 (1~1,000,000,000)"\ndeveloperApply: "\uBCC0\uACBD \uD655\uC778"\ndeveloperFieldOnly: "\uD544\uB4DC \uB300\uAE30 \uC0C1\uD0DC\uC5D0\uC11C \uC870\uC815\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC804\uD22C\xB7\uC870\uC6B0 \uC900\uBE44\uB97C \uB9C8\uCE58\uC138\uC694."\ndeveloperUncertain: "\uACB0\uACFC\uAC00 \uBD88\uBA85\uD655\uD569\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC744 \uC7AC\uD655\uC778\uD558\uC138\uC694."\ndeveloperRetry: "\uB3D9\uC77C \uC694\uCCAD \uC7AC\uD655\uC778"\ndeveloperHistory: "\uBCC0\uACBD \uC774\uB825"\ndeveloperNext: "\uB2E4\uC74C \uC774\uB825"\n\ndeveloperItems: "\uC544\uC774\uD15C \uC870\uC815"\ndeveloperSearch: "\uD488\uBAA9 \uAC80\uC0C9"\ndeveloperSelectItem: "\uD488\uBAA9\uC744 \uC120\uD0DD\uD558\uC138\uC694"\ndeveloperCardQuantity: "\uC2A4\uD0AC\uCE74\uB4DC\uB294 \uD55C \uBC88\uC5D0 1\uAC1C\uB9CC \uC870\uC815\uD569\uB2C8\uB2E4. \uC9C0\uAE09\uC740 \uC790\uB3D9 \uC2B5\uB4DD\uC774 \uC544\uB2C8\uBA70, \uBCF4\uAD00\uD568\uC5D0\uC11C \uBB38\uD574 \uC870\uAC74\uC744 \uCDA9\uC871\uD55C \uB4A4 \uC0AC\uC6A9\uD558\uC138\uC694."\ndeveloperEquipmentQuantity: "\uC7A5\uBE44\uB294 \uD55C \uBC88\uC5D0 1\uAC1C\uB97C \uC870\uC815\uD569\uB2C8\uB2E4. \uD68C\uC218\uB294 \uC7A5\uCC29\xB7\uC218\uB9AC \uC911\uC774 \uC544\uB2CC \uAC1C\uCCB4\uB97C \uC120\uD0DD\uD558\uC138\uC694."\ndeveloperInstance: "\uD68C\uC218\uD560 \uC7A5\uBE44 \uAC1C\uCCB4"\ndeveloperEquipmentLocked: "\uC7A5\uCC29\xB7\uC218\uB9AC \uC911: \uD574\uC81C \uB610\uB294 \uC218\uB9AC \uC218\uB839 \uD6C4 \uC774\uC6A9"\ndeveloperPermitDuration: "\uC99D\uC11C\uB294 \uD55C \uBC88\uC5D0 1\uAC1C\uB97C \uC9C0\uAE09\uD558\uBA70 \uBC1C\uAE09 \uC2DC\uAC01\uBD80\uD130 7\uC77C\uAC04 \uC720\uD6A8\uD569\uB2C8\uB2E4."\ndeveloperPermitCity: "\uB3C4\uC2DC"\ndeveloperPermitIssuer: "\uACBD\uBE44\uC13C\uD130 \uBC1C\uAE09\uCC98"\ndeveloperPermitInstance: "\uD68C\uC218\uD560 \uC99D\uC11C \xB7 \uB3C4\uC2DC \xB7 \uB9CC\uB8CC\uC77C \xB7 \uAC1C\uCCB4 ID"\n\ndeveloperBatchLevel: "\uC9C0\uAE09\uD560 \uC0DD\uC0B0 \uB808\uBCA8"\ndeveloperBatchInstance: "\uD68C\uC218\uD560 \uBC30\uCE58 \xB7 \uB808\uBCA8 \xB7 \uBCF4\uC720 \uC218\uB7C9 \xB7 ID"\n\ndeveloperCancel: "\uCDE8\uC18C"\ndeveloperProceed: "\uC870\uC815 \uC2E4\uD589"\n\ndeveloperInvalidQuantity: "\uC218\uB7C9\uC740 1~1,000,000,000 \uC0AC\uC774\uC758 \uC815\uC218\uB85C \uC785\uB825\uD558\uC138\uC694."\ndeveloperSelectionRequired: "\uD488\uBAA9\uACFC \uD544\uC694\uD55C \uB808\uBCA8\xB7\uAC1C\uCCB4\xB7\uBC30\uCE58\xB7\uBC1C\uAE09\uCC98\uB97C \uC120\uD0DD\uD558\uC138\uC694. \uAC1C\uCCB4\uD615 \uC544\uC774\uD15C\uC758 \uC218\uB7C9\uC740 1\uC774\uC5B4\uC57C \uD569\uB2C8\uB2E4."\ndeveloperInsufficientBalance: "\uD68C\uC218 \uC218\uB7C9\uC774 \uBCF4\uC720\uB7C9\uBCF4\uB2E4 \uB9CE\uC2B5\uB2C8\uB2E4. \uBCF4\uC720\uB7C9 \uC774\uD558\uB85C \uC904\uC774\uC138\uC694."\n\nbagCategory: \uAC00\uBC29 \uBD84\uB958\nbagCategoryEmpty: \uC774 \uBD84\uB958\uC5D0 \uBCF4\uC720\uD55C \uC544\uC774\uD15C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\nbagSuppliesPagination: \uC7AC\uB8CC\xB7\uC18C\uBAA8\uD488 \uD398\uC774\uC9C0 \uC774\uB3D9\nbagPreviousPage: \uC774\uC804\nbagNextPage: \uB2E4\uC74C\nbagPageNumber: "{page} / {total}\uD398\uC774\uC9C0"\nbagEquipmentPagination: \uC7A5\uBE44 \uD398\uC774\uC9C0 \uC774\uB3D9\nbagEquipmentPage: "{page}\uD398\uC774\uC9C0"\n\ndeveloperResetTitle: "\uCE90\uB9AD\uD130 \uC804\uCCB4 \uCD08\uAE30\uD654"\ndeveloperResetDescription: "\uCE90\uB9AD\uD130\xB7\uC7AC\uC0B0\xB7\uBCF4\uAD00\uD568\xB7\uCF54\uC2A4\uD2AC\xB7\uC774\uC804 \uC2DC\uC98C \uAE30\uB85D\uC744 \uBAA8\uB450 \uC0AD\uC81C\uD569\uB2C8\uB2E4. \uBCF5\uAD6C\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uACC4\uC815\uACFC \uBE44\uBC00\uBC88\uD638\uB294 \uC720\uC9C0\uB418\uBA70 \uB2E4\uC2DC \uB85C\uADF8\uC778\uD558\uBA74 \uCE90\uB9AD\uD130 \uC0DD\uC131 \uC804 \uC0C1\uD0DC\uB85C \uC2DC\uC791\uD569\uB2C8\uB2E4."\ndeveloperResetConfirm: "\uD655\uC778\uD558\uB824\uBA74 RESET test\uB97C \uC785\uB825\uD558\uC138\uC694."\ndeveloperResetUncertain: "\uCD08\uAE30\uD654 \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC73C\uB85C \uACB0\uACFC\uB97C \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694."\n', "./locales/ko/auth.yaml": 'illustration: \uC232\uC18D \uAF43\uBC2D\uC758 \uAC10\uAC01\uAE30\uAD00 \uC5C6\uB294 \uBC18\uD22C\uBA85 \uCCAD\uB85D\uC0C9 \uC2AC\uB77C\uC784\neyebrow: \uB098\uB9CC\uC758 \uC18D\uB3C4\uB85C, \uC0C8\uB85C\uC6B4 \uC2DC\uAC04\nheadline: \uCC9C\uCC9C\uD788 \uBA38\uBB3C\uACE0,\nemphasis: \uD568\uAED8 \uC77C\uC0C1\uC744 \uC313\uC544\uC694.\nintro: \uB290\uAE0B\uD558\uAC8C \uAC70\uB2D0\uACE0, \uC11C\uB85C\uC758 \uD558\uB8E8\uB97C \uB098\uB204\uC138\uC694.\npace: \uC774\uACF3\uC5D0\uC11C\uB294 \uB2F9\uC2E0\uC758 \uC18D\uB3C4\uB85C \uC9C0\uB0B4\uBA74 \uB3FC\uC694.\njump: \uB85C\uADF8\uC778\uC73C\uB85C \uC774\uB3D9\nsteps: \u25C7 \uB290\uAE0B\uD55C \uBC1C\uAC78\uC74C\ntogether: \u25CE \uD568\uAED8\uD558\uB294 \uC2DC\uAC04\ndaily: \u25CC \uB098\uB9CC\uC758 \uC77C\uC0C1\nwelcome: \uC5B4\uC11C \uC624\uC138\uC694.\nsubtitle: \uC624\uB298\uB3C4 \uB098\uB9CC\uC758 \uC18D\uB3C4\uB85C \uC2DC\uC791\uD574\uC694.\nusername: \uC544\uC774\uB514\npassword: \uBE44\uBC00\uBC88\uD638\nlogin: \uC811\uC18D\uD558\uAE30\nsignupHint: \uCC98\uC74C \uC624\uC168\uB098\uC694? \uC0C8 \uACC4\uC815\uC744 \uB9CC\uB4E4\uC5B4 \uC8FC\uC138\uC694.\nregister: \uC0C8 \uACC4\uC815 \uB9CC\uB4E4\uAE30\nbusy: \uCC98\uB9AC \uC911\uC774\uC5D0\uC694. \uC7A0\uC2DC\uB9CC \uAE30\uB2E4\uB824 \uC8FC\uC138\uC694.\nrules: \uAC00\uC785 \uC870\uAC74 \uD655\uC778\uD558\uAE30\nusernameRule: "\uAC00\uC785 \uC544\uC774\uB514: \uC601\uBB38 \uC18C\uBB38\uC790\xB7\uC22B\uC790\uB9CC \uD5C8\uC6A9\uD569\uB2C8\uB2E4."\npasswordRule: "\uBE44\uBC00\uBC88\uD638: \uACF5\uBC31 \uC5C6\uC774 ASCII \uBB38\uC790\uB9CC \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4(\uCD5C\uB300 128\uC790)."\n\ninputHint: \uC544\uC774\uB514\uC640 \uBE44\uBC00\uBC88\uD638\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694.\nsigningIn: \uC811\uC18D \uC911\u2026\nregistering: \uACC4\uC815 \uB9CC\uB4DC\uB294 \uC911\u2026\nregistered: \uAC00\uC785\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC811\uC18D\uD558\uAE30\uB97C \uB20C\uB7EC \uC8FC\uC138\uC694.\nshowPassword: \uBE44\uBC00\uBC88\uD638 \uD45C\uC2DC\nhidePassword: \uBE44\uBC00\uBC88\uD638 \uC228\uAE30\uAE30\n\nregisterSubtitle: \uC0AC\uC6A9\uD560 \uC544\uC774\uB514\uC640 \uBE44\uBC00\uBC88\uD638\uB97C \uC785\uB825\uD574 \uC8FC\uC138\uC694.\nbackToLogin: \uB85C\uADF8\uC778\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30\ninvalidUsername: \uC544\uC774\uB514\uB294 \uC601\uBB38 \uC18C\uBB38\uC790\uC640 \uC22B\uC790\uB9CC \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4(\uCD5C\uB300 40\uC790).\ninvalidPassword: \uBE44\uBC00\uBC88\uD638\uB294 \uACF5\uBC31 \uC5C6\uC774 ASCII \uBB38\uC790\uB9CC \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4(\uCD5C\uB300 128\uC790).\n', "./locales/ko/battle.yaml": `healthAlly: 'HP {hp} / {maxHp}'
healthFallen: \uC4F0\uB7EC\uC9D0
healthHidden: \uCCB4\uB825 \uBBF8\uD655\uC778 \xB7 \uBAAC\uC2A4\uD130\uD559 \uD544\uC694
healthLight: \uC190\uC0C1 \uC801\uC74C \xB7 \uBAAC\uC2A4\uD130\uD559 \xB7 2\uAD6C\uAC04 \uD310\uBCC4
healthHeavy: \uC190\uC0C1 \uD07C \xB7 \uBAAC\uC2A4\uD130\uD559 \xB7 2\uAD6C\uAC04 \uD310\uBCC4
selectedCharacter: \uC120\uD0DD\uD55C \uCE90\uB9AD\uD130
activeCharacter: \uD604\uC7AC \uD589\uB3D9 \uCE90\uB9AD\uD130
characterAp: \uCE90\uB9AD\uD130 AP
remainingAp: \uB0A8\uC740 AP
apUnknown: AP \uD655\uC778 \uBD88\uAC00
apValue: '\uB0A8\uC740 AP {value}'
apMaximum: '\uB0A8\uC740 AP {value} / {maximum}'
unitDetails: \uC120\uD0DD \uCE90\uB9AD\uD130 \uC124\uBA85
selectUnitHelp: \uCE90\uB9AD\uD130\uB97C \uC120\uD0DD\uD558\uBA74 \uC774\uACF3\uC5D0\uC11C \uC0C1\uD0DC\uB97C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.
ally: \uC544\uAD70
enemy: \uC801
incapacitated: \uC804\uD22C \uBD88\uB2A5
guarding: \uBC29\uC5B4 \uC911
noGuard: \uBC29\uC5B4 \uC5C6\uC74C
unitStats: '\uACF5\uACA9 {attack} \xB7 \uBC29\uC5B4 {defense} \xB7 \uC18D\uB3C4 {speed} \xB7 \uC774\uB3D9 {move} \xB7 \uC0AC\uAC70\uB9AC {range}'
move: "\uC774\uB3D9"
attack: "\uACF5\uACA9"
guard: "\uBC29\uC5B4"
endTurn: "\uD134 \uC885\uB8CC"
wait: "\uC2DC\uAC04 \uCD08\uACFC \uB300\uAE30"
surrenderVote: "\uB3C4\uC8FC \uB3D9\uC758"
cancel: "\uCDE8\uC18C"
confirm: "\uD655\uC815"
preparing: "\uC804\uD22C \uB9F5 \uC900\uBE44 \uC911"
preparingHelp: "\uB9F5\uACFC \uC804\uC6A9 \uCC44\uD305\uB8F8, \uCC38\uAC00\uC790 \uC900\uBE44\uAC00 \uC644\uB8CC\uB41C \uB4A4 \uCCAB \uD134\uC744 \uC2DC\uC791\uD569\uB2C8\uB2E4."
controls: "\uC804\uD22C \uCEE8\uD2B8\uB864 \uCE74\uB4DC"
myTurn: "\uB0B4 \uCC28\uB840"
waiting: "\uD589\uB3D9 \uB300\uAE30"
participant: "\uCC38\uAC00\uC790"
moveHint: "\uD30C\uB780 \uC774\uB3D9 \uCE78\uC744 \uC120\uD0DD\uD558\uBA74 \uD655\uC815 \uCC3D\uC774 \uC5F4\uB9BD\uB2C8\uB2E4."
attackHint: "\uB300\uC0C1\uC744 \uC120\uD0DD\uD55C \uB4A4 \uBAA9\uB85D\uC758 \uACF5\uACA9 \uBC84\uD2BC\uC744 \uB204\uB974\uC138\uC694."
endHint: "\uD134 \uC885\uB8CC\uB294 \uD655\uC815 \uCC3D\uC5D0\uC11C \uACB0\uC815\uD569\uB2C8\uB2E4."
actions: "\uC804\uD22C \uD589\uB3D9 \uC120\uD0DD"
noTarget: "\uD604\uC7AC \uC704\uCE58\uC5D0\uC11C \uACF5\uACA9 \uAC00\uB2A5\uD55C \uB300\uC0C1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."
confirmSurrender: "\uB3C4\uC8FC \uB3D9\uC758 \uD655\uC815"
surrender: "\uB3C4\uC8FC"
targetSelection: "\uACF5\uACA9 \uB300\uC0C1 \uC120\uD0DD"
clearSelection: "\uC120\uD0DD \uD574\uC81C"
noAttackTargets: "\uD604\uC7AC \uC704\uCE58\uC5D0\uC11C \uACF5\uACA9\uD560 \uC218 \uC788\uB294 \uB300\uC0C1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."
attackCandidates: "\uACF5\uACA9 \uAC00\uB2A5\uD55C \uBAB9 \uBAA9\uB85D"
selected: "\uC120\uD0DD\uB428"
help: "\uC804\uD22C \uB3C4\uC6C0\uB9D0 \uCE74\uB4DC"
movementLegend: "\uC774\uB3D9 \uBC94\uC704 \uBC94\uB840"
moveTiles: "\uD30C\uB780 \uCE78 \xB7 \uC774\uB3D9 \uAC00\uB2A5"
pathLine: "\uBC88\uD638\uC120 \xB7 \uC120\uD0DD \uACBD\uB85C"
arrivalLine: "\uC8FC\uD669 \uC548\uCABD\uC120 \xB7 \uB3C4\uCC29 \uD6C4 \uACF5\uACA9"
chooseTile: "\uBC1D\uC740 \uD30C\uB780 \uD14C\uB450\uB9AC \uC548\uC758 \uCE78\uC744 \uC120\uD0DD\uD558\uC138\uC694."
endAfterAction: "\uD589\uB3D9\uC744 \uC774\uBBF8 \uC0AC\uC6A9\uD588\uC2B5\uB2C8\uB2E4. \uCD94\uAC00 \uBC29\uC5B4 \uC5C6\uC774 \uD134\uC744 \uC885\uB8CC\uD569\uB2C8\uB2E4."
autoGuardHelp: "\uB0A8\uC740 \uC774\uB3D9\uC744 \uD3EC\uAE30\uD558\uACE0 \uC790\uB3D9 \uBC29\uC5B4\uD569\uB2C8\uB2E4. \uB2E4\uC74C \uC790\uAE30 \uD134\uAE4C\uC9C0 \uBC1B\uB294 \uAE30\uBCF8 \uACF5\uACA9 \uD53C\uD574\uAC00 \uC808\uBC18\uC73C\uB85C \uC904\uC5B4\uB4ED\uB2C8\uB2E4."
arrivalHeading: "\uB3C4\uCC29 \uD6C4 \uACF5\uACA9 \uC548\uB0B4"
moveEndsTurn: "\uD589\uB3D9\uC744 \uC774\uBBF8 \uC0AC\uC6A9\uD588\uC2B5\uB2C8\uB2E4. \uC774\uB3D9\uD558\uBA74 \uD134\uC774 \uC885\uB8CC\uB429\uB2C8\uB2E4."
noArrivalTargets: "\uB3C4\uCC29 \uD6C4 \uACF5\uACA9 \uAC00\uB2A5\uD55C \uC801\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."
moveOnly: "\uC774\uB3D9\uB9CC \uD655\uC815\uD569\uB2C8\uB2E4. \uACF5\uACA9\uC740 \uB3C4\uCC29 \uD6C4 \uB530\uB85C \uC120\uD0DD\uD558\uC138\uC694."
turnCharacters: "\uD134\xB7\uCE90\uB9AD\uD130"
turnOrder: "\uC774\uBC88 \uB77C\uC6B4\uB4DC \uD589\uB3D9 \uC21C\uC11C"
used: "\uC0AC\uC6A9\uD568"
once: "1\uD68C"
legacyActionHelp: "\uC774\uB3D9\uACFC \uD589\uB3D9\uC740 \uC21C\uC11C \uC790\uC720 \xB7 \uBAA8\uB450 \uC0AC\uC6A9\uD558\uBA74 \uC790\uB3D9 \uD134 \uC885\uB8CC"
terrainControls: "\uC9C0\uD615\xB7\uC870\uC791"
terrainHelp: "\uD0C0\uC77C\uC744 \uC120\uD0DD\uD574 \uC774\uB3D9\xB7\uACF5\uACA9 \uB300\uC0C1\uC744 \uC9C0\uC815\uD558\uC138\uC694. \uB4DC\uB798\uADF8\uB85C \uC2DC\uC810\uC744 \uC774\uB3D9\uD558\uACE0 \uD655\uB300\xB7\uCD95\uC18C \uBC0F \uD68C\uC804 \uBC84\uD2BC\uC73C\uB85C \uC9C0\uD615\uC744 \uD655\uC778\uD558\uC138\uC694."
units: "\uC804\uD22C \uC720\uB2DB"
emptyLog: "\uC544\uC9C1 \uC804\uD22C \uC561\uC158 \uAE30\uB85D\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."
endNoGuard: "\uCD94\uAC00 \uBC29\uC5B4 \uC5C6\uC774 \uD134\uC744 \uC885\uB8CC\uD569\uB2C8\uB2E4."
endWithGuard: "\uB0A8\uC740 \uC774\uB3D9\uC744 \uD3EC\uAE30\uD558\uACE0 \uBC29\uC5B4\uD558\uBA70 \uD134\uC744 \uC885\uB8CC\uD569\uB2C8\uB2E4."
seconds: "{seconds}\uCD08"
waitFor: "{name}\uC758 \uD589\uB3D9\uC744 \uAE30\uB2E4\uB9AC\uACE0 \uC788\uC2B5\uB2C8\uB2E4."
targetCount: "\uACF5\uACA9 \uB300\uC0C1 \xB7 {count}"
expectedDamage: "\uC608\uC0C1 \uD53C\uD574 {damage}"
moveRoute: "\uC774\uB3D9 {count}\uC140: {path}"
arrivalRange: "\uC8FC\uD669 \uC548\uCABD\uC120: \uB3C4\uCC29 \uD6C4 \uACF5\uACA9 \uBC94\uC704 \xB7 \uC0AC\uAC70\uB9AC {range}\uC140"
roundStatus: "\uB77C\uC6B4\uB4DC {round} \xB7 \uD604\uC7AC {name}"
actionUsage: "\uC774\uB3D9 {move} \xB7 \uD589\uB3D9 {action}"
portrait: "{name} \uBAA8\uC2B5"
healthLabel: "{name} \uCCB4\uB825"
unitCount: "\uCC38\uAC00 \uC720\uB2DB \xB7 {count}"
logCount: "\uC804\uD22C\uAE30\uB85D \uBCF4\uAE30 \xB7 {count}\uAC1C \uC561\uC158"
turnNumber: "\uD134 {turn}"
logMove: "\uC774\uB3D9 {path}"
autoGuard: "\uC790\uB3D9 \uBC29\uC5B4"
logDamage: " \u2192 {name} ({damage} \uD53C\uD574)"
confirmAction: "{action} \uD655\uC778"

apExhausted: AP\uB97C \uBAA8\uB450 \uC0AC\uC6A9\uD588\uC2B5\uB2C8\uB2E4. \uD134 \uC885\uB8CC\uB97C \uB20C\uB7EC \uB2E4\uC74C \uCC28\uB840\uB85C \uB118\uAE30\uC138\uC694.
reportTitle: "\uC804\uD22C \uB9AC\uD3EC\uD2B8"
resultWin: "\uC2B9\uB9AC"
resultLose: "\uD328\uBC30"
resultTimeout: "\uC2DC\uAC04 \uCD08\uACFC"
resultSurrender: "\uB3C4\uC8FC"
resultPreparationFailed: "\uC804\uD22C \uC900\uBE44 \uC2E4\uD328"
earnedCurrency: "\uD68D\uB4DD \uC7AC\uD654"
returnCountdown: "{seconds}\uCD08 \uD6C4 \uB9F5 \uBCF5\uADC0\uB97C \uC2DC\uC791\uD569\uB2C8\uB2E4."
acknowledge: \uD655\uC778
apRules: \uC774\uB3D9 1\uCE78\uB2F9 1 AP \xB7 \uC77C\uBC18 \uACF5\uACA9 3 AP \xB7 \uC790\uAE30 \uD134\uB9C8\uB2E4 \uCD5C\uB300 AP\uC758 50% \uBC18\uC62C\uB9BC \uD68C\uBCF5 \xB7 \uC794\uC5EC AP \uC774\uC6D4
apRecovery: '\uC790\uAE30 \uD134 \uC2DC\uC791 +{count} AP'
apPreview: '\uC18C\uBAA8 {cost} AP \xB7 \uC2E4\uD589 \uD6C4 {remaining} AP'

skills: "\uC2A4\uD0AC"
skillSelection: "\uC2A4\uD0AC \uC120\uD0DD"
noSlottedSkills: "\uCE90\uB9AD\uD130 \uC124\uC815\uC5D0\uC11C \uC804\uD22C \uC2A4\uD0AC\uC744 \uC9C0\uC815\uD558\uC138\uC694."
skillPreviewOnly: "\uC2E4\uD589 \uAC00\uB2A5\uD55C \uC561\uC158\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uD574\uAE08 \uB808\uBCA8\xB7\uC804\uD22C \uC2AC\uB86F\xB7\uC7A5\uBE44 \uC870\uAC74\uC744 \uD655\uC778\uD558\uC138\uC694."

idleTurnNotice: "5\uCD08 \uB3D9\uC548 \uC785\uB825\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uD589\uB3D9\uC744 \uB9C8\uCCE4\uB2E4\uBA74 \uD134 \uC885\uB8CC\uB97C \uB20C\uB7EC \uC8FC\uC138\uC694."

noLoot: "\uD68D\uB4DD\uD55C \uC804\uB9AC\uD488\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."

basicAttackSkillHelp: "\uC2E0\uCCB4\uD65C\uB3D9\uC5D0 \uD3EC\uD568\uB41C \uC77C\uBC18 \uACF5\uACA9\uC785\uB2C8\uB2E4. \uB300\uC0C1\uC744 \uC120\uD0DD\uD558\uACE0 \uD655\uC778\uD558\uBA74 \uC2E4\uD589\uD569\uB2C8\uB2E4."
selectSkillHelp: "\uC2A4\uD0AC\uC744 \uC120\uD0DD\uD574 \uC124\uBA85\uACFC \uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uD589\uB3D9\uC744 \uD655\uC778\uD558\uC138\uC694."
terrainApPreview: "\uAE30\uBCF8 {base} AP \xB7 \uC608\uC0C1 {expected} AP \xB7 \uCD5C\uB300 {max} AP. \uC9C0\uD615 \uCD94\uAC00 \uC18C\uBAA8\uB85C AP\uAC00 0 \uC774\uD558\uAC00 \uB418\uBA74 \uB3C4\uCC29 \uC804\uC5D0 \uBA48\uCD9C \uC218 \uC788\uC2B5\uB2C8\uB2E4."
terrainMovementStopped: "AP \uBD80\uC871\uC73C\uB85C \uACBD\uB85C \uC911\uB2E8"

surrenderConfirmation: "\uB3C4\uC8FC\uC5D0 \uB3D9\uC758\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C? \uB3C4\uC8FC\uD558\uBA74 \uC774\uBC88 \uC804\uD22C\uC5D0\uC11C \uD68D\uB4DD\uD55C \uC804\uB9AC\uD488\uC744 \uAC1C\uB2F9 50% \uD655\uB960\uB85C \uBD84\uC2E4\uD569\uB2C8\uB2E4."

moveSummary: "\uC774\uB3D9 {count}\uCE78 \xB7 \uC804\uCCB4 \uACBD\uB85C\uB294 \uB9F5\uACFC \uD655\uC778\uCC3D\uC5D0\uC11C \uD655\uC778\uD558\uC138\uC694."
attackHelpDetail: "\uB9F5\uC774\uB098 \uBAA9\uB85D\uC5D0\uC11C \uB300\uC0C1\uC744 \uC120\uD0DD\uD55C \uB4A4 \uC120\uD0DD \uD574\uC81C \uC606 \uACF5\uACA9 \uBC84\uD2BC\uC73C\uB85C \uD655\uC778\uCC3D\uC744 \uC5EC\uC138\uC694. \uD655\uC815 \uC804 \uC608\uC0C1 \uD53C\uD574\uB97C \uD655\uC778\uD560 \uC218 \uC788\uC73C\uBA70, \uC801 \uCCB4\uB825 \uC815\uBCF4\uB294 \uBAAC\uC2A4\uD130\uD559 \uC218\uC900\uC5D0 \uB530\uB77C \uD45C\uC2DC\uB429\uB2C8\uB2E4."

plainEndTurn: "\uADF8\uB0E5 \uC885\uB8CC \xB7 AP 0"
guardEndTurn: "\uBC29\uC5B4 \uD6C4 \uC885\uB8CC \xB7 AP 1"
turnEndChoice: "\uBC29\uC5B4 \uD6C4 \uC885\uB8CC\uB294 AP 1\uC744 \uC18C\uBAA8\uD569\uB2C8\uB2E4. \uADF8\uB0E5 \uC885\uB8CC\uD558\uBA74 AP \uC18C\uBAA8 \uC5C6\uC774 \uBC29\uC5B4\uD558\uC9C0 \uC54A\uACE0 \uD134\uC744 \uB118\uAE41\uB2C8\uB2E4."
guardEndUnavailable: "\uBC29\uC5B4 \uD6C4 \uC885\uB8CC\uC5D0\uB294 AP 1\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uC9C0\uAE08\uC740 AP \uC18C\uBAA8 \uC5C6\uC774 \uADF8\uB0E5 \uC885\uB8CC\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."

lostLoot: "\uB3C4\uC8FC \uC911 \uBD84\uC2E4"
turnEndPrompt: "\uD134\uC744 \uB9C8\uCE60 \uBC29\uBC95\uC744 \uC120\uD0DD\uD558\uC138\uC694."
plainEndDetail: "\uBC29\uC5B4 \uC5C6\uC774 \uD134\uC744 \uB118\uAE41\uB2C8\uB2E4."
guardEndDetail: "\uBC29\uC5B4 \uC0C1\uD0DC\uB85C \uC804\uD658\uD55C \uB4A4 \uD134\uC744 \uB118\uAE41\uB2C8\uB2E4."
guardEndDisabledDetail: "AP \uBD80\uC871 \xB7 \uBC29\uC5B4\uD558\uB824\uBA74 AP 1\uC774 \uD544\uC694\uD569\uB2C8\uB2E4."
distributionTitle: "\uD68D\uB4DD \uBC0F \uBD84\uBC30"
distributionQuantities: "\uCD1D \uD68D\uB4DD {total} / \uB0B4 \uC9C0\uAE09 {mine}"
distributionInitiator: "\uC9C4\uD589\uC790"
distributionSupporter: "\uC9C0\uC6D0\uC790"
distributionDetails: "\uAC1C\uBCC4 \uCD94\uCCA8 \uB0B4\uC5ED"
distributionRoll: "{sequence}\uBC88 \xB7 \uB208\uAE08 {face} \u2192 {name}"
distributionMailbox: "\uC9C0\uC6D0\uC790 \uBAAB\uC740 \uD574\uB2F9 \uCE90\uB9AD\uD130 \uC18C\uC720 \uACC4\uC815\uC758 \uBCF4\uAD00\uD568\uC5D0 \uBCF4\uAD00\uB429\uB2C8\uB2E4."

recoveryPending: \uC804\uD22C\uBD88\uB2A5 \uD68C\uBCF5 \uB300\uAE30 \uC911\uC5D0\uB294 \uC774\uB3D9\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uC81C\uC790\uB9AC\uC5D0\uC11C \uAC00\uB2A5\uD55C \uD589\uB3D9\uC774\uB098 \uD134 \uC885\uB8CC\uB97C \uC120\uD0DD\uD558\uC138\uC694.

finishingStrike: \uC77C\uACA9\uD544\uC0B4
skillUnavailable: AP\uAC00 \uBD80\uC871\uD558\uAC70\uB098 \uC0AC\uAC70\uB9AC \uC548\uC5D0 \uACF5\uACA9 \uAC00\uB2A5\uD55C \uB300\uC0C1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.
useSkillAction: \uC2A4\uD0AC \uC0AC\uC6A9

supportExcluded: \uC774\uBC88 \uC804\uD22C\uC5D0\uC11C \uC81C\uC678\uB41C \uD30C\uD2F0\uC6D0
supportExpired: \uB300\uC5EC \uAE30\uAC04 \uB9CC\uB8CC
supportCpMismatch: CP \uD3B8\uC131 \uC870\uAC74 \uBD88\uCDA9\uC871
supportMigration: \uB300\uC5EC \uC131\uC7A5 \uAE30\uB85D \uD655\uC778 \uD544\uC694
supportRecovering: \uC804\uD22C\uBD88\uB2A5 \uD68C\uBCF5 \uB300\uAE30
supportBusy: \uB2E4\uB978 \uC804\uD22C \uCC38\uC5EC \uC911
supportPreview: \uC608\uC0C1 \uC804\uD22C \uCC38\uAC00\uC790
supportRecheck: \uC870\uC6B0 \uC2DC \uCD5C\uC2E0 \uC790\uACA9\uC73C\uB85C \uB2E4\uC2DC \uD310\uC815\uD569\uB2C8\uB2E4. \uC81C\uC678\uB418\uC5B4\uB3C4 \uD3B8\uC131\uC740 \uC720\uC9C0\uB429\uB2C8\uB2E4.
supportPreviewFailed: \uCC38\uAC00 \uBA85\uB2E8\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694.
supportRefresh: \uBA85\uB2E8 \uC0C8\uB85C\uACE0\uCE68

distributionGuild: "\uAE38\uB4DC \uADC0\uC18D"
distributionGuildStorage: "\uAE38\uB4DC \uAE30\uBCF8 \uD30C\uD2F0\uC6D0\uC758 \uB2F9\uCCA8 \uC7AC\uB8CC\uB294 \uAE38\uB4DC \uC6D0\uC7A5\uC5D0 \uBCF4\uAD00\uB429\uB2C8\uB2E4. \uAC1C\uC778 \uBCF4\uAD00\uD568\uC5D0\uC11C\uB294 \uC218\uB839\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4."
dissectionApplied: "\uD574\uBD80 \uBCF4\uC815 \uC801\uC6A9 \xB7 \uB2F4\uB2F9 \uC219\uB828 \uB808\uBCA8 {level}"
dissectionRecoveryHint: "\uBAAC\uC2A4\uD130\uBCC4 \uB09C\uC774\uB3C4\uAC00 \uBC18\uC601\uB429\uB2C8\uB2E4. \uD574\uBD80\uAC00 \uBBF8\uC219\uD558\uBA74 \uC628\uC804\uD55C \uC7AC\uB8CC \uD68C\uC218\uC5D0 \uC2E4\uD328\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."

expectedHealing: "\uC608\uC0C1 HP \uD68C\uBCF5 {healing}"
expectedDrain: "\uC790\uC2E0 HP \uD68C\uBCF5 {healing}"

apRulesFloor: "\uC774\uB3D9 1\uCE78\uB2F9 1 AP \xB7 \uC77C\uBC18 \uACF5\uACA9 3 AP \xB7 \uC790\uAE30 \uD134\uB9C8\uB2E4 \uCD5C\uB300 AP\uC758 50% \uB0B4\uB9BC \uD68C\uBCF5 \xB7 \uC794\uC5EC AP \uC774\uC6D4"

automaticEnable: \uC790\uB3D9\uC804\uD22C \uCF1C\uAE30

automaticDisable: \uC790\uB3D9\uC804\uD22C \uB044\uAE30

automaticActiveHelp: \uC790\uB3D9\uC804\uD22C \uC911\uC785\uB2C8\uB2E4. \uC218\uB3D9 \uD589\uB3D9\uC740 \uC790\uB3D9\uC804\uD22C\uB97C \uB048 \uB4A4 \uC120\uD0DD\uD558\uC138\uC694.

automaticManualHelp: \uC774\uBC88 \uC804\uD22C\uC5D0\uC11C\uB9CC \uC801\uC6A9\uB429\uB2C8\uB2E4. \uC811\uC18D \uC885\uB8CC \uD6C4\uC5D0\uB294 \uC218\uB3D9\uC73C\uB85C \uB3CC\uC544\uC635\uB2C8\uB2E4.

automaticEnabledLog: \uC790\uB3D9\uC804\uD22C \uCF2C

automaticDisabledLog: \uC790\uB3D9\uC804\uD22C \uB054
patternTitle: "\uC790\uB3D9\uC804\uD22C \uD328\uD134"
patternHelp: "\uC704\uC5D0\uC11C\uBD80\uD130 \uC2E4\uD589 \uAC00\uB2A5\uD55C \uCCAB \uADDC\uCE59\uC744 \uC0AC\uC6A9\uD569\uB2C8\uB2E4. \uC800\uC7A5\uD55C \uD328\uD134\uC740 \uC0C8 \uC804\uD22C\xB7\uC0C8 \uB300\uC5EC\uC5D0 \uC801\uC6A9\uB429\uB2C8\uB2E4. \uC804\uD22C \uC911 \uC790\uB3D9\uC804\uD22C\uB97C \uCF1C\uC57C \uC2E4\uD589\uB429\uB2C8\uB2E4."
patternRuleNumber: "\uADDC\uCE59 {number}"
patternEndRule: "\uD56D\uC0C1 \u2192 \uD134 \uC885\uB8CC (\uB9C8\uC9C0\uB9C9 \uACE0\uC815 \uADDC\uCE59)"
patternCondition: "\uC870\uAC74"
patternConditionAlways: "\uD56D\uC0C1"
patternConditionSelfHp: "\uBCF8\uC778 HP \uC774\uD558"
patternConditionAllyHp: "\uC544\uAD70 HP \uC774\uD558"
patternHpPercent: "HP \uBE44\uC728 (%)"
patternAction: "\uD589\uB3D9"
patternActionAttack: "\uC77C\uBC18 \uACF5\uACA9"
patternActionSkill: "\uC2A4\uD0AC \uC561\uC158"
patternActionApproach: "\uCD5C\uADFC\uC811 \uC801\uC5D0\uAC8C \uD55C \uCE78 \uC811\uADFC"
patternActionEndTurn: "\uD134 \uC885\uB8CC"
patternSkillAction: "\uC0AC\uC6A9\uD560 \uC2A4\uD0AC \uC561\uC158"
patternMissingSkill: "\uC0AC\uC6A9\uD560 \uC218 \uC5C6\uB294 \uC2A4\uD0AC \xB7 \uC2AC\uB86F\uACFC \uB808\uBCA8 \uD655\uC778"
patternMoveUp: "\uC704\uB85C"
patternMoveDown: "\uC544\uB798\uB85C"
patternRemoveRule: "\uADDC\uCE59 \uC0AD\uC81C"
patternAddRule: "\uADDC\uCE59 \uCD94\uAC00"
patternRuleLimit: "\uADDC\uCE59\uC740 \uB9C8\uC9C0\uB9C9 \uD134 \uC885\uB8CC\uB97C \uD3EC\uD568\uD574 \uCD5C\uB300 10\uAC1C\uC785\uB2C8\uB2E4. \uAE30\uC874 \uADDC\uCE59\uC744 \uC0AD\uC81C\uD558\uBA74 \uCD94\uAC00\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."
patternInvalidRules: "HP \uBE44\uC728\uC740 1~100\uC758 \uC815\uC218\uB85C \uC785\uB825\uD558\uACE0 \uC0AC\uC6A9\uD560 \uC218 \uC788\uB294 \uC2A4\uD0AC \uC561\uC158\uC744 \uC120\uD0DD\uD558\uC138\uC694."
patternSave: "\uD328\uD134 \uC800\uC7A5"
patternReload: "\uC800\uC7A5\uB41C \uADDC\uCE59 \uB2E4\uC2DC \uC77D\uAE30"
patternDelete: "\uB4F1\uB85D \uD328\uD134 \uC0AD\uC81C"
patternSaved: "\uBCC0\uACBD\uC774 \uC800\uC7A5\uB418\uC5C8\uC2B5\uB2C8\uB2E4."
`, "./locales/ko/cards.yaml": "shop: \uC11C\uC810 \uC2A4\uD0AC\uCE74\uB4DC\nstorage: \uBCF4\uAD00 \uC911\uC778 \uC2A4\uD0AC\uCE74\uB4DC\npolicy: \uAD6C\uB9E4\uD55C \uCE74\uB4DC\uB294 \uACC4\uC815 \uBCF4\uAD00\uD568\uC5D0 \uC9C0\uAE09\uB429\uB2C8\uB2E4. \uC0AC\uC6A9\uD558\uBA74 \uC18C\uBAA8\uB418\uBA70 \uC2A4\uD0AC\uC744 \uC2B5\uB4DD\uD569\uB2C8\uB2E4.\nrefresh: \uCE74\uB4DC \uBAA9\uB85D \uC0C8\uB85C\uACE0\uCE68\npending: \uC2A4\uD0AC\uCE74\uB4DC\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.\nliteracy: '\uC0AC\uC6A9 \uC694\uAD6C \uBB38\uD574: {level}'\nrequirement: '\uBB38\uD574 \uC694\uAD6C {required} \xB7 \uD604\uC7AC {current}'\nbuy: '{price} P\uC5D0 \uAD6C\uB9E4'\nowned: \uACC4\uC815 \uBCF4\uAD00\uD568\uC5D0 \uBCF4\uAD00 \uC911\nlearned: \uC774\uBBF8 \uC2B5\uB4DD\uD55C \uC2A4\uD0AC\nindefinite: \uBB34\uAE30\uD55C \uBCF4\uAD00\nuse: \uCE74\uB4DC \uC0AC\uC6A9\nconfirmTitle: \uC2A4\uD0AC\uCE74\uB4DC \uC0AC\uC6A9 \uD655\uC778\nconfirm: '{name} 1\uAC1C\uB97C \uC18C\uBAA8\uD558\uACE0 \uD574\uB2F9 \uC2A4\uD0AC\uC744 \uB808\uBCA8 0\uC73C\uB85C \uC2B5\uB4DD\uD569\uB2C8\uB2E4.'\nconfirmUse: \uC18C\uBAA8\uD558\uACE0 \uC2B5\uB4DD\ncancel: \uCDE8\uC18C\nempty: \uBCF4\uAD00 \uC911\uC778 \uC2A4\uD0AC\uCE74\uB4DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\npurchased: \uACC4\uC815 \uBCF4\uAD00\uD568\uC5D0 \uC2A4\uD0AC\uCE74\uB4DC\uB97C \uC9C0\uAE09\uD588\uC2B5\uB2C8\uB2E4.\nused: \uCE74\uB4DC\uB97C \uC18C\uBAA8\uD558\uACE0 \uC2A4\uD0AC\uC744 \uC2B5\uB4DD\uD588\uC2B5\uB2C8\uB2E4.\nuncertain: \uCC98\uB9AC \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC73C\uB85C \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\nretry: \uAC19\uC740 \uC694\uCCAD \uB2E4\uC2DC \uD655\uC778\n\nfieldRequired: \uAC8C\uC784\uC5D0 \uC785\uC7A5\uD55C \uB4A4 \uC804\uD22C\xB7\uC870\uC6B0\uAC00 \uC5C6\uB294 \uC0C1\uD0DC\uC5D0\uC11C \uC2A4\uD0AC\uCE74\uB4DC\uB97C \uAD6C\uB9E4\uD558\uAC70\uB098 \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\nwaitForConnection: \uC5F0\uACB0\uC774 \uBCF5\uAD6C\uB418\uACE0 \uC9C4\uD589 \uC911\uC778 \uC694\uCCAD\uC774 \uB05D\uB098\uBA74 \uB2E4\uC2DC \uC2DC\uB3C4\uD558\uC138\uC694.\ninsufficientFunds: \uAD6C\uB9E4\uC5D0 \uD544\uC694\uD55C P\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4.\n", "./locales/ko/channels.yaml": "open: \uCC44\uB110 \uC774\uB3D9\ntitle: \uCC44\uB110 \uBAA9\uB85D\xB7\uC774\uB3D9\ncurrent: '\uD604\uC7AC \uCC44\uB110: {address}'\nhelp: \uAC19\uC740 \uB9F5\uC758 \uB2E4\uB978 \uCC44\uB110\uB85C \uC774\uB3D9\uD569\uB2C8\uB2E4. \uC704\uCE58\uB294 \uC720\uC9C0\uB418\uBA70 \uC0C8 \uCC44\uB110\uC758 \uCC44\uD305\uC5D0 \uB2E4\uC2DC \uC811\uC18D\uD569\uB2C8\uB2E4.\nrefresh: \uBAA9\uB85D \uC0C8\uB85C\uACE0\uCE68\ncheckState: \uD604\uC7AC \uC0C1\uD0DC \uB2E4\uC2DC \uD655\uC778\naddress: \uC774\uB3D9\uD560 \uCC44\uB110 \uC8FC\uC18C\naddressHelp: a1, aa22, ba234 \uD615\uC2DD\uC785\uB2C8\uB2E4. \uB300\uC18C\uBB38\uC790\uB294 \uAD6C\uBD84\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\njoinAddress: \uC8FC\uC18C\uB85C \uC774\uB3D9\njoin: \uC774\uB3D9\nsameMap: \uAC19\uC740 \uB9F5\uC758 \uCC44\uB110\npopulation: '\uC0AC\uC6A9 \uC88C\uC11D {used}/{capacity} \xB7 \uC811\uC18D {online}\uBA85'\npopulationHelp: \uC0AC\uC6A9 \uC88C\uC11D\uC5D0\uB294 \uC804\uD22C \uBCF5\uADC0 \uC608\uC57D\uC774 \uD3EC\uD568\uB429\uB2C8\uB2E4. \uC870\uD68C \uD6C4 \uC778\uC6D0\uC774 \uBC14\uB00C\uBA74 \uC774\uB3D9\uC774 \uC2E4\uD328\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\npopulationUnavailable: \uC774 \uC11C\uBC84\uB294 \uCC44\uB110 \uC778\uC6D0\uC744 \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uC774\uB3D9\uD560 \uB54C \uC815\uC6D0\uC744 \uD655\uC778\uD569\uB2C8\uB2E4.\nidentifier: 'ID: {id}'\npending: \uCC44\uB110 \uC815\uBCF4\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4\u2026\nuncertain: \uC774\uB3D9 \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uD604\uC7AC \uC0C1\uD0DC\uB97C \uB2E4\uC2DC \uD655\uC778\uD55C \uB4A4 \uC774\uB3D9\uD558\uC138\uC694.\ninvalidAddress: \uC54C\uD30C\uBCB3 \uB4A4\uC5D0 1 \uC774\uC0C1\uC758 \uC22B\uC790\uB97C \uC785\uB825\uD558\uC138\uC694. \uACF5\uBC31\uACFC \uAE30\uD638\uB294 \uC0AC\uC6A9\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.\ninvalidList: \uCC44\uB110 \uBAA9\uB85D\uC758 \uD615\uC2DD\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC870\uD68C\uD574 \uC8FC\uC138\uC694.\nstateRequired: \uD604\uC7AC \uCC44\uB110 \uC815\uBCF4\uB97C \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694.\nfieldRequired: \uC804\uD22C\xB7\uC870\uC6B0 \uC900\uBE44\uB97C \uB9C8\uCE58\uACE0 \uD544\uB4DC\uC5D0\uC11C \uC774\uB3D9\uD558\uC138\uC694.\nleaveParty: \uD30C\uD2F0\uC5D0\uC11C \uD0C8\uD1F4\uD55C \uB4A4 \uCC44\uB110\uC744 \uC774\uB3D9\uD558\uC138\uC694.\nrecoveryRequired: \uC804\uD22C\uBD88\uB2A5 \uD6C4 \uCD5C\uB300 HP\uC758 50% \uC774\uC0C1\uC744 \uD68C\uBCF5\uD574\uC57C \uC774\uB3D9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\nfpRequired: FP\uAC00 \uC74C\uC218\uC785\uB2C8\uB2E4. \uCDA9\uC804\uC744 \uAE30\uB2E4\uB9B0 \uB4A4 \uC774\uB3D9\uD558\uC138\uC694.\ndifferentMap: \uB2E4\uB978 \uB9F5\uC758 \uCC44\uB110\uC785\uB2C8\uB2E4. \uC6E8\uC774\uD3EC\uC778\uD2B8\uB85C \uD574\uB2F9 \uB9F5\uC5D0 \uBA3C\uC800 \uC774\uB3D9\uD558\uC138\uC694.\nalreadyHere: \uD604\uC7AC \uCC44\uB110\uC785\uB2C8\uB2E4.\nclosed: \uC785\uC7A5\uC774 \uC911\uC9C0\uB41C \uCC44\uB110\uC785\uB2C8\uB2E4.\nfull: \uB9CC\uC11D\uC785\uB2C8\uB2E4. \uB2E4\uB978 \uCC44\uB110\uC744 \uC120\uD0DD\uD558\uAC70\uB098 \uBAA9\uB85D\uC744 \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\nwaitAction: \uC9C4\uD589 \uC911\uC778 \uC774\uB3D9\xB7\uB85C\uB529\uC744 \uB9C8\uCE5C \uB4A4 \uCC44\uB110\uC744 \uC774\uB3D9\uD558\uC138\uC694.\npagination: \uCC44\uB110 \uBAA9\uB85D \uD398\uC774\uC9C0\npreviousPage: \uC774\uC804\nnextPage: \uB2E4\uC74C\npageNumber: '{page} / {total} \uD398\uC774\uC9C0'\nempty: \uD45C\uC2DC\uD560 \uAC19\uC740 \uB9F5\uC758 \uCC44\uB110\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uBAA9\uB85D\uC744 \uC0C8\uB85C\uACE0\uCE68\uD574 \uC8FC\uC138\uC694.\n", "./locales/ko/character.yaml": 'ready: \uBAA8\uD5D8\uC744 \uC2DC\uC791\uD560 \uC900\uBE44\uAC00 \uB418\uC5C8\uB098\uC694?\nremaining: \uBBF8\uBC30\uBD84 {points}\nlocation: \uB9C8\uC9C0\uB9C9 \uB9F5\uC758 \uC2DC\uC791\uC810\uC73C\uB85C \uC774\uB3D9\uD569\uB2C8\uB2E4.\npending: \uC9C4\uD589 \uC911 \uC804\uD22C \uC815\uC0B0 \uB300\uAE30\nenter: \uAC8C\uC784\uC73C\uB85C \uAC00\uAE30 \u2192\ntitle: \uC544\uC9C1 \uBC30\uBD84\uD558\uC9C0 \uC54A\uC740 \uD3EC\uC778\uD2B8\uAC00 \uC788\uC5B4\uC694\nconfirm: "{points}\uAC00 \uB0A8\uC544 \uC788\uC2B5\uB2C8\uB2E4. \uAC8C\uC784\uC73C\uB85C \uC774\uB3D9\uD560\uAE4C\uC694?"\nallocated: \uD3EC\uC778\uD2B8 \uBC30\uBD84\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uAC8C\uC784\uC73C\uB85C \uC774\uB3D9\uD560\uAE4C\uC694?\nback: \uC124\uC815\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30\nproceed: \uAC8C\uC784\uC73C\uB85C \uC774\uB3D9\nidentity: "\uB0B4 \uCE90\uB9AD\uD130"\nadventurer: "\uB098\uC758 \uBAA8\uD5D8\uAC00"\ncostume: "\uAE30\uBCF8 \uBAA8\uD5D8\uAC00 \uC758\uC0C1"\ncoins: "\uBCF4\uC720 \uD3F0(PON)"\ngrowth: "\uCE90\uB9AD\uD130 \uC131\uC7A5"\ndirection: "\uC131\uC7A5\uC758 \uBC29\uD5A5"\navailable: "\uC0AC\uC6A9 \uAC00\uB2A5\uD55C {currency}"\nconnectionRequired: "\uC5F0\uACB0 \uD655\uC778 \uD544\uC694"\nbreakdown: "\uCE90\uB9AD\uD130 \uD3EC\uC778\uD2B8 \uAD6C\uBD84"\ngeneralPoints: "\uC77C\uBC18\uD3EC\uC778\uD2B8"\nseasonPoints: "\uC2DC\uC98C\uD3EC\uC778\uD2B8"\nintro: "\uC5B4\uB5A4 \uBAA8\uD5D8\uAC00\uB85C \uC131\uC7A5\uD560\uAE4C\uC694?"\ncurrencies: "\uB2A5\uB825\uCE58\uB294 CP, \uC2A4\uD0AC\uC740 SP\uB85C \uC131\uC7A5\uD569\uB2C8\uB2E4. \uB2A5\uB825\uCE58 \uC131\uC7A5\uC5D0\uB294 \uC2DC\uC98C CP\uB97C \uBA3C\uC800 \uC0AC\uC6A9\uD569\uB2C8\uB2E4."\ncategory: "\uC131\uC7A5 \uD56D\uBAA9 \uC120\uD0DD"\nattributes: "\uB2A5\uB825\uCE58"\nskills: "\uC2A4\uD0AC"\nskillList: "\uC2E0\uCCB4\uD65C\uB3D9\xB7\uBB38\uD574\xB7\uB9D0\uD558\uAE30\uB294 \uCE90\uB9AD\uD130 \uC0DD\uC131 \uC2DC \uC81C\uACF5\uB429\uB2C8\uB2E4. \uC774\uD6C4 \uC2B5\uB4DD\uD55C \uC2A4\uD0AC\uB3C4 \uC774 \uBAA9\uB85D\uC5D0\uC11C \uAD00\uB9AC\uD569\uB2C8\uB2E4."\nnextCost: "{category} \uC131\uC7A5 {count}\uD68C \xB7 \uB2E4\uC74C \uC131\uC7A5 \uBE44\uC6A9 {cost} {currency}"\nnoEffect: " \xB7 \uD6A8\uACFC \uC5C6\uC74C"\nraiseLabel: "{name} \uB808\uBCA8 {level}\uC5D0\uC11C {next}\uB85C \uC0C1\uC2B9, {cost} {currency} \uC0AC\uC6A9"\nraise: "+1 \uB808\uBCA8"\ninsufficient: "{currency} \uBD80\uC871 \xB7 {cost} \uD544\uC694"\nspend: "{cost} {currency} \uC0AC\uC6A9"\nlocked: "\uC804\uD22C\xB7\uC870\uC6B0\uAC00 \uB05D\uB098\uBA74 \uC131\uC7A5 \uD3EC\uC778\uD2B8\uB97C \uBD84\uBC30\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nsaved: "\uC131\uC7A5\uC740 \uC989\uC2DC \uC800\uC7A5\uB429\uB2C8\uB2E4. \uB2A5\uB825\uCE58 \uC131\uC7A5\uC740 \uB2E4\uC74C CP \uBE44\uC6A9\uC744, \uC2A4\uD0AC \uC131\uC7A5\uC740 \uD574\uB2F9 \uC2A4\uD0AC\uC758 \uB2E4\uC74C SP \uBE44\uC6A9\uB9CC \uC62C\uB9BD\uB2C8\uB2E4."\nrulesTitle: "\uC131\uC7A5 \uADDC\uCE59 \uC548\uB0B4"\nrules: "\uC2DC\uC791 \uC2DC 10 CP\uC640 0 SP\uB97C \uBC1B\uC73C\uBA70 \uBB38\uD574\xB7\uB9D0\uD558\uAE30\xB7\uC2E0\uCCB4\uD65C\uB3D9\uC740 \uAC01\uAC01 \uB808\uBCA8 1\uB85C \uC81C\uACF5\uB429\uB2C8\uB2E4. CP\uB294 \uB2A5\uB825\uCE58 \uC0C1\uC2B9 \uD69F\uC218, SP\uB294 \uC62C\uB9AC\uB824\uB294 \uAC1C\uBCC4 \uC2A4\uD0AC\uC758 \uC0C1\uC2B9 \uD69F\uC218\uB85C \uBE44\uC6A9\uC774 \uCCAB 20\uB2E8\uACC4\uC5D0\uC11C 1 \u2192 2 \u2192 3 \u2192 4 \u2192 \u2026 \u2192 100\uC73C\uB85C \uC99D\uAC00\uD558\uBA70, \uC774\uD6C4\uC5D0\uB3C4 110 \u2192 121 \u2192 132\uCC98\uB7FC \uACC4\uC18D \uC99D\uAC00\uD569\uB2C8\uB2E4. \uC0DD\uC131 \uC2DC \uC9C0\uAE09\uB41C \uB808\uBCA8 1\uC740 \uBE44\uC6A9 \uB204\uC801\uC5D0\uC11C \uC81C\uC678\uD558\uBA70 \uCCAB 1 \u2192 2 \uC131\uC7A5 \uBE44\uC6A9\uC740 1 SP\uC785\uB2C8\uB2E4. \uC774\uD6C4 \uC5C5\uC801\uC73C\uB85C \uD68D\uB4DD\uD558\uB294 \uC2A4\uD0AC\uC740 \uB808\uBCA8 0\uBD80\uD130 \uC2DC\uC791\uD569\uB2C8\uB2E4. \uAE30\uC874 \uC9C0\uAE09 \uB808\uBCA8\uC740 \uBCF4\uC874\uB429\uB2C8\uB2E4. \uBD84\uBC30 \uD6C4 \uB418\uB3CC\uB9AC\uAE30\uB294 \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\nsummary: "\uCE90\uB9AD\uD130 \uC124\uC815 \xB7 CP {cp} \xB7 SP {sp}"\nportrait: "\uCCAD\uB85D\uC0C9 \uCC9C \uC758\uC0C1\uACFC \uAC00\uC8FD \uC7A5\uD654\uB97C \uCC29\uC6A9\uD55C \uAE30\uBCF8 \uBAA8\uD5D8\uAC00"\nbodyName: "\uC2E0\uCCB4"\nbodyDescription: "\uBAB8\uC744 \uC6C0\uC9C1\uC774\uB294 \uAE30\uBC18 \uC5ED\uB7C9"\nintellectName: "\uC9C0\uC131"\nintellectDescription: "\uC774\uD574\uD558\uACE0 \uD310\uB2E8\uD558\uB294 \uAE30\uBC18 \uC5ED\uB7C9"\nspiritName: "\uC601\uC131"\nspiritDescription: "\uC601\uC801 \uD65C\uB3D9\uC758 \uAE30\uBC18 \uC5ED\uB7C9"\n\nbattleSlots: "\uC804\uD22C \uC2A4\uD0AC \uC2AC\uB86F"\nbattleSlotsHelp: "\uC804\uD22C \uBAA9\uB85D\uC5D0 \uD45C\uC2DC\uD560 \uC2A4\uD0AC\uC744 \uC9C0\uC815\uD558\uC138\uC694. \uC120\uD0DD\uD55C \uC21C\uC11C\uB300\uB85C \uC800\uC7A5\uB429\uB2C8\uB2E4. 0\uB808\uBCA8\uC740 \uD6A8\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."\n\nskillUseLocked: "\uC0AC\uC6A9 \uC7A0\uAE40"\nskillBookSold: "\uC2A4\uD0AC\uBD81 \uD310\uB9E4\uB85C \uC0AC\uC6A9\uC774 \uC7A0\uACBC\uC2B5\uB2C8\uB2E4. \uD68D\uB4DD \uAE30\uB85D\uACFC \uB808\uBCA8\uC740 \uC720\uC9C0\uB429\uB2C8\uB2E4."\n\nactionUnlockLevel: "\uB808\uBCA8 {level}\uC5D0\uC11C \uD574\uAE08"\nactionUnlocked: "\uD574\uAE08\uB428 \xB7 \uC694\uAD6C \uB808\uBCA8 {level}"\nactionCostPower: "{ap} AP \xB7 \uACF5\uACA9\uB825 {power}\uBC30"\nactionSwordRequirement: "\uC804\uD22C \uC2AC\uB86F \uB4F1\uB85D\uACFC \uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uD55C\uC190\uAC80\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uBCF8\uC778 \uD134\xB7\uC0AC\uAC70\uB9AC\xB7\uB0A8\uC740 AP\uC5D0 \uB530\uB77C \uC2E4\uD589\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\ncostumeDetails: "\uC758\uC0C1 \uC124\uBA85"\ncostumeDescription: "\uD770\uC0C9 \uBC18\uD314 \uD2F0\uC154\uCE20\uC640 \uD68C\uC0C9 \uBC18\uBC14\uC9C0, \uD558\uC580\uC0C9 \uC6B4\uB3D9\uD654\uB97C \uCC29\uC6A9\uD55C \uAE30\uBCF8 \uCE90\uB9AD\uD130 \uB514\uC790\uC778\uC785\uB2C8\uB2E4."\ncostumeAppearanceOnly: "\uCF54\uC2A4\uD2AC\uC740 \uC5BC\uAD74\xB7\uD5E4\uC5B4\xB7\uC2E0\uCCB4\xB7\uBCF5\uC7A5\uC744 \uD3EC\uD568\uD55C \uCE90\uB9AD\uD130 \uC804\uCCB4 \uB514\uC790\uC778\uC785\uB2C8\uB2E4. \uB2A5\uB825\uCE58\uB098 \uC2A4\uD0AC \uC131\uB2A5\uC5D0\uB294 \uC601\uD5A5\uC744 \uC8FC\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\n\nactionHealingPower: "{ap} AP \xB7 \uC601\uC131 \xD7 {power} HP \uD68C\uBCF5"\nactionMagicPower: "{ap} AP \xB7 (10 + 2 \xD7 \uC601\uC131) \xD7 {power} \uC704\uB825"\nactionGreatswordRequirement: "\uC804\uD22C \uC2AC\uB86F\uACFC \uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uC591\uC190\uAC80\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uBCF8\uC778 \uD134\xB7\uC0AC\uAC70\uB9AC\xB7AP \uC870\uAC74\uC744 \uD655\uC778\uD558\uC138\uC694."\nactionGeneralRequirement: "\uC804\uD22C \uC2AC\uB86F \uB4F1\uB85D\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uBCF8\uC778 \uD134\xB7\uB300\uC0C1\xB7\uC0AC\uAC70\uB9AC\xB7AP \uC870\uAC74\uC744 \uD655\uC778\uD558\uC138\uC694."\nactionRange: "\uC0AC\uAC70\uB9AC {minimum}~{maximum}\uCE78"\nactionFeedingRequirement: "\uD3EC\uC2DD\uC5D0 \uC801\uD569\uD55C \uC2E0\uCCB4\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4."\nactionDrainRate: "\uC2E4\uC81C HP \uD53C\uD574\uC758 {percent}%\uB97C \uC790\uC2E0 HP\uB85C \uD68C\uBCF5\uD569\uB2C8\uB2E4."\n\ncostumeLoading: \uCF54\uC2A4\uD2AC \uC124\uBA85\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\uC785\uB2C8\uB2E4.\ncostumeUnsupported: \uD604\uC7AC \uBBF8\uB9AC\uBCF4\uAE30\uC640 \uC77C\uCE58\uD558\uB294 \uB514\uC790\uC778\uC774 \uC544\uB2D9\uB2C8\uB2E4.\n\ncostumeSponsorUnavailable: \uC2A4\uD3F0\uC11C \uAD11\uACE0\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC124\uBA85\uC744 \uB2EB\uC558\uB2E4 \uB2E4\uC2DC \uC5F4\uBA74 \uC7AC\uC2DC\uB3C4\uD569\uB2C8\uB2E4.\n\nguildMembership: "\uBAA8\uD5D8\uC790\uAE38\uB4DC \uC18C\uC18D"\nguildCertificateIssued: "\uBAA8\uD5D8\uC790\uAE38\uB4DC \uC790\uACA9\uC99D \uBC1C\uAE09 \uC644\uB8CC"\n', "./locales/ko/citizenship.yaml": "title: \uBCF4\uC720 \uC2DC\uBBFC\uAD8C\nunavailable: \uC11C\uBC84\uC5D0\uC11C \uC2DC\uBBFC\uAD8C \uC815\uBCF4\uB97C \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\nempty: \uBC1C\uAE09\uB41C \uC2DC\uBBFC\uAD8C\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\nvalid: \uC720\uD6A8\nexpired: \uB9CC\uB8CC\npending: \uD6A8\uB825 \uC2DC\uC791 \uC804\ninitial: \uAE30\uBCF8 \uBC1C\uAE09\npurchase: \uC720\uB8CC \uBC1C\uAE09\nstarts: \uC720\uD6A8 \uC2DC\uC791\nexpires: \uB9CC\uB8CC\nchecked: \uB9C8\uC9C0\uB9C9 \uC11C\uBC84 \uB3D9\uAE30\uD654 \uAE30\uC900\nhelp: \uC758\uB8B0\uC640 \uC2DC\uC124 \uC774\uC6A9\uC5D0\uB294 \uD574\uB2F9 \uB3C4\uC2DC\uC758 \uC720\uD6A8\uD55C \uC2DC\uBBFC\uAD8C\uC774 \uD544\uC694\uD569\uB2C8\uB2E4.\nvalidCount: '\uC720\uD6A8 {count}\uAC1C'\n\npermitTitle: \uC5EC\uD589\uC790\uC99D\uBA85\uC11C\npermitUnavailable: \uC11C\uBC84\uC5D0\uC11C \uC5EC\uD589\uC790\uC99D\uBA85\uC11C \uC815\uBCF4\uB97C \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\npermitEmpty: \uBCF4\uC720\uD55C \uC5EC\uD589\uC790\uC99D\uBA85\uC11C\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\npermitOwner: \uC18C\uC720\uC790\npermitIssuer: \uBC1C\uAE09 \uACBD\uBE44\uC13C\uD130\npermitIssued: \uBC1C\uAE09\uC77C\n\npermitPurchased: \uC5EC\uD589\uC790\uC99D\uBA85\uC11C\uB97C \uBC1C\uAE09\uD588\uC2B5\uB2C8\uB2E4. \uAC00\uBC29\uC5D0\uC11C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\npermitPrice: \uC5EC\uD589\uC790\uC99D\uBA85\uC11C \uBC1C\uAE09 \uC694\uAE08 \uD655\uC778\npermitQuote: '\uBC1C\uAE09 \uC694\uAE08 {price}P \xB7 \uACAC\uC801 \uB0A8\uC740 \uC2DC\uAC04 {seconds}\uCD08'\npermitExpired: \uACAC\uC801\uC774 \uB9CC\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC694\uAE08\uC744 \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\npermitPurchaseHelp: '{price}P\uB97C \uC9C0\uBD88\uD558\uBA74 \uC9C0\uAE08\uBD80\uD130 7\uC77C\uAC04 \uC720\uD6A8\uD55C \uC5EC\uD589\uC790\uC99D\uBA85\uC11C\uB97C \uBC1C\uAE09\uD569\uB2C8\uB2E4.'\npermitRetry: \uAC19\uC740 \uBC1C\uAE09 \uC694\uCCAD \uB2E4\uC2DC \uD655\uC778\npermitPurchase: \uC5EC\uD589\uC790\uC99D\uBA85\uC11C \uBC1C\uAE09 \uD655\uC815\npermitUncertain: \uBC1C\uAE09 \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC73C\uB85C \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\n\nbarterEnable: \uC7AC\uB8CC\uC640 \uD604\uAE08\uC73C\uB85C \uB0A9\uBD80\nbarterCash: \uD604\uAE08 \uB0A9\uBD80\uC561 (p)\nbarterEmpty: \uB0A9\uBD80\uD560 \uC7AC\uB8CC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\nbarterInvalid: \uD604\uAE08\uACFC \uC7AC\uB8CC \uC218\uB7C9\uC744 \uD655\uC778\uD558\uACE0 \uC7AC\uB8CC\uB97C \uD558\uB098 \uC774\uC0C1 \uC120\uD0DD\uD558\uC138\uC694.\nbarterCashValue: '\uD3F0 {cash}P'\nbarterMaterialQuantity: '{name} \xD7 {quantity}'\nbarterNoChange: '\uC120\uD0DD\uD55C \uD3F0\uACFC \uC7AC\uB8CC\uB97C \uBAA8\uB450 \uB0A9\uBD80\uD569\uB2C8\uB2E4. \uAC70\uC2A4\uB984\uB3C8\uC740 \uC9C0\uAE09\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.'\nbarterPurchaseHelp: '\uBC1C\uAE09\uB8CC {price}P\uB97C \uD655\uC778\uD55C \uD604\uAE08\uACFC \uC7AC\uB8CC\uB85C \uB0A9\uBD80\uD569\uB2C8\uB2E4. \uCD08\uACFC\uC561\uC740 \uBC18\uD658\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.'\nbarterStateChanged: \uBCF4\uC720 \uC0C1\uD0DC\uAC00 \uBCC0\uACBD\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uBC1C\uAE09 \uC694\uAE08\uC744 \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\n", "./locales/ko/city.yaml": "facilities: \uB3C4\uC2DC \uC2DC\uC124\nguild: \uBAA8\uD5D8\uAC00 \uAE38\uB4DC \uD68C\uAD00\nbookshop: \uC11C\uC810\ninn: \uC5EC\uAD00\nworkshop: \uB300\uC7A5\uAC04\xB7\uACF5\uBC29\nmarket: \uC2DC\uC7A5\napproach: \uCD9C\uC785\uAD6C\uB85C \uC774\uB3D9\narrived: \uCD9C\uC785\uAD6C\uC5D0 \uB3C4\uCC29\uD588\uC2B5\uB2C8\uB2E4\nsafeTown: \uB3C4\uC2DC \uC804\uCCB4\uAC00 \uC548\uC804 \uAD6C\uC5ED\uC785\uB2C8\uB2E4\nstaff: '\uB2F4\uB2F9 NPC: {names}'\n", "./locales/ko/common.yaml": 'language: \uC5B8\uC5B4\nbrand: \uC0C8\uB85C\uC6B4 \uC2DC\uAC04\nconnected: \uC5F0\uACB0\uB428\nconnecting: \uC5F0\uACB0 \uD655\uC778 \uC911\nstart: \uC77C\uC0C1\uC758 \uC2DC\uC791\nrelogin: \uB2E4\uC2DC \uB85C\uADF8\uC778\nlogout: \uB85C\uADF8\uC544\uC6C3\nsettings: \uCE90\uB9AD\uD130 \uC124\uC815\nachievements: \uC5C5\uC801 \uBCF4\uAE30\nnearby: \uC8FC\uBCC0\nencounter: \uC870\uC6B0 \uC900\uBE44\nparty: \uD30C\uD2F0\nbattleChat: \uC804\uD22C \uB300\uD654\nchannelChat: \uCC44\uB110 \uB300\uD654\nexplorer: \uC0C8\uB85C\uC6B4 \uBAA8\uD5D8\uAC00\ncharacterName: \uCE90\uB9AD\uD130 \uC774\uB984\n\nclose: "\uB2EB\uAE30"\n', "./locales/ko/cutins.yaml": 'settings: \uAC8C\uC784\uC124\uC815\nshow: \uC561\uC158 \uCEF7\uC778 \uD45C\uC2DC \uC2DC\uAC04\nhelp: \uAE30\uBCF8 3\uCD08\uC774\uBA70 \uC120\uD0DD\uD55C \uC2DC\uAC04\uC774 \uC9C0\uB098\uBA74 \uC790\uB3D9\uC73C\uB85C \uB2EB\uD799\uB2C8\uB2E4. \uAC74\uB108\uB6F0\uAE30\uB294 \uC81C\uACF5\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uC124\uC815\uC740 \uC774 \uBE0C\uB77C\uC6B0\uC800\uC5D0 \uC800\uC7A5\uB429\uB2C8\uB2E4.\npresentation: \uC804\uD22C \uC561\uC158 \uCEF7\uC778\nattack: \uC77C\uBC18 \uACF5\uACA9\nimageFailed: \uC561\uC158 \uCEF7\uC778 \uC774\uBBF8\uC9C0\uB97C \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.\nseconds: "{seconds}\uCD08"\noff: \uB044\uAE30\n\nsettingReadFailed: \uCEF7\uC778 \uC124\uC815\uC744 \uC77D\uC744 \uC218 \uC5C6\uC5B4 \uC5F0\uCD9C\uC744 \uC911\uC9C0\uD588\uC2B5\uB2C8\uB2E4. \uAE30\uBCF8\uAC12\uC744 \uBCF5\uAD6C\uD558\uAC70\uB098 \uAC8C\uC784\uC124\uC815\uC5D0\uC11C \uC2DC\uAC04\uC744 \uB2E4\uC2DC \uC120\uD0DD\uD558\uC138\uC694.\nsettingWriteFailed: \uCEF7\uC778 \uC124\uC815\uC744 \uC800\uC7A5\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC774\uC804 \uC124\uC815\uC744 \uC720\uC9C0\uD569\uB2C8\uB2E4. \uBE0C\uB77C\uC6B0\uC800 \uC800\uC7A5\uC18C \uC811\uADFC\uC744 \uD5C8\uC6A9\uD55C \uB4A4 \uB2E4\uC2DC \uC2DC\uB3C4\uD558\uC138\uC694.\nrestoreDefault: \uAE30\uBCF8 3\uCD08\uB85C \uBCF5\uAD6C\nsettingUnavailable: \uC124\uC815 \uD655\uC778 \uD544\uC694\nassetUnavailable: \uB4F1\uB85D\uB418\uC9C0 \uC54A\uC558\uAC70\uB098 \uC190\uC0C1\uB41C \uCEF7\uC778 \uC678\uD615\uC785\uB2C8\uB2E4. \uC5F0\uCD9C \uC2DC\uAC04\uC774 \uC9C0\uB098\uBA74 \uAC8C\uC784\uC73C\uB85C \uB3CC\uC544\uAC11\uB2C8\uB2E4.\n', "./locales/ko/directmessages.yaml": "open: '1:1 \uBA54\uC2DC\uC9C0'\nretention: '\uB300\uD654\uBCC4 \uCD5C\uADFC 30\uC77C, \uC591\uBC29\uD5A5 \uD569\uACC4 \uCD5C\uB300 100\uAC1C\uB97C \uBCF4\uAD00\uD569\uB2C8\uB2E4. \uBC1C\uC1A1 \uC644\uB8CC\uB294 \uC11C\uBC84 \uC800\uC7A5\uC744 \uB73B\uD558\uBA70 \uC0C1\uB300\uC758 \uC77D\uC74C \uC5EC\uBD80\uAC00 \uC544\uB2D9\uB2C8\uB2E4.'\nnoticeFailed: '\uB3C4\uCC29 \uC54C\uB9BC\uC744 \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uD655\uC778\uD569\uB2C8\uB2E4.'\nsaved: '\uC11C\uBC84\uC5D0 \uC800\uC7A5\uD588\uC2B5\uB2C8\uB2E4.'\npending: '{recipient}\uC5D0\uAC8C \uBCF4\uB0B8 \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC73C\uB85C \uC7AC\uD655\uC778\uD558\uC138\uC694.'\nretry: '\uAE30\uC874 \uBC1C\uC1A1 \uC7AC\uD655\uC778'\nrecipient: '\uB300\uD654 \uC0C1\uB300'\ncharacterId: '\uCE90\uB9AD\uD130 ID'\nselect: '\uC0C1\uB300 \uC120\uD0DD'\nnearby: '\uD604\uC7AC \uB9F5\uC758 \uBAA8\uD5D8\uAC00'\nconversations: '\uCD5C\uADFC \uB300\uD654 \uBAA9\uB85D'\nblocks: '\uC218\uC2E0 \uCC28\uB2E8 \uBAA9\uB85D'\nnext: '\uBAA9\uB85D \uB2E4\uC74C \uD398\uC774\uC9C0'\nhistory: '\uAC1C\uC778 \uB300\uD654 \uB0B4\uC5ED'\nrefresh: '\uCD5C\uC2E0 \uB300\uD654 \uC870\uD68C'\nblock: '\uC774 \uC0C1\uB300 \uC218\uC2E0 \uCC28\uB2E8'\nunblock: '\uC774 \uC0C1\uB300 \uC218\uC2E0 \uCC28\uB2E8 \uD574\uC81C'\nself: '\uB098'\nempty: '\uBCF4\uAD00 \uC911\uC778 \uBA54\uC2DC\uC9C0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.'\nolder: '\uC774\uC804 \uBA54\uC2DC\uC9C0 \uD398\uC774\uC9C0'\nbody: '\uBA54\uC2DC\uC9C0 (1~1000\uC790)'\nsend: '\uBCF4\uB0B4\uAE30'\ninvalidResponse: '\uAC1C\uC778 \uBA54\uC2DC\uC9C0 \uC751\uB2F5\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.'\nsessionChanged: '\uB85C\uADF8\uC778 \uC138\uC158\uC774 \uBCC0\uACBD\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC5F4\uC5B4 \uC8FC\uC138\uC694.'\npendingSend: '\uC9C4\uD589 \uC911\uC774\uAC70\uB098 \uACB0\uACFC\uAC00 \uBD88\uBA85\uD655\uD55C \uBC1C\uC1A1\uC744 \uBA3C\uC800 \uD655\uC778\uD558\uC138\uC694.'\ninvalidRecipient: '\uBCF8\uC778\uC774 \uC544\uB2CC \uBAA8\uD5D8\uAC00 \uCE90\uB9AD\uD130 ID\uB97C \uC120\uD0DD\uD558\uC138\uC694.'\ninvalidText: '\uACF5\uBC31\uB9CC \uC785\uB825\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uBA54\uC2DC\uC9C0\uB294 1~1000\uC790\uC785\uB2C8\uB2E4.'\nrequestExpired: '\uCD5C\uCD08 \uBC1C\uC1A1 \uC2DC\uAC04\uC774 \uC9C0\uB0AC\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uBCF4\uB0B4\uAE30\uB97C \uB204\uB974\uC138\uC694.'\nnoPendingSend: '\uC7AC\uD655\uC778\uD560 \uBC1C\uC1A1\uC774 \uC5C6\uAC70\uB098 \uC7AC\uC2DC\uB3C4 \uAE30\uD55C\uC774 \uC9C0\uB0AC\uC2B5\uB2C8\uB2E4.'\nautoRefresh: '\uCD5C\uC2E0 \uB300\uD654\uB97C 30\uCD08\uB9C8\uB2E4 \uC790\uB3D9\uC73C\uB85C \uD655\uC778\uD569\uB2C8\uB2E4.'\nrefreshFailed: '\uCD5C\uC2E0 \uB300\uD654\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC74C \uC8FC\uAE30\uC5D0 \uC7AC\uC2DC\uB3C4\uD558\uAC70\uB098 \uC9C1\uC811 \uC870\uD68C\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.'\nhistoryPaused: '\uC774\uC804 \uB0B4\uC5ED\uC744 \uC77D\uB294 \uB3D9\uC548 \uC790\uB3D9 \uAC31\uC2E0\uC744 \uBA48\uCDA5\uB2C8\uB2E4. \uCD5C\uC2E0 \uB300\uD654 \uC870\uD68C\uB85C \uB3CC\uC544\uAC08 \uC218 \uC788\uC2B5\uB2C8\uB2E4.'\nnoticeLoading: '\uBA54\uC2DC\uC9C0 \uC54C\uB9BC \uD655\uC778 \uC911'\nnoticeCount: '\uC0C8 \uBA54\uC2DC\uC9C0 \uC54C\uB9BC {count}\uAC1C'\n", "./locales/ko/equipment.yaml": 'title: \uC7A5\uBE44\nrefresh: \uC0C8\uB85C\uACE0\uCE68\nloading: \uC7A5\uBE44\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.\nslots: \uC7A5\uCC29 \uC2AC\uB86F\nmainHand: \uC8FC\uBB34\uAE30\noffHand: \uBCF4\uC870 \uC190\nbody: \uBAB8\uD1B5\nback: \uB4F1\nfeet: \uBC1C\ntool: \uB3C4\uAD6C\nemptySlot: \uBBF8\uC7A5\uCC29\nweight: "\uC18C\uC9C0 \uC7A5\uBE44 \uBB34\uAC8C {weight} g"\nitemWeight: \uBB34\uAC8C\ndurability: \uB0B4\uAD6C\uB3C4\nattack: \uACF5\uACA9 \uBCF4\uC815\ndefense: \uBC29\uC5B4 \uBCF4\uC815\nequip: \uC7A5\uCC29\nunequip: \uD574\uC81C\nequipped: \uC7A5\uCC29 \uC911\nreserved: \uC608\uC57D \uC911\nbroken: \uB0B4\uAD6C\uB3C4 \uC18C\uC9C4\nnoItems: \uC774 \uD398\uC774\uC9C0\uC5D0 \uD574\uB2F9 \uC2AC\uB86F\uC758 \uC7A5\uBE44\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\nmore: \uB354 \uBCF4\uAE30\nsaved: \uC7A5\uBE44 \uAD6C\uC131\uC744 \uC800\uC7A5\uD588\uC2B5\uB2C8\uB2E4.\nuncertain: \uCC98\uB9AC \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC73C\uB85C \uACB0\uACFC\uB97C \uB2E4\uC2DC \uD655\uC778\uD574 \uC8FC\uC138\uC694.\nretry: \uACB0\uACFC \uB2E4\uC2DC \uD655\uC778\ncomparison: "\uD604\uC7AC \uC2AC\uB86F \uB300\uBE44 \uACF5\uACA9 {attack} \xB7 \uBC29\uC5B4 {defense}"\n\nhistory: "\uBCC0\uACBD \uC774\uB825"\ncloseHistory: "\uC774\uB825 \uB2EB\uAE30"\nnoHistory: "\uC800\uC7A5\uB41C \uBCC0\uACBD \uC774\uB825\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uACFC\uAC70 \uAE30\uB85D\uC740 \uC18C\uAE09 \uC0DD\uC131\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\nhistoryChanged: "\uC774\uB825 \uD398\uC774\uC9C0\uAC00 \uBCC0\uACBD\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC0C8\uB85C\uACE0\uCE68\uD574 \uC8FC\uC138\uC694."\nhistoryAcquired: "\uC81C\uC791 \uC218\uB839"\nhistoryEquipped: "\uC7A5\uCC29"\nhistoryUnequipped: "\uD574\uC81C"\nhistoryRepairReserved: "\uC218\uB9AC \uB9E1\uAE40"\nhistoryRepaired: "\uC218\uB9AC \uC218\uB839"\nhistoryWorn: "\uC804\uD22C \uB9C8\uBAA8"\n\ninventoryChanged: "\uC7A5\uBE44 \uBAA9\uB85D\uC774 \uBCC0\uACBD\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uBAA9\uB85D\uC744 \uC0C8\uB85C\uACE0\uCE68\uD558\uC138\uC694."\nactionPoints: "\uAE30\uBCF8 \uCD5C\uB300 AP {base} \xB7 \uC7A5\uCC29 {weight} g \xB7 \uC911\uB7C9 \uAC10\uC18C {penalty} AP \xB7 \uCD5C\uC885 \uCD5C\uB300 AP {maximum}"\nzeroActionPoints: \uC911\uB7C9 \uB54C\uBB38\uC5D0 \uCD5C\uB300 AP\uAC00 0\uC785\uB2C8\uB2E4. AP\uAC00 \uD544\uC694\uD55C \uD589\uB3D9\uC744 \uD558\uB824\uBA74 \uC804\uD22C \uC804\uC5D0 \uC7A5\uBE44\uB97C \uAC00\uBCCD\uAC8C \uBC14\uAFB8\uC138\uC694.\nequipAp: "\uC7A5\uCC29 \uD6C4 \uCD5C\uB300 AP: {maximum}"\nunequipAp: "\uD574\uC81C \uD6C4 \uCD5C\uB300 AP: {maximum}"\nhistoryRevoked: "\uAC1C\uBC1C\uC790 \uD68C\uC218"\n\nhistoryPagination: \uC7A5\uBE44 \uBCC0\uACBD \uC774\uB825 \uD398\uC774\uC9C0 \uC774\uB3D9\npreviousPage: \uC774\uC804\nnextPage: \uB2E4\uC74C\nhistoryPage: "{page}\uD398\uC774\uC9C0"\ninventoryPagination: \uC7A5\uBE44 \uBAA9\uB85D \uD398\uC774\uC9C0 \uC774\uB3D9\ninventoryPageHelp: \uD604\uC7AC \uD398\uC774\uC9C0\uC758 \uC7A5\uBE44 \uC911 \uC120\uD0DD\uD55C \uC7A5\uCC29 \uBD80\uC704\uC5D0 \uB9DE\uB294 \uC7A5\uBE44\uB97C \uD45C\uC2DC\uD569\uB2C8\uB2E4.\n', "./locales/ko/field.yaml": `points: \uD544\uB4DC\uD3EC\uC778\uD2B8
connecting: \uC5F0\uACB0 \uC911
maximum: \uCD5C\uB300 1,000 \xB7 \uBD84\uB2F9 +1
next: \uB2E4\uC74C +1 \xB7 {seconds}\uCD08
grass: \uD480\uBC2D
dew: \uC774\uC2AC \uC9C0\uBA74
flowers: \uAF43\uBC2D
road: \uD759\uAE38
legend: \uD1B5\uD589 \uAC00\uB2A5\uD55C \uC9C0\uD615 \uBC94\uB840
guidance: \uACC4\uB2E8\uC73C\uB85C \uB192\uC774 \uC774\uB3D9 \xB7 \uC808\uBCBD\xB7\uBC14\uC704\xB7\uC218\uD480\xB7\uD638\uC218\uB294 \uD1B5\uD589 \uBD88\uAC00
debt: FP\uAC00 \uC74C\uC218\uC785\uB2C8\uB2E4 \xB7 \uD544\uB4DC \uD589\uB3D9\uC740 \uCDA9\uC804 \uD6C4 \uAC00\uB2A5\uD569\uB2C8\uB2E4
destinationHeading: '{name} \uC5F0\uACB0 \uC9C0\uC810'
travelTo: '{name} \uC774\uB3D9'
destinationArrival: \uC5F0\uACB0 \uC9C0\uC810\uC5D0 \uB3C4\uCC29\uD588\uC2B5\uB2C8\uB2E4. \uB2E4\uC74C \uB9F5\uC73C\uB85C \uC774\uB3D9\uD560 \uC218 \uC788\uC5B4\uC694.
connectedMaps: '\uB2E4\uB978 \uB9F5\uC73C\uB85C \uAC00\uB294 \uAE38 \xB7 {count}'
currentPosition: \uD604\uC7AC \uC704\uCE58
gridDistance: '\uACA9\uC790 \uAC70\uB9AC {count}\uCE78'
noConnections: \uC5F0\uACB0\uB41C \uB9F5\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.
destinationRoute: '\uC5F0\uACB0 \uC9C0\uC810\uAE4C\uC9C0 {count}\uCE78 \xB7 \uB3C4\uCC29 \uD6C4 \uB9F5 \uC774\uB3D9\uC744 \uC120\uD0DD\uD558\uC138\uC694.'
aggressiveMonster: "\uC120\uACF5 \uBAAC\uC2A4\uD130"
passiveMonster: "\uBE44\uC120\uACF5 \uBAAC\uC2A4\uD130"
mapConnection: "\uB9F5 \uC5F0\uACB0"
nearbyEvents: "\uAC00\uAE4C\uC6B4 \uC774\uBCA4\uD2B8 \uC9C0\uC810"
noEvents: "\uC8FC\uBCC0\uC5D0 \uC120\uD0DD\uD560 \uC774\uBCA4\uD2B8 \uC9C0\uC810\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."
debtHelp: "FP\uAC00 \uC74C\uC218\uC5EC\uC11C \uD544\uB4DC \uD589\uB3D9\uC744 \uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uCDA9\uC804\uC744 \uAE30\uB2E4\uB824 \uC8FC\uC138\uC694."
walkingProgress: "\uC774\uB3D9 \uC9C4\uD589"
walking: "\uC774\uB3D9 \uC911"
stopping: "\uC774\uB3D9\uC744 \uBA48\uCD94\uB294 \uC911"
walkingHeading: "\uBAA9\uC801\uC9C0\uB85C \uC774\uB3D9\uD558\uACE0 \uC788\uC5B4\uC694"
stopRequested: "\uC911\uC9C0 \uC694\uCCAD\uB428"
stop: "\uC774\uB3D9 \uC911\uC9C0"
stopAfterTile: "\uC9C4\uD589 \uC911\uC778 \uD55C \uCE78\uC744 \uB9C8\uCE58\uBA74 \uBA48\uCDA5\uB2C8\uB2E4."
stopAnytime: "\uC5B8\uC81C\uB4E0 \uC774\uB3D9\uC744 \uC911\uC9C0\uD560 \uC218 \uC788\uC5B4\uC694."
progressLabel: "\uC774\uB3D9 \uC9C4\uD589\uB960"
tileCommands: "\uD0C0\uC77C \uBA85\uB839"
explore: "\uC8FC\uBCC0 \uB458\uB7EC\uBCF4\uAE30"
whereTo: "\uC5B4\uB514\uB85C \uB5A0\uB0A0\uAE4C\uC694?"
selectHint: "\uD0C0\uC77C \uC120\uD0DD \u2192 \uD589\uB3D9 \uD655\uC778"
finishPreparation: "\uC870\uC6B0 \uC900\uBE44\uB97C \uC644\uB8CC\uD558\uAC70\uB098 \uCDE8\uC18C\uD55C \uB4A4 \uC774\uB3D9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."
busy: "\uC694\uCCAD \uCC98\uB9AC \uC911\uC5D0\uB294 \uD589\uB3D9\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4."
selectedLocation: "\uC120\uD0DD\uD55C \uC704\uCE58"
targetHeading: "\uB300\uC0C1 \uD655\uC778"
locationHeading: "\uBAA9\uC801\uC9C0 \uD655\uC778"
monsterEncounter: "\uBAAC\uC2A4\uD130 \uC870\uC6B0"
blockedTerrain: "\uC774\uB3D9 \uBD88\uAC00 \uC9C0\uD615"
safeArea: "\uC548\uC804 \uAD6C\uC5ED"
explorationPoint: "\uD0D0\uC0C9 \uC9C0\uC810"
clearSelection: "\uC120\uD0DD \uD574\uC81C"
clear: "\uD574\uC81C"
aggressiveWarning: "! \uC120\uACF5 \xB7 \uC811\uADFC \uC8FC\uC758"
passive: "\uBE44\uC120\uACF5"
aggressive: "\uC120\uACF5"
encounterBusy: "\uB2E4\uB978 \uC870\uC6B0\uAC00 \uC9C4\uD589 \uC911\uC785\uB2C8\uB2E4."
noApproach: "\uC811\uADFC \uAC00\uB2A5\uD55C \uACBD\uB85C\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."
adjacent: "\uC778\uC811 \xB7 \uBC14\uB85C \uC870\uC6B0\uD560 \uC218 \uC788\uC5B4\uC694"
approachEncounter: "\uC811\uADFC \uD6C4 \uC870\uC6B0"
startEncounter: "\uC870\uC6B0 \uC2DC\uC791"
blockedHelp: "\uBC14\uC704\xB7\uC218\uD480\xB7\uBB3C\uC740 \uD1B5\uACFC\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uB2E4\uB978 \uD0C0\uC77C\uC744 \uC120\uD0DD\uD558\uC138\uC694."
currentHelp: "\uD604\uC7AC \uC11C \uC788\uB294 \uC704\uCE58\uC785\uB2C8\uB2E4. \uB2E4\uB978 \uD0C0\uC77C\uC744 \uC120\uD0DD\uD558\uC138\uC694."
noRoute: "\uD604\uC7AC \uC704\uCE58\uC5D0\uC11C \uAC08 \uC218 \uC788\uB294 \uACBD\uB85C\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uB2E4\uB978 \uC9C0\uC810\uC744 \uC120\uD0DD\uD558\uC138\uC694."
insufficientFp: "\uC774\uB3D9\uC5D0\uB294 1\uCE78\uB2F9 1 FP\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4. \uCDA9\uC804\uC744 \uAE30\uB2E4\uB824 \uC8FC\uC138\uC694."
tileDetails: "\uC88C\uD45C"
moveToGate: "\uC5F0\uACB0 \uC9C0\uC810\uC73C\uB85C \uC774\uB3D9"
moveHere: "\uC774\uB3D9"
available: "\uD0D0\uC0C9 \uAC00\uB2A5"
unavailable: "\uC870\uC6B0 \uBD88\uAC00"
preparation: "\uC870\uC6B0 \uC900\uBE44"
waitingParty: "\uB3D9\uB8CC \uC900\uBE44 \uB300\uAE30"
ready: "\uC900\uBE44 \uC644\uB8CC"
cancelReservation: "\uC608\uC57D \uCDE8\uC18C"
nearby: "\uC8FC\uBCC0 \uD0D0\uC0C9"
nearbyHelp: "\uAC00\uAE4C\uC6B4 \uBAAC\uC2A4\uD130\uBD80\uD130 \uD45C\uC2DC\uD569\uB2C8\uB2E4. \uC120\uD0DD\uD558\uBA74 \uB9F5\uC5D0\uC11C \uD655\uC778\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."
noMonsters: "\uC774 \uB9F5\uC5D0\uB294 \uD45C\uC2DC\uD560 \uBAAC\uC2A4\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."
walked: "{completed} / {total}\uCE78 \uC774\uB3D9"
approachCost: "\uC778\uC811 \uC704\uCE58\uAE4C\uC9C0 {count}\uCE78 \xB7 {count} FP"
walkRoute: "\uAC78\uC5B4\uC11C {count}\uCE78 \xB7 \uAE38\uACFC \uACC4\uB2E8\uC744 \uB530\uB77C \uC774\uB3D9\uD569\uB2C8\uB2E4."
coordinates: "\uC88C\uD45C {column}, {row} \xB7 \uB192\uC774 {height}"
moveCost: " \xB7 {count}\uCE78 / {count} FP"
readyProgress: "\uC900\uBE44 {ready}/{total} \xB7 \uB0A8\uC740 \uC2DC\uAC04 {seconds}\uCD08"
remainingMonsters: "\uB098\uBA38\uC9C0 \uBAAC\uC2A4\uD130 {count}\uB9C8\uB9AC"
legacyslime: \uC2AC\uB77C\uC784
legacybeast: \uC57C\uC218
legacygiant: \uAC70\uC778
monster: \uBAAC\uC2A4\uD130
approachFieldRequired: \uD0D0\uC0C9 \uC911\uC5D0\uB9CC \uC870\uC6B0\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.
approachFpDebt: FP\uAC00 \uC74C\uC218\uC5EC\uC11C \uD544\uB4DC \uD589\uB3D9\uC744 \uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uCDA9\uC804\uC744 \uAE30\uB2E4\uB824 \uC8FC\uC138\uC694.
approachTargetLost: \uC120\uD0DD\uD55C \uBAAC\uC2A4\uD130\uC640 \uB354 \uC774\uC0C1 \uC870\uC6B0\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.
approachTooLong: \uBAAC\uC2A4\uD130 \uC811\uADFC \uAC70\uB9AC\uAC00 \uAE38\uC5B4 \uC774\uB3D9\uC744 \uBA48\uCDC4\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uC120\uD0DD\uD574 \uC8FC\uC138\uC694.
aggroInterruption: \uBAAC\uC2A4\uD130\uC758 \uC120\uACF5\uC73C\uB85C \uD544\uB4DC \uD589\uB3D9\uC774 \uC911\uB2E8\uB418\uC5B4 \uC804\uD22C\uC5D0 \uC9C4\uC785\uD588\uC2B5\uB2C8\uB2E4. \uC774\uBBF8 \uC774\uB3D9\uD55C \uC704\uCE58\uB294 \uC720\uC9C0\uB418\uBA70 \uB0A8\uC740 \uC774\uB3D9\xB7\uC870\uC6B0 \uC694\uCCAD\uC740 \uB2E4\uC2DC \uC2E4\uD589\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.

resources: \uCCB4\uB825\uACFC \uD544\uB4DC\uD3EC\uC778\uD2B8
healthUnknown: \uBBF8\uD655\uC778

shortcutDistance: "{count}\uCE78"
arrivalCompact: "\uB3C4\uCC29 \xB7 \uB9F5 \uC774\uB3D9 \uAC00\uB2A5"
adjacentCompact: "\uC778\uC811"
compactCoordinates: "\uC88C\uD45C {column},{row} \xB7 \uB192\uC774 {height}"
terrainFpPreview: "\uAE30\uBCF8 {base} FP \xB7 \uC608\uC0C1 {expected} FP \xB7 \uCD5C\uB300 {max} FP. \uCD94\uAC00 \uC18C\uBAA8\uB85C FP\uAC00 0 \uC774\uD558\uAC00 \uB418\uBA74 \uC911\uB2E8\uD569\uB2C8\uB2E4."
terrainFpButton: " \xB7 {count}\uCE78"

healthDepleted: \uCCB4\uB825\uC774 \uC5C6\uC5B4 \uC870\uC6B0\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uD734\uC2DD\uD558\uAC70\uB098 \uB85C\uADF8\uC544\uC6C3 \uD6C4 \uD68C\uBCF5\uD558\uC138\uC694.

restStart: \uD734\uC2DD
restStop: \uD734\uC2DD \uC885\uB8CC
restProgress: \uD734\uC2DD \uC911 \xB7 1\uBD84\uB2F9 HP +{amount} \xB7 \uB2E4\uC74C \uD68C\uBCF5 {seconds}\uCD08
restHint: \uC774\uB3D9\xB7\uD589\uB3D9\xB7\uC120\uACF5 \uC2DC \uD734\uC2DD\uC774 \uB05D\uB098\uBA70 \uB0A8\uC740 \uCD08\uB294 \uBC84\uB9BD\uB2C8\uB2E4.
firstAidButton: "\uC751\uAE09\uCC98\uCE58 \xB7 \uBD95\uB300 {count}"
firstAidHint: "\uC548\uC804\uC9C0\uB300 \uBC16\uC5D0\uC11C \uBD95\uB300 {count}\uAC1C\uB85C HP {amount} \uD68C\uBCF5 \xB7 \uBB38\uD574 {literacy} \uC774\uC0C1 \uD544\uC694"
restCompactProgress: HP +{amount} \xB7 {seconds}\uCD08
terrainFpCompact: "\uC608\uC0C1 {expected} FP \xB7 \uCD5C\uB300 {max}"
terrainFpHelp: "\uC774\uB3D9 \uC911 \uC9C0\uD615 \uCD94\uAC00 \uC18C\uBAA8\uB85C FP\uAC00 0 \uC774\uD558\uAC00 \uB418\uBA74 \uBA48\uCDA5\uB2C8\uB2E4."

recoveryPending: \uC804\uD22C\uBD88\uB2A5 \uD6C4 \uCD5C\uB300 HP\uC758 50% \uC774\uC0C1\uC744 \uD68C\uBCF5\uD574\uC57C \uC774\uB3D9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uD734\uC2DD\uD558\uAC70\uB098 \uB85C\uADF8\uC544\uC6C3 \uD6C4 \uD68C\uBCF5\uD558\uC138\uC694.

scoutButton: '\uC815\uCC30 \xB7 {cost} FP'
scoutHelp: '\uD604\uC7AC \uAC70\uB9AC \uC81C\uD55C {range}\uCE78 \xB7 \uC2DC\uB3C4\uB2F9 {cost} FP'
scoutFailed: '\uAD00\uCE21 \uC2E4\uD328 \xB7 \uAC1C\uCCB4 \uC218 \uBBF8\uD655\uC778'
scoutCountExact: '\uAD00\uCE21: {count}\uB9C8\uB9AC'
scoutCountRange: '\uAD00\uCE21: {minimum}~{maximum}\uB9C8\uB9AC'
scoutCountAtLeast: '\uAD00\uCE21: {minimum}\uB9C8\uB9AC \uC774\uC0C1'
scoutExpires: '{seconds}\uCD08 \uD6C4 \uB9CC\uB8CC'

scoutRiskLow: \uC704\uD5D8\uB3C4 \uB0AE\uC74C
scoutRiskEven: \uC704\uD5D8\uB3C4 \uB300\uB4F1
scoutRiskHigh: \uC704\uD5D8
scoutRiskVeryHigh: \uB9E4\uC6B0 \uC704\uD5D8
scoutRiskUnknown: \uC704\uD5D8\uB3C4 \uD310\uB2E8 \uBD88\uAC00
scoutRiskHelp: \uCC38\uAC00 \uAC00\uB2A5\uD55C \uD30C\uD2F0\uC758 \uC804\uD22C \uC131\uC7A5 \uC218\uC900\uACFC \uBE44\uAD50\uD569\uB2C8\uB2E4. \uD604\uC7AC \uCCB4\uB825\xB7\uC9C0\uD615\xB7\uC804\uC220\uC744 \uBC18\uC601\uD55C \uC2B9\uB960\uC774 \uC544\uB2D9\uB2C8\uB2E4.
guardCenterHelp: \uC774 \uB3C4\uC2DC \uC785\uAD6C\uC5D0\uB294 \uACBD\uBE44\uC13C\uD130\uAC00 \uC788\uC2B5\uB2C8\uB2E4. \uD604\uC9C0 \uC2DC\uBBFC\uAD8C\uC774 \uC5C6\uC73C\uBA74 \uC774\uACF3\uC5D0\uC11C \uC5EC\uD589\uC790\uC99D\uBA85\uC11C\uB97C \uBC1C\uAE09\uBC1B\uC544 \uC785\uC7A5\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uBC1C\uAE09 \uCC3D\uAD6C\uB294 \uC785\uAD6C\uC5D0 \uB3C4\uCC29\uD558\uBA74 \uC5F4\uB9BD\uB2C8\uB2E4.
exploreHelp: "\uD0D0\uC0C9\uC740 FP {cost}\uB97C \uC18C\uBE44\uD569\uB2C8\uB2E4. \uC131\uACF5 \uC2DC \uC790\uB3D9\uC73C\uB85C \uC218\uC9D1\uD569\uB2C8\uB2E4."
exploreRequirements: "\uD0D0\uC0C9 \uC2A4\uD0AC 1\xB7\uBB38\uD574 2 \uD544\uC694. \uAC70\uB9AC {range}\uCE78 \xB7 \uC131\uACF5\uB960 {chance}%"
exploreMineral: \uAD11\uBB3C\uD0D0\uC0C9
exploreTreasure: \uBCF4\uBB3C\uD0D0\uC0C9
exploreSuccess: \uBC1C\uACAC\uD55C \uC790\uC6D0\uC744 \uC218\uC9D1\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC7A5\uC18C\uB294 24\uC2DC\uAC04 \uB4A4 \uC7AC\uD0D0\uC0C9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.
exploreFailure: \uBC1C\uACAC\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC7A5\uC18C\uB294 30\uCD08 \uB4A4 \uC7AC\uD0D0\uC0C9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.
exploreReward: "\uD68D\uB4DD: {reward}"
exploreBusy: \uD604\uC7AC \uD589\uB3D9\uC744 \uB9C8\uCE58\uACE0 \uD544\uB4DC\uC5D0\uC11C \uD0D0\uC0C9\uD558\uC138\uC694.
exploreSafe: \uC548\uC804\uC9C0\uB300 \uBC16\uC73C\uB85C \uC774\uB3D9\uD55C \uB4A4 \uD0D0\uC0C9\uD558\uC138\uC694.
exploreSkill: \uD574\uB2F9 \uD0D0\uC0C9 \uC2A4\uD0AC 1\uB808\uBCA8\uACFC \uC0AC\uC6A9 \uAC00\uB2A5\uD55C \uBB38\uD574 2\uB808\uBCA8\uC774 \uD544\uC694\uD569\uB2C8\uB2E4.
exploreRange: "\uC120\uD0DD\uD55C \uC7A5\uC18C\uC5D0\uC11C {range}\uCE78 \uC774\uB0B4\uB85C \uC774\uB3D9\uD558\uC138\uC694."
exploreFp: "FP\uB97C {cost} \uC774\uC0C1 \uD68C\uBCF5\uD55C \uB4A4 \uD0D0\uC0C9\uD558\uC138\uC694."

partyTravelBlocked: \uC628\uB77C\uC778 \uD30C\uD2F0 \uC18C\uC18D\uC778 \uB3D9\uC548\uC5D0\uB294 \uB9F5\uC744 \uC774\uB3D9\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uD30C\uD2F0 \uBA54\uB274\uC5D0\uC11C \uD0C8\uD1F4\uD55C \uB4A4 \uC774\uB3D9\uD558\uC138\uC694.
`, "./locales/ko/formation.yaml": `title: \uD30C\uD2F0 \uBAA8\uC9D1
count: '\uD604\uC7AC \uD3B8\uC131 {count} / 4\uBA85 (\uBCF8\uC778 \uD3EC\uD568)'
help: \uC774 \uAE38\uB4DC\uC5D0 \uB4F1\uB85D\uB41C \uCE90\uB9AD\uD130\uB97C \uC120\uD0DD\uD569\uB2C8\uB2E4. \uC0C8 \uB300\uC5EC\uB294 7\uC77C\uAC04 \uC720\uC9C0\uB418\uBA70, \uD30C\uD2F0\uC5D0\uC11C \uD574\uC81C\uD574\uB3C4 \uB300\uC5EC\uB294 \uC885\uB8CC\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.
available: \uBAA8\uC9D1 \uAC00\uB2A5
borrowed: \uB300\uC5EC \uC911 \xB7 \uAE30\uC874 \uBCF5\uC0AC\uBCF8\uC73C\uB85C \uD3B8\uC131
cpBlocked: CP \uD3B8\uC131 \uBC94\uC704 \uCD08\uACFC
full: \uB300\uC5EC \uC815\uC6D0 \uB9C8\uAC10
selected: \uC774\uBBF8 \uD30C\uD2F0\uC5D0 \uD3B8\uC131\uB428
empty: \uC774 \uAE38\uB4DC\uC5D0 \uB4F1\uB85D\uB41C \uB2E4\uB978 \uD6C4\uBCF4\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.
choose: \uD6C4\uBCF4 \uC120\uD0DD
confirmName: '{name} \uCE90\uB9AD\uD130\uB97C \uD30C\uD2F0\uC5D0 \uB4F1\uB85D\uD569\uB2C8\uB2E4.'
add: \uD30C\uD2F0 \uBAA8\uC9D1 \uB4F1\uB85D
remove: \uD30C\uD2F0 \uBAA8\uC9D1 \uD574\uC81C
next: \uB2E4\uC74C \uD6C4\uBCF4
recover: \uD3B8\uC131 \uACB0\uACFC \uD655\uC778\xB7\uC7AC\uC2DC\uB3C4
pending: \uD30C\uD2F0 \uC815\uBCF4\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.
saved: \uD30C\uD2F0 \uD3B8\uC131\uC744 \uBC18\uC601\uD588\uC2B5\uB2C8\uB2E4.
manage: \uD604\uC7AC \uD30C\uD2F0 \uD3B8\uC131
fieldHelp: \uD544\uB4DC\uC5D0\uC11C \uD30C\uD2F0 \uD3B8\uC131\uC744 \uD574\uC81C\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uD574\uC81C\uD574\uB3C4 7\uC77C \uB300\uC5EC\uB294 \uC720\uC9C0\uB429\uB2C8\uB2E4. \uCE90\uB9AD\uD130\uB97C \uCD94\uAC00\uD558\uB824\uBA74 \uAE38\uB4DC\uB97C \uBC29\uBB38\uD558\uC138\uC694.
expired: \uB300\uC5EC \uB9CC\uB8CC \xB7 \uD3B8\uC131 \uD574\uC81C \uD544\uC694

noviceName: "\uCD08\uBCF4 \uAE38\uB4DC\uC6D0"
noviceTerms: "\uAE38\uB4DC \uAE30\uBCF8 \uD30C\uD2F0\uC6D0 \xB7 \uBB34\uB8CC 7\uC77C \uACC4\uC57D \xB7 \uB204\uC801 CP \xB120% \uD3B8\uC131 \uC870\uAC74 \xB7 \uC7AC\uB8CC \uB2F9\uCCA8\uBD84\uC740 \uAE38\uB4DC \uADC0\uC18D"
`, "./locales/ko/guild.yaml": "title: \uAE38\uB4DC\uC5D0 \uC7AC\uB8CC \uD310\uB9E4\nhelp: \uBCF4\uC720 \uC7AC\uB8CC\uB97C \uAE38\uB4DC\uC5D0 \uD310\uB9E4\uD569\uB2C8\uB2E4. \uC2DC\uBBFC\uAD8C \uC5C6\uC774 \uC774\uC6A9\uD560 \uC218 \uC788\uC73C\uBA70 FP\uB294 \uC18C\uBAA8\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\nempty: \uD310\uB9E4\uD560 \uC7AC\uB8CC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\nmaterial: \uD310\uB9E4\uD560 \uC7AC\uB8CC\nchoose: \uC7AC\uB8CC\uB97C \uC120\uD0DD\uD558\uC138\uC694\noption: '{name} \xB7 \uBCF4\uC720 {count}\uAC1C \xB7 \uAC1C\uB2F9 {price} P'\nquantity: '\uD310\uB9E4 \uC218\uB7C9 (\uCD5C\uB300 {max}\uAC1C)'\nquote: \uC218\uB839\uC561 \uD655\uC778\ntotal: '{count}\uAC1C \uD310\uB9E4 \xB7 {price} P \uC218\uB839'\nconfirm: \uD310\uB9E4 \uD655\uC815\nretry: \uAC70\uB798 \uACB0\uACFC \uD655\uC778\xB7\uC7AC\uC2DC\uB3C4\nuncertain: \uCC98\uB9AC \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uAC70\uB798\uC758 \uACB0\uACFC\uB97C \uD655\uC778\uD55C \uB4A4 \uBBF8\uCC98\uB9AC\uB41C \uACBD\uC6B0\uC5D0\uB9CC \uC7AC\uC2DC\uB3C4\uD569\uB2C8\uB2E4.\npending: \uAC70\uB798 \uC815\uBCF4\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.\nsold: \uD310\uB9E4\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.\ncitizenshipPrice: \uC2DC\uBBFC\uAD8C \uAC00\uACA9 \uC870\uD68C\ncitizenshipQuote: '\uD604\uC7AC \uC2DC\uBBFC\uAD8C \uAC00\uACA9 {price} P \xB7 \uACAC\uC801 \uC720\uD6A8 {seconds}\uCD08'\ncitizenshipExpired: \uACAC\uC801\uC774 \uB9CC\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uAC00\uACA9\uC744 \uB2E4\uC2DC \uC870\uD68C\uD558\uC138\uC694.\ncitizenshipPurchaseHelp: '{price} P\uB97C \uC9C0\uBD88\uD558\uBA74 \uC774 \uB3C4\uC2DC\uC758 \uC2DC\uBBFC\uAD8C\uC744 1\uB144\uAC04 \uBC1C\uAE09\uD569\uB2C8\uB2E4.'\ncitizenshipPurchase: \uC2DC\uBBFC\uAD8C \uBC1C\uAE09 \uD655\uC815\ncitizenshipRetry: \uBC1C\uAE09 \uACB0\uACFC \uD655\uC778\xB7\uC7AC\uC2DC\uB3C4\ncitizenshipUncertain: \uCC98\uB9AC \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uBC1C\uAE09 \uC694\uCCAD\uC744 \uB2E4\uC2DC \uD655\uC778\uD569\uB2C8\uB2E4.\ncitizenshipPurchased: \uC2DC\uBBFC\uAD8C \uBC1C\uAE09\uC774 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4.\nregistrationStatus: \uB0B4 \uCE90\uB9AD\uD130 \uD6C4\uBCF4 \uB4F1\uB85D \uC0C1\uD0DC\nregistered: \uB0B4 \uCE90\uB9AD\uD130\uAC00 \uC774 \uB3C4\uC2DC\uC758 \uBAA8\uC9D1 \uD6C4\uBCF4\uB85C \uB4F1\uB85D\uB418\uC5B4 \uC788\uC2B5\uB2C8\uB2E4.\nunregistered: \uB0B4 \uCE90\uB9AD\uD130\uAC00 \uC774 \uB3C4\uC2DC\uC758 \uBAA8\uC9D1 \uD6C4\uBCF4\uB85C \uB4F1\uB85D\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4.\nregistrationHelp: \uB2E4\uB978 \uC720\uC800\uAC00 \uBAA8\uC9D1\uD560 \uC218 \uC788\uB3C4\uB85D \uB0B4 \uCE90\uB9AD\uD130\uB97C \uD6C4\uBCF4\uB85C \uACF5\uAC1C\uD569\uB2C8\uB2E4. \uD6C4\uBCF4\uC5D0\uC11C \uB0B4\uB824\uB3C4 \uC774\uBBF8 \uC131\uB9BD\uD55C 7\uC77C \uB300\uC5EC\uB294 \uC720\uC9C0\uB429\uB2C8\uB2E4. \uB2E4\uB978 \uCE90\uB9AD\uD130\uC758 \uD30C\uD2F0 \uD3B8\uC131\uACFC\uB294 \uBCC4\uAC1C\uC785\uB2C8\uB2E4.\nregister: \uB0B4 \uCE90\uB9AD\uD130 \uD6C4\uBCF4 \uB4F1\uB85D\nunregister: \uB0B4 \uCE90\uB9AD\uD130 \uD6C4\uBCF4 \uD574\uC81C\nregistrationUncertain: \uBCC0\uACBD \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC0C1\uD0DC \uD655\uC778 \uBC84\uD2BC\uC73C\uB85C \uD604\uC7AC \uD30C\uD2F0 \uBAA8\uC9D1 \uB4F1\uB85D \uC5EC\uBD80\uB97C \uBA3C\uC800 \uD655\uC778\uD558\uC138\uC694.\n", "./locales/ko/hunts.yaml": "title: \uC0AC\uB0E5 \uAE30\uB85D\nhelp: \uC11C\uBC84\uAC00 \uC815\uC0B0\uD55C \uBCF8\uC778\uC758 \uACF5\uB3D9 \uCC98\uCE58 \uAE30\uB85D\uC785\uB2C8\uB2E4. \uC6D0\uC7A5 \uB3C4\uC785 \uC774\uC804 \uAE30\uB85D\uC740 \uD3EC\uD568\uB418\uC9C0 \uC54A\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC774\uC804 \uC11C\uBC84 \uC751\uB2F5\uC740 \uC774\uB984 \uB300\uC2E0 \uC2DD\uBCC4\uC790\uB85C \uD45C\uC2DC\uB420 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\nrefresh: \uCC98\uC74C\uBD80\uD130 \uC0C8\uB85C\uACE0\uCE68\nloading: \uC0AC\uB0E5 \uAE30\uB85D\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\uC785\uB2C8\uB2E4.\ntotals: \uBAAC\uC2A4\uD130 \uC885\uB958\uBCC4 \uB204\uC801 \uC218\uB7C9\nempty: \uC0AC\uB0E5 \uAE30\uB85D\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\npage: \uD604\uC7AC \uD398\uC774\uC9C0\uC758 \uAE30\uB85D\nemptyPage: \uC774 \uD398\uC774\uC9C0\uC5D0 \uAE30\uB85D\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\nmap: \uB9F5\nresult: \uACB0\uACFC\nbattle: \uC804\uD22C\nnext: \uB2E4\uC74C \uD398\uC774\uC9C0\nsubstituteTitle: FP \uB300\uCCB4 \uC0AC\uB0E5\nsubstituteHelp: \uCCAB \uC0AC\uB0E5\uC744 \uC644\uB8CC\uD55C \uBAAC\uC2A4\uD130\uC758 \uC218\uC9D1\uD488\uC744 FP\uB85C \uC5BB\uC2B5\uB2C8\uB2E4. \uC7AC\uB8CC\uAC00 \uB098\uC624\uC9C0 \uC54A\uC544\uB3C4 FP\uB294 \uC18C\uBE44\uB429\uB2C8\uB2E4.\nrefreshTargets: \uB300\uC0C1 \uC0C8\uB85C\uACE0\uCE68\nprocessing: \uCC98\uB9AC \uC911\uC785\uB2C8\uB2E4.\ninvalidState: \uC804\uD22C\xB7\uC608\uC57D\xB7\uC815\uC0B0\uC744 \uC885\uB8CC\uD558\uACE0 \uD544\uB4DC \uB610\uB294 \uC790\uB9AC\uBE44\uC6C0 \uC0C1\uD0DC\uC5D0\uC11C \uC774\uC6A9\uD558\uC138\uC694.\nfirstRequired: \uD574\uB2F9 \uC885\uC758 \uCCAB \uC0AC\uB0E5 \uC5C5\uC801\uC744 \uBA3C\uC800 \uB2EC\uC131\uD558\uC138\uC694.\nfpRequired: FP\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4. \uD68C\uBCF5 \uD6C4 \uC0C8\uB85C\uACE0\uCE68\uD558\uC138\uC694.\nfpBalance: '\uBCF4\uC720 FP: {amount}'\nfpCost: '\uC18C\uBE44 FP: {amount}'\nexecute: \uB300\uCCB4 \uC0AC\uB0E5 \uC2E4\uD589\nuncertain: \uC774\uC804 \uC694\uCCAD\uC758 \uACB0\uACFC\uB97C \uBA3C\uC800 \uD655\uC778\uD558\uC138\uC694.\nretry: \uAC19\uC740 \uC694\uCCAD \uB2E4\uC2DC \uD655\uC778\ncompleted: '{amount} FP\uB97C \uC18C\uBE44\uD588\uC2B5\uB2C8\uB2E4.'\nemptyDrop: \uC774\uBC88\uC5D0\uB294 \uD68D\uB4DD\uD55C \uC7AC\uB8CC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\npagination: \uC0AC\uB0E5 \uAE30\uB85D \uD398\uC774\uC9C0 \uC774\uB3D9\nprevious: \uC774\uC804 \uD398\uC774\uC9C0\npageNumber: '{page}\uD398\uC774\uC9C0'\ntargetPagination: FP \uB300\uCCB4 \uC0AC\uB0E5 \uB300\uC0C1 \uD398\uC774\uC9C0 \uC774\uB3D9\ntargetPageNumber: '{page} / {total} \uD398\uC774\uC9C0'\n", "./locales/ko/journal.yaml": "title: \uBA54\uC778 \uC758\uB8B0 \uAE30\uB85D\nhelp: \uC218\uB839\uD55C \uC758\uB8B0\uC640 \uC644\uB8CC \uAE30\uB85D\uC785\uB2C8\uB2E4. \uC7AC\uB8CC \uC218\uB7C9\uC740 \uB9C8\uC9C0\uB9C9 \uC870\uD68C \uC2DC\uC810 \uAE30\uC900\uC785\uB2C8\uB2E4.\nrefresh: \uC0C8\uB85C\uACE0\uCE68\nloading: \uC758\uB8B0 \uAE30\uB85D\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\uC785\uB2C8\uB2E4.\nempty: \uC544\uC9C1 \uC218\uB839\uD55C \uBA54\uC778 \uC758\uB8B0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\naccepted: \uC9C4\uD589 \uC911\ncompleted: \uC644\uB8CC\nreceiver: '\uC804\uB2EC NPC: {name}'\nmaterial: '{name} \xB7 \uD604\uC7AC {owned} / \uD544\uC694 {required}'\nreward: '\uC644\uB8CC \uBCF4\uC0C1: {amount}P'\npaid: '\uC9C0\uAE09\uB41C \uBCF4\uC0C1: {amount}P'\nstartedAt: '\uC218\uB839: {time}'\nfinishedAt: '\uC644\uB8CC: {time}'\nmaterialsReady: \uC7AC\uB8CC\uAC00 \uC900\uBE44\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC804\uB2EC \uC2DC NPC \uC704\uCE58\uC640 \uC2DC\uBBFC\uAD8C \uB4F1 \uC774\uC6A9 \uC870\uAC74\uC744 \uB2E4\uC2DC \uD655\uC778\uD569\uB2C8\uB2E4.\n\ncapacity: '\uC218\uB839 \uC911 {count} / {limit}\uAC1C'\ncapacityHelp: \uBA54\uC778\xB7\uC2DC\uC98C\xB7\uB79C\uB364 \uC758\uB8B0\uB97C \uD569\uC0B0\uD569\uB2C8\uB2E4. \uC644\uB8CC\uD55C \uC758\uB8B0\uB294 \uD55C\uB3C4\uC5D0\uC11C \uC81C\uC678\uB429\uB2C8\uB2E4.\ncapacityFull: \uC218\uB839 \uD55C\uB3C4\uC5D0 \uB3C4\uB2EC\uD588\uC2B5\uB2C8\uB2E4. \uC9C4\uD589 \uC911\uC778 \uC758\uB8B0\uB97C \uC644\uB8CC\uD558\uBA74 \uC0C8 \uC758\uB8B0\uB97C \uBC1B\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\n\nshowDestination: \uC804\uB2EC \uB3C4\uC2DC \uBCF4\uAE30\ndestinationUnavailable: \uC804\uB2EC \uB3C4\uC2DC\uB294 \uD604\uC7AC \uC6D4\uB4DC\uB9F5\uC5D0 \uACF5\uAC1C\uB418\uC5B4 \uC788\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\n\nreturnToJournal: \uC758\uB8B0 \uAE30\uB85D\uC73C\uB85C \uB3CC\uC544\uAC00\uAE30\n", "./locales/ko/loans.yaml": 'title: \uB300\uC5EC \uD30C\uD2F0\uC6D0\nhelp: \uB300\uC5EC \uC2DC\uC810\uC758 \uBCF5\uC0AC\uBCF8\uC785\uB2C8\uB2E4. \uB300\uC5EC\uB294 7\uC77C\uAC04 \uC720\uC9C0\uB418\uBA70 \uC6D0\uBCF8 \uCE90\uB9AD\uD130\uC758 FP\uB294 \uC18C\uBAA8\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\nrefresh: \uC0C8\uB85C\uACE0\uCE68\nloading: \uB300\uC5EC \uD30C\uD2F0\uC6D0\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\u2026\nempty: \uB300\uC5EC \uC911\uC778 \uD30C\uD2F0\uC6D0\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.\nhealth: "HP {current} / {maximum}"\ninbattle: \uC804\uD22C \uCC38\uAC00 \uC911\navailable: \uB300\uC5EC \uC720\uC9C0 \uC911\nremaining: "\uB0A8\uC740 \uB300\uC5EC \uAE30\uAC04 {hours}\uC2DC\uAC04 {minutes}\uBD84"\nexpires: "\uB300\uC5EC \uC885\uB8CC: {time}"\nexpiredbattle: \uB300\uC5EC \uB9CC\uB8CC \xB7 \uC9C4\uD589 \uC911\uC778 \uC804\uD22C\uC640 \uC815\uC0B0\uC740 \uC720\uC9C0\uB429\uB2C8\uB2E4.\nexpired: \uB300\uC5EC \uC885\uB8CC \xB7 \uC0C8\uB85C\uACE0\uCE68\uD558\uBA74 \uBAA9\uB85D\uC5D0\uC11C \uC81C\uC678\uB429\uB2C8\uB2E4.\nmore: \uB354 \uBCF4\uAE30\nended: \uB300\uC5EC \uC885\uB8CC\nrecoveryPending: "\uC804\uD22C\uBD88\uB2A5 \uD68C\uBCF5 \uB300\uAE30 \xB7 \uCD5C\uB300 HP 50% \uC774\uC0C1 \uD68C\uBCF5 \uC804 \uC774\uB3D9 \uBD88\uAC00"\ncpEligible: CP \uD3B8\uC131 \uAE30\uC900 \uCDA9\uC871\ncpOutOfRange: CP \uD3B8\uC131 \uBC94\uC704 \uCD08\uACFC \xB7 \uC0C8 \uC804\uD22C \uD3B8\uC131 \uBD88\uAC00\ncpMigrationRequired: \uB300\uC5EC \uC2DC\uC810 CP \uAE30\uB85D \uC774\uAD00 \uD544\uC694 \xB7 \uC0C8 \uC804\uD22C \uD3B8\uC131 \uBD88\uAC00\ncpUnknown: CP \uD3B8\uC131 \uC815\uBCF4 \uBBF8\uC81C\uACF5\ncpHelp: \uC870\uD68C \uC2DC\uC810\uC758 \uD30C\uD2F0\uC7A5 \uB204\uC801 CP\uC640 \uBE44\uAD50\uD55C \uACB0\uACFC\uC785\uB2C8\uB2E4. \uC2E4\uC81C \uD3B8\uC131 \uC2DC CP\xB7\uAE30\uAC04\xB7HP\xB7\uC804\uD22C \uCC38\uAC00 \uC0C1\uD0DC\uB97C \uB2E4\uC2DC \uD655\uC778\uD569\uB2C8\uB2E4.\n', "./locales/ko/missions.yaml": 'title: "\uC815\uC81C \uC784\uBB34 \uAE30\uB85D"\nrecord: "\uC815\uC81C \uC784\uBB34"\nnoRefund: "\uCDE8\uC18C\uD558\uBA74 \uB2F4\uBCF4\uAE08\uC740 \uBC18\uD658\uB418\uC9C0 \uC54A\uC73C\uBA70 \uC644\uB8CC \uBCF4\uC218\uB3C4 \uC9C0\uAE09\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4. \uC704\uD0C1 \uBB3C\uD488\uC740 \uC790\uB3D9 \uD68C\uC218\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\nrefresh: "\uC0C8\uB85C\uACE0\uCE68"\nloading: "\uC784\uBB34 \uCC98\uB9AC \uC911\uC785\uB2C8\uB2E4."\nchanged: "\uCE90\uB9AD\uD130 \uC0C1\uD0DC\uAC00 \uBC14\uB00C\uC5C8\uC2B5\uB2C8\uB2E4. \uC0C8\uB85C\uACE0\uCE68 \uD6C4 \uB2E4\uC2DC \uC120\uD0DD\uD558\uC138\uC694."\nuncertain: "\uCC98\uB9AC \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC694\uCCAD\uC744 \uC7AC\uC2DC\uB3C4\uD558\uC138\uC694."\nretry: "\uAC19\uC740 \uCDE8\uC18C \uC694\uCCAD \uC7AC\uC2DC\uB3C4"\nempty: "\uC815\uC81C \uC784\uBB34 \uAE30\uB85D\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."\nstatusActive: "\uC9C4\uD589 \uC911"\nstatusCancelled: "\uCDE8\uC18C"\nstatusCompleted: "\uC644\uB8CC"\noutput: "\uACB0\uACFC: {item} ({grade}) \xD7 {count}"\nprocessing: "\uC704\uD0C1 \uC218\uB7C9 {count} \xB7 \uC815\uC81C \uC2DC\uAC04 {seconds}\uCD08"\npayment: "\uB2F4\uBCF4 {deposit}P \xB7 \uC815\uC81C\uBE44 {cost}P \xB7 \uC644\uB8CC \uBCF4\uC218 {reward}P"\ncancel: "\uC784\uBB34 \uCDE8\uC18C"\nnext: "\uB2E4\uC74C \uAE30\uB85D"\nconfirmTitle: "\uC815\uC81C \uC784\uBB34 \uCDE8\uC18C \uD655\uC778"\nconfirm: "\uBB34\uD658\uBD88 \uCDE8\uC18C \uD655\uC815"\nkeep: "\uC784\uBB34 \uC720\uC9C0"\ncancelled: "\uC784\uBB34\uAC00 \uCDE8\uC18C\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC0C8\uB85C\uACE0\uCE68\uC73C\uB85C \uAE30\uB85D\uC744 \uD655\uC778\uD558\uC138\uC694."\ninvalidReceipt: "\uCDE8\uC18C \uC751\uB2F5\uC774 \uC694\uCCAD\uACFC \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\nlow: "\uD558\uAE09"\nmedium: "\uC911\uAE09"\nhigh: "\uC0C1\uAE09"\ndestination: "\uC815\uC81C \uB3C4\uC2DC: {city} \xB7 \uC804\uB2EC: {receiverCity} / {npc}"\nacceptedAt: "\uC218\uB77D \uC2DC\uAC01: {time}"\n', "./locales/ko/network.yaml": "protocol: \uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uD504\uB85C\uD1A0\uCF5C\uC785\uB2C8\uB2E4.\nstateRequired: \uC0C1\uD0DC\uB97C \uBA3C\uC800 \uBD88\uB7EC\uC640\uC57C \uD569\uB2C8\uB2E4.\nconnected: \uC2E4\uC2DC\uAC04 \uC5F0\uACB0\uB428\ninvalidMessage: \uC11C\uBC84 \uBA54\uC2DC\uC9C0\uB97C \uC77D\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.\nreconnecting: \uC5F0\uACB0 \uBCF5\uAD6C \uC911 \xB7 \uC785\uB825 \uC7A0\uAE08\ntransitioning: \uC138\uC158 \uC804\uD658 \uD655\uC778 \uC911 \xB7 \uC7A0\uC2DC \uAE30\uB2E4\uB824 \uC8FC\uC138\uC694.\ntransitionDelayed: \uC138\uC158 \uC804\uD658\uC774 \uC9C0\uC5F0\uB418\uACE0 \uC788\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uB85C\uADF8\uC778\uD574 \uC0C1\uD0DC\uB97C \uD655\uC778\uD558\uC138\uC694.\nchatVerificationExpired: \uAD11\uACE0 \uAC80\uC99D \uB610\uB294 \uCC44\uD305 \uC811\uC18D\uC774 \uB9CC\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\nsessionChanged: \uC138\uC158\uC774 \uBCC0\uACBD\uB418\uC5B4 \uC774\uC804 \uC694\uCCAD\uC758 \uCC98\uB9AC\uB97C \uC911\uB2E8\uD588\uC2B5\uB2C8\uB2E4.\nrequestTimeout: \uC751\uB2F5 \uB300\uAE30 \uC2DC\uAC04\uC774 \uCD08\uACFC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uC11C\uBC84 \uCC98\uB9AC \uC5EC\uBD80\uB294 \uC544\uC9C1 \uD655\uC778\uB418\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4. \uC5F0\uACB0\uC744 \uBCF5\uAD6C\uD574 \uCD5C\uC2E0 \uC0C1\uD0DC\uB97C \uD655\uC778\uD558\uC138\uC694.\n", "./locales/ko/npc.yaml": "talk: '\uB300\uD654: {name}'\ntitle: NPC \uC758\uB8B0\npending: \uC758\uB8B0 \uC815\uBCF4\uB97C \uD655\uC778\uD558\uB294 \uC911\uC785\uB2C8\uB2E4.\nreload: \uC0C8\uB85C\uACE0\uCE68\uD558\uC5EC \uD604\uC7AC \uC758\uB8B0 \uC0C1\uD0DC\uB97C \uD655\uC778\uD558\uC138\uC694.\ncapacity: '\uBBF8\uC644\uB8CC \uC758\uB8B0 {count} / {max} \xB7 \uBA54\uC778\xB7\uC2DC\uC98C\xB7\uB79C\uB364 \uD569\uC0B0'\nempty: \uC774 NPC\uC5D0\uAC8C \uC9C4\uD589\uD560 \uBA54\uC778 \uC758\uB8B0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\navailable: \uC218\uB839 \uAC00\uB2A5\nlocked: \uC870\uAC74 \uBBF8\uCDA9\uC871\naccepted: \uC9C4\uD589 \uC911\ncompleted: \uC644\uB8CC\naccept: \uC758\uB8B0 \uC218\uB839\ncomplete: \uC804\uB2EC \uB0B4\uC6A9 \uD655\uC778\ngiverrequired: \uC218\uB839 \uB2F4\uB2F9 NPC\uB97C \uBC29\uBB38\uD558\uC138\uC694.\nreceiverrequired: \uC804\uB2EC \uB2F4\uB2F9 NPC\uB97C \uBC29\uBB38\uD558\uC138\uC694.\nprerequisiterequired: \uC120\uD589 \uC758\uB8B0\uB97C \uBA3C\uC800 \uC644\uB8CC\uD558\uC138\uC694.\nquestlimitreached: \uC218\uB839 \uD55C\uB3C4\uC5D0 \uB3C4\uB2EC\uD588\uC2B5\uB2C8\uB2E4. \uC9C4\uD589 \uC911\uC778 \uC758\uB8B0\uB97C \uC644\uB8CC\uD558\uC138\uC694.\nmaterialsrequired: \uC804\uB2EC\uD560 \uC7AC\uB8CC\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4.\ncitizenshiprequired: \uC774 \uB3C4\uC2DC\uC758 \uC720\uD6A8\uD55C \uC2DC\uBBFC\uAD8C\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uD604\uC9C0 \uBAA8\uD5D8\uAC00 \uAE38\uB4DC\uC5D0\uC11C \uBC1C\uAE09\uBC1B\uC73C\uC138\uC694. \uC2DC\uBBFC\uAD8C\uC774 \uC5C6\uC5B4\uB3C4 \uAE38\uB4DC\uC5D0 \uC7AC\uB8CC\uB97C \uD314\uC544 \uBC1C\uAE09 \uBE44\uC6A9\uC744 \uB9C8\uB828\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.\ndeliveryReview: \uC804\uB2EC \uB0B4\uC6A9 \uD655\uC778\ndeliveryCharacter: '\uC120\uD0DD\uD55C \uCE90\uB9AD\uD130: {name}'\ndeliveryMaterial: '{name} {quantity}\uAC1C \uCC28\uAC10'\ndeliveryConfirm: \uC804\uB2EC\uD558\uAE30\ndeliveryCancel: \uB3CC\uC544\uAC00\uAE30\ndestination: '\uC804\uB2EC\uCC98: {city} \xB7 {name}'\ndestinationCitizenship: '\uC644\uB8CC\uD558\uB824\uBA74 {city}\uC758 \uC720\uD6A8\uD55C \uC2DC\uBBFC\uAD8C\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uD604\uC9C0 \uBAA8\uD5D8\uAC00 \uAE38\uB4DC\uC5D0\uC11C \uC2DC\uBBFC\uAD8C\uC744 \uBC1C\uAE09\uBC1B\uC744 \uC218 \uC788\uC73C\uBA70, \uC2DC\uBBFC\uAD8C\uC774 \uC5C6\uC5B4\uB3C4 \uC7AC\uB8CC\uB97C \uD314\uC544 \uBC1C\uAE09 \uBE44\uC6A9\uC744 \uB9C8\uB828\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.'\n", "./locales/ko/parcels.yaml": 'title: \uC6B0\uD3B8\xB7\uC18C\uD3EC\nhelp: \uACC4\uC815 \uBCF4\uAD00\uD568\uC5D0\uC11C \uC18C\uD3EC\uC758 \uCCA8\uBD80\uBB3C\uC744 \uC218\uB839\uD569\uB2C8\uB2E4. \uB9CC\uB8CC\uB41C \uC18C\uD3EC\uB294 \uD3D0\uAE30\uB429\uB2C8\uB2E4.\nrefresh: \uC18C\uD3EC \uBAA9\uB85D \uC0C8\uB85C\uACE0\uCE68\nempty: \uC218\uB839 \uAC00\uB2A5\uD55C \uC18C\uD3EC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.\nclaim: \uC774 \uC18C\uD3EC \uC218\uB839\nnext: \uB2E4\uC74C \uBAA9\uB85D\nretry: \uC218\uB839 \uACB0\uACFC \uB2E4\uC2DC \uD655\uC778\nuncertain: \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uC18C\uD3EC\uC758 \uC218\uB839 \uACB0\uACFC\uB97C \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\npending: \uC18C\uD3EC \uC694\uCCAD \uCC98\uB9AC \uC911\u2026\nreceived: \uC18C\uD3EC \uCCA8\uBD80\uBB3C\uC744 \uC218\uB839\uD588\uC2B5\uB2C8\uB2E4.\nmoney: "{amount}P"\ncostume: "\uCF54\uC2A4\uD2AC {name}"\nitem: "{name} \xD7 {quantity}"\nexpires: "\uB9CC\uB8CC: {time}"\nexpired: \uBCF4\uAD00\uAE30\uAC04\uC774 \uB05D\uB0AC\uC2B5\uB2C8\uB2E4. \uBAA9\uB85D\uC744 \uC0C8\uB85C\uACE0\uCE68\uD558\uC138\uC694.\narrived: "\uC18C\uD3EC {count}\uAC1C\uAC00 \uB3C4\uCC29\uD588\uC2B5\uB2C8\uB2E4. \uACC4\uC815 \uBCF4\uAD00\uD568\uC5D0\uC11C \uC218\uB839\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nnoticeFailed: \uC18C\uD3EC \uB3C4\uCC29 \uC5EC\uBD80\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC7A0\uC2DC \uD6C4 \uB2E4\uC2DC \uD655\uC778\uD569\uB2C8\uB2E4.\n\npagination: \uC18C\uD3EC \uD398\uC774\uC9C0 \uC774\uB3D9\nprevious: \uC774\uC804 \uD398\uC774\uC9C0\npage: "{page}\uD398\uC774\uC9C0"\n', "./locales/ko/rewards.yaml": 'title: "\uACC4\uC815 \uBCF4\uAD00\uD568"\nhelp: "\uC2DC\uC2A4\uD15C \uC18C\uD3EC\uC640 \uB300\uC5EC \uBCF4\uC0C1\uC744 \uC5B4\uB514\uC11C\uB098 \uD655\uC778\uD558\uACE0 \uC218\uB839\uD569\uB2C8\uB2E4. \uC18C\uD3EC\uB294 \uBC1C\uC1A1 \uC2DC \uC815\uD55C \uAE30\uD55C, \uB300\uC5EC \uBCF4\uC0C1\uC740 7\uC77C \uB3D9\uC548 \uBCF4\uAD00\uD569\uB2C8\uB2E4."\nrefresh: "\uC0C8\uB85C\uACE0\uCE68"\nloading: "\uBCF4\uAD00\uB41C \uBCF4\uC0C1\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\u2026"\nempty: "\uC218\uB839\uD560 \uBCF4\uC0C1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."\nremaining: "\uB0A8\uC740 \uBCF4\uAD00 \uAE30\uAC04 {hours}\uC2DC\uAC04 {minutes}\uBD84"\nexpires: "\uC218\uB839 \uAE30\uD55C: {time}"\nexpired: "\uBCF4\uAD00 \uAE30\uAC04 \uB9CC\uB8CC \xB7 \uC218\uB839 \uBD88\uAC00"\nclaim: "\uC218\uB839"\nclaiming: "\uC218\uB839 \uC911\u2026"\nclaimed: "\uBCF4\uC0C1\uC744 \uAC00\uBC29\uC73C\uB85C \uC218\uB839\uD588\uC2B5\uB2C8\uB2E4."\nmore: "\uB354 \uBCF4\uAE30"\nclaimAll: "\uB300\uC5EC \uBCF4\uC0C1 \uBAA8\uB450 \uC218\uB839"\nclaimAllHelp: "\uC544\uC9C1 \uD3BC\uCE58\uC9C0 \uC54A\uC740 \uD398\uC774\uC9C0\uAE4C\uC9C0 \uC720\uD6A8\uD55C \uB300\uC5EC \uBCF4\uC0C1\uC744 \uBAA8\uB450 \uD569\uC0B0\uD574 \uC218\uB839\uD569\uB2C8\uB2E4."\nclaimSummary: "\uBCF4\uC0C1 {count}\uAC74 \xB7 \uBB3C\uD488 \uCD1D {quantity}\uAC1C\uB97C \uC218\uB839\uD588\uC2B5\uB2C8\uB2E4."\nnothingClaimed: "\uD604\uC7AC \uC218\uB839 \uAC00\uB2A5\uD55C \uBCF4\uC0C1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uC774\uBBF8 \uC218\uB839\uD588\uAC70\uB098 \uBCF4\uAD00 \uAE30\uD55C\uC774 \uC9C0\uB0AC\uC744 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\n\nloanRewards: "\uB300\uC5EC \uBCF4\uC0C1"\n\npagination: "\uB300\uC5EC \uBCF4\uC0C1 \uD398\uC774\uC9C0 \uC774\uB3D9"\nprevious: "\uC774\uC804 \uD398\uC774\uC9C0"\nnext: "\uB2E4\uC74C \uD398\uC774\uC9C0"\npage: "{page}\uD398\uC774\uC9C0"\n', "./locales/ko/sponsor.yaml": "region: \uC2A4\uD3F0\uC11C \uAD11\uACE0 \uD655\uC778\ndefaultAd: \uAE30\uBCF8 \uAD11\uACE0\nwelcome: \uC2AC\uB77C\uC784\uC5D0 \uC624\uC2E0\uAC78 \uD658\uC601\uD569\uB2C8\uB2E4.\nplayback: \uC2A4\uD3F0\uC11C \uAD11\uACE0 \uC7AC\uC0DD\nretry: \uB2E4\uC2DC \uD655\uC778\nlogout: \uB85C\uADF8\uC544\uC6C3\ninvalidAttempt: \uAD11\uACE0 \uC785\uC7A5 \uACC4\uC57D\uC774 \uC62C\uBC14\uB974\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\n", "./locales/ko/terms.yaml": 'title: "\uC0AC\uC6A9\uC57D\uAD00"\nbackToMenu: "\uBA54\uB274\uB85C \uB3CC\uC544\uAC00\uAE30"\npendingNotice: "\uC2DC\uD589 \uC804 \uC548\uB0B4: \uC544\uB798\uB294 \uC774\uC0C1 \uC2E0\uACE0, \uC0AC\uAC74\uAE30\uB85D \uBCF4\uAD00 \uBC0F \uAC8C\uC784 \uB370\uC774\uD130 \uC190\uC2E4\uC5D0 \uAD00\uD55C \uC870\uD56D\uC785\uB2C8\uB2E4. \uC0AC\uAC74\uAE30\uB85D \uC11C\uBE44\uC2A4\uC640 \uC2E0\uACE0 \uAE30\uB2A5\uC740 \uC544\uC9C1 \uC81C\uACF5\uB418\uC9C0 \uC54A\uC73C\uBA70, \uC801\uC6A9 \uC2DC \uBCC4\uB3C4\uB85C \uC548\uB0B4\uD569\uB2C8\uB2E4."\nreportHeading: "\uC774\uC0C1 \uC2E0\uACE0 \uAE30\uD55C"\nreportPolicy: "\uC11C\uBE44\uC2A4 \uC774\uC6A9 \uC911 \uD589\uB3D9 \uACB0\uACFC, \uC544\uC774\uD15C, \uC7AC\uD654 \uB4F1\uC5D0 \uC774\uC0C1\uC744 \uD655\uC778\uD55C \uACBD\uC6B0, \uC774\uC0C1\uC744 \uD655\uC778\uD55C \uC2DC\uC810\uBD80\uD130 1\uC8FC\uC77C \uC774\uB0B4\uC5D0 \uC2E0\uACE0\uD574 \uC8FC\uC154\uC57C \uAE30\uB85D\uC744 \uBC14\uD0D5\uC73C\uB85C \uD655\uC778 \uBC0F \uB3C4\uC6C0\uC744 \uB4DC\uB9B4 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nreportDetails: "\uC2E0\uACE0 \uC2DC \uBAA8\uD5D8\uAC00 \uC815\uBCF4, \uC774\uC0C1\uC744 \uD655\uC778\uD55C \uC2DC\uAC01, \uCD94\uC815 \uBC1C\uC0DD \uC2DC\uAC01\uACFC \uAD6C\uCCB4\uC801\uC778 \uB0B4\uC6A9\uC744 \uD568\uAED8 \uC54C\uB824 \uC8FC\uC138\uC694."\nretentionHeading: "\uC0AC\uAC74\uAE30\uB85D \uBCF4\uAD00"\nretentionPolicy: "\uC0AC\uC6A9\uC790 \uD589\uB3D9\uACFC \uACB0\uACFC\uC5D0 \uAD00\uD55C \uC0AC\uAC74\uAE30\uB85D\uC740 \uC0AC\uAC74 \uBC1C\uC0DD \uC2DC\uC810\uBD80\uD130 \uCD5C\uB300 14\uC77C\uAC04 \uBCF4\uAD00\uD55C \uB4A4 \uC0AD\uC81C\uD569\uB2C8\uB2E4."\nsupportLimits: "\uAE30\uD55C \uB0B4\uC5D0 \uC2E0\uACE0\uD558\uB354\uB77C\uB3C4 \uBC1C\uC0DD \uD6C4 \uC2DC\uAC04\uC774 \uC9C0\uB098 \uAE30\uB85D\uC774 \uC774\uBBF8 \uC0AD\uC81C\uB418\uC5C8\uAC70\uB098 \uD655\uC778 \uC790\uB8CC\uAC00 \uBD80\uC871\uD55C \uACBD\uC6B0\uC5D0\uB294 \uC870\uC0AC\uC640 \uC9C0\uC6D0\uC774 \uC81C\uD55C\uB420 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC2E0\uACE0 \uC811\uC218\uB85C \uAE30\uB85D \uBCF4\uAD00 \uAE30\uAC04\uC774 \uC5F0\uC7A5\uB418\uC9C0 \uC54A\uC73C\uBA70, \uC2E0\uACE0 \uC811\uC218 \uC790\uCCB4\uAC00 \uBCF5\uAD6C \uB610\uB294 \uBCF4\uC0C1\uC744 \uBCF4\uC7A5\uD558\uC9C0\uB294 \uC54A\uC2B5\uB2C8\uB2E4."\ndataLossHeading: "\uC7AC\uD574 \uB4F1\uC5D0 \uB530\uB978 \uAC8C\uC784 \uB370\uC774\uD130 \uC190\uC2E4"\ndataLossPolicy: "\uCC9C\uC7AC\uC9C0\uBCC0 \uB4F1 \uC11C\uBE44\uC2A4 \uC6B4\uC601\uC790\uAC00 \uD569\uB9AC\uC801\uC73C\uB85C \uC608\uBC29\uD558\uAC70\uB098 \uB300\uC751\uD558\uAE30 \uC5B4\uB824\uC6B4 \uC0C1\uD669\uC5D0\uC11C\uB294 \uAC8C\uC784 \uB370\uC774\uD130\uAC00 \uC190\uC2E4\uB420 \uC218 \uC788\uC73C\uBA70, \uC774\uB7EC\uD55C \uC0C1\uD669\uC5D0\uC11C \uB370\uC774\uD130 \uC190\uC2E4 \uBC29\uC9C0\uB098 \uC190\uC2E4\uB41C \uB370\uC774\uD130\uC758 \uBCF5\uAD6C\uB97C \uBCF4\uC7A5\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4."\noperationHeading: "\uBB34\uB8CC \uC11C\uBE44\uC2A4\uC640 \uCE90\uB9AD\uD130 \uC0DD\uC131"\noperationPolicy: "\uAC8C\uC784\uC744 \uBB34\uB8CC\uB85C \uC81C\uACF5\uD558\uAE30 \uC704\uD574 \uC800\uBE44\uC6A9 \uC6B4\uC601 \uC815\uCC45\uC744 \uC801\uC6A9\uD558\uACE0 \uC788\uC73C\uBA70, \uC774\uC6A9\uC790 1\uC778\uB2F9 \uCE90\uB9AD\uD130 1\uAC1C \uC0DD\uC131\uB9CC \uC9C0\uC6D0\uD569\uB2C8\uB2E4."\nconnectionLimitHeading: "\uB3D9\uC2DC \uC811\uC18D\uC790 \uC218 \uC81C\uD55C"\nconnectionLimitPolicy: "\uAC8C\uC784\uC758 \uC548\uC815\uC801\uC778 \uC6B4\uC601\uC744 \uC704\uD574 \uB3D9\uC2DC \uC811\uC18D\uC790 \uC218\uB97C \uC81C\uD55C\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uC811\uC18D \uC815\uC6D0\uC774 \uCC2C \uACBD\uC6B0 \uC2E0\uADDC \uC811\uC18D\uC774 \uC81C\uD55C\uB420 \uC218 \uC788\uC73C\uBA70, \uC5EC\uC720\uAC00 \uC0DD\uAE34 \uB4A4 \uB2E4\uC2DC \uC811\uC18D\uC744 \uC2DC\uB3C4\uD574 \uC8FC\uC138\uC694. \uC811\uC18D \uC0C1\uD55C\uC740 \uC11C\uBE44\uC2A4 \uC6B4\uC601 \uC0C1\uD669\uC5D0 \uB530\uB77C \uC870\uC815\uB420 \uC218 \uC788\uC2B5\uB2C8\uB2E4."\nseasonLoginHeading: "\uC2DC\uC98C \uC77C\uC77C \uB85C\uADF8\uC778 \uBCF4\uC0C1"\nseasonLoginPolicy: "\uC2DC\uC98C\uC774 \uC2DC\uC791\uB418\uBA74 \uC2DC\uC98C \uC9C4\uD589 \uAE30\uAC04 \uC911 \uD55C\uAD6D \uC2DC\uAC04 \uAE30\uC900 \uD558\uB8E8 \uCCAB \uB85C\uADF8\uC778\uC5D0 \uC2DC\uC98C\uC5C5\uC801 \uBCF4\uC0C1\uC73C\uB85C CP 1\uACFC SP 1\uC744 \uBC1B\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uB0A0 \uC5EC\uB7EC \uBC88 \uB85C\uADF8\uC778\uD574\uB3C4 \uCD94\uAC00 \uC9C0\uAE09\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."\ncurrentSeason: "\uD604\uC7AC \uC2DC\uC98C\uC740 \uC2DC\uC98C 0 \xB7 \uD14C\uC2A4\uD2B8\uC2DC\uC98C\uC774\uBA70, \uB3D9\uC77C\uD55C \uC77C\uC77C \uB85C\uADF8\uC778 \uBCF4\uC0C1 \uC815\uCC45\uC744 \uC801\uC6A9\uD569\uB2C8\uB2E4."\npartyInactivityHeading: "\uC7A5\uAE30 \uBBF8\uC811\uC18D \uD30C\uD2F0 \uD574\uC0B0"\npartyInactivityPolicy: "\uD30C\uD2F0\uC7A5\uC774 \uC5F0\uC18D 24\uC2DC\uAC04 \uC774\uC0C1 \uBBF8\uC811\uC18D\uD558\uBA74 \uD30C\uD2F0\uAC00 \uC790\uB3D9 \uD574\uC0B0\uB429\uB2C8\uB2E4. \uD574\uB2F9 \uD30C\uD2F0\uC7A5\uC758 \uB300\uC5EC \uACC4\uC57D\uB3C4 \uC870\uAE30 \uC885\uB8CC\uD558\uC5EC \uB2E4\uB978 \uD30C\uD2F0\uAC00 \uCE90\uB9AD\uD130\uB97C \uD65C\uC6A9\uD560 \uC218 \uC788\uB3C4\uB85D \uC815\uC6D0\uC744 \uBC18\uD658\uD569\uB2C8\uB2E4. \uC77C\uBC18 \uD30C\uD2F0\uC6D0\uC774\uB098 \uB300\uC5EC \uCE90\uB9AD\uD130 \uC6D0\uBCF8 \uC18C\uC720\uC790\uC758 \uBBF8\uC811\uC18D\uC740 \uD574\uC0B0 \uAE30\uC900\uC774 \uC544\uB2D9\uB2C8\uB2E4. \uC9C4\uD589 \uC911 \uC804\uD22C\uC640 \uBCF4\uC0C1 \uC815\uC0B0\uC740 \uC720\uC9C0\uB429\uB2C8\uB2E4."\npartyDisbandNotice: "\uC774\uC804\uC5D0 \uCC38\uAC00\uD55C \uD30C\uD2F0\uAC00 \uD30C\uD2F0\uC7A5\uC758 \uC5F0\uC18D 24\uC2DC\uAC04 \uBBF8\uC811\uC18D\uC73C\uB85C \uC790\uB3D9 \uD574\uC0B0\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uD574\uB2F9 \uD30C\uD2F0\uC7A5\uC758 \uB300\uC5EC \uC815\uC6D0\uC774 \uBC18\uD658\uB418\uC5C8\uC73C\uBA70, \uC9C4\uD589 \uC911\uC774\uB358 \uC804\uD22C\uC640 \uBCF4\uC0C1 \uC815\uC0B0\uC740 \uC720\uC9C0\uB429\uB2C8\uB2E4."\n', "./locales/ko/timedquests.yaml": `talk: '{name}\uC758 \uC2DC\uC98C\xB7\uB79C\uB364 \uC758\uB8B0'
title: \uC2DC\uC98C\xB7\uB79C\uB364 \uC758\uB8B0 \uAE30\uB85D
empty: \uD45C\uC2DC\uD560 \uAE30\uAC04 \uC758\uB8B0\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uB2F9\uC77C \uB79C\uB364 \uC758\uB8B0\uAC00 \uC5C6\uB294 \uAC83\uC740 \uC815\uC0C1\uC785\uB2C8\uB2E4.
expired: \uAE30\uD55C \uB9CC\uB8CC \xB7 \uBCF4\uC0C1 \uC5C6\uC74C
destination: '\uC804\uB2EC\uCC98: {name}'
acceptBefore: '\uC218\uB839 \uB9C8\uAC10: {time}'
deliverBefore: '\uC804\uB2EC \uB9C8\uAC10: {time}'
randomDeadline: \uC218\uB839 \uD655\uC815 \uD6C4 24\uC2DC\uAC04 \uC774\uB0B4\uC5D0 \uC804\uB2EC\uD574\uC57C \uD569\uB2C8\uB2E4.
seasonDeadline: '\uC218\uB839 \uD6C4 \uC804\uB2EC \uAE30\uD55C: {time}'
next: \uB2E4\uC74C \uAE30\uB85D

pagination: \uAE30\uAC04 \uC758\uB8B0 \uAE30\uB85D \uD398\uC774\uC9C0 \uC774\uB3D9
previous: \uC774\uC804 \uAE30\uB85D
page: "{page}\uD398\uC774\uC9C0"
`, "./locales/ko/wardrobe.yaml": 'title: \uBCF4\uC720 \uCF54\uC2A4\uD2AC\nhelp: \uC18C\uD3EC\uB098 \uC0C1\uC810\uC5D0\uC11C \uD68D\uB4DD\uD55C \uCF54\uC2A4\uD2AC\uC744 \uD655\uC778\uD569\uB2C8\uB2E4. \uCF54\uC2A4\uD2AC\uC740 \uC678\uD615\uC5D0\uB9CC \uC601\uD5A5\uC744 \uC90D\uB2C8\uB2E4.\nrefresh: \uBCF4\uC720 \uCF54\uC2A4\uD2AC \uC870\uD68C\nloading: \uCF54\uC2A4\uD2AC\uC744 \uC870\uD68C\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4\u2026\nempty: \uD68D\uB4DD\uD55C \uCF54\uC2A4\uD2AC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uAE30\uBCF8 \uB514\uC790\uC778\uC744 \uC0AC\uC6A9\uD569\uB2C8\uB2E4.\nreceived: "\uC18C\uD3EC\uB85C \uD68D\uB4DD: {time}"\nequip: \uCC29\uC6A9\ndefault: \uAE30\uBCF8 \uB514\uC790\uC778\uC73C\uB85C \uBCC0\uACBD\nretry: \uCC29\uC6A9 \uACB0\uACFC \uB2E4\uC2DC \uD655\uC778\nuncertain: \uACB0\uACFC\uB97C \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uAC19\uC740 \uCC29\uC6A9 \uC694\uCCAD\uC758 \uACB0\uACFC\uB97C \uB2E4\uC2DC \uD655\uC778\uD558\uC138\uC694.\nequipped: \uCF54\uC2A4\uD2AC\uC744 \uBCC0\uACBD\uD588\uC2B5\uB2C8\uB2E4.\nunavailable: \uC804\uD22C\uB97C \uC885\uB8CC\uD558\uACE0 \uBA54\uB274\uC5D0\uC11C \uCF54\uC2A4\uD2AC\uC744 \uBCC0\uACBD\uD558\uC138\uC694.\ninvalidResponse: \uCC29\uC6A9 \uC751\uB2F5\uC758 \uC694\uCCAD\xB7\uCE90\uB9AD\uD130\xB7\uB514\uC790\uC778 \uC815\uBCF4\uAC00 \uC77C\uCE58\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.\n\npurchased: "\uC0C1\uC810\uC5D0\uC11C \uD68D\uB4DD: {time}"\n', "./locales/ko/workshop.yaml": `title: \uACF5\uBC29 \uC81C\uC791\xB7\uC218\uB9AC
citizenship: \uC0C8 \uACC4\uC57D\uC5D0\uB294 \uC720\uD6A8\uD55C \uD604\uC9C0 \uC2DC\uBBFC\uAD8C\uC774 \uD544\uC694\uD569\uB2C8\uB2E4. \uAE30\uC874 \uACC4\uC57D\uC740 \uC2DC\uBBFC\uAD8C\uC774 \uB9CC\uB8CC\uB418\uC5B4\uB3C4 \uC774 \uACF5\uBC29\uC5D0\uC11C \uC218\uB839\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.
craft: \uC81C\uC791
repair: \uC218\uB9AC
pending: \uACF5\uBC29 \uC815\uBCF4\uB97C \uD655\uC778\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4.
item: \uB300\uC0C1 \uD488\uBAA9
choose: \uD488\uBAA9\uC744 \uC120\uD0DD\uD558\uC138\uC694
noItems: \uC120\uD0DD\uD560 \uC218 \uC788\uB294 \uD488\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4. \uC218\uB9AC\uB294 \uC7A5\uCC29\xB7\uC608\uC57D\uB418\uC9C0 \uC54A\uC740 \uC190\uC0C1 \uC7A5\uBE44\uB9CC \uAC00\uB2A5\uD569\uB2C8\uB2E4.
quote: \uACAC\uC801 \uD655\uC778
price: '\uBE44\uC6A9 {cost} P \xB7 \uC18C\uC694 \uC2DC\uAC04 {seconds}\uCD08'
durability: '\uB0B4\uAD6C\uB3C4 {before}/{beforeMax} \u2192 {after}/{afterMax} (\uCD5C\uB300 \uB0B4\uAD6C\uB3C4 \uAC10\uC18C)'
noCancel: \uACC4\uC57D\uD558\uBA74 \uBE44\uC6A9\xB7\uC7AC\uB8CC\uAC00 \uCC28\uAC10\uB418\uBA70 \uCDE8\uC18C\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4. \uC624\uD504\uB77C\uC778\uC5D0\uB3C4 \uC9C4\uD589\uB418\uACE0 \uC644\uB8CC \uD6C4 \uC774 \uACF5\uBC29\uC5D0\uC11C \uC9C1\uC811 \uC218\uB839\uD569\uB2C8\uB2E4.
confirm: \uBE44\uC6A9 \uD655\uC778 \uD6C4 \uACC4\uC57D
contracts: \uACC4\uC57D \uBAA9\uB85D
empty: \uACC4\uC57D \uB0B4\uC5ED\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.
ready: \uC218\uB839 \uAC00\uB2A5
inprogress: \uC9C4\uD589 \uC911 \xB7 \uC644\uB8CC \uC2DC\uAC01 \uC774\uD6C4 \uC0C8\uB85C\uACE0\uCE68\uD558\uC138\uC694
claimed: \uC218\uB839 \uC644\uB8CC
readyAt: '\uC644\uB8CC \uC2DC\uAC01: {time}'
claim: \uACB0\uACFC\uBB3C \uC218\uB839
next: \uB2E4\uC74C \uACC4\uC57D \uD398\uC774\uC9C0
uncertain: \uC751\uB2F5\uC744 \uD655\uC778\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4. \uC544\uB798 \uACC4\uC57D \uBC84\uD2BC\uC73C\uB85C \uAC19\uC740 \uC694\uCCAD\uC758 \uACB0\uACFC\uB97C \uC7AC\uD655\uC778\uD558\uC138\uC694. \uC911\uBCF5 \uACB0\uC81C\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.

consumable: \uC18C\uBAA8\uD488 \uC81C\uC791

quantity: '\uC81C\uC791 \uC218\uB7C9 (1~1000)'
quantityTime: '{quantity}\uAC1C \xB7 \uAC1C\uB2F9 {seconds}\uCD08 \xB7 \uB2E4\uB978 \uACC4\uC57D\uACFC \uB3D9\uC2DC \uC81C\uC791'
balance: '\uACAC\uC801 \uC2DC\uC810 \uBCF4\uC720 {owned} P \xB7 \uBD80\uC871 {missing} P'
materialBalance: '\uBCF4\uC720 {owned}\uAC1C \xB7 \uBD80\uC871 {missing}\uAC1C'
materialAllocation: "\uBCF4\uC720 {owned} \xB7 \uC0AC\uC6A9 {used} \xB7 \uBD80\uC871 {missing}"
costBreakdown: '\uAE30\uBCF8 \uC81C\uC791\uBE44 {base} P + \uBD80\uC871 \uC7AC\uB8CC \uBE44\uC6A9 {missing} P'
substitutionRule: '\uBCF4\uC720 \uC7AC\uB8CC\uB97C \uBA3C\uC800 \uC0AC\uC6A9\uD569\uB2C8\uB2E4. \uBD80\uC871 \uC218\uB7C9 \xD7 \uAE38\uB4DC \uB9E4\uC785\uAC00\uC758 \uD569\uACC4\uC5D0 1.5\uB97C \uACF1\uD558\uACE0 \uC62C\uB9BC\uD558\uC5EC \uCD94\uAC00 \uACB0\uC81C\uD569\uB2C8\uB2E4. \uBD80\uC871 \uC7AC\uB8CC\uB294 \uAC00\uBC29\uC5D0 \uC9C0\uAE09\uB418\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.'
paidTotal: '\uACC4\uC57D \uB2F9\uC2DC \uACB0\uC81C \uCD1D\uC561: {cost} P'

refiningContracts: \uAC00\uACF5 \uACC4\uC57D\xB7\uC644\uB8CC\uD488 \uC218\uB839
refiningCreate: \uAC00\uACF5 \uC758\uB8B0
refiningBrowse: \uAC00\uACF5 \uD488\uBAA9 \uBCF4\uAE30
refiningUnavailable: \uC774 \uB3C4\uC2DC\uC758 \uAC00\uACF5 \uC11C\uBE44\uC2A4\uB294 \uC544\uC9C1 \uC900\uBE44 \uC911\uC785\uB2C8\uB2E4.
refiningRecipe: \uC81C\uC791\uD560 \uC7AC\uB8CC\xB7\uB4F1\uAE09
refiningQuantity: \uC81C\uC791 \uC218\uB7C9
refiningQuote: \uACAC\uC801 \uD655\uC778
refiningSummary: '\uC218\uC9D1\uD488 {input}\uAC1C \uD544\uC694 (\uBCF4\uC720 {owned}\uAC1C) \xB7 {cost} P \xB7 {seconds}\uCD08'
refiningSubmit: \uBE44\uC6A9\uC744 \uC9C0\uBD88\uD558\uACE0 \uAC00\uACF5 \uC758\uB8B0
refiningCreated: \uAC00\uACF5 \uC758\uB8B0\uAC00 \uC811\uC218\uB418\uC5C8\uC2B5\uB2C8\uB2E4. \uACC4\uC57D \uBAA9\uB85D\uC744 \uC0C8\uB85C\uACE0\uCE68\uD558\uC5EC \uC644\uB8CC \uD6C4 \uC218\uB839\uD558\uC138\uC694.

processingMethodRefining: \uC815\uC81C
processingMethodSmelting: \uC815\uB828
processingKindMaterial: \uC77C\uBC18 \uAC00\uACF5\uC7AC
processingKindEssence: \uC18D\uC131 \uC815\uC218

materialSelection: \uB4F1\uAE09\uBCC4 \uD22C\uC785 \uC7AC\uB8CC
materialOwned: '\uBCF4\uC720 {quantity}\uAC1C'
materialTotal: '\uC120\uD0DD {selected} / \uD544\uC694 {required}'
materialTotalInvalid: \uD544\uC694\uD55C \uCD1D\uC218\uB7C9\uC5D0 \uB9DE\uAC8C \uB4F1\uAE09\uBCC4 \uC218\uB7C9\uC744 \uC120\uD0DD\uD558\uC138\uC694.

material: \uC911\uAC04\uC7AC \uC81C\uC791

batchSelection: \uC911\uAC04\uC7AC \uBC30\uCE58
batchRequired: \uBCF4\uC720\uD55C \uC911\uAC04\uC7AC \uBC30\uCE58\uB97C \uD544\uC694 \uC218\uB7C9\uB9CC\uD07C \uC120\uD0DD\uD558\uC138\uC694. \uBD80\uC871\uBD84\uC740 \uB300\uCCB4 \uAD6C\uB9E4\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.
ownedMaterialRequired: \uBCF4\uC720\uD55C \uC7AC\uB8CC\uB9CC \uC0AC\uC6A9\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4. \uBD80\uC871\uBD84\uC740 \uC7AC\uB8CC\uB97C \uD655\uBCF4\uD55C \uB4A4 \uC81C\uC791\uD558\uC138\uC694.
ownedMaterialInvalid: \uBCF4\uC720\uB7C9 \uC548\uC5D0\uC11C \uD544\uC694\uD55C \uC218\uB7C9\uC744 \uC120\uD0DD\uD558\uC138\uC694. \uC7AC\uB8CC\uAC00 \uBD80\uC871\uD558\uBA74 \uC8FC\uBB38 \uC218\uB7C9\uC744 \uC904\uC774\uAC70\uB098 \uC7AC\uB8CC\uB97C \uD655\uBCF4\uD558\uC138\uC694.
`, "./locales/en/achievements.yaml": 'title: "Achievements"\naway: "Away \xB7 Field movement and encounters are paused."\nreturn: "Return to menu"\nretry: "Retry"\nloading: "Loading achievements\u2026"\nbalance: "Available growth points"\nunsupported: "Unavailable"\nbalanceHelp: "These are your current balances, not the total earned in the history below."\ncategory: "Achievement category"\ngeneral: "General achievements"\nseasonal: "Seasonal achievements"\ncompletedCount: "{done}/{total} completed"\nseason: "Current season: {season}"\nempty: "No achievements registered."\ncomplete: "Completed"\ninProgress: "In progress"\nreward: "Reward"\nskill: "Skill unlock: {name}"\nhistory: "Point award history \xB7 {count} entries"\nhistoryHelp: "Awards for the selected season and category. CP and SP are recorded separately."\nnoHistory: "No awards yet."\nsupplement: "Retroactive supplement"\nawarded: "Achievement award"\nviewSeason: "Season to view"\ncurrentSeason: "Current season"\narchivedHelp: "Previous season records. These rewards are not included in your current balance and will not be awarded again."\npagination: Achievement pages\nhistoryPagination: Award history pages\nprevious: Previous\nnext: Next\npage: "Page {page} of {total}"\n', "./locales/en/app.yaml": `reportRegion: "Battle result"
menu: "Menu"
backToMap: "Back to map"
gameMenu: "Game menu"
characterNavigation: "Character page navigation"
back: "Back"
characterSelectLink: "Character selection"
characterSelect: "Select character"
characterCreate: "Create character"
myCharacter: "My character"
continueAdventure: "Continue your adventure with this character."
characterSettings: "Character settings"
characterLimit: "Character 1 / 1 \xB7 One character is available per account."
noCharacter: "You have no character yet. Create your first adventurer."
createLimit: "You can create one character per account."
creating: "Creating\u2026"
mapMenu: "Map menu"
battleMap: "Battle map"
fieldMap: "Field map"
cameraControls: "Map view controls"
zoomOut: "Zoom out"
zoomIn: "Zoom in"
rotateLeft: "Rotate map 90 degrees left"
rotateRight: "Rotate map 90 degrees right"
resetView: "Reset view"
mapExplore: "Explore map \xB7 Use arrow keys to select a tile"
fieldControls: "Field controls"
reconnectHelp: "Reconnect to restore the view."
connectingHelp: "Connecting to the server. Actions will be available when connected."
preparingMap: "Preparing the map."
processing: "Processing your request."
fieldHelp: "Field help"
fieldControlsHelp: "Click the map or focus it and use the arrow keys to select a tile. Drag to pan and use the wheel or zoom buttons. Rotate 90 degrees with \u21B6\xB7\u21B7 to see behind elevated terrain."
battleLegend: "Blue: movement \xB7 Numbered line: route \xB7 Orange: attack range after arrival"
reserved: "Preparing encounter"
exploring: "Exploring"
selectCell: "Select a tile"
keyboardHelp: "\xB7 Arrow keys to select / Wheel to zoom"
settlementHelp: "Wait for settlement before entering at the starting point."
nearbyHeading: "Nearby exploration and waypoints"
partyHeading: "Explore together"
chat: "Chat"
leaveParty: "Leave party"
disbandParty: "Disband party"
createParty: "Create party"
kick: "Remove"
invite: "Invite"
partyCpOutOfRange: "Cumulative CP must be within 20% of the leader's total"
commandBusy: "Processing command\u2026"
loadingRegion: "Loading location"
loadingFailed: "Loading failed"
loading: "Loading\u2026"
reconnect: "Reconnect"
invitationCount: " \xB7 Invitations: {count}"
partySummary: "Party {count}/4 \xB7 Leader {leader}"
acceptInvitation: "Accept invitation from {name}"
position: "My position {column}, {row} \xB7 {status}"
selectedTile: "Selected {column}, {row}"
selectedBlocked: "Selected {column}, {row} \xB7 Impassable"
resultSummary: "{result} \xB7 Currency +{coins}"
recentBattle: "Last battle"
battleHeading: "{name} \xB7 Round {round}"
battlefield: "Tactical battlefield"
webglReconnect: "Reconnect to restore the WebGL view."
webglUnsupported: "This browser cannot run WebGL."
sessionRelogin: "Sign in again. Your existing battle continues on the server."
loggedOut: "You have signed out."
noRouteError: "No route is available from your current location."
movementFpError: "Insufficient FP to move. Each tile costs 1 FP."

bag: "Bag"
emptyBag: "Your bag is empty."
bagUnavailable: "Bag information is unavailable. Please reconnect."

bagWeight: "Known weight {weight}g / carrying allowance {capacity}g"
bagUnknownWeight: "Weight is not yet defined for {count} items."
itemWeight: "{weight}g each"

fieldHelpSelect: "Select a destination on the map or a nearby shortcut. Move or encounter using the controls above."
fieldHelpEncounter: "Use the controls to approach or encounter. Name colors show aggression; danger requires scouting."
fieldHelpSelection: "Tap a character or monster to select its tile. Tap overlapping images again to cycle through their tiles. Arrow keys also select tiles."
fieldHelpCamera: "Pan \xB7 drag / Zoom \xB7 wheel or \xB1 / Rotate \xB7 \u21B6\u21B7"
fieldHelpReset: "Crosshair \xB7 return to your position and default zoom"
currentCharacter: Current character

bagLoading: "Loading belongings and weight."
bagChanged: "Your bag changed. Please refresh."
bagMaterials: "Materials & consumables"
useHealingItem: "Use {count} \xB7 HP +{amount}"
useMarkerItem: "Use {count} \xB7 Personal marker here for {seconds}s"

worldMap: "World map"
mapTown: "Town"
mapField: "Field"
mapUnknownKind: "Connected map"
worldMapHelp: "Explore the relative layout and connections. Drag to pan and use the buttons or mouse wheel to zoom. Select a map to inspect nearby regions. Travel through waypoints in the field."
worldMapCurrent: "You are here"
worldMapConnections: "Connected regions"
worldMapLoading: "Loading world map\u2026"
worldMapRetry: "Retry"
mapAssetsFailed: "Map assets could not be loaded. Please reconnect."
mapSceneFailed: "The map view could not be created. Please reconnect."

bagSupplies: "Collectibles, materials & consumables"
bagCollection: "Collectible \xB7 unrefined"
bagRefinedMaterial: "Refined material"
refiningGradeLow: "Low grade"
refiningGradeMedium: "Mid grade"
refiningGradeHigh: "High grade"

partyListedMembers: "{count} listed characters"

onlinePartyUnavailable: Online parties are not available. Use adventurer loans and formation at the guild.

townMap: "Town field card"

developerTitle: "Developer tools"
developerInvalid: "Invalid developer API response."
developerConfirm: "Change {asset} from {before} to {after}?"
developerCompleted: "Adjustment completed."
developerSelf: "Local developer tools for your own character."
developerRefresh: "Refresh"
developerBalance: "Adjust assets"
developerAsset: "Asset"
developerOperation: "Operation"
developerAdd: "Add"
developerRemove: "Remove"
developerQuantity: "Quantity (1\u20131,000,000,000)"
developerApply: "Review change"
developerFieldOnly: "Finish battle or encounter preparation and return to field idle state."
developerUncertain: "The outcome is uncertain. Check the original request."
developerRetry: "Check original request"
developerHistory: "Adjustment history"
developerNext: "Next page"

developerItems: "Adjust items"
developerSearch: "Search items"
developerSelectItem: "Select an item"
developerCardQuantity: "Adjust one skill card at a time. Granting does not teach the skill; use it from account storage after meeting its literacy requirement."
developerEquipmentQuantity: "Adjust one equipment instance at a time. Unequip it and finish repairs before removal."
developerInstance: "Equipment instance to remove"
developerEquipmentLocked: "In use: unequip or claim repair first"
developerPermitDuration: "Grant one certificate at a time, valid for seven days from issuance."
developerPermitCity: "City"
developerPermitIssuer: "Issuing guard center"
developerPermitInstance: "Certificate \xB7 city \xB7 expiry \xB7 instance ID"

developerBatchLevel: "Production level to grant"
developerBatchInstance: "Batch to remove \xB7 level \xB7 owned quantity \xB7 ID"

developerCancel: "Cancel"
developerProceed: "Apply adjustment"

developerInvalidQuantity: "Enter a whole quantity from 1 to 1,000,000,000."
developerSelectionRequired: "Select an item and its required level, instance, batch or issuer. Instance items require a quantity of one."
developerInsufficientBalance: "Removal exceeds the owned balance. Reduce the quantity to the available amount."

bagCategory: Bag category
bagCategoryEmpty: No items in this category.
bagSuppliesPagination: Supplies pages
bagPreviousPage: Previous
bagNextPage: Next
bagPageNumber: "Page {page} of {total}"
bagEquipmentPagination: Equipment pages
bagEquipmentPage: "Page {page}"

developerResetTitle: "Reset all character data"
developerResetDescription: "Permanently delete the character, assets, storage, costumes and past season records. Keep the account and password. Sign in again to start before character creation."
developerResetConfirm: "Type RESET test to confirm."
developerResetUncertain: "The reset result is unknown. Check again using the same request."
`, "./locales/en/auth.yaml": 'illustration: A translucent teal slime in a forest flower garden\neyebrow: A new beginning, at your own pace\nheadline: Take your time,\nemphasis: make memories together.\nintro: Wander freely and share your day.\npace: Here, life moves at your pace.\njump: Go to sign in\nsteps: \u25C7 Unhurried steps\ntogether: \u25CE Time together\ndaily: \u25CC Your own adventure\nwelcome: Welcome.\nsubtitle: Start today at your own pace.\nusername: Username\npassword: Password\nlogin: Sign in\nsignupHint: New here? Create an account to get started.\nregister: Create account\nbusy: Please wait a moment\u2026\nrules: Registration requirements\nusernameRule: "Username: lowercase Latin letters and numbers only."\npasswordRule: "Password: use ASCII characters without spaces (maximum 128 characters)."\n\ninputHint: Enter your username and password.\nsigningIn: Signing in\u2026\nregistering: Creating account\u2026\nregistered: Account created. Select Sign in to continue.\nshowPassword: Show password\nhidePassword: Hide password\n\nregisterSubtitle: Choose a username and password for your account.\nbackToLogin: Back to sign in\ninvalidUsername: Use only lowercase letters and digits for your username (up to 40 characters).\ninvalidPassword: Use ASCII characters without spaces for your password (up to 128 characters).\n', "./locales/en/battle.yaml": `healthAlly: 'HP {hp} / {maxHp}'
healthFallen: Fallen
healthHidden: Health unknown \xB7 Monster Lore required
healthLight: Light damage \xB7 Monster Lore \xB7 Two health bands
healthHeavy: Heavy damage \xB7 Monster Lore \xB7 Two health bands
selectedCharacter: Selected character
activeCharacter: Active character
characterAp: Character AP
remainingAp: Remaining AP
apUnknown: AP unavailable
apValue: 'Remaining AP {value}'
apMaximum: 'Remaining AP {value} / {maximum}'
unitDetails: Selected character details
selectUnitHelp: Select a character to view their status here.
ally: Ally
enemy: Enemy
incapacitated: Incapacitated
guarding: Guarding
noGuard: Not guarding
unitStats: 'Attack {attack} \xB7 Defense {defense} \xB7 Speed {speed} \xB7 Move {move} \xB7 Range {range}'
move: "Move"
attack: "Attack"
guard: "Guard"
endTurn: "End turn"
wait: "Wait (time expired)"
surrenderVote: "Flee vote"
cancel: "Cancel"
confirm: "Confirm"
preparing: "Preparing battlefield"
preparingHelp: "The first turn starts when the map, battle chat and all participants are ready."
controls: "Battle controls"
myTurn: "Your turn"
waiting: "Waiting"
participant: "Participant"
moveHint: "Select a blue movement tile to open confirmation."
attackHint: "Select a target, then press Attack beside Clear selection."
endHint: "Confirm in the dialog to end your turn."
actions: "Battle actions"
noTarget: "No attack targets are in range."
confirmSurrender: "Confirm flee vote"
surrender: "Flee"
targetSelection: "Select attack target"
clearSelection: "Clear selection"
noAttackTargets: "No targets can be attacked from this position."
attackCandidates: "Available attack targets"
selected: "Selected"
help: "Battle help"
movementLegend: "Movement range legend"
moveTiles: "Blue tiles \xB7 Reachable"
pathLine: "Numbered line \xB7 Selected route"
arrivalLine: "Orange inner line \xB7 Attack after arrival"
chooseTile: "Select a tile inside the bright blue outline."
endAfterAction: "You have used your action. End the turn without additional guard."
autoGuardHelp: "Give up remaining movement and guard automatically. Basic attack damage received is halved until your next turn."
arrivalHeading: "Attacks after arrival"
moveEndsTurn: "You have used your action. Moving will end your turn."
noArrivalTargets: "No enemies can be attacked after arrival."
moveOnly: "Only movement is confirmed. Choose an attack separately after arrival."
turnCharacters: "Turns and characters"
turnOrder: "Turn order this round"
used: "Used"
once: "Once"
legacyActionHelp: "Move and act in either order \xB7 The turn ends after both are used"
terrainControls: "Terrain and controls"
terrainHelp: "Select tiles to move or target an attack. Drag to pan; use zoom and rotation controls to inspect the terrain."
units: "Battle units"
emptyLog: "No battle actions recorded yet."
endNoGuard: "End the turn without additional guard."
endWithGuard: "Give up remaining movement and end the turn guarding."
seconds: "{seconds}s"
waitFor: "Waiting for {name} to act."
targetCount: "Attack targets \xB7 {count}"
expectedDamage: "Expected damage {damage}"
moveRoute: "Move {count} cells: {path}"
arrivalRange: "Orange inner line: attack range after arrival \xB7 Range {range} cells"
roundStatus: "Round {round} \xB7 Active: {name}"
actionUsage: "Movement: {move} \xB7 Action: {action}"
portrait: "Portrait of {name}"
healthLabel: "{name} health"
unitCount: "Participating units \xB7 {count}"
logCount: "Battle log \xB7 Actions: {count}"
turnNumber: "Turn {turn}"
logMove: "Move {path}"
autoGuard: "Auto guard"
logDamage: " \u2192 {name} ({damage} damage)"
confirmAction: "Confirm {action}"

apExhausted: All AP has been spent. Select End turn to continue to the next turn.
reportTitle: "Battle report"
resultWin: "Victory"
resultLose: "Defeat"
resultTimeout: "Time expired"
resultSurrender: "Fled"
resultPreparationFailed: "Battle preparation failed"
earnedCurrency: "Currency earned"
returnCountdown: "Returning to the map in {seconds}s."
acknowledge: OK
apRules: Movement costs 1 AP per tile \xB7 Basic attack costs 3 AP \xB7 Recover 50% of max AP rounded each turn \xB7 Unused AP carries over
apRecovery: '+{count} AP at the start of your turn'
apPreview: 'Cost {cost} AP \xB7 {remaining} AP after action'

skills: "Skills"
skillSelection: "Select a skill"
noSlottedSkills: "Assign battle skills in character settings."
skillPreviewOnly: "No executable actions. Check unlock levels, battle slots, and equipment requirements."

idleTurnNotice: "No input for 5 seconds. End your turn when you have finished acting."

noLoot: "No loot acquired."

basicAttackSkillHelp: "Basic attack is part of Physical Activity. Select a target and confirm to attack."
selectSkillHelp: "Select a skill to view its description and available actions."
terrainApPreview: "Base {base} AP \xB7 expected {expected} AP \xB7 maximum {max} AP. Terrain costs may reduce AP to zero or below and stop movement before arrival."
terrainMovementStopped: "Route stopped due to insufficient AP"

surrenderConfirmation: "Agree to flee? Each item acquired in this battle has a 50% chance of being lost when fleeing."

moveSummary: "Move {count} tiles \xB7 View the full path on the map and in the confirmation dialog."
attackHelpDetail: "Choose a target on the map or in the list, then press Attack beside Clear selection to open confirmation. Review expected damage before confirming; enemy health information depends on Monster Lore."

plainEndTurn: "End turn \xB7 0 AP"
guardEndTurn: "Guard and end \xB7 1 AP"
turnEndChoice: "Guard and end costs 1 AP. Ending without guarding costs no AP."
guardEndUnavailable: "Guarding requires 1 AP. You can end without guarding at no AP cost."

lostLoot: "Lost while fleeing"
turnEndPrompt: "Choose how to end your turn."
plainEndDetail: "End your turn without guarding."
guardEndDetail: "Guard, then end your turn."
guardEndDisabledDetail: "Not enough AP \xB7 Guarding requires 1 AP."
distributionTitle: "Loot and distribution"
distributionQuantities: "Total {total} / Yours {mine}"
distributionInitiator: "Leader"
distributionSupporter: "Supporter"
distributionDetails: "Individual rolls"
distributionRoll: "Item {sequence} \xB7 Roll {face} \u2192 {name}"
distributionMailbox: "Supporter rewards are held in the character owner's account mailbox."

recoveryPending: Movement is unavailable while recovering from incapacitation. Choose an available action from your position or end the turn.

finishingStrike: Finishing Strike
skillUnavailable: Not enough AP or no valid target within range.
useSkillAction: Use skill

supportExcluded: Party members excluded from this battle
supportExpired: Loan expired
supportCpMismatch: CP eligibility not met
supportMigration: Loan growth record needs updating
supportRecovering: Recovering from incapacitation
supportBusy: In another battle
supportPreview: Expected battle participants
supportRecheck: Eligibility is checked again at encounter time. Exclusion does not remove the formation.
supportPreviewFailed: Could not load participants. Please try again.
supportRefresh: Refresh participants

distributionGuild: "Guild allocation"
distributionGuildStorage: "Materials allocated to guild companions are stored in the guild ledger, not in a personal reward inbox."
dissectionApplied: "Dissection applied \xB7 operator skill level {level}"
dissectionRecoveryHint: "Difficulty varies by monster. Low dissection proficiency may prevent intact material recovery."

expectedHealing: "Expected HP healing {healing}"
expectedDrain: "Self HP healing {healing}"

apRulesFloor: "Move: 1 AP per tile \xB7 Basic attack: 3 AP \xB7 Recover 50% of maximum AP rounded down each turn \xB7 Unused AP carries over"

automaticEnable: Enable automatic battle

automaticDisable: Disable automatic battle

automaticActiveHelp: Automatic battle is active. Disable it before choosing a manual action.

automaticManualHelp: Applies to this battle only. Disconnecting returns you to manual control.

automaticEnabledLog: Automatic battle enabled

automaticDisabledLog: Automatic battle disabled
patternTitle: "Automatic battle pattern"
patternHelp: "The first usable rule is selected from top to bottom. Saved changes apply to new battles and loans. Enable automatic battle during combat to use it."
patternRuleNumber: "Rule {number}"
patternEndRule: "Always \u2192 End turn (required final rule)"
patternCondition: "Condition"
patternConditionAlways: "Always"
patternConditionSelfHp: "Own HP at or below"
patternConditionAllyHp: "Ally HP at or below"
patternHpPercent: "HP threshold (%)"
patternAction: "Action"
patternActionAttack: "Basic attack"
patternActionSkill: "Skill action"
patternActionApproach: "Approach nearest enemy by one tile"
patternActionEndTurn: "End turn"
patternSkillAction: "Skill action to use"
patternMissingSkill: "Unavailable skill \u2014 check slots and level"
patternMoveUp: "Move up"
patternMoveDown: "Move down"
patternRemoveRule: "Remove rule"
patternAddRule: "Add rule"
patternRuleLimit: "A pattern allows up to 10 rules including the final end turn. Remove a rule to add another."
patternInvalidRules: "Enter an integer HP threshold from 1 to 100 and select an available skill action."
patternSave: "Save pattern"
patternReload: "Reload saved rules"
patternDelete: "Delete saved pattern"
patternSaved: "Changes saved."
`, "./locales/en/cards.yaml": "shop: Bookshop skill cards\nstorage: Stored skill cards\npolicy: Purchased cards go to account storage. Using a card consumes it and teaches its skill.\nrefresh: Refresh cards\npending: Checking skill cards.\nliteracy: 'Required literacy to use: {level}'\nrequirement: 'Required literacy {required} \xB7 Current {current}'\nbuy: 'Buy for {price} P'\nowned: In account storage\nlearned: Skill already learned\nindefinite: No expiration\nuse: Use card\nconfirmTitle: Confirm skill card use\nconfirm: 'Consume one {name} and learn its skill at level 0.'\nconfirmUse: Consume and learn\ncancel: Cancel\nempty: No skill cards in storage.\npurchased: The skill card was delivered to account storage.\nused: Card consumed and skill learned.\nuncertain: The result could not be confirmed. Retry the same request.\nretry: Retry same request\n\nfieldRequired: Enter the game and finish any battle or encounter before buying or using skill cards.\nwaitForConnection: Try again once the connection is restored and pending requests have finished.\ninsufficientFunds: You do not have enough P for this purchase.\n", "./locales/en/channels.yaml": "open: Change channel\ntitle: Channels\ncurrent: 'Current channel: {address}'\nhelp: Move to another channel on this map. Your position stays the same and chat reconnects for the new channel.\nrefresh: Refresh list\ncheckState: Check current state\naddress: Destination channel address\naddressHelp: Use a1, aa22, or ba234. Addresses are case-insensitive.\njoinAddress: Join address\njoin: Join\nsameMap: Channels on this map\npopulation: 'Seats {used}/{capacity} \xB7 {online} online'\npopulationHelp: Seats include battle return reservations. Joining may fail if occupancy changes after this list is loaded.\npopulationUnavailable: This server does not provide channel occupancy. Capacity is checked when you join.\nidentifier: 'ID: {id}'\npending: Checking channel information\u2026\nuncertain: The transfer result is unknown. Check your current state before trying another transfer.\ninvalidAddress: Enter letters followed by a number greater than zero. Spaces and symbols are not allowed.\ninvalidList: The channel list has an invalid format. Please refresh it.\nstateRequired: Please check your current channel information again.\nfieldRequired: Finish battle or encounter preparation before changing channels in the field.\nleaveParty: Leave your party before changing channels.\nrecoveryRequired: Recover at least 50% of your maximum HP after being incapacitated before moving.\nfpRequired: FP is negative. Wait for it to recharge before moving.\ndifferentMap: This channel is on another map. Travel there using a waypoint first.\nalreadyHere: You are in this channel.\nclosed: This channel is closed to new arrivals.\nfull: This channel is full. Choose another channel or refresh the list.\nwaitAction: Finish the current movement or loading before changing channels.\npagination: Channel list pages\npreviousPage: Previous\nnextPage: Next\npageNumber: 'Page {page} of {total}'\nempty: No channels on this map are available to display. Refresh the list to check again.\n", "./locales/en/character.yaml": 'ready: Ready for your adventure?\nremaining: "Unspent: {points}"\nlocation: Enter at the starting point of your last map.\npending: Waiting for battle results\nenter: Enter game \u2192\ntitle: You have unspent points\nconfirm: You have {points} remaining. Enter the game?\nallocated: All points allocated. Enter the game?\nback: Back to settings\nproceed: Enter game\nidentity: "My character"\nadventurer: "My adventurer"\ncostume: "Standard adventurer outfit"\ncoins: "PON balance"\ngrowth: "Character growth"\ndirection: "Choose your growth"\navailable: "Available {currency}"\nconnectionRequired: "Check connection"\nbreakdown: "Character point balances"\ngeneralPoints: "General points"\nseasonPoints: "Seasonal points"\nintro: "What kind of adventurer will you become?"\ncurrencies: "Spend CP on attributes and SP on skills. Seasonal CP is spent first on attributes."\ncategory: "Choose a growth category"\nattributes: "Attributes"\nskills: "Skills"\nskillList: "Physical Activity, Literacy and Speaking are granted at character creation. Skills acquired later also appear here."\nnextCost: "{category} upgraded {count} times \xB7 Next cost: {cost} {currency}"\nnoEffect: " \xB7 No effect"\nraiseLabel: "Raise {name} from level {level} to {next}, spending {cost} {currency}"\nraise: "+1 level"\ninsufficient: "Not enough {currency} \xB7 Need {cost}"\nspend: "Spend {cost} {currency}"\nlocked: "You can allocate growth points after the battle or encounter ends."\nsaved: "Upgrades are saved immediately. Attribute upgrades increase the next CP cost; skill upgrades increase only that skill\u2019s next SP cost."\nrulesTitle: "Growth rules"\nrules: "You start with 10 CP and 0 SP, with Literacy, Speaking and Physical Activity at level 1. Attribute upgrades share a CP cost sequence and each skill has its own SP sequence: 1 \u2192 2 \u2192 3 \u2192 4 \u2192 \u2026 \u2192 100 over the first 20 steps, then 110 \u2192 121 \u2192 132 and onward. Granted levels do not increase costs, so the first skill upgrade from level 1 to 2 costs 1 SP. Skills earned through achievements start at level 0. Previously granted levels are preserved. Allocations cannot be undone."\nsummary: "Character settings \xB7 CP {cp} \xB7 SP {sp}"\nportrait: "An adventurer wearing teal clothes and leather boots"\nbodyName: "Body"\nbodyDescription: "The foundation for physical activity"\nintellectName: "Intellect"\nintellectDescription: "The foundation for understanding and judgment"\nspiritName: "Spirit"\nspiritDescription: "The foundation for spiritual activity"\n\nbattleSlots: "Battle skill slots"\nbattleSlotsHelp: "Choose skills for the battle list. Selection order is saved. Level 0 has no effect."\n\nskillUseLocked: "Use locked"\nskillBookSold: "Use is locked because the skillbook was sold. Acquisition and level are preserved."\n\nactionUnlockLevel: "Unlocks at level {level}"\nactionUnlocked: "Unlocked \xB7 requires level {level}"\nactionCostPower: "{ap} AP \xB7 {power}\xD7 attack power"\nactionSwordRequirement: "Requires a battle skill slot and a usable one-handed sword. Use depends on your turn, range, and remaining AP."\ncostumeDetails: "Outfit details"\ncostumeDescription: "The default character design wears a white short-sleeved T-shirt, gray shorts, and white sneakers."\ncostumeAppearanceOnly: "A costume is a complete character design, including the face, hair, body, and clothing. It does not affect attributes or skill performance."\n\nactionHealingPower: "{ap} AP \xB7 Restore spirit \xD7 {power} HP"\nactionMagicPower: "{ap} AP \xB7 (10 + 2 \xD7 spirit) \xD7 {power} power"\nactionGreatswordRequirement: "Requires a battle slot and a usable two-handed sword. Check turn, range, and AP."\nactionGeneralRequirement: "Requires a battle slot. Check turn, target, range, and AP."\nactionRange: "Range {minimum}\u2013{maximum} cells"\nactionFeedingRequirement: "Requires anatomy suited to feeding on the target."\nactionDrainRate: "Restore {percent}% of actual HP damage as self HP."\n\ncostumeLoading: Loading costume details.\ncostumeUnsupported: This design does not match the current preview.\n\ncostumeSponsorUnavailable: The sponsor advertisement could not load. Close and reopen the details to retry.\n\nguildMembership: "Adventurers Guild member"\nguildCertificateIssued: "Adventurers Guild certificate issued"\n', "./locales/en/citizenship.yaml": "title: Citizenship\nunavailable: Citizenship information is unavailable from this server.\nempty: No citizenship has been issued.\nvalid: Valid\nexpired: Expired\npending: Not yet effective\ninitial: Initial grant\npurchase: Purchased\nstarts: Valid from\nexpires: Expires\nchecked: Based on the latest server update\nhelp: Quests and facilities require valid citizenship in that town.\nvalidCount: '{count} valid'\n\npermitTitle: Traveler certificates\npermitUnavailable: Traveler certificate information is unavailable from this server.\npermitEmpty: No traveler certificates owned.\npermitOwner: Owner\npermitIssuer: Issuing guard center\npermitIssued: Issued\n\npermitPurchased: Traveler certificate issued. You can view it in your bag.\npermitPrice: Check traveler certificate fee\npermitQuote: 'Fee {price}P \xB7 Quote expires in {seconds}s'\npermitExpired: Quote expired. Check the fee again.\npermitPurchaseHelp: 'Pay {price}P to receive a traveler certificate valid for seven days from now.'\npermitRetry: Check the same issuance request again\npermitPurchase: Confirm traveler certificate issuance\npermitUncertain: The issuance outcome is unknown. Check again using the same request.\n\nbarterEnable: Pay with materials and coins\nbarterCash: Coin payment (p)\nbarterEmpty: No materials available for payment.\nbarterInvalid: Check the coin amount and quantities, and select at least one material.\nbarterCashValue: 'PON: {cash}P'\nbarterMaterialQuantity: '{name} \xD7 {quantity}'\nbarterNoChange: 'All selected PON and materials will be paid. No change is given.'\nbarterPurchaseHelp: 'Pay the {price}P fee with the confirmed coins and materials. Excess value is not returned.'\nbarterStateChanged: Your inventory state changed. Request a new quote.\n", "./locales/en/city.yaml": "facilities: City facilities\nguild: Adventurers' Guild\nbookshop: Bookshop\ninn: Inn\nworkshop: Smithy and workshop\nmarket: Market\napproach: Walk to entrance\narrived: At the entrance\nsafeTown: The entire city is a safe area\nstaff: 'NPC: {names}'\n", "./locales/en/common.yaml": 'language: Language\nbrand: A new beginning\nconnected: Connected\nconnecting: Connecting\nstart: Your day begins\nrelogin: Sign in again\nlogout: Sign out\nsettings: Character\nachievements: Achievements\nnearby: Nearby\nencounter: Prepare encounter\nparty: Party\nbattleChat: Battle chat\nchannelChat: Channel chat\nexplorer: New adventurer\ncharacterName: Character name\n\nclose: "Close"\n', "./locales/en/cutins.yaml": 'settings: Game settings\nshow: Action Cut-in duration\nhelp: Defaults to 3 seconds and closes automatically after the selected duration. Skipping is unavailable. This setting is saved in this browser.\npresentation: Action Cut-in\nattack: Basic attack\nimageFailed: Failed to load the Action Cut-in image.\nseconds: "{seconds} seconds"\noff: Off\n\nsettingReadFailed: Cut-ins are suspended because the setting could not be read. Restore the default or choose a duration in Game settings.\nsettingWriteFailed: Could not save the cut-in setting. The previous setting is unchanged. Allow browser storage access and try again.\nrestoreDefault: Restore default (3 seconds)\nsettingUnavailable: Setting needs attention\nassetUnavailable: The cut-in appearance is unregistered or damaged. The game will resume when the presentation ends.\n', "./locales/en/directmessages.yaml": "open: 'Direct messages'\nretention: 'Each conversation retains up to 100 messages in both directions for 30 days. Sent means saved on the server, not read by the recipient.'\nnoticeFailed: 'Arrival notices could not be retrieved. They will be checked again shortly.'\nsaved: 'Saved on the server.'\npending: 'The send to {recipient} is unconfirmed. Check the same request again.'\nretry: 'Check original send'\nrecipient: 'Conversation partner'\ncharacterId: 'Character ID'\nselect: 'Select recipient'\nnearby: 'Adventurers on this map'\nconversations: 'Recent conversations'\nblocks: 'Blocked recipients'\nnext: 'Next list page'\nhistory: 'Private message history'\nrefresh: 'Load latest messages'\nblock: 'Block incoming messages'\nunblock: 'Unblock incoming messages'\nself: 'Me'\nempty: 'No retained messages.'\nolder: 'Older message page'\nbody: 'Message (1\u20131000 characters)'\nsend: 'Send'\ninvalidResponse: 'Invalid direct message response.'\nsessionChanged: 'Your login session changed. Open this panel again.'\npendingSend: 'Resolve the pending or unconfirmed send first.'\ninvalidRecipient: 'Select another adventurer by character ID.'\ninvalidText: 'Enter 1\u20131000 characters, not just whitespace.'\nrequestExpired: 'The initial send window expired. Press Send again.'\nnoPendingSend: 'There is no pending send, or its retry window expired.'\nautoRefresh: 'Latest messages are checked automatically every 30 seconds.'\nrefreshFailed: 'Could not refresh messages. The next cycle will retry, or you can refresh now.'\nhistoryPaused: 'Automatic refresh pauses while viewing older messages. Load latest messages to resume.'\nnoticeLoading: 'Checking message notifications'\nnoticeCount: '{count} new message notifications'\n", "./locales/en/equipment.yaml": 'title: Equipment\nrefresh: Refresh\nloading: Loading equipment.\nslots: Equipment slots\nmainHand: Main hand\noffHand: Off hand\nbody: Body\nback: Back\nfeet: Feet\ntool: Tool\nemptySlot: Empty\nweight: "Carried equipment weight: {weight} g"\nitemWeight: Weight\ndurability: Durability\nattack: Attack bonus\ndefense: Defense bonus\nequip: Equip\nunequip: Unequip\nequipped: Equipped\nreserved: Reserved\nbroken: Broken\nnoItems: No equipment for this slot on this page.\nmore: Load more\nsaved: Equipment saved.\nuncertain: The result could not be confirmed. Check again using the same request.\nretry: Check result again\ncomparison: "Compared with this slot: attack {attack} \xB7 defense {defense}"\n\nhistory: "Change history"\ncloseHistory: "Close history"\nnoHistory: "No recorded changes. Earlier history is not reconstructed."\nhistoryChanged: "History changed. Please refresh."\nhistoryAcquired: "Craft claimed"\nhistoryEquipped: "Equipped"\nhistoryUnequipped: "Unequipped"\nhistoryRepairReserved: "Repair started"\nhistoryRepaired: "Repair claimed"\nhistoryWorn: "Battle wear"\n\ninventoryChanged: "The equipment list changed. Please refresh the list."\nactionPoints: "Base max AP {base} \xB7 Equipped {weight} g \xB7 Weight penalty {penalty} AP \xB7 Effective max AP {maximum}"\nzeroActionPoints: Weight has reduced your maximum AP to 0. Equip lighter gear before battle to use actions that cost AP.\nequipAp: "Maximum AP after equipping: {maximum}"\nunequipAp: "Maximum AP after removing: {maximum}"\nhistoryRevoked: "Developer revocation"\n\nhistoryPagination: Equipment history pages\npreviousPage: Previous\nnextPage: Next\nhistoryPage: "Page {page}"\ninventoryPagination: Equipment inventory pages\ninventoryPageHelp: Shows equipment for the selected slot on the current page.\n', "./locales/en/field.yaml": `points: Field activity points
connecting: Connecting
maximum: Max 1,000 \xB7 +1/min
next: Next +1 \xB7 {seconds}s
grass: Grass
dew: Dewy ground
flowers: Flowers
road: Dirt path
legend: Passable terrain legend
guidance: Use steps to change elevation \xB7 Cliffs, rocks, bushes and lakes block movement
debt: Negative FP \xB7 Field actions are locked until recovery
destinationHeading: 'Waypoint to {name}'
travelTo: 'Travel to {name}'
destinationArrival: You have reached the waypoint. You can travel to the next map.
connectedMaps: 'Connected maps \xB7 {count}'
currentPosition: Current location
gridDistance: 'Grid distance: {count} tiles'
noConnections: No connected maps.
destinationRoute: '{count} tiles to the waypoint \xB7 Choose travel after arrival.'
aggressiveMonster: "Aggressive monster"
passiveMonster: "Passive monster"
mapConnection: "Map connection"
nearbyEvents: "Nearby events"
noEvents: "No selectable events nearby."
debtHelp: "Your FP is negative. Wait for recovery before taking field actions."
walkingProgress: "Movement progress"
walking: "Moving"
stopping: "Stopping movement"
walkingHeading: "Moving to your destination"
stopRequested: "Stop requested"
stop: "Stop moving"
stopAfterTile: "Movement will stop after the current tile."
stopAnytime: "You can stop moving at any time."
progressLabel: "Movement completion"
tileCommands: "Tile commands"
explore: "Look around"
whereTo: "Where would you like to go?"
selectHint: "Select a tile \u2192 Review action"
finishPreparation: "Complete or cancel encounter preparation before moving."
busy: "Wait for the current request to finish."
selectedLocation: "Selected location"
targetHeading: "Review target"
locationHeading: "Review destination"
monsterEncounter: "Monster encounter"
blockedTerrain: "Impassable terrain"
safeArea: "Safe area"
explorationPoint: "Exploration point"
clearSelection: "Clear selection"
clear: "Clear"
aggressiveWarning: "! Aggressive \xB7 Approach with care"
passive: "Passive"
aggressive: "Aggressive"
encounterBusy: "Another encounter is in progress."
noApproach: "No approach route is available."
adjacent: "Adjacent \xB7 Ready to encounter"
approachEncounter: "Approach and encounter"
startEncounter: "Start encounter"
blockedHelp: "Rocks, bushes and water block movement. Select another tile."
currentHelp: "You are standing here. Select another tile."
noRoute: "No route from your location. Select another destination."
insufficientFp: "Movement costs 1 FP per tile. Wait for recovery."
tileDetails: "Coordinates"
moveToGate: "Move to waypoint"
moveHere: "Move"
available: "Available"
unavailable: "Unavailable"
preparation: "Encounter preparation"
waitingParty: "Waiting for party"
ready: "Ready"
cancelReservation: "Cancel reservation"
nearby: "Nearby exploration"
nearbyHelp: "Monsters are listed nearest first. Select one to locate it on the map."
noMonsters: "No monsters to display on this map."
walked: "Moved {completed} / {total} tiles"
approachCost: "{count} tiles to approach \xB7 {count} FP"
walkRoute: "Walk {count} tiles along paths and steps."
coordinates: "Coordinates {column}, {row} \xB7 Elevation {height}"
moveCost: " \xB7 {count} tiles / {count} FP"
readyProgress: "Ready {ready}/{total} \xB7 {seconds}s remaining"
remainingMonsters: "More monsters: {count}"
legacyslime: Slime
legacybeast: Beast
legacygiant: Giant
monster: Monster
approachFieldRequired: You can start an encounter only while exploring.
approachFpDebt: Your FP is below zero. Wait for it to recharge before acting in the field.
approachTargetLost: The selected monster is no longer available for an encounter.
approachTooLong: The approach took too many steps and was stopped. Select the monster again.
aggroInterruption: A monster initiated combat and interrupted your field action. Completed movement is preserved; remaining movement and encounter requests will not resume.

resources: Health and field points
healthUnknown: Unknown

shortcutDistance: "{count} tiles"
arrivalCompact: "Arrived \xB7 travel available"
adjacentCompact: "Adjacent"
compactCoordinates: "{column},{row} \xB7 Height {height}"
terrainFpPreview: "Base {base} FP \xB7 expected {expected} FP \xB7 maximum {max} FP. Movement stops if extra costs reduce FP to zero or below."
terrainFpButton: " \xB7 {count} cells"

healthDepleted: Your HP is depleted. Rest or log out to recover before starting an encounter.

restStart: Rest
restStop: Stop resting
restProgress: Resting \xB7 HP +{amount}/min \xB7 next recovery in {seconds}s
restHint: Moving, acting, or being attacked ends rest and discards partial minutes.
restCompactProgress: HP +{amount} \xB7 {seconds}s
terrainFpCompact: "Est. {expected} FP \xB7 max {max}"
terrainFpHelp: "Movement stops if terrain costs reduce FP to zero or below."

recoveryPending: After incapacitation, recover at least 50% of maximum HP before moving. Rest or log out to recover.
firstAidButton: "First aid \xB7 {count} bandages"
firstAidHint: "Outside safe zones, use {count} bandages to restore {amount} HP. Requires literacy {literacy}."

scoutButton: 'Scout \xB7 {cost} FP'
scoutHelp: 'Current range: {range} tiles \xB7 {cost} FP per attempt'
scoutFailed: 'Observation failed \xB7 Count unknown'
scoutCountExact: 'Observed: {count}'
scoutCountRange: 'Observed: {minimum}\u2013{maximum}'
scoutCountAtLeast: 'Observed: {minimum} or more'
scoutExpires: 'Expires in {seconds}s'

scoutRiskLow: Low risk
scoutRiskEven: Even match
scoutRiskHigh: High risk
scoutRiskVeryHigh: Very high risk
scoutRiskUnknown: Risk unknown
scoutRiskHelp: Compares combat growth with eligible party members. This is not a win probability and does not account for current health, terrain, or tactics.
guardCenterHelp: A guard center serves this city entrance. Without local citizenship, obtain a traveler permit here to enter. The permit desk opens when you reach the entrance.
exploreHelp: "Exploration costs {cost} FP. Discoveries are collected automatically."
exploreRequirements: "Exploration level 1 and Literacy 2 required. Range {range} \xB7 Success {chance}%"
exploreMineral: Search for minerals
exploreTreasure: Search for treasure
exploreSuccess: Discovery collected. Search this spot again after 24 hours.
exploreFailure: Nothing found. Search this spot again after 30 seconds.
exploreReward: "Received: {reward}"
exploreBusy: Finish your current action and return to the field to explore.
exploreSafe: Move outside the safe zone before exploring.
exploreSkill: Exploration level 1 and usable Literacy level 2 are required.
exploreRange: "Move within {range} tiles of the selected spot."
exploreFp: "Recover to at least {cost} FP before exploring."

partyTravelBlocked: You cannot travel between maps while in an online party. Leave the party from the party menu before travelling.
`, "./locales/en/formation.yaml": `title: Party recruitment
count: 'Party {count} / 4 members (including you)'
help: Select a character registered at this guild. New loans last seven days. Removing a party member does not end the loan.
available: Available to recruit
borrowed: Already borrowed \xB7 Use existing copy
cpBlocked: Outside the CP range
full: Loan capacity full
selected: Already in your party
empty: No other candidates are registered at this guild.
choose: Select candidate
confirmName: 'Add {name} to your party.'
add: Add to party
remove: Remove from party
next: Next candidates
recover: Check formation result and retry
pending: Checking party details.
saved: Party formation updated.
manage: Current party formation
fieldHelp: You can remove members in the field without ending their seven-day loans. Visit a guild to add characters.
expired: Loan expired \xB7 remove from formation

noviceName: "Novice Guild Member"
noviceTerms: "Guild companion \xB7 Free 7-day contract \xB7 \xB120% earned CP requirement \xB7 Allocated materials go to the guild"
`, "./locales/en/guild.yaml": "title: Sell materials to the guild\nhelp: Sell your materials to the guild. No citizenship or FP is required.\nempty: You have no materials to sell.\nmaterial: Material to sell\nchoose: Select a material\noption: '{name} \xB7 Owned {count} \xB7 {price} P each'\nquantity: 'Quantity (up to {max})'\nquote: Review payment\ntotal: 'Sell {count} \xB7 Receive {price} P'\nconfirm: Confirm sale\nretry: Check result and retry\nuncertain: The result is unconfirmed. Check this transaction first and retry only if it has not been recorded.\npending: Checking transaction details.\nsold: Sale completed.\ncitizenshipPrice: Check citizenship price\ncitizenshipQuote: 'Current citizenship price {price} P \xB7 Quote valid for {seconds}s'\ncitizenshipExpired: This quote expired. Check the price again.\ncitizenshipPurchaseHelp: 'Pay {price} P to issue this city\u2019s citizenship for one year.'\ncitizenshipPurchase: Confirm citizenship issue\ncitizenshipRetry: Check result and retry\ncitizenshipUncertain: The result is unconfirmed. Check the same citizenship request again.\ncitizenshipPurchased: Citizenship issued.\nregistrationStatus: Check my candidate registration\nregistered: Your character is listed as a recruitment candidate in this city.\nunregistered: Your character is not listed as a recruitment candidate in this city.\nregistrationHelp: List your character for other players to recruit. Unlisting preserves existing seven-day loans. This is separate from adding another character to your party.\nregister: List my character as a candidate\nunregister: Unlist my character as a candidate\nregistrationUncertain: The update result is unconfirmed. Check your current party recruitment status first.\n", "./locales/en/hunts.yaml": "title: Hunt history\nhelp: Your shared kills recorded by the server at settlement. Records before the ledger was introduced may be absent. Older server responses may show IDs instead of names.\nrefresh: Refresh from the beginning\nloading: Loading hunt history.\ntotals: Totals by monster type\nempty: No hunt records.\npage: Records on this page\nemptyPage: No records on this page.\nmap: Map\nresult: Result\nbattle: Battle\nnext: Next page\nsubstituteTitle: FP substitute hunt\nsubstituteHelp: Spend FP for materials from species you have hunted before. FP is spent even when no materials drop.\nrefreshTargets: Refresh targets\nprocessing: Processing.\ninvalidState: Finish combat or reservations and return to the field or away mode.\nfirstRequired: Complete this species\u2019 first hunt achievement first.\nfpRequired: Not enough FP. Refresh after recovery.\nfpBalance: 'Available FP: {amount}'\nfpCost: 'FP cost: {amount}'\nexecute: Execute substitute hunt\nuncertain: Check the previous request\u2019s outcome first.\nretry: Check the same request again\ncompleted: 'Spent {amount} FP.'\nemptyDrop: No materials dropped this time.\npagination: Hunt history pages\nprevious: Previous page\npageNumber: 'Page {page}'\ntargetPagination: FP substitute hunt target pages\ntargetPageNumber: 'Page {page} of {total}'\n", "./locales/en/journal.yaml": "title: Main quest journal\nhelp: Accepted and completed quests. Material counts reflect the last refresh.\nrefresh: Refresh\nloading: Loading quest journal.\nempty: No main quests have been accepted yet.\naccepted: In progress\ncompleted: Completed\nreceiver: 'Deliver to: {name}'\nmaterial: '{name} \xB7 Owned {owned} / Required {required}'\nreward: 'Completion reward: {amount}P'\npaid: 'Reward received: {amount}P'\nstartedAt: 'Accepted: {time}'\nfinishedAt: 'Completed: {time}'\nmaterialsReady: Materials are ready. NPC location, citizenship and other requirements are checked again when delivering.\n\ncapacity: 'Accepted quests: {count} / {limit}'\ncapacityHelp: Main, seasonal, and random quests share this limit. Completed quests do not count.\ncapacityFull: The acceptance limit is full. Complete an active quest to accept another.\n\nshowDestination: Show delivery town\ndestinationUnavailable: The delivery town is not available on the current world map.\n\nreturnToJournal: Return to quest journal\n", "./locales/en/loans.yaml": `title: Borrowed party members
help: These are copies made when borrowed. Loans last 7 days and do not consume the original character's FP.
refresh: Refresh
loading: Loading borrowed party members\u2026
empty: No borrowed party members.
health: "HP {current} / {maximum}"
inbattle: In battle
available: Loan active
remaining: "{hours}h {minutes}m remaining"
expires: "Loan ends: {time}"
expiredbattle: Loan expired \xB7 The ongoing battle and settlement will continue.
expired: Loan ended \xB7 Refresh to remove it from this list.
more: Show more
ended: Loan ended
recoveryPending: "Recovering from incapacitation \xB7 Movement locked until HP recovers to at least 50% of maximum"
cpEligible: CP formation requirement met
cpOutOfRange: Outside the CP range \xB7 Cannot join a new battle
cpMigrationRequired: Loan-time CP migration required \xB7 Cannot join a new battle
cpUnknown: CP formation information unavailable
cpHelp: Compared with the leader's cumulative CP at the time of retrieval. CP, expiration, HP and battle participation are checked again when forming a party.
`, "./locales/en/missions.yaml": 'title: "Refining mission records"\nrecord: "Refining mission"\nnoRefund: "Cancellation does not refund the deposit or pay the completion reward. Entrusted goods are not automatically retrieved."\nrefresh: "Refresh"\nloading: "Processing mission request."\nchanged: "Character state changed. Refresh and select again."\nuncertain: "The result is uncertain. Retry the same request."\nretry: "Retry the same cancellation"\nempty: "No refining mission records."\nstatusActive: "Active"\nstatusCancelled: "Cancelled"\nstatusCompleted: "Completed"\noutput: "Output: {item} ({grade}) \xD7 {count}"\nprocessing: "Entrusted quantity {count} \xB7 Refining time {seconds}s"\npayment: "Deposit {deposit}P \xB7 Refining fee {cost}P \xB7 Completion reward {reward}P"\ncancel: "Cancel mission"\nnext: "Next records"\nconfirmTitle: "Confirm mission cancellation"\nconfirm: "Confirm without refund"\nkeep: "Keep mission"\ncancelled: "Mission cancelled. Refresh to view the record."\ninvalidReceipt: "The cancellation response does not match the request."\nlow: "Low"\nmedium: "Medium"\nhigh: "High"\ndestination: "Refining city: {city} \xB7 Deliver to: {receiverCity} / {npc}"\nacceptedAt: "Accepted: {time}"\n', "./locales/en/network.yaml": "protocol: Unsupported protocol.\nstateRequired: Load the game state first.\nconnected: Live connection established\ninvalidMessage: Unable to read the server message.\nreconnecting: Reconnecting \xB7 Controls locked\ntransitioning: Checking the session transition \xB7 Please wait.\ntransitionDelayed: The session transition is taking longer than expected. Sign in again to check its status.\nchatVerificationExpired: Advertisement verification or the chat connection has expired. Please try again.\nsessionChanged: The session changed, so the previous request was stopped.\nrequestTimeout: The response timed out. The server outcome is not yet known. Reconnect to check the latest state.\n", "./locales/en/npc.yaml": "talk: 'Talk: {name}'\ntitle: NPC quests\npending: Checking quest information.\nreload: Refresh to check the current quest status.\ncapacity: 'Active quests {count} / {max} \xB7 Main, seasonal, and random combined'\nempty: This NPC has no main quests for you.\navailable: Available\nlocked: Requirements not met\naccepted: In progress\ncompleted: Completed\naccept: Accept quest\ncomplete: Review delivery\ngiverrequired: Visit the NPC who offers this quest.\nreceiverrequired: Visit the delivery NPC.\nprerequisiterequired: Complete the prerequisite quest first.\nquestlimitreached: Quest limit reached. Complete an active quest first.\nmaterialsrequired: You do not have enough delivery materials.\ncitizenshiprequired: Valid citizenship in this town is required. Obtain it at the local Adventurers Guild. You can sell materials there to cover the fee even without citizenship.\ndeliveryReview: Review delivery\ndeliveryCharacter: 'Selected character: {name}'\ndeliveryMaterial: 'Consume {quantity} \xD7 {name}'\ndeliveryConfirm: Deliver\ndeliveryCancel: Go back\ndestination: 'Deliver to: {city} \xB7 {name}'\ndestinationCitizenship: 'Completing this quest requires valid citizenship in {city}. Obtain it at the local Adventurers Guild. You can sell materials there to cover the fee even without citizenship.'\n", "./locales/en/parcels.yaml": 'title: Mail and parcels\nhelp: Collect all parcel attachments from account storage. Expired parcels are discarded.\nrefresh: Refresh parcels\nempty: No parcels available to collect.\nclaim: Collect this parcel\nnext: Next page\nretry: Check collection result\nuncertain: The result is unknown. Check the same parcel again.\npending: Processing parcel request\u2026\nreceived: Parcel attachments collected.\nmoney: "{amount}P"\ncostume: "Costume {name}"\nitem: "{name} \xD7 {quantity}"\nexpires: "Expires: {time}"\nexpired: The storage period has ended. Refresh the parcel list.\narrived: "You have {count} parcels. Collect them from account storage."\nnoticeFailed: Could not check for parcels. Retrying shortly.\n\npagination: Parcel pages\nprevious: Previous page\npage: "Page {page}"\n', "./locales/en/rewards.yaml": 'title: "Account storage"\nhelp: "View and collect system parcels and lending rewards from anywhere. Parcels keep their assigned expiry; lending rewards expire after seven days."\nrefresh: "Refresh"\nloading: "Loading stored rewards\u2026"\nempty: "No rewards to claim."\nremaining: "{hours}h {minutes}m remaining"\nexpires: "Claim before: {time}"\nexpired: "Expired \xB7 Cannot claim"\nclaim: "Claim"\nclaiming: "Claiming\u2026"\nclaimed: "Rewards have been added to your bag."\nmore: "Load more"\nclaimAll: "Claim all lending rewards"\nclaimAllHelp: "Collect all unexpired lending rewards together, including pages not yet loaded."\nclaimSummary: "Claimed {count} rewards, containing {quantity} items in total."\nnothingClaimed: "No rewards are currently available. They may have been claimed or expired."\n\nloanRewards: "Lending rewards"\n\npagination: "Lending reward pages"\nprevious: "Previous page"\nnext: "Next page"\npage: "Page {page}"\n', "./locales/en/sponsor.yaml": "region: Sponsor advertisement verification\ndefaultAd: Default advertisement\nwelcome: Welcome to SLIME.\nplayback: Sponsor advertisement playback\nretry: Try again\nlogout: Sign out\ninvalidAttempt: The advertisement admission response is invalid.\n", "./locales/en/terms.yaml": 'title: "Terms of Use"\nbackToMenu: "Back to menu"\npendingNotice: "Advance notice: These clauses cover issue reports, incident record retention, and game data loss. Incident recording and issue reporting are not yet available. We will announce when these clauses take effect."\nreportHeading: "Reporting deadline"\nreportPolicy: "If you notice an issue with an action result, an item, or currency while using the service, please report it within one week of discovering it so that we can review the records and help you."\nreportDetails: "Include your adventurer information, when you noticed the issue, when you believe it occurred, and a description of what happened."\nretentionHeading: "Incident record retention"\nretentionPolicy: "Records of user actions and their results are retained for no more than 14 days from the time of the incident, then deleted."\nsupportLimits: "Even if you report within the deadline, investigation and assistance may be limited if records have already been deleted or there is insufficient information. Reporting does not extend record retention and does not guarantee restoration or compensation."\ndataLossHeading: "Game data loss due to disasters"\ndataLossPolicy: "Game data may be lost due to natural disasters or other circumstances that the service operator cannot reasonably prevent or respond to. In such circumstances, we cannot guarantee the prevention of data loss or the restoration of lost data."\noperationHeading: "Free service and character creation"\noperationPolicy: "To provide the game free of charge, we follow a low-cost operating policy and support the creation of only one character per person."\nconnectionLimitHeading: "Concurrent player limit"\nconnectionLimitPolicy: "To keep the game stable, we may limit the number of concurrent players. New connections may be restricted when the service is full. Please try again when capacity becomes available. The limit may be adjusted according to operating conditions."\nseasonLoginHeading: "Daily seasonal login reward"\nseasonLoginPolicy: "Once a season begins, your first login each day during the season earns 1 CP and 1 SP as a seasonal achievement reward. Days follow Korea Standard Time. Additional logins on the same day do not earn another reward."\ncurrentSeason: "The current season is Season 0 \xB7 Test Season. The same daily login reward policy applies."\npartyInactivityHeading: "Party disbanding after inactivity"\npartyInactivityPolicy: "A party is automatically disbanded after its leader has been continuously offline for at least 24 hours. The leader\u2019s character loans also end early, releasing capacity for other parties. Inactivity of ordinary members or the original owners of borrowed characters does not trigger disbanding. Ongoing battles and reward settlement are preserved."\npartyDisbandNotice: "A party you previously belonged to was automatically disbanded after its leader was offline for 24 consecutive hours. The leader\u2019s loan capacity was released. Battles already in progress and their reward settlement are preserved."\n', "./locales/en/timedquests.yaml": `talk: '{name}: seasonal and random quests'
title: Seasonal and random quest journal
empty: No timed quests to show. Having no random quest today is normal.
expired: Expired \xB7 no reward
destination: 'Deliver to: {name}'
acceptBefore: 'Accept before: {time}'
deliverBefore: 'Deliver before: {time}'
randomDeadline: Deliver within 24 hours after accepting.
seasonDeadline: 'Delivery deadline after acceptance: {time}'
next: Next records

pagination: Timed quest journal pages
previous: Previous records
page: "Page {page}"
`, "./locales/en/wardrobe.yaml": 'title: Owned costumes\nhelp: View costumes acquired through parcels or shops. Costumes affect appearance only.\nrefresh: Load owned costumes\nloading: Loading costumes\u2026\nempty: No acquired costumes. The default design is available.\nreceived: "Received by parcel: {time}"\nequip: Equip\ndefault: Use default design\nretry: Check equip result\nuncertain: The result is unknown. Check the same equip request again.\nequipped: Costume changed.\nunavailable: Finish combat and change your costume from the menu.\ninvalidResponse: The equip response does not match the request, character, or design.\n\npurchased: "Purchased from shop: {time}"\n', "./locales/en/workshop.yaml": `title: Workshop crafting and repairs
citizenship: New contracts require valid local citizenship. Existing contracts can be collected here even after citizenship expires.
craft: Craft
repair: Repair
pending: Checking workshop information.
item: Item
choose: Select an item
noItems: No eligible items. Repairs require damaged equipment that is neither equipped nor reserved.
quote: Review quote
price: 'Cost {cost} P \xB7 Duration {seconds} seconds'
durability: 'Durability {before}/{beforeMax} \u2192 {after}/{afterMax} (maximum durability decreases)'
noCancel: Confirming deducts the cost and materials and cannot be cancelled. Work continues offline. Collect the result here when ready.
confirm: Accept cost and create contract
contracts: Contracts
empty: No contracts.
ready: Ready to collect
inprogress: In progress \xB7 Refresh after the completion time
claimed: Collected
readyAt: 'Completion time: {time}'
claim: Collect result
next: Next contracts page
uncertain: The response was not confirmed. Use the contract button below to retry the same request without a duplicate charge.

consumable: Consumable crafting

quantity: 'Quantity (1\u20131000)'
quantityTime: '{quantity} items \xB7 {seconds}s each \xB7 Other contracts run concurrently'
balance: 'Balance at quote: {owned} P \xB7 Shortfall: {missing} P'
materialBalance: 'Owned: {owned} \xB7 Shortfall: {missing}'
materialAllocation: "Owned {owned} \xB7 Used {used} \xB7 Missing {missing}"
costBreakdown: 'Crafting fee {base} P + missing materials {missing} P'
substitutionRule: 'Owned materials are used first. Missing quantities are valued at guild buying prices; their total is multiplied by 1.5 and rounded up for payment. Missing materials are not added to your bag.'
paidTotal: 'Total paid at contract creation: {cost} P'

refiningContracts: Processing contracts & collection
refiningCreate: Request processing
refiningBrowse: Browse processing recipes
refiningUnavailable: Processing is not available in this city yet.
refiningRecipe: Output material and grade
refiningQuantity: Output quantity
refiningQuote: Get quote
refiningSummary: 'Requires {input} collectibles ({owned} owned) \xB7 {cost} P \xB7 {seconds} seconds'
refiningSubmit: Pay and request processing
refiningCreated: Processing requested. Refresh the contract list and collect when ready.

processingMethodRefining: Refining
processingMethodSmelting: Smelting
processingKindMaterial: Processed material
processingKindEssence: Elemental essence

materialSelection: Materials by grade
materialOwned: 'Owned {quantity}'
materialTotal: 'Selected {selected} / required {required}'
materialTotalInvalid: Select grade quantities that add up to the required total.

material: Material crafting

batchSelection: Material batches
batchRequired: Select the required quantity from owned batches. Missing batches cannot be purchased.
ownedMaterialRequired: Only owned materials can be used. Obtain any missing materials before crafting.
ownedMaterialInvalid: Select the required quantity within your stock. Reduce the order quantity or obtain more materials if needed.
` };
var catalogs = { ko: {}, en: {} };
for (const [path, source] of Object.entries(sources)) {
  const match = path.match(/^\.\/locales\/(ko|en)\/([a-z]+)\.yaml$/);
  if (!match) throw new Error(`\uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uC5B8\uC5B4\uD329 \uACBD\uB85C: ${path}`);
  const [, locale2, domain] = match;
  for (const [key, value] of Object.entries(parsePack(source, path))) catalogs[locale2][`${domain}.${key}`] = value;
}
validatePair(catalogs.ko, catalogs.en, "en");
var saved = localStorage.getItem(STORAGE_KEY);
var locale = saved === null ? "ko" : checkedLocale(saved);
function checkedLocale(value) {
  if (value !== "ko" && value !== "en") throw new Error(`\uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uC5B8\uC5B4: ${value}`);
  return value;
}
document.documentElement.lang = locale;
function t3(key, values) {
  const message = catalogs[locale][key];
  if (message === void 0) throw new Error(`\uBC88\uC5ED\uC744 \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4: ${locale}.${key}`);
  return formatMessage(message, values);
}

// src/game/terrain/cityBuildings.ts
function cityBuildingCells(currentCityBuilding) {
  return Array.from({ length: currentCityBuilding.width * currentCityBuilding.height }, (_2, currentCellIndex) => ({
    column: currentCityBuilding.origin.column + currentCellIndex % currentCityBuilding.width,
    row: currentCityBuilding.origin.row + Math.floor(currentCellIndex / currentCityBuilding.width)
  }));
}

// src/game/terrain/blockStructureRendering.ts
var CITY_HALF_TILE = 0.5;
var WALL_ENTRANCE_POSITION_TOLERANCE = 0.01;
function drawBlockStructure(currentMapScene, currentCityBuilding, projectTerrainPosition, calculateTerrainDepth, currentAnnotationDepth, currentBuildingSelected) {
  if (currentCityBuilding.blockSchemaVersion !== 1) throw new Error("\uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uAC74\uBB3C \uBE14\uB85D \uBC84\uC804");
  const currentBuildingCorners = cityBuildingCells(currentCityBuilding).map(projectTerrainPosition);
  const currentBuildingDepth = Math.max(...cityBuildingCells(currentCityBuilding).map(calculateTerrainDepth)) + TERRAIN_DEPTH.overlay;
  const currentSurfaceFaces = buildRenderedBlockFaces(currentCityBuilding.blocks);
  const currentProjectedFaces = currentSurfaceFaces.map((currentSurfaceFace) => ({ surface: currentSurfaceFace, depth: currentSurfaceFace.vertices.reduce((currentDepthSum, currentVertexPoint) => currentDepthSum + projectTerrainPosition({ column: currentCityBuilding.origin.column + currentVertexPoint.column, row: currentCityBuilding.origin.row + currentVertexPoint.row }).y, 0) / currentSurfaceFace.vertices.length, points: currentSurfaceFace.vertices.map((currentVertexPoint) => {
    const currentScreenPoint = projectTerrainPosition({ column: currentCityBuilding.origin.column + currentVertexPoint.column, row: currentCityBuilding.origin.row + currentVertexPoint.row });
    return { x: currentScreenPoint.x, y: currentScreenPoint.y - currentVertexPoint.height };
  }) }));
  const currentVisibleFaces = currentProjectedFaces.filter((currentProjectedFace) => currentProjectedFace.surface.top || currentProjectedFace.points.reduce((currentSignedArea, currentPointValue, currentPointIndex) => {
    const nextPointValue = currentProjectedFace.points[(currentPointIndex + 1) % currentProjectedFace.points.length];
    return currentSignedArea + currentPointValue.x * nextPointValue.y - nextPointValue.x * currentPointValue.y;
  }, 0) > 0);
  currentVisibleFaces.sort((firstSurfaceFace, secondSurfaceFace) => firstSurfaceFace.depth - secondSurfaceFace.depth);
  const currentBuildingGraphic = currentMapScene.add.graphics().setDepth(currentBuildingDepth);
  for (const currentProjectedFace of currentVisibleFaces) {
    currentBuildingGraphic.fillStyle(currentProjectedFace.surface.material === "roof" ? CITY_BUILDING_STYLE.roofColors[currentCityBuilding.facilityKind] : CITY_BUILDING_STYLE.wallLight, 1).fillPoints(currentProjectedFace.points, true);
    currentBuildingGraphic.lineStyle(1, CITY_BUILDING_STYLE.outlineColor, 0.35).strokePoints(currentProjectedFace.points, true);
  }
  const usesUnifiedWoodWall = ["reedhaven-", "grainstead-", "saltford-"].some((currentCityPrefix) => currentCityBuilding.id.startsWith(currentCityPrefix)) || ["iseulon-bookshop", "iseulon-inn"].includes(currentCityBuilding.id);
  if (usesUnifiedWoodWall) {
    const woodRoofBaseHeight = Math.min(...currentSurfaceFaces.filter((currentFaceRecord) => currentFaceRecord.material === "roof").flatMap((currentFaceRecord) => currentFaceRecord.vertices.map((currentVertexPoint) => currentVertexPoint.height)));
    for (const currentWallFace of currentVisibleFaces.filter((currentFaceRecord) => !currentFaceRecord.surface.top)) {
      const wallMinimumScreenX = Math.floor(Math.min(...currentWallFace.points.map((currentPointValue) => currentPointValue.x)));
      const wallMinimumScreenY = Math.floor(Math.min(...currentWallFace.points.map((currentPointValue) => currentPointValue.y)));
      const wallCanvasPixelWidth = Math.ceil(Math.max(...currentWallFace.points.map((currentPointValue) => currentPointValue.x))) - wallMinimumScreenX;
      const wallCanvasPixelHeight = Math.ceil(Math.max(...currentWallFace.points.map((currentPointValue) => currentPointValue.y))) - wallMinimumScreenY;
      const wallTextureUniqueIdentifier = shared_phaser_default.Utils.String.UUID();
      const wallCanvasTexture = currentMapScene.textures.createCanvas(wallTextureUniqueIdentifier, wallCanvasPixelWidth, wallCanvasPixelHeight);
      if (!wallCanvasTexture) throw new Error("\uB098\uBB34 \uBCBD \uCE94\uBC84\uC2A4 \uC0DD\uC131 \uC2E4\uD328");
      const wallDrawingContext = wallCanvasTexture.getContext();
      const wallVertexRecords = currentWallFace.surface.vertices;
      const wallColumnVaries = wallVertexRecords.some((currentVertexPoint) => currentVertexPoint.column !== wallVertexRecords[0].column);
      const wallMinimumHorizontal = Math.min(...wallVertexRecords.map((currentVertexPoint) => wallColumnVaries ? currentVertexPoint.column : currentVertexPoint.row));
      const wallMaximumHorizontal = Math.max(...wallVertexRecords.map((currentVertexPoint) => wallColumnVaries ? currentVertexPoint.column : currentVertexPoint.row));
      const wallMinimumHeight = Math.min(...wallVertexRecords.map((currentVertexPoint) => currentVertexPoint.height));
      const wallMaximumHeight = Math.max(...wallVertexRecords.map((currentVertexPoint) => currentVertexPoint.height));
      const wallHorizontalIndex = Math.floor(wallMinimumHorizontal + CITY_HALF_TILE);
      const entranceColumnLocal = currentCityBuilding.entrance.column - currentCityBuilding.origin.column;
      const entranceRowLocal = currentCityBuilding.entrance.row - currentCityBuilding.origin.row;
      const entranceAlongWall = wallColumnVaries ? entranceColumnLocal : entranceRowLocal;
      const wallEntranceDistance = Math.abs(wallHorizontalIndex - Math.round(entranceAlongWall));
      const wallUsesWindowTexture = wallMinimumHeight < woodRoofBaseHeight && wallEntranceDistance % 2 !== 0;
      const entranceAcrossWall = wallColumnVaries ? entranceRowLocal : entranceColumnLocal;
      const wallFixedCoordinate = wallColumnVaries ? wallVertexRecords[0].row : wallVertexRecords[0].column;
      const wallUsesDoorTexture = wallMinimumHeight < WALL_ENTRANCE_POSITION_TOLERANCE && Math.abs(entranceAlongWall - (wallMinimumHorizontal + wallMaximumHorizontal) / 2) < WALL_ENTRANCE_POSITION_TOLERANCE && Math.abs(Math.abs(entranceAcrossWall - wallFixedCoordinate) - CITY_HALF_TILE) < WALL_ENTRANCE_POSITION_TOLERANCE;
      const wallSelectedTexture = wallMinimumHeight >= woodRoofBaseHeight ? WOOD_CROSSBAR_WALL_TEXTURE : wallUsesDoorTexture ? WOOD_DOOR_WALL_TEXTURE : wallUsesWindowTexture ? WOOD_WINDOW_WALL_TEXTURE : UNIFIED_WOOD_WALL_TEXTURE;
      const wallSourceImage = currentMapScene.textures.get(wallSelectedTexture).getSourceImage();
      const wallOriginPosition = { column: currentCityBuilding.origin.column + (wallColumnVaries ? wallMinimumHorizontal : wallVertexRecords[0].column), row: currentCityBuilding.origin.row + (wallColumnVaries ? wallVertexRecords[0].row : wallMinimumHorizontal) };
      const wallOriginScreenPoint = projectTerrainPosition(wallOriginPosition);
      const wallEndScreenPoint = projectTerrainPosition({ column: wallOriginPosition.column + (wallColumnVaries ? wallMaximumHorizontal - wallMinimumHorizontal : 0), row: wallOriginPosition.row + (wallColumnVaries ? 0 : wallMaximumHorizontal - wallMinimumHorizontal) });
      wallDrawingContext.beginPath();
      currentWallFace.points.forEach((currentPointValue, currentPointIndex) => {
        if (currentPointIndex === 0) wallDrawingContext.moveTo(currentPointValue.x - wallMinimumScreenX, currentPointValue.y - wallMinimumScreenY);
        else wallDrawingContext.lineTo(currentPointValue.x - wallMinimumScreenX, currentPointValue.y - wallMinimumScreenY);
      });
      wallDrawingContext.closePath();
      wallDrawingContext.clip();
      wallDrawingContext.transform((wallEndScreenPoint.x - wallOriginScreenPoint.x) / wallSourceImage.width, (wallEndScreenPoint.y - wallOriginScreenPoint.y) / wallSourceImage.width, 0, (wallMaximumHeight - wallMinimumHeight) / wallSourceImage.height, wallOriginScreenPoint.x - wallMinimumScreenX, wallOriginScreenPoint.y - wallMaximumHeight - wallMinimumScreenY);
      wallDrawingContext.drawImage(wallSourceImage, 0, 0);
      wallCanvasTexture.refresh();
      currentMapScene.add.image(wallMinimumScreenX, wallMinimumScreenY, wallTextureUniqueIdentifier).setOrigin(0).setDepth(currentBuildingDepth + 0.01).once("destroy", () => currentMapScene.textures.remove(wallTextureUniqueIdentifier));
    }
  }
  if (usesUnifiedWoodWall || currentCityBuilding.id.startsWith("stonewarm-")) {
    const roofSurfaceFaces = currentVisibleFaces.filter((currentFaceRecord) => currentFaceRecord.surface.material === "roof" && currentFaceRecord.surface.top);
    if (roofSurfaceFaces.length) {
      const roofCornerPoints = roofSurfaceFaces.flatMap((currentFaceRecord) => currentFaceRecord.points);
      const roofMinimumX = Math.floor(Math.min(...roofCornerPoints.map((currentPointValue) => currentPointValue.x)));
      const roofMinimumY = Math.floor(Math.min(...roofCornerPoints.map((currentPointValue) => currentPointValue.y)));
      const roofCanvasWidth = Math.ceil(Math.max(...roofCornerPoints.map((currentPointValue) => currentPointValue.x))) - roofMinimumX;
      const roofCanvasHeight = Math.ceil(Math.max(...roofCornerPoints.map((currentPointValue) => currentPointValue.y))) - roofMinimumY;
      const roofTextureIdentifier = shared_phaser_default.Utils.String.UUID();
      const roofCanvasTexture = currentMapScene.textures.createCanvas(roofTextureIdentifier, roofCanvasWidth, roofCanvasHeight);
      if (!roofCanvasTexture) throw new Error("\uC9C0\uBD95 \uCE94\uBC84\uC2A4 \uC0DD\uC131 \uC2E4\uD328");
      const roofDrawingContext = roofCanvasTexture.getContext();
      const selectedRoofTextureIdentifier = usesUnifiedWoodWall ? UNIFIED_WOOD_ROOF_TEXTURE : currentCityBuilding.facilityKind === "guild" ? STONEWARM_GUILD_ROOF_TEXTURE : STONEWARM_ROOF_TEXTURE;
      const roofSourceImage = currentMapScene.textures.get(selectedRoofTextureIdentifier).getSourceImage();
      for (const roofFaceRecord of roofSurfaceFaces) {
        const roofFacePoints = roofFaceRecord.points;
        if (roofFacePoints.length !== 4) throw new Error("\uC9C0\uBD95 \uBA74\uC740 \uC0AC\uAC01\uD615\uC774\uC5B4\uC57C \uD569\uB2C8\uB2E4.");
        roofDrawingContext.save();
        roofDrawingContext.beginPath();
        roofFacePoints.forEach((roofPointValue, roofPointIndex) => {
          if (roofPointIndex === 0) roofDrawingContext.moveTo(roofPointValue.x - roofMinimumX, roofPointValue.y - roofMinimumY);
          else roofDrawingContext.lineTo(roofPointValue.x - roofMinimumX, roofPointValue.y - roofMinimumY);
        });
        roofDrawingContext.closePath();
        roofDrawingContext.clip();
        roofDrawingContext.transform(
          (roofFacePoints[1].x - roofFacePoints[0].x) / roofSourceImage.width,
          (roofFacePoints[1].y - roofFacePoints[0].y) / roofSourceImage.width,
          (roofFacePoints[3].x - roofFacePoints[0].x) / roofSourceImage.height,
          (roofFacePoints[3].y - roofFacePoints[0].y) / roofSourceImage.height,
          roofFacePoints[0].x - roofMinimumX,
          roofFacePoints[0].y - roofMinimumY
        );
        roofDrawingContext.drawImage(roofSourceImage, 0, 0);
        roofDrawingContext.restore();
      }
      roofCanvasTexture.refresh();
      currentMapScene.add.image(roofMinimumX, roofMinimumY, roofTextureIdentifier).setOrigin(0).setDepth(currentBuildingDepth + 0.01).once("destroy", () => currentMapScene.textures.remove(roofTextureIdentifier));
    }
  }
  const currentRoofCorners = currentVisibleFaces.flatMap((currentProjectedFace) => currentProjectedFace.points);
  const currentEntrancePoint = projectTerrainPosition(currentCityBuilding.entrance);
  const currentMarkerGraphic = currentMapScene.add.graphics().setDepth(currentAnnotationDepth);
  currentMarkerGraphic.lineStyle(
    currentBuildingSelected ? CITY_BUILDING_STYLE.selectedWidth : CITY_BUILDING_STYLE.outlineWidth,
    currentBuildingSelected ? CITY_BUILDING_STYLE.selectedColor : CITY_BUILDING_STYLE.wallLight
  );
  currentMarkerGraphic.strokeCircle(currentEntrancePoint.x, currentEntrancePoint.y, CITY_BUILDING_STYLE.entranceRadius);
  if (currentBuildingSelected) currentMarkerGraphic.strokePoints(currentBuildingCorners, true);
  const currentRoofCenter = {
    x: currentRoofCorners.reduce((currentTotalValue, currentCornerPoint) => currentTotalValue + currentCornerPoint.x, 0) / currentRoofCorners.length,
    y: currentRoofCorners.reduce((currentTotalValue, currentCornerPoint) => currentTotalValue + currentCornerPoint.y, 0) / currentRoofCorners.length
  };
  currentMapScene.add.text(
    currentRoofCenter.x,
    currentRoofCenter.y - CITY_BUILDING_STYLE.labelOffset,
    t3(`city.${currentCityBuilding.facilityKind}`),
    { fontFamily: "sans-serif", fontSize: CITY_BUILDING_STYLE.labelFont, color: "#fff7de", stroke: "#39362d", strokeThickness: 4 }
  ).setOrigin(CITY_HALF_TILE).setDepth(currentAnnotationDepth);
  const currentVisiblePoints = [...currentBuildingCorners, ...currentRoofCorners];
  return {
    position: currentCityBuilding.origin,
    depth: currentBuildingDepth,
    polygons: currentVisibleFaces.map((currentFaceValue) => new shared_phaser_default.Geom.Polygon(currentFaceValue.points)),
    left: Math.min(...currentVisiblePoints.map((currentPointValue) => currentPointValue.x)),
    right: Math.max(...currentVisiblePoints.map((currentPointValue) => currentPointValue.x)),
    top: Math.min(...currentVisiblePoints.map((currentPointValue) => currentPointValue.y)),
    bottom: Math.max(...currentVisiblePoints.map((currentPointValue) => currentPointValue.y))
  };
}

// packages/field-renderer/field-renderer.mjs
function prepareFieldConnectedTexture(currentGameScene, currentSourceKey, currentGrassKey, currentConnectionMask) {
  const currentTextureKey = `field-connected:${currentSourceKey}:${currentGrassKey}:${currentConnectionMask}`;
  if (currentGameScene.textures.exists(currentTextureKey)) return currentTextureKey;
  const currentSourceImage = currentGameScene.textures.get(currentSourceKey).getSourceImage();
  const currentGrassImage = currentGameScene.textures.get(currentGrassKey).getSourceImage();
  const currentTextureSize = currentSourceImage.width;
  const currentCanvasTexture = currentGameScene.textures.createCanvas(currentTextureKey, currentTextureSize, currentTextureSize);
  if (!currentCanvasTexture) throw Error("\uD544\uB4DC \uC5F0\uACB0 \uD14D\uC2A4\uCC98 \uC0DD\uC131 \uC2E4\uD328");
  const currentDrawingContext = currentCanvasTexture.getContext();
  const currentInsetPixels = currentTextureSize * FIELD_CONNECTION_SHAPE.inset, currentHalfPixels = currentTextureSize * FIELD_CONNECTION_SHAPE.half, currentInnerWidth = currentTextureSize - currentInsetPixels * 2;
  currentDrawingContext.drawImage(currentGrassImage, 0, 0, currentTextureSize, currentTextureSize);
  currentDrawingContext.save();
  currentDrawingContext.beginPath();
  currentDrawingContext.roundRect(currentInsetPixels, currentInsetPixels, currentInnerWidth, currentInnerWidth, currentTextureSize * FIELD_CONNECTION_SHAPE.radius);
  if (currentConnectionMask & 1) currentDrawingContext.rect(currentInsetPixels, 0, currentInnerWidth, currentHalfPixels);
  if (currentConnectionMask & 2) currentDrawingContext.rect(currentHalfPixels, currentInsetPixels, currentHalfPixels, currentInnerWidth);
  if (currentConnectionMask & 4) currentDrawingContext.rect(currentInsetPixels, currentHalfPixels, currentInnerWidth, currentHalfPixels);
  if (currentConnectionMask & 8) currentDrawingContext.rect(0, currentInsetPixels, currentHalfPixels, currentInnerWidth);
  if ((currentConnectionMask & 3) === 3) currentDrawingContext.rect(currentHalfPixels, 0, currentHalfPixels, currentHalfPixels);
  if ((currentConnectionMask & 6) === 6) currentDrawingContext.rect(currentHalfPixels, currentHalfPixels, currentHalfPixels, currentHalfPixels);
  if ((currentConnectionMask & 12) === 12) currentDrawingContext.rect(0, currentHalfPixels, currentHalfPixels, currentHalfPixels);
  if ((currentConnectionMask & 9) === 9) currentDrawingContext.rect(0, 0, currentHalfPixels, currentHalfPixels);
  currentDrawingContext.clip();
  currentDrawingContext.drawImage(currentSourceImage, 0, 0, currentTextureSize, currentTextureSize);
  currentDrawingContext.restore();
  currentCanvasTexture.refresh();
  return currentTextureKey;
}

// src/game/terrain/fieldTileRendering.ts
function resolveFieldTileTextures(currentGameScene, currentTerrainName, currentCellPosition, currentMapIdentifier, currentConnectionMask, resolveGroundMaterial) {
  const currentSelectedFrame = currentTerrainName === "water" ? `water-${currentConnectionMask}` : currentTerrainName === "road" ? selectFieldRoadFrame(currentConnectionMask, currentCellPosition, false, currentMapIdentifier) : currentTerrainName === "flowers" && currentMapIdentifier === "meadow" ? "meadow-flowers" : currentTerrainName;
  const currentConnectedFrame = /^(water|road|dirt-road|stone-road)-(\d+)$/.exec(currentSelectedFrame);
  const currentGroundKey = currentConnectedFrame ? prepareFieldConnectedTexture(currentGameScene, `terrain-source-${currentConnectedFrame[1]}`, "terrain-source-grass", Number(currentConnectedFrame[2])) : `terrain-source-${currentSelectedFrame}`;
  return { ground: currentGroundKey, resolveGroundMaterial, cliff: CLIFF_WALL_TEXTURE, tread: RAMP_TREAD_TEXTURE, roadConnectionMask: currentTerrainName === "road" ? currentConnectionMask : void 0, fullTileRoad: currentTerrainName === "road" && !currentConnectedFrame, underlay: ["boulder", "tree-base"].includes(currentTerrainName) ? "terrain-source-grass" : void 0 };
}

// packages/field-renderer/town-renderer.ts
function collectTerrainTextureSources() {
  const registeredTextureSources = {};
  preloadTerrain({ load: { image(currentTextureKey, currentAssetPath) {
    registeredTextureSources[currentTextureKey] = currentAssetPath;
  } } });
  return registeredTextureSources;
}
export {
  BUILDING_RENDER_BLOCK_HEIGHT,
  TERRAIN_ATLAS,
  TERRAIN_DEPTH,
  buildRenderedBlockFaces,
  cellDepth,
  collectTerrainTextureSources,
  createTerrainAtlas,
  drawBlockStructure,
  mapAnnotationDepth,
  resolveFieldTileTextures,
  resolveGrassFrameForMap,
  resolveMapTileSize,
  resolvePavingFrameForMap,
  roadConnections,
  selectFieldRoadFrame,
  waterConnections
};
