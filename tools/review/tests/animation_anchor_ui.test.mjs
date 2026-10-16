import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const reviewHtmlContent=readFileSync(process.argv[2],'utf8');
let currentReviewPayloadText=reviewHtmlContent.split('<script id="anchor-review-data" type="application/json">')[1].split('</script>')[0];
const reviewScriptContent=reviewHtmlContent.split('<script>')[1].split('</script>')[0];
const elementLookupTable=new Map();
const canvasTraceOperations=[];
const mockCanvasContext=new Proxy({}, {get:(currentCanvasTarget,currentOperationName)=>(...currentOperationArguments)=>{canvasTraceOperations.push([currentOperationName,...currentOperationArguments]);}});
function selectMockElement(selectorQueryText){if(!elementLookupTable.has(selectorQueryText))elementLookupTable.set(selectorQueryText,{value:selectorQueryText==='#directionChoice'?'down_left':selectorQueryText==='#pointChoice'?'anchor':'0',textContent:'',innerHTML:'',checked:true,options:[],add(){},getContext:()=>mockCanvasContext});return elementLookupTable.get(selectorQueryText)}
const testDocumentEvents={},testWindowEvents={};
const fakeDocumentAdapter={body:{dataset:{}},dispatchEvent(){},addEventListener(eventNameValue,eventHandlerValue){testDocumentEvents[eventNameValue]=eventHandlerValue;},querySelector:selectMockElement,querySelectorAll:currentSelectorText=>currentSelectorText==='script#anchor-review-data[type="application/json"]'?[{textContent:currentReviewPayloadText}]:[],createElement:()=>({click(){}})};
const testExecutionContext=vm.createContext({document:fakeDocumentAdapter,window:{addEventListener(eventNameValue,eventHandlerValue){testWindowEvents[eventNameValue]=eventHandlerValue;}},CustomEvent:class{constructor(eventNameValue,eventDetailValue){this.type=eventNameValue;this.detail=eventDetailValue.detail;}},Image:class{set src(sourceImageLocation){if(this.onload)this.onload()}},requestAnimationFrame(){},performance:{now:()=>0},canvasTraceOperations,URL,URLSearchParams,structuredClone,sessionStorage:{getItem:()=>null,removeItem(){}},Blob,setTimeout});
vm.runInContext(reviewScriptContent,testExecutionContext);
await new Promise(currentResolveCallback=>setTimeout(currentResolveCallback,0));
vm.runInContext(`
if(document.body.dataset.coordinateDownloadPending!=='false')throw new Error('초기 상태 변경 감지 오류');
const originalFirstFrameCopy=JSON.stringify(reviewFrameRecords[0]);
const originalSecondAnchorX=reviewFrameRecords[1].anchor.x;
document.querySelector('#nextFrame').onclick();
if(frameChoiceElement.value!=='1'||animationPlaybackActive)throw new Error('다음 프레임은 일시정지해야 함');
moveSelectedPoint(1,0);
if(reviewFrameRecords[1].anchor.x!==originalSecondAnchorX+1)throw new Error('1px 이동 오류');
if(document.body.dataset.coordinateDownloadPending!=='true')throw new Error('변경 감지 누락');
document.querySelector('#undoCoordinateChange').onclick();
if(reviewFrameRecords[1].anchor.x!==originalSecondAnchorX||document.body.dataset.coordinateDownloadPending!=='false')throw new Error('실행 취소 또는 원본 복원 오류');
document.querySelector('#redoCoordinateChange').onclick();
if(reviewFrameRecords[1].anchor.x!==originalSecondAnchorX+1)throw new Error('다시 실행 오류');
const previousHistoryCount=coordinateUndoHistory.length;moveSelectedPoint(0,0);moveSelectedPoint(-99999,0);
if(coordinateUndoHistory.length!==previousHistoryCount)throw new Error('무효 편집 기록 생성');
document.querySelector('#resetCurrentFrame').onclick();
if(document.body.dataset.coordinateDownloadPending!=='false')throw new Error('현재 프레임 복원 오류');
document.querySelector('#undoCoordinateChange').onclick();
savedCoordinateSnapshotValue=JSON.stringify(reviewFrameRecords.map(copyFrameCoordinates));
refreshCoordinateStatus();
if(document.body.dataset.coordinateDownloadPending!=='false')throw new Error('저장 상태 오류');
document.querySelector('#undoCoordinateChange').onclick();
if(document.body.dataset.coordinateDownloadPending!=='true')throw new Error('저장 이후 변경 감지 누락');
document.querySelector('#redoCoordinateChange').onclick();
if(document.body.dataset.coordinateDownloadPending!=='false')throw new Error('저장 시점 복원 오류');
if(JSON.stringify(reviewFrameRecords[0])!==originalFirstFrameCopy)throw new Error('다른 프레임 변경');
document.querySelector('#previousFrame').onclick();
if(frameChoiceElement.value!=='0')throw new Error('이전 프레임 오류');
document.querySelector('#previousFrame').onclick();
if(frameChoiceElement.value!=='7')throw new Error('프레임 순환 오류');
const originalCoordinateExport=JSON.stringify(buildCoordinateArtifact());
previewTileWidthElement.value='320';
if(!updatePreviewGroundSize()||previewTileWidthValue!==320||previewTileHeightValue!==160)throw new Error('가상 타일 크기 적용 실패');
if(!gameOutputScaleToggleElement.checked||GAME_OUTPUT_TILE_WIDTH!==64||GAME_OUTPUT_TILE_HEIGHT!==32||GAME_OUTPUT_CHARACTER_HEIGHT!==60)throw new Error('게임 출력 비율 기준 누락');
const expectedGameOutputScale=(reviewSourceMetadata.runtimeScale.baseHeight*previewTileWidthValue/GAME_OUTPUT_TILE_WIDTH)/reviewSourceMetadata.runtimeScale.sourceHeight;
if(calculateCurrentSpriteScale({height:100})!==expectedGameOutputScale)throw new Error('게임 출력 비율 확대 오류');
gameOutputScaleToggleElement.checked=false;
if(calculateCurrentSpriteScale({height:100})!==1)throw new Error('원본 픽셀 비율 전환 오류');
gameOutputScaleToggleElement.checked=true;
canvasTraceOperations.length=0;drawPreviewGroundPlane();
const initialShadowOperation=canvasTraceOperations.find(currentOperationRecord=>currentOperationRecord[0]==='ellipse');
if(initialShadowOperation[3]!==80||initialShadowOperation[4]!==40)throw new Error('그림자 50% 비율 오류');
actorSizeChoiceElement.value='huge';
canvasTraceOperations.length=0;drawPreviewGroundPlane();
const hugeTileMoveOperations=canvasTraceOperations.filter(currentOperationRecord=>currentOperationRecord[0]==='moveTo');
if(hugeTileMoveOperations.length<4)throw new Error('초대형 2x2 타일 배치 누락');
actorSizeChoiceElement.value='medium';
previewTileWidthElement.value='600';updatePreviewGroundSize();
if(previewTileHeightValue!==300||calculatePreviewGroundHeight()+previewTileHeightValue/2>REVIEW_CANVAS_HEIGHT-PREVIEW_GROUND_BOTTOM_MARGIN)throw new Error('최대 타일 비율 또는 경계 오류');
canvasTraceOperations.length=0;drawPreviewGroundPlane();
const enlargedShadowOperation=canvasTraceOperations.find(currentOperationRecord=>currentOperationRecord[0]==='ellipse');
if(enlargedShadowOperation[3]!==150||enlargedShadowOperation[4]!==75)throw new Error('그림자 확대 비례 오류');
previewTileWidthElement.value='321';if(updatePreviewGroundSize())throw new Error('짝수가 아닌 너비 허용');
previewTileWidthElement.value='-1';
if(updatePreviewGroundSize()!==false||previewTileWidthValue!==600)throw new Error('잘못된 타일 크기 허용');
canvasTraceOperations.length=0;drawPreviewGroundPlane();
if(!canvasTraceOperations.some(currentOperationRecord=>currentOperationRecord[0]==='ellipse'))throw new Error('그림자 미표시');
document.querySelector('#shadowPreviewToggle').checked=false;
canvasTraceOperations.length=0;drawPreviewGroundPlane();
if(canvasTraceOperations.some(currentOperationRecord=>currentOperationRecord[0]==='ellipse'))throw new Error('그림자 숨김 실패');
if(JSON.stringify(buildCoordinateArtifact())!==originalCoordinateExport)throw new Error('표시 설정이 좌표 내보내기를 변경함');
const exportedArtifactValue=buildCoordinateArtifact();
if(exportedArtifactValue.frames.length!==32||!exportedArtifactValue.description||exportedArtifactValue.source.sheets.length!==4)throw new Error('내보내기 메타데이터 누락');
for(const frameRecordValue of exportedArtifactValue.frames)for(const pointRecordValue of [...frameRecordValue.points,frameRecordValue.anchor])if(!Number.isInteger(pointRecordValue.x)||!Number.isInteger(pointRecordValue.y))throw new Error('정수 좌표 아님');
`,testExecutionContext);
assert.equal(vm.runInContext('buildCoordinateArtifact().artifactType',testExecutionContext),'character-animation-anchor-review');
console.log('프레임 전환·1px 이동·다른 프레임 보존·정수 JSON 내보내기·가상 타일·그림자 검사 통과');
// 저장 응답 전 추가 편집은 저장 완료로 오인하지 않으며 중복 요청을 차단한다.
await vm.runInContext(`
(async()=>{
 let releasePendingSaveResponse;
 let observedSaveRequestCount=0;
 let submittedCoordinateRecord;
 requestAnchorHistoryCommand=async(currentCommandName,currentPayloadValue)=>{
  if(currentCommandName==='anchor-save'){
   observedSaveRequestCount++;
   submittedCoordinateRecord=structuredClone(currentPayloadValue.document);
   return await new Promise(currentResolveCallback=>{releasePendingSaveResponse=currentResolveCallback;});
  }
  return {items:[]};
 };
 refreshAnchorHistoryList=async()=>{};
 moveSelectedPoint(1,0);
 const firstSavePromise=saveCurrentAnchorCoordinates();
 if(!saveAnchorHistoryButton.disabled)throw Error('저장 중 중복 접수 차단 없음');
 let duplicateRequestRejected=false;
 try{await saveCurrentAnchorCoordinates();}catch(currentSaveError){duplicateRequestRejected=true;}
 if(!duplicateRequestRejected||observedSaveRequestCount!==1)throw Error('중복 저장 요청 허용');
 const submittedCoordinateSnapshot=JSON.stringify(submittedCoordinateRecord.frames.map(currentFrameRecord=>currentFrameRecord.anchor));
 moveSelectedPoint(1,0);
 releasePendingSaveResponse({id:'isolated-delayed-save'});
 await firstSavePromise;
 if(saveAnchorHistoryButton.disabled)throw Error('완료 후 저장 버튼 잠김');
 if(document.body.dataset.coordinateDownloadPending!=='true')throw Error('저장 중 추가 편집이 저장 완료로 표시됨');
 if(JSON.stringify(buildCoordinateArtifact().frames.map(currentFrameRecord=>currentFrameRecord.anchor))===submittedCoordinateSnapshot)throw Error('추가 편집 소실');
 requestAnchorHistoryCommand=async()=>{throw Error('격리 저장 실패');};
 await saveCurrentAnchorCoordinates();
 if(saveAnchorHistoryButton.disabled||document.body.dataset.coordinateDownloadPending!=='true')throw Error('실패 후 재시도 또는 편집 상태 소실');
 requestAnchorHistoryCommand=async()=>{const currentAbortError=new Error('signal is aborted without reason');currentAbortError.name='AbortError';throw currentAbortError;};
 await saveCurrentAnchorCoordinates();
 if(!document.querySelector('#anchorHistoryStatus').textContent.includes('이전 동작의 이력'))throw Error('응답 중단 시 저장 결과 확인 안내 누락');

})()
`,testExecutionContext);
console.log('지연 저장·중복 요청 차단·추가 편집 보존·저장 실패 후 재시도 검사 통과');

