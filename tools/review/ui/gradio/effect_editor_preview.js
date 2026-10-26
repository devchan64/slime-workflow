async (currentDetailRecord,currentLeftValue,currentTopValue,currentRightValue,currentBottomValue,currentAlphaValue,currentFrameValues,currentPlayEnabled,currentFrameIndex,currentHostEnabled,currentBoundsEnabled)=>{
 const currentCanvasElement=document.getElementById('effect-alignment-preview');
 if(!currentCanvasElement||!currentDetailRecord.document)return '이펙트를 먼저 불러오세요.';
 const currentTargetBounds=[currentLeftValue,currentTopValue,currentRightValue,currentBottomValue];
 const currentFrameRows=Array.isArray(currentFrameValues)?currentFrameValues:currentFrameValues.data;
 if(!currentFrameRows||[currentTargetBounds,...currentFrameRows].some(currentBounds=>currentBounds.length!==4||currentBounds.some(currentValue=>!Number.isFinite(currentValue)||currentValue<0||currentValue>1)||currentBounds[0]>=currentBounds[2]||currentBounds[1]>=currentBounds[3]))return '좌표는 0~1이며 왼쪽 < 오른쪽, 위쪽 < 아래쪽이어야 합니다.';
 currentCanvasElement.effectPreviewRevision=(currentCanvasElement.effectPreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.effectPreviewRevision;
 const {calculateEffectFramePlacement}=await import('__RENDERER_URL__');
 const currentImageValues=await Promise.all([currentDetailRecord.hostImage,currentDetailRecord.sheetImage].map(currentSourceUrl=>new Promise((resolveCurrentImage,rejectCurrentImage)=>{if(!currentSourceUrl){resolveCurrentImage(null);return;}const currentLoadedImage=new Image();currentLoadedImage.onload=()=>resolveCurrentImage(currentLoadedImage);currentLoadedImage.onerror=()=>rejectCurrentImage(Error('원본 이미지 로드 실패'));currentLoadedImage.src=currentSourceUrl;})));
 const [currentHostImage,currentSheetImage]=currentImageValues;
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 const currentHostHeight=420,currentHostWidth=currentHostImage?currentHostHeight*currentHostImage.width/currentHostImage.height:currentHostHeight;
 const currentHostLeft=(640-currentHostWidth)/2,currentHostTop=110;
 const currentStartTime=performance.now();
 const drawCurrentEffectFrame=currentElapsedTime=>{
  if(!currentCanvasElement.isConnected||currentCanvasElement.effectPreviewRevision!==currentPreviewRevision)return;
  const currentActiveFrame=currentPlayEnabled?Math.floor(Math.max(0,currentElapsedTime-currentStartTime)/250)%8:currentFrameIndex;
  const currentPlacementValues=calculateEffectFramePlacement(currentTargetBounds,currentFrameRows[currentActiveFrame]);
  const currentColumnIndex=currentActiveFrame%4,currentRowIndex=Math.floor(currentActiveFrame/4);
  const currentSourceLeft=Math.round(currentSheetImage.width*currentColumnIndex/4),currentSourceTop=Math.round(currentSheetImage.height*currentRowIndex/2);
  const currentSourceWidth=Math.round(currentSheetImage.width*(currentColumnIndex+1)/4)-currentSourceLeft,currentSourceHeight=Math.round(currentSheetImage.height*(currentRowIndex+1)/2)-currentSourceTop;
  currentCanvasContext.globalAlpha=1;currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.fillStyle='#182329';currentCanvasContext.fillRect(0,0,640,640);
  if(currentHostEnabled&&currentHostImage)currentCanvasContext.drawImage(currentHostImage,currentHostLeft,currentHostTop,currentHostWidth,currentHostHeight);
  currentCanvasContext.globalCompositeOperation=currentDetailRecord.document.alignment.texture==='fireflies'?'source-over':'lighter';currentCanvasContext.globalAlpha=currentAlphaValue;
  currentCanvasContext.drawImage(currentSheetImage,currentSourceLeft,currentSourceTop,currentSourceWidth,currentSourceHeight,currentHostLeft+currentPlacementValues.left*currentHostWidth,currentHostTop+currentPlacementValues.top*currentHostHeight,currentPlacementValues.width*currentHostWidth,currentPlacementValues.height*currentHostHeight);
  currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.globalAlpha=1;
  if(currentBoundsEnabled){currentCanvasContext.strokeStyle='#ff70be';currentCanvasContext.strokeRect(currentHostLeft+currentTargetBounds[0]*currentHostWidth,currentHostTop+currentTargetBounds[1]*currentHostHeight,(currentTargetBounds[2]-currentTargetBounds[0])*currentHostWidth,(currentTargetBounds[3]-currentTargetBounds[1])*currentHostHeight);}
  currentCanvasContext.fillStyle='white';currentCanvasContext.fillText(`프레임 ${currentActiveFrame+1}/8 · 좌표 검수 (맵 조명·색상 별도)`,16,24);
  if(currentPlayEnabled)requestAnimationFrame(drawCurrentEffectFrame);
 };
 requestAnimationFrame(drawCurrentEffectFrame);
 return '미저장 미리보기 · 분홍선: 대상 영역 · 정지하면 프레임을 개별 확인할 수 있습니다.';
}
