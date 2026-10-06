import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// 실제 결과 파일을 수정하지 않고 브라우저 재생 명령과 합성 좌표 계약을 검증한다.
async function createSeparationHarness(currentFrameCount) {
 const currentElementRecords=new Map();
 const currentDrawRecords=[];
 const currentAnimationCallbacks=[];
 const createCanvasElement=()=>({width:0,height:0,getContext:()=>({drawImage:(...currentDrawArguments)=>currentDrawRecords.push(currentDrawArguments)})});
 for(const currentElementName of ['source','base','outfit','combined'])currentElementRecords.set(currentElementName,createCanvasElement());
 for(const currentElementName of ['status','frame','play','playback-controls','single-frame-note','outfit-x','outfit-y','outfit-scale','reset-alignment','base-download','outfit-download','archive-download'])currentElementRecords.set(currentElementName,{value:currentElementName==='outfit-scale'?'1':'0',textContent:'',hidden:false});
 const currentManifestRecord={schema_version:2,size:16,fps:8,frames:Array.from({length:currentFrameCount},(_,currentFrameIndex)=>({column:currentFrameIndex,row:0,source:{frameId:'frame.'+currentFrameIndex}}))};
 const currentWindowObject={parent:{},addEventListener:()=>{}};
 const currentContextObject=vm.createContext({window:currentWindowObject,document:{hidden:false,getElementById:currentElementName=>currentElementRecords.get(currentElementName),querySelectorAll:()=>[],querySelector:()=>({}),createElement:createCanvasElement},fetch:async()=>({ok:true,json:async()=>currentManifestRecord}),Image:class {set src(currentImagePath){queueMicrotask(()=>this.onload());}},ResizeObserver:class {observe(){} disconnect(){}},requestAnimationFrame:currentCallbackFunction=>currentAnimationCallbacks.push(currentCallbackFunction),console});
 vm.runInContext(readFileSync(new URL('../ui/shared/transform-joypad.js',import.meta.url),'utf8'),currentContextObject);
 currentWindowObject.parent.calculateJoypadTransforms=currentWindowObject.calculateJoypadTransforms;
 const currentHtmlSource=readFileSync(new URL('../ui/character_animation/separation-preview.html',import.meta.url),'utf8');
 vm.runInContext(currentHtmlSource.split('<script>')[1].split('</script>')[0].replace('__RESULT_BASE__',JSON.stringify('/fixture/')),currentContextObject);
 await new Promise(currentResolveFunction=>setImmediate(currentResolveFunction));
 return {currentWindowObject,currentElementRecords,currentDrawRecords,currentAnimationCallbacks};
}

test('다중 프레임 이동·재생·정지는 같은 합성 프레임을 사용한다',async()=>{
 const {currentWindowObject,currentElementRecords,currentAnimationCallbacks,currentDrawRecords}=await createSeparationHarness(3);
 assert.match(currentWindowObject.separationReviewPlayback('next'),/2\/3/);
 assert.match(currentWindowObject.separationReviewPlayback('prev'),/1\/3/);
 assert.match(currentWindowObject.separationReviewSeek(3),/frame.2/);
 assert.throws(()=>currentWindowObject.separationReviewSeek(4),/범위/);
 currentWindowObject.separationReviewPlayback('play');
 currentAnimationCallbacks.shift()(1000);
 assert.match(currentElementRecords.get('status').textContent,/frame.0/);
 currentWindowObject.separationReviewPlayback('stop');
 currentAnimationCallbacks.shift()(2000);
 assert.match(currentElementRecords.get('status').textContent,/frame.0/);
 assert.ok(currentDrawRecords.some(currentDrawArguments=>currentDrawArguments[1]===32));
});

test('단일 프레임 재생 거절 및 조이패드·초기화',async()=>{
 const {currentWindowObject,currentElementRecords}=await createSeparationHarness(1);
 assert.throws(()=>currentWindowObject.separationReviewPlayback('play'),/단일 프레임/);
 const currentMovedRecord=currentWindowObject.separationReviewTransform('right',{positionStep:1});
 assert.equal(currentMovedRecord.x,1);
 const currentScaledRecord=currentWindowObject.separationReviewTransform('scale-up',{scaleStep:.01});
 assert.equal(currentScaledRecord.scale,1.01);
 currentWindowObject.separationReviewTransform('reset',{});
 assert.equal(Number(currentElementRecords.get('outfit-x').value),0);
 assert.equal(Number(currentElementRecords.get('outfit-scale').value),1);
 assert.throws(()=>currentWindowObject.separationReviewTransform('set-scale',{scale:0}),/허용 범위/);
});