// 등록 소수 앵커와 두 발 중심·앞뒤 네 점 모드도 원본을 정확하게 복원한다.
const anchorTemplateSource=readFileSync(new URL('../ui/shared/animation-anchor-editor/editor.js',import.meta.url),'utf8');
assert.match(anchorTemplateSource,/resolveReviewAssetUrl\(currentImageFilename\)/);
for(const coordinateModeValue of ['anchor','foot-centers','endpoints']){
 const sampleContactPoints=coordinateModeValue==='anchor'?[{x:10.25,y:20.75}]:[{x:8,y:20},{x:12,y:20}];
 const sampleFrameRecords=['down_left','down_right','up_left','up_right'].map(currentDirectionName=>({frameId:currentDirectionName+'.0',direction:currentDirectionName,image:'test.png',rect:{x:0,y:0,width:100,height:100},anchor:coordinateModeValue==='anchor'?{...sampleContactPoints[0]}:{x:10,y:20},contacts:sampleContactPoints.map(currentPointRecord=>({...currentPointRecord})),endpoints:coordinateModeValue==='endpoints'?[{x:6,y:20},{x:10,y:20},{x:10,y:20},{x:14,y:20}]:[]}));
 elementLookupTable.clear();
 const modeExecutionContext=vm.createContext({document:fakeDocumentAdapter,window:{addEventListener(){}},CustomEvent:class{},Image:class{set src(sourceImageLocation){this.onload();}},requestAnimationFrame(){},performance:{now:()=>0},URL,URLSearchParams,structuredClone,sessionStorage:{getItem:()=>null,removeItem(){}},Blob,setTimeout});
 currentReviewPayloadText=JSON.stringify({schemaVersion:1,frames:sampleFrameRecords,sourceMetadata:{coordinateMode:coordinateModeValue,sheets:[],gameRenderMetrics:{tileWidth:64,tileHeight:32,characterHeight:60}}});
 vm.runInContext(anchorTemplateSource,modeExecutionContext);
 await new Promise(currentResolveCallback=>setTimeout(currentResolveCallback,0));
 vm.runInContext(`
 const originalExportSnapshot=JSON.stringify(buildCoordinateArtifact());
 moveSelectedPoint(1,0);moveFrameSelection(1);directionChoiceElement.value='up_right';directionChoiceElement.onchange();
 replayCoordinateChange(true);
 if(directionChoiceElement.value!=='down_left'||JSON.stringify(buildCoordinateArtifact())!==originalExportSnapshot)throw new Error('모드별 원본 복원 실패');
 replayCoordinateChange(false);document.querySelector('#resetCurrentFrame').onclick();
 if(JSON.stringify(buildCoordinateArtifact())!==originalExportSnapshot)throw new Error('모드별 프레임 복원 실패');
 `,modeExecutionContext);
}
console.log('실행 취소·다시 실행·저장 변경 상태·소수 앵커·양발 좌표 복원 검사 통과');

