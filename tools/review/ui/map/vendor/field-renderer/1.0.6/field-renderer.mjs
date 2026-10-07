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
var FIELD_RENDERER_VERSION = "1.0.6";
var FIELD_ELEVATION_EDGE_STYLE = Object.freeze({ color: 5327677, width: 2, alpha: 0.85 });
var FIELD_MESH_BOUNDARY_STYLE = Object.freeze({ color: 14476783, width: 1, alpha: 0.9 });
var FIELD_ACTOR_CONTACT_SHADOW_PROFILES = Object.freeze({
  baseline: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.3, coreAlpha: 0.24, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  contrast: Object.freeze({ width: 0.4, height: 0.32, alpha: 0.36, coreAlpha: 0.3, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 }),
  broad: Object.freeze({ width: 0.44, height: 0.34, alpha: 0.32, coreAlpha: 0.26, coreScale: 0.65, scale: 1.3, opacityScale: 1.5 })
});
var FIELD_ACTOR_CONTACT_SHADOW_COLOR = 1587502;
var FIELD_SAFE_TOWER_PROFILE = Object.freeze({ anchorX: 627, anchorY: 1095, bodyTop: 82, displayHeight: 112 });
var FIELD_SAFE_AURA_PROFILE = Object.freeze({ columns: 4, rows: 2, frames: 8, height: 15, alpha: 0.7, frameDuration: 120, horizontalCrop: 0.02, topCrop: 0.25, bottomCrop: 0.1 });
var FIELD_EDGE_COORDINATE_EPSILON = 1e-6;
var FIELD_QUAD_TRIANGLES = [0, 1, 2, 0, 2, 3];
var FIELD_CELL_CORNERS = [[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]];
var FIELD_BOUNDARY_NEIGHBORS = [{ column: 1, row: 0, edge: [1, 2] }, { column: 0, row: 1, edge: [2, 3] }, { column: -1, row: 0, edge: [3, 0] }, { column: 0, row: -1, edge: [0, 1] }];
var FIELD_CONNECTION_SHAPE = Object.freeze({ inset: 0.08, radius: 0.2, half: 0.5 });
function resolveFieldActorContactShadow(currentShadowProfileName = "contrast") {
  const currentShadowProfile = FIELD_ACTOR_CONTACT_SHADOW_PROFILES[currentShadowProfileName];
  if (!currentShadowProfile) throw Error("\uC9C0\uC6D0\uD558\uC9C0 \uC54A\uB294 \uC811\uC9C0 \uADF8\uB9BC\uC790 \uD504\uB85C\uD544: " + currentShadowProfileName);
  const currentShadowWidth = FIELD_RENDER_METRICS.tileWidth * currentShadowProfile.width * currentShadowProfile.scale;
  const currentShadowHeight = FIELD_RENDER_METRICS.tileHeight * currentShadowProfile.height * currentShadowProfile.scale;
  return { color: FIELD_ACTOR_CONTACT_SHADOW_COLOR, outer: { width: currentShadowWidth, height: currentShadowHeight, alpha: currentShadowProfile.alpha * currentShadowProfile.opacityScale }, core: { width: currentShadowWidth * currentShadowProfile.coreScale, height: currentShadowHeight * currentShadowProfile.coreScale, alpha: currentShadowProfile.coreAlpha * currentShadowProfile.opacityScale } };
}
function drawFieldActorContactShadow(currentShadowGraphics, currentScreenPosition, currentShadowProfileName = "contrast") {
  const currentShadowMetrics = resolveFieldActorContactShadow(currentShadowProfileName);
  currentShadowGraphics.fillStyle(currentShadowMetrics.color, currentShadowMetrics.outer.alpha);
  currentShadowGraphics.fillEllipse(currentScreenPosition.x, currentScreenPosition.y, currentShadowMetrics.outer.width, currentShadowMetrics.outer.height);
  currentShadowGraphics.fillStyle(currentShadowMetrics.color, currentShadowMetrics.core.alpha);
  currentShadowGraphics.fillEllipse(currentScreenPosition.x, currentScreenPosition.y, currentShadowMetrics.core.width, currentShadowMetrics.core.height);
  return currentShadowMetrics;
}
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
function buildFieldElevationEdges(currentCellPosition, currentMapSurface, currentRenderOptions = FIELD_RENDER_METRICS) {
  if (findSurfaceStair(currentCellPosition, currentMapSurface)) return [];
  const currentCellHeight = readSurfaceHeight(currentCellPosition, currentMapSurface);
  const currentCornerPoints = FIELD_CELL_CORNERS.map(([currentColumnOffset, currentRowOffset]) => projectSurfaceVertex({ column: currentCellPosition.column + currentColumnOffset, row: currentCellPosition.row + currentRowOffset, height: currentCellHeight * currentRenderOptions.elevationHeight }, currentRenderOptions));
  return FIELD_BOUNDARY_NEIGHBORS.flatMap((currentNeighborOffset) => {
    const currentNeighborCell = { column: currentCellPosition.column + currentNeighborOffset.column, row: currentCellPosition.row + currentNeighborOffset.row };
    if (currentNeighborCell.column < 0 || currentNeighborCell.row < 0 || currentNeighborCell.column >= currentMapSurface.columns || currentNeighborCell.row >= currentMapSurface.rows || (readSurfaceHeight(currentNeighborCell, currentMapSurface) > currentCellHeight || readSurfaceHeight(currentNeighborCell, currentMapSurface) === currentCellHeight && !findSurfaceStair(currentNeighborCell, currentMapSurface))) return [];
    return [currentNeighborOffset.edge.map((currentCornerIndex) => currentCornerPoints[currentCornerIndex])];
  });
}
function buildFieldRoadEdges(currentCellPosition, currentMapSurface, currentConnectionMask, currentRenderOptions = FIELD_RENDER_METRICS, currentFullTileRoad = false) {
  const currentCellCenter = projectSurfaceCell(currentCellPosition, currentMapSurface, currentRenderOptions);
  const currentInsetValue = currentFullTileRoad ? 0 : FIELD_CONNECTION_SHAPE.inset, currentCornerRadius = currentFullTileRoad ? 0 : FIELD_CONNECTION_SHAPE.radius;
  const currentCurveSteps = 8;
  const currentRoadSegments = [];
  for (let currentCornerIndex = 0; currentCornerIndex < 4; currentCornerIndex++) {
    const currentFirstConnected = Boolean(currentConnectionMask & 1 << currentCornerIndex);
    const currentSecondConnected = Boolean(currentConnectionMask & 1 << (currentCornerIndex + 1) % 4);
    if (currentFirstConnected && currentSecondConnected) continue;
    let currentCornerPoints;
    if (currentFirstConnected) currentCornerPoints = [[1 - currentInsetValue, 0], [1 - currentInsetValue, 0.5]];
    else if (currentSecondConnected) currentCornerPoints = [[0.5, currentInsetValue], [1, currentInsetValue]];
    else {
      currentCornerPoints = [[0.5, currentInsetValue]];
      for (let currentCurveIndex = 0; currentCurveIndex <= currentCurveSteps; currentCurveIndex++) {
        const currentCurveAngle = -Math.PI / 2 + Math.PI / 2 * currentCurveIndex / currentCurveSteps;
        currentCornerPoints.push([1 - currentInsetValue - currentCornerRadius + Math.cos(currentCurveAngle) * currentCornerRadius, currentInsetValue + currentCornerRadius + Math.sin(currentCurveAngle) * currentCornerRadius]);
      }
      currentCornerPoints.push([1 - currentInsetValue, 0.5]);
    }
    const currentProjectedPoints = currentCornerPoints.map((currentCornerPoint) => {
      let [currentTextureColumn, currentTextureRow] = currentCornerPoint;
      for (let currentRotationIndex = 0; currentRotationIndex < currentCornerIndex; currentRotationIndex++) [currentTextureColumn, currentTextureRow] = [1 - currentTextureRow, currentTextureColumn];
      return { x: currentCellCenter.x + (currentTextureColumn - currentTextureRow) * currentRenderOptions.tileWidth / 2, y: currentCellCenter.y + (currentTextureColumn + currentTextureRow - 1) * currentRenderOptions.tileHeight / 2 };
    });
    for (let currentPointIndex = 1; currentPointIndex < currentProjectedPoints.length; currentPointIndex++) currentRoadSegments.push([currentProjectedPoints[currentPointIndex - 1], currentProjectedPoints[currentPointIndex]]);
  }
  return currentRoadSegments;
}
function drawFieldElevationOutline(currentGameScene, currentEdgeSegments, currentRenderDepth) {
  const currentEdgeGraphic = currentGameScene.add.graphics().setDepth(currentRenderDepth);
  let previousStrokeWidth = null;
  const synchronizeElevationWidth = () => {
    const currentStrokeWidth = FIELD_ELEVATION_EDGE_STYLE.width * currentGameScene.scale.displayScale.x / currentGameScene.cameras.main.zoom;
    if (currentStrokeWidth === previousStrokeWidth) return;
    previousStrokeWidth = currentStrokeWidth;
    currentEdgeGraphic.clear();
    currentEdgeGraphic.lineStyle(currentStrokeWidth, FIELD_ELEVATION_EDGE_STYLE.color, FIELD_ELEVATION_EDGE_STYLE.alpha);
    for (const [currentStartPoint, currentEndPoint] of currentEdgeSegments) currentEdgeGraphic.lineBetween(currentStartPoint.x, currentStartPoint.y, currentEndPoint.x, currentEndPoint.y);
  };
  synchronizeElevationWidth();
  currentGameScene.events.on("postupdate", synchronizeElevationWidth);
  currentEdgeGraphic.once("destroy", () => currentGameScene.events.off("postupdate", synchronizeElevationWidth));
  return currentEdgeGraphic;
}
function buildFieldCliffEdges(currentCellPosition, currentMapSurface, currentFacePoints, currentRenderOptions = FIELD_RENDER_METRICS) {
  const currentEdgeSegments = currentFacePoints.map((currentStartPoint, currentPointIndex) => [currentStartPoint, currentFacePoints[(currentPointIndex + 1) % 4]]);
  if (findSurfaceStair(currentCellPosition, currentMapSurface)) return currentEdgeSegments;
  const currentTopVector = { x: currentFacePoints[1].x - currentFacePoints[0].x, y: currentFacePoints[1].y - currentFacePoints[0].y };
  const currentNeighborFaces = FIELD_BOUNDARY_NEIGHBORS.flatMap((currentNeighborOffset) => {
    const currentNeighborCell = { column: currentCellPosition.column + currentNeighborOffset.column, row: currentCellPosition.row + currentNeighborOffset.row };
    if (currentNeighborCell.column < 0 || currentNeighborCell.row < 0 || currentNeighborCell.column >= currentMapSurface.columns || currentNeighborCell.row >= currentMapSurface.rows || findSurfaceStair(currentNeighborCell, currentMapSurface)) return [];
    return buildSurfaceCliffs(currentNeighborCell, currentMapSurface, currentRenderOptions);
  });
  return currentEdgeSegments.flatMap(([currentStartPoint, currentEndPoint], currentEdgeIndex) => {
    if (currentEdgeIndex % 2 === 0) return [[currentStartPoint, currentEndPoint]];
    let currentVisibleRanges = [[Math.min(currentStartPoint.y, currentEndPoint.y), Math.max(currentStartPoint.y, currentEndPoint.y)]];
    for (const currentNeighborPoints of currentNeighborFaces) {
      const currentNeighborVector = { x: currentNeighborPoints[1].x - currentNeighborPoints[0].x, y: currentNeighborPoints[1].y - currentNeighborPoints[0].y };
      if (Math.abs(currentTopVector.x * currentNeighborVector.y - currentTopVector.y * currentNeighborVector.x) > FIELD_EDGE_COORDINATE_EPSILON) continue;
      for (const currentNeighborIndex of [1, 3]) {
        const currentNeighborStart = currentNeighborPoints[currentNeighborIndex], currentNeighborEnd = currentNeighborPoints[(currentNeighborIndex + 1) % 4];
        if (Math.abs(currentNeighborStart.x - currentStartPoint.x) > FIELD_EDGE_COORDINATE_EPSILON) continue;
        const currentRangeLower = Math.min(currentNeighborStart.y, currentNeighborEnd.y), currentRangeUpper = Math.max(currentNeighborStart.y, currentNeighborEnd.y);
        currentVisibleRanges = currentVisibleRanges.flatMap(([currentLowerValue, currentUpperValue]) => {
          if (currentRangeUpper <= currentLowerValue || currentRangeLower >= currentUpperValue) return [[currentLowerValue, currentUpperValue]];
          return [[currentLowerValue, Math.min(currentUpperValue, currentRangeLower)], [Math.max(currentLowerValue, currentRangeUpper), currentUpperValue]].filter(([currentFromValue, currentToValue]) => currentToValue - currentFromValue > FIELD_EDGE_COORDINATE_EPSILON);
        });
      }
    }
    return currentVisibleRanges.map(([currentLowerValue, currentUpperValue]) => [{ x: currentStartPoint.x, y: currentLowerValue }, { x: currentStartPoint.x, y: currentUpperValue }]);
  });
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
    if (currentFaceRecord.kind === "tread" || currentFaceRecord.kind === "cliff") {
      const currentFaceSegments = currentFaceRecord.kind === "cliff" ? buildFieldCliffEdges(currentCellPosition, currentMapSurface, currentFaceRecord.points, currentRenderOptions) : currentFaceRecord.points.map((currentStartPoint, currentPointIndex) => [currentStartPoint, currentFaceRecord.points[(currentPointIndex + 1) % currentFaceRecord.points.length]]);
      currentRenderObjects.push(drawFieldElevationOutline(currentGameScene, currentFaceSegments, currentFaceDepth + 2e-3));
    }
    if (currentShowMesh) currentRenderObjects.push(drawFieldMeshBoundary(currentGameScene, currentFaceRecord.points, currentFaceDepth + 2e-3));
  }
  if (currentTextureKeys.roadConnectionMask !== void 0 && !findSurfaceStair(currentCellPosition, currentMapSurface)) {
    const currentRoadEdges = buildFieldRoadEdges(currentCellPosition, currentMapSurface, currentTextureKeys.roadConnectionMask, currentRenderOptions, currentTextureKeys.fullTileRoad);
    if (currentRoadEdges.length) currentRenderObjects.push(drawFieldElevationOutline(currentGameScene, currentRoadEdges, currentRenderDepth + 0.98));
  }
  const currentElevationEdges = buildFieldElevationEdges(currentCellPosition, currentMapSurface, currentRenderOptions);
  if (currentElevationEdges.length) currentRenderObjects.push(drawFieldElevationOutline(currentGameScene, currentElevationEdges, currentRenderDepth + 0.99));
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
  FIELD_ACTOR_CONTACT_SHADOW_COLOR,
  FIELD_ACTOR_CONTACT_SHADOW_PROFILES,
  FIELD_ELEVATION_EDGE_STYLE,
  FIELD_MESH_BOUNDARY_STYLE,
  FIELD_RENDERER_VERSION,
  FIELD_RENDER_METRICS,
  FIELD_SAFE_AURA_PROFILE,
  FIELD_SAFE_TOWER_PROFILE,
  buildFieldBoundaryPanels,
  buildFieldCellGeometry,
  buildFieldCliffEdges,
  buildFieldElevationEdges,
  buildFieldPanelVertices,
  buildFieldRoadEdges,
  containsSurfacePoint,
  drawFieldActorContactShadow,
  drawFieldAuraPanel,
  drawFieldCellObjects,
  drawFieldElevationOutline,
  drawFieldMeshBoundary,
  drawFieldTexturePanel,
  drawFieldTowerObject,
  prepareFieldConnectedTexture,
  projectSurfaceCell,
  projectSurfaceVertex,
  resolveFieldActorContactShadow,
  resolveFieldAuraUvs,
  rotateSurfacePosition
};
