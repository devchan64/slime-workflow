const initialReviewMetadata=__SOURCE_METADATA__;
const availableActionReviews=initialReviewMetadata.actionReviews||[];
const requestedActionIdentifier=new URLSearchParams(window.location?.search).get('action')||initialReviewMetadata.defaultActionId;
const selectedActionReview=availableActionReviews.find(currentActionRecord=>currentActionRecord.id===requestedActionIdentifier);
const reviewFrameRecords=selectedActionReview?structuredClone(selectedActionReview.frames):__FRAME_RECORDS__;
const reviewSourceMetadata=selectedActionReview?.source||initialReviewMetadata;
const resolveReviewAssetUrl=assetPathValue=>selectedActionReview?selectedActionReview.frames.find(currentFrameRecord=>currentFrameRecord.image===assetPathValue)?.url||assetPathValue:window.resolveStaticReviewAssetUrl?.(assetPathValue)||assetPathValue;
const actionChoiceElement=document.querySelector('#actionChoice');
document.querySelector('#actionChoiceField').hidden=!availableActionReviews.length;
for(const currentActionRecord of availableActionReviews)actionChoiceElement.add(new Option(`${currentActionRecord.source.displayNameKo} · ${currentActionRecord.source.animationVersion}`,currentActionRecord.id));
if(selectedActionReview)actionChoiceElement.value=selectedActionReview.id;
const actionDraftStorageKey='animation-anchor-draft:'+reviewSourceMetadata.animationId+':'+reviewSourceMetadata.animationVersion;
function selectReviewAnimationAction(){
 pauseFramePlayback();
 sessionStorage.setItem(actionDraftStorageKey,JSON.stringify({frames:reviewFrameRecords.map(copyFrameCoordinates),saved:savedCoordinateSnapshotValue,source:reviewSourceMetadata.sheets}));
 document.body.dataset.coordinateDownloadPending='false';
 const selectedActionLocation=new URL(window.location.href);
 selectedActionLocation.searchParams.set('action',actionChoiceElement.value);
 window.location.replace(selectedActionLocation.href);
}
actionChoiceElement.onchange=selectReviewAnimationAction;
const usesAnchorOnlyMode=reviewSourceMetadata.coordinateMode==='anchor';
const usesFootCentersOnly=usesAnchorOnlyMode||reviewSourceMetadata.coordinateMode==='foot-centers';
const reviewAnimationIdentity=reviewSourceMetadata.animationId||'character.default.white-shirt.idle';
const reviewAnimationVersion=reviewSourceMetadata.animationVersion||'4';
const reviewCanvasElement=document.querySelector('#reviewCanvas'),reviewCanvasContext=reviewCanvasElement.getContext('2d'),rigMiniMapElement=document.querySelector('#rigMiniMap'),rigMiniMapContext=rigMiniMapElement?.getContext('2d');
const directionChoiceElement=document.querySelector('#directionChoice'),frameChoiceElement=document.querySelector('#frameChoice'),pointChoiceElement=document.querySelector('#pointChoice');
const anchorToggleElement=document.querySelector('#anchorToggle'),guideToggleElement=document.querySelector('#guideToggle'),rigMiniMapToggleElement=document.querySelector('#rigMiniMapToggle');
rigMiniMapToggleElement.onchange=()=>{document.querySelector('.rig-mini-map').hidden=!rigMiniMapToggleElement.checked};
const REVIEW_CANVAS_WIDTH=650,REVIEW_CANVAS_HEIGHT=reviewSourceMetadata.runtimeScale?.actorKind==='monster'?750:400,REVIEW_FRAME_DURATION=reviewSourceMetadata.frameDurationMs||400,REVIEW_FRAME_COUNT=reviewFrameRecords.filter(currentFrameValue=>currentFrameValue.direction==='down_left').length,REVIEW_ANCHOR_POSITION={x:325,y:reviewSourceMetadata.runtimeScale?.actorKind==='monster'?600:350};
reviewCanvasElement.width=REVIEW_CANVAS_WIDTH;reviewCanvasElement.height=REVIEW_CANVAS_HEIGHT;
const PREVIEW_TILE_DEFAULT_WIDTH=240,PREVIEW_TILE_DEFAULT_HEIGHT=120,PREVIEW_TILE_MINIMUM_WIDTH=32,PREVIEW_TILE_MAXIMUM_WIDTH=600,PREVIEW_TILE_MINIMUM_HEIGHT=16,PREVIEW_TILE_MAXIMUM_HEIGHT=300,PREVIEW_TILE_ASPECT_RATIO=2,PREVIEW_GROUND_BOTTOM_MARGIN=10;
const gameRenderMetrics=reviewSourceMetadata.gameRenderMetrics;
if(!gameRenderMetrics)throw new Error('게임 크기 기준이 없습니다. 관리도구 검수본을 다시 빌드하세요.');
let GAME_OUTPUT_TILE_WIDTH=gameRenderMetrics.tileWidth,GAME_OUTPUT_TILE_HEIGHT=gameRenderMetrics.tileHeight;
const GAME_OUTPUT_CHARACTER_HEIGHT=gameRenderMetrics.characterHeight;
const GAME_SIZE_PRESETS={small:{label:'소형',scale:0.5,tiles:1,recommendedGuideHeight:GAME_OUTPUT_CHARACTER_HEIGHT*0.5},medium:{label:'중형',scale:1,tiles:1,recommendedGuideHeight:GAME_OUTPUT_CHARACTER_HEIGHT},large:{label:'대형',scale:1.5,tiles:2,recommendedGuideHeight:GAME_OUTPUT_CHARACTER_HEIGHT*1.5},huge:{label:'초대형',scale:2,tiles:2,recommendedGuideHeight:GAME_OUTPUT_CHARACTER_HEIGHT*2}};
// 권장 가이드는 입력 가능한 출력 신체 높이와 분리된 게임 기준값이다.
// 중형(100%)에서 게임의 사람 기준 높이가 되며, 크기 등급을 선택했을 때만 등급 배율을 적용한다.
const PREVIEW_TILE_FILL_COLOR='#426b6a55',PREVIEW_TILE_LINE_COLOR='#8abdb3',PREVIEW_SHADOW_FILL_COLOR='#07111c88',PREVIEW_SHADOW_SCALE_RATIO=0.5;
let previewTileWidthValue=PREVIEW_TILE_DEFAULT_WIDTH,previewTileHeightValue=PREVIEW_TILE_DEFAULT_HEIGHT;
const previewTileWidthElement=document.querySelector('#tilePreviewWidth'),previewTileHeightElement=document.querySelector('#tilePreviewHeight'),gameOutputScaleToggleElement=document.querySelector('#gameOutputScaleToggle'),actorSizeChoiceElement=document.querySelector('#actorSizeChoice'),bodyHeightInputElement=document.querySelector('#bodyHeightInput');
actorSizeChoiceElement.value=reviewSourceMetadata.runtimeScale?.defaultSizeClass||'medium';
document.querySelector('.preview-display-settings').open=false;
bodyHeightInputElement.value=String(reviewSourceMetadata.runtimeScale?.baseHeight||GAME_OUTPUT_CHARACTER_HEIGHT);
previewTileWidthElement.value=String(PREVIEW_TILE_DEFAULT_WIDTH);previewTileHeightElement.value=String(PREVIEW_TILE_DEFAULT_HEIGHT);
previewTileWidthElement.min=String(PREVIEW_TILE_MINIMUM_WIDTH);previewTileWidthElement.max=String(PREVIEW_TILE_MAXIMUM_WIDTH);previewTileHeightElement.min=String(PREVIEW_TILE_MINIMUM_HEIGHT);previewTileHeightElement.max=String(PREVIEW_TILE_MAXIMUM_HEIGHT);
function updatePreviewGroundSize(){
 const requestedTileWidth=Number(previewTileWidthElement.value),requestedTileHeight=requestedTileWidth/PREVIEW_TILE_ASPECT_RATIO;
 if(!Number.isInteger(requestedTileWidth)||!Number.isInteger(requestedTileHeight)||requestedTileWidth<PREVIEW_TILE_MINIMUM_WIDTH||requestedTileWidth>PREVIEW_TILE_MAXIMUM_WIDTH||requestedTileHeight<PREVIEW_TILE_MINIMUM_HEIGHT||requestedTileHeight>PREVIEW_TILE_MAXIMUM_HEIGHT){document.querySelector('#groundPreviewError').textContent=`너비는 ${PREVIEW_TILE_MINIMUM_WIDTH}–${PREVIEW_TILE_MAXIMUM_WIDTH}px 범위의 짝수를 입력하세요. 높이는 2:1 비율로 자동 계산하며 마지막 유효한 크기를 표시합니다.`;return false;}
 previewTileWidthValue=requestedTileWidth;previewTileHeightValue=requestedTileHeight;previewTileHeightElement.value=String(requestedTileHeight);document.querySelector('#groundPreviewError').textContent='';
 const reviewScaleRatio=previewTileWidthValue/GAME_OUTPUT_TILE_WIDTH,currentSizePreset=GAME_SIZE_PRESETS[actorSizeChoiceElement.value],outputBodyHeightValue=Number(bodyHeightInputElement.value);
 if(!Number.isInteger(outputBodyHeightValue)||outputBodyHeightValue<1||outputBodyHeightValue>240){document.querySelector('#groundPreviewError').textContent='출력 신체 높이는 1–240px 정수여야 합니다.';return false;}
 document.querySelector('#groundPreviewStatus').textContent=`게임 타일 ${GAME_OUTPUT_TILE_WIDTH} × ${GAME_OUTPUT_TILE_HEIGHT}px · ${currentSizePreset.label} ${currentSizePreset.scale*100}% · ${currentSizePreset.tiles}×${currentSizePreset.tiles} 배치 · 출력 ${outputBodyHeightValue*currentSizePreset.scale}px · 고정 권장 ${currentSizePreset.recommendedGuideHeight}px · 검수 ${reviewScaleRatio.toFixed(2)}× · 표시 설정`;return true;
}
document.querySelector('#mapScaleChoice').onchange=()=>{const currentTownSelected=document.querySelector('#mapScaleChoice').value==='town';GAME_OUTPUT_TILE_WIDTH=currentTownSelected?gameRenderMetrics.townTileWidth:gameRenderMetrics.tileWidth;GAME_OUTPUT_TILE_HEIGHT=currentTownSelected?gameRenderMetrics.townTileHeight:gameRenderMetrics.tileHeight;updatePreviewGroundSize();};
previewTileWidthElement.oninput=updatePreviewGroundSize;gameOutputScaleToggleElement.onchange=updatePreviewGroundSize;actorSizeChoiceElement.onchange=updatePreviewGroundSize;bodyHeightInputElement.oninput=updatePreviewGroundSize;updatePreviewGroundSize();
function calculatePreviewGroundHeight(){return Math.min(REVIEW_ANCHOR_POSITION.y,REVIEW_CANVAS_HEIGHT-previewTileHeightValue/2-PREVIEW_GROUND_BOTTOM_MARGIN);}
function drawPreviewGroundPlane(){
 const groundCenterPositionX=REVIEW_ANCHOR_POSITION.x,groundCenterPositionY=calculatePreviewGroundHeight(),currentSizePreset=GAME_SIZE_PRESETS[actorSizeChoiceElement.value];
 reviewCanvasContext.save();
 if(document.querySelector('#tilePreviewToggle').checked){
  reviewCanvasContext.fillStyle=PREVIEW_TILE_FILL_COLOR;reviewCanvasContext.strokeStyle=PREVIEW_TILE_LINE_COLOR;
  for(let tileRowIndex=0;tileRowIndex<currentSizePreset.tiles;tileRowIndex++)for(let tileColumnIndex=0;tileColumnIndex<currentSizePreset.tiles;tileColumnIndex++){const tileCenterPositionX=groundCenterPositionX+(tileColumnIndex-tileRowIndex)*previewTileWidthValue/2,tileCenterPositionY=groundCenterPositionY+(tileColumnIndex+tileRowIndex-currentSizePreset.tiles+1)*previewTileHeightValue/2;reviewCanvasContext.beginPath();reviewCanvasContext.moveTo(tileCenterPositionX,tileCenterPositionY-previewTileHeightValue/2);reviewCanvasContext.lineTo(tileCenterPositionX+previewTileWidthValue/2,tileCenterPositionY);reviewCanvasContext.lineTo(tileCenterPositionX,tileCenterPositionY+previewTileHeightValue/2);reviewCanvasContext.lineTo(tileCenterPositionX-previewTileWidthValue/2,tileCenterPositionY);reviewCanvasContext.closePath();reviewCanvasContext.fill();reviewCanvasContext.stroke();}
 }
 if(document.querySelector('#shadowPreviewToggle').checked){const shadowScaleRatio=reviewSourceMetadata.runtimeScale?.actorKind==='monster'?0.54:PREVIEW_SHADOW_SCALE_RATIO;reviewCanvasContext.fillStyle=PREVIEW_SHADOW_FILL_COLOR;reviewCanvasContext.beginPath();reviewCanvasContext.ellipse(groundCenterPositionX,groundCenterPositionY,previewTileWidthValue*currentSizePreset.tiles*shadowScaleRatio/2,previewTileHeightValue*currentSizePreset.tiles*shadowScaleRatio/2,0,0,Math.PI*2);reviewCanvasContext.fill();}
 reviewCanvasContext.restore();
}
const reviewImageElements={},reviewRigImageElements={};let animationPlaybackActive=false,animationStartedTime=0,currentSpriteOffsetX=0,currentSpriteOffsetY=0,currentSpriteScale=1;
const initialCoordinateRecords=reviewFrameRecords.map(copyFrameCoordinates);
const coordinateUndoHistory=[],coordinateRedoHistory=[];
let savedCoordinateSnapshotValue=JSON.stringify(initialCoordinateRecords);
function copyFrameCoordinates(currentFrameRecord){return {anchor:{...currentFrameRecord.anchor},contacts:currentFrameRecord.contacts.map(currentPointRecord=>({...currentPointRecord})),endpoints:currentFrameRecord.endpoints.map(currentPointRecord=>({...currentPointRecord}))};}
function refreshCoordinateStatus(){
 const currentCoordinateRecords=reviewFrameRecords.map(copyFrameCoordinates);
 const modifiedFrameCount=currentCoordinateRecords.filter((currentCoordinateRecord,currentFrameIndex)=>JSON.stringify(currentCoordinateRecord)!==JSON.stringify(initialCoordinateRecords[currentFrameIndex])).length;
 const coordinateDownloadPending=JSON.stringify(currentCoordinateRecords)!==savedCoordinateSnapshotValue;
 document.body.dataset.coordinateDownloadPending=String(coordinateDownloadPending);
 document.querySelector('#coordinateEditStatus').textContent=`원본 대비 ${modifiedFrameCount}개 프레임 변경 · ${coordinateDownloadPending?'저장 필요':'추가 저장 불필요'}`;
 document.querySelector('#undoCoordinateChange').disabled=coordinateUndoHistory.length===0;
 document.querySelector('#redoCoordinateChange').disabled=coordinateRedoHistory.length===0;
 document.dispatchEvent(new CustomEvent('review-coordinate-state',{detail:{pending:coordinateDownloadPending}}));
}
function recordCoordinateChange(currentFrameRecord,previousCoordinateRecord){
 const nextCoordinateRecord=copyFrameCoordinates(currentFrameRecord);
 if(JSON.stringify(previousCoordinateRecord)===JSON.stringify(nextCoordinateRecord))return;
 coordinateUndoHistory.push({frameIndex:reviewFrameRecords.indexOf(currentFrameRecord),before:previousCoordinateRecord,after:nextCoordinateRecord});
 coordinateRedoHistory.length=0;
 refreshCoordinateStatus();
}
function restoreFrameCoordinates(currentFrameRecord,nextCoordinateRecord){Object.assign(currentFrameRecord,copyFrameCoordinates(nextCoordinateRecord));}
function replayCoordinateChange(undoRequestedValue){
 const sourceHistoryRecords=undoRequestedValue?coordinateUndoHistory:coordinateRedoHistory;
 const targetHistoryRecords=undoRequestedValue?coordinateRedoHistory:coordinateUndoHistory;
 const selectedHistoryRecord=sourceHistoryRecords.pop();
 if(!selectedHistoryRecord)return;
 pauseFramePlayback();
 const currentFrameRecord=reviewFrameRecords[selectedHistoryRecord.frameIndex];
 restoreFrameCoordinates(currentFrameRecord,undoRequestedValue?selectedHistoryRecord.before:selectedHistoryRecord.after);
 directionChoiceElement.value=currentFrameRecord.direction;
 frameChoiceElement.value=currentFrameRecord.frameId.split('.').at(-1);
 targetHistoryRecords.push(selectedHistoryRecord);
 document.querySelector('#reviewError').textContent='';
 refreshCoordinateStatus();
}
document.querySelector('#undoCoordinateChange').onclick=()=>replayCoordinateChange(true);
document.querySelector('#redoCoordinateChange').onclick=()=>replayCoordinateChange(false);
let coordinateInputIdentity='';
document.querySelector('#applyCoordinateInputs').onclick=()=>{
 const requestedPointValue={x:Number(document.querySelector('#coordinateInputX').value),y:Number(document.querySelector('#coordinateInputY').value)};
 const currentFrameRecord=selectCurrentFrame();
 if(['X','Y'].some(axisNameValue=>document.querySelector('#coordinateInput'+axisNameValue).value.trim()==='')||!Number.isFinite(requestedPointValue.x)||!Number.isFinite(requestedPointValue.y)||requestedPointValue.x<0||requestedPointValue.y<0||requestedPointValue.x>=currentFrameRecord.rect.width||requestedPointValue.y>=currentFrameRecord.rect.height){document.querySelector('#reviewError').textContent='셀 범위 안의 유한한 X·Y 좌표를 입력하세요.';return;}
 const selectedPointRecord=pointChoiceElement.value==='anchor'?currentFrameRecord.anchor:(usesFootCentersOnly?currentFrameRecord.contacts:currentFrameRecord.endpoints)[Number(pointChoiceElement.value)];
 moveSelectedPoint(requestedPointValue.x-selectedPointRecord.x,requestedPointValue.y-selectedPointRecord.y);
 coordinateInputIdentity='';
};
function copyPreviousFrameAnchor(){
 pauseFramePlayback();
 const currentFrameRecord=selectCurrentFrame();
 const previousFrameRecord=reviewFrameRecords.find(frameRecordValue=>frameRecordValue.frameId===`${directionChoiceElement.value}.${Number(frameChoiceElement.value)-1}`);
 if(!previousFrameRecord)return;
 const previousCoordinateRecord=copyFrameCoordinates(currentFrameRecord);
 const anchorDeltaValue={x:previousFrameRecord.anchor.x-currentFrameRecord.anchor.x,y:previousFrameRecord.anchor.y-currentFrameRecord.anchor.y};
 const translatedCoordinateRecord=copyFrameCoordinates(currentFrameRecord);
 for(const pointRecordValue of [translatedCoordinateRecord.anchor,...translatedCoordinateRecord.contacts,...translatedCoordinateRecord.endpoints]){pointRecordValue.x+=anchorDeltaValue.x;pointRecordValue.y+=anchorDeltaValue.y;}
 if([translatedCoordinateRecord.anchor,...(usesFootCentersOnly?translatedCoordinateRecord.contacts:translatedCoordinateRecord.endpoints)].some(pointRecordValue=>pointRecordValue.x<0||pointRecordValue.y<0||pointRecordValue.x>=currentFrameRecord.rect.width||pointRecordValue.y>=currentFrameRecord.rect.height)){document.querySelector('#reviewError').textContent='좌표가 셀을 벗어나 이전 앵커를 적용하지 않았습니다.';return;}
 restoreFrameCoordinates(currentFrameRecord,translatedCoordinateRecord);
 document.querySelector('#reviewError').textContent='';
 recordCoordinateChange(currentFrameRecord,previousCoordinateRecord);
}
document.querySelector('#copyPreviousAnchor').onclick=copyPreviousFrameAnchor;
function restoreOriginalFrameCoordinates(){
 pauseFramePlayback();
 const currentFrameRecord=selectCurrentFrame(),previousCoordinateRecord=copyFrameCoordinates(currentFrameRecord);
 restoreFrameCoordinates(currentFrameRecord,initialCoordinateRecords[reviewFrameRecords.indexOf(currentFrameRecord)]);
 document.querySelector('#reviewError').textContent='';
 recordCoordinateChange(currentFrameRecord,previousCoordinateRecord);
}
document.querySelector('#resetCurrentFrame').onclick=restoreOriginalFrameCoordinates;
document.addEventListener('keydown',currentKeyboardEvent=>{
 if(!(currentKeyboardEvent.ctrlKey||currentKeyboardEvent.metaKey)||currentKeyboardEvent.altKey||currentKeyboardEvent.target.closest('input,select,textarea,[contenteditable]'))return;
 if(currentKeyboardEvent.key.toLowerCase()==='z'){currentKeyboardEvent.preventDefault();replayCoordinateChange(!currentKeyboardEvent.shiftKey);}
});
document.addEventListener('review-pane-hidden',pauseFramePlayback);
window.addEventListener('beforeunload',currentUnloadEvent=>{if(document.body.dataset.coordinateDownloadPending==='true'){currentUnloadEvent.preventDefault();currentUnloadEvent.returnValue='';}});
const storedActionDraft=sessionStorage.getItem(actionDraftStorageKey);
if(storedActionDraft){
 const restoredActionDraft=JSON.parse(storedActionDraft);
 if(JSON.stringify(restoredActionDraft.source)===JSON.stringify(reviewSourceMetadata.sheets)&&restoredActionDraft.frames.length===reviewFrameRecords.length){
 restoredActionDraft.frames.forEach((currentCoordinateRecord,currentFrameIndex)=>restoreFrameCoordinates(reviewFrameRecords[currentFrameIndex],currentCoordinateRecord));
 savedCoordinateSnapshotValue=restoredActionDraft.saved;
 }
}
for(const currentDirectionOption of [...directionChoiceElement.options])if(!reviewFrameRecords.some(currentFrameRecord=>currentFrameRecord.direction===currentDirectionOption.value))currentDirectionOption.remove();
refreshCoordinateStatus();
frameChoiceElement.max=String(REVIEW_FRAME_COUNT-1);
if(usesAnchorOnlyMode){document.querySelector('#coordinateHelp').textContent='초기 좌표는 수동 편집 시작점입니다. 떠 있는 발의 중간점 대신 지면 기준점을 지정하세요.';document.querySelector('h1').textContent='걷기 앵커 편집';document.querySelector('h1+p').textContent='초기 앵커는 셀 하단 중앙의 편집 시작점입니다. 자동 검출 좌표가 아닙니다. 떠 있는 발의 중간점 대신 지면 기준점을 프레임별로 지정하세요. 정수 원본 픽셀 단위로 저장합니다.';}
if(reviewSourceMetadata.registeredSource){document.querySelector('h1').textContent=reviewSourceMetadata.displayNameKo+' · 앵커 편집';document.querySelector('h1+p').textContent=reviewSourceMetadata.description;document.querySelector('#coordinateHelp').textContent='등록된 원본 앵커를 불러왔습니다. 소수 좌표는 유지하며 클릭 지정은 정수 픽셀을 사용합니다.';}
const pointLabelNames=usesAnchorOnlyMode?[]:usesFootCentersOnly?['왼쪽 발 중심','오른쪽 발 중심']:['왼쪽 앞꿈치','왼쪽 뒤꿈치','오른쪽 앞꿈치','오른쪽 뒤꿈치'];
pointChoiceElement.innerHTML='<option value="anchor">최종 앵커</option>'+pointLabelNames.map((pointLabelText,pointSequenceIndex)=>`<option value="${pointSequenceIndex}">${pointLabelText}</option>`).join('');
function selectCurrentFrame(){return reviewFrameRecords.find(currentFrameValue=>currentFrameValue.frameId===`${directionChoiceElement.value}.${frameChoiceElement.value}`)}
function calculatePointMidpoint(firstPointValue,secondPointValue){return {x:Math.round((firstPointValue.x+secondPointValue.x)/2),y:Math.round((firstPointValue.y+secondPointValue.y)/2)}}
function updateFrameCoordinates(currentFrameValue){if(usesAnchorOnlyMode){currentFrameValue.anchor={...currentFrameValue.contacts[0]};return;}if(!usesFootCentersOnly)currentFrameValue.contacts=[calculatePointMidpoint(...currentFrameValue.endpoints.slice(0,2)),calculatePointMidpoint(...currentFrameValue.endpoints.slice(2,4))];currentFrameValue.anchor=calculatePointMidpoint(...currentFrameValue.contacts)}
function pauseFramePlayback(){animationPlaybackActive=false;document.querySelector('#playToggle').textContent='재생'}
function moveFrameSelection(frameStepAmount){pauseFramePlayback();frameChoiceElement.value=String((Number(frameChoiceElement.value)+frameStepAmount+REVIEW_FRAME_COUNT)%REVIEW_FRAME_COUNT)}
function moveSelectedPoint(pointDeltaX,pointDeltaY){
 pauseFramePlayback();if(pointDeltaX===0&&pointDeltaY===0)return;const currentFrameValue=selectCurrentFrame(),previousCoordinateRecord=copyFrameCoordinates(currentFrameValue),editablePointValues=usesFootCentersOnly?currentFrameValue.contacts:currentFrameValue.endpoints;
 const affectedPointValues=pointChoiceElement.value==='anchor'?editablePointValues:[editablePointValues[Number(pointChoiceElement.value)]];
 if(affectedPointValues.some(currentPointValue=>currentPointValue.x+pointDeltaX<0||currentPointValue.y+pointDeltaY<0||currentPointValue.x+pointDeltaX>=currentFrameValue.rect.width||currentPointValue.y+pointDeltaY>=currentFrameValue.rect.height)){document.querySelector('#reviewError').textContent='좌표가 셀을 벗어나 이동하지 않았습니다.';return}
 affectedPointValues.forEach(currentPointValue=>{currentPointValue.x+=pointDeltaX;currentPointValue.y+=pointDeltaY});if(pointChoiceElement.value==='anchor'){currentFrameValue.anchor.x+=pointDeltaX;currentFrameValue.anchor.y+=pointDeltaY;if(!usesFootCentersOnly)currentFrameValue.contacts.forEach(pointRecordValue=>{pointRecordValue.x+=pointDeltaX;pointRecordValue.y+=pointDeltaY});}else updateFrameCoordinates(currentFrameValue);document.querySelector('#reviewError').textContent='';recordCoordinateChange(currentFrameValue,previousCoordinateRecord);
}
function calculateCurrentSpriteScale(currentFrameBounds){if(!gameOutputScaleToggleElement.checked)return 1;const runtimeScaleMetadata=reviewSourceMetadata.runtimeScale||{},currentSizePreset=GAME_SIZE_PRESETS[actorSizeChoiceElement.value],sourceHeightValue=runtimeScaleMetadata.sourceHeight||currentFrameBounds.height*(runtimeScaleMetadata.sourceHeightMultiplier||1),targetHeightValue=Number(bodyHeightInputElement.value)*currentSizePreset.scale*previewTileWidthValue/GAME_OUTPUT_TILE_WIDTH;return targetHeightValue/sourceHeightValue;}
function drawRigMiniMap(currentFrameValue){
 const rigSheetRecord=reviewSourceMetadata.rigSheets?.find(currentRigSheetRecord=>currentRigSheetRecord.direction===currentFrameValue.direction),rigImageElement=rigSheetRecord&&reviewRigImageElements[rigSheetRecord.image];
 if(!rigMiniMapContext||!rigImageElement)return;
 const rigFrameIndex=Number(currentFrameValue.frameId.split('.')[1]),rigColumnCount=4,rigRowCount=2,sourceCellWidth=rigImageElement.naturalWidth/rigColumnCount,sourceCellHeight=rigImageElement.naturalHeight/rigRowCount,miniMapScale=Math.min(rigMiniMapElement.width/sourceCellWidth,rigMiniMapElement.height/sourceCellHeight),miniMapDrawWidth=sourceCellWidth*miniMapScale,miniMapDrawHeight=sourceCellHeight*miniMapScale;
 rigMiniMapContext.clearRect(0,0,rigMiniMapElement.width,rigMiniMapElement.height);rigMiniMapContext.drawImage(rigImageElement,(rigFrameIndex%rigColumnCount)*sourceCellWidth,Math.floor(rigFrameIndex/rigColumnCount)*sourceCellHeight,sourceCellWidth,sourceCellHeight,(rigMiniMapElement.width-miniMapDrawWidth)/2,(rigMiniMapElement.height-miniMapDrawHeight)/2,miniMapDrawWidth,miniMapDrawHeight);
}
function drawReviewFrame(currentAnimationTime){
 if(animationPlaybackActive)frameChoiceElement.value=String(Math.floor((currentAnimationTime-animationStartedTime)/REVIEW_FRAME_DURATION)%REVIEW_FRAME_COUNT);
 const currentFrameValue=selectCurrentFrame(),currentFrameBounds=currentFrameValue.rect;
 currentSpriteScale=calculateCurrentSpriteScale(currentFrameBounds);
 currentSpriteOffsetX=REVIEW_ANCHOR_POSITION.x-currentFrameValue.anchor.x*currentSpriteScale;
 currentSpriteOffsetY=calculatePreviewGroundHeight()-currentFrameValue.anchor.y*currentSpriteScale;
 reviewCanvasContext.clearRect(0,0,REVIEW_CANVAS_WIDTH,REVIEW_CANVAS_HEIGHT);
 drawPreviewGroundPlane();
 drawRigMiniMap(currentFrameValue);
 reviewCanvasContext.drawImage(reviewImageElements[currentFrameValue.image],currentFrameBounds.x,currentFrameBounds.y,currentFrameBounds.width,currentFrameBounds.height,currentSpriteOffsetX,currentSpriteOffsetY,currentFrameBounds.width*currentSpriteScale,currentFrameBounds.height*currentSpriteScale);
 if(guideToggleElement.checked){
  reviewCanvasContext.strokeStyle='#ffdf66';reviewCanvasContext.beginPath();reviewCanvasContext.moveTo(0,calculatePreviewGroundHeight());reviewCanvasContext.lineTo(REVIEW_CANVAS_WIDTH,calculatePreviewGroundHeight());reviewCanvasContext.moveTo(REVIEW_ANCHOR_POSITION.x,0);reviewCanvasContext.lineTo(REVIEW_ANCHOR_POSITION.x,REVIEW_CANVAS_HEIGHT);reviewCanvasContext.stroke();
  for(let endpointPairOffset=0;endpointPairOffset<currentFrameValue.endpoints.length;endpointPairOffset+=2){reviewCanvasContext.beginPath();reviewCanvasContext.moveTo(currentSpriteOffsetX+currentFrameValue.endpoints[endpointPairOffset].x*currentSpriteScale,currentSpriteOffsetY+currentFrameValue.endpoints[endpointPairOffset].y*currentSpriteScale);reviewCanvasContext.lineTo(currentSpriteOffsetX+currentFrameValue.endpoints[endpointPairOffset+1].x*currentSpriteScale,currentSpriteOffsetY+currentFrameValue.endpoints[endpointPairOffset+1].y*currentSpriteScale);reviewCanvasContext.stroke()}
  reviewCanvasContext.strokeStyle='#00ffff';reviewCanvasContext.beginPath();currentFrameValue.contacts.forEach((currentPointValue,currentPointIndex)=>{if(currentPointIndex===0)reviewCanvasContext.moveTo(currentSpriteOffsetX+currentPointValue.x*currentSpriteScale,currentSpriteOffsetY+currentPointValue.y*currentSpriteScale);else reviewCanvasContext.lineTo(currentSpriteOffsetX+currentPointValue.x*currentSpriteScale,currentSpriteOffsetY+currentPointValue.y*currentSpriteScale)});reviewCanvasContext.stroke();
  [...currentFrameValue.contacts,currentFrameValue.anchor].forEach((currentPointValue,currentPointIndex)=>{reviewCanvasContext.fillStyle=currentPointIndex===currentFrameValue.contacts.length?'#ff4444':'#00ffff';reviewCanvasContext.beginPath();reviewCanvasContext.arc(currentSpriteOffsetX+currentPointValue.x*currentSpriteScale,currentSpriteOffsetY+currentPointValue.y*currentSpriteScale,4,0,Math.PI*2);reviewCanvasContext.fill()});
 }
 const recommendedGuideHeight=GAME_SIZE_PRESETS[actorSizeChoiceElement.value].recommendedGuideHeight*previewTileWidthValue/GAME_OUTPUT_TILE_WIDTH,recommendedGuideTop=calculatePreviewGroundHeight()-recommendedGuideHeight;
 reviewCanvasContext.save();reviewCanvasContext.strokeStyle='#ff4df3';reviewCanvasContext.lineWidth=3;reviewCanvasContext.setLineDash([8,5]);reviewCanvasContext.beginPath();reviewCanvasContext.moveTo(REVIEW_ANCHOR_POSITION.x,calculatePreviewGroundHeight());reviewCanvasContext.lineTo(REVIEW_ANCHOR_POSITION.x,recommendedGuideTop);reviewCanvasContext.stroke();reviewCanvasContext.setLineDash([]);reviewCanvasContext.beginPath();reviewCanvasContext.moveTo(REVIEW_ANCHOR_POSITION.x-12,recommendedGuideTop);reviewCanvasContext.lineTo(REVIEW_ANCHOR_POSITION.x+12,recommendedGuideTop);reviewCanvasContext.stroke();reviewCanvasContext.fillStyle='#ffdcfb';reviewCanvasContext.fillRect(REVIEW_ANCHOR_POSITION.x+8,recommendedGuideTop-23,116,20);reviewCanvasContext.fillStyle='#5d0758';reviewCanvasContext.fillText(`고정 권장 ${GAME_SIZE_PRESETS[actorSizeChoiceElement.value].recommendedGuideHeight}px`,REVIEW_ANCHOR_POSITION.x+12,recommendedGuideTop-8);reviewCanvasContext.restore();
 const selectedPointValue=pointChoiceElement.value==='anchor'?currentFrameValue.anchor:(usesFootCentersOnly?currentFrameValue.contacts:currentFrameValue.endpoints)[Number(pointChoiceElement.value)];
 document.querySelector('#copyPreviousAnchor').disabled=Number(frameChoiceElement.value)===0;
 document.querySelector('#previousAnchorStatus').textContent=Number(frameChoiceElement.value)===0?'첫 프레임에는 이전 앵커가 없습니다.':'같은 방향의 이전 프레임 앵커에 맞춥니다.';
 const currentInputIdentity=`${currentFrameValue.frameId}:${pointChoiceElement.value}:${selectedPointValue.x}:${selectedPointValue.y}`;
 if(coordinateInputIdentity!==currentInputIdentity){document.querySelector('#coordinateInputX').value=String(selectedPointValue.x);document.querySelector('#coordinateInputY').value=String(selectedPointValue.y);coordinateInputIdentity=currentInputIdentity;}
 document.querySelector('#pointStatus').textContent=`X ${selectedPointValue.x} / Y ${selectedPointValue.y}`;
 document.querySelector('#frameNumber').textContent=`${Number(frameChoiceElement.value)+1} / ${REVIEW_FRAME_COUNT}`;
 document.querySelector('#frameStatus').textContent=`${currentFrameValue.frameId} | 앵커 (${currentFrameValue.anchor.x}, ${currentFrameValue.anchor.y}) | ${REVIEW_FRAME_DURATION}ms · ${REVIEW_FRAME_COUNT*REVIEW_FRAME_DURATION/1000}초 반복`;
 requestAnimationFrame(drawReviewFrame);
}
window.anchorReviewActions=currentActionIdentifier=>{
 const currentActionOptions=[...actionChoiceElement.options].map(currentOptionValue=>[currentOptionValue.textContent,currentOptionValue.value]);
 if(currentActionIdentifier!==null){
  if(!currentActionOptions.some(currentOptionValue=>currentOptionValue[1]===currentActionIdentifier))throw Error('등록되지 않은 애니메이션 동작입니다.');
  if(currentActionIdentifier!==actionChoiceElement.value){actionChoiceElement.value=currentActionIdentifier;selectReviewAnimationAction();}
 }
 return [{__type__:'update',choices:currentActionOptions,value:actionChoiceElement.value||null},currentActionOptions.length?'동작을 선택하고 불러오세요. 편집 중 좌표는 동작별로 임시 보존됩니다.':'현재 애니메이션은 단일 동작입니다.'];
};
window.anchorReviewCoordinateCommands=currentCommandName=>{
 if(currentCommandName==='undo'){
  if(!coordinateUndoHistory.length)throw Error('실행 취소할 변경이 없습니다. 좌표를 수정한 뒤 사용할 수 있습니다.');
  replayCoordinateChange(true);
 }else if(currentCommandName==='redo'){
  if(!coordinateRedoHistory.length)throw Error('다시 실행할 변경이 없습니다. 먼저 실행 취소하세요.');
  replayCoordinateChange(false);
 }else if(currentCommandName==='previous'){
  if(Number(frameChoiceElement.value)===0)throw Error('첫 프레임에는 이전 앵커가 없습니다. 두 번째 이후 프레임을 선택하세요.');
  copyPreviousFrameAnchor();
 }else if(currentCommandName==='reset')restoreOriginalFrameCoordinates();
 else if(currentCommandName!=='status')throw Error('지원하지 않는 좌표 명령입니다.');
 const currentErrorText=document.querySelector('#reviewError').textContent;
 return (currentErrorText?currentErrorText+' · ':'')+document.querySelector('#coordinateEditStatus').textContent;
};
window.anchorReviewOutputSettings=currentOutputValues=>{
 const currentMapInput=document.querySelector('#mapScaleChoice');
 if(currentOutputValues!==null){
  if(!Array.isArray(currentOutputValues))throw Error('출력 설정 입력은 목록이어야 합니다.');
  const [currentScaleEnabled,currentMapKind,currentSizeClass,currentBodyHeight,currentTileWidth]=currentOutputValues;
  if(currentOutputValues.length!==5||typeof currentScaleEnabled!=='boolean'||!['field','town'].includes(currentMapKind)||!Object.hasOwn(GAME_SIZE_PRESETS,currentSizeClass))throw Error('출력 비율·맵 기준·크기 등급이 올바르지 않습니다.');
  if(!Number.isInteger(currentBodyHeight)||currentBodyHeight<1||currentBodyHeight>240)throw Error('출력 신체 높이는 1–240px 정수여야 합니다.');
  if(!Number.isInteger(currentTileWidth)||currentTileWidth%2||currentTileWidth<PREVIEW_TILE_MINIMUM_WIDTH||currentTileWidth>PREVIEW_TILE_MAXIMUM_WIDTH)throw Error(`타일 너비는 ${PREVIEW_TILE_MINIMUM_WIDTH}–${PREVIEW_TILE_MAXIMUM_WIDTH}px 범위의 짝수여야 합니다.`);
  const currentMapDimensions=currentMapKind==='town'?[gameRenderMetrics.townTileWidth,gameRenderMetrics.townTileHeight]:[gameRenderMetrics.tileWidth,gameRenderMetrics.tileHeight];
  if(currentMapDimensions.some(currentDimensionValue=>!Number.isFinite(currentDimensionValue)||currentDimensionValue<=0))throw Error('선택한 맵의 게임 크기 기준이 없습니다.');
  gameOutputScaleToggleElement.checked=currentScaleEnabled;currentMapInput.value=currentMapKind;actorSizeChoiceElement.value=currentSizeClass;
  bodyHeightInputElement.value=String(currentBodyHeight);previewTileWidthElement.value=String(currentTileWidth);
  currentMapInput.onchange();
 }
 return [gameOutputScaleToggleElement.checked,currentMapInput.value,actorSizeChoiceElement.value,Number(bodyHeightInputElement.value),Number(previewTileWidthElement.value),document.querySelector('#groundPreviewStatus').textContent];
};
// 표시 선택은 좌표·이력과 분리하고 모든 입력을 검사한 뒤 함께 적용한다.
window.anchorReviewDisplay=(currentDisplayValues)=>{
 const currentDisplayElements=[guideToggleElement,rigMiniMapToggleElement,document.querySelector('#tilePreviewToggle'),document.querySelector('#shadowPreviewToggle')];
 if(currentDisplayValues!==null){
  if(!Array.isArray(currentDisplayValues)||currentDisplayValues.length!==4||currentDisplayValues.some(currentOptionValue=>typeof currentOptionValue!=='boolean'))throw Error('가이드·리그·타일·그림자 표시값은 참/거짓이어야 합니다.');
  currentDisplayElements.forEach((currentInputElement,currentInputIndex)=>{currentInputElement.checked=currentDisplayValues[currentInputIndex];});
  rigMiniMapToggleElement.onchange();
 }
 return [...currentDisplayElements.map(currentInputElement=>currentInputElement.checked),'표시 설정을 확인했습니다. 앵커 좌표와 저장 이력은 변경하지 않습니다.'];
};
// 좌표 조작은 기존 셀 범위 검사와 실행 취소 기록을 공유한다.
window.anchorReviewSelection=(currentDirectionName,currentPointName)=>{
 if(currentDirectionName!==null){
  if(![...directionChoiceElement.options].some(currentOptionValue=>currentOptionValue.value===currentDirectionName))throw Error('지원하지 않는 방향입니다.');
  if(![...pointChoiceElement.options].some(currentOptionValue=>currentOptionValue.value===currentPointName))throw Error('지원하지 않는 좌표입니다.');
  pauseFramePlayback();directionChoiceElement.value=currentDirectionName;pointChoiceElement.value=currentPointName;
 }
 return [
  {__type__:'update',choices:[...directionChoiceElement.options].map(currentOptionValue=>[currentOptionValue.textContent,currentOptionValue.value]),value:directionChoiceElement.value},
  {__type__:'update',choices:[...pointChoiceElement.options].map(currentOptionValue=>[currentOptionValue.textContent,currentOptionValue.value]),value:pointChoiceElement.value},
  `${directionChoiceElement.value} · ${Number(frameChoiceElement.value)+1}/${REVIEW_FRAME_COUNT} · 좌표 선택 완료`
 ];
};
window.anchorReviewCoordinates=(currentActionName,currentInputValues)=>{
 const currentFrameRecord=selectCurrentFrame();
 const currentPointRecord=pointChoiceElement.value==='anchor'?currentFrameRecord.anchor:(usesFootCentersOnly?currentFrameRecord.contacts:currentFrameRecord.endpoints)[Number(pointChoiceElement.value)];
 const currentMovementSteps={up:[0,-1],down:[0,1],left:[-1,0],right:[1,0]};
 let currentDeltaValues;
 if(currentActionName==='set-x'||currentActionName==='set-y'){
  const currentAxisName=currentActionName==='set-x'?'x':'y';
  if(typeof currentInputValues[currentAxisName]!=='number'||!Number.isFinite(currentInputValues[currentAxisName]))throw Error('유한한 좌표를 입력하세요.');
  currentDeltaValues=currentAxisName==='x'?[currentInputValues.x-currentPointRecord.x,0]:[0,currentInputValues.y-currentPointRecord.y];
 }else if(currentActionName in currentMovementSteps)currentDeltaValues=currentMovementSteps[currentActionName];
 else if(currentActionName!=='read')throw Error('지원하지 않는 좌표 조작입니다.');
 if(currentDeltaValues){
  moveSelectedPoint(...currentDeltaValues);
  const currentErrorText=document.querySelector('#reviewError').textContent;
  if(currentErrorText)throw Error(currentErrorText);
 }
 const currentSelectedPoint=pointChoiceElement.value==='anchor'?currentFrameRecord.anchor:(usesFootCentersOnly?currentFrameRecord.contacts:currentFrameRecord.endpoints)[Number(pointChoiceElement.value)];
 return {x:currentSelectedPoint.x,y:currentSelectedPoint.y,scale:1,message:`${currentFrameRecord.frameId} · X ${currentSelectedPoint.x} / Y ${currentSelectedPoint.y}`};
};
// 공용 Gradio 탐색기와 독립 검수 화면이 같은 브라우저 재생 상태를 사용한다.
window.anchorReviewPlayback=currentActionName=>{
 if(currentActionName==='prev')moveFrameSelection(-1);
 else if(currentActionName==='next')moveFrameSelection(1);
 else if(currentActionName==='stop')pauseFramePlayback();
 else if(currentActionName==='play'){
  animationPlaybackActive=true;
  animationStartedTime=performance.now()-Number(frameChoiceElement.value)*REVIEW_FRAME_DURATION;
  document.querySelector('#playToggle').textContent='일시정지';
 }else throw Error('지원하지 않는 프레임 탐색 명령입니다.');
 return `${Number(frameChoiceElement.value)+1} / ${REVIEW_FRAME_COUNT} · ${animationPlaybackActive?'재생 중':'정지'}`;
};
window.anchorReviewSeekFrame=currentFrameNumber=>{
 if(!Number.isInteger(currentFrameNumber)||currentFrameNumber<1||currentFrameNumber>REVIEW_FRAME_COUNT)throw Error(`프레임 번호는 1~${REVIEW_FRAME_COUNT} 정수로 입력하세요.`);
 pauseFramePlayback();frameChoiceElement.value=String(currentFrameNumber-1);
 return `${currentFrameNumber} / ${REVIEW_FRAME_COUNT} · 정지`;
};
if(window.parent!==window&&new URLSearchParams(window.location?.search).get('embedded')==='gradio-static'){
 for(const currentStyleElement of document.querySelectorAll('style'))currentStyleElement.disabled=true;
 const currentCanvasStyles=document.querySelector('#anchor-canvas-layout');currentCanvasStyles.disabled=false;currentCanvasStyles.media='all';
 const currentLegacyControls=[document.querySelector('.anchor-preview h2'),document.querySelector('.coordinate-legend'),document.querySelector('#frameStatus'),document.querySelector('body>header'),document.querySelector('.anchor-controls'),document.querySelector('.editor-save-panel'),document.querySelector('.anchor-history-panel'),document.querySelector('#actionChoiceField'),document.querySelector('#undoCoordinateChange').parentElement,document.querySelector('#copyPreviousAnchor'),document.querySelector('#resetCurrentFrame'),document.querySelector('#previousAnchorStatus'),document.querySelector('.preview-display-settings'),document.querySelector('.options'),document.querySelector('#tilePreviewToggle').parentElement,document.querySelector('#shadowPreviewToggle').parentElement,document.querySelector('.anchor-coordinate-inputs'),document.querySelector('.anchor-joypad'),directionChoiceElement.parentElement,pointChoiceElement.parentElement];
 for(const currentControlElement of currentLegacyControls){const currentHiddenWrapper=document.createElement('div');currentHiddenWrapper.hidden=true;currentControlElement.before(currentHiddenWrapper);currentHiddenWrapper.append(currentControlElement);}
 for(const currentLabelSelector of ['label[for="directionChoice"]','label[for="pointChoice"]'])document.querySelector(currentLabelSelector).hidden=true;
 const currentPlaybackRow=document.querySelector('#previousFrame').parentElement;
 const currentHiddenControls=document.createElement('div');currentHiddenControls.hidden=true;
 currentPlaybackRow.before(currentHiddenControls);currentHiddenControls.append(currentPlaybackRow);
 frameChoiceElement.hidden=true;
 document.querySelector('label[for="frameChoice"]').hidden=true;
}
document.querySelector('#previousFrame').onclick=()=>moveFrameSelection(-1);
document.querySelector('#nextFrame').onclick=()=>moveFrameSelection(1);
frameChoiceElement.oninput=pauseFramePlayback;
directionChoiceElement.onchange=pauseFramePlayback;
document.querySelector('#playToggle').onclick=()=>{animationPlaybackActive=!animationPlaybackActive;animationStartedTime=performance.now()-Number(frameChoiceElement.value)*REVIEW_FRAME_DURATION;document.querySelector('#playToggle').textContent=animationPlaybackActive?'일시정지':'재생'};
document.querySelectorAll('[data-move-x]').forEach(currentButtonElement=>currentButtonElement.onclick=()=>moveSelectedPoint(Number(currentButtonElement.dataset.moveX),Number(currentButtonElement.dataset.moveY)));
reviewCanvasElement.onclick=(pointerClickEvent)=>{if(animationPlaybackActive)return;const currentFrameValue=selectCurrentFrame(),canvasClientBounds=reviewCanvasElement.getBoundingClientRect();const clickedPointPosition={x:Math.round(((pointerClickEvent.clientX-canvasClientBounds.left)*REVIEW_CANVAS_WIDTH/canvasClientBounds.width-currentSpriteOffsetX)/currentSpriteScale),y:Math.round(((pointerClickEvent.clientY-canvasClientBounds.top)*REVIEW_CANVAS_HEIGHT/canvasClientBounds.height-currentSpriteOffsetY)/currentSpriteScale)};const selectedPointValue=pointChoiceElement.value==='anchor'?currentFrameValue.anchor:(usesFootCentersOnly?currentFrameValue.contacts:currentFrameValue.endpoints)[Number(pointChoiceElement.value)];moveSelectedPoint(clickedPointPosition.x-selectedPointValue.x,clickedPointPosition.y-selectedPointValue.y)};
function buildCoordinateArtifact(){return {schemaVersion:1,artifactType:reviewSourceMetadata.artifactType||'character-standing-anchor-review',description:reviewSourceMetadata.description||'스탠딩 정수 앵커 검수 좌표. 셀 왼쪽 위 원점, x 오른쪽·y 아래. points는 화면 왼쪽 발부터 두 발 중심 또는 각 발 앞뒤 네 점이며 anchor는 발 중심 평균을 반올림한다.',coordinateMode:reviewSourceMetadata.coordinateMode,source:{animationId:reviewAnimationIdentity,animationVersion:reviewAnimationVersion,sheets:reviewSourceMetadata.sheets},frames:reviewFrameRecords.map(currentFrameValue=>({frameId:currentFrameValue.frameId,direction:currentFrameValue.direction,image:currentFrameValue.image,rect:currentFrameValue.rect,points:usesAnchorOnlyMode?[currentFrameValue.anchor]:usesFootCentersOnly?currentFrameValue.contacts:currentFrameValue.endpoints,anchor:currentFrameValue.anchor}))}}
function buildNormalizationArtifact(){return {schemaVersion:1,artifactType:'animation-scale-normalization-review',source:{animationId:reviewAnimationIdentity,animationVersion:reviewAnimationVersion,sheets:reviewSourceMetadata.sheets},gameRenderMetrics,mapKind:document.querySelector('#mapScaleChoice').value,normalization:{unit:'px',tileWidth:GAME_OUTPUT_TILE_WIDTH,tileHeight:GAME_OUTPUT_TILE_HEIGHT,gameBodyHeight:Number(bodyHeightInputElement.value),sizeClass:actorSizeChoiceElement.value,sourceHeight:reviewSourceMetadata.runtimeScale?.sourceHeight||null,sourceHeightMultiplier:reviewSourceMetadata.runtimeScale?.sourceHeightMultiplier||null}}}
function downloadNormalizationArtifact(){if(!updatePreviewGroundSize())return;const downloadAnchorElement=document.createElement('a');downloadAnchorElement.href=URL.createObjectURL(new Blob([JSON.stringify(buildNormalizationArtifact(),null,2)+'\n'],{type:'application/json'}));downloadAnchorElement.download=reviewAnimationIdentity+'-normalization-review.json';downloadAnchorElement.click();document.querySelector('#normalizationDownloadStatus').textContent='정규화 검수 JSON 다운로드 요청됨 · 적용 전 검토하세요.';setTimeout(()=>URL.revokeObjectURL(downloadAnchorElement.href),1000)}
document.querySelector('#saveNormalization').onclick=downloadNormalizationArtifact;
window.anchorReviewDownloadSettings=()=>{downloadNormalizationArtifact();return document.querySelector('#normalizationDownloadStatus').textContent;};
Promise.all([...new Set(reviewFrameRecords.map(currentFrameValue=>currentFrameValue.image))].map(currentImageFilename=>new Promise((resolveImageLoad,rejectImageLoad)=>{const currentImageElement=new Image();currentImageElement.onload=()=>{reviewImageElements[currentImageFilename]=currentImageElement;resolveImageLoad()};currentImageElement.onerror=()=>rejectImageLoad(new Error(`이미지 로드 실패: ${currentImageFilename}`));currentImageElement.src=resolveReviewAssetUrl(currentImageFilename)}))).then(()=>Promise.all((reviewSourceMetadata.rigSheets||[]).map(currentRigSheetRecord=>new Promise((resolveRigLoad,rejectRigLoad)=>{const currentRigImageElement=new Image();currentRigImageElement.onload=()=>{reviewRigImageElements[currentRigSheetRecord.image]=currentRigImageElement;resolveRigLoad()};currentRigImageElement.onerror=()=>rejectRigLoad(new Error(`리그 이미지 로드 실패: ${currentRigSheetRecord.image}`));currentRigImageElement.src=resolveReviewAssetUrl(currentRigSheetRecord.image)}))).then(()=>requestAnimationFrame(drawReviewFrame))).catch(currentLoadError=>document.querySelector('#reviewError').textContent=currentLoadError.message);

