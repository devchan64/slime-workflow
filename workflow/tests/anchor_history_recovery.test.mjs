import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {latestRequest} from '../../gui/latestRequest.mjs';
import {anchorHistoryRequest,validAnchorHistoryPage} from '../../gui/anchorHistoryPage.mjs';

const source=readFileSync(new URL('../../gui/AnchorHistory.jsx',import.meta.url),'utf8');
test('앵커 이력이 메시지 없이 실패해도 이전 결과와 재조회 안내를 유지한다',async()=>{
  const start=source.indexOf('  async function load(next,offset=null,event) {'),end=source.indexOf('\n  function edit(',start);
  for(const problem of [null,new Error('')]){
    let error='',busy=true;const context=vm.createContext({document:{activeElement:{}},request:{current:latestRequest()},activeRequest:{current:null},AbortController,TypeError,untilAborted,animation:'walk',version:'v1',page:{next_offset:20},filtersChanged:false,focusPage:{current:null},anchorHistoryRequest:()=>({}),setTimeout,clearTimeout,setBusy:value=>busy=value,setError:value=>error=value,managementCommand:async()=>{throw problem;}});
    vm.runInContext(source.slice(start,end)+'\nthis.load=load;',context);await context.load(false);
    assert.match(error,/다시 조회/);assert.match(error,/이전 조회 결과/);assert.equal(busy,false);
  }
});
test('앵커 이력 요청이 중단을 무시해도 시간 초과 후 이전 결과를 유지한다',async()=>{
  const start=source.indexOf('  async function load(next,offset=null,event) {'),end=source.indexOf('\n  function edit(',start);assert.ok(start>=0 && end>start);
  let timeout,finish,error='',busy=false,updates=0;const context=vm.createContext({document:{activeElement:{}},request:{current:latestRequest()},activeRequest:{current:null},AbortController,untilAborted,animation:'walk',version:'v1',page:{next_offset:20},filtersChanged:false,focusPage:{current:null},
    anchorHistoryRequest:()=>({}),validAnchorHistoryPage:()=>true,setTimeout:fn=>(timeout=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setError:value=>error=value,setPage:()=>updates++,setReceivedAt:()=>{},managementCommand:()=>new Promise(resolve=>finish=resolve)});
  vm.runInContext(source.slice(start,end)+'\nthis.load=load;',context);const pending=context.load(true);timeout();await pending;
  assert.equal(busy,false);assert.match(error,/시간이 초과/);assert.match(error,/이전 조회 결과/);finish({});await new Promise(resolve=>setImmediate(resolve));assert.equal(updates,0);
});
test('검색 조건 수정은 이전 결과를 유지하고 늦은 조회와 이전 페이지 이동을 막는다',async()=>{
  const begin=source.indexOf('  function edit(setter,value) {'),end=source.indexOf('\n  function pagination(',begin);assert.ok(begin>=0 && end>begin);
  let invalidated=false,aborted=false,busy=true,value='',error='실패',page={id:'기존'};
  const context=vm.createContext({request:{current:{invalidate(){invalidated=true;}}},activeRequest:{current:{abort(){aborted=true;}}},focusPage:{current:{}},focusSearch:{current:true},setBusy:v=>busy=v,setError:v=>error=v,setPage:v=>page=v});
  vm.runInContext(source.slice(begin,end)+'\nthis.edit=edit;',context);context.edit(v=>value=v,'새 조건');
  assert.equal(invalidated,true);assert.equal(aborted,true);assert.equal(busy,false);assert.equal(value,'새 조건');assert.equal(error,'');assert.equal(page.id,'기존');assert.equal(context.focusSearch.current,false);
  assert.match(source,/filtersChanged \|\| page\.offset<=0/);assert.match(source,/filtersChanged \|\| page\.next_offset==null/);
});
test('수정 중 오래된 앵커 조회는 무시하고 새 조건의 결과만 적용한다',async()=>{
  const start=source.indexOf('  async function load(next,offset=null,event) {'),end=source.indexOf('\n  function pagination(',start);assert.ok(start>=0 && end>start);
  let resolveFirst,page={id:'기존'},filters=null,calls=[];
  const context=vm.createContext({document:{activeElement:{}},request:{current:latestRequest()},activeRequest:{current:null},AbortController,untilAborted,animation:'old',version:'v1',page,filtersChanged:false,focusPage:{current:null},focusSearch:{current:false},anchorHistoryRequest,validAnchorHistoryPage,setTimeout,clearTimeout,
    setBusy:()=>{},setError:()=>{},setPage:value=>page=value,setPageFilters:value=>filters=value,setReceivedAt:()=>{},
    managementCommand:(_service,_op,payload)=>{calls.push(payload);if(calls.length===1)return new Promise(resolve=>resolveFirst=resolve);return Promise.resolve({total:0,offset:0,records:[],snapshot:'a'.repeat(64),next_offset:null});}});
  vm.runInContext(source.slice(start,end)+'\nthis.load=load;this.edit=edit;',context);
  const first=context.load(false);context.edit(value=>context.animation=value,'new');const next=context.load(false);await next;
  resolveFirst({total:0,offset:0,records:[],snapshot:'b'.repeat(64),next_offset:null});await first;
  assert.equal(calls[1].animation_id,'new');assert.equal(filters.animation,'new');assert.equal(page.snapshot,'a'.repeat(64));
});
test('이력 조회 완료는 사라진 버튼 초점만 복구한다',()=>{
  const start=source.indexOf('  useEffect(()=>{if(!busy && focusSearch.current)'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const state of ['body','other','disabled']){
    const body={},document={body,activeElement:state==='other'?{}:body};let focused=false;
    const context=vm.createContext({document,busy:false,page:null,error:'',focusSearch:{current:true},searchButton:{current:{disabled:state==='disabled',focus(){focused=true;}}},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.equal(focused,state==='body');assert.equal(context.focusSearch.current,false);
  }
});
test('앵커 이력 페이지 이동은 잃은 초점만 결과로 이동한다',()=>{
  const start=source.indexOf('  useEffect(()=>{if(page && focusPage.current)'),end=source.indexOf('\n',start);assert.ok(start>=0 && end>start);
  for(const state of ['trigger','body','other']){
    const body={},trigger={},other={},document={body,activeElement:state==='body'?body:state==='trigger'?trigger:other};let focus=0,scroll=0;
    const context=vm.createContext({document,page:{},focusPage:{current:trigger},resultRef:{current:{focus(){focus++;},scrollIntoView(){scroll++;}}},useEffect:fn=>fn()});
    vm.runInContext(source.slice(start,end),context);assert.equal(focus,state==='other'?0:1);assert.equal(scroll,focus);assert.equal(context.focusPage.current,null);
  }
});
