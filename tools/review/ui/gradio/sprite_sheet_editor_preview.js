(currentImageData,currentFrameRows,currentFrameIndex,currentPlayEnabled,currentShadowEnabled,currentEditMode,currentSourceBounds)=>{
 const currentCanvasElement=document.getElementById('sprite-sheet-alignment-preview');
 if(!currentCanvasElement)return '미리보기 캔버스가 없습니다.';
 const currentRows=(Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data)?.map(currentFrameRow=>currentFrameRow.map(Number));
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 const currentCanvasSize=640,currentCanvasPadding=48,currentAnchorRadius=9;
 currentCanvasElement.spritePreviewRevision=(currentCanvasElement.spritePreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.spritePreviewRevision;
 currentCanvasElement.onpointerdown=currentCanvasElement.onpointermove=currentCanvasElement.onpointerup=currentCanvasElement.onpointercancel=null;
 currentCanvasContext.fillStyle='#888';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
 if(!currentImageData||!currentRows?.length)return '원본 시트를 불러오세요.';
 if(currentRows.some(currentFrameRow=>currentFrameRow.length!==6||currentFrameRow.some(currentValue=>!Number.isFinite(currentValue))||currentFrameRow[2]<=0||currentFrameRow[3]<=0))return '유효한 프레임 좌표가 필요합니다.';
 const currentSignature=JSON.stringify(currentRows);
 const currentSelectedIndex=Math.max(0,Math.min(currentRows.length-1,Number(currentFrameIndex)-1));
 let currentEditorState=currentCanvasElement.spriteEditorState;
 if(!currentEditorState||currentEditorState.image!==currentImageData){currentEditorState={image:currentImageData,signature:currentSignature,undo:[],drafts:{}};currentCanvasElement.spriteEditorState=currentEditorState;}
 if(currentEditorState.signature!==currentSignature){if(currentEditorState.expectedSignature!==currentSignature)currentEditorState.undo=[];currentEditorState.expectedSignature=null;currentEditorState.signature=currentSignature;currentEditorState.drafts={};}
 const currentOriginalRow=currentRows[currentSelectedIndex];
 const currentDraftRow=currentEditorState.drafts[currentSelectedIndex]??[...currentOriginalRow];
 currentEditorState.drafts[currentSelectedIndex]=currentDraftRow;
 currentEditorState.index=currentSelectedIndex;currentEditorState.rows=currentRows;
 const currentImageElement=new Image();
 currentImageElement.onload=()=>{
  if(currentCanvasElement.spritePreviewRevision!==currentPreviewRevision)return;
  // 수동 이동과 재생은 전체 프레임의 공통 배율과 화면 앵커를 사용한다.
  const currentMaxLeft=Math.max(...currentRows.map(currentFrameRow=>currentFrameRow[4]));
  const currentMaxTop=Math.max(...currentRows.map(currentFrameRow=>currentFrameRow[5]));
  const currentBoundsWidth=currentMaxLeft+Math.max(...currentRows.map(currentFrameRow=>currentFrameRow[2]-currentFrameRow[4]));
  const currentBoundsHeight=currentMaxTop+Math.max(...currentRows.map(currentFrameRow=>currentFrameRow[3]-currentFrameRow[5]));
  const currentScaleValue=Math.min((currentCanvasSize-currentCanvasPadding*2)/currentBoundsWidth,(currentCanvasSize-currentCanvasPadding*2)/currentBoundsHeight);
  const currentFixedAnchorLeft=(currentCanvasSize-currentBoundsWidth*currentScaleValue)/2+currentMaxLeft*currentScaleValue;
  const currentFixedAnchorTop=(currentCanvasSize-currentBoundsHeight*currentScaleValue)/2+currentMaxTop*currentScaleValue;
  const currentOriginLeft=currentFixedAnchorLeft-currentOriginalRow[4]*currentScaleValue,currentOriginTop=currentFixedAnchorTop-currentOriginalRow[5]*currentScaleValue;
  const currentStartTime=performance.now();
  const drawCurrentEditorFrame=currentTime=>{
   if(!currentCanvasElement.isConnected||currentCanvasElement.spritePreviewRevision!==currentPreviewRevision)return;
   currentCanvasContext.fillStyle='#888';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
   const currentActiveIndex=currentPlayEnabled?Math.floor(Math.max(0,currentTime-currentStartTime)*6/1000)%currentRows.length:currentSelectedIndex;
   const currentActiveRow=currentPlayEnabled?currentRows[currentActiveIndex]:currentDraftRow;
   let currentDrawScale=currentScaleValue,currentDrawLeft=currentOriginLeft,currentDrawTop=currentOriginTop;
   if(currentPlayEnabled){
    currentDrawLeft=currentFixedAnchorLeft-currentActiveRow[4]*currentDrawScale;
    currentDrawTop=currentFixedAnchorTop-currentActiveRow[5]*currentDrawScale;
   }
   const currentAnchorLeft=currentDrawLeft+(currentPlayEnabled?currentActiveRow[4]:currentActiveRow[0]-currentOriginalRow[0]+currentActiveRow[4])*currentDrawScale;
   const currentAnchorTop=currentDrawTop+(currentPlayEnabled?currentActiveRow[5]:currentActiveRow[1]-currentOriginalRow[1]+currentActiveRow[5])*currentDrawScale;
   const currentDrawRow=currentActiveRow;
   const currentCropOffsetLeft=currentPlayEnabled?0:(currentActiveRow[0]-currentOriginalRow[0])*currentDrawScale;
   const currentCropOffsetTop=currentPlayEnabled?0:(currentActiveRow[1]-currentOriginalRow[1])*currentDrawScale;
   const currentSourceRect=currentSourceBounds?.[currentActiveIndex]??[0,0,currentImageElement.width,currentImageElement.height];
   const currentClipLeft=Math.max(currentDrawRow[0],currentSourceRect[0]),currentClipTop=Math.max(currentDrawRow[1],currentSourceRect[1]);
   const currentClipRight=Math.min(currentDrawRow[0]+currentDrawRow[2],currentSourceRect[0]+currentSourceRect[2]),currentClipBottom=Math.min(currentDrawRow[1]+currentDrawRow[3],currentSourceRect[1]+currentSourceRect[3]);
   if(currentClipRight>currentClipLeft&&currentClipBottom>currentClipTop)currentCanvasContext.drawImage(currentImageElement,currentClipLeft,currentClipTop,currentClipRight-currentClipLeft,currentClipBottom-currentClipTop,currentDrawLeft+currentCropOffsetLeft+(currentClipLeft-currentDrawRow[0])*currentDrawScale,currentDrawTop+currentCropOffsetTop+(currentClipTop-currentDrawRow[1])*currentDrawScale,(currentClipRight-currentClipLeft)*currentDrawScale,(currentClipBottom-currentClipTop)*currentDrawScale);
   if(currentShadowEnabled){currentCanvasContext.fillStyle='rgba(0,0,0,.22)';currentCanvasContext.beginPath();currentCanvasContext.ellipse(currentAnchorLeft,currentAnchorTop,currentOriginalRow[2]*currentDrawScale*.24,currentOriginalRow[3]*currentDrawScale*.06,0,0,Math.PI*2);currentCanvasContext.fill();}
   if(!currentPlayEnabled){currentCanvasContext.strokeStyle='#987000';currentCanvasContext.lineWidth=2;currentCanvasContext.strokeRect(currentOriginLeft+(currentDraftRow[0]-currentOriginalRow[0])*currentScaleValue,currentOriginTop+(currentDraftRow[1]-currentOriginalRow[1])*currentScaleValue,currentDraftRow[2]*currentScaleValue,currentDraftRow[3]*currentScaleValue);}
   currentCanvasContext.strokeStyle='#e22';currentCanvasContext.beginPath();currentCanvasContext.arc(currentAnchorLeft,currentAnchorTop,currentAnchorRadius,0,Math.PI*2);currentCanvasContext.moveTo(currentAnchorLeft-14,currentAnchorTop);currentCanvasContext.lineTo(currentAnchorLeft+14,currentAnchorTop);currentCanvasContext.moveTo(currentAnchorLeft,currentAnchorTop-14);currentCanvasContext.lineTo(currentAnchorLeft,currentAnchorTop+14);currentCanvasContext.stroke();
   currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText(`프레임 ${currentActiveIndex+1}/${currentRows.length} · ${currentPlayEnabled?'재생 중에는 편집할 수 없습니다.':currentEditMode+' 드래그 후 적용 버튼을 누르세요.'}`,16,24);
   if(currentPlayEnabled)requestAnimationFrame(drawCurrentEditorFrame);
  };
  const readCurrentPointer=currentEvent=>{const currentBounds=currentCanvasElement.getBoundingClientRect();return [Math.round(((currentEvent.clientX-currentBounds.left)*currentCanvasSize/currentBounds.width-currentOriginLeft)/currentScaleValue),Math.round(((currentEvent.clientY-currentBounds.top)*currentCanvasSize/currentBounds.height-currentOriginTop)/currentScaleValue)];};
  let currentDragStart=null,currentDragBackup=null;
  currentCanvasElement.onpointerdown=currentEvent=>{if(currentPlayEnabled)return;currentEvent.preventDefault();currentCanvasElement.setPointerCapture(currentEvent.pointerId);currentDragStart=readCurrentPointer(currentEvent);currentDragBackup=[...currentDraftRow];currentCanvasElement.onpointermove(currentEvent);};
  currentCanvasElement.onpointermove=currentEvent=>{
   if(!currentDragStart)return;const currentPoint=readCurrentPointer(currentEvent);
   if(currentEditMode==='앵커'){
    currentDraftRow[4]=Math.max(0,Math.min(currentDraftRow[2]-1,currentOriginalRow[0]+currentPoint[0]-currentDraftRow[0]));currentDraftRow[5]=Math.max(0,Math.min(currentDraftRow[3]-1,currentOriginalRow[1]+currentPoint[1]-currentDraftRow[1]));
   }else{
    const currentLeft=Math.min(currentDragStart[0],currentPoint[0]),currentTop=Math.min(currentDragStart[1],currentPoint[1]);
    const currentWidth=Math.abs(currentPoint[0]-currentDragStart[0]),currentHeight=Math.abs(currentPoint[1]-currentDragStart[1]);
    if(currentWidth&&currentHeight){const currentAnchorX=currentDragBackup[0]+currentDragBackup[4],currentAnchorY=currentDragBackup[1]+currentDragBackup[5];currentDraftRow.splice(0,6,currentOriginalRow[0]+currentLeft,currentOriginalRow[1]+currentTop,currentWidth,currentHeight,Math.max(0,Math.min(currentWidth-1,currentAnchorX-currentOriginalRow[0]-currentLeft)),Math.max(0,Math.min(currentHeight-1,currentAnchorY-currentOriginalRow[1]-currentTop)));}
   }
   drawCurrentEditorFrame(performance.now());
  };
  currentCanvasElement.onpointerup=()=>{currentDragStart=null;};
  currentCanvasElement.onpointercancel=()=>{if(currentDragBackup)currentDraftRow.splice(0,6,...currentDragBackup);currentDragStart=null;drawCurrentEditorFrame(performance.now());};
  drawCurrentEditorFrame(currentStartTime);
 };
 currentImageElement.src=currentImageData;
 return '크롭: 영역을 드래그 · 앵커: 클릭 또는 드래그 · 적용 전까지 출력에 반영되지 않습니다.';
}
