import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const reviewHtmlContent=readFileSync(process.argv[2],'utf8');
const reviewScriptContent=reviewHtmlContent.split('<script>')[1].split('</script>')[0];
const elementLookupTable=new Map();
const mockCanvasContext=new Proxy({}, {get:()=>()=>{}});
function selectMockElement(selectorQueryText){if(!elementLookupTable.has(selectorQueryText))elementLookupTable.set(selectorQueryText,{value:selectorQueryText==='#directionChoice'?'down_left':selectorQueryText==='#pointChoice'?'anchor':'0',textContent:'',innerHTML:'',checked:true,getContext:()=>mockCanvasContext});return elementLookupTable.get(selectorQueryText)}
const fakeDocumentAdapter={querySelector:selectMockElement,querySelectorAll:()=>[],createElement:()=>({click(){}})};
const testExecutionContext=vm.createContext({document:fakeDocumentAdapter,Image:class{set src(sourceImageLocation){if(this.onload)this.onload()}},requestAnimationFrame(){},performance:{now:()=>0},URL,Blob,setTimeout});
vm.runInContext(reviewScriptContent,testExecutionContext);
vm.runInContext(`
const originalFirstFrameCopy=JSON.stringify(reviewFrameRecords[0]);
const originalSecondAnchorX=reviewFrameRecords[1].anchor.x;
document.querySelector('#nextFrame').onclick();
if(frameChoiceElement.value!=='1'||animationPlaybackActive)throw new Error('다음 프레임은 일시정지해야 함');
moveSelectedPoint(1,0);
if(reviewFrameRecords[1].anchor.x!==originalSecondAnchorX+1)throw new Error('1px 이동 오류');
if(JSON.stringify(reviewFrameRecords[0])!==originalFirstFrameCopy)throw new Error('다른 프레임 변경');
document.querySelector('#previousFrame').onclick();
if(frameChoiceElement.value!=='0')throw new Error('이전 프레임 오류');
document.querySelector('#previousFrame').onclick();
if(frameChoiceElement.value!=='3')throw new Error('프레임 순환 오류');
const exportedArtifactValue=buildCoordinateArtifact();
if(exportedArtifactValue.frames.length!==16||!exportedArtifactValue.description||exportedArtifactValue.source.sheets.length!==4)throw new Error('내보내기 메타데이터 누락');
for(const frameRecordValue of exportedArtifactValue.frames)for(const pointRecordValue of [...frameRecordValue.points,frameRecordValue.anchor])if(!Number.isInteger(pointRecordValue.x)||!Number.isInteger(pointRecordValue.y))throw new Error('정수 좌표 아님');
`,testExecutionContext);
assert.equal(vm.runInContext('buildCoordinateArtifact().artifactType',testExecutionContext),'character-standing-anchor-review');
console.log('프레임 전환·1px 이동·다른 프레임 보존·정수 JSON 내보내기 검사 통과');
