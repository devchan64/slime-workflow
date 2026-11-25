import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('셀 조회 실패 후 사용자가 이동한 초점은 유지한다',async()=>{
 const source=readFileSync(new URL('../../gui/MapReview.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function inspectCell('),end=source.indexOf('\n  const [ready,',start);
 assert.ok(start>=0 && end>start);
 for(const state of ['origin','body','other']){
  const body={},origin={},other={},document={body,activeElement:origin};let rejectRequest,scheduled,focused=false,feedback='',reading=false;
  const context=vm.createContext({document,window:{mapReviewControlOptions:()=>({selected:'map'})},cellDirty:false,source:null,
   readMap:()=>new Promise((_,reject)=>{rejectRequest=reject;}),setReading:value=>reading=value,setFeedback:value=>feedback=value,
   requestAnimationFrame:fn=>scheduled=fn,feedbackRef:{current:{focus:()=>focused=true}}});
  vm.runInContext(source.slice(start,end)+'\nthis.inspectCell=inspectCell;',context);
  const pending=context.inspectCell({column:9999,row:0});document.activeElement={body,origin,other}[state];rejectRequest(new Error('좌표 오류'));await pending;scheduled();
  assert.equal(feedback,'좌표 오류');assert.equal(reading,false);assert.equal(focused,state!=='other');
 }
});
