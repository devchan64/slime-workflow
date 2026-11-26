import {restoreLostFocus,visibleFocusTarget} from '../../gui/restoreLostFocus.mjs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
const start=source.indexOf('  useEffect(()=>{\n    if(!embedded || !seedProposal || !template)return;'),end=source.indexOf('  },[embedded,seedProposal,template,seedRevision]);',start)+'  },[embedded,seedProposal,template,seedRevision]);'.length,effect=source.slice(start,end);
function fixture(fetch){
 let cleanup,timer,busy,error='',applied;const context=vm.createContext({AbortController,untilAborted,encodeURIComponent,embedded:true,seedProposal:{job_id:'id',reuse:true},template:{},seedRevision:0,seedPending:{current:false},requestRef:{current:{prompt:'기존'}},attachmentRevision:{current:0},reviewEpoch:{current:0},saveAttempt:{current:null},useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setSeedError:value=>error=value,fetch,validFunInput:record=>record.valid===true,requestErrorMessage:e=>e.message,setRequest:value=>applied=value,setReferenceReset:()=>{},setVideoInfo:()=>{},setPoseError:()=>{},setError:()=>{},poseError:"",setSourceSeed:()=>{},setSourceJob:()=>{},setJob:()=>{},setNotice:()=>{}});
 vm.runInContext(effect,context);return {context,timeout:()=>timer(),stop:()=>cleanup(),error:()=>error,busy:()=>busy,applied:()=>applied};
}
test('원본 시드 입력은 요청과 본문 지연에서 시간 초과 후 현재 입력을 유지한다',async()=>{
 for(const stage of ['request','body']){
  const f=fixture(()=>stage==='request'?new Promise(()=>{}):Promise.resolve({ok:true,json:()=>new Promise(()=>{})}));await Promise.resolve();f.timeout();await new Promise(done=>setImmediate(done));
  assert.match(f.error(),/시간이 초과/);assert.equal(f.busy(),false);assert.equal(f.applied(),undefined);f.stop();
 }
});
test('손상된 원본 입력과 조회 중 변경된 입력은 적용하지 않는다',async()=>{
 for(const mode of ['invalid','changed']){
  let finish;const f=fixture(()=>new Promise(done=>finish=done));if(mode==='changed')f.context.requestRef.current={prompt:'새 입력'};
  finish({ok:true,json:async()=>({valid:mode!=='invalid',id:'id',request:{seed:1},video:{}})});await new Promise(done=>setImmediate(done));
  assert.match(f.error(),mode==='invalid'?/입력이나 시드/:/입력이 변경/);assert.equal(f.applied(),undefined);f.stop();
 }
});
test('원본 조회 재시도에서 유효한 입력과 시드를 적용한다',async()=>{
 const f=fixture(async()=>({ok:true,json:async()=>({valid:true,id:'id',request:{seed:7,prompt:'원본'},video:{}})}));await new Promise(done=>setImmediate(done));
 assert.equal(f.applied().prompt,'원본');assert.equal(f.applied().seed,7);assert.equal(f.error(),'');assert.equal(f.busy(),false);f.stop();
});
test('원본 입력 재조회는 중복을 막고 잃은 초점만 복구한다',()=>{
 const begin=source.indexOf('onClick={()=>{if(seedPending.current || interactionRef.current.busy'),endHandler=source.indexOf('}}>원본 입력 다시 불러오기',begin),handler=source.slice(begin+'onClick={'.length,endHandler+1);
 const focus=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !seedRetryFocus\.current\)return;.*?\},\[busy,seedError\]\);/)?.[0];assert.ok(begin>=0 && endHandler>begin && focus);
 for(const mode of ['success','failure','moved','folded']){
  const body={},button={},other={};let run,count=0,formFocus=0,retryFocus=0,summaryFocus=0;
  const summary={isConnected:true,focus:()=>summaryFocus++},details={tagName:"DETAILS",open:mode!=="folded",parentElement:null,querySelector:()=>summary};
  const context=vm.createContext({restoreLostFocus,visibleFocusTarget,document:{body,activeElement:button},seedPending:{current:false},interactionRef:{current:{busy:false,pending:null}},seedRetryFocus:{current:false},seedRetryRef:{current:button},retrySeed:()=>count++,useEffect:fn=>run=fn,busy:false,seedError:mode==='failure'?'오류':'',formRef:{current:{isConnected:true,parentElement:details,matches:()=>false,focus:()=>formFocus++}}});
  button.isConnected=true;button.matches=()=>false;button.focus=()=>retryFocus++;
  vm.runInContext('this.retry='+handler+';'+focus,context);context.retry();context.retry();assert.equal(count,1);context.document.activeElement=mode==='moved'?other:body;run();assert.equal(formFocus,mode==='success'?1:0);assert.equal(retryFocus,mode==='failure'?1:0);assert.equal(summaryFocus,mode==='folded'?1:0);
 }
});
