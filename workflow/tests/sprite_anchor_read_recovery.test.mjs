import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {isSpriteAnchorHistoryId} from '../../gui/spriteAnchorRestore.mjs';

const source=readFileSync(new URL('../../gui/SpriteAnchorRestore.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function read(operation,payload){'),end=source.indexOf('\n  async function save(event){',start);assert.ok(start>=0 && end>start);
test('스프라이트 앵커 이력 조회는 지연·손상 시 이전 목록을 보존하고 선택도 유지한다',async()=>{
  const old='2026-11-24_12-00-00-11111111',next='2026-11-24_12-00-00-22222222';
  let timer,finish,busy=false,failed=false,notice='',items=[{id:old}],selected=old,mode='delay';
  const context=vm.createContext({AbortController,untilAborted,isSpriteAnchorHistoryId,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},saving:{current:false},loaded:true,original:{animation:{animationId:'walk',version:'v1'}},
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setFailed:value=>failed=value,setNotice:value=>notice=value,setItems:value=>items=value,
    selectedId:{current:old},selectId:value=>{context.selectedId.current=value;selected=value;},setReview:()=>{},setLoaded:()=>{},
    managementCommand:()=>mode==='delay'?new Promise(resolve=>finish=resolve):Promise.resolve(mode==='invalid'?{items:[{id:'../bad'}]}:mode==='duplicate'?{items:[{id:old},{id:old}]}:{items:[{id:next},{id:old}]})});
  vm.runInContext(source.slice(start,end)+'\nthis.list=list;',context);
  const pending=context.list();await context.list();timer();await pending;assert.equal(busy,false);assert.equal(failed,true);assert.match(notice,/이전 목록/);assert.equal(items[0].id,old);
  finish({items:[{id:next}]});await new Promise(resolve=>setImmediate(resolve));assert.equal(items[0].id,old);
  for(const invalidMode of ['invalid','duplicate']){mode=invalidMode;await context.list();assert.equal(failed,true);assert.equal(items[0].id,old);}
  mode='success';await context.list();assert.equal(failed,false);assert.equal(selected,old);assert.equal(items[0].id,next);
});
test('앵커 복원 내용 조회는 시간 초과와 화면 종료 뒤 늦은 결과를 적용하지 않는다',async()=>{
  const readStart=source.indexOf('  async function read(operation,payload){'),readEnd=source.indexOf('\n  async function list(event)',readStart);
  const start=source.indexOf('  async function prepare(event){'),end=source.indexOf('\n  return <details>',start);assert.ok(readStart>=0 && start>=0 && end>start);
  for(const reason of ['timeout','unmount']){
    let timer,finish,review='이전',notice='',busy=false;const readRequest={current:null};
    const context=vm.createContext({AbortController,untilAborted,beginFocus:()=>{},focusPending:{current:null},readRequest,saving:{current:false},selectedId:{current:'old'},original:{},rows:[],
      setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:value=>notice=value,setFailed:()=>{},setReview:value=>review=value,
      restoreSpriteAnchors:()=>({rows:[]}),managementCommand:()=>new Promise(resolve=>finish=resolve)});
    vm.runInContext(source.slice(readStart,readEnd)+'\n'+source.slice(start,end)+'\nthis.prepare=prepare;',context);
    const pending=context.prepare();if(reason==='timeout')timer();else{const active=readRequest.current;readRequest.current=null;active.abort();}await pending;
    if(reason==='timeout'){assert.equal(busy,false);assert.match(notice,/시간이 초과/);}else assert.equal(notice,'');
    finish({document:{}});await new Promise(resolve=>setImmediate(resolve));assert.equal(review,'이전');
  }
});
test('복원 조회 중 선택이 바뀌면 이전 이력의 성공과 오류를 표시하지 않는다',async()=>{
  const start=source.indexOf('  async function prepare(event){'),end=source.indexOf('\n  return <details>',start);
  for(const outcome of ['success','failure']){
    let resolveRead,rejectRead,review=null,notice='',busy=false,requested;
    const context=vm.createContext({AbortController,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},saving:{current:false},selectedId:{current:'old'},original:{},rows:[],
      setBusy:value=>busy=value,setNotice:value=>notice=value,setFailed:()=>{},setReview:value=>review=value,restoreSpriteAnchors:()=>({rows:[]}),
      read:(_operation,payload)=>{requested=payload.id;return new Promise((resolve,reject)=>{resolveRead=resolve;rejectRead=reject;});}});
    vm.runInContext(source.slice(start,end)+'\nthis.prepare=prepare;',context);
    const pending=context.prepare();context.selectedId.current='new';
    if(outcome==='success')resolveRead({document:{}});else rejectRead(new Error('이전 오류'));
    await pending;assert.equal(requested,'old');assert.equal(review,null);assert.equal(notice,'');assert.equal(busy,false);
  }
});
