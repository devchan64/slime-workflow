import {FIELD_RENDER_METRICS,projectSurfaceVertex,projectSurfaceCell,buildSurfaceCliffs,buildSurfaceStairs,findSurfaceStair,readSurfaceHeight,containsSurfacePoint,resolveCliffTextureScale} from './vendor/field-surface/1.0.3/field-surface.mjs';

// Canvas 어댑터는 공통 라이브러리의 면·투영 결과만 그린다.
export function createFieldReviewFrame(currentMapSurface,currentQuarterTurns){
 const currentRenderOptions={...FIELD_RENDER_METRICS,rotation:currentQuarterTurns};
 const currentCellRecords=[];
 for(let currentRowIndex=0;currentRowIndex<currentMapSurface.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapSurface.columns;currentColumnIndex++){
  const currentCellPosition={column:currentColumnIndex,row:currentRowIndex};
  const currentStairRecord=findSurfaceStair(currentCellPosition,currentMapSurface);
  const currentGroundVertices=[[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]].map(([currentColumnOffset,currentRowOffset])=>({column:currentColumnIndex+currentColumnOffset,row:currentRowIndex+currentRowOffset,height:readSurfaceHeight(currentCellPosition,currentMapSurface)*currentRenderOptions.elevationHeight}));
  const currentGroundFace={top:true,ground:true,vertices:currentGroundVertices,points:currentGroundVertices.map(currentVertexPoint=>projectSurfaceVertex(currentVertexPoint,currentRenderOptions))};
  const currentCellFaces=currentStairRecord?buildSurfaceStairs(currentStairRecord,currentMapSurface,currentRenderOptions):[...buildSurfaceCliffs(currentCellPosition,currentMapSurface,currentRenderOptions).map(currentFacePoints=>({top:false,points:currentFacePoints,cliff:true})),currentGroundFace];
  currentCellRecords.push({cell:currentCellPosition,faces:currentCellFaces,depth:projectSurfaceVertex(currentCellPosition,currentRenderOptions).y,center:projectSurfaceCell(currentCellPosition,currentMapSurface,currentRenderOptions)});
 }
 currentCellRecords.sort((currentFirstCell,currentSecondCell)=>currentFirstCell.depth-currentSecondCell.depth||currentFirstCell.cell.row-currentSecondCell.cell.row);
 return {cells:currentCellRecords,points:currentCellRecords.flatMap(currentCellRecord=>currentCellRecord.faces.flatMap(currentFaceRecord=>currentFaceRecord.points)),options:currentRenderOptions};
}
export function pickFieldReviewCell(currentScreenPoint,currentFieldFrame){
 for(const currentCellRecord of [...currentFieldFrame.cells].reverse())for(const currentFaceRecord of [...currentCellRecord.faces].reverse()){
  if(containsSurfacePoint(currentScreenPoint,currentFaceRecord.points))return currentFaceRecord.top?currentCellRecord.cell:null;
 }
 return null;
}
export function drawFieldReviewFrame(currentFieldFrame,currentDrawingContext,currentMapSurface,currentTextureImages,currentTextureNames,drawPolygonSurface,drawGroundTexture,drawCellCharacter){
 for(const currentCellRecord of currentFieldFrame.cells){
  const currentTerrainName=currentMapSurface.terrainCodes[currentMapSurface.terrainRows[currentCellRecord.cell.row][currentCellRecord.cell.column]];
  for(const currentFaceRecord of currentCellRecord.faces){
   drawPolygonSurface(currentFaceRecord.points,currentFaceRecord.top?'#beb694':'#81785e');
   if(currentFaceRecord.ground){
    const currentGroundImage=currentTextureImages[currentTextureNames[currentTerrainName]];
    if(!currentGroundImage)throw Error('필드 지면 텍스처 누락: '+currentTerrainName);
    drawGroundTexture(currentFaceRecord,currentGroundImage);
   }else if(currentFaceRecord.cliff){
    const currentCliffTexture=currentTextureImages['cliff-wall'];
    if(!currentCliffTexture)throw Error('절벽 측면 텍스처 누락');
    // 게임과 같은 배율로 벽 한 칸·한 층에 텍스처 한 장을 반복한다.
    const currentTextureScale=resolveCliffTextureScale(currentFieldFrame.options,currentCliffTexture.width,currentCliffTexture.height);
    const currentMinimumX=Math.min(...currentFaceRecord.points.map(currentPointValue=>currentPointValue.x)),currentMinimumY=Math.min(...currentFaceRecord.points.map(currentPointValue=>currentPointValue.y));
    const currentMaximumX=Math.max(...currentFaceRecord.points.map(currentPointValue=>currentPointValue.x)),currentMaximumY=Math.max(...currentFaceRecord.points.map(currentPointValue=>currentPointValue.y));
    currentDrawingContext.save();currentDrawingContext.beginPath();currentFaceRecord.points.forEach((currentPointValue,currentPointIndex)=>currentPointIndex?currentDrawingContext.lineTo(currentPointValue.x,currentPointValue.y):currentDrawingContext.moveTo(currentPointValue.x,currentPointValue.y));currentDrawingContext.closePath();currentDrawingContext.clip();currentDrawingContext.translate(currentMinimumX,currentMinimumY);currentDrawingContext.scale(currentTextureScale.scaleX,currentTextureScale.scaleY);currentDrawingContext.fillStyle=currentDrawingContext.createPattern(currentCliffTexture,'repeat');currentDrawingContext.fillRect(0,0,(currentMaximumX-currentMinimumX)/currentTextureScale.scaleX,(currentMaximumY-currentMinimumY)/currentTextureScale.scaleY);currentDrawingContext.restore();
   }
  }
  drawCellCharacter(currentCellRecord.cell,currentCellRecord.center);
 }
}