// 없는 동작을 기본 프레임으로 바꾸면 다른 원본을 편집할 수 있으므로 거절한다.
const actionSelectionSource=anchorTemplateSource.split('const reviewFrameRecords=')[0];
function evaluateActionSelection(currentSearchQuery,currentDefaultIdentifier){
 const currentPayloadRecord={schemaVersion:1,frames:[{}],sourceMetadata:{defaultActionId:currentDefaultIdentifier,actionReviews:[{id:'walk'}]}};
 return vm.runInNewContext(actionSelectionSource+';selectedActionReview?.id',{document:{querySelectorAll:()=>[{textContent:JSON.stringify(currentPayloadRecord)}]},window:{location:{search:currentSearchQuery}},URLSearchParams});
}
assert.equal(evaluateActionSelection('?action=walk','walk'),'walk');
assert.equal(evaluateActionSelection('','walk'),'walk');
assert.equal(evaluateActionSelection('',undefined),undefined);
assert.throws(()=>evaluateActionSelection('?action=missing','walk'),/등록되지 않은 앵커 동작/);
assert.throws(()=>evaluateActionSelection('','missing'),/등록되지 않은 앵커 동작/);
console.log('앵커 동작 선택·미등록 ID 거절 검사 통과');

// 뒤쪽 프레임의 손상도 앞쪽 프레임을 적용하기 전에 거절한다.
const draftRestoreSource=anchorTemplateSource.split('const storedActionDraft=')[1].split('for(const currentDirectionOption')[0];
const draftFrameRecords=[0,1].map(()=>({anchor:{x:10,y:20},contacts:[{x:10,y:20}],endpoints:[]}));
for(const currentFailureMode of ['valid','point','shape','saved','source','missing','json','null','saved-json']){
 const currentDraftFrames=structuredClone(draftFrameRecords);currentDraftFrames[0].anchor.x=30;
 const currentDraftRecord={source:[],frames:currentDraftFrames,saved:JSON.stringify(draftFrameRecords)};
 if(currentFailureMode==='point')currentDraftFrames[1].anchor.x='invalid';
 if(currentFailureMode==='shape')currentDraftFrames[1].contacts=[];
 if(currentFailureMode==='saved')currentDraftRecord.saved='{}';
 if(currentFailureMode==='source')currentDraftRecord.source=['other.png'];
 if(currentFailureMode==='missing')delete currentDraftRecord.frames;
 if(currentFailureMode==='saved-json')currentDraftRecord.saved='{';
 const currentStoredDraft=currentFailureMode==='json'?'{':currentFailureMode==='null'?'null':JSON.stringify(currentDraftRecord);
 const currentRestoreTargets=structuredClone(draftFrameRecords);
 const currentDraftStorage=new Map([['test',currentStoredDraft]]);
 let currentRecoveryNavigation=0;
 const currentRestoreContext={window:{location:{href:'http://audit.test/',replace:()=>currentRecoveryNavigation++}},sessionStorage:{getItem:currentKey=>currentDraftStorage.get(currentKey)??null,setItem:(currentKey,currentValue)=>currentDraftStorage.set(currentKey,currentValue),removeItem:currentKey=>currentDraftStorage.delete(currentKey)},actionDraftStorageKey:'test',reviewSourceMetadata:{sheets:[]},reviewFrameRecords:currentRestoreTargets,savedCoordinateSnapshotValue:'',restoreFrameCoordinates:(currentTargetFrame,currentNextCoordinates)=>Object.assign(currentTargetFrame,structuredClone(currentNextCoordinates))};
 const restoreCurrentDraft=()=>vm.runInNewContext('const storedActionDraft='+draftRestoreSource,currentRestoreContext);
 if(currentFailureMode==='valid'){restoreCurrentDraft();assert.equal(currentRestoreTargets[0].anchor.x,30);}
 else{assert.throws(restoreCurrentDraft,/앵커 초안/);assert.deepEqual(currentRestoreTargets,draftFrameRecords);}
 if(currentFailureMode==='json'){
  assert.throws(()=>currentRestoreContext.window.anchorRecoverStoredDraft(false),/확인/);
  assert.equal(currentDraftStorage.get('test'),currentStoredDraft);
  currentRestoreContext.window.anchorRecoverStoredDraft(true);
  assert.equal(currentDraftStorage.has('test'),false);
  assert.equal([...currentDraftStorage.values()][0],currentStoredDraft);
  assert.equal(currentRecoveryNavigation,1);
 }

}
console.log('손상 초안의 부분 적용 방지 검사 통과');


