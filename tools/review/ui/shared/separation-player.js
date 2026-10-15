// 컴포넌트마다 결과·캔버스·재생 수명을 분리한다. 프레임 이동은 서버를 호출하지 않는다.
const currentViewPanels={compare:['source','combined'],parts:['base','outfit'],all:['source','base','outfit','combined']};
const currentPanelLabels={source:'원본',base:'신체 베이스',outfit:'복장',combined:'복장 겹쳐보기'};
let currentManifestRecord=null,currentImageSources=[],currentFrameNumber=0,currentPlaybackTimer=null;
let currentRequestSequence=0,currentFetchController=null,currentViewName='compare',currentTransformRecord={x:0,y:0,scale:1};
const showPreviewMessage=currentMessageText=>{element.querySelector('[data-player-status]').textContent=currentMessageText;return currentMessageText;};
const stopPreviewPlayback=()=>{clearInterval(currentPlaybackTimer);currentPlaybackTimer=null;};
const requirePreviewReady=()=>{if(!currentManifestRecord)throw Error('완료된 결과를 먼저 조회하세요.');};
const updatePreviewPanels=()=>{
 for(const currentPanelElement of element.querySelectorAll('[data-review-part]'))currentPanelElement.hidden=!currentViewPanels[currentViewName].includes(currentPanelElement.dataset.reviewPart);
};
const drawPreviewFrame=()=>{
 const currentFrameRecord=currentManifestRecord.frames[currentFrameNumber],currentFrameSize=currentManifestRecord.size;
 for(const [currentSourceIndex,currentSourceName] of ['source','base','outfit'].entries()){
  const currentCanvasElement=element.querySelector('[data-canvas-part="'+currentSourceName+'"]');
  currentCanvasElement.width=currentFrameSize;currentCanvasElement.height=currentFrameSize;
  currentCanvasElement.getContext('2d').drawImage(currentImageSources[currentSourceIndex],currentFrameRecord.column*currentFrameSize,currentFrameRecord.row*currentFrameSize,currentFrameSize,currentFrameSize,0,0,currentFrameSize,currentFrameSize);
 }
 const currentCombinedCanvas=element.querySelector('[data-canvas-part="combined"]');
 currentCombinedCanvas.width=currentFrameSize;currentCombinedCanvas.height=currentFrameSize;
 const currentCombinedContext=currentCombinedCanvas.getContext('2d');
 currentCombinedContext.drawImage(element.querySelector('[data-canvas-part="base"]'),0,0);
 currentCombinedContext.drawImage(element.querySelector('[data-canvas-part="outfit"]'),currentTransformRecord.x,currentTransformRecord.y,currentFrameSize*currentTransformRecord.scale,currentFrameSize*currentTransformRecord.scale);
 return showPreviewMessage(`프레임 ${currentFrameNumber+1}/${currentManifestRecord.frames.length} · ${currentFrameRecord.source.frameId}`+(currentPlaybackTimer?' · 재생 중':' · 정지'));
};
const loadPreviewResult=async()=>{
 stopPreviewPlayback();currentFetchController?.abort();currentManifestRecord=null;currentImageSources=[];
 const currentRequestNumber=++currentRequestSequence;
 currentFrameNumber=0;currentViewName='compare';currentTransformRecord={x:0,y:0,scale:1};
 const currentCanvasContainer=element.querySelector('[data-player-images]');currentCanvasContainer.replaceChildren();
 if(!props.value){showPreviewMessage('완료된 결과를 조회하세요.');return;}
 showPreviewMessage('결과 로딩 중');
 try{
  const currentResultPayload=JSON.parse(props.value);
  if(!currentResultPayload.base)throw Error('결과 주소가 없습니다.');
  currentFetchController=new AbortController();
  const currentManifestResponse=await fetch(currentResultPayload.base+'manifest.json',{signal:currentFetchController.signal});
  if(!currentManifestResponse.ok)throw Error('결과 메타데이터 조회 실패');
  const currentPendingManifest=await currentManifestResponse.json();
  if(currentPendingManifest.schema_version!==2)throw Error('이전 머리·좌우 분리 결과는 검수 지원이 종료되었습니다. 두 프롬프트로 새로 생성하세요.');
  if(!Number.isInteger(currentPendingManifest.size)||currentPendingManifest.size<1||!Number.isFinite(currentPendingManifest.fps)||currentPendingManifest.fps<=0||!Array.isArray(currentPendingManifest.frames)||!currentPendingManifest.frames.length)throw Error('결과 크기·FPS·프레임 형식 오류');
  for(const currentFrameRecord of currentPendingManifest.frames)if(!Number.isInteger(currentFrameRecord.column)||currentFrameRecord.column<0||!Number.isInteger(currentFrameRecord.row)||currentFrameRecord.row<0||typeof currentFrameRecord.source?.frameId!=='string')throw Error('결과 프레임 좌표·원본 ID 형식 오류');
  const currentPendingImages=await Promise.all(['source','base','outfit'].map(currentSourceName=>new Promise((resolvePreviewImage,rejectPreviewImage)=>{
   const currentImageElement=new Image();currentImageElement.onload=()=>resolvePreviewImage(currentImageElement);currentImageElement.onerror=()=>rejectPreviewImage(Error('시트 로딩 실패'));currentImageElement.src=currentResultPayload.base+currentSourceName+'-sheet.png';
  })));
  if(currentRequestNumber!==currentRequestSequence||!element.isConnected)return;
  for(const currentFrameRecord of currentPendingManifest.frames)for(const currentImageElement of currentPendingImages)if((currentFrameRecord.column+1)*currentPendingManifest.size>currentImageElement.naturalWidth||(currentFrameRecord.row+1)*currentPendingManifest.size>currentImageElement.naturalHeight)throw Error('프레임 좌표가 시트 범위를 벗어났습니다.');
  for(const [currentPartName,currentPartLabel] of Object.entries(currentPanelLabels)){
   const currentPanelElement=document.createElement('figure');currentPanelElement.dataset.reviewPart=currentPartName;currentPanelElement.style.minWidth='0';
   const currentCanvasElement=document.createElement('canvas');currentCanvasElement.dataset.canvasPart=currentPartName;currentCanvasElement.setAttribute('aria-label',currentPartLabel+' 프레임');currentCanvasElement.style.width='100%';currentCanvasElement.style.height='auto';
   const currentCaptionElement=document.createElement('figcaption');currentCaptionElement.textContent=currentPartLabel;currentPanelElement.append(currentCaptionElement,currentCanvasElement);currentCanvasContainer.append(currentPanelElement);
  }
  currentManifestRecord=currentPendingManifest;currentImageSources=currentPendingImages;updatePreviewPanels();drawPreviewFrame();
 }catch(currentErrorValue){if(currentRequestNumber===currentRequestSequence&&element.isConnected){currentManifestRecord=null;showPreviewMessage('결과 오류: '+currentErrorValue.message);}}
};
const currentPlaybackHandler=currentActionName=>{
 requirePreviewReady();if(!['prev','next','play','stop'].includes(currentActionName))throw Error('지원하지 않는 재생 명령입니다.');
 stopPreviewPlayback();
 if(currentActionName==='play'){
  if(currentManifestRecord.frames.length<2)throw Error('단일 프레임 결과입니다. 재생 없이 비교하세요.');
  currentPlaybackTimer=setInterval(()=>{if(!element.isConnected){stopPreviewPlayback();return;}if(document.hidden)return;currentFrameNumber=(currentFrameNumber+1)%currentManifestRecord.frames.length;drawPreviewFrame();},1000/currentManifestRecord.fps);
 }else if(currentActionName==='prev'||currentActionName==='next')currentFrameNumber=(currentFrameNumber+(currentActionName==='next'?1:-1)+currentManifestRecord.frames.length)%currentManifestRecord.frames.length;
 return drawPreviewFrame();
};
const currentSeekHandler=currentFrameValue=>{requirePreviewReady();if(!Number.isInteger(currentFrameValue)||currentFrameValue<1||currentFrameValue>currentManifestRecord.frames.length)throw Error('프레임 번호가 범위를 벗어났습니다.');stopPreviewPlayback();currentFrameNumber=currentFrameValue-1;return drawPreviewFrame();};
const currentViewHandler=currentSelectedView=>{requirePreviewReady();if(!Object.hasOwn(currentViewPanels,currentSelectedView))throw Error('지원하지 않는 비교 보기입니다.');currentViewName=currentSelectedView;updatePreviewPanels();return '비교 보기를 변경했습니다.';};
const currentTransformHandler=(currentActionName,currentInputValues)=>{requirePreviewReady();[currentTransformRecord]=currentActionName==='reset'?[{x:0,y:0,scale:1}]:window.calculateJoypadTransforms(currentActionName,currentInputValues,[currentTransformRecord]);drawPreviewFrame();return {...currentTransformRecord,message:'겹쳐보기만 조정했습니다. 저장된 이미지는 변경하지 않습니다.'};};
const currentReadinessHandler=()=>({ready:Boolean(currentManifestRecord)&&currentImageSources.length===3,frameCount:currentManifestRecord?.frames.length??0,playing:Boolean(currentPlaybackTimer),message:element.querySelector('[data-player-status]').textContent});
const currentHandlerRecords={Readiness:currentReadinessHandler,Playback:currentPlaybackHandler,Seek:currentSeekHandler,View:currentViewHandler,Transform:currentTransformHandler};
for(const [currentHandlerSuffix,currentHandlerFunction] of Object.entries(currentHandlerRecords))window[currentPlayerIdentifier+currentHandlerSuffix]=currentHandlerFunction;
const currentRemovalObserver=new MutationObserver(()=>{
 if(element.isConnected)return;
 stopPreviewPlayback();++currentRequestSequence;currentFetchController?.abort();currentRemovalObserver.disconnect();
 for(const [currentHandlerSuffix,currentHandlerFunction] of Object.entries(currentHandlerRecords))if(window[currentPlayerIdentifier+currentHandlerSuffix]===currentHandlerFunction)delete window[currentPlayerIdentifier+currentHandlerSuffix];
});
currentRemovalObserver.observe(document.body,{childList:true,subtree:true});
watch('value',loadPreviewResult);loadPreviewResult();
