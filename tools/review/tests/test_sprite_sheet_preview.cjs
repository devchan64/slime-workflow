const currentFileSystem=require('fs'),currentAssertModule=require('assert');
const renderCurrentPreview=eval(currentFileSystem.readFileSync('tools/review/ui/gradio/sprite_sheet_editor_preview.js','utf8'));
const currentFrameRows=[[0,0,232,330,115,327],[0,330,232,210,115,200]];
let currentAnchorCalls=[],currentImageCalls=[];
const currentCanvasContext=new Proxy({arc:(...currentCallArguments)=>currentAnchorCalls.push(currentCallArguments),drawImage:(...currentCallArguments)=>currentImageCalls.push(currentCallArguments)},{get:(currentTargetObject,currentPropertyName)=>currentTargetObject[currentPropertyName]||(()=>{})});
const currentCanvasElement={getContext:()=>currentCanvasContext,isConnected:true};
global.document={getElementById:()=>currentCanvasElement};global.Image=class{width=928;height=1695;set src(currentImageSource){this.onload()}};global.requestAnimationFrame=()=>{};
for(let currentFrameIndex=1;currentFrameIndex<=2;currentFrameIndex++)renderCurrentPreview('image',currentFrameRows,currentFrameIndex,false,false,'크롭',null);
renderCurrentPreview('image',currentFrameRows,1,true,false,'크롭',null);
currentAssertModule.deepStrictEqual(currentAnchorCalls[0],currentAnchorCalls[1]);currentAssertModule.deepStrictEqual(currentAnchorCalls[0],currentAnchorCalls[2]);
currentAssertModule.strictEqual(currentImageCalls[0][7]/232,currentImageCalls[1][7]/232);
console.log('수동 이동·재생 앵커와 배율 일치 확인');

// 같은 화면 갱신 주기의 RAF 시간이 초기 performance.now보다 앞서도 첫 프레임을 유지한다.
let currentAnimationCallback;
global.requestAnimationFrame=currentFrameCallback=>{currentAnimationCallback=currentFrameCallback};
renderCurrentPreview('image',currentFrameRows,1,true,false,'크롭',null);
currentAssertModule.doesNotThrow(()=>currentAnimationCallback(0));
console.log('첫 RAF 시간차 음수 경계 검증');
