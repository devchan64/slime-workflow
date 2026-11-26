import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

for(const kind of ['resize','retire'])test(`${kind} 처리 지연은 중복을 막고 상태 확인을 안내한다`,async()=>{
 const source=readFileSync(new URL('../../gui/BillboardLifecycle.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function confirm(){');const code=source.slice(start,source.indexOf('  return <details',start));
 let timer,busy=false,message='',plan={kind,request:{}},calls=0,completed=0;const saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,saving,previewRequest:{current:null},restoreFocus:{current:false},plan,texture:'asset',setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setMessage:value=>message=value,setPlan:value=>plan=value,onComplete:()=>completed++,managementCommand:()=>{calls++;return new Promise(()=>{});}});
 vm.runInContext(code,context);const first=context.confirm();await context.confirm();assert.equal(calls,1);timer();await first;assert.equal(busy,false);assert.equal(saving.current,null);assert.equal(plan,null);assert.equal(completed,0);assert.match(message,/응답 시간이 초과/);assert.match(message,/에셋 상태를 확인/);
});

for(const kind of ['resize','retire'])test(`${kind} 화면 종료 후 늦은 응답은 완료 처리를 실행하지 않는다`,async()=>{
 const source=readFileSync(new URL('../../gui/BillboardLifecycle.jsx',import.meta.url),'utf8');
 const start=source.indexOf('  async function confirm(){');const code=source.slice(start,source.indexOf('  return <details',start));
 let resolve,completed=0,changes=0,message='';const saving={current:null};
 const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,saving,previewRequest:{current:null},restoreFocus:{current:false},plan:{kind,request:{},before:[256,256]},texture:'asset',setTimeout:()=>1,clearTimeout:()=>{},setBusy:()=>{},setMessage:value=>message=value,setPlan:()=>changes++,onComplete:()=>completed++,managementCommand:()=>new Promise(done=>resolve=done)});
 vm.runInContext(code,context);const running=context.confirm();const request=saving.current;saving.current=null;request.abort();resolve({retired:true,texture:'asset'});await running;assert.equal(completed,0);assert.equal(changes,0);assert.equal(message,'');
});
