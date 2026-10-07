// packages/field-surface/field-surface.mjs
var FIELD_RENDER_METRICS = Object.freeze({ tileWidth: 80, tileHeight: 40, elevationHeight: 32, baseThickness: 16 });
var TERRAIN_STAIR_COUNT = 6;
function readSurfaceHeight(currentCellPosition, currentMapSurface) {
  if (currentCellPosition.column < 0 || currentCellPosition.row < 0 || currentCellPosition.column >= currentMapSurface.columns || currentCellPosition.row >= currentMapSurface.rows) return 0;
  if (currentMapSurface.heightSource) return readSurfaceHeight(currentMapSurface.heightSource.position(currentCellPosition), currentMapSurface.heightSource.surface);
  return currentMapSurface.elevations?.[currentCellPosition.row]?.[currentCellPosition.column] ?? 0;
}
function rotateSurfacePosition(currentCellPosition, currentQuarterTurns = 0) {
  let currentColumnValue = currentCellPosition.column, currentRowValue = currentCellPosition.row;
  for (let currentTurnIndex = 0; currentTurnIndex < (currentQuarterTurns % 4 + 4) % 4; currentTurnIndex++) [currentColumnValue, currentRowValue] = [-currentRowValue, currentColumnValue];
  return { column: currentColumnValue, row: currentRowValue };
}
function projectSurfaceVertex(currentVertexPosition, currentRenderOptions) {
  const currentRotatedPosition = rotateSurfacePosition(currentVertexPosition, currentRenderOptions.rotation ?? 0);
  return { x: (currentRenderOptions.originX ?? 0) + (currentRotatedPosition.column - currentRotatedPosition.row) * currentRenderOptions.tileWidth / 2, y: (currentRenderOptions.originY ?? 0) + (currentRotatedPosition.column + currentRotatedPosition.row) * currentRenderOptions.tileHeight / 2 - (currentVertexPosition.height ?? 0) };
}
function findSurfaceStair(currentCellPosition, currentMapSurface) {
  return currentMapSurface.elevationTileIndex ? currentMapSurface.elevationTileIndex.get(`${currentCellPosition.column},${currentCellPosition.row}`) : currentMapSurface.elevationTiles?.find((currentStairRecord) => currentStairRecord.cell.column === currentCellPosition.column && currentStairRecord.cell.row === currentCellPosition.row);
}
function projectSurfaceCell(currentCellPosition, currentMapSurface, currentRenderOptions) {
  return projectSurfaceVertex({ ...currentCellPosition, height: (readSurfaceHeight(currentCellPosition, currentMapSurface) - (findSurfaceStair(currentCellPosition, currentMapSurface) ? 0.5 : 0)) * currentRenderOptions.elevationHeight }, currentRenderOptions);
}
function buildSurfaceCliffs(currentCellPosition, currentMapSurface, currentRenderOptions) {
  if (!currentMapSurface.elevations && !currentMapSurface.heightSource) return [];
  const currentCenterPoint = projectSurfaceCell(currentCellPosition, currentMapSurface, currentRenderOptions), currentHeightValue = readSurfaceHeight(currentCellPosition, currentMapSurface);
  const currentVisibleEdges = [{ direction: { column: 1, row: 0 }, edge: [[0, currentRenderOptions.tileHeight / 2], [currentRenderOptions.tileWidth / 2, 0]] }, { direction: { column: 0, row: 1 }, edge: [[-currentRenderOptions.tileWidth / 2, 0], [0, currentRenderOptions.tileHeight / 2]] }];
  return currentVisibleEdges.flatMap((currentEdgeRecord) => {
    const currentNeighborOffset = rotateSurfacePosition(currentEdgeRecord.direction, -(currentRenderOptions.rotation ?? 0));
    const currentNeighborCell = { column: currentCellPosition.column + currentNeighborOffset.column, row: currentCellPosition.row + currentNeighborOffset.row };
    const currentNeighborInside = currentNeighborCell.column >= 0 && currentNeighborCell.row >= 0 && currentNeighborCell.column < currentMapSurface.columns && currentNeighborCell.row < currentMapSurface.rows;
    const currentNeighborStair = findSurfaceStair(currentNeighborCell, currentMapSurface);
    const currentRampSideWall = Boolean(currentNeighborStair && currentNeighborOffset.column * (currentNeighborStair.cell.column - currentNeighborStair.lower.column) + currentNeighborOffset.row * (currentNeighborStair.cell.row - currentNeighborStair.lower.row) === 0);
    const currentNeighborHeight = readSurfaceHeight(currentNeighborCell, currentMapSurface) - (currentRampSideWall ? 1 : 0);
    const currentHeightDrop = currentNeighborInside ? (currentHeightValue - currentNeighborHeight) * currentRenderOptions.elevationHeight : currentHeightValue * currentRenderOptions.elevationHeight + currentRenderOptions.baseThickness;
    if (currentHeightDrop <= 0) return [];
    const [currentFirstPoint, currentSecondPoint] = currentEdgeRecord.edge.map(([currentOffsetX, currentOffsetY]) => ({ x: currentCenterPoint.x + currentOffsetX, y: currentCenterPoint.y + currentOffsetY }));
    return [Object.assign([currentFirstPoint, currentSecondPoint, { x: currentSecondPoint.x, y: currentSecondPoint.y + currentHeightDrop }, { x: currentFirstPoint.x, y: currentFirstPoint.y + currentHeightDrop }], { rampWall: currentRampSideWall })];
  });
}
function buildSurfaceStairs(currentStairRecord, currentMapSurface, currentRenderOptions) {
  const currentColumnDelta = currentStairRecord.cell.column - currentStairRecord.lower.column, currentRowDelta = currentStairRecord.cell.row - currentStairRecord.lower.row;
  const currentLowerHeight = readSurfaceHeight(currentStairRecord.cell, currentMapSurface) - 1;
  const currentViewDirection = rotateSurfacePosition({ column: currentColumnDelta, row: currentRowDelta }, currentRenderOptions.rotation ?? 0);
  const projectStairVertex = (currentAlongOffset, currentAcrossOffset, currentHeightValue) => projectSurfaceVertex({ column: currentStairRecord.cell.column + currentColumnDelta * currentAlongOffset - currentRowDelta * currentAcrossOffset, row: currentStairRecord.cell.row + currentRowDelta * currentAlongOffset + currentColumnDelta * currentAcrossOffset, height: currentHeightValue * currentRenderOptions.elevationHeight }, currentRenderOptions);
  return Array.from({ length: TERRAIN_STAIR_COUNT }, (_, currentStepIndex) => {
    const currentNearOffset = currentStepIndex / TERRAIN_STAIR_COUNT - 0.5, currentFarOffset = (currentStepIndex + 1) / TERRAIN_STAIR_COUNT - 0.5, currentTopHeight = currentLowerHeight + (currentStepIndex + 1) / TERRAIN_STAIR_COUNT;
    const currentTopPoints = [projectStairVertex(currentNearOffset, -0.5, currentTopHeight), projectStairVertex(currentFarOffset, -0.5, currentTopHeight), projectStairVertex(currentFarOffset, 0.5, currentTopHeight), projectStairVertex(currentNearOffset, 0.5, currentTopHeight)];
    const currentSideFaces = currentTopPoints.map((currentFirstPoint, currentPointIndex) => {
      const currentSecondPoint = currentTopPoints[(currentPointIndex + 1) % 4], currentFaceDrop = (currentTopHeight - currentLowerHeight) * currentRenderOptions.elevationHeight + currentRenderOptions.baseThickness;
      return { points: [currentFirstPoint, currentSecondPoint, { x: currentSecondPoint.x, y: currentSecondPoint.y + currentFaceDrop }, { x: currentFirstPoint.x, y: currentFirstPoint.y + currentFaceDrop }], top: false };
    });
    return { order: (currentViewDirection.column + currentViewDirection.row) * (currentNearOffset + currentFarOffset) / 2, faces: [...currentSideFaces, { points: currentTopPoints, top: true }] };
  }).sort((currentFirstBlock, currentSecondBlock) => currentFirstBlock.order - currentSecondBlock.order).flatMap((currentStepBlock) => currentStepBlock.faces);
}
function containsSurfacePoint(currentScreenPoint, currentPolygonPoints) {
  let currentInsideValue = false;
  for (let currentPointIndex = 0, previousPointIndex = currentPolygonPoints.length - 1; currentPointIndex < currentPolygonPoints.length; previousPointIndex = currentPointIndex++) {
    const currentVertexPoint = currentPolygonPoints[currentPointIndex], previousVertexPoint = currentPolygonPoints[previousPointIndex];
    if (currentVertexPoint.y > currentScreenPoint.y !== previousVertexPoint.y > currentScreenPoint.y && currentScreenPoint.x < (previousVertexPoint.x - currentVertexPoint.x) * (currentScreenPoint.y - currentVertexPoint.y) / (previousVertexPoint.y - currentVertexPoint.y) + currentVertexPoint.x) currentInsideValue = !currentInsideValue;
  }
  return currentInsideValue;
}
function resolveCliffTextureScale(currentRenderOptions, currentTextureWidth, currentTextureHeight) {
  if (!Number.isFinite(currentTextureWidth) || !Number.isFinite(currentTextureHeight) || currentTextureWidth <= 0 || currentTextureHeight <= 0) throw new Error("\uC554\uBCBD \uD14D\uC2A4\uCC98 \uD06C\uAE30\uB294 \uC591\uC218\uC5EC\uC57C \uD569\uB2C8\uB2E4.");
  return { scaleX: currentRenderOptions.tileWidth / (2 * currentTextureWidth), scaleY: currentRenderOptions.elevationHeight / currentTextureHeight };
}
var CHARACTER_OUTLINE_STYLE = Object.freeze({ color: 16774084, cssColor: "#fff3c4", width: 5, outerStrength: 4, quality: 0.1 });

