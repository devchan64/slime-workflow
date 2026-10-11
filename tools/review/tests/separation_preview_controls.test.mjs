import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const currentPlayerSource=readFileSync(new URL('../ui/shared/separation-player.js',import.meta.url),'utf8');
const currentJoypadSource=readFileSync(new URL('../ui/shared/transform-joypad.js',import.meta.url),'utf8');
const settlePreviewPromises=()=>new Promise(currentResolveFunction=>setImmediate(currentResolveFunction));

async function createSeparationHarness(currentFrameCount,currentWindowObject={},currentPlayerIdentifier='fixturePlayer',currentFetchHandler=null){
 const currentDrawRecords=[],currentTimerCallbacks=new Map(),currentObserverCallbacks=[];
 const createPreviewElement=()=>({dataset:{},style:{},children:[],hidden:false,textContent:'',append(...currentChildElements){this.children.push(...currentChildElements);},replaceChildren(){this.children=[];},setAttribute(){},getContext:()=>({drawImage:(...currentDrawArguments)=>currentDrawRecords.push(currentDrawArguments)})});
 const currentImageContainer=createPreviewElement(),currentStatusElement=createPreviewElement();
 const currentRootElement={isConnected:true,querySelector:currentSelectorText=>currentSelectorText==='[data-player-status]'?currentStatusElement:currentSelectorText==='[data-player-images]'?currentImageContainer:currentImageContainer.children.flatMap(currentPanelElement=>currentPanelElement.children).find(currentCanvasElement=>currentSelectorText===`[data-canvas-part="${currentCanvasElement.dataset.canvasPart}"]`),querySelectorAll:()=>currentImageContainer.children};
 const currentManifestRecord={schema_version:2,size:16,fps:8,frames:Array.from({length:currentFrameCount},(_,currentFrameIndex)=>({column:currentFrameIndex,row:0,source:{frameId:'frame.'+currentFrameIndex}}))};
 let currentValueWatcher,currentTimerSequence=0;
 const currentPropsRecord={value:JSON.stringify({base:'/fixture/'})};
 const currentContextObject=vm.createContext({window:currentWindowObject,element:currentRootElement,props:currentPropsRecord,currentPlayerIdentifier,watch:(_,currentCallbackFunction)=>{currentValueWatcher=currentCallbackFunction;},document:{body:{},hidden:false,createElement:createPreviewElement},fetch:currentFetchHandler||(async()=>({ok:true,json:async()=>currentManifestRecord})),AbortController,Image:class {naturalWidth=64;naturalHeight=16;set src(currentImagePath){queueMicrotask(()=>this.onload());}},MutationObserver:class {constructor(currentCallbackFunction){currentObserverCallbacks.push(currentCallbackFunction);}observe(){} disconnect(){}},setInterval:currentCallbackFunction=>{currentTimerCallbacks.set(++currentTimerSequence,currentCallbackFunction);return currentTimerSequence;},clearInterval:currentTimerIdentifier=>currentTimerCallbacks.delete(currentTimerIdentifier),console});
 vm.runInContext(currentJoypadSource,currentContextObject);vm.runInContext(currentPlayerSource,currentContextObject);
 await settlePreviewPromises();
 return {currentWindowObject,currentRootElement,currentImageContainer,currentStatusElement,currentDrawRecords,currentTimerCallbacks,currentObserverCallbacks,currentPropsRecord,currentManifestRecord,reloadPreviewValue:()=>currentValueWatcher()};
}

test('다중 프레임 이동·재생·정지는 같은 합성 프레임을 사용한다',async()=>{
 const currentHarnessRecord=await createSeparationHarness(3);
 const {currentWindowObject,currentStatusElement,currentTimerCallbacks,currentDrawRecords}=currentHarnessRecord;
 assert.match(currentWindowObject.fixturePlayerPlayback('next'),/2\/3/);
 assert.match(currentWindowObject.fixturePlayerPlayback('prev'),/1\/3/);
 assert.match(currentWindowObject.fixturePlayerSeek(3),/frame.2/);
 assert.throws(()=>currentWindowObject.fixturePlayerSeek(4),/범위/);
 currentWindowObject.fixturePlayerPlayback('play');
 [...currentTimerCallbacks.values()][0]();assert.match(currentStatusElement.textContent,/frame.0/);
 currentWindowObject.fixturePlayerPlayback('stop');assert.equal(currentTimerCallbacks.size,0);
 assert.ok(currentDrawRecords.some(currentDrawArguments=>currentDrawArguments[1]===32));
});

