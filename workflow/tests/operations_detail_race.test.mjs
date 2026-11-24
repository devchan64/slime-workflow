import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/OperationsJobs.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function inspectJob(id,event){'),end=source.indexOf('\n  useEffect(()=>{\n    if(linkedJob',start);
assert.ok(start>=0 && end>start);
test('운영 상세는 새 선택을 늦은 이전 응답이 덮지 않는다',async()=>{
  const deferred=[];let current=null,busy=false;
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},detailRequest:{current:null},diffRequest:{current:null},diffFocus:{current:null},setDiffError:()=>{},detailFocus:{current:null},detail:null,setTimeout,clearTimeout,
    setBusy:value=>busy=value,setError:()=>{},setDetailError:()=>{},setDiffPage:()=>{},setDetail:value=>current=value,setDetailCheckedAt:()=>{},
    managementCommand:(_service,_command,{id})=>new Promise(resolve=>deferred.push({id,resolve}))});
  vm.runInContext(source.slice(start,end)+'\nthis.inspectJob=inspectJob;',context);
  const first=context.inspectJob('first'),second=context.inspectJob('second');
  deferred[1].resolve({id:'second',status:{status:'completed'}});await second;assert.equal(current.id,'second');assert.equal(busy,false);
  deferred[0].resolve({id:'first',status:{status:'completed'}});await first;await new Promise(resolve=>setImmediate(resolve));assert.equal(current.id,'second');
});
test('운영 상세 재조회가 지연되면 기존 상세를 보존하고 대기를 해제한다',async()=>{
  let timer,finish,error='',busy=false,detail={id:'job',status:{status:'running'}};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,document:{activeElement:{}},detailRequest:{current:null},diffRequest:{current:null},diffFocus:{current:null},setDiffError:()=>{},detailFocus:{current:null},detail,
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:()=>{},setDetailError:value=>error=value,setDiffPage:()=>{},setDetail:value=>detail=value,setDetailCheckedAt:()=>{},
    managementCommand:()=>new Promise(resolve=>finish=resolve)});
  vm.runInContext(source.slice(start,end)+'\nthis.inspectJob=inspectJob;',context);const pending=context.inspectJob('job');timer();await pending;
  assert.equal(busy,false);assert.match(error,/이전 조회 내용을 표시/);assert.equal(detail.status.status,'running');
  finish({id:'job',status:{status:'completed'}});await new Promise(resolve=>setImmediate(resolve));assert.equal(detail.status.status,'running');
});