// 브라우저 저장과 CLI는 같은 명령 게이트웨이·실행별 기록을 사용한다.
async function requestAnchorHistoryCommand(commandNameValue,payloadRecordValue){
 const responseRecordValue=await fetch('/management/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:'character-animation',command:commandNameValue,payload:payloadRecordValue})});
 const responsePayloadValue=await responseRecordValue.json();
 if(!responseRecordValue.ok)throw new Error(responsePayloadValue.error||'좌표 이력 요청 실패');
 return responsePayloadValue;
}
const currentEmbeddedReviewMode=window.parent!==window&&new URLSearchParams(window.location?.search).get('embedded')==='gradio-static';
window.anchorReviewHistory=async(currentActionName,currentSelectedId)=>{
 if(!['list','inspect','result','restore','reset'].includes(currentActionName))throw Error('지원하지 않는 좌표 이력 명령입니다.');
 let currentFeedbackText='이력을 선택한 뒤 조회하거나 불러오세요.';
 if(currentActionName==='reset'){
  if(!window.confirm('현재 애니메이션 버전의 좌표 이력 목록을 초기화할까요? 원본 파일과 편집값은 유지합니다.'))currentFeedbackText='이력 초기화를 취소했습니다.';
  else {const currentResetResult=await requestAnchorHistoryCommand('anchor-history-reset',{animation_id:reviewAnimationIdentity,animation_version:reviewAnimationVersion});currentFeedbackText=`${currentResetResult.cleared}건 목록 초기화 · 원본 파일 유지`;}
 }
 const currentHistoryResponse=await requestAnchorHistoryCommand('anchor-history',{animation_id:reviewAnimationIdentity,animation_version:reviewAnimationVersion});
 const currentSelectedRecord=currentHistoryResponse.items.find(currentHistoryRecord=>currentHistoryRecord.id===currentSelectedId);
 if(['inspect','result','restore'].includes(currentActionName)&&!currentSelectedRecord)throw Error('현재 동작의 이력을 먼저 선택하세요.');
 let currentDetailRecord=currentSelectedRecord||null;
 if(currentActionName==='result')currentDetailRecord=(await requestAnchorHistoryCommand('anchor-load',{id:currentSelectedId})).document;
 if(currentActionName==='restore'){await restoreAnchorHistoryRecord(currentSelectedRecord);currentFeedbackText=document.querySelector('#anchorHistoryStatus').textContent;}
 return [{__type__:'update',choices:currentHistoryResponse.items.map(currentHistoryRecord=>[`${currentHistoryRecord.created_at||currentHistoryRecord.id} · ${currentHistoryRecord.id}`,currentHistoryRecord.id]),value:currentSelectedRecord?.id||null},currentSelectedRecord?.id||'',currentActionName==='list'&&currentSelectedRecord?{__type__:'update'}:currentDetailRecord,'',currentFeedbackText];
};
const anchorHistoryViewState={page:0,selected:null};
async function restoreAnchorHistoryRecord(historyRecordValue){
 const historyStatusElement=document.querySelector('#anchorHistoryStatus');
 try{
   const {document:coordinateDocumentValue}=await requestAnchorHistoryCommand('anchor-load',{id:historyRecordValue.id});
   const currentDocumentValue=buildCoordinateArtifact();
   if(JSON.stringify(coordinateDocumentValue.source)!==JSON.stringify(currentDocumentValue.source)||coordinateDocumentValue.coordinateMode!==currentDocumentValue.coordinateMode||coordinateDocumentValue.frames.length!==currentDocumentValue.frames.length)throw new Error('현재 애니메이션 출처·시트·좌표 모드와 다른 이력입니다.');
   coordinateDocumentValue.frames.forEach((frameValue,indexValue)=>{const currentFrameValue=currentDocumentValue.frames[indexValue];for(const fieldNameValue of ['frameId','direction','image','rect'])if(JSON.stringify(frameValue[fieldNameValue])!==JSON.stringify(currentFrameValue[fieldNameValue]))throw new Error('프레임 구성이 다른 이력입니다.');});
   pauseFramePlayback();
   coordinateDocumentValue.frames.forEach((frameValue,indexValue)=>{const currentFrameValue=reviewFrameRecords[indexValue],beforeCoordinateValue=copyFrameCoordinates(currentFrameValue);currentFrameValue.anchor={...frameValue.anchor};if(usesAnchorOnlyMode)currentFrameValue.contacts=[{...frameValue.anchor},{...frameValue.anchor}];else if(usesFootCentersOnly)currentFrameValue.contacts=frameValue.points.map(pointValue=>({...pointValue}));else currentFrameValue.endpoints=frameValue.points.map(pointValue=>({...pointValue}));recordCoordinateChange(currentFrameValue,beforeCoordinateValue);});
   historyStatusElement.textContent=`불러옴 · ${historyRecordValue.id}`;

 }catch(errorValue){historyStatusElement.textContent=errorValue.message;}
}
async function refreshAnchorHistoryList(){
 const historyStatusElement=document.querySelector('#anchorHistoryStatus');
 try{
 const responsePayloadValue=await requestAnchorHistoryCommand('anchor-history',{animation_id:reviewAnimationIdentity,animation_version:reviewAnimationVersion});
 if(!responsePayloadValue.items.some(recordValue=>recordValue.id===anchorHistoryViewState.selected))anchorHistoryViewState.selected=null;
 if(currentEmbeddedReviewMode){historyStatusElement.textContent=`좌표 이력 ${responsePayloadValue.items.length}건`;return;}
 renderSavedRecordHistory(document.querySelector('#anchorHistoryList'),responsePayloadValue.items,anchorHistoryViewState,{refresh:refreshAnchorHistoryList,restore:restoreAnchorHistoryRecord,inspect:async(historyRecordValue)=>{
 try{const responseDocumentValue=await requestAnchorHistoryCommand('anchor-load',{id:historyRecordValue.id});const historyDetailElement=document.querySelector('#anchorHistoryDetail');historyDetailElement.hidden=false;historyDetailElement.textContent=JSON.stringify(responseDocumentValue.document,null,2);}catch(errorValue){historyStatusElement.textContent=errorValue.message;}
 }});
 historyStatusElement.textContent=responsePayloadValue.items.length?'카드를 선택한 뒤 저장 입력을 조회하거나 불러오세요.':'저장된 좌표가 없습니다. 좌표 저장 버튼으로 생성 이력을 남기세요.';
 }catch(errorValue){historyStatusElement.textContent=errorValue.message;}
}
const saveAnchorHistoryButton=document.querySelector('#saveAnchorHistory');
async function saveCurrentAnchorCoordinates(){
 if(saveAnchorHistoryButton.disabled)throw Error('좌표 저장 중입니다. 완료 후 다시 시도하세요.');
 saveAnchorHistoryButton.disabled=true;
 try{const savedCoordinateSnapshot=JSON.stringify(reviewFrameRecords.map(copyFrameCoordinates));const savedHistoryRecord=await requestAnchorHistoryCommand('anchor-save',{document:buildCoordinateArtifact()});savedCoordinateSnapshotValue=savedCoordinateSnapshot;sessionStorage.removeItem(actionDraftStorageKey);refreshCoordinateStatus();await refreshAnchorHistoryList();document.querySelector('#anchorHistoryStatus').textContent=`저장 완료 · ${savedHistoryRecord.id}`;}
 catch(errorValue){document.querySelector('#anchorHistoryStatus').textContent=errorValue.message;}
 finally{saveAnchorHistoryButton.disabled=false;}
 return document.querySelector('#anchorHistoryStatus').textContent;
}
saveAnchorHistoryButton.onclick=saveCurrentAnchorCoordinates;
window.anchorReviewSaveCoordinates=saveCurrentAnchorCoordinates;

if(typeof window.location!=='undefined'&&/^https?:$/.test(window.location.protocol))refreshAnchorHistoryList();

document.querySelector('#resetAnchorHistory').onclick=async()=>{
 if(!window.confirm('현재 애니메이션 버전의 좌표 생성 이력을 전체 초기화할까요? 목록만 초기화하며 원본 좌표 파일과 현재 편집값은 유지합니다.'))return;
 const resetHistoryButton=document.querySelector('#resetAnchorHistory');resetHistoryButton.disabled=true;
 try{const resetHistoryResult=await requestAnchorHistoryCommand('anchor-history-reset',{animation_id:reviewAnimationIdentity,animation_version:reviewAnimationVersion});anchorHistoryViewState.page=0;anchorHistoryViewState.selected=null;document.querySelector('#anchorHistoryDetail').hidden=true;await refreshAnchorHistoryList();document.querySelector('#anchorHistoryStatus').textContent=`${resetHistoryResult.cleared}건 초기화 완료 · 원본 좌표 파일 유지`;}
 catch(errorValue){document.querySelector('#anchorHistoryStatus').textContent=errorValue.message;}
 finally{resetHistoryButton.disabled=false;}
};
