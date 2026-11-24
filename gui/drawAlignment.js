import {effectAlignmentBoundsError} from "./effectAlignmentBounds.mjs";

export async function drawAlignment(currentCanvasElement,currentDetailRecord,alignment,currentPlayEnabled,currentFrameIndex,currentHostEnabled,currentBoundsEnabled){
 currentCanvasElement.effectPreviewRevision=(currentCanvasElement.effectPreviewRevision||0)+1;
 const currentPreviewRevision=currentCanvasElement.effectPreviewRevision;
 const currentCanvasContext=currentCanvasElement.getContext('2d');
 currentCanvasContext.clearRect(0,0,640,640);
 const rejectCurrentPreviewInput=currentErrorMessage=>{
  currentCanvasContext.globalAlpha=1;currentCanvasContext.globalCompositeOperation='source-over';
  currentCanvasContext.clearRect(0,0,640,640);
  currentCanvasContext.fillStyle='#182329';currentCanvasContext.fillRect(0,0,640,640);
  currentCanvasContext.fillStyle='white';currentCanvasContext.fillText('입력 오류 · 미리보기를 중지했습니다.',16,24);
  currentCanvasContext.fillText(currentErrorMessage,16,48);
  return currentErrorMessage;
 };
 const currentTargetBounds=alignment.target.map(value=>value===""?NaN:Number(value));
 const currentFrameValues=alignment.frames,currentAlphaValue=Number(alignment.alpha);
 const currentRawFrameRows=Array.isArray(currentFrameValues)?currentFrameValues:currentFrameValues?.data;
 const currentFrameRows=currentRawFrameRows?.map(currentFrameRow=>currentFrameRow.map(currentCellValue=>typeof currentCellValue==='string'&&currentCellValue.trim()!==''?Number(currentCellValue):currentCellValue));
 const currentBoundsError=effectAlignmentBoundsError({target:currentTargetBounds,frames:currentFrameRows});
 if(currentBoundsError)return rejectCurrentPreviewInput(currentBoundsError);
 const {calculateEffectFramePlacement,sampleMothAnimationFrame,sampleEffectAnimationFrame,sampleFogAnimationFrame}=await import(currentDetailRecord.rendererModule);
 const currentImageValues=await Promise.all([currentDetailRecord.hostImage,currentDetailRecord.sheetImage].map(currentSourceUrl=>new Promise((resolveCurrentImage,rejectCurrentImage)=>{if(!currentSourceUrl){resolveCurrentImage(null);return;}const currentLoadedImage=new Image();currentLoadedImage.onload=()=>resolveCurrentImage(currentLoadedImage);currentLoadedImage.onerror=()=>rejectCurrentImage(Error('원본 이미지 로드 실패'));currentLoadedImage.src=currentSourceUrl;})));
 const [currentHostImage,currentSheetImage]=currentImageValues;
 if(currentCanvasElement.effectPreviewRevision!==currentPreviewRevision)return '최신 입력을 적용 중입니다.';
 const previewCanvasSize=640,previewHostMaximumHeight=420,previewHostMaximumWidth=520;
 const currentHostAspectRatio=currentHostImage?currentHostImage.width/currentHostImage.height:(currentDetailRecord.document.renderer==='fog'?2:1);
 const currentHostHeight=Math.min(previewHostMaximumHeight,previewHostMaximumWidth/currentHostAspectRatio),currentHostWidth=currentHostHeight*currentHostAspectRatio;
 const currentHostLeft=(previewCanvasSize-currentHostWidth)/2,currentHostTop=(previewCanvasSize-currentHostHeight)/2;
 const currentStartTime=performance.now();
 const drawCurrentEffectFrame=currentElapsedTime=>{
  if(!currentCanvasElement.isConnected||currentCanvasElement.effectPreviewRevision!==currentPreviewRevision)return;
  const currentMothPreviewEnabled=currentDetailRecord.document.alignment.texture==='moths';
  const currentMothMotion=currentPlayEnabled&&currentMothPreviewEnabled?sampleMothAnimationFrame(Math.max(0,currentElapsedTime-currentStartTime)):null;
  const currentFogMotion=currentPlayEnabled&&currentDetailRecord.document.renderer==='fog'?sampleFogAnimationFrame(Math.max(0,currentElapsedTime-currentStartTime)):null;
  const currentActiveFrame=currentPlayEnabled?(currentFogMotion?.frame??currentMothMotion?.frame??sampleEffectAnimationFrame(Math.max(0,currentElapsedTime-currentStartTime))):currentFrameIndex;
  currentCanvasElement.effectDisplayedFrame=currentActiveFrame;
  const currentFlightOffsetX=(currentMothMotion?.offsetX??0)*currentHostWidth;
  const currentFlightOffsetY=(currentMothMotion?.offsetY??0)*currentHostHeight;
  currentCanvasContext.globalAlpha=1;currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.fillStyle='#182329';currentCanvasContext.fillRect(0,0,640,640);
  if(currentHostEnabled&&currentHostImage)currentCanvasContext.drawImage(currentHostImage,currentHostLeft,currentHostTop,currentHostWidth,currentHostHeight);
  currentCanvasContext.globalCompositeOperation=['fireflies','fog'].includes(currentDetailRecord.document.alignment.texture)?'source-over':'lighter';
  const drawSelectedSheetFrame=(currentSelectedFrame,currentBlendWeight)=>{
   const currentPlacementValues=calculateEffectFramePlacement(currentTargetBounds,currentFrameRows[currentSelectedFrame]);
   const currentColumnIndex=currentSelectedFrame%4,currentRowIndex=Math.floor(currentSelectedFrame/4);
   const currentSourceLeft=Math.round(currentSheetImage.width*currentColumnIndex/4),currentSourceTop=Math.round(currentSheetImage.height*currentRowIndex/2);
   const currentSourceWidth=Math.round(currentSheetImage.width*(currentColumnIndex+1)/4)-currentSourceLeft,currentSourceHeight=Math.round(currentSheetImage.height*(currentRowIndex+1)/2)-currentSourceTop;
   currentCanvasContext.globalAlpha=currentAlphaValue*currentBlendWeight;
   currentCanvasContext.drawImage(currentSheetImage,currentSourceLeft,currentSourceTop,currentSourceWidth,currentSourceHeight,currentHostLeft+currentPlacementValues.left*currentHostWidth+currentFlightOffsetX,currentHostTop+currentPlacementValues.top*currentHostHeight+currentFlightOffsetY,currentPlacementValues.width*currentHostWidth,currentPlacementValues.height*currentHostHeight);
  };
  drawSelectedSheetFrame(currentActiveFrame,1-(currentFogMotion?.mix??0));
  if(currentFogMotion)drawSelectedSheetFrame(currentFogMotion.nextFrame,currentFogMotion.mix);
  currentCanvasContext.globalCompositeOperation='source-over';currentCanvasContext.globalAlpha=1;
  if(currentBoundsEnabled){currentCanvasContext.strokeStyle='#ff70be';currentCanvasContext.strokeRect(currentHostLeft+currentTargetBounds[0]*currentHostWidth,currentHostTop+currentTargetBounds[1]*currentHostHeight,(currentTargetBounds[2]-currentTargetBounds[0])*currentHostWidth,(currentTargetBounds[3]-currentTargetBounds[1])*currentHostHeight);}
  currentCanvasContext.fillStyle='white';currentCanvasContext.fillText(`프레임 ${currentActiveFrame+1}/8 · 좌표 검수 (맵 조명·색상 별도)`,16,24);
  if(currentPlayEnabled)requestAnimationFrame(drawCurrentEffectFrame);
 };
 requestAnimationFrame(drawCurrentEffectFrame);
 return currentDetailRecord.document.alignment.texture==='moths'?'나방 · 초당 6프레임 · 검수 비행 주기 4초 · 정지하면 이동 없이 좌표를 확인합니다.':'초당 6프레임 · 미저장 미리보기 · 분홍선: 대상 영역 · 정지하면 프레임을 개별 확인할 수 있습니다.';
}
