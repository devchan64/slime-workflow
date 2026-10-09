import {FIELD_RENDER_METRICS,buildFieldCellGeometry,projectSurfaceCell,projectSurfaceVertex,containsSurfacePoint} from './vendor/field-renderer/1.0.22/field-renderer.mjs';

// 검수 어댑터는 공용 렌더러의 면 목록으로 화면 범위와 선택만 계산한다.
export function createFieldReviewFrame(currentMapSurface,currentQuarterTurns){
 const currentRenderOptions={...FIELD_RENDER_METRICS,rotation:currentQuarterTurns};
 const currentCellRecords=[];
 for(let currentRowIndex=0;currentRowIndex<currentMapSurface.rows;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentMapSurface.columns;currentColumnIndex++){
  const currentCellPosition={column:currentColumnIndex,row:currentRowIndex};
  currentCellRecords.push({cell:currentCellPosition,faces:buildFieldCellGeometry(currentCellPosition,currentMapSurface,currentRenderOptions),depth:projectSurfaceVertex(currentCellPosition,currentRenderOptions).y,center:projectSurfaceCell(currentCellPosition,currentMapSurface,currentRenderOptions)});
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