// packages/field-renderer/field-renderer.mjs
var FIELD_RENDERER_VERSION = "1.0.3";
var FIELD_MESH_BOUNDARY_STYLE = Object.freeze({ color: 14476783, width: 1, alpha: 0.9 });
var FIELD_SAFE_TOWER_PROFILE = Object.freeze({ anchorX: 627, anchorY: 1095, bodyTop: 82, displayHeight: 112 });
var FIELD_SAFE_AURA_PROFILE = Object.freeze({ columns: 4, rows: 2, frames: 8, height: 15, alpha: 0.7, frameDuration: 120, horizontalCrop: 0.02, topCrop: 0.25, bottomCrop: 0.1 });
var FIELD_QUAD_TRIANGLES = [0, 1, 2, 0, 2, 3];
var FIELD_CELL_CORNERS = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]];
var FIELD_BOUNDARY_NEIGHBORS = [{ column: 1, row: 0, edge: [1, 2] }, { column: 0, row: 1, edge: [2, 3] }, { column: -1, row: 0, edge: [3, 0] }, { column: 0, row: -1, edge: [0, 1] }];
var FIELD_CONNECTION_SHAPE = Object.freeze({ inset: 0.08, radius: 0.2, half: 0.5 });
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
function buildFieldCellGeometry(currentCellPosition, currentMapSurface, currentRenderOptions = FIELD_RENDER_METRICS) {
  const currentStairRecord = findSurfaceStair(currentCellPosition, currentMapSurface);
  if (currentStairRecord) return buildSurfaceStairs(currentStairRecord, currentMapSurface, currentRenderOptions).map((currentFaceRecord) => ({ ...currentFaceRecord, kind: currentFaceRecord.top ? "tread" : "cliff" }));
  const currentScreenCenter = projectSurfaceCell(currentCellPosition, currentMapSurface, currentRenderOptions);
  const currentGroundPoints = FIELD_CELL_CORNERS.map(([currentColumnOffset, currentRowOffset]) => ({ x: currentScreenCenter.x + (currentColumnOffset - currentRowOffset) * currentRenderOptions.tileWidth / 2, y: currentScreenCenter.y + (currentColumnOffset + currentRowOffset) * currentRenderOptions.tileHeight / 2 }));
  return [...buildSurfaceCliffs(currentCellPosition, currentMapSurface, currentRenderOptions).map((currentFacePoints) => ({ points: currentFacePoints, top: false, kind: "cliff" })), { points: currentGroundPoints, top: true, kind: "ground" }];
}
function buildFieldPanelVertices(currentPanelPoints) {
  if (currentPanelPoints.length !== 4 || currentPanelPoints.some((currentPointValue) => !Number.isFinite(currentPointValue.x) || !Number.isFinite(currentPointValue.y))) throw Error("\uD544\uB4DC \uD328\uB110\uC740 \uC720\uD6A8\uD55C \uAF2D\uC9D3\uC810 4\uAC1C\uC5EC\uC57C \uD569\uB2C8\uB2E4.");
  const currentPanelCenter = { x: currentPanelPoints.reduce((currentPointSum, currentPointValue) => currentPointSum + currentPointValue.x, 0) / 4, y: currentPanelPoints.reduce((currentPointSum, currentPointValue) => currentPointSum + currentPointValue.y, 0) / 4 };
  return { center: currentPanelCenter, vertices: FIELD_QUAD_TRIANGLES.flatMap((currentPointIndex) => [currentPanelPoints[currentPointIndex].x - currentPanelCenter.x, currentPanelCenter.y - currentPanelPoints[currentPointIndex].y]) };
}
function drawFieldMeshBoundary(currentGameScene, currentPanelPoints, currentRenderDepth) {
  const currentMeshGraphic = currentGameScene.add.graphics().setDepth(currentRenderDepth);
  currentMeshGraphic.lineStyle(FIELD_MESH_BOUNDARY_STYLE.width, FIELD_MESH_BOUNDARY_STYLE.color, FIELD_MESH_BOUNDARY_STYLE.alpha);
  currentMeshGraphic.strokePoints(currentPanelPoints, true);
  currentMeshGraphic.lineBetween(currentPanelPoints[0].x, currentPanelPoints[0].y, currentPanelPoints[2].x, currentPanelPoints[2].y);
  return currentMeshGraphic;
}
function drawFieldTexturePanel(currentGameScene, currentPanelPoints, currentTextureKey, currentRenderDepth, currentUvCorners = [0, 0, 1, 0, 1, 1, 0, 1]) {
  if (!currentGameScene.textures.exists(currentTextureKey)) throw Error("\uD544\uB4DC \uD14D\uC2A4\uCC98 \uB204\uB77D: " + currentTextureKey);
  const currentPanelGeometry = buildFieldPanelVertices(currentPanelPoints);
  const currentPanelUvs = FIELD_QUAD_TRIANGLES.flatMap((currentPointIndex) => currentUvCorners.slice(currentPointIndex * 2, currentPointIndex * 2 + 2));
  const currentPanelMesh = currentGameScene.add.mesh(currentPanelGeometry.center.x, currentPanelGeometry.center.y, currentTextureKey, void 0, currentPanelGeometry.vertices, currentPanelUvs);
  currentPanelMesh.hideCCW = false;
  currentPanelMesh.ignoreDirtyCache = true;
  currentPanelMesh.setOrtho(currentPanelMesh.width, currentPanelMesh.height);
  currentPanelMesh.setDepth(currentRenderDepth);
  return currentPanelMesh;
}
function drawFieldCellObjects(currentGameScene, currentCellPosition, currentMapSurface, currentRenderOptions, currentTextureKeys, currentRenderDepth, currentShowMesh = false) {
  const currentCellFaces = buildFieldCellGeometry(currentCellPosition, currentMapSurface, currentRenderOptions);
  const currentTreadCount = currentCellFaces.filter((currentFaceRecord) => currentFaceRecord.kind === "tread").length;
  const currentRenderObjects = [];
  for (const [currentFaceIndex, currentFaceRecord] of currentCellFaces.entries()) {
    const currentFaceDepth = currentRenderDepth + currentFaceIndex / (currentCellFaces.length + 1);
    const currentTextureKey = currentTextureKeys[currentFaceRecord.kind];
    if (!currentGameScene.textures.exists(currentTextureKey)) throw Error("\uD544\uB4DC \uD14D\uC2A4\uCC98 \uB204\uB77D: " + currentTextureKey);
    if (currentFaceRecord.kind === "cliff") {
      const currentSourceImage = currentGameScene.textures.get(currentTextureKey).getSourceImage();
      const currentTextureScale = resolveCliffTextureScale(currentRenderOptions, currentSourceImage.width, currentSourceImage.height);
      const currentMinimumX = Math.min(...currentFaceRecord.points.map((currentPointValue) => currentPointValue.x)), currentMaximumX = Math.max(...currentFaceRecord.points.map((currentPointValue) => currentPointValue.x));
      const currentMinimumY = Math.min(...currentFaceRecord.points.map((currentPointValue) => currentPointValue.y)), currentMaximumY = Math.max(...currentFaceRecord.points.map((currentPointValue) => currentPointValue.y));
      const currentWallSprite = currentGameScene.add.tileSprite(currentMinimumX, currentMinimumY, Math.max(1, currentMaximumX - currentMinimumX), Math.max(1, currentMaximumY - currentMinimumY), currentTextureKey).setOrigin(0).setDepth(currentFaceDepth);
      currentWallSprite.setTileScale(currentTextureScale.scaleX, currentTextureScale.scaleY);
      const currentWallMask = currentGameScene.add.graphics().setVisible(false);
      currentWallMask.fillPoints(currentFaceRecord.points, true);
      currentWallSprite.setMask(currentWallMask.createGeometryMask());
      currentRenderObjects.push(currentWallSprite, currentWallMask);
    } else {
      const currentUvCorners = currentFaceRecord.kind === "tread" ? [0, 0, 1 / currentTreadCount, 0, 1 / currentTreadCount, 1, 0, 1] : void 0;
      if (currentFaceRecord.kind === "ground" && currentTextureKeys.underlay) currentRenderObjects.push(drawFieldTexturePanel(currentGameScene, currentFaceRecord.points, currentTextureKeys.underlay, currentFaceDepth));
      currentRenderObjects.push(drawFieldTexturePanel(currentGameScene, currentFaceRecord.points, currentTextureKey, currentFaceDepth + 1e-3, currentUvCorners));
    }
    if (currentShowMesh) currentRenderObjects.push(drawFieldMeshBoundary(currentGameScene, currentFaceRecord.points, currentFaceDepth + 2e-3));
  }
  return currentRenderObjects;
}
function buildFieldBoundaryPanels(currentCellPosition, currentSafeCenter, currentSafeRadius, currentScreenCenter, currentRenderOptions = FIELD_RENDER_METRICS) {
  if (!Number.isInteger(currentSafeRadius) || currentSafeRadius < 0) throw Error("\uACB0\uACC4 \uBC18\uACBD\uC740 0 \uC774\uC0C1\uC758 \uC815\uC218\uC5EC\uC57C \uD569\uB2C8\uB2E4.");
  const currentCenterDistance = Math.abs(currentCellPosition.column - currentSafeCenter.column) + Math.abs(currentCellPosition.row - currentSafeCenter.row);
  if (currentCenterDistance > currentSafeRadius) return [];
  const currentCellPoints = [{ x: currentScreenCenter.x, y: currentScreenCenter.y - currentRenderOptions.tileHeight / 2 }, { x: currentScreenCenter.x + currentRenderOptions.tileWidth / 2, y: currentScreenCenter.y }, { x: currentScreenCenter.x, y: currentScreenCenter.y + currentRenderOptions.tileHeight / 2 }, { x: currentScreenCenter.x - currentRenderOptions.tileWidth / 2, y: currentScreenCenter.y }];
  return FIELD_BOUNDARY_NEIGHBORS.filter((currentNeighborRecord) => Math.abs(currentCellPosition.column + currentNeighborRecord.column - currentSafeCenter.column) + Math.abs(currentCellPosition.row + currentNeighborRecord.row - currentSafeCenter.row) > currentSafeRadius).map((currentNeighborRecord) => {
    const [currentFirstPoint, currentSecondPoint] = currentNeighborRecord.edge.map((currentPointIndex) => currentCellPoints[currentPointIndex]);
    return [{ x: currentFirstPoint.x, y: currentFirstPoint.y - FIELD_SAFE_AURA_PROFILE.height }, { x: currentSecondPoint.x, y: currentSecondPoint.y - FIELD_SAFE_AURA_PROFILE.height }, currentSecondPoint, currentFirstPoint];
  });
}
function resolveFieldAuraUvs(currentFrameIndex, currentImageWidth, currentImageHeight) {
  if (!Number.isInteger(currentFrameIndex) || currentFrameIndex < 0 || currentFrameIndex >= FIELD_SAFE_AURA_PROFILE.frames) throw Error("\uACB0\uACC4 \uD504\uB808\uC784 \uBC94\uC704 \uC624\uB958");
  const currentColumnIndex = currentFrameIndex % FIELD_SAFE_AURA_PROFILE.columns, currentRowIndex = Math.floor(currentFrameIndex / FIELD_SAFE_AURA_PROFILE.columns);
  const currentLeftPixel = Math.round(currentColumnIndex * currentImageWidth / FIELD_SAFE_AURA_PROFILE.columns), currentRightPixel = Math.round((currentColumnIndex + 1) * currentImageWidth / FIELD_SAFE_AURA_PROFILE.columns);
  const currentTopPixel = Math.round(currentRowIndex * currentImageHeight / FIELD_SAFE_AURA_PROFILE.rows), currentBottomPixel = Math.round((currentRowIndex + 1) * currentImageHeight / FIELD_SAFE_AURA_PROFILE.rows);
  const currentCropPixels = (currentRightPixel - currentLeftPixel) * FIELD_SAFE_AURA_PROFILE.horizontalCrop;
  const currentLeftUv = (currentLeftPixel + currentCropPixels) / currentImageWidth, currentRightUv = (currentRightPixel - currentCropPixels) / currentImageWidth, currentTopUv = (currentTopPixel + (currentBottomPixel - currentTopPixel) * FIELD_SAFE_AURA_PROFILE.topCrop) / currentImageHeight, currentBottomUv = (currentBottomPixel - (currentBottomPixel - currentTopPixel) * FIELD_SAFE_AURA_PROFILE.bottomCrop) / currentImageHeight;
  return [currentLeftUv, currentTopUv, currentRightUv, currentTopUv, currentRightUv, currentBottomUv, currentLeftUv, currentBottomUv];
}
function drawFieldAuraPanel(currentGameScene, currentPanelPoints, currentTextureKey, currentRenderDepth) {
  const currentSourceImage = currentGameScene.textures.get(currentTextureKey).getSourceImage();
  const currentAuraMesh = drawFieldTexturePanel(currentGameScene, currentPanelPoints, currentTextureKey, currentRenderDepth, resolveFieldAuraUvs(0, currentSourceImage.width, currentSourceImage.height));
  currentAuraMesh.setAlpha(FIELD_SAFE_AURA_PROFILE.alpha);
  const synchronizeFieldAura = (currentTimeMilliseconds) => {
    const currentFrameIndex = Math.floor(currentTimeMilliseconds / FIELD_SAFE_AURA_PROFILE.frameDuration) % FIELD_SAFE_AURA_PROFILE.frames;
    const currentUvCorners = resolveFieldAuraUvs(currentFrameIndex, currentSourceImage.width, currentSourceImage.height);
    for (const [currentVertexIndex, currentCornerIndex] of FIELD_QUAD_TRIANGLES.entries()) {
      const currentMeshVertex = currentAuraMesh.vertices[currentVertexIndex];
      currentMeshVertex.u = currentMeshVertex.tu = currentUvCorners[currentCornerIndex * 2];
      currentMeshVertex.v = currentMeshVertex.tv = currentUvCorners[currentCornerIndex * 2 + 1];
    }
  };
  currentGameScene.events.on("update", synchronizeFieldAura);
  currentAuraMesh.once("destroy", () => currentGameScene.events.off("update", synchronizeFieldAura));
  return currentAuraMesh;
}
function drawFieldTowerObject(currentGameScene, currentScreenPosition, currentTextureKey, currentRenderDepth = 0) {
  if (!currentGameScene.textures.exists(currentTextureKey)) throw Error("\uACB0\uACC4\uD0D1 \uD14D\uC2A4\uCC98 \uB204\uB77D");
  const currentTowerImage = currentGameScene.add.image(currentScreenPosition.x, currentScreenPosition.y, currentTextureKey);
  return currentTowerImage.setOrigin(FIELD_SAFE_TOWER_PROFILE.anchorX / currentTowerImage.width, FIELD_SAFE_TOWER_PROFILE.anchorY / currentTowerImage.height).setScale(FIELD_SAFE_TOWER_PROFILE.displayHeight / (FIELD_SAFE_TOWER_PROFILE.anchorY - FIELD_SAFE_TOWER_PROFILE.bodyTop)).setDepth(currentRenderDepth);
}
export {
  FIELD_MESH_BOUNDARY_STYLE,
  FIELD_RENDERER_VERSION,
  FIELD_RENDER_METRICS,
  FIELD_SAFE_AURA_PROFILE,
  FIELD_SAFE_TOWER_PROFILE,
  buildFieldBoundaryPanels,
  buildFieldCellGeometry,
  buildFieldPanelVertices,
  containsSurfacePoint,
  drawFieldAuraPanel,
  drawFieldCellObjects,
  drawFieldMeshBoundary,
  drawFieldTexturePanel,
  drawFieldTowerObject,
  prepareFieldConnectedTexture,
  projectSurfaceCell,
  projectSurfaceVertex,
  resolveFieldAuraUvs,
  rotateSurfacePosition
};
