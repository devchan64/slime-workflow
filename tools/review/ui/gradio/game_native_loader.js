async function mountNativeGameReview(currentReviewRoot,currentPageLocation){
  const currentRequestController=new AbortController();
  let currentMountedController=null;
  let currentReviewDisposed=false;
  let currentBattlefieldBridge=null;
  const currentConnectionObserver=new MutationObserver(()=>{
    if(!currentReviewRoot.isConnected)disposeNativeGameReview();
  });
  function disposeNativeGameReview(){
    if(currentReviewDisposed)return;
    currentReviewDisposed=true;
    currentRequestController.abort();
    currentConnectionObserver.disconnect();
    window.removeEventListener('pagehide',disposeNativeGameReview);
    currentMountedController?.dispose();
    if(window.battlefieldReviewControls===currentBattlefieldBridge){delete window.battlefieldReviewControls;delete window.battlefieldChoiceSignature;}
  }
  currentConnectionObserver.observe(document.body,{childList:true,subtree:true});
  window.addEventListener('pagehide',disposeNativeGameReview);
  try{
    if(!/\/ui-[a-f0-9]{16}\/review\/(design-system|battlefield-preview)\.html$/.test(currentPageLocation.pathname))throw Error('등록된 게임 검수 번들 경로가 아닙니다.');
    const currentBundleLocation=new URL('../',currentPageLocation);
    const currentManifestResponse=await fetch(new URL('manifest.json',currentBundleLocation),{signal:currentRequestController.signal});
    if(!currentManifestResponse.ok)throw Error(`검수 manifest 조회 실패: ${currentManifestResponse.status}`);
    const currentManifestRecord=await currentManifestResponse.json();
    if(currentManifestRecord.schemaVersion!==2||currentManifestRecord.kind!=='slime-ui-review'||!Array.isArray(currentManifestRecord.pages)||!Array.isArray(currentManifestRecord.files))throw Error('직접 마운트 가능한 검수 번들 v2로 재게시하세요.');
    const currentPageRecord=currentManifestRecord.pages.find(currentPageRecord=>new URL(currentPageRecord.path,currentBundleLocation).pathname===currentPageLocation.pathname);
    const currentModulePath=currentManifestRecord.componentModules?.[currentPageRecord?.id];
    if(typeof currentModulePath!=='string'||!/^assets\/[a-zA-Z0-9_-]+\.js$/.test(currentModulePath)||!currentManifestRecord.files.some(currentFileRecord=>currentFileRecord.path===currentModulePath&&/^[a-f0-9]{64}$/.test(currentFileRecord.sha256)))throw Error('검증된 검수 컴포넌트 모듈이 없습니다.');
    if(currentReviewDisposed||!currentReviewRoot.isConnected)return;
    const currentComponentModule=await import(new URL(currentModulePath,currentBundleLocation).href);
    if(currentReviewDisposed||!currentReviewRoot.isConnected)return;
    if(typeof currentComponentModule.mountReviewPage!=='function')throw Error('검수 컴포넌트 마운트 계약이 없습니다.');
    const currentReviewHost=document.createElement('section');
    const currentBattlefieldPage=currentPageLocation.pathname.endsWith('/battlefield-preview.html');
    currentReviewHost.setAttribute('aria-label',currentBattlefieldPage?'게임 전장 검수':'게임 디자인 시스템');
    currentReviewRoot.replaceChildren(currentReviewHost);
    currentMountedController=currentComponentModule.mountReviewPage(currentReviewHost,{locale:currentPageLocation.searchParams.get('locale')??'ko',field:currentPageLocation.searchParams.get('field')??'all',overview:currentPageLocation.searchParams.has('overview')});
    if(typeof currentMountedController?.dispose!=='function')throw Error('검수 컴포넌트 해제 계약이 없습니다.');
    if(currentBattlefieldPage){
      if(typeof currentMountedController.readState!=='function'||typeof currentMountedController.selectField!=='function')throw Error('전장 선택·상태 계약이 없습니다.');
      currentBattlefieldBridge=currentSelectedField=>{
        if(currentReviewDisposed)throw Error('해제된 전장 검수 화면입니다.');
        if(currentSelectedField!==null){
          currentMountedController.selectField(currentSelectedField);
          const currentBrowserLocation=new URL(window.location.href);currentBrowserLocation.searchParams.set('field',currentSelectedField);
          window.history.replaceState(null,'',currentBrowserLocation);
        }
        const currentBattlefieldState=currentMountedController.readState();
        return [{__type__:'update',choices:currentBattlefieldState.choices,value:currentBattlefieldState.field},currentBattlefieldState.status];
      };
      const currentInitialSelection=currentMountedController.readState().field;
      if(currentPageLocation.searchParams.get('field')==='all'&&currentInitialSelection!=='all'){
        const currentBrowserLocation=new URL(window.location.href);
        currentBrowserLocation.searchParams.set('field',currentInitialSelection);
        window.history.replaceState(null,'',currentBrowserLocation);
      }
      window.battlefieldReviewControls=currentBattlefieldBridge;
      delete window.battlefieldChoiceSignature;
    }
    currentReviewRoot.setAttribute('aria-busy','false');
  }catch(currentReviewError){
    if(currentReviewDisposed)return;
    disposeNativeGameReview();
    const currentErrorMessage=document.createElement('p');
    currentErrorMessage.setAttribute('role','alert');
    currentErrorMessage.textContent=`게임 검수 로드 실패: ${currentReviewError.message}`;
    currentReviewRoot.replaceChildren(currentErrorMessage);
    currentReviewRoot.setAttribute('aria-busy','false');
  }
}
