import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {requestErrorMessage} from '../../gui/requestError.mjs';

test('셀 조회 실패 후 사용자가 이동한 초점은 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function inspectCell('),end=source.indexOf('\n  const [ready,',start);
 assert.ok(start>=0 && end>start);
 for(const state of ['origin','body','other']){
  const body={},origin={},other={},document={body,activeElement:origin};let rejectRequest,scheduled,focused=false,feedback='',reading=false;
  const context=vm.createContext({document,window:{mapReviewControlOptions:()=>({selected:'map'})},readRequest:{current:null},importRequest:{current:null},savingRef:{current:false},cellDirty:false,source:null,
   readMap:()=>new Promise((_,reject)=>{rejectRequest=reject;}),setReading:value=>reading=value,setFeedback:value=>feedback=value,
   requestAnimationFrame:fn=>scheduled=fn,feedbackRef:{current:{focus:()=>focused=true}},feedbackFocusOrigin:{current:null},requestErrorMessage});
  vm.runInContext(source.slice(start,end)+'\nthis.inspectCell=inspectCell;',context);
  const pending=context.inspectCell({column:9999,row:0});document.activeElement={body,origin,other}[state];rejectRequest(new Error('좌표 오류'));await pending;scheduled();
  assert.equal(feedback,'좌표 오류');assert.equal(reading,false);assert.equal(focused,state!=='other');
 }
});

test('셀 조회에서 오류 내용이 없어도 재시도 안내를 표시한다',async()=>{
 const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function inspectCell('),end=source.indexOf('\n  const [ready,',start);
 let feedback='',reading=false,scheduled;
 const document={body:{},activeElement:{}};
 const context=vm.createContext({document,window:{mapReviewControlOptions:()=>({selected:'map'})},readRequest:{current:null},importRequest:{current:null},savingRef:{current:false},cellDirty:false,source:null,
  readMap:async()=>{throw null;},setReading:value=>reading=value,setFeedback:value=>feedback=value,requestErrorMessage,
  requestAnimationFrame:fn=>scheduled=fn,feedbackRef:{current:{focus(){}}},feedbackFocusOrigin:{current:null}});
 vm.runInContext(source.slice(start,end)+'\nthis.inspectCell=inspectCell;',context);
 await context.inspectCell({column:0,row:0});scheduled();
 assert.match(feedback,/다시 시도/);assert.equal(reading,false);
});
