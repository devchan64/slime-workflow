// 게시 HTML의 실행 코드·스타일을 가져오지 않는다. 공용 편집 구현과 JSON만 연결한다.
let currentAnchorDisposer=null;
const currentAnchorHandlerNames=['anchorReviewSelection','anchorReviewCoordinates','anchorReviewDisplay','anchorReviewOutputSettings','anchorReviewDownloadSettings','anchorReviewActions','anchorReviewCoordinateCommands','anchorReviewHistory','anchorReviewSaveCoordinates','anchorReviewPlayback','anchorReviewSeekFrame','anchorReviewResetTarget'];
async function mountNativeAnchorReview(currentContainerElement,currentPageLocation){
 currentAnchorDisposer?.();
 const currentLifecycleController=new AbortController();
 const currentScheduledFrames=new Set();
 let currentRuntimeDisposed=false,currentRuntimeWindow=null,currentRemovalObserver=null;
 const currentEditorRoot=document.createElement('section');currentEditorRoot.setAttribute('aria-label','등록 애니메이션 앵커 검수');
 currentContainerElement.replaceChildren(currentEditorRoot);
 const disposeAnchorRuntime=()=>{
  if(currentRuntimeDisposed)return;
  currentRuntimeDisposed=true;currentLifecycleController.abort();
  for(const currentFrameHandle of currentScheduledFrames)cancelAnimationFrame(currentFrameHandle);
  currentScheduledFrames.clear();currentRemovalObserver?.disconnect();
  for(const currentHandlerName of currentAnchorHandlerNames)if(window[currentHandlerName]===currentRuntimeWindow?.[currentHandlerName])delete window[currentHandlerName];
 };
 currentAnchorDisposer=disposeAnchorRuntime;
 currentRemovalObserver=new MutationObserver(()=>{if(!currentEditorRoot.isConnected)disposeAnchorRuntime();});
 currentRemovalObserver.observe(document.body,{childList:true,subtree:true});
 try{
  const currentPageResponse=await fetch(currentPageLocation.href,{signal:currentLifecycleController.signal});
  if(!currentPageResponse.ok)throw Error('앵커 검수 데이터 조회 실패: '+currentPageResponse.status);
  const currentPageDocument=new DOMParser().parseFromString(await currentPageResponse.text(),'text/html');
  const currentPayloadBlocks=currentPageDocument.querySelectorAll('#anchor-review-data');
  if(currentPayloadBlocks.length!==1||currentPayloadBlocks[0].tagName!=='SCRIPT'||currentPayloadBlocks[0].type!=='application/json')throw Error('앵커 JSON 데이터가 없습니다. 검수 페이지를 다시 게시하세요.');
  if(currentRuntimeDisposed)return;
  currentEditorRoot.innerHTML=currentAnchorMarkup;
  const currentPayloadElement=document.createElement('script');currentPayloadElement.id='anchor-review-data';currentPayloadElement.type='application/json';currentPayloadElement.textContent=currentPayloadBlocks[0].textContent;currentEditorRoot.append(currentPayloadElement);
  // 기능용 캔버스 배치만 지정한다. 설정·이력·확인은 바깥 Gradio를 사용한다.
  const currentCanvasStage=currentEditorRoot.querySelector('.anchor-stage');currentCanvasStage.style.position='relative';
  const currentReviewCanvas=currentEditorRoot.querySelector('#reviewCanvas');currentReviewCanvas.style.width='100%';currentReviewCanvas.style.height='auto';currentReviewCanvas.style.display='block';
  const currentRigContainer=currentEditorRoot.querySelector('.rig-mini-map');Object.assign(currentRigContainer.style,{position:'absolute',left:'0',top:'0',width:'120px',height:'120px'});
  const currentRigCanvas=currentRigContainer.querySelector('canvas');currentRigCanvas.style.width='100%';currentRigCanvas.style.height='100%';
  const currentScopedDocument={body:currentEditorRoot,querySelector:currentSelectorText=>currentEditorRoot.querySelector(currentSelectorText==='body>header'?'header':currentSelectorText),querySelectorAll:currentSelectorText=>currentEditorRoot.querySelectorAll(currentSelectorText),createElement:currentTagName=>document.createElement(currentTagName),dispatchEvent:currentEventObject=>currentEditorRoot.dispatchEvent(currentEventObject),addEventListener:(currentEventName,currentEventHandler)=>currentEditorRoot.addEventListener(currentEventName,currentEventHandler,{signal:currentLifecycleController.signal})};
  const currentLocationAdapter={href:currentPageLocation.href,search:currentPageLocation.search,protocol:currentPageLocation.protocol,replace:currentNextAddress=>{
   const currentNextLocation=new URL(currentNextAddress,currentPageLocation);
   const currentPublicLocation=new URL(window.location.href);currentPublicLocation.searchParams.set('action',currentNextLocation.searchParams.get('action'));
   window.history.replaceState(window.history.state,'',currentPublicLocation.href);
   void mountNativeAnchorReview(currentContainerElement,currentNextLocation);
  }};
  currentRuntimeWindow={anchorReviewNativeMode:true,location:currentLocationAdapter,resolveStaticReviewAssetUrl:currentAssetPath=>new URL(currentAssetPath,currentPageLocation).href,addEventListener:(currentEventName,currentEventHandler)=>window.addEventListener(currentEventName,currentEventHandler,{signal:currentLifecycleController.signal})};
  const scheduleAnchorFrame=currentFrameCallback=>{
   if(currentRuntimeDisposed||!currentEditorRoot.isConnected)return 0;
   const currentFrameHandle=requestAnimationFrame(currentFrameTime=>{currentScheduledFrames.delete(currentFrameHandle);if(!currentRuntimeDisposed&&currentEditorRoot.isConnected)currentFrameCallback(currentFrameTime);});currentScheduledFrames.add(currentFrameHandle);return currentFrameHandle;
  };
  const sendAnchorCommand=(currentRequestPath,currentRequestOptions)=>{
   if(currentRuntimeDisposed)return Promise.reject(Error('검수 동작이 변경되었습니다. 다시 조회하세요.'));
   return fetch(new URL(currentRequestPath,currentPageLocation),{...currentRequestOptions,signal:currentLifecycleController.signal});
  };
  createNativeAnchorRuntime(currentScopedDocument,currentRuntimeWindow,scheduleAnchorFrame,sendAnchorCommand);
  for(const currentHandlerName of currentAnchorHandlerNames)window[currentHandlerName]=currentRuntimeWindow[currentHandlerName];
  currentContainerElement.setAttribute('aria-busy','false');
 }catch(currentLoadError){
  if(currentRuntimeDisposed)return;
  disposeAnchorRuntime();currentEditorRoot.replaceChildren();const currentErrorElement=document.createElement('p');currentErrorElement.setAttribute('role','alert');currentErrorElement.textContent=currentLoadError.message;currentEditorRoot.append(currentErrorElement);currentContainerElement.setAttribute('aria-busy','false');
 }
}
