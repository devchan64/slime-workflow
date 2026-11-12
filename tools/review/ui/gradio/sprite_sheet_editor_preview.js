(function renderSpriteSheetPreview(currentImageData,currentFrameRows,currentFrameIndex,currentPlayEnabled,currentShadowEnabled,currentEditMode,currentSourceBounds,currentPlaybackRate=6,currentBaselineEnabled=false,currentOnionEnabled=false,currentPreviewClip='',currentSourceRecord={},currentGameSizeEnabled=false,currentReferenceHeight=480,currentGameBodyHeight=80,currentFeetEnabled=false,currentRestoredFeet={},currentHeightGuideEnabled=false){
 const currentCanvasElement=document.getElementById('sprite-sheet-alignment-preview');
 if(!currentCanvasElement)return '미리보기 캔버스가 없습니다.';
 const currentRows=(Array.isArray(currentFrameRows)?currentFrameRows:currentFrameRows?.data)?.map(currentFrameRow=>currentFrameRow.map(Number));
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 const currentPlaybackFps=Number(currentPlaybackRate);
 if(![4,6,8,12,16,24,30].includes(currentPlaybackFps))return '지원하지 않는 검수 FPS입니다.';
 const currentCanvasSize=640,currentCanvasPadding=48,currentAnchorRadius=9,currentOnionOpacity=.28;
 currentCanvasElement.spritePreviewRevision=(currentCanvasElement.spritePreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.spritePreviewRevision;
 currentCanvasElement.onpointerdown=currentCanvasElement.onpointermove=currentCanvasElement.onpointerup=currentCanvasElement.onpointercancel=null;
 currentCanvasContext.fillStyle='#888';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
 if(!currentImageData||!currentRows?.length)return '원본 시트를 불러오세요.';
 if(currentRows.some(currentFrameRow=>currentFrameRow.length!==6||currentFrameRow.some(currentValue=>!Number.isFinite(currentValue))||currentFrameRow[2]<=0||currentFrameRow[3]<=0))return '유효한 프레임 좌표가 필요합니다.';
 const currentClipRecord=currentPreviewClip?(currentSourceRecord.animation?.clips||[]).find(currentClipValue=>currentClipValue.clipId===currentPreviewClip):null;
 if(currentPreviewClip&&!currentClipRecord)return '선택한 동작을 다시 확인하세요.';
 const currentPlaybackIndices=currentClipRecord?currentClipRecord.frames.map(currentClipFrame=>(currentSourceRecord.animation.frames||[]).findIndex(currentSourceFrame=>currentSourceFrame.frameId===currentClipFrame.frameId)):currentRows.map((currentFrameRow,currentFrameNumber)=>currentFrameNumber);
 if(!currentPlaybackIndices.length||currentPlaybackIndices.some(currentFrameNumber=>currentFrameNumber<0||currentFrameNumber>=currentRows.length))return '클립의 프레임 참조가 유효하지 않습니다.';
 const currentSignature=JSON.stringify(currentRows);
 const currentSelectedIndex=Math.max(0,Math.min(currentRows.length-1,Number(currentFrameIndex)-1));
 let currentEditorState=currentCanvasElement.spriteEditorState;
 if(!currentEditorState||currentEditorState.image!==currentImageData){currentEditorState={image:currentImageData,signature:currentSignature,undo:[],drafts:{},headValues:{}};currentCanvasElement.spriteEditorState=currentEditorState;}
 if(currentEditorState.signature!==currentSignature){if(currentEditorState.expectedSignature!==currentSignature)currentEditorState.undo=[];currentEditorState.expectedSignature=null;currentEditorState.signature=currentSignature;currentEditorState.drafts={};currentEditorState.headValues={};currentEditorState.bodyReference=null;}
 if(!currentEditorState.referenceLoaded&&currentSourceRecord?.runtimeDimensions?.bodyReference){
  const currentSavedReference=currentSourceRecord.runtimeDimensions.bodyReference;
  const currentReferenceIndex=(currentSourceRecord.animation?.frames||[]).findIndex(currentFrame=>currentFrame.frameId===currentSavedReference.frameId);
  if(currentReferenceIndex>=0&&currentRows[currentReferenceIndex]&&Number.isFinite(currentSavedReference.headY)&&currentSavedReference.headY>=0&&currentSavedReference.headY<currentRows[currentReferenceIndex][5]){
   currentEditorState.headValues[currentReferenceIndex]=currentSavedReference.headY;
   currentEditorState.bodyReference={frame:currentReferenceIndex+1,row:[...currentRows[currentReferenceIndex]],headY:currentSavedReference.headY,floorY:currentRows[currentReferenceIndex][5],height:currentRows[currentReferenceIndex][5]-currentSavedReference.headY};
  }
  currentEditorState.referenceLoaded=true;
 }
 const currentBodyReference=currentEditorState.bodyReference||{};
 const currentEffectiveHeight=currentBodyReference.height??Number(currentReferenceHeight);
 const currentEffectiveGameHeight=currentBodyReference.height?80:Number(currentGameBodyHeight);
 if(currentGameSizeEnabled&&(!Number.isFinite(currentEffectiveHeight)||currentEffectiveHeight<=0||!Number.isFinite(currentEffectiveGameHeight)||currentEffectiveGameHeight<=0))return '원본 신체 높이와 게임 출력 높이는 양수여야 합니다.';
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
  const currentScaleValue=currentGameSizeEnabled?currentEffectiveGameHeight/currentEffectiveHeight:Math.min((currentCanvasSize-currentCanvasPadding*2)/currentBoundsWidth,(currentCanvasSize-currentCanvasPadding*2)/currentBoundsHeight);
  const currentFixedAnchorLeft=(currentCanvasSize-currentBoundsWidth*currentScaleValue)/2+currentMaxLeft*currentScaleValue;
  const currentFixedAnchorTop=(currentCanvasSize-currentBoundsHeight*currentScaleValue)/2+currentMaxTop*currentScaleValue;
  const currentOriginLeft=currentFixedAnchorLeft-currentOriginalRow[4]*currentScaleValue,currentOriginTop=currentFixedAnchorTop-currentOriginalRow[5]*currentScaleValue;
  const currentStartTime=performance.now();
  const drawCurrentEditorFrame=currentTime=>{
   if(!currentCanvasElement.isConnected||currentCanvasElement.spritePreviewRevision!==currentPreviewRevision)return;
   currentCanvasContext.fillStyle='#888';currentCanvasContext.fillRect(0,0,currentCanvasSize,currentCanvasSize);
   const currentPlaybackStep=Math.floor(Math.max(0,currentTime-currentStartTime)*currentPlaybackFps/1000);
   const currentPlaybackPosition=currentClipRecord?.loop===false?Math.min(currentPlaybackStep,currentPlaybackIndices.length-1):currentPlaybackStep%currentPlaybackIndices.length;
   const currentActiveIndex=currentPlayEnabled?currentPlaybackIndices[currentPlaybackPosition]:currentSelectedIndex;
   currentEditorState.displayedIndex=currentActiveIndex;
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
   const currentClipPosition=currentPlaybackIndices.indexOf(currentActiveIndex);
   const currentPreviousIndex=currentClipPosition>0?currentPlaybackIndices[currentClipPosition-1]:-1;
   if(currentOnionEnabled&&currentPreviousIndex>=0){
    const currentPreviousRow=currentRows[currentPreviousIndex];
    const currentPreviousBounds=currentSourceBounds?.[currentPreviousIndex]??[0,0,currentImageElement.width,currentImageElement.height];
    const currentPreviousLeft=Math.max(currentPreviousRow[0],currentPreviousBounds[0]);
    const currentPreviousTop=Math.max(currentPreviousRow[1],currentPreviousBounds[1]);
    const currentPreviousRight=Math.min(currentPreviousRow[0]+currentPreviousRow[2],currentPreviousBounds[0]+currentPreviousBounds[2]);
    const currentPreviousBottom=Math.min(currentPreviousRow[1]+currentPreviousRow[3],currentPreviousBounds[1]+currentPreviousBounds[3]);
    if(currentPreviousRight>currentPreviousLeft&&currentPreviousBottom>currentPreviousTop){
     currentCanvasContext.save();currentCanvasContext.globalAlpha=currentOnionOpacity;
     currentCanvasContext.drawImage(currentImageElement,currentPreviousLeft,currentPreviousTop,currentPreviousRight-currentPreviousLeft,currentPreviousBottom-currentPreviousTop,currentFixedAnchorLeft+(currentPreviousLeft-currentPreviousRow[0]-currentPreviousRow[4])*currentDrawScale,currentFixedAnchorTop+(currentPreviousTop-currentPreviousRow[1]-currentPreviousRow[5])*currentDrawScale,(currentPreviousRight-currentPreviousLeft)*currentDrawScale,(currentPreviousBottom-currentPreviousTop)*currentDrawScale);
     currentCanvasContext.restore();
    }
   }
   if(currentFeetEnabled){
    const currentOriginalFrame=currentSourceRecord?.animation?.frames?.[currentActiveIndex];
    const currentFootPoints=currentRestoredFeet?.[String(currentActiveIndex)]??currentOriginalFrame?.contacts;
    if(Array.isArray(currentFootPoints)&&currentFootPoints.length===2&&currentFootPoints.every(currentFootPoint=>Number.isFinite(currentFootPoint.x)&&Number.isFinite(currentFootPoint.y))){
     currentCanvasContext.strokeStyle='#00a4ad';
     for(const currentFootPoint of currentFootPoints){
      const currentFootLeft=currentDrawLeft+currentCropOffsetLeft+(currentOriginalFrame.rect.x+currentFootPoint.x-currentDrawRow[0])*currentDrawScale;
      const currentFootTop=currentDrawTop+currentCropOffsetTop+(currentOriginalFrame.rect.y+currentFootPoint.y-currentDrawRow[1])*currentDrawScale;
      currentCanvasContext.beginPath();currentCanvasContext.arc(currentFootLeft,currentFootTop,5,0,Math.PI*2);currentCanvasContext.stroke();
     }
    }else{currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText('발 중심 좌표 미등록 · 앵커와 별도 데이터입니다.',16,44);}
   }
   if(currentBaselineEnabled){currentCanvasContext.strokeStyle='#e5bd24';currentCanvasContext.beginPath();currentCanvasContext.moveTo(0,currentFixedAnchorTop);currentCanvasContext.lineTo(currentCanvasSize,currentFixedAnchorTop);currentCanvasContext.stroke();}
   if(currentShadowEnabled){currentCanvasContext.fillStyle='rgba(0,0,0,.22)';currentCanvasContext.beginPath();currentCanvasContext.ellipse(currentAnchorLeft,currentAnchorTop,currentOriginalRow[2]*currentDrawScale*.24,currentOriginalRow[3]*currentDrawScale*.06,0,0,Math.PI*2);currentCanvasContext.fill();}
   if(currentHeightGuideEnabled){
    const currentSourceHeight=currentEffectiveHeight,currentOutputHeight=currentEffectiveGameHeight,currentGuidePixels=80;
    if(Number.isFinite(currentSourceHeight)&&currentSourceHeight>0&&Number.isFinite(currentOutputHeight)&&currentOutputHeight>0){
     const currentGuideHeight=currentGuidePixels*currentSourceHeight/currentOutputHeight*currentDrawScale;
     const currentGuideX=32,currentGuideTop=currentAnchorTop-currentGuideHeight;
     currentCanvasContext.strokeStyle='#087e8b';currentCanvasContext.lineWidth=2;currentCanvasContext.beginPath();currentCanvasContext.moveTo(currentGuideX,currentAnchorTop);currentCanvasContext.lineTo(currentGuideX,currentGuideTop);currentCanvasContext.moveTo(currentGuideX-6,currentAnchorTop);currentCanvasContext.lineTo(currentGuideX+6,currentAnchorTop);currentCanvasContext.moveTo(currentGuideX-6,currentGuideTop);currentCanvasContext.lineTo(currentGuideX+6,currentGuideTop);currentCanvasContext.stroke();
     currentCanvasContext.fillStyle='#075b65';currentCanvasContext.fillText('게임 80px · 앵커 기준',currentGuideX+10,Math.max(42,currentGuideTop-8));
    }else{currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText('80px 기준 표시: 원본 신체 높이와 게임 출력 높이를 입력하세요.',16,44);}
   }
   if(currentBodyReference?.frame===currentActiveIndex+1){
    if(JSON.stringify(currentBodyReference.row)===JSON.stringify(currentDrawRow)){
     for(const [currentLineY,currentLineLabel] of [[currentBodyReference.headY,'머리끝'],[currentBodyReference.floorY,'바닥']]){
      const currentLinePosition=currentDrawTop+currentCropOffsetTop+currentLineY*currentDrawScale;
      currentCanvasContext.strokeStyle='#176e38';currentCanvasContext.lineWidth=2;currentCanvasContext.beginPath();currentCanvasContext.moveTo(currentDrawLeft+currentCropOffsetLeft,currentLinePosition);currentCanvasContext.lineTo(currentDrawLeft+currentCropOffsetLeft+currentDrawRow[2]*currentDrawScale,currentLinePosition);currentCanvasContext.stroke();currentCanvasContext.fillStyle='#135b2f';currentCanvasContext.fillText(currentLineLabel,currentDrawLeft+currentCropOffsetLeft+4,currentLinePosition-4);
     }
    }else{currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText('기준 프레임 좌표가 변경됐습니다. 기준 높이를 다시 계산하세요.',16,60);}
   }
   if(!currentPlayEnabled&&currentEditMode==='머리 기준'&&Number.isFinite(currentEditorState.headValues?.[currentSelectedIndex])){
    const currentHeadLine=currentDrawTop+currentCropOffsetTop+currentEditorState.headValues[currentSelectedIndex]*currentDrawScale;
    currentCanvasContext.strokeStyle='#176e38';currentCanvasContext.lineWidth=2;currentCanvasContext.beginPath();currentCanvasContext.moveTo(currentDrawLeft+currentCropOffsetLeft,currentHeadLine);currentCanvasContext.lineTo(currentDrawLeft+currentCropOffsetLeft+currentDrawRow[2]*currentDrawScale,currentHeadLine);currentCanvasContext.stroke();currentCanvasContext.fillStyle='#135b2f';currentCanvasContext.fillText(`머리끝 Y ${currentEditorState.headValues[currentSelectedIndex]}`,currentDrawLeft+currentCropOffsetLeft+4,currentHeadLine-4);
    if(currentBodyReference.height)currentCanvasContext.fillText(`신체 높이 ${currentBodyReference.height}px · 80px 배율 ${(80/currentBodyReference.height).toFixed(4)}`,16,60);
   }
   if(!currentPlayEnabled){currentCanvasContext.strokeStyle='#987000';currentCanvasContext.lineWidth=2;currentCanvasContext.strokeRect(currentOriginLeft+(currentDraftRow[0]-currentOriginalRow[0])*currentScaleValue,currentOriginTop+(currentDraftRow[1]-currentOriginalRow[1])*currentScaleValue,currentDraftRow[2]*currentScaleValue,currentDraftRow[3]*currentScaleValue);}
   currentCanvasContext.strokeStyle='#e22';currentCanvasContext.beginPath();currentCanvasContext.arc(currentAnchorLeft,currentAnchorTop,currentAnchorRadius,0,Math.PI*2);currentCanvasContext.moveTo(currentAnchorLeft-14,currentAnchorTop);currentCanvasContext.lineTo(currentAnchorLeft+14,currentAnchorTop);currentCanvasContext.moveTo(currentAnchorLeft,currentAnchorTop-14);currentCanvasContext.lineTo(currentAnchorLeft,currentAnchorTop+14);currentCanvasContext.stroke();
   currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText(`프레임 ${currentActiveIndex+1}/${currentRows.length} · ${currentPlayEnabled?(currentClipRecord?.loop===false&&currentPlaybackStep>=currentPlaybackIndices.length-1?'재생 완료 · 정지를 눌러 마지막 프레임을 편집하세요.':'재생 중에는 편집할 수 없습니다.'):(currentEditMode==='머리 기준'?'머리끝을 지정하면 80px 기준을 계산합니다.':currentEditMode+' 드래그 후 적용 버튼을 누르세요.')}`,16,24);
   currentCanvasContext.fillText(`크롭 X ${currentActiveRow[0]} · Y ${currentActiveRow[1]} · ${currentActiveRow[2]}×${currentActiveRow[3]} / 앵커 X ${currentActiveRow[4]} · Y ${currentActiveRow[5]}`,16,currentCanvasSize-16);
   if(currentPlayEnabled&&!(currentClipRecord?.loop===false&&currentPlaybackStep>=currentPlaybackIndices.length-1))requestAnimationFrame(drawCurrentEditorFrame);
  };
  const readCurrentPointer=currentEvent=>{const currentBounds=currentCanvasElement.getBoundingClientRect();return [Math.round(((currentEvent.clientX-currentBounds.left)*currentCanvasSize/currentBounds.width-currentOriginLeft)/currentScaleValue),Math.round(((currentEvent.clientY-currentBounds.top)*currentCanvasSize/currentBounds.height-currentOriginTop)/currentScaleValue)];};
  let currentDragStart=null,currentDragBackup=null;
  currentCanvasElement.onpointerdown=currentEvent=>{if(currentPlayEnabled)return;currentEvent.preventDefault();currentCanvasElement.setPointerCapture(currentEvent.pointerId);currentDragStart=readCurrentPointer(currentEvent);currentDragBackup=[...currentDraftRow];currentCanvasElement.onpointermove(currentEvent);};
  currentCanvasElement.onpointermove=currentEvent=>{
   if(!currentDragStart)return;const currentPoint=readCurrentPointer(currentEvent);
   if(currentEditMode==='머리 기준'){
    currentEditorState.headValues[currentSelectedIndex]=Math.max(0,Math.min(currentDraftRow[3]-1,currentOriginalRow[1]+currentPoint[1]-currentDraftRow[1]));
   }else if(currentEditMode==='배치 앵커'){
    currentDraftRow[4]=Math.max(0,Math.min(currentDraftRow[2]-1,currentOriginalRow[0]+currentPoint[0]-currentDraftRow[0]));currentDraftRow[5]=Math.max(0,Math.min(currentDraftRow[3]-1,currentOriginalRow[1]+currentPoint[1]-currentDraftRow[1]));
   }else{
    const currentLeft=Math.min(currentDragStart[0],currentPoint[0]),currentTop=Math.min(currentDragStart[1],currentPoint[1]);
    const currentWidth=Math.abs(currentPoint[0]-currentDragStart[0]),currentHeight=Math.abs(currentPoint[1]-currentDragStart[1]);
    if(currentWidth&&currentHeight){const currentAnchorX=currentDragBackup[0]+currentDragBackup[4],currentAnchorY=currentDragBackup[1]+currentDragBackup[5];currentDraftRow.splice(0,6,currentOriginalRow[0]+currentLeft,currentOriginalRow[1]+currentTop,currentWidth,currentHeight,Math.max(0,Math.min(currentWidth-1,currentAnchorX-currentOriginalRow[0]-currentLeft)),Math.max(0,Math.min(currentHeight-1,currentAnchorY-currentOriginalRow[1]-currentTop)));}
   }
   drawCurrentEditorFrame(performance.now());
  };
  currentCanvasElement.onpointerup=()=>{
   currentDragStart=null;
   if(currentEditMode==='머리 기준'){
    const currentHeadY=currentEditorState.headValues[currentSelectedIndex];
    if(JSON.stringify(currentDraftRow)!==JSON.stringify(currentOriginalRow)){currentEditorState.bodyReference=null;currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText('크롭·배치 앵커를 먼저 반영하세요.',16,60);return;}
    if(!Number.isFinite(currentHeadY)||currentHeadY>=currentOriginalRow[5]){currentEditorState.bodyReference=null;currentCanvasContext.fillStyle='#222';currentCanvasContext.fillText('머리끝을 배치 앵커보다 위에 지정하세요.',16,60);return;}
    currentEditorState.bodyReference={frame:currentSelectedIndex+1,row:[...currentOriginalRow],headY:currentHeadY,floorY:currentOriginalRow[5],height:currentOriginalRow[5]-currentHeadY};
    renderSpriteSheetPreview(currentImageData,currentFrameRows,currentFrameIndex,currentPlayEnabled,currentShadowEnabled,currentEditMode,currentSourceBounds,currentPlaybackRate,currentBaselineEnabled,currentOnionEnabled,currentPreviewClip,currentSourceRecord,currentGameSizeEnabled,currentReferenceHeight,currentGameBodyHeight,currentFeetEnabled,currentRestoredFeet,currentHeightGuideEnabled);
   }
  };
  currentCanvasElement.onpointercancel=()=>{if(currentDragBackup)currentDraftRow.splice(0,6,...currentDragBackup);currentDragStart=null;drawCurrentEditorFrame(performance.now());};
  drawCurrentEditorFrame(currentStartTime);
 };
 currentImageElement.src=currentImageData;
 return '크롭: 영역을 드래그 · 앵커: 클릭 또는 드래그 · 적용 전까지 출력에 반영되지 않습니다.';
})
