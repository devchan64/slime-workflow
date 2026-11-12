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

// 겹쳐보기는 직전 프레임을 동일 앵커 위치로 추가하고 입력 좌표는 수정하지 않는다.
const currentOriginalRows=JSON.stringify(currentFrameRows);
currentImageCalls=[];
renderCurrentPreview('image',currentFrameRows,2,false,false,'크롭',null,12,true,true);
currentAssertModule.strictEqual(currentImageCalls.length,2);
const currentCurrentDraw=currentImageCalls[0],currentPreviousDraw=currentImageCalls[1];
currentAssertModule.strictEqual(currentCurrentDraw[5]+115*(currentCurrentDraw[7]/232),currentPreviousDraw[5]+115*(currentPreviousDraw[7]/232));
currentAssertModule.ok(Math.abs((currentCurrentDraw[6]+200*(currentCurrentDraw[8]/210))-(currentPreviousDraw[6]+327*(currentPreviousDraw[8]/330)))<1e-9);
currentAssertModule.strictEqual(JSON.stringify(currentFrameRows),currentOriginalRows);
currentImageCalls=[];
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,12,true,true);
currentAssertModule.strictEqual(currentImageCalls.length,1);
currentAssertModule.match(renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,0),/지원하지 않는/);
console.log('이전 프레임 공통 앵커·입력 불변·첫 프레임 처리 검증');

// 클립은 재생 순서만 제한한다. 원본 좌표 배열과 편집 프레임 번호는 보존한다.
const currentClipSource={animation:{frames:[{frameId:'a'},{frameId:'b'}],clips:[{clipId:'exit.left',loop:false,frames:[{frameId:'b'}]}]}};
currentImageCalls=[];
renderCurrentPreview('image',currentFrameRows,1,true,false,'크롭',null,6,false,false,'exit.left',currentClipSource);
currentAssertModule.strictEqual(currentImageCalls[0][2],330);
currentAssertModule.strictEqual(JSON.stringify(currentFrameRows),currentOriginalRows);
currentAssertModule.match(renderCurrentPreview('image',currentFrameRows,1,true,false,'크롭',null,6,false,false,'missing',currentClipSource),/다시 확인/);
console.log('클립 재생 범위와 원본 좌표 보존 검증');

// 게임 크기는 크롭 높이 변화와 무관하게 지정된 신체 높이 비율을 유지한다.
currentImageCalls=[];
for(let currentFrameIndex=1;currentFrameIndex<=2;currentFrameIndex++)renderCurrentPreview('image',currentFrameRows,currentFrameIndex,false,false,'크롭',null,6,false,false,'',{},true,400,80);
currentAssertModule.strictEqual(currentImageCalls[0][7]/232,.2);
currentAssertModule.strictEqual(currentImageCalls[1][7]/232,.2);
currentAssertModule.match(renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,false,'',{},true,null,80),/양수/);
console.log('게임 출력 공통 배율과 누락 값 거절 검증');

currentAssertModule.strictEqual(currentCanvasElement.spriteEditorState.displayedIndex,1);

// 동작의 첫 프레임에는 다른 동작의 직전 시트 프레임을 겹치지 않는다.
currentImageCalls=[];
renderCurrentPreview('image',currentFrameRows,2,false,false,'크롭',null,6,false,true,'exit.left',currentClipSource);
currentAssertModule.strictEqual(currentImageCalls.length,1);
const currentReverseSource={animation:{frames:[{frameId:'a'},{frameId:'b'}],clips:[{clipId:'reverse',loop:false,frames:[{frameId:'b'},{frameId:'a'}]}]}};
currentImageCalls=[];
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,true,'reverse',currentReverseSource);
currentAssertModule.strictEqual(currentImageCalls.length,2);
currentAssertModule.strictEqual(currentImageCalls[1][2],330);
console.log('동작별 이전 프레임 순서와 경계 검증');
const selectCurrentClip=eval(currentFileSystem.readFileSync('tools/review/ui/gradio/sprite_sheet_clip_select.js','utf8'));
currentAssertModule.deepStrictEqual(selectCurrentClip('exit.left',currentClipSource,1),[false,2]);
currentAssertModule.deepStrictEqual(selectCurrentClip('',currentClipSource,2),[false,1]);
currentAssertModule.deepStrictEqual(selectCurrentClip('missing',currentClipSource,2),[false,2]);
console.log('동작 선택 시 정지와 첫 원본 프레임 이동 검증');

// 발 좌표는 원본 셀 기준으로 변환하며 앵커를 발로 추정하지 않는다.
currentAnchorCalls=[];
const currentFootSource={animation:{frames:[{rect:{x:0,y:0},contacts:[{x:90,y:320},{x:140,y:320}]}]}};
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,false,'',currentFootSource,false,480,80,true);
currentAssertModule.strictEqual(currentAnchorCalls.length,3);
currentAssertModule.strictEqual(currentAnchorCalls[0][2],5);
currentAssertModule.strictEqual(currentAnchorCalls[1][2],5);
currentAssertModule.ok(currentAnchorCalls[0][0]<currentAnchorCalls[2][0]);
currentAssertModule.ok(currentAnchorCalls[1][0]>currentAnchorCalls[2][0]);
currentAnchorCalls=[];
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,false,'',{},false,480,80,true);
currentAssertModule.strictEqual(currentAnchorCalls.length,1);
console.log('등록 발 중심 표시 및 미등록 시 임의 좌표 생성 방지 검증');

// 80px 가이드는 게임 배율을 원본 좌표에 환산하며, 기준 높이가 없으면 선을 그리지 않는다.
let currentGuideMoves=[],currentGuideLabels=[];
currentCanvasContext.moveTo=(...currentArguments)=>currentGuideMoves.push(currentArguments);
currentCanvasContext.lineTo=()=>{};
currentCanvasContext.fillText=(...currentArguments)=>currentGuideLabels.push(currentArguments[0]);
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,false,'',{},true,400,80,false,{},true);
currentAssertModule.ok(currentGuideLabels.includes('게임 80px · 앵커 기준'));
currentAssertModule.ok(currentGuideMoves.some(currentPoint=>currentPoint[0]===32));
currentGuideMoves=[];currentGuideLabels=[];
renderCurrentPreview('image',currentFrameRows,1,false,false,'크롭',null,6,false,false,'',{},false,null,null,false,{},true);
currentAssertModule.ok(currentGuideLabels.some(currentLabel=>currentLabel.includes('원본 신체 높이와 게임 출력 높이')));
currentAssertModule.ok(!currentGuideMoves.some(currentPoint=>currentPoint[0]===32));
currentAssertModule.strictEqual(JSON.stringify(currentFrameRows),currentOriginalRows);
console.log('80px 가이드 표시·기준 누락 안내·좌표 불변 검증');
