// 기존 ANNY 메시 렌더러를 재사용한다. 후보 마커는 깊이와 무관한 검수 오버레이다.
const LANDMARK_AXIS_DISPLAY_LENGTH = 0.12;
const LANDMARK_CLICK_DRAG_LIMIT = 4;

class AnnyLandmarkPreview extends AnnyMeshPreview {
 constructor(previewCanvasElement, overlayCanvasElement, currentSourceRecord) {
  super(previewCanvasElement);
  this.previewBackgroundChannels=[1,1,1];
  this.overlayCanvasElement=overlayCanvasElement;
  this.currentSourceRecord=currentSourceRecord;
  this.currentReviewRecord={draft:{points:{}},review:{axes:[]}};
  this.currentPickedPoint=null;
  this.loadPreviewMeshPayload(currentSourceRecord);
  let currentPointerOrigin=null;
  previewCanvasElement.addEventListener('pointerdown',currentPointerEvent=>{currentPointerOrigin=[currentPointerEvent.clientX,currentPointerEvent.clientY]});
  previewCanvasElement.addEventListener('pointerup',currentPointerEvent=>{
   if(!currentPointerOrigin || Math.hypot(currentPointerEvent.clientX-currentPointerOrigin[0],currentPointerEvent.clientY-currentPointerOrigin[1])>LANDMARK_CLICK_DRAG_LIMIT)return;
   const currentCanvasBounds=previewCanvasElement.getBoundingClientRect();
   this.currentPickedPoint=this.pickVisibleVertex([currentPointerEvent.clientX-currentCanvasBounds.left,currentPointerEvent.clientY-currentCanvasBounds.top]);
   this.drawPreviewMesh();
  });
 }
 projectCandidatePoint(currentPointValues) {
  const currentLocalValues=currentPointValues.map((currentAxisValue,currentAxisIndex)=>currentAxisValue-this.previewCenterValues[currentAxisIndex]);
  const currentHorizontalValue=Math.cos(this.previewYawRadians)*currentLocalValues[0]-Math.sin(this.previewYawRadians)*currentLocalValues[1];
  const currentForwardValue=Math.sin(this.previewYawRadians)*currentLocalValues[0]+Math.cos(this.previewYawRadians)*currentLocalValues[1];
  const currentVerticalValue=Math.cos(this.previewPitchRadians)*currentLocalValues[2]-Math.sin(this.previewPitchRadians)*currentForwardValue;
  const currentDepthValue=Math.sin(this.previewPitchRadians)*currentLocalValues[2]+Math.cos(this.previewPitchRadians)*currentForwardValue;
  const currentPixelScale=this.previewCanvasElement.clientHeight*1.7/this.previewHeightValue*this.previewZoomFactor/2;
  return [this.previewCanvasElement.clientWidth/2+currentHorizontalValue*currentPixelScale,this.previewCanvasElement.clientHeight/2-currentVerticalValue*currentPixelScale,currentDepthValue];
 }
 pickVisibleVertex(currentPixelPoint) {
  const currentProjectedVertices=this.currentSourceRecord.vertices.map(currentVertexPoint=>this.projectCandidatePoint(currentVertexPoint));
  let currentClosestDepth=Infinity,currentSelectedIndex=null;
  for(const currentTriangleIndices of this.currentSourceRecord.faces){
   const [currentFirstPoint,currentSecondPoint,currentThirdPoint]=currentTriangleIndices.map(currentVertexIndex=>currentProjectedVertices[currentVertexIndex]);
   const currentDenominatorValue=(currentSecondPoint[1]-currentThirdPoint[1])*(currentFirstPoint[0]-currentThirdPoint[0])+(currentThirdPoint[0]-currentSecondPoint[0])*(currentFirstPoint[1]-currentThirdPoint[1]);
   if(Math.abs(currentDenominatorValue)<1e-10)continue;
   const currentFirstWeight=((currentSecondPoint[1]-currentThirdPoint[1])*(currentPixelPoint[0]-currentThirdPoint[0])+(currentThirdPoint[0]-currentSecondPoint[0])*(currentPixelPoint[1]-currentThirdPoint[1]))/currentDenominatorValue;
   const currentSecondWeight=((currentThirdPoint[1]-currentFirstPoint[1])*(currentPixelPoint[0]-currentThirdPoint[0])+(currentFirstPoint[0]-currentThirdPoint[0])*(currentPixelPoint[1]-currentThirdPoint[1]))/currentDenominatorValue;
   const currentThirdWeight=1-currentFirstWeight-currentSecondWeight;
   if(Math.min(currentFirstWeight,currentSecondWeight,currentThirdWeight)<-1e-8)continue;
   const currentTriangleDepth=currentFirstWeight*currentFirstPoint[2]+currentSecondWeight*currentSecondPoint[2]+currentThirdWeight*currentThirdPoint[2];
   if(currentTriangleDepth>=currentClosestDepth)continue;
   currentClosestDepth=currentTriangleDepth;
   currentSelectedIndex=currentTriangleIndices.reduce((currentBestIndex,currentVertexIndex)=>Math.hypot(...currentProjectedVertices[currentVertexIndex].slice(0,2).map((currentAxisValue,currentAxisIndex)=>currentAxisValue-currentPixelPoint[currentAxisIndex]))<Math.hypot(...currentProjectedVertices[currentBestIndex].slice(0,2).map((currentAxisValue,currentAxisIndex)=>currentAxisValue-currentPixelPoint[currentAxisIndex]))?currentVertexIndex:currentBestIndex);
  }
  return currentSelectedIndex===null?null:this.currentSourceRecord.vertices[currentSelectedIndex];
 }
 drawPreviewMesh() {
  super.drawPreviewMesh();
  if(!this.overlayCanvasElement || !this.previewTriangleCount)return;
  const currentOverlayCanvas=this.overlayCanvasElement;
  currentOverlayCanvas.width=this.previewCanvasElement.width;currentOverlayCanvas.height=this.previewCanvasElement.height;
  const currentDrawingContext=currentOverlayCanvas.getContext('2d');
  currentDrawingContext.scale(devicePixelRatio,devicePixelRatio);
  currentDrawingContext.font='12px sans-serif';currentDrawingContext.lineWidth=2;
  const drawCandidateMarker=(currentPointValues,currentLabelText)=>{
   const currentScreenPoint=this.projectCandidatePoint(currentPointValues);
   currentDrawingContext.fillStyle='black';currentDrawingContext.strokeStyle='white';currentDrawingContext.beginPath();currentDrawingContext.arc(currentScreenPoint[0],currentScreenPoint[1],5,0,Math.PI*2);currentDrawingContext.fill();currentDrawingContext.stroke();
   currentDrawingContext.strokeText(currentLabelText,currentScreenPoint[0]+8,currentScreenPoint[1]);currentDrawingContext.fillText(currentLabelText,currentScreenPoint[0]+8,currentScreenPoint[1]);
  };
  for(const [currentPointName,currentPointRecord] of Object.entries(this.currentReviewRecord.draft.points))drawCandidateMarker(currentPointRecord.position,currentPointName);
  if(this.currentPickedPoint)drawCandidateMarker(this.currentPickedPoint,'선택 · 아직 미반영');
  for(const currentAxisRecord of this.currentReviewRecord.review.axes){
   const currentOriginPoint=this.projectCandidatePoint(currentAxisRecord.origin);
   currentAxisRecord.axes.forEach((currentAxisValues,currentAxisIndex)=>{
    const currentTargetPoint=this.projectCandidatePoint(currentAxisRecord.origin.map((currentAxisValue,currentCoordinateIndex)=>currentAxisValue+currentAxisValues[currentCoordinateIndex]*LANDMARK_AXIS_DISPLAY_LENGTH));
    currentDrawingContext.strokeStyle=['red','green','blue'][currentAxisIndex];currentDrawingContext.beginPath();currentDrawingContext.moveTo(...currentOriginPoint.slice(0,2));currentDrawingContext.lineTo(...currentTargetPoint.slice(0,2));currentDrawingContext.stroke();
   });
  }
 }
}

window.initializeLandmarkViewer=(currentSourceText)=>{
 const currentCanvasElement=document.querySelector('#anny-landmark-mesh');
 if(!currentCanvasElement)throw Error('기준점 캔버스를 찾을 수 없습니다.');
 if(window.currentAnnyLandmarkViewer)throw Error('이미 불러온 원본입니다. 새로 고침 후 시도하세요.');
 window.currentAnnyLandmarkViewer=new AnnyLandmarkPreview(currentCanvasElement,document.querySelector('#anny-landmark-overlay'),JSON.parse(currentSourceText));
};
window.updateLandmarkViewer=(currentReviewText)=>{
 if(!window.currentAnnyLandmarkViewer || !currentReviewText)return;
 window.currentAnnyLandmarkViewer.currentReviewRecord=JSON.parse(currentReviewText);
 window.currentAnnyLandmarkViewer.drawPreviewMesh();
};
