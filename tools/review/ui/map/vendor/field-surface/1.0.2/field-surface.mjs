/** 게임과 검수가 함께 사용하는 고도·투영 계약. 엔진과 DOM에 의존하지 않는다. */
export const FIELD_SURFACE_VERSION = '1.0.2';
export const FIELD_RENDER_METRICS = Object.freeze({tileWidth:80,tileHeight:40,elevationHeight:32,baseThickness:16});
const TERRAIN_STAIR_COUNT = 6;
export function readSurfaceHeight(currentCellPosition,currentMapSurface){
 if(currentCellPosition.column<0||currentCellPosition.row<0||currentCellPosition.column>=currentMapSurface.columns||currentCellPosition.row>=currentMapSurface.rows)return 0;
 if(currentMapSurface.heightSource)return readSurfaceHeight(currentMapSurface.heightSource.position(currentCellPosition),currentMapSurface.heightSource.surface);
 return currentMapSurface.elevations?.[currentCellPosition.row]?.[currentCellPosition.column]??0;
}
export function rotateSurfacePosition(currentCellPosition,currentQuarterTurns=0){
 let currentColumnValue=currentCellPosition.column,currentRowValue=currentCellPosition.row;
 for(let currentTurnIndex=0;currentTurnIndex<((currentQuarterTurns%4)+4)%4;currentTurnIndex++)[currentColumnValue,currentRowValue]=[-currentRowValue,currentColumnValue];
 return {column:currentColumnValue,row:currentRowValue};
}
export function projectSurfaceVertex(currentVertexPosition,currentRenderOptions){
 const currentRotatedPosition=rotateSurfacePosition(currentVertexPosition,currentRenderOptions.rotation??0);
 return {x:(currentRenderOptions.originX??0)+(currentRotatedPosition.column-currentRotatedPosition.row)*currentRenderOptions.tileWidth/2,y:(currentRenderOptions.originY??0)+(currentRotatedPosition.column+currentRotatedPosition.row)*currentRenderOptions.tileHeight/2-(currentVertexPosition.height??0)};
}
export function findSurfaceStair(currentCellPosition,currentMapSurface){
 return currentMapSurface.elevationTileIndex?currentMapSurface.elevationTileIndex.get(`${currentCellPosition.column},${currentCellPosition.row}`):currentMapSurface.elevationTiles?.find(currentStairRecord=>currentStairRecord.cell.column===currentCellPosition.column&&currentStairRecord.cell.row===currentCellPosition.row);
}
export function projectSurfaceCell(currentCellPosition,currentMapSurface,currentRenderOptions){
 return projectSurfaceVertex({...currentCellPosition,height:(readSurfaceHeight(currentCellPosition,currentMapSurface)-(findSurfaceStair(currentCellPosition,currentMapSurface)?0.5:0))*currentRenderOptions.elevationHeight},currentRenderOptions);
}
export function buildSurfaceCliffs(currentCellPosition,currentMapSurface,currentRenderOptions){
 if(!currentMapSurface.elevations&&!currentMapSurface.heightSource)return [];
 const currentCenterPoint=projectSurfaceCell(currentCellPosition,currentMapSurface,currentRenderOptions),currentHeightValue=readSurfaceHeight(currentCellPosition,currentMapSurface);
 const currentVisibleEdges=[{direction:{column:1,row:0},edge:[[0,currentRenderOptions.tileHeight/2],[currentRenderOptions.tileWidth/2,0]]},{direction:{column:0,row:1},edge:[[-currentRenderOptions.tileWidth/2,0],[0,currentRenderOptions.tileHeight/2]]}];
 return currentVisibleEdges.flatMap(currentEdgeRecord=>{
  const currentNeighborOffset=rotateSurfacePosition(currentEdgeRecord.direction,-(currentRenderOptions.rotation??0));
  const currentNeighborCell={column:currentCellPosition.column+currentNeighborOffset.column,row:currentCellPosition.row+currentNeighborOffset.row};
  const currentNeighborInside=currentNeighborCell.column>=0&&currentNeighborCell.row>=0&&currentNeighborCell.column<currentMapSurface.columns&&currentNeighborCell.row<currentMapSurface.rows;
  const currentHeightDrop=currentNeighborInside?(currentHeightValue-readSurfaceHeight(currentNeighborCell,currentMapSurface))*currentRenderOptions.elevationHeight:currentHeightValue*currentRenderOptions.elevationHeight+currentRenderOptions.baseThickness;
  if(currentHeightDrop<=0)return [];
  const [currentFirstPoint,currentSecondPoint]=currentEdgeRecord.edge.map(([currentOffsetX,currentOffsetY])=>({x:currentCenterPoint.x+currentOffsetX,y:currentCenterPoint.y+currentOffsetY}));
  return [[currentFirstPoint,currentSecondPoint,{x:currentSecondPoint.x,y:currentSecondPoint.y+currentHeightDrop},{x:currentFirstPoint.x,y:currentFirstPoint.y+currentHeightDrop}]];
 });
}
export function buildSurfaceStairs(currentStairRecord,currentMapSurface,currentRenderOptions){
 const currentColumnDelta=currentStairRecord.cell.column-currentStairRecord.lower.column,currentRowDelta=currentStairRecord.cell.row-currentStairRecord.lower.row;
 const currentLowerHeight=readSurfaceHeight(currentStairRecord.cell,currentMapSurface)-1;
 const currentViewDirection=rotateSurfacePosition({column:currentColumnDelta,row:currentRowDelta},currentRenderOptions.rotation??0);
 const projectStairVertex=(currentAlongOffset,currentAcrossOffset,currentHeightValue)=>projectSurfaceVertex({column:currentStairRecord.cell.column+currentColumnDelta*currentAlongOffset-currentRowDelta*currentAcrossOffset,row:currentStairRecord.cell.row+currentRowDelta*currentAlongOffset+currentColumnDelta*currentAcrossOffset,height:currentHeightValue*currentRenderOptions.elevationHeight},currentRenderOptions);
 return Array.from({length:TERRAIN_STAIR_COUNT},(_,currentStepIndex)=>{
  const currentNearOffset=currentStepIndex/TERRAIN_STAIR_COUNT-.5,currentFarOffset=(currentStepIndex+1)/TERRAIN_STAIR_COUNT-.5,currentTopHeight=currentLowerHeight+(currentStepIndex+1)/TERRAIN_STAIR_COUNT;
  const currentTopPoints=[projectStairVertex(currentNearOffset,-.5,currentTopHeight),projectStairVertex(currentFarOffset,-.5,currentTopHeight),projectStairVertex(currentFarOffset,.5,currentTopHeight),projectStairVertex(currentNearOffset,.5,currentTopHeight)];
  const currentSideFaces=currentTopPoints.map((currentFirstPoint,currentPointIndex)=>{const currentSecondPoint=currentTopPoints[(currentPointIndex+1)%4],currentFaceDrop=(currentTopHeight-currentLowerHeight)*currentRenderOptions.elevationHeight+currentRenderOptions.baseThickness;return {points:[currentFirstPoint,currentSecondPoint,{x:currentSecondPoint.x,y:currentSecondPoint.y+currentFaceDrop},{x:currentFirstPoint.x,y:currentFirstPoint.y+currentFaceDrop}],top:false};});
  return {order:(currentViewDirection.column+currentViewDirection.row)*(currentNearOffset+currentFarOffset)/2,faces:[...currentSideFaces,{points:currentTopPoints,top:true}]};
 }).sort((currentFirstBlock,currentSecondBlock)=>currentFirstBlock.order-currentSecondBlock.order).flatMap(currentStepBlock=>currentStepBlock.faces);
}
export function containsSurfacePoint(currentScreenPoint,currentPolygonPoints){
 let currentInsideValue=false;
 for(let currentPointIndex=0,previousPointIndex=currentPolygonPoints.length-1;currentPointIndex<currentPolygonPoints.length;previousPointIndex=currentPointIndex++){
  const currentVertexPoint=currentPolygonPoints[currentPointIndex],previousVertexPoint=currentPolygonPoints[previousPointIndex];
  if((currentVertexPoint.y>currentScreenPoint.y)!==(previousVertexPoint.y>currentScreenPoint.y)&&currentScreenPoint.x<(previousVertexPoint.x-currentVertexPoint.x)*(currentScreenPoint.y-currentVertexPoint.y)/(previousVertexPoint.y-currentVertexPoint.y)+currentVertexPoint.x)currentInsideValue=!currentInsideValue;
 }
 return currentInsideValue;
}

/** 벽 한 칸의 투영 너비와 한 단계 층고에 원본 텍스처 한 장을 맞춘다. */
export function resolveCliffTextureScale(currentRenderOptions,currentTextureWidth,currentTextureHeight){
 if(!Number.isFinite(currentTextureWidth)||!Number.isFinite(currentTextureHeight)||currentTextureWidth<=0||currentTextureHeight<=0)throw new Error('암벽 텍스처 크기는 양수여야 합니다.');
 return {scaleX:currentRenderOptions.tileWidth/(2*currentTextureWidth),scaleY:currentRenderOptions.elevationHeight/currentTextureHeight};
}

/** 맵 캐릭터 외곽 강조의 공용 색상·두께. */
export const CHARACTER_OUTLINE_STYLE = Object.freeze({color:0xfff3c4,cssColor:'#fff3c4',width:2,outerStrength:4,quality:0.1});