// 이미지 로딩 실패를 정상 프레임 상태로 보고하지 않는다.
vm.runInContext(`
currentImageLoadComplete=false;
try{window.anchorReviewPlayback('status');throw Error('준비 상태 허용');}catch(currentErrorValue){if(!currentErrorValue.message.includes('불러오는 중'))throw currentErrorValue;}
currentImageLoadFailure='이미지 로드 실패: sheet.png';
try{window.anchorReviewPlayback('status');throw Error('실패 상태 허용');}catch(currentErrorValue){if(!currentErrorValue.message.includes('sheet.png'))throw currentErrorValue;}
currentImageLoadFailure=null;currentImageLoadComplete=true;
if(!window.anchorReviewPlayback('status').includes(' / '))throw Error('정상 복원 실패');
`,testExecutionContext);

vm.runInContext(`
const currentCoordinatesBeforeFailure=JSON.stringify(reviewFrameRecords);
const currentUndoCountBeforeFailure=coordinateUndoHistory.length;
for(const currentFailureText of [null,'이미지 로드 실패: sheet.png']){
 currentImageLoadComplete=false;currentImageLoadFailure=currentFailureText;
 moveSelectedPoint(3,4);copyPreviousFrameAnchor();restoreOriginalFrameCoordinates();replayCoordinateChange(true);
 reviewCanvasElement.onclick({});
 if(JSON.stringify(reviewFrameRecords)!==currentCoordinatesBeforeFailure)throw Error('로드 실패 중 좌표 변경');
 if(coordinateUndoHistory.length!==currentUndoCountBeforeFailure)throw Error('로드 실패 중 실행 취소 기록 변경');
 if(!document.querySelector('#reviewError').textContent)throw Error('로드 안내 누락');
}
currentImageLoadComplete=true;currentImageLoadFailure=null;
`,testExecutionContext);
