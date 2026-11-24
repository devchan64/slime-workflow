import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {isSpriteAnchorHistoryId} from '../../gui/spriteAnchorRestore.mjs';

const source=readFileSync(new URL('../../gui/SpriteAnchorRestore.jsx',import.meta.url),'utf8');
const start=source.indexOf('  async function save(event){'),end=source.indexOf('\n  async function prepare(event){',start);assert.ok(start>=0 && end>start);
test('앵커 저장 지연은 중복 요청을 막고 불확실 안내를 유지한다',async()=>{
  let timer,finish,busy=false,uncertain=false,notice='',calls=0,items=[];
  const original={path:'sheet.png',imageSha256:'a'.repeat(64),animation:{animationId:'walk',version:'v1',frames:[{frameId:'f',rect:{x:0,y:0,width:4,height:4},direction:'south'}]}};
  const context=vm.createContext({AbortController,untilAborted,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},writeRequest:{current:null},saving:{current:false},uncertainRef:{current:false},mounted:{current:true},original,rows:[{x:0,y:0,width:4,height:4,anchorX:2,anchorY:3}],
    setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},setBusy:value=>busy=value,setNotice:value=>notice=value,setFailed:()=>{},setReview:()=>{},setSaveUncertain:value=>uncertain=value,setItems:fn=>items=fn(items),selectId:()=>{},
    managementCommand:()=>{calls++;return new Promise(resolve=>finish=resolve);}});
  vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);const pending=context.save();await context.save();assert.equal(calls,1);
  timer();await pending;assert.equal(busy,false);assert.equal(uncertain,true);assert.match(notice,/중복 저장하지 말고/);
  await context.save();assert.equal(calls,1);
  finish({id:'2026-11-24_12-00-00-12345678'});await new Promise(resolve=>setImmediate(resolve));assert.equal(items.length,0);
});
test('앵커 입력 오류는 저장 요청을 보내지 않고 수정할 수 있다',async()=>{
  let notice='',uncertain=false,calls=0;
  const context=vm.createContext({AbortController,untilAborted,beginFocus:()=>{},focusPending:{current:{target:'trigger'}},readRequest:{current:null},writeRequest:{current:null},saving:{current:false},uncertainRef:{current:false},mounted:{current:true},original:{path:'sheet.png',animation:{frames:[{}]}},rows:[],setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:value=>notice=value,setFailed:()=>{},setReview:()=>{},setSaveUncertain:value=>uncertain=value,managementCommand:()=>calls++});
  vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);await context.save();assert.equal(calls,0);assert.equal(uncertain,false);assert.equal(context.focusPending.current.target,'notice');assert.match(notice,/프레임 수/);
});
test('앵커 좌표가 유한하지 않거나 프레임 밖이면 전송 전 수정하도록 안내한다',async()=>{
  for(const [x,y] of [[-1,0],[4,0],[0,4],['Infinity',0],['invalid',0]]){
    let notice='',uncertain=false,calls=0;
    const original={path:'sheet.png',animation:{frames:[{frameId:'f',rect:{x:0,y:0,width:4,height:4},direction:'south'}]}};
    const context=vm.createContext({AbortController,untilAborted,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},writeRequest:{current:null},saving:{current:false},uncertainRef:{current:false},mounted:{current:true},original,rows:[{x:0,y:0,width:4,height:4,anchorX:x,anchorY:y}],setTimeout,clearTimeout,
      setBusy:()=>{},setNotice:value=>notice=value,setFailed:()=>{},setReview:()=>{},setSaveUncertain:value=>uncertain=value,managementCommand:()=>calls++});
    vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);await context.save();
    assert.equal(calls,0);assert.equal(uncertain,false);assert.match(notice,/1번 프레임.*크롭 영역 안/);
  }
});
test('앵커 이력 저장은 등록 원본 적용 옵션 없이 저장 문서만 보낸다',async()=>{
  let payload,notice='';const original={path:'sheet.png',imageSha256:'a'.repeat(64),animation:{animationId:'walk',version:'v1',frames:[{frameId:'f',rect:{x:0,y:0,width:4,height:4},direction:'south'}]}};
  const rows=[{x:0,y:0,width:4,height:4,anchorX:2,anchorY:3}];
  const context=vm.createContext({AbortController,untilAborted,isSpriteAnchorHistoryId,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},writeRequest:{current:null},saving:{current:false},uncertainRef:{current:false},mounted:{current:true},latestRows:{current:rows},original,rows,setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:value=>notice=value,setFailed:()=>{},setReview:()=>{},setItems:()=>{},selectId:()=>{},setSaveUncertain:()=>{},
    managementCommand:async(_service,_operation,value)=>{payload=value;return {id:'2026-11-24_12-00-00-12345678'};}});
  vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);await context.save();
  assert.deepEqual(Object.keys(payload),['document']);assert.equal(payload.document.coordinateMode,'anchor');assert.match(notice,/저장 완료/);
  assert.doesNotMatch(notice,/편집표가 변경/);
});
test('앵커 이력 저장 중 편집표가 바뀌면 이전 입력의 저장임을 안내한다',async()=>{
  let finish,notice='';const rows=[{x:0,y:0,width:4,height:4,anchorX:2,anchorY:3}],latestRows={current:rows};
  const original={path:'sheet.png',imageSha256:'a'.repeat(64),animation:{animationId:'walk',version:'v1',frames:[{frameId:'f',rect:{x:0,y:0,width:4,height:4},direction:'south'}]}};
  const context=vm.createContext({AbortController,untilAborted,isSpriteAnchorHistoryId,beginFocus:()=>{},focusPending:{current:null},readRequest:{current:null},writeRequest:{current:null},saving:{current:false},uncertainRef:{current:false},mounted:{current:true},latestRows,original,rows,setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:value=>notice=value,setFailed:()=>{},setReview:()=>{},setItems:()=>{},selectId:()=>{},setSaveUncertain:()=>{},managementCommand:()=>new Promise(resolve=>finish=resolve)});
  vm.runInContext(source.slice(start,end)+'\nthis.save=save;',context);const pending=context.save();latestRows.current=[{...rows[0],anchorX:1}];
  finish({id:'2026-11-24_12-00-00-12345678'});await pending;assert.match(notice,/저장 요청 후 편집표가 변경/);
});
