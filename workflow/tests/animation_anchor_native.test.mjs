import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const currentLoaderSource=fs.readFileSync(new URL('../ui/shared/animation-anchor-editor/native-loader.js',import.meta.url),'utf8');

function createNativeFixtureHarness(){
 const currentRuntimeRecords=[],currentObserverRecords=[],currentRequestRecords=[];
 const currentFrameCallbacks=new Map(),currentCancelledFrames=[];
 const currentContainerElement={children:[],setAttribute(){},replaceChildren(...currentChildNodes){for(const currentChildNode of this.children)currentChildNode.isConnected=false;this.children=currentChildNodes;}};
 function createFixtureElement(currentElementTag){
  const currentNodeRecord={tagName:currentElementTag,style:{},isConnected:true,children:[],setAttribute(){},append(currentChildNode){this.children.push(currentChildNode);},replaceChildren(){this.children=[];},addEventListener(){},dispatchEvent(){}};
  currentNodeRecord.querySelector=()=>createFixtureElement('canvas');currentNodeRecord.querySelectorAll=()=>[];
  return currentNodeRecord;
 }
 const currentWindowAdapter={location:{href:'http://gui.test/?review=anchor'},history:{state:null,replaceState(currentStateRecord,currentTitleText,currentAddressText){currentWindowAdapter.location.href=currentAddressText;}},addEventListener(){}};
 const currentContextRecord={URL,AbortController,Set,Error,console,window:currentWindowAdapter,
  document:{body:{},createElement:createFixtureElement},
  MutationObserver:class{constructor(currentCallbackValue){this.callback=currentCallbackValue;currentObserverRecords.push(this);}observe(){}disconnect(){this.disconnected=true;}},
  DOMParser:class{parseFromString(currentBodyText){return {querySelectorAll:()=>currentBodyText==='invalid'?[]:[{tagName:'SCRIPT',type:'application/json',textContent:'{"schemaVersion":1}'}]};}},
  requestAnimationFrame(currentCallbackValue){const currentFrameHandle=currentFrameCallbacks.size+1;currentFrameCallbacks.set(currentFrameHandle,currentCallbackValue);return currentFrameHandle;},
  cancelAnimationFrame(currentFrameHandle){currentCancelledFrames.push(currentFrameHandle);},
  fetch(currentRequestAddress,currentRequestOptions){return new Promise(currentResolveResponse=>currentRequestRecords.push({address:String(currentRequestAddress),options:currentRequestOptions,resolve:currentResolveResponse}));},
  currentAnchorMarkup:'<main>신뢰된 공용 마크업</main>',
  createNativeAnchorRuntime(currentScopedDocument,currentScopedWindow,currentScheduleFrame,currentSendCommand){
   currentScopedWindow.anchorReviewPlayback=()=>currentScopedWindow.location.href;
   currentRuntimeRecords.push({document:currentScopedDocument,window:currentScopedWindow,schedule:currentScheduleFrame,send:currentSendCommand});
  },
 };
 vm.createContext(currentContextRecord);vm.runInContext(currentLoaderSource,currentContextRecord);
 return {context:currentContextRecord,container:currentContainerElement,runtimes:currentRuntimeRecords,observers:currentObserverRecords,requests:currentRequestRecords,frames:currentFrameCallbacks,cancelled:currentCancelledFrames,
  mount:currentAddressText=>currentContextRecord.mountNativeAnchorReview(currentContainerElement,new URL(currentAddressText)),
  respond(currentRequestIndex,currentBodyText='valid'){currentRequestRecords[currentRequestIndex].resolve({ok:true,text:async()=>currentBodyText});},
 };
}

test('동작 전환은 이전 요청과 재생을 정리하고 외부 문서 대신 공용 DOM만 사용한다',async()=>{
 const currentFixtureHarness=createNativeFixtureHarness();
 const currentFirstMount=currentFixtureHarness.mount('http://review.test/animation/anchors.html');currentFixtureHarness.respond(0);await currentFirstMount;
 const currentFirstRuntime=currentFixtureHarness.runtimes[0];
 assert.equal(currentFirstRuntime.document.body,currentFixtureHarness.container.children[0]);
 assert.equal(currentFirstRuntime.document.body.innerHTML,currentFixtureHarness.context.currentAnchorMarkup);
 assert.equal(currentFirstRuntime.window.resolveStaticReviewAssetUrl('sheet.png'),'http://review.test/animation/sheet.png');
 let currentFrameInvoked=false;const currentFrameHandle=currentFirstRuntime.schedule(()=>{currentFrameInvoked=true;});
 const currentSecondMount=currentFixtureHarness.mount('http://review.test/animation/anchors.html?action=walk');
 assert.equal(currentFixtureHarness.requests[0].options.signal.aborted,true);
 assert.deepEqual(currentFixtureHarness.cancelled,[currentFrameHandle]);
 currentFixtureHarness.frames.get(currentFrameHandle)(1);assert.equal(currentFrameInvoked,false);
 await assert.rejects(currentFirstRuntime.send('/management/command'),/변경/);
 currentFixtureHarness.respond(1);await currentSecondMount;
 assert.equal(currentFixtureHarness.runtimes.length,2);
 assert.equal(currentFixtureHarness.context.window.anchorReviewPlayback(), 'http://review.test/animation/anchors.html?action=walk');
 currentFixtureHarness.container.children[0].isConnected=false;currentFixtureHarness.observers[1].callback();
 assert.equal(currentFixtureHarness.context.window.anchorReviewPlayback,undefined);
 assert.equal(currentFixtureHarness.observers[1].disconnected,true);
});

test('늦은 이전 응답은 새 동작을 덮어쓰지 않는다',async()=>{
 const currentFixtureHarness=createNativeFixtureHarness();
 const currentFirstMount=currentFixtureHarness.mount('http://review.test/anchors.html?action=idle');
 const currentSecondMount=currentFixtureHarness.mount('http://review.test/anchors.html?action=walk');
 currentFixtureHarness.respond(1);await currentSecondMount;currentFixtureHarness.respond(0);await currentFirstMount;
 assert.equal(currentFixtureHarness.runtimes.length,1);
 assert.match(currentFixtureHarness.context.window.anchorReviewPlayback(),/walk/);
});

test('잘못된 게시 형식은 실패하고 iframe으로 우회하지 않는다',async()=>{
 const currentFixtureHarness=createNativeFixtureHarness();
 const currentMountPromise=currentFixtureHarness.mount('http://review.test/anchors.html');currentFixtureHarness.respond(0,'invalid');await currentMountPromise;
 assert.equal(currentFixtureHarness.runtimes.length,0);
 assert.match(currentFixtureHarness.container.children[0].children[0].textContent,/다시 게시/);
 assert.equal(currentFixtureHarness.requests[0].options.signal.aborted,true);
});

test('동작 이동은 외곽 검수 URL을 보존한다',async()=>{
 const currentFixtureHarness=createNativeFixtureHarness();
 const currentMountPromise=currentFixtureHarness.mount('http://review.test/anchors.html');currentFixtureHarness.respond(0);await currentMountPromise;
 currentFixtureHarness.runtimes[0].window.location.replace('?action=walk');
 const currentAddressValue=new URL(currentFixtureHarness.context.window.location.href);
 assert.equal(currentAddressValue.searchParams.get('review'),'anchor');assert.equal(currentAddressValue.searchParams.get('action'),'walk');
 currentFixtureHarness.respond(1);
});
