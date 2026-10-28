async (currentDetailRecord,currentLeftValue,currentTopValue,currentRightValue,currentBottomValue,currentAlphaValue,currentFrameValues,currentPlayEnabled,currentFrameIndex,currentHostEnabled,currentBoundsEnabled)=>{
 const currentCanvasElement=document.getElementById('effect-alignment-preview');
 if(!currentCanvasElement)return '미리보기 화면을 찾을 수 없습니다.';
 currentCanvasElement.effectPreviewRevision=(currentCanvasElement.effectPreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.effectPreviewRevision;
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 const rejectCurrentPreviewInput=currentErrorMessage=>{
  currentCanvasContext.globalAlpha=1;currentCanvasContext.globalCompositeOperation='source-over';
  currentCanvasContext.clearRect(0,0,640,640);
  currentCanvasContext.fillStyle='#182329';currentCanvasContext.fillRect(0,0,640,640);
  currentCanvasContext.fillStyle='white';currentCanvasContext.fillText('입력 오류 · 미리보기를 중지했습니다.',16,24);
  currentCanvasContext.fillText(currentErrorMessage,16,48);
  return currentErrorMessage;
 };
 if(!currentDetailRecord?.document)return rejectCurrentPreviewInput('이펙트를 먼저 불러오세요.');
 const currentTargetBounds=[currentLeftValue,currentTopValue,currentRightValue,currentBottomValue];
 const currentRawFrameRows=Array.isArray(currentFrameValues)?currentFrameValues:currentFrameValues?.data;
 const currentFrameRows=currentRawFrameRows?.map(currentFrameRow=>currentFrameRow.map(currentCellValue=>typeof currentCellValue==='string'&&currentCellValue.trim()!==''?Number(currentCellValue):currentCellValue));
 const currentCoordinateLabels=['왼쪽','위쪽','오른쪽','아래쪽'];
 const validateCurrentBounds=(currentBoundsValues,currentBoundsLabel)=>{
  if(!Array.isArray(currentBoundsValues)||currentBoundsValues.length!==4)return `${currentBoundsLabel}: 좌표 4개가 필요합니다.`;
  for(let currentCoordinateIndex=0;currentCoordinateIndex<4;currentCoordinateIndex++){
   const currentCoordinateValue=currentBoundsValues[currentCoordinateIndex];
   if(!Number.isFinite(currentCoordinateValue)||currentCoordinateValue<0||currentCoordinateValue>1)return `${currentBoundsLabel} · ${currentCoordinateLabels[currentCoordinateIndex]}: 0~1 사이 숫자를 입력하세요.`;
  }
  if(currentBoundsValues[0]>=currentBoundsValues[2]||currentBoundsValues[1]>=currentBoundsValues[3])return `${currentBoundsLabel}: 왼쪽 < 오른쪽, 위쪽 < 아래쪽이어야 합니다.`;
  return '';
 };
 const currentTargetError=validateCurrentBounds(currentTargetBounds,'대상 영역');
 if(currentTargetError)return rejectCurrentPreviewInput(currentTargetError);
 if(!Array.isArray(currentFrameRows)||currentFrameRows.length!==8)return rejectCurrentPreviewInput('프레임 영역은 8개가 필요합니다.');
 for(let currentRowIndex=0;currentRowIndex<8;currentRowIndex++){
  const currentFrameError=validateCurrentBounds(currentFrameRows[currentRowIndex],`프레임 ${currentRowIndex+1}`);
  if(currentFrameError)return rejectCurrentPreviewInput(currentFrameError);
 }
 const {calculateEffectFramePlacement,sampleMothAnimationFrame,sampleEffectAnimationFrame}=await import('__RENDERER_URL__');
 const currentImageValues=await Promise.all([currentDetailRecord.hostImage,currentDetailRecord.sheetImage].map(currentSourceUrl=>new Promise((resolveCurrentImage,rejectCurrentImage)=>{if(!currentSourceUrl){resolveCurrentImage(null);return;}const currentLoadedImage=new Image();currentLoadedImage.onload=()=>resolveCurrentImage(currentLoadedImage);currentLoadedImage.onerror=()=>rejectCurrentImage(Error('원본 이미지 로드 실패'));currentLoadedImage.src=currentSourceUrl;})));
 const [currentHostImage,currentSheetImage]=currentImageValues;
 if(currentCanvasElement.effectPreviewRevision!==currentPreviewRevision)return '최신 입력을 적용 중입니다.';
 const previewCanvasSize=640,previewHostMaximumHeight=420,previewHostMaximumWidth=520;
 const currentHostAspectRatio=currentHostImage?currentHostImage.width/currentHostImage.height:1;
 const currentHostHeight=Math.min(previewHostMaximumHeight,previewHostMaximumWidth/currentHostAspectRatio),currentHostWidth=currentHostHeight*currentHostAspectRatio;
 const currentHostLeft=(previewCanvasSize-currentHostWidth)/2,currentHostTop=(previewCanvasSize-currentHostHeight)/2;
 const currentStartTime=performance.now();
 const drawCurrentEffectFrame=currentElapsedTime=>{
  if(!currentCanvasElement.isConnected||currentCanvasElement.effectPreviewRevision!==currentPreviewRevision)return;
  const currentMothPreviewEnabled=currentDetailRecord.document.alignment.texture==='moths';
  const currentMothMotion=currentPlayEnabled&&currentMothPreviewEnabled?sampleMothAnimationFrame(Math.max(0,currentElapsedTime-currentStartTime)):null;
  const currentActiveFrame=currentPlayEnabled?(currentMothMotion?.frame??sampleEffectAnimationFrame(Math.max(0,currentElapsedTime-currentStartTime))):currentFrameIndex;
  const currentFlightOffsetX=(currentMothMotion?.offsetX??0)*currentHostWidth;
  const currentFlightOffsetY=(currentMothMotion?.offsetY??0)*currentHostHeight;
  const currentPlacementValues=calculateEffectFramePlacement(currentTargetBounds,currentFrameRows[currentActiveFrame]);
  const currentColumnIndex=currentActiveFrame%4,currentRowIndex=Math.floor(currentActiveFrame/4);
  const currentSourceLeft=Math.round(currentSheetImage.width*currentColumnIndex/4),currentSourceTop=Math.round(currentSheetImage.height*currentRowIndex/2);
  const currentSourceWidth=Math.round(currentSheetImage.width*(currentColumnIndex+1)/4)-currentSourceLeft,currentSourceHeight=Math.round(currentSheetImage.height*(currentRowIndex+1)/2)-currentSourceTop;
  currentCanvasContext.globalAlpha=1;currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.fillStyle='#182329';currentCanvasContext.fillRect(0,0,640,640);
  if(currentHostEnabled&&currentHostImage)currentCanvasContext.drawImage(currentHostImage,currentHostLeft,currentHostTop,currentHostWidth,currentHostHeight);
  currentCanvasContext.globalCompositeOperation=currentDetailRecord.document.alignment.texture==='fireflies'?'source-over':'lighter';currentCanvasContext.globalAlpha=currentAlphaValue;
  currentCanvasContext.drawImage(currentSheetImage,currentSourceLeft,currentSourceTop,currentSourceWidth,currentSourceHeight,currentHostLeft+currentPlacementValues.left*currentHostWidth+currentFlightOffsetX,currentHostTop+currentPlacementValues.top*currentHostHeight+currentFlightOffsetY,currentPlacementValues.width*currentHostWidth,currentPlacementValues.height*currentHostHeight);
  currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.globalAlpha=1;
  if(currentBoundsEnabled){currentCanvasContext.strokeStyle='#ff70be';currentCanvasContext.strokeRect(currentHostLeft+currentTargetBounds[0]*currentHostWidth,currentHostTop+currentTargetBounds[1]*currentHostHeight,(currentTargetBounds[2]-currentTargetBounds[0])*currentHostWidth,(currentTargetBounds[3]-currentTargetBounds[1])*currentHostHeight);}
  currentCanvasContext.fillStyle='white';currentCanvasContext.fillText(`프레임 ${currentActiveFrame+1}/8 · 좌표 검수 (맵 조명·색상 별도)`,16,24);
  if(currentPlayEnabled)requestAnimationFrame(drawCurrentEffectFrame);
 };
 requestAnimationFrame(drawCurrentEffectFrame);
 return currentDetailRecord.document.alignment.texture==='moths'?'나방 · 초당 6프레임 · 검수 비행 주기 4초 · 정지하면 이동 없이 좌표를 확인합니다.':'초당 6프레임 · 미저장 미리보기 · 분홍선: 대상 영역 · 정지하면 프레임을 개별 확인할 수 있습니다.';
}
