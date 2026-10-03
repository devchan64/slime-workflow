import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const editorSourceText=readFileSync(new URL('../ui/shared/animation-anchor-editor/editor.js',import.meta.url),'utf8');
const actionReviewRecords=['idle','rest','walk'].map((currentActionName,currentActionIndex)=>({id:'asset:'+currentActionName,source:{animationId:currentActionName,animationVersion:'v1',coordinateMode:'anchor',sheets:[{image:currentActionName+'.png',sha256:currentActionName}],gameRenderMetrics:{tileWidth:80,tileHeight:40,characterHeight:80}},frames:[{frameId:'down_left.0',direction:'down_left',image:currentActionName+'.png',url:`/animation-${currentActionIndex+1}/${currentActionName}.png`,rect:{x:0,y:0,width:384,height:384},anchor:{x:192,y:346},contacts:[{x:192,y:346}],endpoints:[]}]}));
const draftStorageRecords=new Map();
function createActionContext(currentActionName){
 const elementLookupRecords=new Map();
 const documentAdapterValue={body:{dataset:{}},addEventListener(){},dispatchEvent(){},querySelectorAll:()=>[],querySelector(currentSelectorText){
 if(!elementLookupRecords.has(currentSelectorText))elementLookupRecords.set(currentSelectorText,{value:currentSelectorText==='#directionChoice'?'down_left':currentSelectorText==='#pointChoice'?'anchor':'0',checked:true,options:[{value:'down_left',remove(){}}],add(){},getContext:()=>({})});
 return elementLookupRecords.get(currentSelectorText);
 }};
 const actionLocationValue=new URL('file:///review.html?action=asset:'+currentActionName);actionLocationValue.replace=()=>{};
 const actionContextValue=vm.createContext({document:documentAdapterValue,window:{location:actionLocationValue,addEventListener(){}},sessionStorage:{getItem:key=>draftStorageRecords.get(key)||null,setItem:(key,value)=>draftStorageRecords.set(key,value),removeItem:key=>draftStorageRecords.delete(key)},Option:class{},CustomEvent:class{},Image:class{set src(value){this.onload();}},URL,URLSearchParams,structuredClone,requestAnimationFrame(){},performance:{now:()=>0}});
 vm.runInContext(editorSourceText.replace('__FRAME_RECORDS__','[]').replace('__SOURCE_METADATA__',JSON.stringify({actionReviews:actionReviewRecords})),actionContextValue);
 return actionContextValue;
}
for(const currentActionName of ['idle','rest','walk']){
 const currentActionContext=createActionContext(currentActionName);
 const exportedActionRecord=JSON.parse(vm.runInContext('JSON.stringify(buildCoordinateArtifact())',currentActionContext));
 assert.equal(exportedActionRecord.source.animationId,currentActionName);
 assert.equal(exportedActionRecord.frames[0].image,currentActionName+'.png');
 assert.equal(vm.runInContext('resolveReviewAssetUrl(reviewFrameRecords[0].image)',currentActionContext),actionReviewRecords.find(record=>record.id==='asset:'+currentActionName).frames[0].url);
 vm.runInContext("moveSelectedPoint(1,0);actionChoiceElement.value='asset:rest';actionChoiceElement.onchange()",currentActionContext);
}
for(const currentActionName of ['idle','rest','walk']){
 const restoredActionContext=createActionContext(currentActionName);
 assert.equal(vm.runInContext('reviewFrameRecords[0].anchor.x',restoredActionContext),193);
 assert.equal(vm.runInContext('document.body.dataset.coordinateDownloadPending',restoredActionContext),'true');
}
assert.equal(draftStorageRecords.size,3);
for(const currentActionName of ['idle','rest','walk']){
 const savedActionContext=createActionContext(currentActionName);
 await vm.runInContext(`requestAnchorHistoryCommand=async(currentCommandName,currentRequestPayload)=>{if(currentCommandName!=='anchor-save')throw new Error('다른 명령');globalThis.savedRequestPayload=currentRequestPayload;return {id:'test'};};refreshAnchorHistoryList=async()=>{};saveAnchorHistoryButton.onclick()`,savedActionContext);
 assert.equal(vm.runInContext('savedRequestPayload.document.source.animationId',savedActionContext),currentActionName);
 assert.equal(vm.runInContext('document.body.dataset.coordinateDownloadPending',savedActionContext),'false');
}
assert.equal(draftStorageRecords.size,0);
console.log('동작별 저장 출처·이미지 경로·미저장 좌표 분리 및 복원 통과');
