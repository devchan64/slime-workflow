(currentImageData,currentFrameRows,currentFrameIndex,currentPlayEnabled,currentShadowEnabled,currentEditMode)=>{
 const currentCanvasElement=document.getElementById('sprite-sheet-alignment-preview');
 if(!currentCanvasElement)return '미리보기 캔버스가 없습니다.';
 const currentRows=(Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data)?.map(currentFrameRow=>currentFrameRow.map(Number));
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 const currentCanvasSize=640,currentCanvasPadding=48,currentAnchorRadius=9;
 currentCanvasElement.spritePreviewRevision=(currentCanvasElement.spritePreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.spritePreviewRevision;
 currentCanvasElement.onpointerdown=currentCanvasElement.onpointermove=currentCanvasElement.onpointerup=currentCanvasElement.onpointercancel=null;
 currentCanvasContext.fillStyle='#fff';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
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
  const currentScaleValue=Math.min((currentCanvasSize-currentCanvasPadding*2)/currentOriginalRow[2],(currentCanvasSize-currentCanvasPadding*2)/currentOriginalRow[3]);
  const currentOriginLeft=(currentCanvasSize-currentOriginalRow[2]*currentScaleValue)/2,currentOriginTop=(currentCanvasSize-currentOriginalRow[3]*currentScaleValue)/2;
  const currentStartTime=performance.now();
  const drawCurrentEditorFrame=currentTime=>{
   if(!currentCanvasElement.isConnected||currentCanvasElement.spritePreviewRevision!==currentPreviewRevision)return;
   currentCanvasContext.fillStyle='#fff';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
   const currentActiveIndex=currentPlayEnabled?Math.floor((currentTime-currentStartTime)*6/1000)%currentRows.length:currentSelectedIndex;
   const currentActiveRow=currentPlayEnabled?currentRows[currentActiveIndex]:currentDraftRow;
   let currentDrawScale=currentScaleValue,currentDrawLeft=currentOriginLeft,currentDrawTop=currentOriginTop;
   if(currentPlayEnabled){
    const currentMaxLeft=Math.max(...currentRows.map(currentRow=>currentRow[4])),currentMaxTop=Math.max(...currentRows.map(currentRow=>currentRow[5]));
    const currentBoundsWidth=currentMaxLeft+Math.max(...currentRows.map(currentRow=>currentRow[2]-currentRow[4])),currentBoundsHeight=currentMaxTop+Math.max(...currentRows.map(currentRow=>currentRow[3]-currentRow[5]));
    currentDrawScale=Math.min(544/currentBoundsWidth,544/currentBoundsHeight);
    currentDrawLeft=(640-currentBoundsWidth*currentDrawScale)/2+(currentMaxLeft-currentActiveRow[4])*currentDrawScale;
    currentDrawTop=(640-currentBoundsHeight*currentDrawScale)/2+(currentMaxTop-currentActiveRow[5])*currentDrawScale;
   }
   const currentAnchorLeft=currentDrawLeft+(currentPlayEnabled?currentActiveRow[4]:currentActiveRow[0]-currentOriginalRow[0]+currentActiveRow[4])*currentDrawScale;
   const currentAnchorTop=currentDrawTop+(currentPlayEnabled?currentActiveRow[5]:currentActiveRow[1]-currentOriginalRow[1]+currentActiveRow[5])*currentDrawScale;
   if(currentShadowEnabled){currentCanvasContext.fillStyle='rgba(0,0,0,.22)';currentCanvasContext.beginPath();currentCanvasContext.ellipse(currentAnchorLeft,currentAnchorTop,currentOriginalRow[2]*currentDrawScale*.24,currentOriginalRow[3]*currentDrawScale*.06,0,0,Math.PI*2);currentCanvasContext.fill();}
   const currentDrawRow=currentPlayEnabled?currentActiveRow:currentOriginalRow;
   currentCanvasContext.drawImage(currentImageElement,...currentDrawRow.slice(0,4),currentDrawLeft,currentDrawTop,currentDrawRow[2]*currentDrawScale,currentDrawRow[3]*currentDrawScale);
   if(!currentPlayEnabled){currentCanvasContext.strokeStyle='#987000';currentCanvasContext.lineWidth=2;currentCanvasContext.strokeRect(currentOriginLeft+(currentDraftRow[0]-currentOriginalRow[0])*currentScaleValue,currentOriginTop+(currentDraftRow[1]-currentOriginalRow[1])*currentScaleValue,currentDraftRow[2]*currentScaleValue,currentDraftRow[3]*currentScaleValue);}
   currentCanvasContext.strokeStyle='#e22';currentCanvasContext.beginPath();currentCanvasContext.arc(currentAnchorLeft,currentAnchorTop,currentAnchorRadius,0,Math.PI*2);currentCanvasContext.moveTo(currentAnchorLeft-14,currentAnchorTop);currentCanvasContext.lineTo(currentAnchorLeft+14,currentAnchorTop);currentCanvasContext.moveTo(currentAnchorLeft,currentAnchorTop-14);currentCanvasContext.lineTo(currentAnchorLeft,currentAnchorTop+14);currentCanvasContext.stroke();
   currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText(`프레임 ${currentActiveIndex+1}/${currentRows.length} · ${currentPlayEnabled?'재생 중에는 편집할 수 없습니다.':currentEditMode+' 드래그 후 적용 버튼을 누르세요.'}`,16,24);
   if(currentPlayEnabled)requestAnimationFrame(drawCurrentEditorFrame);
  };
  const readCurrentPointer=currentEvent=>{const currentBounds=currentCanvasElement.getBoundingClientRect();return [Math.max(0,Math.min(currentOriginalRow[2],Math.round(( (currentEvent.clientX-currentBounds.left)*640/currentBounds.width-currentOriginLeft)/currentScaleValue))),Math.max(0,Math.min(currentOriginalRow[3],Math.round(((currentEvent.clientY-currentBounds.top)*640/currentBounds.height-currentOriginTop)/currentScaleValue)))];};
  let currentDragStart=null,currentDragBackup=null;
  currentCanvasElement.onpointerdown=currentEvent=>{if(currentPlayEnabled)return;currentEvent.preventDefault();currentCanvasElement.setPointerCapture(currentEvent.pointerId);currentDragStart=readCurrentPointer(currentEvent);currentDragBackup=[...currentDraftRow];currentCanvasElement.onpointermove(currentEvent);};
  currentCanvasElement.onpointermove=currentEvent=>{
   if(!currentDragStart)return;const currentPoint=readCurrentPointer(currentEvent);
   if(currentEditMode==='앵커'){
    currentDraftRow[4]=Math.max(0,Math.min(currentDraftRow[2]-1,currentOriginalRow[0]+currentPoint[0]-currentDraftRow[0]));currentDraftRow[5]=Math.max(0,Math.min(currentDraftRow[3]-1,currentOriginalRow[1]+currentPoint[1]-currentDraftRow[1]));
   }else{
    const currentLeft=Math.min(currentDragStart[0],currentPoint[0]),currentTop=Math.min(currentDragStart[1],currentPoint[1]);
    const currentWidth=Math.abs(currentPoint[0]-currentDragStart[0]),currentHeight=Math.abs(currentPoint[1]-currentDragStart[1]);
    if(currentWidth&&currentHeight){const currentAnchorX=currentDragBackup[0]+currentDragBackup[4],currentAnchorY=currentDragBackup[1]+currentDragBackup[5];currentDraftRow.splice(0,6,currentOriginalRow[0]+currentLeft,currentOriginalRow[1]+currentTop,currentWidth,currentHeight,currentAnchorX-currentOriginalRow[0]-currentLeft,currentAnchorY-currentOriginalRow[1]-currentTop);}
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
