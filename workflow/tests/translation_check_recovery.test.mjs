import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {untilAborted} from '../../gui/managementCommand.js';
import {requestErrorMessage} from '../../gui/requestError.mjs';

const source=readFileSync(new URL('../../gui/TranslationResult.jsx',import.meta.url),'utf8');
const code=source.slice(source.indexOf('  async function inspect() {'),source.indexOf('  async function copy() {'));

test('번역 점검 시간 초과는 이전 표를 보존하고 늦은 응답을 무시한다',async()=>{
  let timer,resolve,checks={rows:['old']},stale=false,notice='',busy=false,calls=0;
  const delayed=new Promise(done=>resolve=done),inspectRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,job:'job',checks,inspectRequest,focusFrame:{current:null},inspectRef:{current:null},document:{activeElement:{}},setTimeout:fn=>(timer=fn,1),clearTimeout:()=>{},
    setBusy:value=>busy=value,setNotice:value=>notice=value,setChecks:value=>checks=value,setStale:value=>stale=value,translationCheckTable:value=>value,managementCommand:()=>{calls++;return delayed;}});
  vm.runInContext(code,context);const pending=context.inspect();await context.inspect();assert.equal(calls,1);timer();await pending;
  assert.equal(busy,false);assert.equal(stale,true);assert.match(notice,/시간이 초과/);assert.deepEqual(checks,{rows:['old']});
  resolve({id:'job',result:{rows:['new']}});await new Promise(done=>setImmediate(done));assert.deepEqual(checks,{rows:['old']});
});

test('화면 종료로 조회를 중단하면 늦은 번역 점검은 적용되지 않는다',async()=>{
  let resolve,updates=0;const delayed=new Promise(done=>resolve=done),inspectRequest={current:null};
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,job:'job',checks:null,inspectRequest,focusFrame:{current:null},inspectRef:{current:null},document:{activeElement:{}},setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:()=>{},setChecks:()=>updates++,setStale:()=>updates++,translationCheckTable:value=>value,managementCommand:()=>delayed});
  vm.runInContext(code,context);const pending=context.inspect();inspectRequest.current.abort();resolve({id:'job',result:{}});await pending;assert.equal(updates,0);
});

test('원본 번역이 다른 점검 응답은 적용하지 않고 일치하면 복구한다',async()=>{
  let checks={rows:['old']},stale=false,notice='',responseText='다른 원본';
  const context=vm.createContext({AbortController,untilAborted,requestErrorMessage,job:'job',sourceText:{current:'표시 원본'},checks,inspectRequest:{current:null},focusFrame:{current:null},inspectRef:{current:null},document:{activeElement:{}},setTimeout,clearTimeout,
    setBusy:()=>{},setNotice:value=>notice=value,setChecks:value=>checks=value,setCheckSource:()=>{},setStale:value=>stale=value,translationCheckTable:value=>value,managementCommand:async()=>({id:'job',result:{text:responseText,rows:['new']}})});
  vm.runInContext(code,context);await context.inspect();assert.deepEqual(checks,{rows:['old']});assert.equal(stale,true);assert.match(notice,/원본 번역과 점검 대상이 다릅니다/);
  responseText='표시 원본';await context.inspect();assert.equal(checks.text,'표시 원본');assert.equal(stale,false);assert.equal(notice,'');
});
