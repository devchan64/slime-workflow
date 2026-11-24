import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';

const source=readFileSync(new URL('../../gui/FunControlPage.jsx',import.meta.url),'utf8');
const validator=source.slice(source.indexOf('export function validFunForm('),source.indexOf('export default function FunControlPage')).replace('export function','function');
const start=source.indexOf('  useEffect(()=>{\n    if(!embedded || !session || !restoreFormId || !template)return;'),end=source.indexOf('  },[embedded,session,restoreFormId,template,restoreRevision]);',start)+'  },[embedded,session,restoreFormId,template,restoreRevision]);'.length,effect=source.slice(start,end);
const request={images:[],pose_video:'',prompt:'',negative_prompt:'',frames:21,steps:4,seed:1,flow_shift:5,guidance_scale:1,switch_ratio:.5};
test('Fun Control 저장 폼은 ID와 입력 계약을 확인한다',()=>{
 const c=vm.createContext({});vm.runInContext(validator+'\nthis.valid=validFunForm;',c);assert.equal(c.valid({form_id:'id',request,video_info:null},'id'),true);
 for(const value of [{form_id:'other',request,video_info:null},{form_id:'id',request:{...request,images:{}},video_info:null},{form_id:'id',request:{...request,frames:'21'},video_info:null},{form_id:'id',request,video_info:[]}])assert.equal(c.valid(value,'id'),false);
});
test('저장 폼 지연은 입력을 유지하고 재조회 후 적용할 수 있다',async()=>{
 assert.ok(start>=0 && end>start);let timer,cleanup,finish,busy,error='',applied,calls=0;
 const context=vm.createContext({AbortController,untilAborted,JSON,embedded:true,session:'s',restoreFormId:'id',template:{},restoreRevision:0,restorePending:{current:false},requestRef:{current:{prompt:'기존'}},attachmentRevision:{current:0},reviewEpoch:{current:0},saveAttempt:{current:null},useEffect:fn=>cleanup=fn(),setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setRestoreError:value=>error=value,managementCommand:()=>++calls===1?new Promise(done=>finish=done):Promise.resolve({form_id:'id',request,video_info:null}),requestErrorMessage:e=>e.message,setRequest:value=>applied=value,setVideoInfo:()=>{},setSourceSeed:()=>{},setSourceJob:()=>{},setJob:()=>{},setNotice:()=>{}});
 vm.runInContext(validator+'\n'+effect,context);timer();await new Promise(done=>setImmediate(done));assert.match(error,/시간이 초과/);assert.equal(busy,false);assert.equal(applied,undefined);cleanup();
 context.restoreRevision++;vm.runInContext(effect,context);await new Promise(done=>setImmediate(done));assert.equal(applied,request);assert.equal(error,'');finish({form_id:'id',request:{...request,prompt:'늦음'},video_info:null});await new Promise(done=>setImmediate(done));assert.equal(applied,request);cleanup();
});
test('저장 폼 조회 중 입력이 바뀌면 기존 입력을 덮지 않는다',async()=>{
 let cleanup,finish,error='',applied;const context=vm.createContext({AbortController,untilAborted,JSON,embedded:true,session:'s',restoreFormId:'id',template:{},restoreRevision:0,restorePending:{current:false},requestRef:{current:{prompt:'기존'}},attachmentRevision:{current:0},reviewEpoch:{current:0},saveAttempt:{current:null},useEffect:fn=>cleanup=fn(),setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setRestoreError:value=>error=value,managementCommand:()=>new Promise(done=>finish=done),requestErrorMessage:e=>e.message,setRequest:value=>applied=value,setVideoInfo:()=>{},setSourceSeed:()=>{},setSourceJob:()=>{},setJob:()=>{},setNotice:()=>{}});
 vm.runInContext(validator+'\n'+effect,context);context.requestRef.current={prompt:'새 입력'};finish({form_id:'id',request,video_info:null});await new Promise(done=>setImmediate(done));assert.match(error,/입력이 변경/);assert.equal(applied,undefined);cleanup();
});
test('저장 폼 재조회는 중복을 막고 잃은 초점만 결과로 복구한다',()=>{
 const begin=source.indexOf('onClick={()=>{if(restorePending.current || interactionRef.current.busy'),endHandler=source.indexOf('}}>저장 폼 다시 불러오기',begin),handler=source.slice(begin+'onClick={'.length,endHandler+1);
 const focus=source.match(/useEffect\(\(\)=>\{if\(busy \|\| !restoreRetryFocus\.current\)return;.*?\},\[busy,restoreError\]\);/)?.[0];assert.ok(begin>=0 && endHandler>begin && focus);
 for(const mode of ['success','failure','moved']){
  const body={},button={},other={};let run,count=0,formFocus=0,retryFocus=0;
  const context=vm.createContext({document:{body,activeElement:button},restorePending:{current:false},interactionRef:{current:{busy:false,pending:null}},restoreRetryFocus:{current:false},restoreRetryRef:{current:button},retryRestore:()=>count++,useEffect:fn=>run=fn,busy:false,restoreError:mode==='failure'?'오류':'',formRef:{current:{isConnected:true,matches:()=>false,focus:()=>formFocus++}}});
  button.isConnected=true;button.matches=()=>false;button.focus=()=>retryFocus++;
  vm.runInContext('this.retry='+handler+';'+focus,context);context.retry();context.retry();assert.equal(count,1);context.document.activeElement=mode==='moved'?other:body;run();assert.equal(formFocus,mode==='success'?1:0);assert.equal(retryFocus,mode==='failure'?1:0);
 }
});
