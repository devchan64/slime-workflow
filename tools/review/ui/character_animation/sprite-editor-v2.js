/* 참조와 프레임을 같은 출력 좌표계에서 비교하는 브라우저 편집기. */
(()=>{
'use strict';
const SPRITE_V2_ZOOM_LIMIT=4,SPRITE_V2_UNDO_LIMIT=50,SPRITE_V2_MOVE_STEP=1,SPRITE_V2_SCALE_STEP=.01;
const SPRITE_V2_GUIDE_NAMES=['머리끝','턱','어깨','허리','골반','무릎','발바닥'];
const SPRITE_V2_GUIDE_RATIOS=[.04,.23,.30,.49,.61,.78,.95];
const SPRITE_V2_COLOR_REFERENCE='#26cfca',SPRITE_V2_COLOR_FRAME='#e685dc';
let currentProjectIdentifier=null,currentProjectDocument=null,currentParentRevision=null,currentFrameIndex=0,currentGuideIndex=0,currentUnsavedChanges=false,currentPlayingState=false,currentPlaybackTimestamp=0,currentBusyState=false;
const currentViewOptions={zoom:'fit',background:'checker',overlay:false,onion:false,guides:true};
function readEditorViewOption(currentOptionName){return currentViewOptions[currentOptionName];}
let currentUploadTarget='reference';
let currentEditorTarget='frame',currentEditorMode='image';
const SPRITE_V2_TARGET_LABELS={frame:'현재 프레임',reference:'레퍼런스',selected:'체크한 프레임',all:'전체 프레임'};
const SPRITE_V2_MODE_LABELS={image:'이미지 배치',face:'얼굴 원',guide:'신체 가이드'};
let currentProjectChoices=[],currentRevisionChoices=[],currentLoadedRevision=null;
const currentEditorActions=new Map();
const currentImageCache=new Map(),currentUndoRecords=[],currentSelectedFrames=new Set();
const findEditorElement=(elementSuffixValue)=>document.getElementById('sv2-'+elementSuffixValue);
const writeEditorStatus=(currentMessageText)=>{findEditorElement('status').textContent=currentMessageText;};
function cloneEditorDocument(){return structuredClone(currentProjectDocument);}
function retainUndoSnapshot(){if(!currentProjectDocument)throw Error('먼저 작업을 생성하거나 불러오세요.');stopEditorPlayback();currentUndoRecords.push(cloneEditorDocument());if(currentUndoRecords.length>SPRITE_V2_UNDO_LIMIT)currentUndoRecords.shift();currentUnsavedChanges=true;}
function selectedEditorRecord(){return currentEditorTarget==='reference'?currentProjectDocument?.reference:currentProjectDocument?.frames[currentFrameIndex];}
function collectEditorTargets(){if(!currentProjectDocument)return[];const currentTargetMode=currentEditorTarget;if(currentTargetMode==='reference')return currentProjectDocument.reference?[currentProjectDocument.reference]:[];if(currentTargetMode==='all')return currentProjectDocument.frames;if(currentTargetMode==='selected')return currentProjectDocument.frames.filter(currentFrameRecord=>currentSelectedFrames.has(currentFrameRecord.id));return currentProjectDocument.frames[currentFrameIndex]?[currentProjectDocument.frames[currentFrameIndex]]:[];}
async function requestEditorCommand(currentCommandName,currentPayloadRecord={}){
 const currentResponseValue=await fetch(window.spriteV2ServerBase+'/management/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({service:'character-animation',command:'sprite-v2-'+currentCommandName,payload:currentPayloadRecord})});
 const currentResponseRecord=await currentResponseValue.json();if(!currentResponseValue.ok||currentResponseRecord.error)throw Error(currentResponseRecord.error||'관리 명령 실패');return currentResponseRecord;
}
function refreshEditorAvailability(){
 const currentWorkExists=Boolean(currentProjectDocument),currentFrameExists=Boolean(currentProjectDocument?.frames.length);
 for(const currentControlElement of document.querySelectorAll('#sprite-v2-root button,#sprite-v2-root input,#sprite-v2-root select')){
  const currentControlName=currentControlElement.id;
  const currentAlwaysAllowed=['sv2-name','sv2-size','sv2-create','sv2-projects','sv2-project-refresh','sv2-load','sv2-zoom','sv2-background','sv2-guides'];
  let currentDisabledReason=currentBusyState?'등록·저장 처리가 끝난 뒤 사용할 수 있습니다.':!currentWorkExists&&!currentAlwaysAllowed.includes(currentControlName)?'작업을 생성하거나 불러오세요.':'';
  if(!currentDisabledReason&&['sv2-earlier','sv2-later','sv2-duplicate','sv2-remove','sv2-play','sv2-prev','sv2-next','sv2-export','sv2-duration','sv2-timeline'].includes(currentControlName)&&!currentFrameExists)currentDisabledReason='프레임을 먼저 등록하세요.';
  if(!currentDisabledReason&&currentControlName==='sv2-undo'&&!currentUndoRecords.length)currentDisabledReason='편집한 뒤 실행 취소할 수 있습니다.';
  if(!currentDisabledReason&&['sv2-guide-label','sv2-guide-axis','sv2-guide-position','sv2-guide-remove'].includes(currentControlName)&&!selectedEditorRecord()?.guides[currentGuideIndex])currentDisabledReason='가로선 또는 세로선을 추가한 뒤 편집하세요.';
  if(!currentDisabledReason&&currentControlName==='sv2-guide-copy'&&(!currentProjectDocument?.reference||!collectEditorTargets().some(currentImageRecord=>currentImageRecord!==currentProjectDocument.reference)))currentDisabledReason='레퍼런스를 등록하고 복사할 프레임을 편집 대상으로 선택하세요.';
  currentControlElement.disabled=Boolean(currentDisabledReason);currentControlElement.title=currentDisabledReason;currentControlElement.setAttribute('aria-description',currentDisabledReason);
 }
}
async function runEditorAction(currentActionCallback,currentPropagateError=false){if(currentBusyState)return;currentBusyState=true;refreshEditorAvailability();try{await currentActionCallback();}catch(currentErrorValue){writeEditorStatus(currentErrorValue.message);if(currentPropagateError)throw currentErrorValue;}finally{currentBusyState=false;refreshEditorAvailability();}}
async function refreshEditorProjects(){const currentResponseRecord=await requestEditorCommand('list');currentProjectChoices=currentResponseRecord.items.map(currentProjectRecord=>[`${currentProjectRecord.name} · ${currentProjectRecord.frames}장 · ${currentProjectRecord.id}`,currentProjectRecord.id]);const currentProjectSelect=findEditorElement('projects');if(currentProjectSelect){currentProjectSelect.replaceChildren(...currentProjectChoices.map(([currentProjectLabel,currentProjectId])=>new Option(currentProjectLabel,currentProjectId)));if(currentProjectIdentifier)currentProjectSelect.value=currentProjectIdentifier;}}
async function refreshEditorHistory(){if(!currentProjectIdentifier)throw Error('먼저 작업을 생성하거나 불러오세요.');const currentResponseRecord=await requestEditorCommand('history',{id:currentProjectIdentifier});currentRevisionChoices=currentResponseRecord.items.map(currentRevisionRecord=>[`${currentRevisionRecord.saved_at} · ${currentRevisionRecord.frames}장 · ${currentRevisionRecord.revision}`,currentRevisionRecord.revision]);const currentHistorySelect=findEditorElement('history');if(currentHistorySelect)currentHistorySelect.replaceChildren(...currentRevisionChoices.map(([currentRevisionLabel,currentRevisionId])=>new Option(currentRevisionLabel,currentRevisionId)));}
async function cacheEditorImage(currentAssetHash,currentBase64Value){if(currentImageCache.has(currentAssetHash))return;const currentImageElement=new Image();currentImageElement.src='data:image/png;base64,'+currentBase64Value;await currentImageElement.decode();currentImageCache.set(currentAssetHash,currentImageElement);}
async function loadEditorProject(currentProjectId,currentRevisionId=null){if(!currentProjectId)throw Error('불러올 작업을 선택하세요.');if(currentUnsavedChanges&&!confirm('저장하지 않은 편집이 있습니다. 불러오면 해당 편집을 버립니다. 계속할까요?'))return;stopEditorPlayback();const currentResponseRecord=await requestEditorCommand('load',{id:currentProjectId,revision:currentRevisionId});for(const [currentAssetHash,currentBase64Value] of Object.entries(currentResponseRecord.images))await cacheEditorImage(currentAssetHash,currentBase64Value);currentProjectIdentifier=currentProjectId;currentProjectDocument=currentResponseRecord.document;currentParentRevision=currentResponseRecord.latest;currentFrameIndex=0;currentUndoRecords.length=0;currentSelectedFrames.clear();currentUnsavedChanges=false;refreshEditorScreen();await refreshEditorHistory();currentLoadedRevision=currentResponseRecord.revision;if(findEditorElement('history'))findEditorElement('history').value=currentLoadedRevision;writeEditorStatus(`작업 ${currentProjectId} · 버전 ${currentResponseRecord.revision} 불러옴`);}
function createEditorImageRecord(currentAssetHash,currentFileName){const currentCellSize=currentProjectDocument.cellSize;return{id:crypto.randomUUID(),asset:currentAssetHash,name:currentFileName.slice(0,200),x:0,y:0,scale:1,duration:0,face:{x:currentCellSize/2,y:currentCellSize*.15,radius:currentCellSize*.095},guides:[...SPRITE_V2_GUIDE_NAMES.map((currentGuideName,currentGuideIndex)=>({label:currentGuideName,axis:'y',position:Math.round(currentCellSize*SPRITE_V2_GUIDE_RATIOS[currentGuideIndex])})),{label:'중심',axis:'x',position:currentCellSize/2}]};}
async function registerEditorFiles(currentFileValues){if(!currentProjectIdentifier)throw Error('먼저 작업을 생성하세요.');const currentTargetMode=currentUploadTarget;if(currentTargetMode!=='append'&&currentFileValues.length!==1)throw Error('참조 등록·교체는 이미지 한 장을 선택하세요.');if(currentTargetMode==='replace'&&!currentProjectDocument.frames[currentFrameIndex])throw Error('교체할 프레임을 선택하세요.');if(currentTargetMode==='append'&&currentProjectDocument.frames.length+currentFileValues.length>128)throw Error('최대 128프레임입니다.');const currentRegisteredRecords=[];for(const currentFileValue of currentFileValues){if(currentFileValue.size>8000000)throw Error('한 장당 최대 8MB입니다.');const currentBase64Value=await new Promise((resolveFileValue,rejectFileValue)=>{const currentFileReader=new FileReader();currentFileReader.onload=()=>resolveFileValue(currentFileReader.result.split(',')[1]);currentFileReader.onerror=rejectFileValue;currentFileReader.readAsDataURL(currentFileValue);});const currentUploadRecord=await requestEditorCommand('upload',{id:currentProjectIdentifier,data:currentBase64Value});await cacheEditorImage(currentUploadRecord.asset,currentUploadRecord.data);currentRegisteredRecords.push(createEditorImageRecord(currentUploadRecord.asset,currentFileValue.name||'클립보드 이미지'));}retainUndoSnapshot();if(currentTargetMode==='reference')currentProjectDocument.reference=currentRegisteredRecords[0];else if(currentTargetMode==='replace'){const previousFrameRecord=currentProjectDocument.frames[currentFrameIndex];currentProjectDocument.frames[currentFrameIndex]={...previousFrameRecord,asset:currentRegisteredRecords[0].asset,name:currentRegisteredRecords[0].name};}else{currentFrameIndex=currentProjectDocument.frames.length;currentProjectDocument.frames.push(...currentRegisteredRecords);}refreshEditorScreen();writeEditorStatus(`${currentRegisteredRecords.length}장 등록 · 수정본 저장이 필요합니다.`);}
window.spriteV2FrameCount=()=>currentProjectDocument?.frames.length||0;
window.spriteV2ValidateSheet=(currentFrameCount)=>{
 if(currentBusyState)throw Error('현재 등록·저장 작업이 끝난 뒤 적용하세요.');
 if(!currentProjectDocument||!currentProjectIdentifier)throw Error('작업을 먼저 생성하거나 불러오세요.');
 if(currentProjectDocument.frames.length+currentFrameCount>128)throw Error('기존 프레임을 포함하여 최대 128프레임입니다.');
 return {id:currentProjectIdentifier,frameCount:currentProjectDocument.frames.length};
};
window.spriteV2AppendSheet=async(currentFrameFiles,currentExpectedProject)=>{
 window.spriteV2ValidateSheet(currentFrameFiles.length);
 if(currentProjectIdentifier!==currentExpectedProject.id||currentProjectDocument.frames.length!==currentExpectedProject.frameCount)throw Error('작업이 변경되었습니다. 분할 적용을 다시 실행하세요.');
 await runEditorAction(async()=>{
  const currentPreviousTarget=currentUploadTarget;
  try{currentUploadTarget='append';await registerEditorFiles(currentFrameFiles);}finally{currentUploadTarget=currentPreviousTarget;}
 },true);
};
function drawEditorImage(currentCanvasContext,currentImageRecord,currentOpacityValue=1){if(!currentImageRecord)return;const currentImageElement=currentImageCache.get(currentImageRecord.asset);if(!currentImageElement)return;const currentCellSize=currentProjectDocument.cellSize;const currentImageScale=currentImageRecord.scale*currentCellSize/Math.max(currentImageElement.width,currentImageElement.height);currentCanvasContext.save();currentCanvasContext.globalAlpha=currentOpacityValue;currentCanvasContext.drawImage(currentImageElement,(currentCellSize-currentImageElement.width*currentImageScale)/2+currentImageRecord.x,(currentCellSize-currentImageElement.height*currentImageScale)/2+currentImageRecord.y,currentImageElement.width*currentImageScale,currentImageElement.height*currentImageScale);currentCanvasContext.restore();}
function drawEditorGuides(currentCanvasContext,currentImageRecord,currentColorValue,currentDashedState=false,currentDrawFace=true){if(!currentImageRecord)return;const currentCellSize=currentProjectDocument.cellSize;currentCanvasContext.save();currentCanvasContext.strokeStyle=currentColorValue;currentCanvasContext.fillStyle=currentColorValue;currentCanvasContext.lineWidth=1;currentCanvasContext.font='10px sans-serif';currentCanvasContext.setLineDash(currentDashedState?[5,4]:[]);for(const currentGuideRecord of currentImageRecord.guides){currentCanvasContext.beginPath();if(currentGuideRecord.axis==='y'){currentCanvasContext.moveTo(0,currentGuideRecord.position);currentCanvasContext.lineTo(currentCellSize,currentGuideRecord.position);currentCanvasContext.fillText(currentGuideRecord.label,3,currentGuideRecord.position-3);}else{currentCanvasContext.moveTo(currentGuideRecord.position,0);currentCanvasContext.lineTo(currentGuideRecord.position,currentCellSize);}currentCanvasContext.stroke();}if(currentDrawFace){currentCanvasContext.beginPath();currentCanvasContext.arc(currentImageRecord.face.x,currentImageRecord.face.y,currentImageRecord.face.radius,0,Math.PI*2);currentCanvasContext.stroke();}currentCanvasContext.restore();}
function drawEditorCanvas(currentCanvasElement,currentReferenceMode){const currentCellSize=currentProjectDocument?.cellSize||384;currentCanvasElement.width=currentCellSize;currentCanvasElement.height=currentCellSize;const currentZoomValue=readEditorViewOption('zoom');const currentFitSize=Math.min(...['reference','frame'].map(currentCanvasName=>findEditorElement(currentCanvasName).parentElement.clientWidth||currentCellSize));const currentDisplaySize=currentZoomValue==='fit'?currentFitSize:currentCellSize*Math.min(SPRITE_V2_ZOOM_LIMIT,Number(currentZoomValue));currentCanvasElement.style.width=currentDisplaySize+'px';currentCanvasElement.style.height=currentDisplaySize+'px';const currentCanvasContext=currentCanvasElement.getContext('2d');const currentBackgroundMode=readEditorViewOption('background');currentCanvasContext.fillStyle=currentBackgroundMode==='dark'?'#252525':'#ffffff';currentCanvasContext.fillRect(0,0,currentCellSize,currentCellSize);if(currentBackgroundMode==='checker'){currentCanvasContext.fillStyle='#dedede';for(let currentRowIndex=0;currentRowIndex<currentCellSize;currentRowIndex+=16)for(let currentColumnIndex=0;currentColumnIndex<currentCellSize;currentColumnIndex+=16)if((currentRowIndex/16+currentColumnIndex/16)%2===0)currentCanvasContext.fillRect(currentColumnIndex,currentRowIndex,16,16);}if(!currentProjectDocument)return;const currentImageRecord=currentReferenceMode?currentProjectDocument.reference:currentProjectDocument.frames[currentFrameIndex];if(!currentReferenceMode&&readEditorViewOption('onion'))drawEditorImage(currentCanvasContext,currentProjectDocument.frames[(currentFrameIndex-1+currentProjectDocument.frames.length)%currentProjectDocument.frames.length],.25);drawEditorImage(currentCanvasContext,currentImageRecord);if(!currentReferenceMode&&readEditorViewOption('overlay'))drawEditorImage(currentCanvasContext,currentProjectDocument.reference,.35);if(readEditorViewOption('guides')){drawEditorGuides(currentCanvasContext,currentImageRecord,currentReferenceMode?SPRITE_V2_COLOR_REFERENCE:SPRITE_V2_COLOR_FRAME);if(!currentReferenceMode)drawEditorGuides(currentCanvasContext,currentProjectDocument.reference,SPRITE_V2_COLOR_REFERENCE,true);else drawEditorGuides(currentCanvasContext,currentProjectDocument.frames[currentFrameIndex],SPRITE_V2_COLOR_FRAME,true,false);}}
function renderEditorCanvases(){findEditorElement('timeline').value=currentFrameIndex;drawEditorCanvas(findEditorElement('reference'),true);drawEditorCanvas(findEditorElement('frame'),false);findEditorElement('frame-title').textContent=`선택 프레임 ${currentProjectDocument?.frames.length?currentFrameIndex+1:0} / ${currentProjectDocument?.frames.length||0}`;}
function refreshEditorScreen(){findEditorElement('timeline').max=Math.max(0,(currentProjectDocument?.frames.length||0)-1);if(findEditorElement('project-summary'))findEditorElement('project-summary').textContent=currentProjectDocument?`${currentProjectDocument.name} · ${currentProjectDocument.cellSize} × ${currentProjectDocument.cellSize}`:'작업을 불러오세요.';findEditorElement('frame-list').replaceChildren(...(currentProjectDocument?.frames||[]).map((currentFrameRecord,currentIndexValue)=>{const currentFrameContainer=document.createElement('div');const currentCheckboxElement=document.createElement('input');currentCheckboxElement.type='checkbox';currentCheckboxElement.checked=currentSelectedFrames.has(currentFrameRecord.id);currentCheckboxElement.setAttribute('aria-label',`${currentIndexValue+1}번 프레임 일괄 선택`);currentCheckboxElement.onchange=()=>{if(currentCheckboxElement.checked)currentSelectedFrames.add(currentFrameRecord.id);else currentSelectedFrames.delete(currentFrameRecord.id);};const currentButtonElement=document.createElement('button');currentButtonElement.setAttribute('aria-pressed',String(currentIndexValue===currentFrameIndex));const currentThumbnailElement=document.createElement('img');currentThumbnailElement.src=currentImageCache.get(currentFrameRecord.asset)?.src||'';currentButtonElement.title=`원본 파일: ${currentFrameRecord.name}`;currentButtonElement.append(currentThumbnailElement,document.createTextNode(`${currentIndexValue===currentFrameIndex?'선택됨 · ':''}프레임 ${currentIndexValue+1}`));currentButtonElement.onclick=()=>{stopEditorPlayback();currentFrameIndex=currentIndexValue;refreshEditorScreen();};currentFrameContainer.append(currentCheckboxElement,currentButtonElement);return currentFrameContainer;}));refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();}
function refreshEditorFields(){
 const currentImageRecord=selectedEditorRecord();
 currentGuideIndex=Math.min(currentGuideIndex,Math.max(0,(currentImageRecord?.guides.length||0)-1));
 findEditorElement('target-summary').textContent=`${SPRITE_V2_TARGET_LABELS[currentEditorTarget]} · ${SPRITE_V2_MODE_LABELS[currentEditorMode]}`;
 const currentDisplayNumber=currentNumberValue=>Number(currentNumberValue.toFixed(2));
 findEditorElement('numeric-summary').textContent=currentImageRecord?
  `이미지 X ${currentDisplayNumber(currentImageRecord.x)} · Y ${currentDisplayNumber(currentImageRecord.y)} · 배율 ${currentDisplayNumber(currentImageRecord.scale)} / 얼굴 원 X ${currentDisplayNumber(currentImageRecord.face.x)} · Y ${currentDisplayNumber(currentImageRecord.face.y)} · 지름 ${currentDisplayNumber(currentImageRecord.face.radius*2)} / 가이드 좌표 ${currentImageRecord.guides[currentGuideIndex]?currentDisplayNumber(currentImageRecord.guides[currentGuideIndex].position):'없음'}`:'이미지를 선택해 좌표를 확인하세요.';
 findEditorElement('timing-summary').textContent=currentProjectDocument?`현재 FPS ${currentProjectDocument.fps} · 선택 프레임 유지 ${currentProjectDocument.frames[currentFrameIndex]?.duration||0}ms (0은 FPS 기준)`:'작업을 불러와 재생 설정을 확인하세요.';
 const currentReferenceRecord=currentProjectDocument?.reference,currentFrameRecord=currentProjectDocument?.frames[currentFrameIndex];
 findEditorElement('difference').textContent=currentReferenceRecord&&currentFrameRecord?
  `얼굴 지름: 참조 ${(currentReferenceRecord.face.radius*2).toFixed(1)}px / 프레임 ${(currentFrameRecord.face.radius*2).toFixed(1)}px (${(currentFrameRecord.face.radius/currentReferenceRecord.face.radius*100).toFixed(1)}%)\n`+
  currentReferenceRecord.guides.map(currentGuideRecord=>{
   const matchingGuideRecord=currentFrameRecord.guides.find(candidateGuideRecord=>candidateGuideRecord.label===currentGuideRecord.label&&candidateGuideRecord.axis===currentGuideRecord.axis);
   return matchingGuideRecord?`${currentGuideRecord.label}: ${(matchingGuideRecord.position-currentGuideRecord.position).toFixed(1)}px`:'';
  }).filter(Boolean).join(' · '):'레퍼런스와 프레임을 등록해 비교하세요.';
}

function applyEditorMove(currentDeltaX,currentDeltaY,currentRecordOverride=null){const currentTargetRecords=currentRecordOverride?[currentRecordOverride]:collectEditorTargets();if(!currentTargetRecords.length)throw Error('편집할 이미지를 선택하세요.');const currentEditMode=currentEditorMode;for(const currentImageRecord of currentTargetRecords){if(currentEditMode==='image'){currentImageRecord.x+=currentDeltaX;currentImageRecord.y+=currentDeltaY;}else if(currentEditMode==='face'){currentImageRecord.face.x+=currentDeltaX;currentImageRecord.face.y+=currentDeltaY;}else{const currentGuideRecord=currentImageRecord.guides[currentGuideIndex];if(currentGuideRecord)currentGuideRecord.position+=currentGuideRecord.axis==='x'?currentDeltaX:currentDeltaY;}}refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();}
function stopEditorPlayback(){currentPlayingState=false;if(findEditorElement('play'))findEditorElement('play').textContent='재생';}
function advanceEditorPlayback(currentTimestampValue){if(!currentPlayingState)return;const currentFrameRecord=currentProjectDocument.frames[currentFrameIndex];const currentDurationValue=currentFrameRecord.duration||1000/currentProjectDocument.fps;if(currentTimestampValue-currentPlaybackTimestamp>=currentDurationValue){currentFrameIndex=(currentFrameIndex+1)%currentProjectDocument.frames.length;currentPlaybackTimestamp=currentTimestampValue;renderEditorCanvases();refreshEditorFields();}requestAnimationFrame(advanceEditorPlayback);}
async function saveEditorProject(){if(!currentProjectIdentifier)throw Error('먼저 작업을 생성하세요.');const currentSavedRecord=await requestEditorCommand('save',{id:currentProjectIdentifier,parent:currentParentRevision,document:currentProjectDocument});currentParentRevision=currentSavedRecord.revision;currentLoadedRevision=currentSavedRecord.revision;currentUnsavedChanges=false;await refreshEditorHistory();await refreshEditorProjects();writeEditorStatus(`저장 완료 · ${currentParentRevision}`);return currentParentRevision;}
function bindEditorAction(currentElementName,currentActionCallback){currentEditorActions.set(currentElementName,currentActionCallback);const currentActionElement=findEditorElement(currentElementName);if(currentActionElement)currentActionElement.onclick=()=>runEditorAction(currentActionCallback);}
async function createEditorProject(currentProjectName,currentOutputSize){if(currentUnsavedChanges&&!confirm('저장하지 않은 편집을 버리고 새 작업을 만들까요?'))return;const currentCreatedRecord=await requestEditorCommand('create',{name:currentProjectName.trim(),cellSize:Number(currentOutputSize)});currentUnsavedChanges=false;await loadEditorProject(currentCreatedRecord.id);await refreshEditorProjects();}
async function exportEditorProject(){if(!currentProjectDocument?.frames.length)throw Error('내보낼 프레임을 먼저 등록하세요.');const currentSavedRevision=await saveEditorProject();const currentExportRecord=await requestEditorCommand('export',{id:currentProjectIdentifier,revision:currentSavedRevision});const currentArchiveBytes=Uint8Array.from(atob(currentExportRecord.data),currentCharacterValue=>currentCharacterValue.charCodeAt(0));const currentDownloadUrl=URL.createObjectURL(new Blob([currentArchiveBytes],{type:'application/zip'}));const currentDownloadLink=document.createElement('a');currentDownloadLink.href=currentDownloadUrl;currentDownloadLink.download=currentExportRecord.filename;currentDownloadLink.click();setTimeout(()=>URL.revokeObjectURL(currentDownloadUrl),10000);writeEditorStatus('PNG 프레임·시트·GIF·메타데이터 ZIP 저장 및 다운로드 완료');}
bindEditorAction('upload',()=>{if(!currentProjectIdentifier)throw Error('먼저 작업을 생성하세요.');findEditorElement('file').disabled=false;findEditorElement('file').click();});findEditorElement('file').onchange=()=>runEditorAction(async()=>{try{await registerEditorFiles([...findEditorElement('file').files]);}finally{findEditorElement('file').value='';}});
bindEditorAction('paste',async()=>{if(!navigator.clipboard?.read)throw Error('브라우저가 클립보드 읽기를 지원하지 않습니다. 입력 대상을 선택하고 Ctrl+V 또는 파일 불러오기를 사용하세요.');let currentClipboardItems;try{currentClipboardItems=await navigator.clipboard.read();}catch(currentClipboardError){throw Error('클립보드 접근이 허용되지 않았습니다. 입력 대상을 선택한 뒤 Ctrl+V 또는 파일 불러오기를 사용하세요.');}const currentClipboardFiles=[];for(const currentClipboardItem of currentClipboardItems){const currentImageType=currentClipboardItem.types.find(currentTypeValue=>currentTypeValue.startsWith('image/'));if(currentImageType)currentClipboardFiles.push(new File([await currentClipboardItem.getType(currentImageType)],'clipboard.png',{type:currentImageType}));}if(!currentClipboardFiles.length)throw Error('클립보드에 이미지가 없습니다.');await registerEditorFiles(currentClipboardFiles);});
document.getElementById('sprite-v2-root').addEventListener('paste',currentPasteEvent=>{const currentImageFiles=[...currentPasteEvent.clipboardData.items].filter(currentItemValue=>currentItemValue.type.startsWith('image/')).map(currentItemValue=>currentItemValue.getAsFile());if(currentImageFiles.length){currentPasteEvent.preventDefault();runEditorAction(()=>registerEditorFiles(currentImageFiles));}});
const currentDropArea=document.querySelector('#sprite-v2-root aside');currentDropArea.ondragover=currentDragEvent=>currentDragEvent.preventDefault();currentDropArea.ondrop=currentDropEvent=>{currentDropEvent.preventDefault();runEditorAction(()=>registerEditorFiles([...currentDropEvent.dataTransfer.files]));};
for(const [currentMoveName,currentDeltaX,currentDeltaY] of [['up',0,-1],['left',-1,0],['right',1,0],['down',0,1]]){
 currentEditorActions.set('move-'+currentMoveName,()=>{retainUndoSnapshot();applyEditorMove(currentDeltaX*SPRITE_V2_MOVE_STEP,currentDeltaY*SPRITE_V2_MOVE_STEP);});
}
for(const currentButtonElement of document.querySelectorAll('[data-sv2-move]'))currentButtonElement.onclick=()=>runEditorAction(()=>{retainUndoSnapshot();applyEditorMove(...currentButtonElement.dataset.sv2Move.split(',').map(currentNumberText=>Number(currentNumberText)*SPRITE_V2_MOVE_STEP));});
for(const [currentButtonName,currentScaleDelta] of [['smaller',-SPRITE_V2_SCALE_STEP],['larger',SPRITE_V2_SCALE_STEP]])bindEditorAction(currentButtonName,()=>{const currentTargetRecords=collectEditorTargets();if(!currentTargetRecords.length)throw Error('편집할 이미지를 선택하세요.');if(currentTargetRecords.some(currentImageRecord=>currentImageRecord.scale+currentScaleDelta<.01||currentImageRecord.scale+currentScaleDelta>8))throw Error('배율은 0.01~8입니다.');retainUndoSnapshot();for(const currentImageRecord of currentTargetRecords)currentImageRecord.scale=Math.round((currentImageRecord.scale+currentScaleDelta)*100)/100;refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();});


bindEditorAction('guide-copy',()=>{
 const currentReferenceRecord=currentProjectDocument?.reference,currentTargetRecords=collectEditorTargets().filter(currentImageRecord=>currentImageRecord!==currentReferenceRecord);
 if(!currentReferenceRecord||!currentTargetRecords.length)throw Error('레퍼런스를 등록하고 복사할 프레임을 편집 대상으로 선택하세요.');
 retainUndoSnapshot();for(const currentImageRecord of currentTargetRecords){currentImageRecord.guides=structuredClone(currentReferenceRecord.guides);currentImageRecord.face=structuredClone(currentReferenceRecord.face);}
 currentGuideIndex=0;refreshEditorFields();renderEditorCanvases();writeEditorStatus('레퍼런스 가이드와 얼굴 원 복사 완료 · 수정본 저장이 필요합니다.');
});
bindEditorAction('face-match',()=>{if(!currentProjectDocument?.reference)throw Error('레퍼런스를 먼저 등록하세요.');retainUndoSnapshot();for(const currentImageRecord of collectEditorTargets())currentImageRecord.face.radius=currentProjectDocument.reference.face.radius;refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();});
for(const [currentButtonName,currentGuideAxis] of [['guide-add','y'],['guide-vertical','x']])bindEditorAction(currentButtonName,()=>{const currentTargetRecords=collectEditorTargets();if(currentTargetRecords.some(currentImageRecord=>currentImageRecord.guides.length>=32))throw Error('가이드는 최대 32개입니다.');retainUndoSnapshot();for(const currentImageRecord of currentTargetRecords)currentImageRecord.guides.push({label:'추가 '+(currentImageRecord.guides.length+1),axis:currentGuideAxis,position:currentProjectDocument.cellSize/2});currentGuideIndex=Math.max(0,(selectedEditorRecord()?.guides.length||1)-1);refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();});
bindEditorAction('guide-remove',()=>{retainUndoSnapshot();for(const currentImageRecord of collectEditorTargets())currentImageRecord.guides.splice(currentGuideIndex,1);refreshEditorFields();renderEditorCanvases();window.spriteSheetControls?.refresh();});
bindEditorAction('undo',()=>{if(!currentUndoRecords.length)return;stopEditorPlayback();currentProjectDocument=currentUndoRecords.pop();currentFrameIndex=Math.min(currentFrameIndex,Math.max(0,currentProjectDocument.frames.length-1));currentUnsavedChanges=true;refreshEditorScreen();});
for(const [currentButtonName,currentOrderDelta] of [['earlier',-1],['later',1]])bindEditorAction(currentButtonName,()=>{const nextFrameIndex=currentFrameIndex+currentOrderDelta;if(!currentProjectDocument||nextFrameIndex<0||nextFrameIndex>=currentProjectDocument.frames.length)return;retainUndoSnapshot();[currentProjectDocument.frames[currentFrameIndex],currentProjectDocument.frames[nextFrameIndex]]=[currentProjectDocument.frames[nextFrameIndex],currentProjectDocument.frames[currentFrameIndex]];currentFrameIndex=nextFrameIndex;refreshEditorScreen();});
bindEditorAction('duplicate',()=>{const currentFrameRecord=currentProjectDocument?.frames[currentFrameIndex];if(!currentFrameRecord)throw Error('복제할 프레임이 없습니다.');if(currentProjectDocument.frames.length>=128)throw Error('최대 128프레임입니다.');retainUndoSnapshot();currentProjectDocument.frames.splice(currentFrameIndex+1,0,{...structuredClone(currentFrameRecord),id:crypto.randomUUID()});currentFrameIndex++;refreshEditorScreen();});
bindEditorAction('remove',()=>{if(!currentProjectDocument?.frames.length)return;retainUndoSnapshot();currentSelectedFrames.delete(currentProjectDocument.frames[currentFrameIndex].id);currentProjectDocument.frames.splice(currentFrameIndex,1);currentFrameIndex=Math.min(currentFrameIndex,Math.max(0,currentProjectDocument.frames.length-1));stopEditorPlayback();refreshEditorScreen();});
for(const [currentButtonName,currentFrameDelta] of [['prev',-1],['next',1]])bindEditorAction(currentButtonName,()=>{if(!currentProjectDocument?.frames.length)return;stopEditorPlayback();currentFrameIndex=(currentFrameIndex+currentFrameDelta+currentProjectDocument.frames.length)%currentProjectDocument.frames.length;refreshEditorScreen();});
bindEditorAction('play',()=>{if(currentPlayingState){stopEditorPlayback();refreshEditorScreen();return;}if(!currentProjectDocument?.frames.length)throw Error('재생할 프레임을 등록하세요.');currentPlayingState=true;currentPlaybackTimestamp=performance.now();if(findEditorElement('play'))findEditorElement('play').textContent='일시정지';requestAnimationFrame(advanceEditorPlayback);});
findEditorElement('timeline').oninput=()=>{stopEditorPlayback();currentFrameIndex=Number(findEditorElement('timeline').value);refreshEditorScreen();};
for(const currentCanvasName of ['reference','frame']){const currentCanvasElement=findEditorElement(currentCanvasName);let currentDragPosition=null;currentCanvasElement.onpointerdown=currentPointerEvent=>{if(currentBusyState)return;const currentImageRecord=currentCanvasName==='reference'?currentProjectDocument?.reference:currentProjectDocument?.frames[currentFrameIndex];if(!currentImageRecord)return;stopEditorPlayback();retainUndoSnapshot();currentEditorTarget=currentCanvasName==='reference'?'reference':'frame';refreshEditorFields();currentDragPosition={x:currentPointerEvent.clientX,y:currentPointerEvent.clientY};currentCanvasElement.setPointerCapture(currentPointerEvent.pointerId);};currentCanvasElement.onpointermove=currentPointerEvent=>{if(!currentDragPosition)return;const currentCanvasRatio=currentProjectDocument.cellSize/currentCanvasElement.getBoundingClientRect().width;const currentDeltaX=Math.round((currentPointerEvent.clientX-currentDragPosition.x)*currentCanvasRatio),currentDeltaY=Math.round((currentPointerEvent.clientY-currentDragPosition.y)*currentCanvasRatio);if(currentDeltaX||currentDeltaY){applyEditorMove(currentDeltaX,currentDeltaY);currentDragPosition.x+=currentDeltaX/currentCanvasRatio;currentDragPosition.y+=currentDeltaY/currentCanvasRatio;}};currentCanvasElement.onpointerup=currentCanvasElement.onpointercancel=()=>{currentDragPosition=null;};}
window.spriteV2UploadTarget=(currentTargetValue)=>{
 if(!['reference','append','replace'].includes(currentTargetValue))throw Error('지원하지 않는 이미지 입력 대상입니다.');
 currentUploadTarget=currentTargetValue;
};
window.spriteV2UploadControls=async(currentActionName)=>{
 if(!['upload','paste'].includes(currentActionName))throw Error('지원하지 않는 이미지 입력 명령입니다.');
 if(!currentProjectIdentifier)throw Error('먼저 작업을 생성하거나 불러오세요.');
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 await runEditorAction(currentEditorActions.get(currentActionName),true);
 return currentActionName==='upload'?'파일을 선택하면 지정한 입력 대상에 등록합니다.':findEditorElement('status').textContent;
};
window.spriteV2EditControls=async(currentActionName)=>{
 const currentAllowedActions=['move-up','move-left','move-right','move-down','smaller','larger','face-match','guide-add','guide-vertical','guide-remove','guide-copy'];
 if(!currentAllowedActions.includes(currentActionName))throw Error('지원하지 않는 편집 명령입니다.');
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument||!collectEditorTargets().length)throw Error('작업과 이미지를 등록하고 편집 대상을 선택하세요.');
 if(currentActionName==='guide-remove'&&!selectedEditorRecord()?.guides[currentGuideIndex])throw Error('삭제할 가이드를 선택하세요.');
 await runEditorAction(currentEditorActions.get(currentActionName),true);
 return '편집 반영됨 · 저장하려면 수정본 저장을 사용하세요. 실행 취소로 이전 상태를 복원할 수 있습니다.';
};
window.spriteV2ImageDeleteControls=async(currentImageTarget)=>{
 if(currentImageTarget!=='reference')throw Error('지원하지 않는 이미지 삭제 대상입니다.');
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument?.reference)throw Error('삭제할 레퍼런스 이미지가 없습니다.');
 retainUndoSnapshot();
 currentProjectDocument.reference=null;
 currentGuideIndex=0;
 refreshEditorScreen();
 return '레퍼런스 이미지를 삭제했습니다. 실행 취소로 복원하거나 수정본 저장으로 반영하세요.';
};
// 프레임 편집 명령도 레거시 화면과 같은 콜백·실행 취소 스택을 사용한다.
window.spriteV2FrameControls=async(currentActionName)=>{
 if(!['earlier','later','duplicate','remove','undo'].includes(currentActionName))throw Error('지원하지 않는 프레임 편집 명령입니다.');
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument)throw Error('먼저 작업을 생성하거나 불러오세요.');
 if(currentActionName==='undo'&&!currentUndoRecords.length)throw Error('실행 취소할 편집이 없습니다.');
 if(currentActionName!=='undo'&&!currentProjectDocument.frames.length)throw Error('편집할 프레임을 먼저 등록하세요.');
 if(currentActionName==='earlier'&&currentFrameIndex===0)throw Error('이미 첫 번째 프레임입니다.');
 if(currentActionName==='later'&&currentFrameIndex===currentProjectDocument.frames.length-1)throw Error('이미 마지막 프레임입니다.');
 await runEditorAction(currentEditorActions.get(currentActionName),true);
 return `프레임 ${currentProjectDocument.frames.length?currentFrameIndex+1:0} / ${currentProjectDocument.frames.length} · 편집 내용을 보존하려면 수정본을 저장하세요.`;
};
// 재생 명령은 기존 애니메이션 루프를 호출하며 서버 상태를 만들지 않는다.
window.spriteV2PlaybackControls=async(currentActionName)=>{
 if(!['prev','play','stop','next'].includes(currentActionName))throw Error('지원하지 않는 재생 명령입니다.');
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument?.frames.length)throw Error('작업을 불러오고 재생할 프레임을 등록하세요.');
 if(currentActionName==='stop'){stopEditorPlayback();refreshEditorScreen();}
 else if(currentActionName!=='play'||!currentPlayingState)await runEditorAction(currentEditorActions.get(currentActionName),true);
 return currentPlayingState?'재생 중입니다.':`일시정지 · ${currentFrameIndex+1} / ${currentProjectDocument.frames.length} 프레임`;
};
// 표시 설정은 저장 문서와 분리하며 서버 호출 없이 캔버스에 반영한다.
window.spriteV2ViewControls=(currentZoomValue,currentBackgroundValue,currentOverlayFlag,currentOnionFlag,currentGuideFlag)=>{
 if(!['fit','1','2','4'].includes(currentZoomValue)||!['checker','white','dark'].includes(currentBackgroundValue))throw Error('지원하지 않는 표시 설정입니다.');
 Object.assign(currentViewOptions,{zoom:currentZoomValue,background:currentBackgroundValue,overlay:currentOverlayFlag,onion:currentOnionFlag,guides:currentGuideFlag});
 renderEditorCanvases();
};
// Gradio 일반 작업 컨트롤은 공개 브라우저 명령으로 연결한다. 캔버스 상태를 서버에 복제하지 않는다.
window.spriteV2ProjectControls=async(currentActionName,currentProjectName,currentOutputSize,currentSelectedId,currentRevisionId)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 다시 시도하세요.');
 await runEditorAction(async()=>{
  if(currentActionName==='list')await refreshEditorProjects();
  else if(currentActionName==='create')await createEditorProject(currentProjectName,currentOutputSize);
  else if(currentActionName==='load')await loadEditorProject(currentSelectedId);
  else if(currentActionName==='history')await refreshEditorHistory();
  else if(currentActionName==='revision'){if(!currentRevisionId)throw Error('불러올 수정 이력을 선택하세요.');await loadEditorProject(currentProjectIdentifier,currentRevisionId);}
  else if(currentActionName==='save')await saveEditorProject();
  else if(currentActionName==='export')await exportEditorProject();
  else throw Error('지원하지 않는 작업 명령입니다.');
 },true);
 const currentSelectedValue=currentActionName==='list'?currentSelectedId:currentProjectIdentifier;
 return [{__type__:'update',choices:currentProjectChoices,value:currentProjectChoices.some(currentChoiceValue=>currentChoiceValue[1]===currentSelectedValue)?currentSelectedValue:null},findEditorElement('status').textContent,{__type__:'update',choices:currentRevisionChoices,value:currentRevisionChoices.some(currentChoiceValue=>currentChoiceValue[1]===currentLoadedRevision)?currentLoadedRevision:null}];
};
// 입력하지 않은 항목은 유지하고 저장 전 브라우저 문서만 수정한다.
window.spriteV2JoypadControls=async(currentActionName,currentInputValues)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 const currentTargetRecords=collectEditorTargets();
 if(!currentTargetRecords.length)throw Error('편집할 이미지를 선택하세요.');
 if(currentEditorMode==='guide'&&currentTargetRecords.some(currentRecordValue=>!currentRecordValue.guides[currentGuideIndex]))throw Error('모든 편집 대상에 선택한 가이드가 있어야 합니다.');
 const currentReadTransform=currentRecordValue=>({
  x:currentEditorMode==='face'?currentRecordValue.face.x:currentEditorMode==='guide'?(currentRecordValue.guides[currentGuideIndex].axis==='x'?currentRecordValue.guides[currentGuideIndex].position:0):currentRecordValue.x,
  y:currentEditorMode==='face'?currentRecordValue.face.y:currentEditorMode==='guide'?(currentRecordValue.guides[currentGuideIndex].axis==='y'?currentRecordValue.guides[currentGuideIndex].position:0):currentRecordValue.y,
  scale:currentRecordValue.scale
 });
 if(currentEditorMode==='guide'){
  const currentAxisName=['left','right','set-x'].includes(currentActionName)?'x':['up','down','set-y'].includes(currentActionName)?'y':null;
  if(currentAxisName&&currentTargetRecords.some(currentRecordValue=>currentRecordValue.guides[currentGuideIndex].axis!==currentAxisName))throw Error('선택한 가이드의 방향과 이동 축이 다릅니다.');
 }
 const currentNextTransforms=window.calculateJoypadTransforms(currentActionName,currentInputValues,currentTargetRecords.map(currentReadTransform));
 if(currentActionName!=='read')await runEditorAction(()=>{
  retainUndoSnapshot();
  currentTargetRecords.forEach((currentRecordValue,currentRecordIndex)=>{
   const currentNextRecord=currentNextTransforms[currentRecordIndex];
   if(currentEditorMode==='face'){currentRecordValue.face.x=currentNextRecord.x;currentRecordValue.face.y=currentNextRecord.y;}
   else if(currentEditorMode==='guide'){const currentGuideRecord=currentRecordValue.guides[currentGuideIndex];currentGuideRecord.position=currentNextRecord[currentGuideRecord.axis];}
   else{currentRecordValue.x=currentNextRecord.x;currentRecordValue.y=currentNextRecord.y;}
   currentRecordValue.scale=currentNextRecord.scale;
  });
  refreshEditorFields();renderEditorCanvases();
 },true);
 return {...currentReadTransform(currentTargetRecords[0]),message:currentActionName==='read'?'첫 번째 편집 대상의 현재 값을 읽었습니다.':'조이패드 적용 완료 · 실행 취소 가능 · 수정본 저장 전입니다.'};
};
window.spriteV2TargetControls=(currentTargetValue,currentModeValue)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument)throw Error('작업을 먼저 생성하거나 불러오세요.');
 if(!Object.hasOwn(SPRITE_V2_TARGET_LABELS,currentTargetValue)||!Object.hasOwn(SPRITE_V2_MODE_LABELS,currentModeValue))throw Error('편집 대상과 조절 대상을 확인하세요.');
 currentEditorTarget=currentTargetValue;currentEditorMode=currentModeValue;
 refreshEditorFields();refreshEditorAvailability();
 return `${SPRITE_V2_TARGET_LABELS[currentEditorTarget]} · ${SPRITE_V2_MODE_LABELS[currentEditorMode]} 선택됨`;
};
window.spriteV2SeekControls=(currentFrameNumber)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 const currentFrameCount=currentProjectDocument?.frames.length||0;
 if(!currentFrameCount)throw Error('프레임을 먼저 등록하세요.');
 if(!Number.isInteger(currentFrameNumber)||currentFrameNumber<1||currentFrameNumber>currentFrameCount)throw Error(`프레임 번호는 1~${currentFrameCount}입니다.`);
 stopEditorPlayback();currentFrameIndex=currentFrameNumber-1;refreshEditorScreen();
 return `${currentFrameNumber} / ${currentFrameCount} 프레임으로 이동했습니다.`;
};
function selectEditorGuideIndex(currentGuideValue){
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 const currentGuideNumber=Number(currentGuideValue);
 if(currentGuideValue===null||!Number.isInteger(currentGuideNumber)||currentGuideNumber<0||!selectedEditorRecord()?.guides[currentGuideNumber])throw Error('가이드 목록을 읽고 편집할 가이드를 선택하세요.');
 currentGuideIndex=currentGuideNumber;
 currentEditorMode='guide';refreshEditorFields();
 return selectedEditorRecord().guides[currentGuideIndex];
}
function describeGuidePositionInput(currentGuideRecord){
 const currentGuideAxis=currentGuideRecord?.axis||'y';
 return {__type__:'update',value:currentGuideRecord?.position??0,label:currentGuideAxis==='y'?'③ 위에서부터 위치 Y · px':'③ 왼쪽에서부터 위치 X · px',info:`출력 크기 ${currentProjectDocument.cellSize} × ${currentProjectDocument.cellSize}px 기준입니다. 숫자가 커지면 ${currentGuideAxis==='y'?'아래':'오른쪽'}로 이동합니다.`};
}
window.spriteV2GuideControls={
 change:async(currentGuideAction,currentGuideValue)=>{
  if(!['guide-add','guide-vertical','guide-remove'].includes(currentGuideAction))throw Error('지원하지 않는 가이드 명령입니다.');
  if(currentGuideAction==='guide-remove')selectEditorGuideIndex(currentGuideValue);
  await window.spriteV2EditControls(currentGuideAction);
  return window.spriteV2GuideControls.list();
 },
 list:()=>{
  const currentImageRecord=selectedEditorRecord();
  if(!currentImageRecord)throw Error('편집할 이미지를 먼저 선택하세요.');
  const currentGuideChoices=currentImageRecord.guides.map((currentGuideRecord,currentIndexValue)=>[`${currentIndexValue+1}. ${currentGuideRecord.label} (${currentGuideRecord.axis})`,String(currentIndexValue)]);
  const currentGuideRecord=currentImageRecord.guides[currentGuideIndex];
  return [{__type__:'update',choices:currentGuideChoices,value:currentGuideRecord?String(currentGuideIndex):null},currentGuideRecord?.label||'',currentGuideRecord?.axis||'y',describeGuidePositionInput(currentGuideRecord),currentGuideChoices.length?'가이드 목록을 읽었습니다.':'가로선 또는 세로선을 먼저 추가하세요.'];
 },
 select:(currentGuideValue)=>{const currentGuideRecord=selectEditorGuideIndex(currentGuideValue);return [currentGuideRecord.label,currentGuideRecord.axis,describeGuidePositionInput(currentGuideRecord),'가이드를 선택했습니다.'];},
 apply:async(currentGuideValue,currentLabelValue,currentAxisValue,currentPositionValue)=>{
  if(!Number.isFinite(currentPositionValue))throw Error('가이드 좌표는 유한한 숫자여야 합니다.');
  const currentLabelText=String(currentLabelValue||'').trim();
  if(!currentLabelText||currentLabelText.length>40)throw Error('가이드 이름은 1~40자로 입력하세요.');
  if(!['x','y'].includes(currentAxisValue))throw Error('가이드 방향을 선택하세요.');
  selectEditorGuideIndex(currentGuideValue);
  const currentTargetRecords=collectEditorTargets();
  if(!currentTargetRecords.length||currentTargetRecords.some(currentImageRecord=>!currentImageRecord.guides[currentGuideIndex]))throw Error('모든 편집 대상에 선택한 가이드가 있어야 합니다.');
  await runEditorAction(()=>{
   retainUndoSnapshot();
   for(const currentImageRecord of currentTargetRecords)Object.assign(currentImageRecord.guides[currentGuideIndex],{label:currentLabelText,axis:currentAxisValue,position:currentPositionValue});
   refreshEditorFields();renderEditorCanvases();
  },true);
  const currentPanelValues=window.spriteV2GuideControls.list();
  currentPanelValues[4]='가이드 설정을 적용했습니다. 실행 취소 또는 수정본 저장을 사용할 수 있습니다.';
  return currentPanelValues;
 }
};
const SPRITE_V2_NUMERIC_FIELDS=['x','y','scale','diameter','face-x','face-y','guide-position'];
function readEditorNumericValue(currentFieldName){
 if(!SPRITE_V2_NUMERIC_FIELDS.includes(currentFieldName))throw Error('지원하지 않는 수치 항목입니다.');
 const currentImageRecord=selectedEditorRecord();
 if(!currentImageRecord)throw Error('편집할 이미지를 선택하세요.');
 if(currentFieldName==='guide-position'){
  if(!currentImageRecord.guides[currentGuideIndex])throw Error('가이드를 먼저 선택하세요.');
  return currentImageRecord.guides[currentGuideIndex].position;
 }
 if(currentFieldName==='diameter')return currentImageRecord.face.radius*2;
 if(currentFieldName.startsWith('face-'))return currentImageRecord.face[currentFieldName.slice(5)];
 return currentImageRecord[currentFieldName];
}
window.spriteV2NumericControls={read:readEditorNumericValue,apply:async(currentFieldName,currentNumberValue)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 readEditorNumericValue(currentFieldName);
 const currentMinimumValue=currentFieldName==='scale'?.01:currentFieldName==='diameter'?2:-8192;
 const currentMaximumValue=currentFieldName==='scale'?8:currentFieldName==='diameter'?4096:8192;
 if(typeof currentNumberValue!=='number'||!Number.isFinite(currentNumberValue)||currentNumberValue<currentMinimumValue||currentNumberValue>currentMaximumValue)throw Error(`입력 범위는 ${currentMinimumValue}~${currentMaximumValue}입니다.`);
 const currentTargetRecords=collectEditorTargets();
 if(!currentTargetRecords.length)throw Error('편집할 이미지를 선택하세요.');
 if(currentFieldName==='guide-position'&&currentTargetRecords.some(currentImageRecord=>!currentImageRecord.guides[currentGuideIndex]))throw Error('모든 편집 대상에 선택한 가이드가 있어야 합니다.');
 await runEditorAction(()=>{
  retainUndoSnapshot();
  for(const currentImageRecord of currentTargetRecords){
   if(currentFieldName.startsWith('face-'))currentImageRecord.face[currentFieldName.slice(5)]=currentNumberValue;
   else if(currentFieldName==='diameter')currentImageRecord.face.radius=currentNumberValue/2;
   else if(currentFieldName==='guide-position')currentImageRecord.guides[currentGuideIndex].position=currentNumberValue;
   else currentImageRecord[currentFieldName]=currentNumberValue;
  }
  refreshEditorFields();renderEditorCanvases();
 },true);
 return '수치를 적용했습니다. 실행 취소할 수 있으며 수정본 저장 전에는 저장된 작업이 바뀌지 않습니다.';
}};
window.spriteV2MetadataControls=async(currentNameValue,currentSizeValue)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 사용할 수 있습니다.');
 if(!currentProjectDocument)throw Error('작업을 먼저 생성하거나 불러오세요.');
 const currentNameText=String(currentNameValue||'').trim();
 if(currentNameText.length>120)throw Error('작업명은 120자 이하여야 합니다.');
 if(!['keep','256','384'].includes(currentSizeValue))throw Error('출력 크기는 256 또는 384를 선택하세요.');
 const currentNextSize=currentSizeValue==='keep'?currentProjectDocument.cellSize:Number(currentSizeValue);
 if((!currentNameText||currentNameText===currentProjectDocument.name)&&currentNextSize===currentProjectDocument.cellSize)return '변경할 작업명 또는 출력 크기를 지정하세요.';
 await runEditorAction(()=>{
  retainUndoSnapshot();
  const currentSizeRatio=currentNextSize/currentProjectDocument.cellSize;
  for(const currentImageRecord of [...currentProjectDocument.frames,...(currentProjectDocument.reference?[currentProjectDocument.reference]:[])]){
   currentImageRecord.x*=currentSizeRatio;currentImageRecord.y*=currentSizeRatio;
   for(const currentFaceField of ['x','y','radius'])currentImageRecord.face[currentFaceField]*=currentSizeRatio;
   for(const currentGuideRecord of currentImageRecord.guides)currentGuideRecord.position*=currentSizeRatio;
  }
  currentProjectDocument.cellSize=currentNextSize;
  if(currentNameText)currentProjectDocument.name=currentNameText;
  refreshEditorScreen();
 },true);
 return '작업 설정을 적용했습니다. 실행 취소할 수 있으며 수정본 저장 전에는 저장된 작업이 바뀌지 않습니다.';
};
window.spriteV2TimingControls=async(currentFpsValue,currentDurationValue)=>{
 if(currentBusyState)throw Error('등록·저장 처리가 끝난 뒤 다시 시도하세요.');
 if(!currentProjectDocument)throw Error('작업을 먼저 생성하거나 불러오세요.');
 const hasFpsChange=currentFpsValue!==null&&currentFpsValue!==undefined;
 const hasDurationChange=currentDurationValue!==null&&currentDurationValue!==undefined;
 if(!hasFpsChange&&!hasDurationChange)throw Error('변경할 FPS 또는 유지 시간을 입력하세요.');
 if(hasFpsChange&&(!Number.isFinite(currentFpsValue)||currentFpsValue<1||currentFpsValue>60))throw Error('FPS는 1~60입니다.');
 if(hasDurationChange&&(!Number.isFinite(currentDurationValue)||currentDurationValue<0||currentDurationValue>10000))throw Error('유지 시간은 0~10000ms입니다.');
 if(hasDurationChange&&!currentProjectDocument.frames[currentFrameIndex])throw Error('유지 시간을 바꿀 프레임을 먼저 선택하세요.');
 await runEditorAction(()=>{stopEditorPlayback();retainUndoSnapshot();if(hasFpsChange)currentProjectDocument.fps=currentFpsValue;if(hasDurationChange)currentProjectDocument.frames[currentFrameIndex].duration=currentDurationValue;refreshEditorScreen();},true);
 return '재생 설정을 적용했습니다. 실행 취소할 수 있으며 수정본 저장 전에는 저장된 작업이 바뀌지 않습니다.';
};

window.addEventListener('beforeunload',currentUnloadEvent=>{if(currentUnsavedChanges){currentUnloadEvent.preventDefault();currentUnloadEvent.returnValue='';}});window.addEventListener('resize',renderEditorCanvases);renderEditorCanvases();runEditorAction(refreshEditorProjects);
})();
