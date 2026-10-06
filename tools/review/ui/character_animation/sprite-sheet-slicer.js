/* 시트 원본은 브라우저에 유지하며 적용할 때만 PNG 프레임으로 등록한다. */
(()=>{
'use strict';
const SHEET_MAX_PIXELS=32000000,SHEET_MAX_BYTES=32000000,SHEET_MAX_FRAMES=128,SHEET_PREVIEW_WIDTH=1000,SHEET_LINE_HIT_RADIUS=10;
function createUniformBoundaries(currentPixelSize,currentCellCount){
 if(!Number.isInteger(currentCellCount)||currentCellCount<1||currentCellCount>SHEET_MAX_FRAMES||currentCellCount>currentPixelSize)throw Error('행·열은 이미지 크기 이내의 1~128 정수여야 합니다.');
 return Array.from({length:currentCellCount+1},(_,currentBoundaryIndex)=>Math.round(currentPixelSize*currentBoundaryIndex/currentCellCount));
}
function validateSheetBoundaries(currentBoundaryValues,currentPixelSize){
 if(currentBoundaryValues.length<2||currentBoundaryValues.length>129||currentBoundaryValues.some((currentBoundaryValue,currentBoundaryIndex)=>!Number.isInteger(currentBoundaryValue)||currentBoundaryValue<0||currentBoundaryValue>currentPixelSize||(currentBoundaryIndex>0&&currentBoundaryValue<=currentBoundaryValues[currentBoundaryIndex-1])))throw Error('분할 좌표는 이미지 범위 안에서 오름차순 정수로 입력하세요.');
 return currentBoundaryValues;
}
function collectSheetRectangles(currentHorizontalCuts,currentVerticalCuts){
 if((currentHorizontalCuts.length-1)*(currentVerticalCuts.length-1)>SHEET_MAX_FRAMES)throw Error('한 번에 최대 128프레임입니다.');
 const currentCropRectangles=[];
 for(let currentRowIndex=0;currentRowIndex<currentVerticalCuts.length-1;currentRowIndex++)for(let currentColumnIndex=0;currentColumnIndex<currentHorizontalCuts.length-1;currentColumnIndex++)currentCropRectangles.push({x:currentHorizontalCuts[currentColumnIndex],y:currentVerticalCuts[currentRowIndex],width:currentHorizontalCuts[currentColumnIndex+1]-currentHorizontalCuts[currentColumnIndex],height:currentVerticalCuts[currentRowIndex+1]-currentVerticalCuts[currentRowIndex]});
 return currentCropRectangles;
}
function collectAppendNumbers(currentExistingCount,currentAddedCount){
 return Array.from({length:currentAddedCount},(_,currentFrameIndex)=>currentExistingCount+currentFrameIndex+1);
}
if(typeof module!=='undefined')module.exports={createUniformBoundaries,validateSheetBoundaries,collectSheetRectangles,collectAppendNumbers};
if(typeof window==='undefined')return;
let currentSheetImage=null,currentSheetName='',currentHorizontalCuts=[],currentVerticalCuts=[],currentSheetBusy=false,currentDraggedLine=null;
const getSheetCanvas=()=>document.getElementById('sprite-sheet-preview');
const writeSheetNotice=currentNoticeText=>{document.getElementById('sprite-sheet-notice').textContent=currentNoticeText;};
function requireSheetImage(){if(!currentSheetImage)throw Error('시트 이미지를 먼저 불러오세요.');if(currentSheetBusy)throw Error('프레임 등록이 끝난 뒤 사용하세요.');}
function drawSheetPreview(){
 const currentPreviewCanvas=getSheetCanvas();if(!currentPreviewCanvas||!currentSheetImage)return;
 const currentPreviewScale=Math.min(1,SHEET_PREVIEW_WIDTH/currentSheetImage.naturalWidth);
 currentPreviewCanvas.width=Math.round(currentSheetImage.naturalWidth*currentPreviewScale);currentPreviewCanvas.height=Math.round(currentSheetImage.naturalHeight*currentPreviewScale);
 const currentDrawingContext=currentPreviewCanvas.getContext('2d');currentDrawingContext.drawImage(currentSheetImage,0,0,currentPreviewCanvas.width,currentPreviewCanvas.height);
 currentDrawingContext.lineWidth=2;currentDrawingContext.strokeStyle='#ff3030';
 for(const currentBoundaryValue of currentHorizontalCuts){currentDrawingContext.beginPath();currentDrawingContext.moveTo(currentBoundaryValue*currentPreviewScale,0);currentDrawingContext.lineTo(currentBoundaryValue*currentPreviewScale,currentPreviewCanvas.height);currentDrawingContext.stroke();}
 for(const currentBoundaryValue of currentVerticalCuts){currentDrawingContext.beginPath();currentDrawingContext.moveTo(0,currentBoundaryValue*currentPreviewScale);currentDrawingContext.lineTo(currentPreviewCanvas.width,currentBoundaryValue*currentPreviewScale);currentDrawingContext.stroke();}
 const currentCropRectangles=collectSheetRectangles(currentHorizontalCuts,currentVerticalCuts);
 const currentAppendNumbers=collectAppendNumbers(window.spriteV2FrameCount(),currentCropRectangles.length);
 currentDrawingContext.font='bold 16px sans-serif';
 currentCropRectangles.forEach((currentCropRectangle,currentFrameNumber)=>{const currentLabelLeft=currentCropRectangle.x*currentPreviewScale+4,currentLabelTop=currentCropRectangle.y*currentPreviewScale+4;currentDrawingContext.fillStyle='#000';currentDrawingContext.fillRect(currentLabelLeft,currentLabelTop,42,22);currentDrawingContext.fillStyle='#fff';currentDrawingContext.fillText(String(currentAppendNumbers[currentFrameNumber]),currentLabelLeft+4,currentLabelTop+17);});
 writeSheetNotice(`${currentSheetName} · ${currentSheetImage.naturalWidth}×${currentSheetImage.naturalHeight}px · ${currentCropRectangles.length}프레임 · 추가 예정 ${currentAppendNumbers[0]}~${currentAppendNumbers.at(-1)}번 · 왼쪽→오른쪽, 위→아래 순서. 빨간 선을 드래그해 조정하세요.`);
 currentPreviewCanvas.onpointerdown=currentPointerEvent=>{
  if(currentSheetBusy)return;
  const currentCanvasBounds=currentPreviewCanvas.getBoundingClientRect();
  const currentPointerCoordinates={x:(currentPointerEvent.clientX-currentCanvasBounds.left)*currentSheetImage.naturalWidth/currentCanvasBounds.width,y:(currentPointerEvent.clientY-currentCanvasBounds.top)*currentSheetImage.naturalHeight/currentCanvasBounds.height};
  let currentNearestDistance=Infinity;currentDraggedLine=null;
  for(const [currentAxisName,currentBoundaryValues,currentScreenScale] of [['x',currentHorizontalCuts,currentCanvasBounds.width/currentSheetImage.naturalWidth],['y',currentVerticalCuts,currentCanvasBounds.height/currentSheetImage.naturalHeight]])currentBoundaryValues.forEach((currentBoundaryValue,currentBoundaryIndex)=>{const currentPointerDistance=Math.abs(currentPointerCoordinates[currentAxisName]-currentBoundaryValue)*currentScreenScale;if(currentPointerDistance<=SHEET_LINE_HIT_RADIUS&&currentPointerDistance<currentNearestDistance){currentNearestDistance=currentPointerDistance;currentDraggedLine={axis:currentAxisName,index:currentBoundaryIndex};}});
  if(currentDraggedLine){currentPreviewCanvas.setPointerCapture(currentPointerEvent.pointerId);currentPointerEvent.preventDefault();}
 };
 currentPreviewCanvas.onpointermove=currentPointerEvent=>{
  if(!currentDraggedLine||currentSheetBusy)return;
  const currentCanvasBounds=currentPreviewCanvas.getBoundingClientRect(),currentAxisHorizontal=currentDraggedLine.axis==='x';
  const currentImageSize=currentAxisHorizontal?currentSheetImage.naturalWidth:currentSheetImage.naturalHeight;
  const currentBoundaryValues=currentAxisHorizontal?currentHorizontalCuts:currentVerticalCuts,currentBoundaryIndex=currentDraggedLine.index;
  const currentPointerPosition=Math.round((currentAxisHorizontal?currentPointerEvent.clientX-currentCanvasBounds.left:currentPointerEvent.clientY-currentCanvasBounds.top)*currentImageSize/(currentAxisHorizontal?currentCanvasBounds.width:currentCanvasBounds.height));
  currentBoundaryValues[currentBoundaryIndex]=Math.max(currentBoundaryIndex?currentBoundaryValues[currentBoundaryIndex-1]+1:0,Math.min(currentBoundaryIndex<currentBoundaryValues.length-1?currentBoundaryValues[currentBoundaryIndex+1]-1:currentImageSize,currentPointerPosition));drawSheetPreview();
 };
 currentPreviewCanvas.onpointerup=currentPreviewCanvas.onpointercancel=()=>{currentDraggedLine=null;};
}
async function loadSheetFile(currentImageFile){
 if(currentSheetBusy)throw Error('프레임 등록이 끝난 뒤 사용하세요.');
 if(!['image/png','image/jpeg','image/webp'].includes(currentImageFile.type)||currentImageFile.size>SHEET_MAX_BYTES)throw Error('PNG/JPEG/WebP, 최대 32MB 시트를 사용하세요.');
 const currentObjectUrl=URL.createObjectURL(currentImageFile),currentLoadedImage=new Image();
 try{currentLoadedImage.src=currentObjectUrl;await currentLoadedImage.decode();if(currentLoadedImage.naturalWidth*currentLoadedImage.naturalHeight>SHEET_MAX_PIXELS)throw Error('시트는 최대 3200만 픽셀입니다.');}catch(currentLoadError){URL.revokeObjectURL(currentObjectUrl);throw currentLoadError;}
 if(currentSheetImage)URL.revokeObjectURL(currentSheetImage.src);
 currentSheetImage=currentLoadedImage;currentSheetName=currentImageFile.name||'클립보드 시트';currentHorizontalCuts=[0,currentLoadedImage.naturalWidth];currentVerticalCuts=[0,currentLoadedImage.naturalHeight];drawSheetPreview();
}
window.spriteSheetControls={
 refresh:drawSheetPreview,
 upload:()=>{const currentFileInput=document.createElement('input');currentFileInput.type='file';currentFileInput.accept='image/png,image/jpeg,image/webp';currentFileInput.hidden=true;document.body.append(currentFileInput);currentFileInput.onchange=()=>{if(currentFileInput.files[0])loadSheetFile(currentFileInput.files[0]).catch(currentLoadError=>writeSheetNotice(currentLoadError.message));currentFileInput.remove();};currentFileInput.oncancel=()=>currentFileInput.remove();currentFileInput.click();return '시트 파일을 선택하세요. 미리보기를 확인한 뒤 행·열을 지정하세요.';},
 paste:async()=>{const currentClipboardItems=await navigator.clipboard.read();for(const currentClipboardItem of currentClipboardItems){const currentImageType=currentClipboardItem.types.find(currentMimeType=>['image/png','image/jpeg','image/webp'].includes(currentMimeType));if(currentImageType){await loadSheetFile(new File([await currentClipboardItem.getType(currentImageType)],'클립보드 시트',{type:currentImageType}));return '시트 이미지를 불러왔습니다.';}}throw Error('클립보드에 지원하는 이미지가 없습니다.');},
 grid:(currentColumnCount,currentRowCount)=>{requireSheetImage();if(currentColumnCount*currentRowCount>SHEET_MAX_FRAMES)throw Error('한 번에 최대 128프레임입니다.');const currentNextHorizontal=createUniformBoundaries(currentSheetImage.naturalWidth,currentColumnCount),currentNextVertical=createUniformBoundaries(currentSheetImage.naturalHeight,currentRowCount);currentHorizontalCuts=currentNextHorizontal;currentVerticalCuts=currentNextVertical;drawSheetPreview();return window.spriteSheetControls.read();},
 read:()=>{requireSheetImage();return [currentHorizontalCuts.join(', '),currentVerticalCuts.join(', '),'현재 분할 좌표를 읽었습니다. 외곽 좌표를 좁히면 여백을 제외할 수 있습니다.'];},
 coordinates:(currentHorizontalText,currentVerticalText)=>{requireSheetImage();const parseBoundaryText=currentInputText=>{if(!/^\s*\d+(\s*,\s*\d+)+\s*$/.test(currentInputText))throw Error('좌표를 쉼표로 구분한 정수로 입력하세요.');return currentInputText.split(',').map(Number);};const currentNextHorizontal=validateSheetBoundaries(parseBoundaryText(currentHorizontalText),currentSheetImage.naturalWidth),currentNextVertical=validateSheetBoundaries(parseBoundaryText(currentVerticalText),currentSheetImage.naturalHeight);collectSheetRectangles(currentNextHorizontal,currentNextVertical);currentHorizontalCuts=currentNextHorizontal;currentVerticalCuts=currentNextVertical;drawSheetPreview();return window.spriteSheetControls.read();},
 apply:async()=>{
  requireSheetImage();const currentCropRectangles=collectSheetRectangles(currentHorizontalCuts,currentVerticalCuts);const currentExpectedProject=window.spriteV2ValidateSheet(currentCropRectangles.length);currentSheetBusy=true;
  const currentAppendNumbers=collectAppendNumbers(currentExpectedProject.frameCount,currentCropRectangles.length);
  try{const currentFrameFiles=[];for(const [currentFrameNumber,currentCropRectangle] of currentCropRectangles.entries()){const currentCropCanvas=document.createElement('canvas');currentCropCanvas.width=currentCropRectangle.width;currentCropCanvas.height=currentCropRectangle.height;currentCropCanvas.getContext('2d').drawImage(currentSheetImage,currentCropRectangle.x,currentCropRectangle.y,currentCropRectangle.width,currentCropRectangle.height,0,0,currentCropRectangle.width,currentCropRectangle.height);const currentFrameBlob=await new Promise(currentResolveBlob=>currentCropCanvas.toBlob(currentResolveBlob,'image/png'));if(!currentFrameBlob||currentFrameBlob.size>8000000)throw Error('분할 프레임은 한 장당 8MB 이하여야 합니다.');currentFrameFiles.push(new File([currentFrameBlob],`${currentSheetName.replace(/\.[^.]+$/,'')}-${String(currentAppendNumbers[currentFrameNumber]).padStart(3,'0')}.png`,{type:'image/png'}));}await window.spriteV2AppendSheet(currentFrameFiles,currentExpectedProject);return `${currentFrameFiles.length}프레임을 추가했습니다. 실행 취소로 되돌리거나 수정본 저장으로 보존하세요.`;}finally{currentSheetBusy=false;}
 }
};
window.spriteSheetActionControls=async(currentActionName)=>{if(!['upload','paste','apply'].includes(currentActionName))throw Error('지원하지 않는 시트 명령입니다.');return await window.spriteSheetControls[currentActionName]();};
})();
