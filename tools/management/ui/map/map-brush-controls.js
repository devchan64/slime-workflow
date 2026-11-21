// 포인터 스트로크는 브라우저에서 모으고 완료된 작업만 Gradio 초안으로 전달한다.
export function installMapBrushControls(currentMapCanvas,currentResolveTarget){
 let currentStrokeEvents=null;
 let currentStrokeVisited=new Set();
 window.mapReviewBrushTool='pan';
 window.mapReviewBrushQueue=[];
 window.mapReviewBrushBusy=false;
 window.mapReviewFlushBrushQueue=()=>{
  if(window.mapReviewBrushBusy||!window.mapReviewBrushQueue.length)return;
  window.mapReviewBrushBusy=true;
  window.dispatchEvent(new CustomEvent('map-editor-brush'));
 };
 function appendMapBrushPoint(currentPointerEvent){
  const currentToolName=window.mapReviewBrushTool;
  const currentTargetRecord=currentResolveTarget(currentPointerEvent,currentToolName);
  if(!currentTargetRecord)return;
  const currentTargetKey=currentToolName==='delete'?currentTargetRecord.object:`${currentTargetRecord.column},${currentTargetRecord.row}`;
  if(currentStrokeVisited.has(currentTargetKey))return;
  currentStrokeVisited.add(currentTargetKey);
  currentStrokeEvents.push({...currentTargetRecord,tool:currentToolName,tile:window.mapReviewBrushTile,wall:window.mapReviewBrushWall,texture:window.mapReviewBrushTexture});
  window.mapReviewSelectedCell={column:currentTargetRecord.column,row:currentTargetRecord.row};
  document.querySelector('#status').textContent=`도구 적용 대상 ${currentStrokeEvents.length}곳 · 포인터를 놓으면 검증합니다.`;
 }
 return {
  beginBrushStroke(currentPointerEvent){
   if(!window.mapReviewEditingEnabled||!window.mapReviewBrushTool||window.mapReviewBrushTool==='pan')return false;
   if(window.mapReviewBrushTool==='place'&&!window.mapReviewBrushTexture){document.querySelector('#status').textContent='빌보드 선택기에서 배치할 에셋을 먼저 선택하세요.';return true;}
   currentStrokeEvents=[];currentStrokeVisited=new Set();
   currentMapCanvas.setPointerCapture(currentPointerEvent.pointerId);
   appendMapBrushPoint(currentPointerEvent);return true;
  },
  moveBrushStroke(currentPointerEvent){if(currentStrokeEvents===null)return false;appendMapBrushPoint(currentPointerEvent);return true;},
  finishBrushStroke(currentCancelledStroke=false){
   if(currentStrokeEvents===null)return false;
   if(!currentCancelledStroke&&currentStrokeEvents.length){window.mapReviewBrushQueue.push(currentStrokeEvents);window.mapReviewFlushBrushQueue();}
   currentStrokeEvents=null;currentStrokeVisited.clear();return true;
  }
 };
}