test('단일 프레임 재생 거절 및 조이패드·초기화',async()=>{
 const {currentWindowObject}=await createSeparationHarness(1);
 assert.throws(()=>currentWindowObject.fixturePlayerPlayback('play'),/단일 프레임/);
 assert.equal(currentWindowObject.fixturePlayerTransform('right',{positionStep:1}).x,1);
 assert.equal(currentWindowObject.fixturePlayerTransform('scale-up',{scaleStep:.01}).scale,1.01);
 assert.equal(currentWindowObject.fixturePlayerTransform('reset',{}).x,0);
 assert.throws(()=>currentWindowObject.fixturePlayerTransform('set-scale',{scale:0}),/허용 범위/);
});

test('결과 탭과 이력의 보기·합성·재생 상태는 독립적이다',async()=>{
 const currentSharedWindow={};
 const currentResultPlayer=await createSeparationHarness(3,currentSharedWindow,'resultPlayer');
 const currentHistoryPlayer=await createSeparationHarness(3,currentSharedWindow,'historyPlayer');
 currentSharedWindow.historyPlayerView('parts');currentSharedWindow.historyPlayerSeek(3);
 assert.deepEqual(currentHistoryPlayer.currentImageContainer.children.filter(currentPanelElement=>!currentPanelElement.hidden).map(currentPanelElement=>currentPanelElement.dataset.reviewPart),['base','outfit']);
 assert.match(currentResultPlayer.currentStatusElement.textContent,/1\/3/);
 currentSharedWindow.resultPlayerPlayback('play');
 currentResultPlayer.currentRootElement.isConnected=false;currentResultPlayer.currentObserverCallbacks[0]();
 assert.equal(currentResultPlayer.currentTimerCallbacks.size,0);assert.equal(currentSharedWindow.resultPlayerPlayback,undefined);
 assert.match(currentSharedWindow.historyPlayerPlayback('prev'),/2\/3/);
});

test('결과 변경은 이전 응답·재생을 폐기하고 실패 뒤 오래된 결과를 조작할 수 없다',async()=>{
 let releaseManifestResponse,currentFetchSequence=0;
 const currentPendingResponse=new Promise(currentResolveFunction=>{releaseManifestResponse=currentResolveFunction;});
 const currentManifestValue={schema_version:2,size:16,fps:8,frames:[{column:0,row:0,source:{frameId:'old'}}]};
 const currentHarnessRecord=await createSeparationHarness(1,{},'fixturePlayer',async()=>++currentFetchSequence===1?currentPendingResponse:{ok:false});
 currentHarnessRecord.currentPropsRecord.value=JSON.stringify({base:'/new/'});await currentHarnessRecord.reloadPreviewValue();
 releaseManifestResponse({ok:true,json:async()=>currentManifestValue});await settlePreviewPromises();
 assert.match(currentHarnessRecord.currentStatusElement.textContent,/결과 오류/);
 assert.equal(currentHarnessRecord.currentImageContainer.children.length,0);
 assert.throws(()=>currentHarnessRecord.currentWindowObject.fixturePlayerSeek(1),/먼저 조회/);
});

test('빈 결과 및 잘못된 프레임 메타데이터는 명시적으로 거절한다',async()=>{
 const currentHarnessRecord=await createSeparationHarness(0);
 assert.match(currentHarnessRecord.currentStatusElement.textContent,/형식 오류/);
 currentHarnessRecord.currentPropsRecord.value='';await currentHarnessRecord.reloadPreviewValue();
 assert.match(currentHarnessRecord.currentStatusElement.textContent,/완료된 결과를 조회/);
});
