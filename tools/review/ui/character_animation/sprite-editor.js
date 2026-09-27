'use strict';
// 출력·좌표 계산은 브라우저 미리보기와 PNG 내보내기가 함께 사용한다.
const SPRITE_DIRECTION_LABELS={down_left:'전방 좌측',down_right:'전방 우측',up_left:'후방 좌측',up_right:'후방 우측'};
const SPRITE_FRAME_FIELDS={center:'원본 중심 X',floor:'원본 바닥 Y',head:'원본 머리 Y',anchorX:'기준점 X',anchorY:'기준점 Y',x:'배치 X',y:'배치 Y',scale:'배율'};
const SPRITE_OUTPUT_FOOT_RATIO=.96;
const SPRITE_UNDO_RECORD_LIMIT=40;
const SPRITE_EXPORT_FRAME_LIMIT=128;
const SPRITE_CUSTOM_GUIDE_LIMIT=32;
const SPRITE_NUDGE_DIRECTION_STEPS={up:{x:0,y:-1},left:{x:-1,y:0},right:{x:1,y:0},down:{x:0,y:1}};
const SPRITE_GUIDE_COLOR_VALUES={center:'#00e5ff',floor:'#ffe338',head:'#f18aff',anchor:'#ff646d'};
const SPRITE_GUIDE_DISPLAY_STYLE={outline:'#101820',lineWidth:2,outlineWidth:4,dashLength:7,dashGap:5,anchorRadius:7,fontSize:11,labelPadding:4,labelHeight:19,labelInset:4};
function calculateSpriteOutputAnchor(outputCellPixels){return{x:outputCellPixels/2,y:Math.round(outputCellPixels*SPRITE_OUTPUT_FOOT_RATIO)};}
function calculateSpriteDrawRectangle(currentFrameRecord,currentFrameSettings,outputCellPixels){
 const outputAnchorPoint=calculateSpriteOutputAnchor(outputCellPixels);
 return{x:outputAnchorPoint.x-currentFrameSettings.anchorX*currentFrameSettings.scale+currentFrameSettings.x,y:outputAnchorPoint.y-currentFrameSettings.anchorY*currentFrameSettings.scale+currentFrameSettings.y,width:currentFrameRecord.rect.width*currentFrameSettings.scale,height:currentFrameRecord.rect.height*currentFrameSettings.scale};
}
function createSpriteDefaultSettings(currentFrameRecord,outputCellPixels,currentBodyBounds,useRegisteredAssetAnchor=false){
 const outputAnchorPoint=calculateSpriteOutputAnchor(outputCellPixels);
 const currentFrameScale=Math.min(outputCellPixels/currentFrameRecord.rect.width,outputCellPixels/currentFrameRecord.rect.height);
 return{center:currentFrameRecord.anchor.x,floor:currentBodyBounds.bottom-1,head:currentBodyBounds.top,anchorX:currentFrameRecord.anchor.x,anchorY:currentFrameRecord.anchor.y,x:useRegisteredAssetAnchor?0:currentFrameRecord.anchor.x*currentFrameScale-outputAnchorPoint.x,y:useRegisteredAssetAnchor?0:currentFrameRecord.anchor.y*currentFrameScale-outputAnchorPoint.y,scale:currentFrameScale};
}
function calculateSpritePointerPosition(pointerClientPosition,canvasClientBounds,outputCellPixels){
 return{x:(pointerClientPosition.x-canvasClientBounds.left)*outputCellPixels/canvasClientBounds.width,y:(pointerClientPosition.y-canvasClientBounds.top)*outputCellPixels/canvasClientBounds.height};
}
function createSpriteSheetLayout(sourceFrameRecords,outputCellPixels){
 if(!sourceFrameRecords.length||sourceFrameRecords.length>SPRITE_EXPORT_FRAME_LIMIT)throw Error('시트는 1~128프레임을 지원합니다.');
 const sourceDirectionNames=Object.keys(SPRITE_DIRECTION_LABELS).filter(directionKeyName=>sourceFrameRecords.some(currentFrameRecord=>currentFrameRecord.direction===directionKeyName));
 if(sourceFrameRecords.some(currentFrameRecord=>!sourceDirectionNames.includes(currentFrameRecord.direction)))throw Error('지원하지 않는 방향입니다.');
 const directionFrameGroups=sourceDirectionNames.map(directionKeyName=>sourceFrameRecords.filter(currentFrameRecord=>currentFrameRecord.direction===directionKeyName));
 const outputColumnCount=Math.max(...directionFrameGroups.map(currentFrameGroup=>currentFrameGroup.length));
 if(outputColumnCount*outputCellPixels>16384||sourceDirectionNames.length*outputColumnCount*outputCellPixels**2>33554432)throw Error('출력 시트가 너무 큽니다. 셀 크기나 프레임 범위를 줄이세요.');
 return{width:outputColumnCount*outputCellPixels,height:sourceDirectionNames.length*outputCellPixels,columns:outputColumnCount,rows:sourceDirectionNames.length,frames:directionFrameGroups.flatMap((currentFrameGroup,directionRowIndex)=>currentFrameGroup.map((currentFrameRecord,frameColumnIndex)=>({frame:currentFrameRecord,x:frameColumnIndex*outputCellPixels,y:directionRowIndex*outputCellPixels})))};
}
function validateSpriteFrameSettings(currentFrameSettings){
 if(Object.keys(currentFrameSettings).length!==Object.keys(SPRITE_FRAME_FIELDS).length||Object.keys(SPRITE_FRAME_FIELDS).some(currentFieldName=>!Number.isFinite(currentFrameSettings[currentFieldName])||Math.abs(currentFrameSettings[currentFieldName])>8192))throw Error('좌표는 -8192~8192 범위의 유한한 숫자여야 합니다.');
 if(currentFrameSettings.scale<.01||currentFrameSettings.scale>8||currentFrameSettings.floor<=currentFrameSettings.head)throw Error('배율은 0.01~8, 머리선은 바닥선보다 위여야 합니다.');
}
function calculateSpriteScaleNudge(currentFrameSettings,bodyHeightDelta){
 validateSpriteFrameSettings(currentFrameSettings);
 if(![-1,1].includes(bodyHeightDelta))throw Error('크기 조절은 높이 ±1px만 지원합니다.');
 const sourceBodyHeight=currentFrameSettings.floor-currentFrameSettings.head;
 const nextFrameSettings={...currentFrameSettings,scale:(sourceBodyHeight*currentFrameSettings.scale+bodyHeightDelta)/sourceBodyHeight};
 validateSpriteFrameSettings(nextFrameSettings);return nextFrameSettings;
}
if(typeof module!=='undefined')module.exports={calculateSpriteScaleNudge,calculateSpriteOutputAnchor,calculateSpriteDrawRectangle,createSpriteDefaultSettings,calculateSpritePointerPosition,createSpriteSheetLayout,validateSpriteFrameSettings};
if(typeof document!=='undefined')void (async function initializeSpriteEditorComponent(){
 const spriteRootElement=document.getElementById('sprite-editor-root')||document.querySelector('main');
 if(spriteRootElement.dataset.initialized==='true')return;
 spriteRootElement.dataset.initialized='true';
 const findSpriteElement=currentElementName=>spriteRootElement.querySelector('#sprite-'+currentElementName);
 const spriteServerBase=window.spriteEditorServerBase||window.location.origin;
 const resolveSpriteUrl=currentPathValue=>new URL(currentPathValue,spriteServerBase).toString();
 const spriteCanvasElement=findSpriteElement('canvas');
 const spriteImageCache=new Map(),spriteBodyBounds=new Map(),spriteUndoRecords=[];
 let spriteSourceRecord=null,spriteProjectDocument=null,spriteFramePosition=0,spritePlaybackHandle=null,spriteLoadingVersion=0,spriteDirtyState=false,spriteBusyState=false,spriteDragOrigin=null,spriteSavedSnapshot=null;
 const readSpriteCellPixels=()=>spriteProjectDocument?.output.cellSize||spriteSourceRecord?.frames[0].rect.width||384;
 const readSpriteDirectionFrames=()=>spriteSourceRecord?.frames.filter(currentFrameRecord=>currentFrameRecord.direction===findSpriteElement('direction').value)||[];
 const readSpriteCurrentFrame=()=>readSpriteDirectionFrames()[spriteFramePosition];
 const readSpriteCurrentSettings=()=>spriteProjectDocument?.frames[readSpriteCurrentFrame()?.frameId];
 function appendSpriteStatusMessage(currentStatusText){findSpriteElement('status').textContent=currentStatusText;const currentLogElement=findSpriteElement('log');currentLogElement.textContent=(currentLogElement.textContent+'\n'+new Date().toLocaleTimeString()+' / sprite-editor / '+currentStatusText).split('\n').slice(-40).join('\n');}
 function updateSpriteControlStates(){
  for(const currentButtonElement of spriteRootElement.querySelectorAll('button')){
   const currentButtonName=currentButtonElement.id;
   let disabledReasonText=spriteBusyState?'원본 로딩 완료 후 사용할 수 있습니다.':!spriteSourceRecord?'에셋 또는 완료된 결과 ID를 먼저 불러오세요.':'';
   if(['sprite-load','sprite-asset-load'].includes(currentButtonName))disabledReasonText=spriteBusyState?'현재 작업 완료 후 다시 불러오세요.':'';
   if(currentButtonName==='sprite-undo'&&!spriteUndoRecords.length)disabledReasonText='편집한 뒤 실행 취소할 수 있습니다.';
   if(currentButtonName==='sprite-stop'&&spritePlaybackHandle===null)disabledReasonText='재생 버튼을 누르면 일시정지할 수 있습니다.';
   if(currentButtonName==='sprite-play'&&spritePlaybackHandle!==null)disabledReasonText='현재 재생 중입니다. 일시정지 후 다시 재생하세요.';
   currentButtonElement.disabled=Boolean(disabledReasonText);currentButtonElement.title=disabledReasonText;currentButtonElement.setAttribute('aria-description',disabledReasonText);
  }
  for(const currentInputElement of spriteRootElement.querySelectorAll('input,select'))currentInputElement.disabled=spriteBusyState||(!spriteSourceRecord&&!['sprite-asset','sprite-job'].includes(currentInputElement.id));
 }
 function stopSpritePlayback(){if(spritePlaybackHandle!==null)cancelAnimationFrame(spritePlaybackHandle);spritePlaybackHandle=null;updateSpriteControlStates();}
 function rememberSpriteDocumentChange(){stopSpritePlayback();spriteUndoRecords.push(structuredClone(spriteProjectDocument));if(spriteUndoRecords.length>SPRITE_UNDO_RECORD_LIMIT)spriteUndoRecords.shift();spriteDirtyState=true;}
 async function requestSpriteManagementCommand(currentCommandName,currentCommandPayload){
  const commandResponseValue=await fetch(resolveSpriteUrl('/management/command'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:'character-animation',command:currentCommandName,payload:currentCommandPayload})});
  const commandResultValue=await commandResponseValue.json();if(!commandResponseValue.ok||commandResultValue.error)throw Error(commandResultValue.error||'관리 명령 실패');return commandResultValue;
 }
 async function loadSpriteSourceImage(currentImageUrl){
  const resolvedImageUrl=resolveSpriteUrl(currentImageUrl);
  if(!spriteImageCache.has(resolvedImageUrl)){
   const loadedImageValue=await new Promise((resolveImageLoad,rejectImageLoad)=>{const currentImageElement=new Image();currentImageElement.onload=()=>resolveImageLoad(currentImageElement);currentImageElement.onerror=()=>rejectImageLoad(Error('이미지 로드 실패: '+currentImageUrl));currentImageElement.src=resolvedImageUrl;});
   spriteImageCache.set(resolvedImageUrl,loadedImageValue);
  }
  return spriteImageCache.get(resolvedImageUrl);
 }
 function measureSpriteBodyBounds(currentFrameRecord){
  const measureCanvasElement=document.createElement('canvas');measureCanvasElement.width=currentFrameRecord.rect.width;measureCanvasElement.height=currentFrameRecord.rect.height;
  const measureCanvasContext=measureCanvasElement.getContext('2d',{willReadFrequently:true}),currentFrameRect=currentFrameRecord.rect;
  measureCanvasContext.drawImage(spriteImageCache.get(resolveSpriteUrl(currentFrameRecord.url)),currentFrameRect.x,currentFrameRect.y,currentFrameRect.width,currentFrameRect.height,0,0,currentFrameRect.width,currentFrameRect.height);
  const measuredImagePixels=measureCanvasContext.getImageData(0,0,measureCanvasElement.width,measureCanvasElement.height).data;
  let firstOpaqueRow=measureCanvasElement.height,lastOpaqueRow=-1;
  for(let currentPixelIndex=3;currentPixelIndex<measuredImagePixels.length;currentPixelIndex+=4)if(measuredImagePixels[currentPixelIndex]>=128){const currentPixelRow=Math.floor((currentPixelIndex-3)/4/measureCanvasElement.width);firstOpaqueRow=Math.min(firstOpaqueRow,currentPixelRow);lastOpaqueRow=Math.max(lastOpaqueRow,currentPixelRow);}
  if(lastOpaqueRow<=firstOpaqueRow)throw Error('검수할 불투명 몸체 영역이 없습니다: '+currentFrameRecord.frameId);
  return{top:firstOpaqueRow,bottom:lastOpaqueRow+1};
 }
 function drawSpriteFrameImage(currentCanvasContext,currentFrameRecord,currentFrameSettings,outputCellPixels){
  const currentFrameRect=currentFrameRecord.rect,currentDrawRect=calculateSpriteDrawRectangle(currentFrameRecord,currentFrameSettings,outputCellPixels);
  currentCanvasContext.drawImage(spriteImageCache.get(resolveSpriteUrl(currentFrameRecord.url)),currentFrameRect.x,currentFrameRect.y,currentFrameRect.width,currentFrameRect.height,currentDrawRect.x,currentDrawRect.y,currentDrawRect.width,currentDrawRect.height);
 }
 function prepareSpriteCanvasContext(currentCanvasElement,outputCellPixels){currentCanvasElement.width=outputCellPixels;currentCanvasElement.height=outputCellPixels;return currentCanvasElement.getContext('2d');}
 function drawSpriteGuideLines(currentCanvasContext,currentFrameSettings,outputCellPixels){
  const outputAnchorPoint=calculateSpriteOutputAnchor(outputCellPixels);
  const transformSpriteGuidePoint=(sourcePointX,sourcePointY)=>({x:outputAnchorPoint.x+(sourcePointX-currentFrameSettings.anchorX)*currentFrameSettings.scale+currentFrameSettings.x,y:outputAnchorPoint.y+(sourcePointY-currentFrameSettings.anchorY)*currentFrameSettings.scale+currentFrameSettings.y});
  const guideDisplayStyle=SPRITE_GUIDE_DISPLAY_STYLE;
  const guidePixelRatio=outputCellPixels/Math.max(1,currentCanvasContext.canvas.getBoundingClientRect().width);
  function strokeSpriteGuideLine(firstPointX,firstPointY,lastPointX,lastPointY,guideColorValue){
   currentCanvasContext.beginPath();currentCanvasContext.moveTo(firstPointX,firstPointY);currentCanvasContext.lineTo(lastPointX,lastPointY);
   currentCanvasContext.strokeStyle=guideDisplayStyle.outline;currentCanvasContext.lineWidth=guideDisplayStyle.outlineWidth*guidePixelRatio;currentCanvasContext.stroke();
   currentCanvasContext.strokeStyle=guideColorValue;currentCanvasContext.lineWidth=guideDisplayStyle.lineWidth*guidePixelRatio;currentCanvasContext.stroke();
  }
  function drawSpriteGuideLabel(currentLabelText,currentLabelPosition,currentLabelColor){
   const currentLabelPadding=guideDisplayStyle.labelPadding*guidePixelRatio,currentLabelHeight=guideDisplayStyle.labelHeight*guidePixelRatio,currentLabelInset=guideDisplayStyle.labelInset*guidePixelRatio;
   const currentLabelWidth=currentCanvasContext.measureText(currentLabelText).width+currentLabelPadding*2;
   const currentLabelTop=Math.max(currentLabelInset,Math.min(outputCellPixels-currentLabelHeight-currentLabelInset,currentLabelPosition-currentLabelHeight/2));
   currentCanvasContext.fillStyle=guideDisplayStyle.outline;currentCanvasContext.fillRect(currentLabelInset,currentLabelTop,currentLabelWidth,currentLabelHeight);
   currentCanvasContext.fillStyle=currentLabelColor;currentCanvasContext.fillText(currentLabelText,currentLabelInset+currentLabelPadding,currentLabelTop+currentLabelHeight/2);
  }
  const headGuidePoint=transformSpriteGuidePoint(currentFrameSettings.center,currentFrameSettings.head),floorGuidePoint=transformSpriteGuidePoint(currentFrameSettings.center,currentFrameSettings.floor),anchorGuidePoint=transformSpriteGuidePoint(currentFrameSettings.anchorX,currentFrameSettings.anchorY);
  currentCanvasContext.save();currentCanvasContext.lineCap='butt';
  currentCanvasContext.setLineDash([guideDisplayStyle.dashLength*guidePixelRatio,guideDisplayStyle.dashGap*guidePixelRatio]);
  strokeSpriteGuideLine(outputAnchorPoint.x,0,outputAnchorPoint.x,outputCellPixels,SPRITE_GUIDE_COLOR_VALUES.center);strokeSpriteGuideLine(0,outputAnchorPoint.y,outputCellPixels,outputAnchorPoint.y,SPRITE_GUIDE_COLOR_VALUES.floor);currentCanvasContext.setLineDash([]);
  strokeSpriteGuideLine(headGuidePoint.x,headGuidePoint.y,floorGuidePoint.x,floorGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.center);strokeSpriteGuideLine(0,headGuidePoint.y,outputCellPixels,headGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.head);strokeSpriteGuideLine(0,floorGuidePoint.y,outputCellPixels,floorGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.floor);
  const anchorMarkerRadius=guideDisplayStyle.anchorRadius*guidePixelRatio;
  currentCanvasContext.beginPath();currentCanvasContext.arc(anchorGuidePoint.x,anchorGuidePoint.y,anchorMarkerRadius,0,Math.PI*2);currentCanvasContext.fillStyle=guideDisplayStyle.outline;currentCanvasContext.fill();currentCanvasContext.strokeStyle=SPRITE_GUIDE_COLOR_VALUES.anchor;currentCanvasContext.lineWidth=guideDisplayStyle.lineWidth*guidePixelRatio;currentCanvasContext.stroke();
  strokeSpriteGuideLine(anchorGuidePoint.x-anchorMarkerRadius,anchorGuidePoint.y,anchorGuidePoint.x+anchorMarkerRadius,anchorGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.anchor);strokeSpriteGuideLine(anchorGuidePoint.x,anchorGuidePoint.y-anchorMarkerRadius,anchorGuidePoint.x,anchorGuidePoint.y+anchorMarkerRadius,SPRITE_GUIDE_COLOR_VALUES.anchor);
  currentCanvasContext.font=`bold ${guideDisplayStyle.fontSize*guidePixelRatio}px sans-serif`;currentCanvasContext.textBaseline='middle';
  drawSpriteGuideLabel('머리',headGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.head);drawSpriteGuideLabel('중심',(headGuidePoint.y+floorGuidePoint.y)/2,SPRITE_GUIDE_COLOR_VALUES.center);drawSpriteGuideLabel('바닥',floorGuidePoint.y,SPRITE_GUIDE_COLOR_VALUES.floor);
  for(const [currentGuideIndex,currentGuideRecord] of (spriteProjectDocument.guides||[]).entries()){
   const currentGuidePosition=currentGuideRecord.position*outputCellPixels;
   currentCanvasContext.setLineDash([guideDisplayStyle.dashLength*guidePixelRatio,guideDisplayStyle.dashGap*guidePixelRatio]);
   if(currentGuideRecord.axis==='horizontal')strokeSpriteGuideLine(0,currentGuidePosition,outputCellPixels,currentGuidePosition,SPRITE_GUIDE_COLOR_VALUES.head);
   else strokeSpriteGuideLine(currentGuidePosition,0,currentGuidePosition,outputCellPixels,SPRITE_GUIDE_COLOR_VALUES.center);
   currentCanvasContext.setLineDash([]);
  }
  currentCanvasContext.restore();
 }
 function renderSpriteSheetCanvas(currentCanvasElement,sourceFrameRecords,currentProjectSnapshot){
  const outputCellPixels=currentProjectSnapshot.output.cellSize,currentSheetLayout=createSpriteSheetLayout(sourceFrameRecords,outputCellPixels);
  currentCanvasElement.width=currentSheetLayout.width;currentCanvasElement.height=currentSheetLayout.height;
  const currentCanvasContext=currentCanvasElement.getContext('2d');
  for(const currentSheetCell of currentSheetLayout.frames){currentCanvasContext.save();currentCanvasContext.beginPath();currentCanvasContext.rect(currentSheetCell.x,currentSheetCell.y,outputCellPixels,outputCellPixels);currentCanvasContext.clip();currentCanvasContext.translate(currentSheetCell.x,currentSheetCell.y);drawSpriteFrameImage(currentCanvasContext,currentSheetCell.frame,currentProjectSnapshot.frames[currentSheetCell.frame.frameId],outputCellPixels);currentCanvasContext.restore();}
  return currentSheetLayout;
 }
 function refreshSpriteSheetOverview(){if(!spriteSourceRecord||!findSpriteElement('sheet-details').open)return;try{const currentSheetLayout=renderSpriteSheetCanvas(findSpriteElement('sheet'),spriteSourceRecord.frames,spriteProjectDocument);findSpriteElement('sheet-info').textContent=`${currentSheetLayout.columns}열 × ${currentSheetLayout.rows}행 · ${currentSheetLayout.width}×${currentSheetLayout.height}px · 가이드 없는 편집본`;}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}}
 function renderSpriteEditorFrame(){
  updateSpriteDisplayZoom();
  const currentFrameRecord=readSpriteCurrentFrame();if(!currentFrameRecord)return;
  spriteDirtyState=JSON.stringify(spriteProjectDocument)!==spriteSavedSnapshot;
  const currentFrameSettings=readSpriteCurrentSettings(),outputCellPixels=readSpriteCellPixels(),directionFrameRecords=readSpriteDirectionFrames();
  const editedCanvasContext=prepareSpriteCanvasContext(spriteCanvasElement,outputCellPixels);
  if(findSpriteElement('onion').checked&&directionFrameRecords.length>1){const previousFrameRecord=directionFrameRecords[(spriteFramePosition+directionFrameRecords.length-1)%directionFrameRecords.length];editedCanvasContext.globalAlpha=.22;drawSpriteFrameImage(editedCanvasContext,previousFrameRecord,spriteProjectDocument.frames[previousFrameRecord.frameId],outputCellPixels);editedCanvasContext.globalAlpha=1;}
  drawSpriteFrameImage(editedCanvasContext,currentFrameRecord,currentFrameSettings,outputCellPixels);
  if(findSpriteElement('guides').checked)drawSpriteGuideLines(editedCanvasContext,currentFrameSettings,outputCellPixels);
  for(const currentFieldName of Object.keys(SPRITE_FRAME_FIELDS))findSpriteElement('field-'+currentFieldName).value=currentFrameSettings[currentFieldName];
  findSpriteElement('timeline').max=directionFrameRecords.length-1;findSpriteElement('timeline').value=spriteFramePosition;
  findSpriteElement('position').textContent=`${spriteFramePosition+1} / ${directionFrameRecords.length} · ${spriteSourceRecord.fps} FPS · ${spritePlaybackHandle===null?'정지':'재생 중'}`;
  findSpriteElement('output-info').textContent=`출력 ${outputCellPixels}×${outputCellPixels}px · 기준점 (${calculateSpriteOutputAnchor(outputCellPixels).x}, ${calculateSpriteOutputAnchor(outputCellPixels).y})`;
  findSpriteElement('nudge-position').textContent=`X ${currentFrameSettings.x}px · Y ${currentFrameSettings.y}px`;
  const currentBodyHeight=(currentFrameSettings.floor-currentFrameSettings.head)*currentFrameSettings.scale;
  findSpriteElement('scale-position').textContent=`몸체 높이 ${currentBodyHeight.toFixed(2)}px · 배율 ${currentFrameSettings.scale.toFixed(5)}`;
  const currentDrawRect=calculateSpriteDrawRectangle(currentFrameRecord,currentFrameSettings,outputCellPixels);
  const currentHeadPosition=currentDrawRect.y+currentFrameSettings.head*currentFrameSettings.scale,currentFloorPosition=currentDrawRect.y+currentFrameSettings.floor*currentFrameSettings.scale;
  findSpriteElement('measurement').textContent=`${currentFrameRecord.frameId} · 몸체 높이 ${currentBodyHeight.toFixed(1)}px · 머리 ${currentHeadPosition.toFixed(1)} / 바닥 ${currentFloorPosition.toFixed(1)}px${currentHeadPosition<0||currentFloorPosition>=outputCellPixels?' · 주의: 몸체가 출력 셀 밖으로 벗어납니다.':''}${spriteDirtyState?' · 저장 전 변경 있음':''}`;
  for(const [currentFrameIndex,currentButtonElement] of [...findSpriteElement('strip').children].entries())currentButtonElement.setAttribute('aria-pressed',String(currentFrameIndex===spriteFramePosition));
  for(const currentDirectionCanvas of findSpriteElement('directions').querySelectorAll('canvas')){
   const syncFrameRecords=spriteSourceRecord.frames.filter(currentSourceFrame=>currentSourceFrame.direction===currentDirectionCanvas.dataset.direction),syncFrameRecord=syncFrameRecords[spriteFramePosition%syncFrameRecords.length];
   const syncCanvasContext=prepareSpriteCanvasContext(currentDirectionCanvas,outputCellPixels);drawSpriteFrameImage(syncCanvasContext,syncFrameRecord,spriteProjectDocument.frames[syncFrameRecord.frameId],outputCellPixels);
  }
  updateSpriteControlStates();
 }
 function rebuildSpriteFrameStrip(){
  findSpriteElement('strip').replaceChildren(...readSpriteDirectionFrames().map((currentFrameRecord,currentFrameIndex)=>{
   const currentButtonElement=document.createElement('button'),currentPreviewCanvas=document.createElement('canvas');currentButtonElement.setAttribute('aria-label','프레임 '+(currentFrameIndex+1));
   const previewCanvasContext=prepareSpriteCanvasContext(currentPreviewCanvas,readSpriteCellPixels());drawSpriteFrameImage(previewCanvasContext,currentFrameRecord,spriteProjectDocument.frames[currentFrameRecord.frameId],readSpriteCellPixels());currentButtonElement.append(currentPreviewCanvas,document.createTextNode(String(currentFrameIndex+1)));
   currentButtonElement.onclick=()=>{stopSpritePlayback();spriteFramePosition=currentFrameIndex;renderSpriteEditorFrame();};return currentButtonElement;
  }));
 }
 function refreshSpriteEditedViews(){renderSpriteCustomGuides();rebuildSpriteFrameStrip();renderSpriteEditorFrame();refreshSpriteSheetOverview();}
 function restoreSpriteOutputControls(){
  const sourceCellPixels=spriteSourceRecord.frames[0].rect.width,previousCellPixels=spriteProjectDocument.output.cellSize;
  if(sourceCellPixels===previousCellPixels)return;
  const cellSizeRatio=sourceCellPixels/previousCellPixels,previousAnchorPoint=calculateSpriteOutputAnchor(previousCellPixels),nextAnchorPoint=calculateSpriteOutputAnchor(sourceCellPixels);
  for(const currentFrameSettings of Object.values(spriteProjectDocument.frames)){currentFrameSettings.x=(previousAnchorPoint.x+currentFrameSettings.x)*cellSizeRatio-nextAnchorPoint.x;currentFrameSettings.y=(previousAnchorPoint.y+currentFrameSettings.y)*cellSizeRatio-nextAnchorPoint.y;currentFrameSettings.scale*=cellSizeRatio;validateSpriteFrameSettings(currentFrameSettings);}
  spriteProjectDocument.output={cellSize:sourceCellPixels,targetHeight:spriteProjectDocument.output.targetHeight*cellSizeRatio};
 }
 async function openSpriteSourceDocument(sourceIdentifierValue){
  if(!sourceIdentifierValue){appendSpriteStatusMessage('에셋을 선택하거나 완료된 결과 ID를 입력하세요.');return;}
  if(spriteDirtyState&&!confirm('저장하지 않은 편집이 있습니다. 다른 원본을 불러올까요?'))return;
  stopSpritePlayback();spriteBusyState=true;updateSpriteControlStates();const currentLoadingVersion=++spriteLoadingVersion;appendSpriteStatusMessage('원본 이미지와 저장된 편집을 불러오는 중…');
  try{
   const sourceAssetRecord=await requestSpriteManagementCommand('sprite-source',{id:sourceIdentifierValue}),savedProjectRecord=await requestSpriteManagementCommand('sprite-load',{id:sourceIdentifierValue});
   if(!sourceAssetRecord.frames?.length||!Number.isFinite(sourceAssetRecord.fps)||sourceAssetRecord.fps<=0)throw Error('원본의 프레임 목록 또는 FPS가 올바르지 않습니다.');
   spriteImageCache.clear();spriteBodyBounds.clear();
   for(const currentImageUrl of new Set(sourceAssetRecord.frames.map(currentFrameRecord=>currentFrameRecord.url)))await loadSpriteSourceImage(currentImageUrl);
   for(const currentFrameRecord of sourceAssetRecord.frames)spriteBodyBounds.set(currentFrameRecord.frameId,measureSpriteBodyBounds(currentFrameRecord));
   if(currentLoadingVersion!==spriteLoadingVersion)return;
   const sourceCellDimension=Math.max(sourceAssetRecord.frames[0].rect.width,sourceAssetRecord.frames[0].rect.height),outputCellPixels=sourceCellDimension;
   if(sourceAssetRecord.frames.some(currentFrameRecord=>currentFrameRecord.rect.width!==outputCellPixels||currentFrameRecord.rect.height!==outputCellPixels))throw Error('동일 크기의 정사각형 원본 셀만 지원합니다.');
   const sourceReferenceHeight=sourceAssetRecord.source?.runtimeScale?.sourceHeight||spriteBodyBounds.get(sourceAssetRecord.frames[0].frameId).bottom-spriteBodyBounds.get(sourceAssetRecord.frames[0].frameId).top;
   const loadedProjectDocument=savedProjectRecord.document||{version:2,source:sourceIdentifierValue,output:{cellSize:outputCellPixels,targetHeight:Math.min(outputCellPixels,sourceReferenceHeight*outputCellPixels/sourceCellDimension)},frames:Object.fromEntries(sourceAssetRecord.frames.map(currentFrameRecord=>[currentFrameRecord.frameId,createSpriteDefaultSettings(currentFrameRecord,outputCellPixels,spriteBodyBounds.get(currentFrameRecord.frameId),sourceIdentifierValue.startsWith('asset:'))]))};
   if(loadedProjectDocument.version===1){loadedProjectDocument.version=2;loadedProjectDocument.output={cellSize:512,targetHeight:80};for(const currentFrameSettings of Object.values(loadedProjectDocument.frames))currentFrameSettings.y-=calculateSpriteOutputAnchor(512).y-448;}
   for(const currentFrameRecord of sourceAssetRecord.frames){if(!loadedProjectDocument.frames[currentFrameRecord.frameId])throw Error('원본과 저장된 편집 프레임이 다릅니다.');validateSpriteFrameSettings(loadedProjectDocument.frames[currentFrameRecord.frameId]);}
   spriteSourceRecord=sourceAssetRecord;spriteProjectDocument=loadedProjectDocument;spriteSavedSnapshot=JSON.stringify(loadedProjectDocument);spriteFramePosition=0;spriteUndoRecords.length=0;spriteDirtyState=false;restoreSpriteOutputControls();spriteSavedSnapshot=JSON.stringify(spriteProjectDocument);
   const sourceDirectionNames=Object.keys(SPRITE_DIRECTION_LABELS).filter(directionKeyName=>sourceAssetRecord.frames.some(currentFrameRecord=>currentFrameRecord.direction===directionKeyName));
   findSpriteElement('direction').replaceChildren(...sourceDirectionNames.map(directionKeyName=>new Option(SPRITE_DIRECTION_LABELS[directionKeyName],directionKeyName)));
   findSpriteElement('directions').replaceChildren(...sourceDirectionNames.map(directionKeyName=>{const directionFigureElement=document.createElement('figure'),directionCanvasElement=document.createElement('canvas'),directionCaptionElement=document.createElement('figcaption');directionCaptionElement.textContent=SPRITE_DIRECTION_LABELS[directionKeyName];directionCanvasElement.className='sprite-preview';directionCanvasElement.dataset.direction=directionKeyName;directionCanvasElement.setAttribute('aria-label',SPRITE_DIRECTION_LABELS[directionKeyName]+' 동기 재생');directionFigureElement.append(directionCaptionElement,directionCanvasElement);return directionFigureElement;}));
   findSpriteElement('summary').textContent=`${sourceAssetRecord.label} · 원본 셀 ${sourceAssetRecord.frames[0].rect.width}×${sourceAssetRecord.frames[0].rect.height} · ${sourceAssetRecord.frames.length}프레임 / ${sourceDirectionNames.length}방향 · ${sourceAssetRecord.fps} FPS · 검수 사본`;
   spriteHistoryViewState.page=0;spriteHistoryViewState.selected=null;findSpriteElement('history-input').textContent='';await refreshSpriteSavedHistory();
   refreshSpriteEditedViews();appendSpriteStatusMessage((savedProjectRecord.warning?savedProjectRecord.warning+' · ':'')+(savedProjectRecord.revision?'저장본 복원: '+savedProjectRecord.revision:'원본 로딩 완료 · 등록 에셋은 런타임 기준점 정렬을 적용합니다. 가이드는 필요 시 직접 조정하세요.'));
  }catch(currentErrorValue){spriteSourceRecord=null;spriteProjectDocument=null;appendSpriteStatusMessage(currentErrorValue.message);}
  finally{spriteBusyState=false;updateSpriteControlStates();}
 }
 function selectedSpriteScopeFrames(){const currentScopeName=findSpriteElement('scope').value;return currentScopeName==='clip'?spriteSourceRecord.frames:currentScopeName==='direction'?readSpriteDirectionFrames():[readSpriteCurrentFrame()];}
 function applySpriteAlignmentChange(normalizeBodyHeight){
  if(!spriteProjectDocument)return;
  try{const changedFrameRecords=selectedSpriteScopeFrames(),changedSettingsLookup={};for(const currentFrameRecord of changedFrameRecords){const nextFrameSettings=structuredClone(spriteProjectDocument.frames[currentFrameRecord.frameId]);nextFrameSettings.anchorX=nextFrameSettings.center;nextFrameSettings.anchorY=nextFrameSettings.floor;nextFrameSettings.x=0;nextFrameSettings.y=0;if(normalizeBodyHeight)nextFrameSettings.scale=spriteProjectDocument.output.targetHeight/(nextFrameSettings.floor-nextFrameSettings.head);validateSpriteFrameSettings(nextFrameSettings);changedSettingsLookup[currentFrameRecord.frameId]=nextFrameSettings;}rememberSpriteDocumentChange();Object.assign(spriteProjectDocument.frames,changedSettingsLookup);refreshSpriteEditedViews();appendSpriteStatusMessage(`${changedFrameRecords.length}프레임 ${normalizeBodyHeight?'높이 맞춤':'중심·바닥 정렬'} · 저장 전 변경`);}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}
 }
 for(const [currentFieldName,currentFieldLabel] of Object.entries(SPRITE_FRAME_FIELDS)){
  const currentFieldInput=document.createElement('input'),currentFieldWrapper=document.createElement('label');currentFieldInput.type='number';currentFieldInput.step=currentFieldName==='scale'?'.01':'.5';currentFieldInput.id='sprite-field-'+currentFieldName;currentFieldWrapper.textContent=currentFieldLabel;currentFieldWrapper.append(currentFieldInput);const currentFieldGroup=['center','floor','head'].includes(currentFieldName)?'guide-fields':['anchorX','anchorY'].includes(currentFieldName)?'anchor-fields':'placement-fields';findSpriteElement(currentFieldGroup).append(currentFieldWrapper);
  currentFieldInput.onchange=()=>{if(!spriteProjectDocument)return;try{if(!currentFieldInput.value.trim())throw Error('숫자를 입력하세요.');const nextFrameSettings={...readSpriteCurrentSettings(),[currentFieldName]:Number(currentFieldInput.value)};validateSpriteFrameSettings(nextFrameSettings);rememberSpriteDocumentChange();spriteProjectDocument.frames[readSpriteCurrentFrame().frameId]=nextFrameSettings;refreshSpriteEditedViews();}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);renderSpriteEditorFrame();}};
 }
 const spriteHistoryViewState={page:0,selected:null};
 async function resetSpriteSavedHistory(selectedHistoryRecord){
  const currentSourceIdentifier=spriteProjectDocument?.source;if(!currentSourceIdentifier)return;
  const currentTargetLabel=selectedHistoryRecord?selectedHistoryRecord.id:currentSourceIdentifier+'의 전체 저장 이력';
  if(!confirm(currentTargetLabel+'\n이력 목록에서만 제외합니다. 원본 이미지와 저장 JSON 파일, 현재 편집은 유지됩니다. 초기화할까요?'))return;
  try{await requestSpriteManagementCommand(selectedHistoryRecord?'sprite-history-delete':'sprite-history-reset',{id:currentSourceIdentifier,...(selectedHistoryRecord?{revision:selectedHistoryRecord.id}:{})});if(spriteProjectDocument?.source!==currentSourceIdentifier)return;spriteHistoryViewState.selected=null;findSpriteElement('history-input').textContent='';findSpriteElement('history-details').open=false;await refreshSpriteSavedHistory();appendSpriteStatusMessage('이력 초기화 완료 · 저장 파일은 보존됩니다.');}catch(currentErrorValue){appendSpriteStatusMessage('이력 초기화 실패: '+currentErrorValue.message);}
 }
 async function refreshSpriteSavedHistory(){
  const currentSourceIdentifier=spriteProjectDocument?.source;
  if(!currentSourceIdentifier)return;
  try{
   const currentHistoryResponse=await requestSpriteManagementCommand('sprite-history',{id:currentSourceIdentifier});
   if(spriteProjectDocument?.source!==currentSourceIdentifier)return;
   renderSavedRecordHistory(findSpriteElement('history'),currentHistoryResponse.items,spriteHistoryViewState,{
    refresh:refreshSpriteSavedHistory,
    remove:resetSpriteSavedHistory,
    reset:()=>resetSpriteSavedHistory(null),
    inspect:currentHistoryRecord=>{findSpriteElement('history-input').textContent=JSON.stringify(currentHistoryRecord.document,null,2);findSpriteElement('history-details').open=true;},
    restore:currentHistoryRecord=>{
     if(!currentHistoryRecord.compatible){appendSpriteStatusMessage('원본 버전이 다른 이력입니다. 입력값 조회만 가능합니다.');return;}
     if(spriteDirtyState&&!confirm('저장 전 변경을 선택한 이력으로 교체할까요? 실행 취소로 되돌릴 수 있습니다.'))return;
     stopSpritePlayback();rememberSpriteDocumentChange();spriteProjectDocument=structuredClone(currentHistoryRecord.document);
     if(spriteProjectDocument.version===1){spriteProjectDocument.version=2;spriteProjectDocument.output={cellSize:512,targetHeight:80};for(const currentFrameSettings of Object.values(spriteProjectDocument.frames))currentFrameSettings.y-=calculateSpriteOutputAnchor(512).y-448;}
     restoreSpriteOutputControls();refreshSpriteEditedViews();appendSpriteStatusMessage('이력 불러오기: '+currentHistoryRecord.id+' · 프로젝트 저장으로 새 이력을 남길 수 있습니다.');
    }
   });
   if(!currentHistoryResponse.items.length)findSpriteElement('history').append(document.createTextNode('저장된 이력이 없습니다. 프로젝트 저장으로 첫 이력을 남기세요.'));
  }catch(currentErrorValue){appendSpriteStatusMessage('저장 이력 조회 실패: '+currentErrorValue.message);}
 }
 function renderSpriteCustomGuides(){
  const currentGuideList=findSpriteElement('guide-list');currentGuideList.replaceChildren();
  for(const currentGuideAxis of ['horizontal','vertical'])findSpriteElement('guide-'+currentGuideAxis).disabled=!spriteProjectDocument||(spriteProjectDocument.guides||[]).length>=SPRITE_CUSTOM_GUIDE_LIMIT;
  if(!spriteProjectDocument){currentGuideList.textContent='원본을 불러오면 가이드를 추가할 수 있습니다.';return;}
  currentGuideList.textContent=(spriteProjectDocument.guides||[]).length?'최대 32개 · 변경 후 프로젝트 저장으로 보존합니다.':'추가 가이드가 없습니다. 가로 또는 세로 가이드 추가를 누르세요.';
  for(const [currentGuideIndex,currentGuideRecord] of (spriteProjectDocument.guides||[]).entries()){
   const currentGuideRow=document.createElement('div'),currentGuideLabel=document.createElement('label'),currentGuideInput=document.createElement('input'),currentDeleteButton=document.createElement('button');
   currentGuideRow.className='sprite-toolbar';currentGuideLabel.textContent=`${currentGuideIndex+1}. ${currentGuideRecord.axis==='horizontal'?'가로 Y':'세로 X'} (px)`;
   currentGuideInput.type='number';currentGuideInput.min=0;currentGuideInput.max=readSpriteCellPixels();currentGuideInput.step='any';currentGuideInput.value=Number((currentGuideRecord.position*readSpriteCellPixels()).toFixed(2));
   currentGuideInput.onchange=()=>{const nextGuidePosition=Number(currentGuideInput.value);if(!currentGuideInput.value.trim()||!Number.isFinite(nextGuidePosition)||nextGuidePosition<0||nextGuidePosition>readSpriteCellPixels()){appendSpriteStatusMessage('가이드 위치는 0부터 출력 셀 크기 사이의 숫자여야 합니다.');renderSpriteCustomGuides();return;}rememberSpriteDocumentChange();currentGuideRecord.position=nextGuidePosition/readSpriteCellPixels();refreshSpriteEditedViews();};
   currentDeleteButton.textContent='삭제';currentDeleteButton.setAttribute('aria-label',`${currentGuideIndex+1}번 가이드 삭제`);currentDeleteButton.onclick=()=>{rememberSpriteDocumentChange();spriteProjectDocument.guides.splice(currentGuideIndex,1);refreshSpriteEditedViews();};
   currentGuideLabel.append(currentGuideInput);currentGuideRow.append(currentGuideLabel,currentDeleteButton);currentGuideList.append(currentGuideRow);
  }
 }
 for(const currentGuideAxis of ['horizontal','vertical'])findSpriteElement('guide-'+currentGuideAxis).onclick=()=>{if(!spriteProjectDocument||(spriteProjectDocument.guides||[]).length>=SPRITE_CUSTOM_GUIDE_LIMIT)return;rememberSpriteDocumentChange();(spriteProjectDocument.guides??=[]).push({axis:currentGuideAxis,position:.5});findSpriteElement('guides').checked=true;refreshSpriteEditedViews();};
 renderSpriteCustomGuides();
 for(const [currentScaleAction,currentHeightDelta] of [['grow',1],['shrink',-1]])findSpriteElement('scale-'+currentScaleAction).onclick=()=>{
  if(!spriteProjectDocument||spriteBusyState)return;
  try{const nextFrameSettings=calculateSpriteScaleNudge(readSpriteCurrentSettings(),currentHeightDelta);rememberSpriteDocumentChange();spriteProjectDocument.frames[readSpriteCurrentFrame().frameId]=nextFrameSettings;refreshSpriteEditedViews();}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}
 };
 for(const [currentDirectionName,currentDirectionStep] of Object.entries(SPRITE_NUDGE_DIRECTION_STEPS))findSpriteElement('nudge-'+currentDirectionName).onclick=()=>{
  if(!spriteProjectDocument||spriteBusyState)return;
  const currentFrameSettings=readSpriteCurrentSettings(),nextFrameSettings={...currentFrameSettings,x:currentFrameSettings.x+currentDirectionStep.x,y:currentFrameSettings.y+currentDirectionStep.y};
  try{validateSpriteFrameSettings(nextFrameSettings);rememberSpriteDocumentChange();Object.assign(currentFrameSettings,nextFrameSettings);refreshSpriteEditedViews();findSpriteElement('nudge-position').textContent=`배치 X ${nextFrameSettings.x}px · Y ${nextFrameSettings.y}px`;}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}
 };
 findSpriteElement('asset-load').onclick=()=>openSpriteSourceDocument(findSpriteElement('asset').value);
 findSpriteElement('load').onclick=()=>openSpriteSourceDocument(findSpriteElement('job').value.trim());
 findSpriteElement('direction').onchange=()=>{stopSpritePlayback();spriteFramePosition=0;refreshSpriteEditedViews();};
 for(const currentToggleName of ['guides','onion'])findSpriteElement(currentToggleName).onchange=renderSpriteEditorFrame;
 function updateSpriteDisplayZoom(){
  const selectedDisplayZoom=findSpriteElement('zoom').value;
  spriteRootElement.style.setProperty('--sprite-display-size',selectedDisplayZoom==='fit'?'100%':`${readSpriteCellPixels()*Number(selectedDisplayZoom)}px`);
 }
 findSpriteElement('zoom').onchange=()=>{updateSpriteDisplayZoom();renderSpriteEditorFrame();};
 findSpriteElement('background').onchange=()=>{spriteRootElement.dataset.background=findSpriteElement('background').value;};
 for(const [currentButtonName,currentFrameDelta] of [['prev',-1],['next',1]])findSpriteElement(currentButtonName).onclick=()=>{if(!spriteProjectDocument)return;stopSpritePlayback();spriteFramePosition=(spriteFramePosition+currentFrameDelta+readSpriteDirectionFrames().length)%readSpriteDirectionFrames().length;renderSpriteEditorFrame();};
 findSpriteElement('timeline').oninput=()=>{stopSpritePlayback();spriteFramePosition=Number(findSpriteElement('timeline').value);renderSpriteEditorFrame();};
 findSpriteElement('stop').onclick=()=>{stopSpritePlayback();renderSpriteEditorFrame();};
 findSpriteElement('speed').onchange=()=>{stopSpritePlayback();renderSpriteEditorFrame();};
 findSpriteElement('play').onclick=()=>{if(!spriteProjectDocument)return;stopSpritePlayback();const initialFramePosition=spriteFramePosition,playbackStartTime=performance.now(),playbackFrameDuration=1000/spriteSourceRecord.fps/Number(findSpriteElement('speed').value);function advanceSpritePlaybackFrame(currentTimestampValue){const nextFramePosition=(initialFramePosition+Math.floor((currentTimestampValue-playbackStartTime)/playbackFrameDuration))%readSpriteDirectionFrames().length;if(nextFramePosition!==spriteFramePosition){spriteFramePosition=nextFramePosition;renderSpriteEditorFrame();}spritePlaybackHandle=requestAnimationFrame(advanceSpritePlaybackFrame);}spritePlaybackHandle=requestAnimationFrame(advanceSpritePlaybackFrame);renderSpriteEditorFrame();};
 findSpriteElement('align').onclick=()=>applySpriteAlignmentChange(false);findSpriteElement('normalize').onclick=()=>applySpriteAlignmentChange(true);
 findSpriteElement('apply').onclick=()=>{if(!spriteProjectDocument)return;const copiedFrameSettings=structuredClone(readSpriteCurrentSettings());rememberSpriteDocumentChange();const changedFrameRecords=selectedSpriteScopeFrames();for(const currentFrameRecord of changedFrameRecords)spriteProjectDocument.frames[currentFrameRecord.frameId]=structuredClone(copiedFrameSettings);refreshSpriteEditedViews();appendSpriteStatusMessage(`${changedFrameRecords.length}프레임에 설정 복사 · 저장 전 변경`);};
 findSpriteElement('undo').onclick=()=>{if(!spriteUndoRecords.length)return;stopSpritePlayback();spriteProjectDocument=spriteUndoRecords.pop();spriteDirtyState=true;restoreSpriteOutputControls();refreshSpriteEditedViews();};
 findSpriteElement('reset').onclick=()=>{if(!spriteProjectDocument)return;rememberSpriteDocumentChange();const currentFrameRecord=readSpriteCurrentFrame();spriteProjectDocument.frames[currentFrameRecord.frameId]=createSpriteDefaultSettings(currentFrameRecord,readSpriteCellPixels(),spriteBodyBounds.get(currentFrameRecord.frameId),spriteProjectDocument.source.startsWith('asset:'));refreshSpriteEditedViews();};
 findSpriteElement('save').onclick=async()=>{if(!spriteProjectDocument)return;const currentProjectSnapshot=structuredClone(spriteProjectDocument);try{const savedProjectRecord=await requestSpriteManagementCommand('sprite-save',{id:currentProjectSnapshot.source,document:currentProjectSnapshot});if(currentProjectSnapshot.source===spriteProjectDocument?.source)spriteSavedSnapshot=JSON.stringify(currentProjectSnapshot);appendSpriteStatusMessage(`정렬 시트 저장 완료 · ${savedProjectRecord.sheet.width}×${savedProjectRecord.sheet.height}px · ${savedProjectRecord.revision}`);renderSpriteEditorFrame();await refreshSpriteSavedHistory();}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}};
 findSpriteElement('sheet-details').ontoggle=refreshSpriteSheetOverview;
 spriteCanvasElement.onpointerdown=currentPointerEvent=>{if(!spriteProjectDocument||spriteBusyState)return;const currentFrameSettings=readSpriteCurrentSettings(),currentPointerPosition=calculateSpritePointerPosition({x:currentPointerEvent.clientX,y:currentPointerEvent.clientY},spriteCanvasElement.getBoundingClientRect(),readSpriteCellPixels()),currentOutputAnchor=calculateSpriteOutputAnchor(readSpriteCellPixels()),currentModeValue=findSpriteElement('mode').value;
  rememberSpriteDocumentChange();if(currentModeValue==='move'){spriteDragOrigin={point:currentPointerPosition,x:currentFrameSettings.x,y:currentFrameSettings.y};spriteCanvasElement.setPointerCapture(currentPointerEvent.pointerId);}else{const sourcePointX=(currentPointerPosition.x-currentOutputAnchor.x-currentFrameSettings.x)/currentFrameSettings.scale+currentFrameSettings.anchorX,sourcePointY=(currentPointerPosition.y-currentOutputAnchor.y-currentFrameSettings.y)/currentFrameSettings.scale+currentFrameSettings.anchorY;const nextFrameSettings={...currentFrameSettings};if(currentModeValue==='anchor'){nextFrameSettings.anchorX=Math.round(sourcePointX);nextFrameSettings.anchorY=Math.round(sourcePointY);}else nextFrameSettings[currentModeValue]=Math.round(currentModeValue==='center'?sourcePointX:sourcePointY);try{validateSpriteFrameSettings(nextFrameSettings);Object.assign(currentFrameSettings,nextFrameSettings);}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}refreshSpriteEditedViews();}};
 spriteCanvasElement.onpointermove=currentPointerEvent=>{if(!spriteDragOrigin)return;const currentPointerPosition=calculateSpritePointerPosition({x:currentPointerEvent.clientX,y:currentPointerEvent.clientY},spriteCanvasElement.getBoundingClientRect(),readSpriteCellPixels()),currentFrameSettings=readSpriteCurrentSettings();currentFrameSettings.x=Math.max(-8192,Math.min(8192,Math.round(spriteDragOrigin.x+currentPointerPosition.x-spriteDragOrigin.point.x)));currentFrameSettings.y=Math.max(-8192,Math.min(8192,Math.round(spriteDragOrigin.y+currentPointerPosition.y-spriteDragOrigin.point.y)));renderSpriteEditorFrame();};
 spriteCanvasElement.onpointerup=spriteCanvasElement.onpointercancel=()=>{spriteDragOrigin=null;refreshSpriteEditedViews();};
 window.addEventListener('beforeunload',currentUnloadEvent=>{if(spriteDirtyState){currentUnloadEvent.preventDefault();currentUnloadEvent.returnValue='';}});
 for(const currentEventName of ['review-pane-hidden','visibilitychange'])document.addEventListener(currentEventName,()=>{if(currentEventName==='review-pane-hidden'||document.hidden)stopSpritePlayback();});
 updateSpriteControlStates();
 try{const catalogResponseValue=await fetch(resolveSpriteUrl('/sprite-assets.json'),{cache:'no-store'});if(!catalogResponseValue.ok)throw Error('프론트 에셋 검수 사본을 다시 빌드해야 합니다.');const sourceCatalogRecord=await catalogResponseValue.json();findSpriteElement('asset').append(...sourceCatalogRecord.assets.map(currentAssetRecord=>new Option(currentAssetRecord.label,currentAssetRecord.id)));const defaultAssetIdentifier='asset:character.default.white-shirt.idle';if(sourceCatalogRecord.assets.some(currentAssetRecord=>currentAssetRecord.id===defaultAssetIdentifier)){findSpriteElement('asset').value=defaultAssetIdentifier;await openSpriteSourceDocument(defaultAssetIdentifier);}else appendSpriteStatusMessage('검수할 에셋을 선택하세요.');}catch(currentErrorValue){appendSpriteStatusMessage(currentErrorValue.message);}
})();
